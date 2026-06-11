from __future__ import annotations

import re

from app.llm.client import LLMClient
from app.schemas import RawDocument, TravelEvidence


class EvidenceExtractor:
    """Extract structured travel evidence from raw travel documents."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def extract_from_documents(
        self,
        destination: str,
        documents: list[RawDocument],
    ) -> list[TravelEvidence]:
        """Extract and validate evidence from all documents."""

        evidences: list[TravelEvidence] = []
        for document in documents:
            evidences.extend(self.extract(destination, document))
        return evidences

    def extract(self, destination: str, document: RawDocument) -> list[TravelEvidence]:
        """Extract evidence from one document, using mock annotations or simple rules."""

        mock_evidences = document.raw.get("evidences")
        if isinstance(mock_evidences, list) and mock_evidences:
            return [
                TravelEvidence(
                    destination=destination,
                    source_doc_id=document.id,
                    source_url=document.url,
                    place_name=item.get("place_name"),
                    place_type=item.get("place_type"),
                    topic=item["topic"],
                    sentiment=item["sentiment"],
                    claim=item["claim"],
                    reason=item.get("reason"),
                    suitable_for=item.get("suitable_for", []),
                    not_suitable_for=item.get("not_suitable_for", []),
                    mentioned_season=item.get("mentioned_season"),
                    mentioned_budget=item.get("mentioned_budget"),
                    mentioned_duration=item.get("mentioned_duration"),
                    transportation_info=item.get("transportation_info"),
                    warning=item.get("warning"),
                    confidence=item.get("confidence", 0.7),
                )
                for item in mock_evidences
            ]

        if self.llm_client and self.llm_client.available:
            try:
                return self._llm_extract(destination, document)
            except Exception:
                return self._heuristic_extract(destination, document)

        return self._heuristic_extract(destination, document)

    def _llm_extract(self, destination: str, document: RawDocument) -> list[TravelEvidence]:
        payload = self.llm_client.complete_json(
            system_prompt=(
                "你是旅游资料证据抽取 Agent。只能根据原文抽取，不能脑补。"
                "输出 JSON object，字段 evidences 是数组。每条 evidence 必须保留 source_doc_id。"
            ),
            user_payload={
                "destination": destination,
                "source_doc_id": document.id,
                "source_url": document.url,
                "title": document.title,
                "content": document.content,
                "schema": {
                    "topic": "string",
                    "sentiment": "positive|negative|neutral",
                    "claim": "string",
                    "reason": "string|null",
                    "suitable_for": ["string"],
                    "not_suitable_for": ["string"],
                    "mentioned_season": "string|null",
                    "mentioned_budget": "string|null",
                    "mentioned_duration": "string|null",
                    "transportation_info": "string|null",
                    "warning": "string|null",
                },
            },
        )
        raw_items = payload.get("evidences", []) if isinstance(payload, dict) else []
        evidences: list[TravelEvidence] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            evidences.append(
                TravelEvidence(
                    destination=destination,
                    place_name=item.get("place_name"),
                    place_type=item.get("place_type"),
                    topic=item.get("topic") or "资料观点",
                    sentiment=item.get("sentiment") if item.get("sentiment") in {"positive", "negative", "neutral"} else "neutral",
                    claim=item.get("claim") or document.content[:80],
                    reason=item.get("reason"),
                    suitable_for=item.get("suitable_for") or [],
                    not_suitable_for=item.get("not_suitable_for") or [],
                    mentioned_season=item.get("mentioned_season"),
                    mentioned_budget=item.get("mentioned_budget"),
                    mentioned_duration=item.get("mentioned_duration"),
                    transportation_info=item.get("transportation_info"),
                    warning=item.get("warning"),
                    source_doc_id=document.id,
                    source_url=document.url,
                    confidence=float(item.get("confidence") or 0.72),
                )
            )
        return evidences

    @staticmethod
    def _heuristic_extract(destination: str, document: RawDocument) -> list[TravelEvidence]:
        sentences = [part.strip() for part in re.split(r"[。！？!?]", document.content) if part.strip()]
        evidences: list[TravelEvidence] = []
        for sentence in sentences:
            sentiment = _sentiment(sentence)
            if sentiment is None:
                continue
            topic = _topic(sentence)
            evidences.append(
                TravelEvidence(
                    destination=destination,
                    place_name=_place_name(sentence),
                    place_type=None,
                    topic=topic,
                    sentiment=sentiment,
                    claim=sentence[:80],
                    reason=sentence[:120],
                    suitable_for=_suitable_for(sentence),
                    not_suitable_for=_not_suitable_for(sentence),
                    mentioned_season=_season(sentence),
                    mentioned_budget=_budget(sentence),
                    mentioned_duration=_duration(sentence),
                    transportation_info=sentence if "地铁" in sentence or "交通" in sentence else None,
                    warning=sentence if sentiment == "negative" else None,
                    source_doc_id=document.id,
                    source_url=document.url,
                    confidence=0.58,
                )
            )
        return evidences


def _sentiment(sentence: str) -> str | None:
    if any(word in sentence for word in ("不建议", "人多", "排队", "很热", "商业化", "坑", "太累", "远")):
        return "negative"
    if any(word in sentence for word in ("建议", "适合", "方便", "好看", "推荐", "够用", "舒服")):
        return "positive"
    if any(word in sentence for word in ("可以", "一般", "取舍")):
        return "neutral"
    return None


def _topic(sentence: str) -> str:
    if any(word in sentence for word in ("热", "天气", "季节", "月")):
        return "季节"
    if any(word in sentence for word in ("住宿", "酒店", "区域")):
        return "住宿"
    if any(word in sentence for word in ("地铁", "交通", "轻轨", "打车")):
        return "交通"
    if any(word in sentence for word in ("预算", "花费", "价格")):
        return "预算"
    if any(word in sentence for word in ("吃", "美食", "火锅")):
        return "美食"
    return "景点/体验"


def _place_name(sentence: str) -> str | None:
    places = ("洪崖洞", "三峡博物馆", "李子坝", "观音桥", "解放碑", "沙坪坝", "长江索道", "磁器口", "南滨路", "江北嘴")
    for place in places:
        if place in sentence:
            return place
    return None


def _suitable_for(sentence: str) -> list[str]:
    result: list[str] = []
    if "爸妈" in sentence or "父母" in sentence or "老人" in sentence:
        result.append("带父母")
    if "美食" in sentence or "吃" in sentence:
        result.append("美食")
    if "拍照" in sentence:
        result.append("拍照")
    if "轻松" in sentence:
        result.append("不喜欢太累")
    return result


def _not_suitable_for(sentence: str) -> list[str]:
    result: list[str] = []
    if "热" in sentence:
        result.append("怕热")
    if "老人" in sentence or "爸妈" in sentence or "父母" in sentence:
        result.append("带父母")
    if "人多" in sentence or "排队" in sentence:
        result.append("怕挤")
    return result


def _season(sentence: str) -> str | None:
    match = re.search(r"(\d{1,2})月", sentence)
    return match.group(0) if match else None


def _budget(sentence: str) -> str | None:
    if "中等预算" in sentence:
        return "中等预算"
    if "预算有限" in sentence:
        return "预算有限"
    if "价格高" in sentence:
        return "偏高"
    return None


def _duration(sentence: str) -> str | None:
    match = re.search(r"(\d{1,2}|[一二两三四五六七八九十])天", sentence)
    return match.group(0) if match else None
