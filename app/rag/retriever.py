from __future__ import annotations

from pathlib import Path

from app.rag.chunker import chunk_text
from app.rag.embeddings import DeterministicEmbedder
from app.rag.vector_store import LocalVectorStore, VectorRecord
from app.schemas import RawDocument, TravelEvidence


class RAGRetriever:
    """Index raw documents and structured evidence, then retrieve both."""

    def __init__(self, persist_dir: Path) -> None:
        self.embedder = DeterministicEmbedder()
        self.vector_store = LocalVectorStore(persist_dir)

    def index(
        self,
        request_id: str,
        raw_docs: list[RawDocument],
        evidences: list[TravelEvidence],
    ) -> None:
        """Index raw document chunks and evidence records for one request."""

        records: list[VectorRecord] = []
        for doc in raw_docs:
            for index, chunk in enumerate(chunk_text(doc.content)):
                text = f"{doc.title or ''}\n{chunk}"
                records.append(
                    VectorRecord(
                        id=f"{request_id}:raw:{doc.id}:{index}",
                        text=text,
                        embedding=self.embedder.embed(text),
                        metadata={
                            "request_id": request_id,
                            "kind": "raw_doc",
                            "doc_id": doc.id,
                            "platform": doc.platform,
                        },
                    )
                )
        for index, evidence in enumerate(evidences):
            text = " ".join(
                part
                for part in [
                    evidence.destination,
                    evidence.place_name or "",
                    evidence.topic,
                    evidence.claim,
                    evidence.reason or "",
                    evidence.warning or "",
                ]
                if part
            )
            records.append(
                VectorRecord(
                    id=f"{request_id}:evidence:{index}",
                    text=text,
                    embedding=self.embedder.embed(text),
                    metadata={
                        "request_id": request_id,
                        "kind": "evidence",
                        "source_doc_id": evidence.source_doc_id,
                        "sentiment": evidence.sentiment,
                    },
                )
            )
        self.vector_store.add(records)

    def retrieve(self, request_id: str, query: str, top_k: int = 5) -> dict[str, list[dict]]:
        """Retrieve raw-document chunks and structured evidence for a query."""

        embedding = self.embedder.embed(query)
        raw = self.vector_store.query(
            embedding,
            top_k=top_k,
            metadata_filter={"request_id": request_id, "kind": "raw_doc"},
        )
        evidences = self.vector_store.query(
            embedding,
            top_k=top_k,
            metadata_filter={"request_id": request_id, "kind": "evidence"},
        )
        return {
            "raw_docs": [{"text": item.text, "metadata": item.metadata} for item in raw],
            "evidences": [{"text": item.text, "metadata": item.metadata} for item in evidences],
        }

