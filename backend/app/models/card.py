import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CardRecord:
    id: int | None
    event_id: str
    headline: str
    summary: str
    why_it_matters: str
    region: str
    topic: str
    status: str
    importance_score: float
    published_at: str
    updated_at: str
    source_list: list[str]
    is_top_story: bool
    is_watchlist: bool

    @classmethod
    def from_db_row(cls, row: Any) -> "CardRecord":
        return cls(
            id=row["id"],
            event_id=row["event_id"],
            headline=row["headline"],
            summary=row["summary"],
            why_it_matters=row["why_it_matters"],
            region=row["region"],
            topic=row["topic"],
            status=row["status"],
            importance_score=float(row["importance_score"]),
            published_at=row["published_at"],
            updated_at=row["updated_at"],
            source_list=json.loads(row["source_list_json"]),
            is_top_story=bool(row["is_top_story"]),
            is_watchlist=bool(row["is_watchlist"]),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CardRecord":
        return cls(
            id=payload.get("id"),
            event_id=payload["event_id"],
            headline=payload["headline"],
            summary=payload["summary"],
            why_it_matters=payload["why_it_matters"],
            region=payload["region"],
            topic=payload["topic"],
            status=payload["status"],
            importance_score=float(payload["importance_score"]),
            published_at=payload["published_at"],
            updated_at=payload["updated_at"],
            source_list=list(payload.get("source_list", [])),
            is_top_story=bool(payload.get("is_top_story", False)),
            is_watchlist=bool(payload.get("is_watchlist", False)),
        )

    def to_api_dict(self) -> dict[str, Any]:
        return asdict(self)

