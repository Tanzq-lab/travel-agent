from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


Sentiment = Literal["positive", "negative", "neutral"]
JudgementLabel = Literal["适合", "不适合", "条件适合", "资料不足，暂不能判断"]
CollectionMode = Literal["media_crawler", "mock", "auto"]
LLMMode = Literal["openai-compatible", "fallback"]


class RawDocument(BaseModel):
    id: str
    platform: str
    query: str
    title: str | None = None
    content: str
    url: str | None = None
    author: str | None = None
    publish_time: str | None = None
    like_count: int | None = None
    collect_count: int | None = None
    comment_count: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class TravelEvidence(BaseModel):
    destination: str
    place_name: str | None = None
    place_type: str | None = None
    topic: str
    sentiment: Sentiment
    claim: str
    reason: str | None = None
    suitable_for: list[str] = Field(default_factory=list)
    not_suitable_for: list[str] = Field(default_factory=list)
    mentioned_season: str | None = None
    mentioned_budget: str | None = None
    mentioned_duration: str | None = None
    transportation_info: str | None = None
    warning: str | None = None
    source_doc_id: str
    source_url: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class UserIntent(BaseModel):
    destination: str
    days: int | None = None
    budget: int | None = None
    budget_level: str | None = None
    companions: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    travel_month: int | None = Field(default=None, ge=1, le=12)


class QueryPlan(BaseModel):
    destination: str
    queries: list[str]

    @field_validator("queries")
    @classmethod
    def queries_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("queries must not be empty")
        return value


class EvidenceSummary(BaseModel):
    total_docs: int = 0
    total_evidences: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0


class CollectionError(BaseModel):
    platform: str | None = None
    query: str | None = None
    error: str


class CollectionSummary(BaseModel):
    mode: CollectionMode
    total_docs: int = 0
    platforms: dict[str, int] = Field(default_factory=dict)
    run_path: str | None = None
    used_mock: bool = False


class JudgeResult(BaseModel):
    final_judgement: JudgementLabel
    score: int = Field(ge=0, le=100)
    suitable_reasons: list[str] = Field(default_factory=list)
    risk_reasons: list[str] = Field(default_factory=list)
    suitable_for: list[str] = Field(default_factory=list)
    not_suitable_for: list[str] = Field(default_factory=list)
    confidence: Literal["高", "中", "低"]
    evidence_summary: EvidenceSummary


class TravelPlanRequest(BaseModel):
    user_query: str = Field(min_length=1)
    platforms: list[str] = Field(default_factory=lambda: ["xhs", "zhihu", "bilibili", "weibo", "tieba"])
    collect_limit_per_query: int = Field(default=5, ge=1, le=50)
    use_mock: bool | None = None
    collection_mode: CollectionMode = "media_crawler"


class TravelPlanResponse(BaseModel):
    request_id: str
    intent: UserIntent
    queries: list[str]
    collection_summary: CollectionSummary
    collection_errors: list[CollectionError] = Field(default_factory=list)
    llm_mode: LLMMode
    evidence_summary: EvidenceSummary
    judgement: JudgeResult
    report: str


class StoredReport(BaseModel):
    request_id: str
    intent: UserIntent
    queries: list[str]
    collection_summary: CollectionSummary | None = None
    collection_errors: list[CollectionError] = Field(default_factory=list)
    llm_mode: LLMMode = "fallback"
    evidence_summary: EvidenceSummary
    judgement: JudgeResult
    report: str
    created_at: str
