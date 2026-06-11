from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.schemas import (
    CollectionError,
    CollectionSummary,
    EvidenceSummary,
    JudgeResult,
    RawDocument,
    StoredReport,
    TravelEvidence,
    UserIntent,
)


class SQLiteStore:
    """SQLite persistence for raw docs, evidence, and generated reports."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Create database tables if they do not exist."""

        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS raw_documents (
                    request_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    query TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    url TEXT,
                    author TEXT,
                    publish_time TEXT,
                    like_count INTEGER,
                    collect_count INTEGER,
                    comment_count INTEGER,
                    raw_json TEXT NOT NULL,
                    PRIMARY KEY (request_id, doc_id)
                );

                CREATE TABLE IF NOT EXISTS evidences (
                    request_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    source_doc_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    place_name TEXT,
                    data_json TEXT NOT NULL,
                    PRIMARY KEY (request_id, evidence_id)
                );

                CREATE TABLE IF NOT EXISTS reports (
                    request_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    user_query TEXT NOT NULL,
                    intent_json TEXT NOT NULL,
                    queries_json TEXT NOT NULL,
                    collection_summary_json TEXT,
                    collection_errors_json TEXT,
                    llm_mode TEXT NOT NULL DEFAULT 'fallback',
                    evidence_summary_json TEXT NOT NULL,
                    judgement_json TEXT NOT NULL,
                    report_md TEXT NOT NULL
                );
                """
            )
            self._ensure_report_columns(conn)

    def save_raw_documents(self, request_id: str, documents: list[RawDocument]) -> None:
        """Persist raw documents for a request."""

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO raw_documents (
                    request_id, doc_id, platform, query, title, content, url, author,
                    publish_time, like_count, collect_count, comment_count, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        request_id,
                        doc.id,
                        doc.platform,
                        doc.query,
                        doc.title,
                        doc.content,
                        doc.url,
                        doc.author,
                        doc.publish_time,
                        doc.like_count,
                        doc.collect_count,
                        doc.comment_count,
                        json.dumps(doc.raw, ensure_ascii=False),
                    )
                    for doc in documents
                ],
            )

    def save_evidences(self, request_id: str, evidences: list[TravelEvidence]) -> None:
        """Persist structured evidence for a request."""

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO evidences (
                    request_id, evidence_id, source_doc_id, topic, sentiment, place_name, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        request_id,
                        f"{index:04d}",
                        evidence.source_doc_id,
                        evidence.topic,
                        evidence.sentiment,
                        evidence.place_name,
                        evidence.model_dump_json(),
                    )
                    for index, evidence in enumerate(evidences)
                ],
            )

    def save_report(
        self,
        request_id: str,
        user_query: str,
        intent: UserIntent,
        queries: list[str],
        collection_summary: CollectionSummary,
        collection_errors: list[CollectionError],
        llm_mode: str,
        evidence_summary: EvidenceSummary,
        judgement: JudgeResult,
        report: str,
    ) -> None:
        """Persist final report and its structured metadata."""

        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reports (
                    request_id, created_at, user_query, intent_json, queries_json,
                    collection_summary_json, collection_errors_json, llm_mode,
                    evidence_summary_json, judgement_json, report_md
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    now,
                    user_query,
                    intent.model_dump_json(),
                    json.dumps(queries, ensure_ascii=False),
                    collection_summary.model_dump_json(),
                    json.dumps([error.model_dump() for error in collection_errors], ensure_ascii=False),
                    llm_mode,
                    evidence_summary.model_dump_json(),
                    judgement.model_dump_json(),
                    report,
                ),
            )

    def get_report(self, request_id: str) -> StoredReport | None:
        """Return one stored report, or None."""

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT request_id, created_at, intent_json, queries_json,
                       collection_summary_json, collection_errors_json, llm_mode,
                       evidence_summary_json, judgement_json, report_md
                FROM reports
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        return StoredReport(
            request_id=row["request_id"],
            created_at=row["created_at"],
            intent=UserIntent.model_validate_json(row["intent_json"]),
            queries=json.loads(row["queries_json"]),
            collection_summary=(
                CollectionSummary.model_validate_json(row["collection_summary_json"])
                if row["collection_summary_json"]
                else None
            ),
            collection_errors=[
                CollectionError.model_validate(item)
                for item in json.loads(row["collection_errors_json"] or "[]")
            ],
            llm_mode=row["llm_mode"] or "fallback",
            evidence_summary=EvidenceSummary.model_validate_json(row["evidence_summary_json"]),
            judgement=JudgeResult.model_validate_json(row["judgement_json"]),
            report=row["report_md"],
        )

    def get_evidences(self, request_id: str) -> list[TravelEvidence]:
        """Return stored evidence for a request."""

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT data_json
                FROM evidences
                WHERE request_id = ?
                ORDER BY evidence_id
                """,
                (request_id,),
            ).fetchall()
        return [TravelEvidence.model_validate_json(row["data_json"]) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _ensure_report_columns(conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(reports)").fetchall()}
        additions = {
            "collection_summary_json": "TEXT",
            "collection_errors_json": "TEXT",
            "llm_mode": "TEXT NOT NULL DEFAULT 'fallback'",
        }
        for column, ddl in additions.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE reports ADD COLUMN {column} {ddl}")
