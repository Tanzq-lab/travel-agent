from __future__ import annotations

from collections import Counter

from app.schemas import CollectionError, CollectionSummary, JudgeResult, RawDocument, TravelEvidence, UserIntent


class ReportWriter:
    """Generate a Markdown travel decision report from judgement and evidence."""

    def write(
        self,
        intent: UserIntent,
        judgement: JudgeResult,
        evidences: list[TravelEvidence],
        raw_docs: list[RawDocument],
        collection_summary: CollectionSummary | None = None,
        collection_errors: list[CollectionError] | None = None,
        llm_mode: str = "fallback",
    ) -> str:
        """Build the final Chinese Markdown report."""

        if judgement.final_judgement == "资料不足，暂不能判断":
            return self._write_insufficient(
                intent,
                judgement,
                evidences,
                raw_docs,
                collection_summary=collection_summary,
                collection_errors=collection_errors or [],
                llm_mode=llm_mode,
            )

        positive = [e for e in evidences if e.sentiment == "positive"]
        negative = [e for e in evidences if e.sentiment == "negative"]
        neutral = [e for e in evidences if e.sentiment == "neutral"]

        lines = [
            f"# {intent.destination} 适不适合去？",
            "",
            "## 1. 结论",
            "",
            f"结论：{judgement.final_judgement}  ",
            f"适配分：{judgement.score} / 100  ",
            f"资料置信度：{judgement.confidence}",
            "",
            "一句话判断：",
            "",
            f"> 根据本次收集到的资料，{self._one_line(intent, judgement)}",
            "",
            "资料模式："
            f"{collection_summary.mode if collection_summary else 'unknown'}；"
            f"LLM 模式：{llm_mode}。"
            + (" 未配置 OPENAI_API_KEY，证据抽取使用规则 fallback。" if llm_mode == "fallback" else ""),
            "",
            "## 2. 为什么这么判断？",
            "",
            "### 正面依据",
            "",
            *_evidence_bullets(positive[:5]),
            "",
            "### 负面依据",
            "",
            *_evidence_bullets(negative[:5]),
            "",
            "## 3. 适合什么人？",
            "",
            *_list_or_empty(judgement.suitable_for),
            "",
            "## 4. 不适合什么人？",
            "",
            *_list_or_empty(judgement.not_suitable_for),
            "",
            "## 5. 推荐玩法",
            "",
            *self._route_lines(intent, evidences),
            "",
            "## 6. 必去 / 可去 / 谨慎去",
            "",
            "### 必去",
            "",
            "| 地点 | 推荐理由 | 资料依据 |",
            "|---|---|---|",
            *self._place_rows(positive, "positive"),
            "",
            "### 可去可不去",
            "",
            "| 地点 | 原因 | 适合情况 |",
            "|---|---|---|",
            *self._place_rows(neutral, "neutral"),
            "",
            "### 谨慎去 / 不推荐",
            "",
            "| 地点 | 风险 | 替代方案 |",
            "|---|---|---|",
            *self._place_rows(negative, "negative"),
            "",
            "## 7. 住宿和交通建议",
            "",
            *self._topic_lines(evidences, topics={"住宿", "交通"}),
            "",
            "## 8. 避坑提醒",
            "",
            *self._warning_lines(negative),
            "",
            "## 9. 预算判断",
            "",
            *self._topic_lines(evidences, topics={"预算"}),
            "",
            "## 10. 资料来源摘要",
            "",
            *self._source_summary(raw_docs),
            "",
            "## 11. 不确定信息",
            "",
            *self._uncertainties(judgement, evidences),
            "",
            "## 12. 采集错误",
            "",
            *self._collection_error_lines(collection_errors or []),
        ]
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _write_insufficient(
        intent: UserIntent,
        judgement: JudgeResult,
        evidences: list[TravelEvidence],
        raw_docs: list[RawDocument],
        collection_summary: CollectionSummary | None = None,
        collection_errors: list[CollectionError] | None = None,
        llm_mode: str = "fallback",
    ) -> str:
        return "\n".join(
            [
                f"# {intent.destination} 适不适合去？",
                "",
                "## 1. 结论",
                "",
                "结论：资料不足，暂不能判断  ",
                f"适配分：{judgement.score} / 100  ",
                f"资料置信度：{judgement.confidence}",
                "",
                "根据本次收集到的资料，当前资料不足，暂不能判断。系统不会用模型常识替代资料结论。",
                "",
                "资料模式："
                f"{collection_summary.mode if collection_summary else 'unknown'}；"
                f"LLM 模式：{llm_mode}。"
                + (" 未配置 OPENAI_API_KEY，证据抽取使用规则 fallback。" if llm_mode == "fallback" else ""),
                "",
                "## 10. 资料来源摘要",
                "",
                *ReportWriter._source_summary(raw_docs),
                "",
                "## 11. 不确定信息",
                "",
                "- 缺少足够的高质量原始资料和结构化 evidence。",
                f"- 当前仅整理 raw documents {len(raw_docs)} 条，evidence {len(evidences)} 条。",
                "",
                "## 12. 采集错误",
                "",
                *ReportWriter._collection_error_lines(collection_errors or []),
            ]
        )

    @staticmethod
    def _one_line(intent: UserIntent, judgement: JudgeResult) -> str:
        if judgement.final_judgement == "适合":
            return f"{intent.destination}与当前偏好匹配度较高，但仍建议按 evidence 控制行程强度。"
        if judgement.final_judgement == "不适合":
            return f"{intent.destination}对当前用户画像存在较强风险，不建议按原计划出行。"
        return f"{intent.destination}可以去，但需要避开高风险场景并降低白天户外强度。"

    @staticmethod
    def _route_lines(intent: UserIntent, evidences: list[TravelEvidence]) -> list[str]:
        days = intent.days or 3
        route_source = "; ".join(
            e.claim for e in evidences if e.topic in {"游玩天数", "景点推荐", "夜景", "美食"}
        )[:300]
        if not route_source:
            return ["- 资料不足，不能强行生成每日路线。"]
        lines: list[str] = []
        default_slots = [
            ("白天安排室内或低强度点位", "下午选择地铁可达的景点", "晚上安排夜景或美食"),
            ("上午选择特色打卡点", "下午保留休息或商圈时间", "晚上安排美食"),
            ("上午补充博物馆或轻松点位", "下午按体力返程前取舍", "晚上不强行加点"),
        ]
        for day in range(1, days + 1):
            slots = default_slots[(day - 1) % len(default_slots)]
            lines.extend(
                [
                    f"### Day {day}",
                    "",
                    f"上午：{slots[0]}。资料依据：{route_source}",
                    f"下午：{slots[1]}。资料依据：{route_source}",
                    f"晚上：{slots[2]}。资料依据：{route_source}",
                    "",
                ]
            )
        return lines

    @staticmethod
    def _place_rows(evidences: list[TravelEvidence], mode: str) -> list[str]:
        rows: list[str] = []
        used: set[str] = set()
        for evidence in evidences:
            if not evidence.place_name or evidence.place_name in used:
                continue
            used.add(evidence.place_name)
            if mode == "positive":
                rows.append(f"| {evidence.place_name} | {evidence.claim} | {evidence.reason or evidence.claim} |")
            elif mode == "neutral":
                suitable = "、".join(evidence.suitable_for) or "资料未明确限定"
                rows.append(f"| {evidence.place_name} | {evidence.claim} | {suitable} |")
            else:
                replacement = "优先选择室内、地铁可达或夜间低强度安排"
                rows.append(f"| {evidence.place_name} | {evidence.warning or evidence.claim} | {replacement} |")
        return rows or ["| 资料不足 | 无法强行下结论 | 无 |"]

    @staticmethod
    def _topic_lines(evidences: list[TravelEvidence], topics: set[str]) -> list[str]:
        selected = [e for e in evidences if e.topic in topics or any(topic in e.topic for topic in topics)]
        if not selected:
            return ["- 资料不足，不能强行判断。"]
        return [f"- 根据本次收集到的资料，{e.claim}（依据：{e.reason or e.source_doc_id}）" for e in selected[:5]]

    @staticmethod
    def _warning_lines(evidences: list[TravelEvidence]) -> list[str]:
        if not evidences:
            return ["- 本次资料未抽取到明确避坑提醒。"]
        return [f"- {e.warning or e.claim}（来源 doc_id：{e.source_doc_id}）" for e in evidences[:6]]

    @staticmethod
    def _source_summary(raw_docs: list[RawDocument]) -> list[str]:
        counts = Counter(doc.platform for doc in raw_docs)
        if not raw_docs:
            return ["本次共整理：0 条资料。"]
        lines = ["本次共整理："]
        for platform, count in sorted(counts.items()):
            lines.append(f"- {platform} 资料：{count} 条")
        times = [doc.publish_time for doc in raw_docs if doc.publish_time]
        if times:
            lines.append("")
            lines.append(f"资料时间范围：{min(times)} 至 {max(times)}  ")
        lines.append("资料一致性：中")
        return lines

    @staticmethod
    def _uncertainties(judgement: JudgeResult, evidences: list[TravelEvidence]) -> list[str]:
        uncertainties = []
        if judgement.confidence != "高":
            uncertainties.append("- 资料置信度未达到高，需要更多平台和更新资料交叉验证。")
        if not any(e.topic == "预算" for e in evidences):
            uncertainties.append("- 预算信息不足，不能给出更细颗粒度花费拆分。")
        if not any("交通" in e.topic for e in evidences):
            uncertainties.append("- 交通信息不足，不能确认所有路线耗时。")
        return uncertainties or ["- 暂无额外不确定信息，但实际开放时间、天气和价格仍需出行前复核。"]

    @staticmethod
    def _collection_error_lines(errors: list[CollectionError]) -> list[str]:
        if not errors:
            return ["- 本次无采集错误。"]
        return [
            f"- platform={error.platform or 'unknown'} query={error.query or 'unknown'} error={error.error}"
            for error in errors[:12]
        ]


def _evidence_bullets(evidences: list[TravelEvidence]) -> list[str]:
    if not evidences:
        return ["- 资料不足，未抽取到可支撑的 evidence。"]
    return [
        f"- 根据本次收集到的资料，{evidence.claim}（来源 doc_id：{evidence.source_doc_id}）。"
        for evidence in evidences
    ]


def _list_or_empty(values: list[str]) -> list[str]:
    if not values:
        return ["- 资料不足，不能强行判断。"]
    return [f"- {value}" for value in values]
