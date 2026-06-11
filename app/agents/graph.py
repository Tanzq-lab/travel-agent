from __future__ import annotations

from typing import Any, TypedDict
from uuid import uuid4
from collections import Counter

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - exercised only if dependency is absent
    END = START = None
    StateGraph = None

from app.agents.destination_judge import DestinationJudge
from app.agents.evidence_extractor import EvidenceExtractor
from app.agents.query_planner import QueryPlanner, UserIntentParser
from app.agents.report_writer import ReportWriter
from app.collectors.media_crawler_adapter import MediaCrawlerAdapter
from app.collectors.media_crawler_adapter import MediaCrawlerRunConfig
from app.collectors.mock_collector import MockCollector
from app.config import Settings, get_settings
from app.llm.client import LLMClient
from app.rag.retriever import RAGRetriever
from app.schemas import (
    CollectionError,
    CollectionSummary,
    JudgeResult,
    QueryPlan,
    RawDocument,
    TravelEvidence,
    TravelPlanRequest,
    TravelPlanResponse,
    UserIntent,
)
from app.storage.sqlite_store import SQLiteStore
from app.utils.dedupe import dedupe_documents
from app.utils.evidence_validator import supported_evidences
from app.utils.text_cleaner import clean_documents


class TravelState(TypedDict, total=False):
    request_id: str
    request: TravelPlanRequest
    intent: UserIntent
    query_plan: QueryPlan
    raw_docs: list[RawDocument]
    clean_docs: list[RawDocument]
    evidences: list[TravelEvidence]
    collection_errors: list[CollectionError]
    collection_summary: CollectionSummary
    llm_mode: str
    retrieved: dict[str, list[dict[str, Any]]]
    judgement: JudgeResult
    report: str


class TravelWorkflow:
    """Stateful workflow nodes and dependencies for one agent run."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm_client = LLMClient.from_settings(settings)
        self.intent_parser = UserIntentParser()
        self.query_planner = QueryPlanner(max_queries=settings.max_queries)
        self.evidence_extractor = EvidenceExtractor(llm_client=self.llm_client)
        self.judge = DestinationJudge()
        self.report_writer = ReportWriter()
        self.store = SQLiteStore(settings.database_path)
        self.retriever = RAGRetriever(settings.vector_store_path)
        self.store.initialize()

    def parse_intent(self, state: TravelState) -> TravelState:
        request = state["request"]
        return {"intent": self.intent_parser.parse(request.user_query)}

    def plan_queries(self, state: TravelState) -> TravelState:
        return {"query_plan": self.query_planner.plan(state["intent"])}

    def collect(self, state: TravelState) -> TravelState:
        request = state["request"]
        collector = self._collector(request, state["request_id"])
        documents: list[RawDocument] = []
        for query in state["query_plan"].queries:
            documents.extend(collector.search(query, request.collect_limit_per_query))
        errors = getattr(collector, "errors", [])
        return {"raw_docs": documents, "collection_errors": errors}

    def clean(self, state: TravelState) -> TravelState:
        cleaned = clean_documents(state.get("raw_docs", []), self.settings.min_document_length)
        return {"clean_docs": dedupe_documents(cleaned)}

    def extract_evidence(self, state: TravelState) -> TravelState:
        evidences = self.evidence_extractor.extract_from_documents(
            state["intent"].destination,
            state.get("clean_docs", []),
        )
        return {"evidences": supported_evidences(evidences)}

    def index_and_retrieve(self, state: TravelState) -> TravelState:
        request_id = state["request_id"]
        docs = state.get("clean_docs", [])
        evidences = state.get("evidences", [])
        self.store.save_raw_documents(request_id, docs)
        self.store.save_evidences(request_id, evidences)
        self.retriever.index(request_id, docs, evidences)
        retrieved = self.retriever.retrieve(request_id, state["request"].user_query, top_k=6)
        return {"retrieved": retrieved, "collection_summary": self._collection_summary(state, docs)}

    def judge_destination(self, state: TravelState) -> TravelState:
        judgement = self.judge.judge(
            state["intent"],
            state.get("evidences", []),
            total_docs=len(state.get("clean_docs", [])),
        )
        return {"judgement": judgement}

    def write_report(self, state: TravelState) -> TravelState:
        report = self.report_writer.write(
            state["intent"],
            state["judgement"],
            state.get("evidences", []),
            state.get("clean_docs", []),
            collection_summary=state.get("collection_summary"),
            collection_errors=state.get("collection_errors", []),
            llm_mode=self.llm_client.mode,
        )
        self.store.save_report(
            state["request_id"],
            state["request"].user_query,
            state["intent"],
            state["query_plan"].queries,
            state["collection_summary"],
            state.get("collection_errors", []),
            self.llm_client.mode,
            state["judgement"].evidence_summary,
            state["judgement"],
            report,
        )
        return {"report": report}

    def _collector(self, request: TravelPlanRequest, request_id: str):
        mode = self._collection_mode(request)
        if mode == "mock":
            return MockCollector(platforms=request.platforms)
        return MediaCrawlerAdapter(
            config=MediaCrawlerRunConfig(
                root=self.settings.media_crawler_root,
                runner=self.settings.media_crawler_runner,
                login_type=self.settings.media_crawler_login_type,
                save_option=self.settings.media_crawler_save_option,
                headless=self.settings.media_crawler_headless,
                runs_path=self.settings.media_crawler_runs_path,
                sleep_seconds=self.settings.media_crawler_sleep_seconds,
                rate_limit_per_minute=self.settings.media_crawler_rate_limit_per_minute,
                timeout_seconds=self.settings.media_crawler_timeout_seconds,
            ),
            platforms=request.platforms,
            request_id=request_id,
        )

    def _collection_mode(self, request: TravelPlanRequest) -> str:
        if request.use_mock is True:
            return "mock"
        if request.use_mock is False:
            return "media_crawler"
        if request.collection_mode == "auto":
            return "media_crawler" if self.settings.media_crawler_root.exists() else "mock"
        return request.collection_mode

    def _collection_summary(self, state: TravelState, documents: list[RawDocument]) -> CollectionSummary:
        request = state["request"]
        mode = self._collection_mode(request)
        counts = Counter(document.platform for document in documents)
        run_path = None
        if mode == "media_crawler":
            run_path = str((self.settings.media_crawler_runs_path / state["request_id"]).resolve())
        return CollectionSummary(
            mode=mode,
            total_docs=len(documents),
            platforms=dict(counts),
            run_path=run_path,
            used_mock=mode == "mock",
        )


def run_travel_agent(
    request: TravelPlanRequest,
    *,
    settings: Settings | None = None,
) -> TravelPlanResponse:
    """Run the LangGraph workflow and return an API response model."""

    runtime_settings = settings or get_settings()
    workflow = TravelWorkflow(runtime_settings)
    request_id = str(uuid4())
    initial_state: TravelState = {"request_id": request_id, "request": request}

    if StateGraph is None:
        final_state = _run_sequential(workflow, initial_state)
    else:
        graph = _build_graph(workflow)
        final_state = graph.invoke(initial_state)

    return TravelPlanResponse(
        request_id=request_id,
        intent=final_state["intent"],
        queries=final_state["query_plan"].queries,
        collection_summary=final_state["collection_summary"],
        collection_errors=final_state.get("collection_errors", []),
        llm_mode=workflow.llm_client.mode,
        evidence_summary=final_state["judgement"].evidence_summary,
        judgement=final_state["judgement"],
        report=final_state["report"],
    )


def _build_graph(workflow: TravelWorkflow):
    graph = StateGraph(TravelState)
    graph.add_node("parse_intent", workflow.parse_intent)
    graph.add_node("plan_queries", workflow.plan_queries)
    graph.add_node("collect", workflow.collect)
    graph.add_node("clean", workflow.clean)
    graph.add_node("extract_evidence", workflow.extract_evidence)
    graph.add_node("index_and_retrieve", workflow.index_and_retrieve)
    graph.add_node("judge_destination", workflow.judge_destination)
    graph.add_node("write_report", workflow.write_report)

    graph.add_edge(START, "parse_intent")
    graph.add_edge("parse_intent", "plan_queries")
    graph.add_edge("plan_queries", "collect")
    graph.add_edge("collect", "clean")
    graph.add_edge("clean", "extract_evidence")
    graph.add_edge("extract_evidence", "index_and_retrieve")
    graph.add_edge("index_and_retrieve", "judge_destination")
    graph.add_edge("judge_destination", "write_report")
    graph.add_edge("write_report", END)
    return graph.compile()


def _run_sequential(workflow: TravelWorkflow, state: TravelState) -> TravelState:
    """Fallback runner used only when LangGraph is not installed."""

    for node in [
        workflow.parse_intent,
        workflow.plan_queries,
        workflow.collect,
        workflow.clean,
        workflow.extract_evidence,
        workflow.index_and_retrieve,
        workflow.judge_destination,
        workflow.write_report,
    ]:
        state.update(node(state))
    return state
