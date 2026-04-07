"""Base contracts for source connectors used by the ingest pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class RawArticleItem:
    source: str
    feed_name: str
    title_raw: str
    url: str
    published_at_raw: str
    excerpt_raw: str
    fetched_at: str


class BaseSource(ABC):
    name = "base"

    @abstractmethod
    def fetch_items(self) -> list[RawArticleItem]:
        """Return raw feed items ready to be persisted."""
