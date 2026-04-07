"""Normalize raw BBC RSS articles into a minimal shared article shape."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..db import fetch_raw_articles_without_normalized, upsert_article_normalized


TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ocid",
}

MARKET_KEYWORDS = ("market", "inflation", "tariff", "trade", "economy", "stocks", "bank", "growth", "exports")
SECURITY_KEYWORDS = ("war", "attack", "military", "security", "missile", "troops", "sanction", "ceasefire", "strike")
TECH_KEYWORDS = ("technology", "tech", "ai", "chip", "chips", "semiconductor", "platform", "software", "digital")
EUROPE_KEYWORDS = ("europe", "britain", "france", "germany", "ukraine", "russia", "brussels", "london", "paris", "berlin")
EAST_ASIA_KEYWORDS = ("japan", "china", "taiwan", "korea", "tokyo", "beijing", "seoul", "hong kong")
NORTH_AMERICA_KEYWORDS = ("united states", "u.s.", "usa", "canada", "mexico", "washington", "white house", "trump", "american")


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        if re.search(rf"\b{re.escape(keyword)}\b", text):
            return True
    return False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _canonicalize_url(raw_url: str) -> str:
    parsed = urlparse((raw_url or "").strip())
    filtered_query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=False) if key.lower() not in TRACKING_QUERY_KEYS]
    canonical = parsed._replace(query=urlencode(filtered_query), fragment="")
    return urlunparse(canonical)


def _parse_published_at(raw_value: str) -> str:
    if not raw_value:
        return _utc_now_iso()

    try:
        parsed = parsedate_to_datetime(raw_value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError):
        return _utc_now_iso()


def _guess_topic(feed_name: str, text_blob: str) -> str:
    normalized_feed = feed_name.lower()
    lowered_blob = text_blob.lower()

    if normalized_feed == "politics":
        return "Policy / Politics"
    if normalized_feed == "business":
        return "Economy / Markets"
    if normalized_feed == "technology":
        return "Business / Tech / Industry"
    if _contains_keyword(lowered_blob, SECURITY_KEYWORDS):
        return "Conflict / Security"
    if _contains_keyword(lowered_blob, MARKET_KEYWORDS):
        return "Economy / Markets"
    if _contains_keyword(lowered_blob, TECH_KEYWORDS):
        return "Business / Tech / Industry"
    return "Policy / Politics"


def _guess_region(feed_name: str, text_blob: str) -> str:
    lowered_blob = text_blob.lower()
    normalized_feed = feed_name.lower()

    if _contains_keyword(lowered_blob, EUROPE_KEYWORDS):
        return "Europe"
    if _contains_keyword(lowered_blob, EAST_ASIA_KEYWORDS):
        return "Japan / East Asia"
    if _contains_keyword(lowered_blob, NORTH_AMERICA_KEYWORDS):
        return "North America"
    if normalized_feed in {"business", "technology"}:
        return "Global Markets"
    return "Global Markets"


def run_normalize() -> dict[str, int]:
    rows = fetch_raw_articles_without_normalized()
    normalized_rows = []

    for row in rows:
        title = _clean_text(row["title_raw"])
        excerpt = _clean_text(row["excerpt_raw"] or title)
        text_blob = f"{title} {excerpt}"

        normalized_rows.append(
            {
                "article_raw_id": row["id"],
                "source": row["source"],
                "title": title,
                "url_canonical": _canonicalize_url(row["url"]),
                "published_at": _parse_published_at(row["published_at_raw"]),
                "excerpt": excerpt,
                "region_guess": _guess_region(row["feed_name"], text_blob),
                "topic_guess": _guess_topic(row["feed_name"], text_blob),
                "normalized_at": _utc_now_iso(),
            }
        )

    saved_count = upsert_article_normalized(normalized_rows)
    return {"normalized_count": saved_count}
