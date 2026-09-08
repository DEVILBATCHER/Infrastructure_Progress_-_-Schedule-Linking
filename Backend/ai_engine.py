import re
import chromadb
from sentence_transformers import SentenceTransformer


# ============================================================
# STAGE 2: NORMALIZATION
# ============================================================

def clean_text(text):
    if text is None:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\-]', '', text)
    return text


def normalize_units(text):
    text = re.sub(r'(\d+)\s*-?\s*inch', r'\1 inch', text)
    text = re.sub(r'(\d+)"', r'\1 inch', text)
    return text


def full_clean(text):
    # normalize_units must run BEFORE clean_text: clean_text strips the "
    # character, so if it ran first, the (\d+)" -> "\1 inch" rule would
    # never match anything (e.g. 12" would collapse straight to "12").
    text = normalize_units(text)
    text = clean_text(text)
    return text


def normalize_batch(text_list):
    return [full_clean(t) for t in text_list]


# ============================================================
# STAGE 3: EMBEDDINGS + STORAGE (now ChromaDB instead of an in-memory array)
# ============================================================

model = SentenceTransformer('all-MiniLM-L6-v2')

# PersistentClient saves the index to disk in ./chroma_data, so the schedule
# stays indexed between separate runs of the program, not just within one.
_chroma_client = chromadb.PersistentClient(path="./chroma_data")
_collection = _chroma_client.get_or_create_collection(
    name="schedule_activities",
    metadata={"hnsw:space": "cosine"}  # match the cosine similarity semantics used everywhere else
)


def embed_texts(text_list):
    return model.encode(text_list)


def _prepare_schedule(schedule_data):
    """
    Filters out malformed rows, normalizes the survivors, embeds them, and
    upserts them into the Chroma collection keyed by activity_id.

    upsert (not add) means calling this again with the same schedule just
    refreshes the existing entries instead of erroring - safe to call on
    every match_report()/match_reports_batch() call, the same way the old
    in-memory _prepare_schedule() re-ran on every call.

    Returns True if at least one usable row was indexed, False otherwise.
    """
    schedule_ids = []
    schedule_texts_raw = []

    for item in schedule_data:
        activity_id = item.get("activity_id")
        description = item.get("description")
        if not activity_id or not description or not str(description).strip():
            # Skip bad rows instead of crashing the whole batch
            continue
        schedule_ids.append(activity_id)
        schedule_texts_raw.append(description)

    if not schedule_texts_raw:
        return False

    schedule_clean = normalize_batch(schedule_texts_raw)
    schedule_embeddings = embed_texts(schedule_clean).tolist()  # Chroma wants plain lists, not numpy arrays

    _collection.upsert(
        ids=schedule_ids,
        embeddings=schedule_embeddings,
        documents=schedule_texts_raw,                          # original text, for display
        metadatas=[{"clean_text": c} for c in schedule_clean]  # cleaned text, needed for the rerank boost
    )
    return True


# ============================================================
# STAGE 4: SEMANTIC SEARCH (now a Chroma query instead of sklearn cosine_similarity)
# ============================================================

def semantic_search(report_line, top_k=5):
    """
    Returns (activity_id, similarity, original_description, clean_text)
    tuples, sorted best-first. Because Chroma keys everything by
    activity_id (not by text), two schedule rows with identical
    descriptions can never collide the way a text-keyed lookup could.
    """
    report_embedding = model.encode(report_line).tolist()
    results = _collection.query(query_embeddings=[report_embedding], n_results=top_k)

    ids = results["ids"][0]
    distances = results["distances"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    candidates = []
    for activity_id, distance, doc, meta in zip(ids, distances, documents, metadatas):
        similarity = 1 - distance  # cosine space: distance = 1 - similarity
        candidates.append((activity_id, similarity, doc, meta["clean_text"]))
    return candidates


# ============================================================
# STAGE 5: RERANKING
# ============================================================

def extract_unit(text):
    match = re.search(r'unit\s*(\d+)', text.lower())
    return match.group(1) if match else None


def extract_measurement(text):
    match = re.search(r'(\d+)\s*inch', text.lower())
    return match.group(1) if match else None


def rerank(report_line, candidates):
    """
    candidates: list of (activity_id, similarity, description, clean_text),
    as returned by semantic_search().
    """
    report_unit = extract_unit(report_line)
    report_measurement = extract_measurement(report_line)

    reranked = []
    for activity_id, score, description, clean_text_val in candidates:
        boost = 0
        if report_unit and extract_unit(clean_text_val) == report_unit:
            boost += 0.1
        if report_measurement and extract_measurement(clean_text_val) == report_measurement:
            boost += 0.1
        reranked.append((activity_id, float(score) + boost, description))

    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked


# ============================================================
# STAGE 6: CONFIDENCE SCORING (unchanged - only ever looks at the score)
# ============================================================

def get_confidence_with_gap(reranked_candidates):
    if len(reranked_candidates) == 0:
        return "None"
    if len(reranked_candidates) < 2:
        top_score = reranked_candidates[0][1]
    else:
        top_score = reranked_candidates[0][1]
        second_score = reranked_candidates[1][1]
        gap = top_score - second_score
        if top_score >= 0.5 and gap >= 0.1:
            return "High"
        elif top_score >= 0.3:
            return "Medium"
        else:
            return "Low"

    if top_score >= 0.5:
        return "High"
    elif top_score >= 0.3:
        return "Medium"
    return "Low"


# ============================================================
# THE INTEGRATION FUNCTION - what Person 2 will actually call
# (signatures and return shapes are UNCHANGED from the sklearn version -
#  schemas.py is still accurate, no changes needed on Person 2's side)
# ============================================================

def _match_single(report_text, top_k, low_confidence_cutoff):
    """
    Internal helper: does the actual matching work for ONE report, against
    whatever is currently indexed in the Chroma collection.
    """
    if not report_text or not report_text.strip():
        return {
            "status": "error",
            "input_report": report_text,
            "top_matches": [],
            "confidence": "None",
            "message": "Report text is empty or missing."
        }

    try:
        report_clean = full_clean(report_text)

        candidates = semantic_search(report_clean, top_k=max(top_k, 2))
        reranked = rerank(report_clean, candidates)

        if not reranked or reranked[0][1] < low_confidence_cutoff:
            return {
                "status": "no_match",
                "input_report": report_text,
                "top_matches": [],
                "confidence": "None",
                "message": "No sufficiently similar schedule activity was found."
            }

        confidence = get_confidence_with_gap(reranked)

        top_matches = []
        for activity_id, score, description in reranked[:top_k]:
            top_matches.append({
                "activity_id": activity_id,
                "description": description,
                "score": round(float(score), 4)
            })

        return {
            "status": "matched",
            "input_report": report_text,
            "top_matches": top_matches,
            "confidence": confidence
        }

    except Exception as e:
        # Never let the backend get an unhandled crash - always return valid JSON
        return {
            "status": "error",
            "input_report": report_text,
            "top_matches": [],
            "confidence": "None",
            "message": f"Matching engine failed: {str(e)}"
        }


def match_report(report_text, schedule_data, top_k=3, low_confidence_cutoff=0.15):
    """
    The single entry point for matching ONE report against the schedule.

    Parameters
    ----------
    report_text : str
        Raw text from a daily report (e.g. "12 inch spool erection completed at Unit 3").
    schedule_data : list of dict
        Each dict must have "activity_id" and "description" keys, e.g.:
        [{"activity_id": "P101", "description": "Install 12-inch carbon steel pipeline"}, ...]
        Indexed into ChromaDB (upsert) every call, so an updated schedule is
        always reflected immediately.
    top_k : int
        How many candidate matches to return.
    low_confidence_cutoff : float
        If the top score is below this, treat it as "no match found" rather than
        returning a misleading low-quality match.

    Returns
    -------
    dict - JSON-serializable, ready to hand back through an API response.
    {
        "status": "matched" | "no_match" | "error",
        "input_report": "...",
        "top_matches": [
            {"activity_id": "P101", "description": "...", "score": 0.42},
            ...
        ],
        "confidence": "High" | "Medium" | "Low" | "None",
        "message": "..."   # present on error / no_match
    }

    NOTE: if you have MULTIPLE reports to match against the same schedule in
    one request, use match_reports_batch() instead - it indexes the schedule
    only once for all reports, instead of once per report.
    """
    if not report_text or not report_text.strip():
        return {
            "status": "error",
            "input_report": report_text,
            "top_matches": [],
            "confidence": "None",
            "message": "Report text is empty or missing."
        }

    if not schedule_data:
        return {
            "status": "error",
            "input_report": report_text,
            "top_matches": [],
            "confidence": "None",
            "message": "No schedule activities were provided to match against."
        }

    if not _prepare_schedule(schedule_data):
        return {
            "status": "error",
            "input_report": report_text,
            "top_matches": [],
            "confidence": "None",
            "message": "No usable schedule activities found (all rows missing activity_id/description)."
        }

    return _match_single(report_text, top_k, low_confidence_cutoff)


def match_reports_batch(report_list, schedule_data, top_k=3, low_confidence_cutoff=0.15):
    """
    Match MANY reports against the same schedule in one call.
    This is the function to use for an upload-a-file-of-reports workflow
    (e.g. Person 2's POST /upload-report handling a whole Excel/CSV of reports),
    since it indexes the schedule only ONCE and reuses it for every report,
    instead of re-indexing it per report like calling match_report() in a loop would.

    Parameters
    ----------
    report_list : list of str
        Multiple raw report text lines.
    schedule_data : list of dict
        Same format as match_report().
    top_k, low_confidence_cutoff : same as match_report().

    Returns
    -------
    dict:
    {
        "status": "completed" | "error",
        "results": [ <same dict shape match_report() returns>, ... ]   # one per report, same order as input
        "message": "..."   # present on error
    }
    """
    if not report_list:
        return {
            "status": "error",
            "results": [],
            "message": "No reports were provided to match."
        }

    if not schedule_data:
        return {
            "status": "error",
            "results": [],
            "message": "No schedule activities were provided to match against."
        }

    if not _prepare_schedule(schedule_data):
        return {
            "status": "error",
            "results": [],
            "message": "No usable schedule activities found (all rows missing activity_id/description)."
        }

    results = [_match_single(report_text, top_k, low_confidence_cutoff) for report_text in report_list]

    return {
        "status": "completed",
        "results": results
    }


# ============================================================
# QUICK LOCAL TEST - run this file directly to sanity-check
# ============================================================

if __name__ == "__main__":
    schedule_data = [
        {"activity_id": "P101", "description": "Install 12-inch carbon steel pipeline, Unit 3"},
        {"activity_id": "P104", "description": "Install 12-inch carbon steel pipeline, Unit 5"},
        {"activity_id": "P102", "description": "Replace 6-inch gate valve at Unit 2"},
        {"activity_id": "P103", "description": "Erect structural steel column at Bay 4"},
    ]

    # Normal case
    result = match_report("12 inch spool erection completed at Unit 3.", schedule_data)
    print("Normal case:", result)

    # Quote-style measurement (regression check for the normalization-order fix)
    print("\nQuote-style measurement:", match_report('12" spool erection completed at Unit 3.', schedule_data))

    # Empty report
    print("\nEmpty report:", match_report("", schedule_data))

    # Empty schedule
    print("\nEmpty schedule:", match_report("some report text", []))

    # Nonsense / unrelated report -> likely no_match or low confidence
    print("\nUnrelated report:", match_report("Weather was sunny today, no work performed.", schedule_data))

    # Duplicate-description regression check: two rows, identical text,
    # different activity_id - Chroma keys by id, so no collision.
    dup_schedule = schedule_data + [{"activity_id": "P105", "description": "Replace 6-inch gate valve at Unit 2"}]
    print("\nDuplicate description schedule:", match_report("Gate valve replaced - Unit 2", dup_schedule))

    # --- Batch test: several reports matched against the same schedule at once ---
    print("\n--- Batch test ---")
    reports = [
        "12 inch spool erection completed at Unit 3.",
        "Gate valve replaced - Unit 2",
        "Weather was sunny today, no work performed.",
        "",  # deliberately empty, to confirm it's handled gracefully inside a batch
    ]
    batch_result = match_reports_batch(reports, schedule_data)
    print("Batch status:", batch_result["status"])
    for i, r in enumerate(batch_result["results"]):
        print(f"  [{i}] status={r['status']} confidence={r['confidence']} "
              f"top_match={r['top_matches'][0]['activity_id'] if r['top_matches'] else None}")

    # --- Malformed schedule row test: one bad row shouldn't break everything ---
    print("\n--- Malformed schedule row test ---")
    messy_schedule = schedule_data + [{"activity_id": "P999"}]  # missing "description"
    print(match_report("12 inch spool erection completed at Unit 3.", messy_schedule))