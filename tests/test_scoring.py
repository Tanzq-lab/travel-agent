from app.schemas import TravelEvidence, UserIntent
from app.utils.scoring import score_destination


def evidence(sentiment: str, claim: str, **kwargs) -> TravelEvidence:
    return TravelEvidence(
        destination="重庆",
        topic=kwargs.pop("topic", "测试"),
        sentiment=sentiment,
        claim=claim,
        source_doc_id=kwargs.pop("source_doc_id", claim),
        confidence=0.8,
        **kwargs,
    )


def test_scoring_returns_insufficient_when_evidence_is_too_thin() -> None:
    intent = UserIntent(destination="重庆")
    result = score_destination(intent, [], total_docs=0)

    assert result.final_judgement == "资料不足，暂不能判断"
    assert result.confidence == "低"


def test_scoring_can_return_suitable() -> None:
    intent = UserIntent(destination="成都", preferences=["美食", "拍照"], days=3)
    evidences = [
        evidence("positive", "美食集中", suitable_for=["美食"]),
        evidence("positive", "拍照点多", suitable_for=["拍照"]),
        evidence("positive", "三天路线成熟", mentioned_duration="3天"),
        evidence("positive", "交通方便"),
        evidence("positive", "住宿选择多"),
        evidence("neutral", "热门点节假日人多"),
    ]

    result = score_destination(intent, evidences, total_docs=4)

    assert result.final_judgement in {"适合", "条件适合"}
    assert result.score >= 70


def test_scoring_returns_conditional_for_chongqing_july_parents() -> None:
    intent = UserIntent(
        destination="重庆",
        days=3,
        budget_level="中等预算",
        companions=["父母"],
        constraints=["怕热", "不喜欢太累"],
        travel_month=7,
    )
    evidences = [
        evidence("negative", "7月重庆白天户外游玩体验较差", not_suitable_for=["怕热"], mentioned_season="7月"),
        evidence("negative", "山城坡多，带老人不宜连续爬坡", not_suitable_for=["带父母", "不喜欢太累"]),
        evidence("negative", "洪崖洞拥挤", not_suitable_for=["怕挤"]),
        evidence("positive", "三峡博物馆适合白天", suitable_for=["带父母", "怕热"]),
        evidence("positive", "三天轻松路线可行", suitable_for=["不喜欢太累"], mentioned_duration="3天"),
        evidence("positive", "中等预算一般够用", suitable_for=["中等预算"], mentioned_budget="中等预算"),
        evidence("neutral", "解放碑交通方便但价格偏高"),
    ]

    result = score_destination(intent, evidences, total_docs=5)

    assert result.final_judgement == "条件适合"
    assert 45 <= result.score < 75


def test_scoring_can_return_unsuitable() -> None:
    intent = UserIntent(destination="重庆", constraints=["怕热"], travel_month=7)
    evidences = [
        evidence("negative", "7月白天很热", not_suitable_for=["怕热"], mentioned_season="7月"),
        evidence("negative", "热门景点排队久", not_suitable_for=["怕挤"]),
        evidence("negative", "坡多很累", not_suitable_for=["不喜欢太累"]),
        evidence("negative", "住宿核心区价格高"),
        evidence("negative", "夜景点拥挤"),
        evidence("positive", "夜景好看"),
    ]

    result = score_destination(intent, evidences, total_docs=4)

    assert result.final_judgement == "不适合"

