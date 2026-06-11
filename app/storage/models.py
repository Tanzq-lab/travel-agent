from dataclasses import dataclass


@dataclass(frozen=True)
class ReportRow:
    """Internal SQLite report row representation."""

    request_id: str
    created_at: str
    user_query: str
    intent_json: str
    queries_json: str
    evidence_summary_json: str
    judgement_json: str
    report_md: str

