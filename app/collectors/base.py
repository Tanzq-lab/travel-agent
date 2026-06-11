from abc import ABC, abstractmethod

from app.schemas import RawDocument


class SourceCollector(ABC):
    """Interface for swappable public-source collectors."""

    @abstractmethod
    def search(self, query: str, limit: int) -> list[RawDocument]:
        """Search public content and normalize results into RawDocument objects."""

