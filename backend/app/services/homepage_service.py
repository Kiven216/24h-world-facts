import json
from datetime import datetime
from pathlib import Path
import re

from ..config import settings
from ..db import fetch_app_meta, fetch_real_final_cards, init_database
from ..models.card import CardRecord
from .explanation_service import enrich_top_stories_with_llm_explanations


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
SAME_EVENT_MIN_SHARED_TOKENS = 3
MODERATE_SAME_EVENT_OVERLAP_THRESHOLD = 0.46
STRONG_SAME_EVENT_OVERLAP_THRESHOLD = 0.68
TOP_STORY_TOPIC_SOFT_CAPS = {
    "Conflict / Security": 2,
    "Policy / Politics": 2,
}
TOP_STORY_DIVERSITY_TOPICS = (
    "Economy / Markets",
    "Business / Tech / Industry",
)
TOP_STORY_DIVERSITY_MIN_SCORE = 7.4
EXPOSURE_HISTORY_FILENAME = "homepage_exposure_history.json"
EXPOSURE_HISTORY_MAX_ROUNDS = 5
EXPOSURE_ROUND_PENALTY = 0.18
EXPOSURE_STREAK_PENALTY = 0.22
REAL_SOURCE_PREFIXES = {"bbc", "nhk", "npr"}
PHRASE_NORMALIZATIONS = {
    "artificial intelligence": "ai",
    "crude oil": "oil",
    "cargo ship": "ship",
    "oil tanker": "ship",
    "supreme court": "court",
    "strait of hormuz": "hormuz",
    "warning shots": "warning",
}
TOKEN_NORMALIZATIONS = {
    "seized": "seize",
    "seizure": "seize",
    "seizures": "seize",
    "warns": "warn",
    "warning": "warn",
    "warnings": "warn",
    "sanctions": "sanction",
    "tariffs": "tariff",
    "cuts": "cut",
    "ships": "ship",
    "vessels": "ship",
    "mortgages": "mortgage",
}
TITLE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "to",
    "with",
}


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


def _is_real_source_event_id(event_id: str) -> bool:
    prefix, _, _ = (event_id or "").partition(":")
    return prefix in REAL_SOURCE_PREFIXES


def _exposure_history_path() -> Path:
    return settings.data_dir / EXPOSURE_HISTORY_FILENAME


def _load_exposure_history() -> dict:
    history_path = _exposure_history_path()
    if not history_path.exists():
        return {"last_recorded_refresh": None, "rounds": []}

    try:
        with history_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {"last_recorded_refresh": None, "rounds": []}

    rounds = payload.get("rounds", [])
    if not isinstance(rounds, list):
        rounds = []
    return {
        "last_recorded_refresh": payload.get("last_recorded_refresh"),
        "rounds": rounds[-EXPOSURE_HISTORY_MAX_ROUNDS:],
    }


def _build_exposure_penalties(history: dict) -> dict[str, float]:
    penalties: dict[str, float] = {}
    rounds = history.get("rounds", [])

    for round_index, round_payload in enumerate(reversed(rounds), start=1):
        for event_id in round_payload.get("event_ids", []):
            penalties[event_id] = penalties.get(event_id, 0.0) + EXPOSURE_ROUND_PENALTY

    if rounds:
        latest_round_event_ids = rounds[-1].get("event_ids", [])
        for event_id in latest_round_event_ids:
            streak = 1
            for round_payload in reversed(rounds[:-1]):
                if event_id not in round_payload.get("event_ids", []):
                    break
                streak += 1
            penalties[event_id] = penalties.get(event_id, 0.0) + max(0, streak - 1) * EXPOSURE_STREAK_PENALTY

    return penalties


def _record_homepage_exposure(history: dict, refresh_marker: str, exposed_event_ids: set[str]) -> None:
    if not refresh_marker or history.get("last_recorded_refresh") == refresh_marker:
        return

    history_path = _exposure_history_path()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    updated_rounds = list(history.get("rounds", []))
    updated_rounds.append(
        {
            "refresh": refresh_marker,
            "event_ids": sorted(event_id for event_id in exposed_event_ids if _is_real_source_event_id(event_id)),
        }
    )
    payload = {
        "last_recorded_refresh": refresh_marker,
        "rounds": updated_rounds[-EXPOSURE_HISTORY_MAX_ROUNDS:],
    }
    with history_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=True, indent=2)


def _card_selection_key(card: CardRecord, exposure_penalties: dict[str, float] | None = None) -> tuple[float, float, datetime, datetime]:
    penalty = (exposure_penalties or {}).get(card.event_id, 0.0)
    adjusted_score = float(card.importance_score) - penalty
    return (
        adjusted_score,
        float(card.importance_score),
        _parse_card_time(card.updated_at),
        _parse_card_time(card.published_at),
    )


def _sorted_cards(cards: list[CardRecord], exposure_penalties: dict[str, float] | None = None) -> list[CardRecord]:
    return sorted(cards, key=lambda card: _card_selection_key(card, exposure_penalties), reverse=True)


def _limit_card_payloads(cards: list[CardRecord], max_items: int) -> list[dict]:
    return [card.to_api_dict() for card in _sorted_cards(cards)[:max_items]]


def _normalize_title_tokens(title: str) -> set[str]:
    cleaned = (title or "").lower()
    for raw_phrase, normalized_phrase in PHRASE_NORMALIZATIONS.items():
        cleaned = cleaned.replace(raw_phrase, normalized_phrase)

    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    tokens = {
        TOKEN_NORMALIZATIONS.get(token, token)
        for token in cleaned.split()
        if len(token) > 1 and token not in TITLE_STOPWORDS
    }
    return tokens


def _same_event_overlap(candidate_tokens: set[str], reference_tokens: set[str]) -> float:
    shared_tokens = candidate_tokens & reference_tokens
    if len(shared_tokens) < SAME_EVENT_MIN_SHARED_TOKENS:
        return 0.0

    smaller_size = min(len(candidate_tokens), len(reference_tokens))
    if not smaller_size:
        return 0.0

    return len(shared_tokens) / smaller_size


def _same_event_strength(candidate: CardRecord, reference_token_sets: list[set[str]]) -> str | None:
    candidate_tokens = _normalize_title_tokens(candidate.headline)
    if len(candidate_tokens) < SAME_EVENT_MIN_SHARED_TOKENS:
        return None

    max_overlap = 0.0
    for reference_tokens in reference_token_sets:
        max_overlap = max(max_overlap, _same_event_overlap(candidate_tokens, reference_tokens))

    if max_overlap >= STRONG_SAME_EVENT_OVERLAP_THRESHOLD:
        return "strong"
    if max_overlap >= MODERATE_SAME_EVENT_OVERLAP_THRESHOLD:
        return "moderate"
    return None


def _select_cards_with_suppression(
    cards: list[CardRecord],
    max_items: int,
    blocked_ids: set[str] | None = None,
    reference_token_sets: list[set[str]] | None = None,
    topic_soft_caps: dict[str, int] | None = None,
    exposure_penalties: dict[str, float] | None = None,
) -> list[CardRecord]:
    sorted_cards = _sorted_cards(cards, exposure_penalties)
    selected_cards: list[CardRecord] = []
    selected_ids = set(blocked_ids or set())
    selected_token_sets = list(reference_token_sets or [])
    selected_topic_counts: dict[str, int] = {}

    def can_take(card: CardRecord, allowed_strengths: set[str | None], enforce_topic_caps: bool) -> bool:
        if card.event_id in selected_ids:
            return False
        if enforce_topic_caps and topic_soft_caps:
            topic_limit = topic_soft_caps.get(card.topic)
            if topic_limit is not None and selected_topic_counts.get(card.topic, 0) >= topic_limit:
                return False
        return _same_event_strength(card, selected_token_sets) in allowed_strengths

    def add_card(card: CardRecord) -> None:
        selected_cards.append(card)
        selected_ids.add(card.event_id)
        selected_token_sets.append(_normalize_title_tokens(card.headline))
        selected_topic_counts[card.topic] = selected_topic_counts.get(card.topic, 0) + 1

    selection_passes = (
        ({"exact_only": False, "allowed_strengths": {None}, "enforce_topic_caps": True}),
        ({"exact_only": False, "allowed_strengths": {None}, "enforce_topic_caps": False}),
        ({"exact_only": False, "allowed_strengths": {None, "moderate"}, "enforce_topic_caps": False}),
        ({"exact_only": True, "allowed_strengths": {None, "moderate", "strong"}, "enforce_topic_caps": False}),
    )

    for selection_pass in selection_passes:
        for card in sorted_cards:
            if card.event_id in selected_ids:
                continue
            if selection_pass["exact_only"]:
                add_card(card)
            elif can_take(card, selection_pass["allowed_strengths"], selection_pass["enforce_topic_caps"]):
                add_card(card)
            if len(selected_cards) >= max_items:
                return selected_cards

    return selected_cards


def _select_top_stories_with_guardrail(
    cards: list[CardRecord],
    exposure_penalties: dict[str, float],
) -> list[CardRecord]:
    reserved_cards: list[CardRecord] = []
    reserved_ids: set[str] = set()
    reserved_token_sets: list[set[str]] = []

    # Try to keep at least one strong economy/business card visible when available.
    for topic in TOP_STORY_DIVERSITY_TOPICS:
        for card in _sorted_cards([candidate for candidate in cards if candidate.topic == topic], exposure_penalties):
            if float(card.importance_score) < TOP_STORY_DIVERSITY_MIN_SCORE:
                continue
            if card.event_id in reserved_ids:
                continue
            if _same_event_strength(card, reserved_token_sets) is not None:
                continue
            reserved_cards.append(card)
            reserved_ids.add(card.event_id)
            reserved_token_sets.append(_normalize_title_tokens(card.headline))
            break

    remaining_cards = [card for card in cards if card.event_id not in reserved_ids]
    filled_cards = _select_cards_with_suppression(
        remaining_cards,
        max(0, MAX_TOP_STORIES - len(reserved_cards)),
        blocked_ids=reserved_ids,
        reference_token_sets=reserved_token_sets,
        topic_soft_caps=TOP_STORY_TOPIC_SOFT_CAPS,
        exposure_penalties=exposure_penalties,
    )

    return _sorted_cards(reserved_cards + filled_cards, exposure_penalties)[:MAX_TOP_STORIES]


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
    exposure_history = _load_exposure_history()
    exposure_penalties = _build_exposure_penalties(exposure_history)
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

    selected_top_stories = _select_top_stories_with_guardrail(top_story_cards, exposure_penalties)
    top_story_ids = {card.event_id for card in selected_top_stories}
    top_story_tokens = [_normalize_title_tokens(card.headline) for card in selected_top_stories]

    top_stories = [card.to_api_dict() for card in selected_top_stories]
    top_stories = enrich_top_stories_with_llm_explanations(top_stories, str(meta.get("last_updated", "")))
    watchlist = [
        card.to_api_dict()
        for card in _select_cards_with_suppression(
            watchlist_cards,
            MAX_WATCHLIST,
            blocked_ids=top_story_ids,
            reference_token_sets=top_story_tokens,
            exposure_penalties=exposure_penalties,
        )
    ]
    limited_region = {
        name: [
            card.to_api_dict()
            for card in _select_cards_with_suppression(
                region_cards,
                MAX_REGION_STORIES,
                blocked_ids=top_story_ids,
                reference_token_sets=top_story_tokens,
                exposure_penalties=exposure_penalties,
            )
        ]
        for name, region_cards in by_region.items()
    }
    limited_topic = {
        name: [
            card.to_api_dict()
            for card in _select_cards_with_suppression(
                topic_cards,
                MAX_TOPIC_STORIES,
                blocked_ids=top_story_ids,
                reference_token_sets=top_story_tokens,
                exposure_penalties=exposure_penalties,
            )
        ]
        for name, topic_cards in by_topic.items()
    }

    exposed_event_ids = top_story_ids | {item["event_id"] for item in watchlist}
    for bucket_items in limited_region.values():
        exposed_event_ids.update(item["event_id"] for item in bucket_items)
    for bucket_items in limited_topic.values():
        exposed_event_ids.update(item["event_id"] for item in bucket_items)
    _record_homepage_exposure(exposure_history, str(meta.get("last_updated", "")), exposed_event_ids)

    return {
        "meta": meta,
        "top_stories": top_stories,
        "by_region": limited_region,
        "by_topic": limited_topic,
        "watchlist": watchlist,
    }
