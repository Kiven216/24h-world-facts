"""Publish filtered multi-source articles into final_cards with temporary scoring logic."""

from datetime import datetime, timedelta, timezone
import re

from ..db import build_app_meta, fetch_publish_candidates, replace_app_meta, replace_real_final_cards


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _source_label(source: str) -> str:
    return {"bbc": "BBC", "nhk": "NHK"}.get(source.lower(), source.upper())


TOPIC_BASE_SCORES = {
    "Conflict / Security": 8.15,
    "Policy / Politics": 8.0,
    "Economy / Markets": 7.95,
    "Business / Tech / Industry": 7.85,
}
ECONOMY_SIGNAL_TERMS = (
    "inflation",
    "cpi",
    "rates",
    "interest rates",
    "central bank",
    "fed",
    "boj",
    "ecb",
    "yield",
    "yields",
    "jobs",
    "payroll",
    "payrolls",
    "unemployment",
    "trade",
    "tariff",
    "tariffs",
    "exports",
    "imports",
    "oil prices",
    "recession",
    "growth",
    "budget",
    "deficit",
    "currency",
    "yen",
    "dollar",
)
BUSINESS_SIGNAL_TERMS = (
    "ai",
    "chip",
    "chips",
    "semiconductor",
    "export controls",
    "cloud",
    "data center",
    "data centres",
    "antitrust",
    "merger",
    "earnings",
    "guidance",
    "layoffs",
    "supply chain",
    "factory",
    "manufacturing",
    "platform",
    "software",
    "telecom",
    "industrial policy",
    "battery",
    "ev",
    "foundry",
    "fab",
)
POLICY_SIGNAL_TERMS = (
    "election",
    "vote",
    "court",
    "ruling",
    "law",
    "regulator",
    "government",
    "minister",
    "cabinet",
    "parliament",
    "diet",
    "president",
    "prime minister",
)
CONFLICT_SIGNAL_TERMS = (
    "war",
    "attack",
    "military",
    "sanction",
    "sanctions",
    "security",
    "hostage",
    "strike",
    "missile",
    "troops",
    "ceasefire",
    "clash",
    "clashes",
    "maritime",
    "territorial",
    "blockade",
)
GENERAL_HIGH_IMPACT_TERMS = (
    "election",
    "court",
    "tariff",
    "inflation",
    "rates",
    "war",
    "attack",
    "sanction",
    "sanctions",
    "central bank",
    "merger",
    "earnings",
    "export controls",
)
TOP_STORY_SCORE_THRESHOLD = 8.4
TOP_STORY_TOPIC_ENTRY_THRESHOLDS = {
    "Economy / Markets": 8.15,
    "Business / Tech / Industry": 8.05,
}


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        if " " in keyword:
            if keyword in text:
                return True
            continue
        if re.search(rf"\b{re.escape(keyword)}\b", text):
            return True
    return False


def _count_term_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if _contains_any(text, (keyword,)))


def _score_article(topic: str, title: str) -> float:
    lowered_title = title.lower()
    # Temporary 10-point display scale until event-level scoring replaces article-level heuristics.
    base_score = TOPIC_BASE_SCORES.get(topic, 8.0)

    if _contains_any(lowered_title, GENERAL_HIGH_IMPACT_TERMS):
        base_score += 0.25

    if topic == "Economy / Markets":
        signal_hits = _count_term_hits(lowered_title, ECONOMY_SIGNAL_TERMS)
        if signal_hits >= 1:
            base_score += 0.25
        if signal_hits >= 2:
            base_score += 0.15
    elif topic == "Business / Tech / Industry":
        signal_hits = _count_term_hits(lowered_title, BUSINESS_SIGNAL_TERMS)
        if signal_hits >= 1:
            base_score += 0.3
        if signal_hits >= 2:
            base_score += 0.15
    elif topic == "Policy / Politics":
        signal_hits = _count_term_hits(lowered_title, POLICY_SIGNAL_TERMS)
        if signal_hits >= 1:
            base_score += 0.2
        if signal_hits >= 2:
            base_score += 0.1
    else:
        signal_hits = _count_term_hits(lowered_title, CONFLICT_SIGNAL_TERMS)
        if signal_hits >= 1:
            base_score += 0.22
        if signal_hits >= 2:
            base_score += 0.1

    return round(min(max(base_score, 6.5), 9.2), 1)


def _derive_status(title: str) -> str:
    official_markers = ("government", "minister", "court", "president", "prime minister", "official")
    return "Confirmed" if any(marker in title.lower() for marker in official_markers) else "Widely Reported"


def _should_watch(title: str, topic: str, score: float) -> bool:
    lowered_title = title.lower()
    watch_terms = ("tariff", "sanction", "inflation", "court", "war", "attack")
    return topic == "Conflict / Security" or (score >= 8.6 and any(keyword in lowered_title for keyword in watch_terms))


def _is_top_story_candidate(topic: str, score: float) -> bool:
    topic_threshold = TOP_STORY_TOPIC_ENTRY_THRESHOLDS.get(topic, TOP_STORY_SCORE_THRESHOLD)
    return score >= topic_threshold


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
                "why_it_matters": "",
                "region": row["region_guess"],
                "topic": row["topic_guess"],
                "status": _derive_status(row["title"]),
                "importance_score": score,
                "published_at": row["published_at"],
                "updated_at": row["filtered_at"],
                "article_url": row["url_canonical"],
                "source_list": [_source_label(row["source"])],
                "is_top_story": _is_top_story_candidate(row["topic_guess"], score),
                "is_watchlist": _should_watch(row["title"], row["topic_guess"], score),
            }
        )

    replace_real_final_cards(cards)
    replace_app_meta(build_app_meta(len(cards)))
    return {"published_count": len(cards)}
