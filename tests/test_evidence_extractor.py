from app.agents.evidence_extractor import EvidenceExtractor
from app.collectors.mock_collector import MockCollector
from app.schemas import TravelEvidence


def test_evidence_extractor_validates_schema_and_source_doc_id() -> None:
    docs = MockCollector(platforms=["xhs"]).search("重庆 7月 避坑", limit=3)
    evidences = EvidenceExtractor().extract_from_documents("重庆", docs)

    assert evidences
    assert all(isinstance(evidence, TravelEvidence) for evidence in evidences)
    assert all(evidence.source_doc_id for evidence in evidences)
    assert any(evidence.topic == "季节风险" for evidence in evidences)
    assert any(evidence.sentiment == "negative" for evidence in evidences)

