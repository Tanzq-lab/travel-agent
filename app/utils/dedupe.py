from __future__ import annotations

from hashlib import sha1

from app.schemas import RawDocument


def document_fingerprint(document: RawDocument) -> str:
    """Build a stable fingerprint from normalized title and content."""

    normalized = "".join(f"{document.title or ''}{document.content}".lower().split())
    return sha1(normalized.encode("utf-8")).hexdigest()


def dedupe_documents(documents: list[RawDocument]) -> list[RawDocument]:
    """Remove duplicate documents by normalized content fingerprint."""

    seen: set[str] = set()
    unique: list[RawDocument] = []
    for document in documents:
        fingerprint = document_fingerprint(document)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(document)
    return unique

