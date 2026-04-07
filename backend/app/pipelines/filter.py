"""Apply reusable quality filters to normalized BBC articles before publish."""

from datetime import datetime, timezone

from ..db import fetch_normalized_articles_without_filter, upsert_article_filtered
from ..rules.filters import evaluate_article_filters


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_filter() -> dict[str, int]:
    rows = fetch_normalized_articles_without_filter()
    filtered_rows = []
    passed_count = 0

    for row in rows:
        evaluation = evaluate_article_filters(
            title=row["title"],
            excerpt=row["excerpt"],
            url=row["url_canonical"],
            topic=row["topic_guess"],
            region=row["region_guess"],
            published_at=row["published_at"],
        )
        passed_count += int(bool(evaluation["passed_filter"]))
        filtered_rows.append(
            {
                "article_normalized_id": row["id"],
                "passed_filter": bool(evaluation["passed_filter"]),
                "filter_reason": str(evaluation["filter_reason"]),
                "time_window_pass": bool(evaluation["time_window_pass"]),
                "topic_pass": bool(evaluation["topic_pass"]),
                "filtered_at": _utc_now_iso(),
            }
        )

    saved_count = upsert_article_filtered(filtered_rows)
    return {"evaluated_count": saved_count, "passed_count": passed_count}
