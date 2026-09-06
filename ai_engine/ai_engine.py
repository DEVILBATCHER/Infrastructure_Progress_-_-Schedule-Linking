import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


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
    text = clean_text(text)
    text = normalize_units(text)
    return text


def normalize_batch(text_list):
    return [full_clean(t) for t in text_list]


# ============================================================
# STAGE 3: EMBEDDINGS
# ============================================================

model = SentenceTransformer('all-MiniLM-L6-v2')


def embed_texts(text_list):
    return model.encode(text_list)


# ============================================================
# STAGE 4: SEMANTIC SEARCH
# ============================================================

def semantic_search(report_line, schedule_texts, schedule_embeddings, top_k=5):
    report_embedding = model.encode(report_line)
    scores = cosine_similarity([report_embedding], schedule_embeddings)[0]
    results = list(zip(schedule_texts, scores))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


# ============================================================
# STAGE 5: RERANKING
# ============================================================

def extract_unit(text):
    match = re.search(r'unit\s*(\d+)', text.lower())
    return match.group(1) if match else None


def extract_measurement(text):
    match = re.search(r'(\d+)\s*inch', text.lower())
    return match.group(1) if match else None


def rerank(report_line, candidates_with_scores):
    report_unit = extract_unit(report_line)
    report_measurement = extract_measurement(report_line)

    reranked = []
    for activity_text, semantic_score in candidates_with_scores:
        boost = 0
        if report_unit and extract_unit(activity_text) == report_unit:
            boost += 0.1
        if report_measurement and extract_measurement(activity_text) == report_measurement:
            boost += 0.1
        reranked.append((activity_text, float(semantic_score) + boost))

    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked


# ============================================================
# STAGE 6: CONFIDENCE SCORING
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
# ============================================================

def _match_single(report_text, schedule_ids, schedule_texts_raw, schedule_clean,
                   schedule_embeddings, top_k, low_confidence_cutoff):
    """
    Internal helper: does the actual matching work for ONE report, given a
    schedule that has ALREADY been cleaned and embedded. Both match_report()
    and match_reports_batch() call this, so the embedding step never happens
    more than once per schedule.
    """
    # --- Edge case: empty or missing report text ---
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

        # Stage 4: retrieve candidates
        candidates = semantic_search(report_clean, schedule_clean, schedule_embeddings, top_k=max(top_k, 2))

        # Stage 5: rerank
        reranked = rerank(report_clean, candidates)

        # --- Edge case: nothing scored above the "is this even worth showing" cutoff ---
        if not reranked or reranked[0][1] < low_confidence_cutoff:
            return {
                "status": "no_match",
                "input_report": report_text,
                "top_matches": [],
                "confidence": "None",
                "message": "No sufficiently similar schedule activity was found."
            }

        # Stage 6: confidence
        confidence = get_confidence_with_gap(reranked)

        # Map cleaned activity text back to its original activity_id
        clean_to_id = dict(zip(schedule_clean, schedule_ids))
        clean_to_original_desc = dict(zip(schedule_clean, schedule_texts_raw))

        top_matches = []
        for activity_text_clean, score in reranked[:top_k]:
            top_matches.append({
                "activity_id": clean_to_id.get(activity_text_clean, "UNKNOWN"),
                "description": clean_to_original_desc.get(activity_text_clean, activity_text_clean),
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


def _prepare_schedule(schedule_data):
    """
    Shared setup step: pulls activity_id/description out of schedule_data,
    normalizes the text, and embeds it ONCE. Skips (rather than crashes on)
    any row that's missing a required field - a malformed schedule row
    shouldn't take down the whole request.
    Returns (schedule_ids, schedule_texts_raw, schedule_clean, schedule_embeddings)
    or None if nothing usable was found.
    """
    schedule_ids = []
    schedule_texts_raw = []

    for i, item in enumerate(schedule_data):
        activity_id = item.get("activity_id")
        description = item.get("description")
        if not activity_id or not description or not str(description).strip():
            # Skip bad rows instead of crashing the whole batch
            continue
        schedule_ids.append(activity_id)
        schedule_texts_raw.append(description)

    if not schedule_texts_raw:
        return None

    schedule_clean = normalize_batch(schedule_texts_raw)
    schedule_embeddings = embed_texts(schedule_clean)
    return schedule_ids, schedule_texts_raw, schedule_clean, schedule_embeddings


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

    NOTE: if you have MULTIPLE reports to match against the same schedule,
    use match_reports_batch() instead - it embeds the schedule only once
    for all reports, instead of once per report.
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

    prepared = _prepare_schedule(schedule_data)
    if prepared is None:
        return {
            "status": "error",
            "input_report": report_text,
            "top_matches": [],
            "confidence": "None",
            "message": "No usable schedule activities found (all rows missing activity_id/description)."
        }

    schedule_ids, schedule_texts_raw, schedule_clean, schedule_embeddings = prepared
    return _match_single(report_text, schedule_ids, schedule_texts_raw, schedule_clean,
                          schedule_embeddings, top_k, low_confidence_cutoff)


def match_reports_batch(report_list, schedule_data, top_k=3, low_confidence_cutoff=0.15):
    """
    Match MANY reports against the same schedule in one call.
    This is the function to use for an upload-a-file-of-reports workflow
    (e.g. Person 2's POST /upload-report handling a whole Excel/CSV of reports),
    since it embeds the schedule only ONCE and reuses it for every report,
    instead of re-embedding it per report like calling match_report() in a loop would.

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

    prepared = _prepare_schedule(schedule_data)
    if prepared is None:
        return {
            "status": "error",
            "results": [],
            "message": "No usable schedule activities found (all rows missing activity_id/description)."
        }

    schedule_ids, schedule_texts_raw, schedule_clean, schedule_embeddings = prepared

    results = []
    for report_text in report_list:
        result = _match_single(report_text, schedule_ids, schedule_texts_raw, schedule_clean,
                                schedule_embeddings, top_k, low_confidence_cutoff)
        results.append(result)

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

    # Empty report
    print("\nEmpty report:", match_report("", schedule_data))

    # Empty schedule
    print("\nEmpty schedule:", match_report("some report text", []))

    # Nonsense / unrelated report -> likely no_match or low confidence
    print("\nUnrelated report:", match_report("Weather was sunny today, no work performed.", schedule_data))

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