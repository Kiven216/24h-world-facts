"""Normalize multi-source raw articles into a minimal shared article shape."""

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

POLICY_KEYWORDS = (
    "government",
    "cabinet",
    "minister",
    "prime minister",
    "president",
    "parliament",
    "diet",
    "election",
    "vote",
    "policy",
    "regulator",
    "court",
)
MARKET_KEYWORDS = ("market", "inflation", "tariff", "trade", "economy", "stocks", "bank", "growth", "exports", "bond", "rates")
SECURITY_KEYWORDS = (
    "war",
    "attack",
    "military",
    "security",
    "missile",
    "troops",
    "sanction",
    "ceasefire",
    "strike",
    "maritime",
    "territorial",
    "coast guard",
)
TECH_KEYWORDS = (
    "technology",
    "tech",
    "ai",
    "chip",
    "chips",
    "semiconductor",
    "platform",
    "software",
    "digital",
    "cyber",
    "telecom",
    "cloud",
    "data center",
    "data centres",
    "supply chain",
    "export controls",
    "semiconductors",
    "chipmaker",
    "chipmakers",
    "manufacturing",
    "manufacturer",
    "telecommunications",
)
EUROPE_KEYWORDS = ("europe", "britain", "france", "germany", "ukraine", "russia", "brussels", "london", "paris", "berlin")
EAST_ASIA_KEYWORDS = (
    "japan",
    "japanese",
    "china",
    "taiwan",
    "korea",
    "tokyo",
    "beijing",
    "seoul",
    "hong kong",
    "taipei",
    "south china sea",
    "east china sea",
    "indo-pacific",
    "taiwan strait",
)
NORTH_AMERICA_KEYWORDS = ("united states", "u.s.", "usa", "canada", "mexico", "washington", "white house", "trump", "american")


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        if re.search(r"[^\w\s]", keyword):
            if keyword in text:
                return True
            continue
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

    cleaned = raw_value.strip()
    if cleaned.isdigit():
        try:
            timestamp = int(cleaned)
            if len(cleaned) >= 13:
                timestamp = timestamp / 1000
            parsed = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        except (OverflowError, ValueError, OSError):
            return _utc_now_iso()

    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except ValueError:
        pass

    try:
        parsed = parsedate_to_datetime(cleaned)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError):
        return _utc_now_iso()


def _guess_topic(source: str, feed_name: str, text_blob: str) -> str:
    normalized_source = source.lower()
    normalized_feed = feed_name.lower()
    lowered_blob = text_blob.lower()

    if normalized_feed == "politics":
        return "Policy / Politics"
    if normalized_feed == "business":
        return "Economy / Markets"
    if normalized_feed == "technology":
        return "Business / Tech / Industry"
    if normalized_source == "dw" and normalized_feed == "germany":
        if _contains_keyword(lowered_blob, SECURITY_KEYWORDS):
            return "Conflict / Security"
        if _contains_keyword(lowered_blob, MARKET_KEYWORDS):
            return "Economy / Markets"
        if _contains_keyword(lowered_blob, TECH_KEYWORDS):
            return "Business / Tech / Industry"
        return "Policy / Politics"

    if normalized_feed == "biztch":
        if _contains_keyword(lowered_blob, TECH_KEYWORDS):
            return "Business / Tech / Industry"
        if _contains_keyword(lowered_blob, MARKET_KEYWORDS):
            return "Economy / Markets"
        return "Business / Tech / Industry"

    if normalized_source == "nhk" and normalized_feed == "japan":
        if _contains_keyword(lowered_blob, SECURITY_KEYWORDS):
            return "Conflict / Security"
        if _contains_keyword(lowered_blob, TECH_KEYWORDS):
            return "Business / Tech / Industry"
        if _contains_keyword(lowered_blob, MARKET_KEYWORDS):
            return "Economy / Markets"
        return "Policy / Politics"

    if normalized_source == "nhk" and normalized_feed == "asia":
        if _contains_keyword(lowered_blob, SECURITY_KEYWORDS):
            return "Conflict / Security"
        if _contains_keyword(lowered_blob, TECH_KEYWORDS):
            return "Business / Tech / Industry"
        if _contains_keyword(lowered_blob, MARKET_KEYWORDS):
            return "Economy / Markets"
        if _contains_keyword(lowered_blob, POLICY_KEYWORDS):
            return "Policy / Politics"
        return "Policy / Politics"

    if _contains_keyword(lowered_blob, SECURITY_KEYWORDS):
        return "Conflict / Security"
    if _contains_keyword(lowered_blob, TECH_KEYWORDS):
        return "Business / Tech / Industry"
    if _contains_keyword(lowered_blob, MARKET_KEYWORDS):
        return "Economy / Markets"
    if _contains_keyword(lowered_blob, POLICY_KEYWORDS):
        return "Policy / Politics"
    return "Policy / Politics"


def _guess_region(source: str, feed_name: str, text_blob: str, topic_guess: str) -> str:
    lowered_blob = text_blob.lower()
    normalized_source = source.lower()
    normalized_feed = feed_name.lower()

    if _contains_keyword(lowered_blob, EUROPE_KEYWORDS):
        return "Europe"
    if _contains_keyword(lowered_blob, NORTH_AMERICA_KEYWORDS):
        return "North America"
    if _contains_keyword(lowered_blob, EAST_ASIA_KEYWORDS):
        return "Japan / East Asia"
    if normalized_source == "dw" and normalized_feed == "germany":
        return "Europe"
    if normalized_source == "nhk" and normalized_feed in {"japan", "asia"}:
        return "Japan / East Asia"
    if normalized_feed in {"business", "technology", "biztch"}:
        return "Global Markets"
    if topic_guess in {"Economy / Markets", "Business / Tech / Industry"}:
        return "Global Markets"
    return "Global Markets"


def run_normalize() -> dict[str, int]:
    rows = fetch_raw_articles_without_normalized()
    normalized_rows = []

    for row in rows:
        title = _clean_text(row["title_raw"])
        excerpt = _clean_text(row["excerpt_raw"] or title)
        text_blob = f"{title} {excerpt}"
        topic_guess = _guess_topic(row["source"], row["feed_name"], text_blob)
        region_guess = _guess_region(row["source"], row["feed_name"], text_blob, topic_guess)

        normalized_rows.append(
            {
                "article_raw_id": row["id"],
                "source": row["source"],
                "title": title,
                "url_canonical": _canonicalize_url(row["url"]),
                "published_at": _parse_published_at(row["published_at_raw"]),
                "excerpt": excerpt,
                "region_guess": region_guess,
                "topic_guess": topic_guess,
                "normalized_at": _utc_now_iso(),
            }
        )

    saved_count = upsert_article_normalized(normalized_rows)
    return {"normalized_count": saved_count}
