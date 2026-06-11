from app.schemas import TravelEvidence


def supported_evidences(evidences: list[TravelEvidence]) -> list[TravelEvidence]:
    """Keep only evidence that can be traced back to a collected source document."""

    return [
        evidence
        for evidence in evidences
        if evidence.source_doc_id and evidence.source_doc_id.strip() and evidence.claim.strip()
    ]

