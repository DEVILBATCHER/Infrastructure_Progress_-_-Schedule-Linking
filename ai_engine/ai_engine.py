import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# STAGE 2: NORMALIZATION  (Lesson 1 + Lesson 4)
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
# STAGE 3: EMBEDDINGS  (Lesson 10)
# ============================================================

# Load once - do NOT reload this inside a loop, it's slow.
model = SentenceTransformer('all-MiniLM-L6-v2')


def embed_texts(text_list):
    """Turn a list of sentences into a list of embedding vectors."""
    return model.encode(text_list)


# ============================================================
# STAGE 4: CANDIDATE RETRIEVAL / SEMANTIC SEARCH  (Lesson 11)
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
# STAGE 5: RERANKING  (Lesson 13)
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
# STAGE 6: CONFIDENCE SCORING  (Lesson 14)
# ============================================================

def get_confidence_level(score):
    """
    Maps a raw similarity/reranked score to a human-readable confidence band.
    NOTE: these thresholds are illustrative starting points only.
    Use evaluate() / top_k_accuracy() below on real labeled data to tune them properly.
    """
    if score >= 0.5:
        return "High"
    elif score >= 0.3:
        return "Medium"
    else:
        return "Low"


def get_confidence_with_gap(reranked_candidates):
    """
    Uses both the top score AND the gap to the second-best score to produce a
    more honest confidence level. A narrow gap means the system is not truly
    sure, even if the top score alone looks decent (e.g. near-duplicate activities).
    """
    if len(reranked_candidates) < 2:
        top_score = reranked_candidates[0][1]
        return get_confidence_level(top_score)

    top_score = reranked_candidates[0][1]
    second_score = reranked_candidates[1][1]
    gap = top_score - second_score

    if top_score >= 0.5 and gap >= 0.1:
        return "High"
    elif top_score >= 0.3:
        return "Medium"
    else:
        return "Low"


# ============================================================
# STAGE 7: EVALUATION  (Lesson 15)
# ============================================================

def evaluate(test_set, schedule_texts, schedule_ids, schedule_embeddings):
    """
    test_set: list of (report_line, true_activity_id) tuples - your labeled ground truth.
    Reports top-1 accuracy: how often the #1 predicted activity was actually correct.
    """
    correct = 0
    total = len(test_set)

    for report_line, true_activity_id in test_set:
        report_clean = full_clean(report_line)
        candidates = semantic_search(report_clean, schedule_texts, schedule_embeddings, top_k=5)
        reranked = rerank(report_clean, candidates)

        top_prediction_text = reranked[0][0]
        predicted_id = [aid for aid, text in zip(schedule_ids, schedule_texts) if text == top_prediction_text][0]

        is_correct = (predicted_id == true_activity_id)
        correct += is_correct
        status = "correct" if is_correct else "WRONG"
        print(f"Report: {report_line[:50]:<50} | Predicted: {predicted_id} | True: {true_activity_id} | {status}")

    accuracy = correct / total
    print(f"\nTop-1 Accuracy: {accuracy:.1%} ({correct}/{total})")
    return accuracy


def top_k_accuracy(test_set, schedule_texts, schedule_ids, schedule_embeddings, k=3):
    """
    Reports whether the true activity showed up ANYWHERE in the top k candidates -
    a more honest metric for a pipeline that ends in human review of a shortlist,
    rather than a fully-automatic single answer.
    """
    correct = 0
    for report_line, true_activity_id in test_set:
        report_clean = full_clean(report_line)
        candidates = semantic_search(report_clean, schedule_texts, schedule_embeddings, top_k=k)
        reranked = rerank(report_clean, candidates)

        top_k_texts = [text for text, score in reranked[:k]]
        top_k_ids = [aid for aid, text in zip(schedule_ids, schedule_texts) if text in top_k_texts]

        if true_activity_id in top_k_ids:
            correct += 1

    accuracy = correct / len(test_set)
    print(f"Top-{k} Accuracy: {accuracy:.1%}")
    return accuracy


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
    schedule_ids = ["P101", "P104", "P102", "P103"]

    # Stage 2: normalize
    schedule_clean = normalize_batch(raw_schedule)

    # Stage 3: embed once
    schedule_embeddings = embed_texts(schedule_clean)

    # --- Single report walkthrough (Stages 4-6) ---
    raw_report = "  12 INCH spool erection completed at Unit 3.  "
    report_clean = full_clean(raw_report)

    candidates = semantic_search(report_clean, schedule_clean, schedule_embeddings, top_k=4)
    reranked_candidates = rerank(report_clean, candidates)

    print("Ranked matches with confidence:")
    for text, score in reranked_candidates:
        print(f"  {score:.3f}  [{get_confidence_level(score)}]  -  {text}")

    overall_confidence = get_confidence_with_gap(reranked_candidates)
    print(f"\nOverall confidence for this report (using top-2 gap): {overall_confidence}")

    # --- Evaluation on a small labeled test set (Stage 7) ---
    print("\n--- Running evaluation ---")
    test_set = [
        ("12 inch spool erection completed at Unit 3", "P101"),
        ("Gate valve replaced - Unit 2", "P102"),
        ("Structural steel column erected, Bay 4", "P103"),
        ("Install 12-inch carbon steel pipeline, Unit 5 work done", "P104"),
    ]

    evaluate(test_set, schedule_clean, schedule_ids, schedule_embeddings)
    top_k_accuracy(test_set, schedule_clean, schedule_ids, schedule_embeddings, k=3)