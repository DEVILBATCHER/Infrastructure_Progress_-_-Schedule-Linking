import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# STAGE 2: NORMALIZATION  (from Lesson 1 + Lesson 4)
# ============================================================

def clean_text(text):
    """Lowercase, strip whitespace, collapse extra spaces, remove punctuation
    (but keep hyphens, since they show up in things like '12-inch')."""
    if text is None:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)              # collapse multiple spaces
    text = re.sub(r'[^\w\s\-]', '', text)          # strip punctuation
    return text


def normalize_units(text):
    """Standardize unit phrasing so '12-inch', '12 inch', and 12" all match."""
    text = re.sub(r'(\d+)\s*-?\s*inch', r'\1 inch', text)
    text = re.sub(r'(\d+)"', r'\1 inch', text)
    return text


def full_clean(text):
    """Run the complete normalization pipeline on one piece of text."""
    text = clean_text(text)
    text = normalize_units(text)
    return text


def normalize_batch(text_list):
    """Apply full_clean() across a whole list of texts."""
    return [full_clean(t) for t in text_list]


# ============================================================
# STAGE 3: EMBEDDINGS  (from Lesson 10)
# ============================================================

# Load once - do NOT reload this inside a loop, it's slow.
model = SentenceTransformer('all-MiniLM-L6-v2')


def embed_texts(text_list):
    """Turn a list of sentences into a list of embedding vectors."""
    return model.encode(text_list)


# ============================================================
# STAGE 4: CANDIDATE RETRIEVAL / SEMANTIC SEARCH  (from Lesson 11)
# ============================================================

def semantic_search(report_line, schedule_texts, schedule_embeddings, top_k=5):
    """
    Compare one report line against all schedule activities.
    Returns the top_k matches as a list of (activity_text, semantic_score) tuples,
    ranked highest score first.
    """
    report_embedding = model.encode(report_line)
    scores = cosine_similarity([report_embedding], schedule_embeddings)[0]

    results = list(zip(schedule_texts, scores))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


# ============================================================
# STAGE 5: RERANKING  (from Lesson 13)
# ============================================================

def extract_unit(text):
    """Pull out something like 'Unit 3' from text, if present."""
    match = re.search(r'unit\s*(\d+)', text.lower())
    return match.group(1) if match else None


def extract_measurement(text):
    """Pull out something like '12 inch' from text, if present."""
    match = re.search(r'(\d+)\s*inch', text.lower())
    return match.group(1) if match else None


def rerank(report_line, candidates_with_scores):
    """
    Re-score the top candidates from semantic_search() using explicit signals
    (matching unit number, matching measurement) that embeddings can underweight.
    """
    report_unit = extract_unit(report_line)
    report_measurement = extract_measurement(report_line)

    reranked = []
    for activity_text, semantic_score in candidates_with_scores:
        boost = 0
        if report_unit and extract_unit(activity_text) == report_unit:
            boost += 0.1
        if report_measurement and extract_measurement(activity_text) == report_measurement:
            boost += 0.1

        final_score = semantic_score + boost
        reranked.append((activity_text, final_score))

    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked


# ============================================================
# PUTTING IT TOGETHER - a quick end-to-end test
# ============================================================

if __name__ == "__main__":
    # Raw schedule data (would normally come from Person 2's database)
    raw_schedule = [
        "Install 12-inch carbon steel pipeline, Unit 3",
        "Install 12-inch carbon steel pipeline, Unit 5",
        "Replace 6-inch gate valve at Unit 2",
        "Erect structural steel column at Bay 4",
    ]

    # Stage 2: normalize
    schedule_clean = normalize_batch(raw_schedule)

    # Stage 3: embed once
    schedule_embeddings = embed_texts(schedule_clean)

    # A new incoming report
    raw_report = "  12 INCH spool erection completed at Unit 3.  "
    report_clean = full_clean(raw_report)

    # Stage 4: retrieve top candidates
    candidates = semantic_search(report_clean, schedule_clean, schedule_embeddings, top_k=4)
    print("Semantic search results (before reranking):")
    for text, score in candidates:
        print(f"  {score:.3f}  -  {text}")

    # Stage 5: rerank
    reranked_candidates = rerank(report_clean, candidates)
    print("\nAfter reranking:")
    for text, score in reranked_candidates:
        print(f"  {score:.3f}  -  {text}")