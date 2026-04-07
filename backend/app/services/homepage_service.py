import json

from ..config import settings
from ..db import fetch_app_meta, fetch_final_cards, init_database
from ..models.card import CardRecord


REGION_BUCKETS = [
    "North America",
    "Europe",
    "Japan / East Asia",
    "Global Markets",
]

TOPIC_BUCKETS = [
    "Policy / Politics",
    "Economy / Markets",
    "Business / Tech / Industry",
    "Conflict / Security",
]


def _blank_buckets(names: list[str]) -> dict[str, list[dict]]:
    return {name: [] for name in names}


def load_mock_payload() -> dict:
    with settings.mock_data_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _cards_from_database() -> list[CardRecord]:
    init_database()
    rows = fetch_final_cards()
    return [CardRecord.from_db_row(row) for row in rows]


def _cards_from_mock() -> tuple[list[CardRecord], dict]:
    payload = load_mock_payload()
    cards = [CardRecord.from_dict(item) for item in payload["cards"]]
    return cards, payload["meta"]


def _resolve_cards_and_meta() -> tuple[list[CardRecord], dict]:
    cards = _cards_from_database()
    if cards:
        meta_row = fetch_app_meta()
        meta = {
            "last_updated": meta_row["last_updated"] if meta_row else cards[0].updated_at,
            "window_hours": meta_row["window_hours"] if meta_row else 24,
            "total_events": meta_row["total_events"] if meta_row else len(cards),
        }
        return cards, meta
    return _cards_from_mock()


def build_homepage_payload() -> dict:
    cards, meta = _resolve_cards_and_meta()
    by_region = _blank_buckets(REGION_BUCKETS)
    by_topic = _blank_buckets(TOPIC_BUCKETS)
    top_stories: list[dict] = []
    watchlist: list[dict] = []

    for card in cards:
        card_payload = card.to_api_dict()
        if card.region not in by_region:
            by_region[card.region] = []
        if card.topic not in by_topic:
            by_topic[card.topic] = []

        by_region[card.region].append(card_payload)
        by_topic[card.topic].append(card_payload)

        if card.is_top_story:
            top_stories.append(card_payload)
        if card.is_watchlist:
            watchlist.append(card_payload)

    return {
        "meta": meta,
        "top_stories": top_stories,
        "by_region": by_region,
        "by_topic": by_topic,
        "watchlist": watchlist,
    }

