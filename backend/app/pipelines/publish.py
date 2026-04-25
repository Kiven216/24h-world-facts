"""Publish filtered multi-source articles into final_cards with temporary scoring logic."""

from datetime import datetime, timedelta, timezone

from ..db import build_app_meta, fetch_publish_candidates, replace_app_meta, replace_real_final_cards


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _source_label(source: str) -> str:
    return {"bbc": "BBC", "nhk": "NHK"}.get(source.lower(), source.upper())


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
                "why_it_matters": "",
                "region": row["region_guess"],
                "topic": row["topic_guess"],
                "status": _derive_status(row["title"]),
                "importance_score": score,
                "published_at": row["published_at"],
                "updated_at": row["filtered_at"],
                "article_url": row["url_canonical"],
                "source_list": [_source_label(row["source"])],
                "is_top_story": score >= 8.6,
                "is_watchlist": _should_watch(row["title"], row["topic_guess"], score),
            }
        )

    replace_real_final_cards(cards)
    replace_app_meta(build_app_meta(len(cards)))
    return {"published_count": len(cards)}
