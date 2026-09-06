"""
schemas.py

This file does not contain any logic - it exists purely to document the exact
shape of the data passed between the AI/NLP matching engine (ai_engine_final.py)
and the backend (Person 2's FastAPI + PostgreSQL code).

Use this as the reference when wiring the two systems together. If the actual
shape of a request/response ever needs to change, update it here first so both
sides stay in sync.
"""

from typing import TypedDict, List, Literal


# ============================================================
# INPUT: one schedule activity
# ============================================================
# This is what each item in `schedule_data` must look like when calling
# match_report() or match_reports_batch(). Comes from Person 2's PostgreSQL
# schedule table.

class ScheduleItem(TypedDict):
    activity_id: str    # e.g. "P101"  - must be unique per activity
    description: str    # e.g. "Install 12-inch carbon steel pipeline"


# Example:
# schedule_data: List[ScheduleItem] = [
#     {"activity_id": "P101", "description": "Install 12-inch carbon steel pipeline"},
#     {"activity_id": "P102", "description": "Replace 6-inch gate valve at Unit 2"},
# ]
#
# NOTE: a row missing activity_id or description will be silently skipped by
# the matching engine rather than causing an error - it will not appear in
# any results, so malformed rows should ideally be filtered/fixed on the
# backend side too, not just relied on here.


# ============================================================
# OUTPUT: one candidate match
# ============================================================
# Appears inside "top_matches" in both match_report() and match_reports_batch()
# results.

class MatchCandidate(TypedDict):
    activity_id: str    # matches ScheduleItem["activity_id"]
    description: str    # the ORIGINAL (not cleaned/normalized) description text
    score: float         # 0.0 to roughly 1.0+ (reranking can push slightly above 1.0
                          # due to the added boost - do not assume a hard ceiling of 1.0)


# ============================================================
# OUTPUT: match_report() - single report result
# ============================================================

MatchStatus = Literal["matched", "no_match", "error"]
ConfidenceLevel = Literal["High", "Medium", "Low", "None"]


class MatchReportResult(TypedDict, total=False):
    status: MatchStatus
    input_report: str
    top_matches: List[MatchCandidate]   # empty list if status is "no_match" or "error"
    confidence: ConfidenceLevel
    message: str                         # ONLY present when status is "error" or "no_match"


# Example - a successful match:
# {
#     "status": "matched",
#     "input_report": "12 inch spool erection completed at Unit 3.",
#     "top_matches": [
#         {"activity_id": "P101", "description": "Install 12-inch carbon steel pipeline, Unit 3", "score": 0.648},
#         {"activity_id": "P104", "description": "Install 12-inch carbon steel pipeline, Unit 5", "score": 0.4882},
#     ],
#     "confidence": "High"
# }
#
# Example - no match found:
# {
#     "status": "no_match",
#     "input_report": "Weather was sunny today, no work performed.",
#     "top_matches": [],
#     "confidence": "None",
#     "message": "No sufficiently similar schedule activity was found."
# }


# ============================================================
# OUTPUT: match_reports_batch() - many reports at once
# ============================================================

BatchStatus = Literal["completed", "error"]


class MatchBatchResult(TypedDict, total=False):
    status: BatchStatus
    results: List[MatchReportResult]   # same order as the input report_list; empty if status is "error"
    message: str                        # ONLY present when status is "error"


# Example:
# {
#     "status": "completed",
#     "results": [
#         { ... a MatchReportResult for report_list[0] ... },
#         { ... a MatchReportResult for report_list[1] ... },
#     ]
# }


# ============================================================
# QUICK REFERENCE - which function to call
# ============================================================
#
# ONE report to match          -> match_report(report_text: str, schedule_data: List[ScheduleItem]) -> MatchReportResult
# MANY reports (e.g. one file  -> match_reports_batch(report_list: List[str], schedule_data: List[ScheduleItem]) -> MatchBatchResult
# upload) to match at once
#
# Both functions are safe to call with malformed input - they return a
# structured "error" status instead of raising an exception, EXCEPT for
# truly unexpected bugs, which are still caught internally and converted
# to an "error" status result rather than crashing the caller.
