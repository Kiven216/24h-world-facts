"""Apply lightweight quality and topical filters to normalized articles."""

from datetime import datetime, timedelta, timezone

from ..db import fetch_normalized_articles_without_filter, upsert_article_filtered


SUPPORTED_TOPICS = {
    "Policy / Politics",
    "Economy / Markets",
    "Business / Tech / Industry",
    "Conflict / Security",
}

EXCLUDE_TERMS = ("sport", "entertainment", "celebrity", "gossip", "review")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _is_valid_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def _evaluate_article(row) -> tuple[bool, str, bool, bool]:
    title = (row["title"] or "").strip()
    excerpt = (row["excerpt"] or "").strip()
    topic = row["topic_guess"]
    published_at = _parse_iso_datetime(row["published_at"])
    text_blob = f"{title} {excerpt}".lower()

    time_window_pass = published_at >= _utc_now() - timedelta(hours=24)
    topic_pass = topic in SUPPORTED_TOPICS

    if not title or len(title) < 12:
        return False, "invalid_title", time_window_pass, topic_pass
    if not excerpt:
        return False, "missing_excerpt", time_window_pass, topic_pass
    if not _is_valid_url(row["url_canonical"]):
        return False, "invalid_url", time_window_pass, topic_pass
    if any(term in text_blob for term in EXCLUDE_TERMS):
        return False, "excluded_by_keyword", time_window_pass, topic_pass
    if not time_window_pass:
        return False, "out_of_time_window", time_window_pass, topic_pass
    if not topic_pass:
        return False, "unsupported_topic", time_window_pass, topic_pass
    return True, "passed", time_window_pass, topic_pass


def run_filter() -> dict[str, int]:
    rows = fetch_normalized_articles_without_filter()
    filtered_rows = []
    passed_count = 0

    for row in rows:
        passed_filter, reason, time_window_pass, topic_pass = _evaluate_article(row)
        passed_count += int(passed_filter)
        filtered_rows.append(
            {
                "article_normalized_id": row["id"],
                "passed_filter": passed_filter,
                "filter_reason": reason,
                "time_window_pass": time_window_pass,
                "topic_pass": topic_pass,
                "filtered_at": _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            }
        )

    saved_count = upsert_article_filtered(filtered_rows)
    return {"evaluated_count": saved_count, "passed_count": passed_count}
