"""Publish filtered multi-source articles into final_cards with temporary scoring logic."""

from datetime import datetime, timedelta, timezone
import re

from ..db import build_app_meta, fetch_publish_candidates, replace_app_meta, replace_real_final_cards


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        if re.search(r"[^\w\s]", keyword):
            if keyword in text:
                return True
            continue
        if re.search(rf"\b{re.escape(keyword)}\b", text):
            return True
    return False


def _source_label(source: str) -> str:
    return {"bbc": "BBC", "nhk": "NHK"}.get(source.lower(), source.upper())


def _build_why_it_matters(title: str, topic: str, region: str) -> str:
    lowered_title = title.lower()
    tech_terms = (
        "ai",
        "chip",
        "chips",
        "chipmaker",
        "semiconductor",
        "platform",
        "cyber",
        "software",
        "telecom",
        "cloud",
        "data center",
        "data centres",
        "manufacturing",
        "export controls",
    )
    east_asia_terms = (
        "japan",
        "japanese",
        "china",
        "taiwan",
        "korea",
        "tokyo",
        "beijing",
        "seoul",
        "taipei",
        "indo-pacific",
        "south china sea",
        "east china sea",
        "taiwan strait",
    )

    if _contains_any(lowered_title, ("trade", "tariff", "tariffs", "export", "exports", "supply chain", "manufacturing", "factory", "export controls")):
        return f"This could move trade flows, supply-chain planning, and production costs tied to {region}."
    if _contains_any(lowered_title, ("inflation", "rates", "rate", "bond", "bonds", "market", "markets", "growth", "oil prices", "economy", "yen")):
        return f"This may shift market expectations, financing conditions, and risk appetite connected to {region}."
    if _contains_any(lowered_title, ("court", "ruling", "law", "regulator", "government", "minister", "cabinet", "parliament", "diet", "supreme court", "election", "vote")):
        return f"This signals where policy or legal direction may be heading, with follow-through implications beyond {region}."
    if _contains_any(lowered_title, ("war", "attack", "military", "sanction", "sanctions", "security", "hostage", "strike", "missile", "troops", "ceasefire", "clash", "clashes", "killed", "rescue", "airman", "maritime", "territorial")):
        return f"This is a live geopolitical risk signal that could spill into security conditions, energy markets, and cross-border sentiment around {region}."
    if region == "Japan / East Asia" and _contains_any(lowered_title, tech_terms) and _contains_any(lowered_title, east_asia_terms):
        return "This matters for East Asia because technology competition, manufacturing links, and regional market positioning can all move off the same signal."
    if region == "Japan / East Asia" and _contains_any(lowered_title, east_asia_terms):
        return "This matters for East Asia because regional trade, manufacturing links, and geopolitical positioning can shift together quickly."
    if _contains_any(lowered_title, tech_terms):
        return f"This is relevant to technology competition, investment priorities, and supply-chain positioning linked to {region}."
    if topic == "Policy / Politics":
        return f"This could shape near-term policy signals and international positioning around {region}."
    if topic == "Economy / Markets":
        return f"This is a useful read-through for cross-border growth, trade, and market sentiment tied to {region}."
    if topic == "Business / Tech / Industry":
        return f"This may affect business planning, supply chains, and technology investment linked to {region}."
    return f"This is worth monitoring because it may alter the near-term security picture and broader risk sentiment around {region}."


def _score_article(topic: str, title: str) -> float:
    lowered_title = title.lower()
    # Temporary 10-point display scale until event-level scoring replaces article-level heuristics.
    if topic == "Policy / Politics":
        base_score = 8.3
    elif topic == "Economy / Markets":
        base_score = 7.8
    elif topic == "Business / Tech / Industry":
        base_score = 7.2
    else:
        base_score = 8.5

    if any(keyword in lowered_title for keyword in ("election", "tariff", "sanction", "inflation", "war", "attack", "court")):
        base_score += 0.4
    if any(keyword in lowered_title for keyword in ("ai", "chip", "market", "trade", "government")):
        base_score += 0.2

    return round(min(max(base_score, 6.5), 9.2), 1)


def _derive_status(title: str) -> str:
    official_markers = ("government", "minister", "court", "president", "prime minister", "official")
    return "Confirmed" if any(marker in title.lower() for marker in official_markers) else "Widely Reported"


def _should_watch(title: str, topic: str, score: float) -> bool:
    lowered_title = title.lower()
    watch_terms = ("tariff", "sanction", "inflation", "court", "war", "attack")
    return topic == "Conflict / Security" or (score >= 8.6 and any(keyword in lowered_title for keyword in watch_terms))


def run_publish() -> dict[str, int]:
    candidates = fetch_publish_candidates()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    cards = []

    for row in candidates:
        published_at = _parse_iso_datetime(row["published_at"])
        if published_at < cutoff:
            continue

        score = _score_article(row["topic_guess"], row["title"])
        cards.append(
            {
                "event_id": f"{row['source']}:{row['article_normalized_id']}",
                "headline": row["title"],
                "summary": row["excerpt"],
                "why_it_matters": _build_why_it_matters(row["title"], row["topic_guess"], row["region_guess"]),
                "region": row["region_guess"],
                "topic": row["topic_guess"],
                "status": _derive_status(row["title"]),
                "importance_score": score,
                "published_at": row["published_at"],
                "updated_at": row["filtered_at"],
                "source_list": [_source_label(row["source"])],
                "is_top_story": score >= 8.6,
                "is_watchlist": _should_watch(row["title"], row["topic_guess"], score),
            }
        )

    replace_real_final_cards(cards)
    replace_app_meta(build_app_meta(len(cards)))
    return {"published_count": len(cards)}
