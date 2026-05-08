import json
from dataclasses import asdict, dataclass
import re
from typing import Any


SIGNAL_TAG_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Surrogacy", ("surrogacy", "surrogate", "surrogate mother", "surrogacy provider")),
    ("Wildlife", ("bear", "bear attack", "animal attack", "wildlife")),
    ("Public Safety", ("public safety", "safety", "fatal accident", "dead", "killed", "injured", "missing", "hiker", "mountain", "outdoor")),
    ("Health", ("health", "public health", "world health organization")),
    ("Virus", ("virus", "hantavirus", "infection", "infected", "pandemic", "epidemic")),
    ("WHO", ("world health organization",)),
    ("Public Health", ("public health", "health authority")),
    ("Outbreak", ("outbreak", "disease outbreak")),
    ("Central Bank", ("federal reserve", "fed", "bank of england", "central bank", "boj", "ecb")),
    ("Rates", ("interest rate", "interest rates", "rate hold", "rate cut", "rate hike", "rates", "holds rate", "keeps rate")),
    ("Bonds", ("bond", "bonds", "treasury", "treasuries")),
    ("Yields", ("yield", "yields")),
    ("Inflation", ("inflation", "cpi", "consumer prices", "price growth")),
    ("GDP", ("gdp", "gross domestic product", "economic growth", "growth")),
    ("Jobs", ("jobs", "payroll", "payrolls", "unemployment", "labour market", "labor market")),
    ("Housing", ("housing", "home prices", "house prices", "property market")),
    ("Mortgage", ("mortgage", "mortgages", "home loan", "home loans")),
    ("AI", ("artificial intelligence", "ai", "chatgpt", "model")),
    ("OpenAI", ("openai",)),
    ("Chips", ("chip", "chips")),
    ("Semiconductor", ("semiconductor", "foundry", "fab")),
    ("Antitrust", ("antitrust", "competition watchdog", "competition regulator", "monopoly case")),
    ("Cybersecurity", ("cybersecurity", "cyber attack", "cyberattack", "hack", "hacking")),
    ("Data Center", ("data center", "data centres", "data centre", "data centers")),
    ("Supply Chain", ("supply chain", "shipping", "shipping route", "logistics")),
    ("Law", ("law", "legal", "legislation", "bill", "ban", "court ruling", "supreme court ruling")),
    ("Regulation", ("regulator", "regulation", "regulatory", "rules", "standards", "compliance")),
    ("Aid", ("aid", "military aid", "security aid", "support package")),
    ("Loan", ("loan", "loans", "loan scheme", "defence loan", "defense loan")),
    ("Financing", ("financing", "funding", "support package", "package", "scheme")),
    ("Trade", ("trade", "exports", "imports", "trade deal")),
    ("Tariff", ("tariff", "tariffs")),
    ("Sanctions", ("sanction", "sanctions")),
    ("Election", ("election", "vote", "votes", "campaign", "ballot")),
    ("Court", ("supreme court", "court", "judge", "lawsuit", "legal challenge")),
    ("Diplomacy", ("diplomacy", "diplomatic", "envoy")),
    ("Negotiation", ("negotiation", "negotiations", "negotiate")),
    ("Proposal", ("proposal", "ceasefire proposal", "responded to proposal")),
    ("Talks", ("talks", "peace talks")),
    ("Earnings", ("earnings", "profit", "profits", "revenue", "sales", "quarterly results")),
    ("Guidance", ("guidance", "forecast", "outlook")),
    ("Layoffs", ("layoffs", "layoff", "job cuts")),
    ("Merger", ("merger", "takeover", "merging")),
    ("Acquisition", ("acquisition", "buyout")),
    ("IPO", ("ipo", "listing", "initial public offering")),
    ("Banking", ("bank", "banks", "banking")),
    ("Retail", ("retail", "consumer spending")),
    ("Manufacturing", ("manufacturing", "factory", "factories", "industrial output")),
    ("Cloud", ("cloud",)),
    ("Export Controls", ("export controls", "export control", "export ban")),
    ("EV", ("electric vehicle", "electric vehicles", "ev")),
    ("Battery", ("battery", "batteries")),
    ("Telecom", ("telecom", "5g", "telecommunications")),
    ("Platform", ("platform", "platforms")),
    ("Software", ("software", "app", "apps")),
    ("Food Security", ("food security", "food", "meals", "grain", "wheat")),
    ("Agriculture", ("fertiliser", "fertilizer", "farm", "farming", "agriculture", "crop", "harvest")),
    ("Cruise", ("cruise", "cruise ship", "ship outbreak", "passengers")),
    ("Ceasefire", ("ceasefire", "truce")),
    ("NATO", ("nato",)),
    ("Migration", ("migration", "migrant", "migrants", "border crossing")),
    ("Currency", ("currency", "yen", "dollar", "euro", "sterling")),
    ("Stocks", ("stock market", "stocks", "shares", "equities")),
    ("Oil", ("oil", "crude", "brent")),
    ("Energy", ("energy", "gas", "gas prices", "electricity", "fuel")),
    ("Budget", ("budget", "budgets", "spending plan")),
    ("Debt", ("debt", "deficit", "borrowing")),
    ("Ukraine", ("ukraine", "ukrainian", "kyiv", "kiev")),
    ("War", ("war", "warfare", "invasion", "armed conflict", "military offensive", "airstrike", "strike", "troops", "missile", "battle", "combat")),
]
SIGNAL_TAG_PRIORITY = {
    "Surrogacy": 0,
    "Wildlife": 0,
    "Public Safety": 0,
    "Health": 0,
    "Virus": 0,
    "WHO": 0,
    "Public Health": 0,
    "Outbreak": 0,
    "Central Bank": 0,
    "Rates": 0,
    "Inflation": 0,
    "AI": 0,
    "OpenAI": 0,
    "Chips": 0,
    "Semiconductor": 0,
    "Antitrust": 0,
    "Cybersecurity": 0,
    "Data Center": 0,
    "Supply Chain": 0,
    "Law": 1,
    "Regulation": 1,
    "Aid": 1,
    "Loan": 1,
    "Financing": 1,
    "Trade": 1,
    "Tariff": 1,
    "Sanctions": 1,
    "Election": 1,
    "Court": 1,
    "Diplomacy": 1,
    "Negotiation": 1,
    "Proposal": 1,
    "Talks": 1,
    "Ukraine": 2,
    "War": 2,
    "Oil": 2,
    "Energy": 2,
}
MAX_SIGNAL_TAGS = 5


def _normalized_signal_text(*parts: str) -> str:
    combined = " ".join(part or "" for part in parts).strip().lower()
    normalized = re.sub(r"[^\w\s]", " ", combined)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return f" {normalized} "


def _has_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = _normalized_signal_text(phrase).strip()
    return f" {normalized_phrase} " in text


def _matches_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_has_phrase(text, phrase) for phrase in phrases)


def _has_wildlife_context(headline_text: str, summary_text: str) -> bool:
    combined_text = f"{headline_text} {summary_text}"
    return _matches_any_phrase(
        combined_text,
        ("bear", "bear attack", "animal attack", "wildlife", "hiker", "hiking", "mountain", "outdoor"),
    )


def _should_include_public_safety_tag(headline_text: str, summary_text: str) -> bool:
    combined_text = f"{headline_text} {summary_text}"
    direct_public_safety_terms = ("public safety", "safety", "fatal accident", "missing", "hiker", "mountain", "outdoor")
    if _matches_any_phrase(combined_text, direct_public_safety_terms):
        return True
    if _has_wildlife_context(headline_text, summary_text) and _matches_any_phrase(combined_text, ("dead", "killed", "injured")):
        return True
    return False


def _should_include_war_tag(headline_text: str, summary_text: str) -> bool:
    combined_text = f"{headline_text} {summary_text}"
    explicit_war_terms = (
        "war",
        "warfare",
        "invasion",
        "armed conflict",
        "military offensive",
        "airstrike",
        "troops",
        "missile",
        "battle",
        "combat",
    )
    if _matches_any_phrase(combined_text, explicit_war_terms):
        return True
    if _matches_any_phrase(combined_text, ("attack", "strike")) and not _has_wildlife_context(headline_text, summary_text):
        return True
    return False


def extract_signal_tags(headline: str, summary: str) -> list[str]:
    headline_text = _normalized_signal_text(headline)
    summary_text = _normalized_signal_text(summary)
    combined_text = f"{headline_text} {summary_text}"
    matched_tags: list[tuple[int, int, str]] = []

    for index, (label, phrases) in enumerate(SIGNAL_TAG_RULES):
        if label == "War":
            matched = _should_include_war_tag(headline_text, summary_text)
        elif label == "Public Safety":
            matched = _should_include_public_safety_tag(headline_text, summary_text)
        else:
            matched = _matches_any_phrase(combined_text, phrases)
        if matched:
            matched_tags.append((SIGNAL_TAG_PRIORITY.get(label, 1), index, label))

    ordered_tags = [label for _, _, label in sorted(matched_tags)[:MAX_SIGNAL_TAGS]]
    return ordered_tags


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
        signal_tags = extract_signal_tags(
            payload["headline"],
            payload["summary"],
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
