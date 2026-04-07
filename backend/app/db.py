import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterable

from .config import settings


ARTICLE_RAW_SCHEMA = """
CREATE TABLE IF NOT EXISTS article_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    feed_name TEXT NOT NULL,
    title_raw TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    published_at_raw TEXT,
    excerpt_raw TEXT,
    fetched_at TEXT NOT NULL
);
"""


ARTICLE_NORMALIZED_SCHEMA = """
CREATE TABLE IF NOT EXISTS article_normalized (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_raw_id INTEGER NOT NULL UNIQUE,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url_canonical TEXT NOT NULL UNIQUE,
    published_at TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    region_guess TEXT NOT NULL,
    topic_guess TEXT NOT NULL,
    normalized_at TEXT NOT NULL,
    FOREIGN KEY(article_raw_id) REFERENCES article_raw(id)
);
"""


ARTICLE_FILTERED_SCHEMA = """
CREATE TABLE IF NOT EXISTS article_filtered (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_normalized_id INTEGER NOT NULL UNIQUE,
    passed_filter INTEGER NOT NULL,
    filter_reason TEXT NOT NULL,
    time_window_pass INTEGER NOT NULL,
    topic_pass INTEGER NOT NULL,
    filtered_at TEXT NOT NULL,
    FOREIGN KEY(article_normalized_id) REFERENCES article_normalized(id)
);
"""


FINAL_CARDS_SCHEMA = """
CREATE TABLE IF NOT EXISTS final_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    headline TEXT NOT NULL,
    summary TEXT NOT NULL,
    why_it_matters TEXT NOT NULL,
    region TEXT NOT NULL,
    topic TEXT NOT NULL,
    status TEXT NOT NULL,
    importance_score REAL NOT NULL DEFAULT 0,
    published_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source_list_json TEXT NOT NULL,
    is_top_story INTEGER NOT NULL DEFAULT 0,
    is_watchlist INTEGER NOT NULL DEFAULT 0
);
"""


APP_META_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_meta (
    id INTEGER PRIMARY KEY,
    last_updated TEXT NOT NULL,
    window_hours INTEGER NOT NULL DEFAULT 24,
    total_events INTEGER NOT NULL DEFAULT 0
);
"""


@contextmanager
def get_connection():
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_database() -> None:
    with get_connection() as connection:
        connection.execute(ARTICLE_RAW_SCHEMA)
        connection.execute(ARTICLE_NORMALIZED_SCHEMA)
        connection.execute(ARTICLE_FILTERED_SCHEMA)
        connection.execute(FINAL_CARDS_SCHEMA)
        connection.execute(APP_META_SCHEMA)


def fetch_final_cards() -> list[sqlite3.Row]:
    query = """
    SELECT *
    FROM final_cards
    ORDER BY importance_score DESC, published_at DESC, id ASC
    """
    with get_connection() as connection:
        rows = connection.execute(query).fetchall()
    return rows


def fetch_real_final_cards() -> list[sqlite3.Row]:
    query = """
    SELECT *
    FROM final_cards
    WHERE event_id LIKE 'bbc:%'
    ORDER BY importance_score DESC, published_at DESC, id ASC
    """
    with get_connection() as connection:
        rows = connection.execute(query).fetchall()
    return rows


def fetch_app_meta() -> sqlite3.Row | None:
    query = """
    SELECT *
    FROM app_meta
    ORDER BY id ASC
    LIMIT 1
    """
    with get_connection() as connection:
        row = connection.execute(query).fetchone()
    return row


def _prepare_final_card_rows(cards: Iterable[dict]) -> list[tuple]:
    return [
        (
            card["event_id"],
            card["headline"],
            card["summary"],
            card["why_it_matters"],
            card["region"],
            card["topic"],
            card["status"],
            card["importance_score"],
            card["published_at"],
            card["updated_at"],
            json.dumps(card["source_list"], ensure_ascii=True),
            int(card.get("is_top_story", False)),
            int(card.get("is_watchlist", False)),
        )
        for card in cards
    ]


def replace_final_cards(cards: Iterable[dict]) -> None:
    insert_sql = """
    INSERT INTO final_cards (
        event_id,
        headline,
        summary,
        why_it_matters,
        region,
        topic,
        status,
        importance_score,
        published_at,
        updated_at,
        source_list_json,
        is_top_story,
        is_watchlist
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    prepared_rows = _prepare_final_card_rows(cards)
    with get_connection() as connection:
        connection.execute("DELETE FROM final_cards")
        if prepared_rows:
            connection.executemany(insert_sql, prepared_rows)


def replace_real_final_cards(cards: Iterable[dict]) -> None:
    insert_sql = """
    INSERT INTO final_cards (
        event_id,
        headline,
        summary,
        why_it_matters,
        region,
        topic,
        status,
        importance_score,
        published_at,
        updated_at,
        source_list_json,
        is_top_story,
        is_watchlist
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    prepared_rows = _prepare_final_card_rows(cards)
    with get_connection() as connection:
        connection.execute("DELETE FROM final_cards WHERE event_id LIKE 'bbc:%'")
        if prepared_rows:
            connection.executemany(insert_sql, prepared_rows)


def replace_app_meta(meta: dict) -> None:
    query = """
    INSERT INTO app_meta (id, last_updated, window_hours, total_events)
    VALUES (1, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        last_updated = excluded.last_updated,
        window_hours = excluded.window_hours,
        total_events = excluded.total_events
    """
    with get_connection() as connection:
        connection.execute(query, (meta["last_updated"], meta["window_hours"], meta["total_events"]))


def insert_article_raw(rows: Iterable[dict]) -> int:
    query = """
    INSERT OR IGNORE INTO article_raw (
        source,
        feed_name,
        title_raw,
        url,
        published_at_raw,
        excerpt_raw,
        fetched_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    inserted = 0
    with get_connection() as connection:
        for row in rows:
            cursor = connection.execute(
                query,
                (
                    row["source"],
                    row["feed_name"],
                    row["title_raw"],
                    row["url"],
                    row.get("published_at_raw"),
                    row.get("excerpt_raw"),
                    row["fetched_at"],
                ),
            )
            inserted += int(cursor.rowcount > 0)
    return inserted


def fetch_raw_articles_without_normalized() -> list[sqlite3.Row]:
    query = """
    SELECT ar.*
    FROM article_raw ar
    LEFT JOIN article_normalized an ON an.article_raw_id = ar.id
    WHERE an.id IS NULL
    ORDER BY ar.id ASC
    """
    with get_connection() as connection:
        rows = connection.execute(query).fetchall()
    return rows


def upsert_article_normalized(rows: Iterable[dict]) -> int:
    query = """
    INSERT INTO article_normalized (
        article_raw_id,
        source,
        title,
        url_canonical,
        published_at,
        excerpt,
        region_guess,
        topic_guess,
        normalized_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(article_raw_id) DO UPDATE SET
        source = excluded.source,
        title = excluded.title,
        url_canonical = excluded.url_canonical,
        published_at = excluded.published_at,
        excerpt = excluded.excerpt,
        region_guess = excluded.region_guess,
        topic_guess = excluded.topic_guess,
        normalized_at = excluded.normalized_at
    """
    count = 0
    with get_connection() as connection:
        for row in rows:
            connection.execute(
                query,
                (
                    row["article_raw_id"],
                    row["source"],
                    row["title"],
                    row["url_canonical"],
                    row["published_at"],
                    row["excerpt"],
                    row["region_guess"],
                    row["topic_guess"],
                    row["normalized_at"],
                ),
            )
            count += 1
    return count


def fetch_normalized_articles_without_filter() -> list[sqlite3.Row]:
    query = """
    SELECT an.*, ar.feed_name
    FROM article_normalized an
    JOIN article_raw ar ON ar.id = an.article_raw_id
    LEFT JOIN article_filtered af ON af.article_normalized_id = an.id
    WHERE af.id IS NULL
    ORDER BY an.id ASC
    """
    with get_connection() as connection:
        rows = connection.execute(query).fetchall()
    return rows


def upsert_article_filtered(rows: Iterable[dict]) -> int:
    query = """
    INSERT INTO article_filtered (
        article_normalized_id,
        passed_filter,
        filter_reason,
        time_window_pass,
        topic_pass,
        filtered_at
    ) VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(article_normalized_id) DO UPDATE SET
        passed_filter = excluded.passed_filter,
        filter_reason = excluded.filter_reason,
        time_window_pass = excluded.time_window_pass,
        topic_pass = excluded.topic_pass,
        filtered_at = excluded.filtered_at
    """
    count = 0
    with get_connection() as connection:
        for row in rows:
            connection.execute(
                query,
                (
                    row["article_normalized_id"],
                    int(row["passed_filter"]),
                    row["filter_reason"],
                    int(row["time_window_pass"]),
                    int(row["topic_pass"]),
                    row["filtered_at"],
                ),
            )
            count += 1
    return count


def fetch_publish_candidates() -> list[sqlite3.Row]:
    query = """
    SELECT
        an.id AS article_normalized_id,
        an.source,
        an.title,
        an.url_canonical,
        an.published_at,
        an.excerpt,
        an.region_guess,
        an.topic_guess,
        af.filtered_at,
        ar.feed_name
    FROM article_filtered af
    JOIN article_normalized an ON an.id = af.article_normalized_id
    JOIN article_raw ar ON ar.id = an.article_raw_id
    WHERE af.passed_filter = 1
    ORDER BY an.published_at DESC, an.id DESC
    """
    with get_connection() as connection:
        rows = connection.execute(query).fetchall()
    return rows


def build_app_meta(total_events: int) -> dict[str, str | int]:
    return {
        "last_updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "window_hours": 24,
        "total_events": total_events,
    }
