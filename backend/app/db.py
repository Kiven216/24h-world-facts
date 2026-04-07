import json
import sqlite3
from contextlib import contextmanager
from typing import Iterable

from .config import settings


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
    prepared_rows = [
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
    with get_connection() as connection:
        connection.execute("DELETE FROM final_cards")
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

