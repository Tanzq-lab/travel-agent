from app.schemas import TravelEvidence
from app.utils.evidence_validator import supported_evidences


def test_supported_evidences_drop_untraceable_claims() -> None:
    valid = TravelEvidence(
        destination="重庆",
        topic="避坑",
        sentiment="negative",
        claim="7月白天热",
        source_doc_id="doc-1",
        confidence=0.8,
    )
    invalid = TravelEvidence(
        destination="重庆",
        topic="泛化建议",
        sentiment="positive",
        claim="可以去",
        source_doc_id="",
        confidence=0.5,
    )

    assert supported_evidences([valid, invalid]) == [valid]

