import json
from dataclasses import asdict, dataclass
from typing import Any


SIGNAL_TAG_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Rates", ("interest rate", "interest rates", "rate hold", "rates", "holds rate", "keeps rate")),
    ("Inflation", ("inflation", "cpi", "consumer prices", "price growth")),
    ("Central Bank", ("federal reserve", "fed", "bank of england", "central bank", "boj", "ecb")),
    ("Oil", ("oil", "crude", "brent")),
    ("Energy", ("energy", "gas", "electricity", "fuel")),
    ("Currency", ("currency", "yen", "dollar", "euro", "sterling")),
    ("Jobs", ("jobs", "payroll", "payrolls", "unemployment", "labour market", "labor market")),
    ("Tariff", ("tariff", "tariffs")),
    ("Trade", ("trade", "exports", "imports", "trade deal")),
    ("AI", ("artificial intelligence", " ai ", "openai", "chatgpt", "model")),
    ("Chips", ("chip", "chips")),
    ("Semiconductor", ("semiconductor", "foundry", "fab")),
    ("Cloud", ("cloud",)),
    ("Data Center", ("data center", "data centres", "data center", "data centres")),
    ("Antitrust", ("antitrust", "competition watchdog", "monopoly case")),
    ("Earnings", ("earnings", "guidance", "quarterly results")),
    ("Supply Chain", ("supply chain", "logistics", "shipping route")),
    ("EV", ("electric vehicle", "electric vehicles", "ev", "battery")),
    ("Court", ("supreme court", "court", "judge", "lawsuit", "legal challenge")),
    ("Election", ("election", "vote", "votes", "campaign", "ballot")),
    ("Sanctions", ("sanction", "sanctions")),
    ("War", ("war", "military", "strike", "attack", "troops")),
    ("Ceasefire", ("ceasefire", "truce")),
    ("NATO", ("nato",)),
    ("Migration", ("migration", "migrant", "migrants", "border crossing")),
]
MAX_SIGNAL_TAGS = 5


def _normalized_signal_text(*parts: str) -> str:
    combined = " ".join(part or "" for part in parts).strip().lower()
    return f" {combined} "


def extract_signal_tags(headline: str, summary: str, topic: str, region: str) -> list[str]:
    text = _normalized_signal_text(headline, summary, topic, region)
    matched_tags: list[str] = []

    for label, phrases in SIGNAL_TAG_RULES:
        if any(f" {phrase.lower()} " in text for phrase in phrases):
            matched_tags.append(label)
        if len(matched_tags) >= MAX_SIGNAL_TAGS:
            break

    return matched_tags


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
    article_url: str | None
    source_list: list[str]
    signal_tags: list[str]
    is_top_story: bool
    is_watchlist: bool

    @classmethod
    def from_db_row(cls, row: Any) -> "CardRecord":
        signal_tags = extract_signal_tags(
            row["headline"],
            row["summary"],
            row["topic"],
            row["region"],
        )
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
            article_url=row["article_url"],
            source_list=json.loads(row["source_list_json"]),
            signal_tags=signal_tags,
            is_top_story=bool(row["is_top_story"]),
            is_watchlist=bool(row["is_watchlist"]),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CardRecord":
        signal_tags = list(payload.get("signal_tags", [])) or extract_signal_tags(
            payload["headline"],
            payload["summary"],
            payload["topic"],
            payload["region"],
        )
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
            article_url=payload.get("article_url"),
            source_list=list(payload.get("source_list", [])),
            signal_tags=signal_tags,
            is_top_story=bool(payload.get("is_top_story", False)),
            is_watchlist=bool(payload.get("is_watchlist", False)),
        )

    def to_api_dict(self) -> dict[str, Any]:
        return asdict(self)
