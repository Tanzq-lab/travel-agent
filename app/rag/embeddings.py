from __future__ import annotations

from hashlib import blake2b
from math import sqrt


class DeterministicEmbedder:
    """Small deterministic hash embedder for offline demo retrieval."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        """Embed text into a stable normalized vector without external services."""

        vector = [0.0] * self.dimensions
        tokens = _tokens(text)
        for token in tokens:
            digest = blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Return cosine similarity for normalized vectors."""

    return sum(a * b for a, b in zip(left, right))


def _tokens(text: str) -> list[str]:
    compact = "".join(text.lower().split())
    if not compact:
        return []
    return [compact[index : index + 2] for index in range(max(len(compact) - 1, 1))]

