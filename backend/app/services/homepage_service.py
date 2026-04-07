import json
from datetime import datetime

from ..config import settings
from ..db import fetch_app_meta, fetch_real_final_cards, init_database
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

MIN_REAL_CARD_COUNT = 6
MAX_TOP_STORIES = 8
MAX_WATCHLIST = 4
MAX_REGION_STORIES = 3
MAX_TOPIC_STORIES = 3


def _blank_buckets(names: list[str]) -> dict[str, list[dict]]:
    return {name: [] for name in names}


def _parse_card_time(value: str) -> datetime:
    return datetime.fromisoformat((value or "").replace("Z", "+00:00"))


def _card_sort_key(card: CardRecord) -> tuple[float, datetime, datetime]:
    return (
        float(card.importance_score),
        _parse_card_time(card.updated_at),
        _parse_card_time(card.published_at),
    )


def _sorted_cards(cards: list[CardRecord]) -> list[CardRecord]:
    return sorted(cards, key=_card_sort_key, reverse=True)


def _limit_card_payloads(cards: list[CardRecord], max_items: int) -> list[dict]:
    return [card.to_api_dict() for card in _sorted_cards(cards)[:max_items]]


def load_mock_payload() -> dict:
    with settings.mock_data_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _cards_from_database() -> list[CardRecord]:
    init_database()
    rows = fetch_real_final_cards()
    return [CardRecord.from_db_row(row) for row in rows]


def _cards_from_mock() -> tuple[list[CardRecord], dict]:
    payload = load_mock_payload()
    cards = [CardRecord.from_dict(item) for item in payload["cards"]]
    return cards, payload["meta"]


def _merge_real_and_mock(real_cards: list[CardRecord], mock_cards: list[CardRecord]) -> list[CardRecord]:
    if len(real_cards) >= MIN_REAL_CARD_COUNT:
        return real_cards

    merged_cards = list(real_cards)
    seen_headlines = {card.headline.strip().lower() for card in real_cards}

    for card in mock_cards:
        normalized_headline = card.headline.strip().lower()
        if normalized_headline in seen_headlines:
            continue

        merged_cards.append(card)
        seen_headlines.add(normalized_headline)

        if len(merged_cards) >= MIN_REAL_CARD_COUNT:
            break

    return merged_cards


def _resolve_cards_and_meta() -> tuple[list[CardRecord], dict]:
    real_cards = _cards_from_database()
    mock_cards, mock_meta = _cards_from_mock()

    if not real_cards:
        return mock_cards, mock_meta

    meta_row = fetch_app_meta()
    merged_cards = _merge_real_and_mock(real_cards, mock_cards)
    meta = {
        "last_updated": meta_row["last_updated"] if meta_row else real_cards[0].updated_at,
        "window_hours": meta_row["window_hours"] if meta_row else 24,
        "total_events": len(merged_cards),
    }
    return merged_cards, meta


def build_homepage_payload() -> dict:
    cards, meta = _resolve_cards_and_meta()
    by_region = _blank_buckets(REGION_BUCKETS)
    by_topic = _blank_buckets(TOPIC_BUCKETS)
    top_story_cards: list[CardRecord] = []
    watchlist_cards: list[CardRecord] = []

    for card in cards:
        if card.region not in by_region:
            by_region[card.region] = []
        if card.topic not in by_topic:
            by_topic[card.topic] = []

        by_region[card.region].append(card)
        by_topic[card.topic].append(card)

        if card.is_top_story:
            top_story_cards.append(card)
        if card.is_watchlist:
            watchlist_cards.append(card)

    top_stories = _limit_card_payloads(top_story_cards, MAX_TOP_STORIES)
    watchlist = _limit_card_payloads(watchlist_cards, MAX_WATCHLIST)
    limited_region = {name: _limit_card_payloads(region_cards, MAX_REGION_STORIES) for name, region_cards in by_region.items()}
    limited_topic = {name: _limit_card_payloads(topic_cards, MAX_TOPIC_STORIES) for name, topic_cards in by_topic.items()}

    return {
        "meta": meta,
        "top_stories": top_stories,
        "by_region": limited_region,
        "by_topic": limited_topic,
        "watchlist": watchlist,
    }
