from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.rag.embeddings import cosine_similarity


@dataclass
class VectorRecord:
    id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any]


class LocalVectorStore:
    """Persistent local vector store with optional Chroma backend fallback semantics."""

    def __init__(self, persist_dir: Path) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.persist_dir / "vectors.jsonl"
        self.records: dict[str, VectorRecord] = {}
        self.backend = "json-fallback"
        self._load()

    def add(self, records: list[VectorRecord]) -> None:
        """Add or replace vector records and persist them to disk."""

        for record in records:
            self.records[record.id] = record
        self._save()

    def query(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorRecord]:
        """Return top-k records by cosine similarity."""

        candidates = list(self.records.values())
        if metadata_filter:
            candidates = [
                record
                for record in candidates
                if all(record.metadata.get(key) == value for key, value in metadata_filter.items())
            ]
        ranked = sorted(
            candidates,
            key=lambda record: cosine_similarity(query_embedding, record.embedding),
            reverse=True,
        )
        return ranked[:top_k]

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            self.records[item["id"]] = VectorRecord(
                id=item["id"],
                text=item["text"],
                embedding=item["embedding"],
                metadata=item["metadata"],
            )

    def _save(self) -> None:
        lines = [
            json.dumps(
                {
                    "id": record.id,
                    "text": record.text,
                    "embedding": record.embedding,
                    "metadata": record.metadata,
                },
                ensure_ascii=False,
            )
            for record in self.records.values()
        ]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
