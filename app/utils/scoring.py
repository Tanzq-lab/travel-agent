from __future__ import annotations

from collections import Counter

from app.schemas import EvidenceSummary, JudgeResult, TravelEvidence, UserIntent


def summarize_evidence(total_docs: int, evidences: list[TravelEvidence]) -> EvidenceSummary:
    """Count documents and evidence by sentiment."""

    counts = Counter(evidence.sentiment for evidence in evidences)
    return EvidenceSummary(
        total_docs=total_docs,
        total_evidences=len(evidences),
        positive_count=counts["positive"],
        negative_count=counts["negative"],
        neutral_count=counts["neutral"],
    )


def score_destination(intent: UserIntent, evidences: list[TravelEvidence], total_docs: int) -> JudgeResult:
    """Score destination fit using only collected structured evidence."""

    summary = summarize_evidence(total_docs, evidences)
    if total_docs < 2 or len(evidences) < 3:
        return JudgeResult(
            final_judgement="资料不足，暂不能判断",
            score=0,
            suitable_reasons=[],
            risk_reasons=["资料不足，暂不能判断；当前 evidence 数量不足以支撑确定结论。"],
            suitable_for=[],
            not_suitable_for=[],
            confidence="低",
            evidence_summary=summary,
        )

    score = 60
    score += min(summary.positive_count * 4, 20)
    score -= min(summary.negative_count * 3, 18)

    positive_reasons: list[str] = []
    risk_reasons: list[str] = []
    suitable_for: list[str] = []
    not_suitable_for: list[str] = []

    user_traits = set(intent.preferences + intent.constraints + intent.companions)
    if intent.budget_level:
        user_traits.add(intent.budget_level)
    if intent.days:
        user_traits.add(f"{intent.days}天")
    if intent.travel_month:
        user_traits.add(f"{intent.travel_month}月")

    for evidence in evidences:
        if evidence.sentiment == "positive":
            positive_reasons.append(f"资料显示：{evidence.claim}")
        elif evidence.sentiment == "negative":
            risk_reasons.append(f"资料提醒：{evidence.claim}")

        suitable_for.extend(evidence.suitable_for)
        not_suitable_for.extend(evidence.not_suitable_for)

        evidence_targets = set(evidence.suitable_for + evidence.not_suitable_for)
        if evidence.mentioned_duration:
            evidence_targets.add(evidence.mentioned_duration)
        if evidence.mentioned_budget:
            evidence_targets.add(evidence.mentioned_budget)
        if evidence.mentioned_season:
            evidence_targets.add(evidence.mentioned_season)

        if evidence.sentiment == "positive" and user_traits & evidence_targets:
            score += 3
        if evidence.sentiment == "negative" and user_traits & evidence_targets:
            score -= 5

        if intent.travel_month and evidence.mentioned_season:
            if str(intent.travel_month) in evidence.mentioned_season and evidence.sentiment == "negative":
                score -= 5
            elif str(intent.travel_month) in evidence.mentioned_season and evidence.sentiment == "positive":
                score += 2

    if summary.negative_count > 0 and summary.positive_count > 0:
        score -= 3
    if summary.total_evidences < 6:
        score -= 8

    score = max(0, min(100, score))
    if score >= 75 and summary.negative_count <= 2:
        judgement = "适合"
    elif score < 45 or summary.negative_count > summary.positive_count + 3:
        judgement = "不适合"
    else:
        judgement = "条件适合"

    confidence = "高" if total_docs >= 8 and len(evidences) >= 20 else "中" if total_docs >= 3 and len(evidences) >= 6 else "低"

    return JudgeResult(
        final_judgement=judgement,
        score=score,
        suitable_reasons=_dedupe(positive_reasons)[:6],
        risk_reasons=_dedupe(risk_reasons)[:6],
        suitable_for=_dedupe(suitable_for)[:8],
        not_suitable_for=_dedupe(not_suitable_for)[:8],
        confidence=confidence,
        evidence_summary=summary,
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

