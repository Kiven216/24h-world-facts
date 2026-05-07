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
MAX_DEBUG_SUPPRESSED = 50
MAX_DEBUG_SUPPRESSED_PER_BUCKET = 15
TOP_STORY_MIN_MODERATE_FALLBACK_COUNT = 6
SAME_EVENT_MIN_SHARED_TOKENS = 3
EVENT_SIGNATURE_SUMMARY_TOKEN_LIMIT = 20
EVENT_SIGNATURE_STRONG_TIME_WINDOW_HOURS = 18
EVENT_SIGNATURE_MODERATE_TIME_WINDOW_HOURS = 26
EVENT_SIGNATURE_MIN_SHARED_ANCHORS = 2
EVENT_SIGNATURE_MIN_SHARED_WEAK_ANCHORS = 2
MODERATE_SAME_EVENT_OVERLAP_THRESHOLD = 0.38
STRONG_SAME_EVENT_OVERLAP_THRESHOLD = 0.6
TOP_STORY_TOPIC_SOFT_CAPS = {
    "Conflict / Security": 2,
    "Policy / Politics": 2,
}
TOP_STORY_TOPIC_SOFT_FLOORS = {
    "Economy / Markets": 1,
    "Business / Tech / Industry": 1,
}
TOP_STORY_DIVERSITY_BOOSTS = {
    "Economy / Markets": 0.45,
    "Business / Tech / Industry": 0.35,
}
TOP_STORY_DIVERSITY_MIN_SCORE = 7.7
TOP_STORY_TOPIC_SOFT_CAP_PENALTY = 0.55
TOP_STORY_OLD_ITEM_PENALTIES = (
    (20, 0.82),
    (16, 0.55),
    (12, 0.24),
)
EXPOSURE_HISTORY_FILENAME = "homepage_exposure_history.json"
EXPOSURE_HISTORY_MAX_ROUNDS = 5
EXPOSURE_ROUND_PENALTY = 0.18
EXPOSURE_STREAK_PENALTY = 0.22
REAL_SOURCE_PREFIXES = {"bbc", "nhk", "npr", "dw"}
PHRASE_NORMALIZATIONS = {
    "artificial intelligence": "ai",
    "crude oil": "oil",
    "cargo ship": "ship",
    "oil tanker": "ship",
    "supreme court": "court",
    "strait of hormuz": "hormuz",
    "warning shots": "warning",
    "united states": "us",
    "u s": "us",
    "united kingdom": "uk",
    "european union": "eu",
    "prime minister": "pm",
    "interest rates": "rate",
    "oil prices": "oilprice",
    "stock market": "market",
}
TOKEN_NORMALIZATIONS = {
    "said": "say",
    "says": "say",
    "seized": "seize",
    "seizure": "seize",
    "seizures": "seize",
    "attacks": "attack",
    "attacked": "attack",
    "killed": "kill",
    "killing": "kill",
    "warns": "warn",
    "warning": "warn",
    "warnings": "warn",
    "sanctions": "sanction",
    "tariffs": "tariff",
    "rates": "rate",
    "elections": "election",
    "votes": "vote",
    "cuts": "cut",
    "ships": "ship",
    "vessels": "ship",
    "talks": "talk",
    "ministers": "minister",
    "governments": "government",
    "holds": "hold",
    "holding": "hold",
    "maintains": "hold",
    "maintained": "hold",
    "prices": "price",
    "surges": "surge",
    "surged": "surge",
    "soared": "surge",
    "soaring": "surge",
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
    "but",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "into",
    "is",
    "it",
    "latest",
    "live",
    "new",
    "of",
    "on",
    "or",
    "over",
    "says",
    "that",
    "the",
    "their",
    "to",
    "up",
    "what",
    "why",
    "with",
}
STRONG_EVENT_ANCHORS = {
    "altman",
    "boj",
    "chip",
    "doj",
    "ecb",
    "eu",
    "fed",
    "gaza",
    "hormuz",
    "israel",
    "musk",
    "nato",
    "openai",
    "powell",
    "semiconductor",
    "tesla",
    "trump",
    "ukraine",
}

WEAK_EVENT_ANCHORS = {
    "ai",
    "attack",
    "ceasefire",
    "court",
    "election",
    "energy",
    "government",
    "hold",
    "inflation",
    "iran",
    "market",
    "merger",
    "minister",
    "oil",
    "oilprice",
    "rate",
    "sanction",
    "ship",
    "surge",
    "tariff",
    "trade",
    "war",
}

EVENT_ANCHOR_TOKENS = STRONG_EVENT_ANCHORS | WEAK_EVENT_ANCHORS
EVENT_ACTION_TOKENS = {
    "approve",
    "arrest",
    "back",
    "ban",
    "bid",
    "block",
    "buy",
    "cut",
    "drop",
    "file",
    "fire",
    "gaffe",
    "halt",
    "hold",
    "impose",
    "jail",
    "keep",
    "launch",
    "move",
    "pause",
    "pave",
    "raise",
    "resume",
    "rule",
    "sell",
    "shift",
    "show",
    "slip",
    "soar",
    "strike",
    "sue",
    "support",
    "suspend",
    "takeover",
    "test",
    "warn",
}


def _blank_buckets(names: list[str]) -> dict[str, list[dict]]:
    return {name: [] for name in names}


def _source_label(card: CardRecord) -> str:
    if not card.source_list:
        return ""
    return card.source_list[0]


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


def _hours_since_published(card: CardRecord, reference_time: datetime) -> float:
    published_at = _parse_card_time(card.published_at)
    return max(0.0, (reference_time - published_at).total_seconds() / 3600)


def _top_story_old_item_penalty(card: CardRecord, reference_time: datetime) -> float:
    age_hours = _hours_since_published(card, reference_time)
    for minimum_hours, penalty in TOP_STORY_OLD_ITEM_PENALTIES:
        if age_hours >= minimum_hours:
            return penalty
    return 0.0


def _top_story_adjusted_score(
    card: CardRecord,
    selected_topic_counts: dict[str, int],
    exposure_penalties: dict[str, float],
    reference_time: datetime,
) -> float:
    score = float(card.importance_score)
    score -= exposure_penalties.get(card.event_id, 0.0)
    score -= _top_story_old_item_penalty(card, reference_time)

    topic_floor = TOP_STORY_TOPIC_SOFT_FLOORS.get(card.topic)
    if (
        topic_floor is not None
        and selected_topic_counts.get(card.topic, 0) < topic_floor
        and float(card.importance_score) >= TOP_STORY_DIVERSITY_MIN_SCORE
    ):
        score += TOP_STORY_DIVERSITY_BOOSTS.get(card.topic, 0.0)

    topic_cap = TOP_STORY_TOPIC_SOFT_CAPS.get(card.topic)
    if topic_cap is not None and selected_topic_counts.get(card.topic, 0) >= topic_cap:
        overflow = selected_topic_counts.get(card.topic, 0) - topic_cap + 1
        score -= TOP_STORY_TOPIC_SOFT_CAP_PENALTY * overflow

    return score


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


def _normalize_event_tokens(text: str, max_tokens: int | None = None) -> list[str]:
    cleaned = (text or "").lower()
    for raw_phrase, normalized_phrase in PHRASE_NORMALIZATIONS.items():
        cleaned = cleaned.replace(raw_phrase, normalized_phrase)

    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    tokens = []
    for token in cleaned.split():
        normalized = TOKEN_NORMALIZATIONS.get(token, token)
        if len(normalized) <= 1 or normalized in TITLE_STOPWORDS:
            continue
        tokens.append(normalized)
        if max_tokens is not None and len(tokens) >= max_tokens:
            break
    return tokens


def _topic_event_group(topic: str) -> str:
    if topic in {"Economy / Markets", "Business / Tech / Industry"}:
        return "economy-business"
    if topic in {"Policy / Politics", "Conflict / Security"}:
        return "policy-conflict"
    return topic


def _regions_are_compatible(
    candidate_region: str,
    reference_region: str,
    topic_group: str = "",
    shared_strong_anchor_count: int = 0,
    headline_overlap: float = 0.0,
) -> bool:
    if candidate_region == reference_region:
        return True
    if "Global Markets" not in {candidate_region, reference_region}:
        return False
    if topic_group == "economy-business":
        return True
    return shared_strong_anchor_count >= 1 or headline_overlap >= STRONG_SAME_EVENT_OVERLAP_THRESHOLD


def _topics_are_compatible(candidate_topic: str, reference_topic: str) -> bool:
    if candidate_topic == reference_topic:
        return True
    return _topic_event_group(candidate_topic) == _topic_event_group(reference_topic)


def _build_event_signature(card: CardRecord) -> dict:
    headline_tokens = _normalize_event_tokens(card.headline)
    summary_tokens = _normalize_event_tokens(card.summary, EVENT_SIGNATURE_SUMMARY_TOKEN_LIMIT)
    signature_tokens = set(headline_tokens) | set(summary_tokens)
    anchor_tokens = sorted(token for token in signature_tokens if token in EVENT_ANCHOR_TOKENS)
    strong_anchor_tokens = sorted(token for token in signature_tokens if token in STRONG_EVENT_ANCHORS)
    weak_anchor_tokens = sorted(token for token in signature_tokens if token in WEAK_EVENT_ANCHORS)
    headline_anchor_tokens = sorted(token for token in headline_tokens if token in EVENT_ANCHOR_TOKENS)
    summary_anchor_tokens = sorted(token for token in summary_tokens if token in EVENT_ANCHOR_TOKENS)
    headline_strong_anchor_tokens = sorted(token for token in headline_tokens if token in STRONG_EVENT_ANCHORS)
    headline_weak_anchor_tokens = sorted(token for token in headline_tokens if token in WEAK_EVENT_ANCHORS)
    headline_action_tokens = sorted(token for token in headline_tokens if token in EVENT_ACTION_TOKENS)
    event_key_strength = ""
    key_basis: list[str] = []
    if headline_strong_anchor_tokens and headline_action_tokens:
        key_basis = (headline_strong_anchor_tokens[:2] + headline_action_tokens[:1])[:3]
        event_key_strength = "strong"
    elif len(headline_weak_anchor_tokens) >= 2 and headline_action_tokens:
        key_basis = (headline_weak_anchor_tokens[:2] + headline_action_tokens[:1])[:3]
        event_key_strength = "weak"
    published_at = _parse_card_time(card.published_at)
    event_key = (
        f"{_topic_event_group(card.topic)}|{card.region}|{published_at.date().isoformat()}|{'-'.join(key_basis)}"
        if key_basis
        else ""
    )
    return {
        "event_id": card.event_id,
        "source": _source_label(card),
        "headline": card.headline,
        "score": float(card.importance_score),
        "headline_tokens": set(headline_tokens),
        "summary_tokens": set(summary_tokens),
        "signature_tokens": signature_tokens,
        "anchor_tokens": set(anchor_tokens),
        "strong_anchor_tokens": set(strong_anchor_tokens),
        "weak_anchor_tokens": set(weak_anchor_tokens),
        "headline_anchor_tokens": set(headline_anchor_tokens),
        "summary_anchor_tokens": set(summary_anchor_tokens),
        "headline_strong_anchor_tokens": set(headline_strong_anchor_tokens),
        "headline_weak_anchor_tokens": set(headline_weak_anchor_tokens),
        "headline_action_tokens": set(headline_action_tokens),
        "topic": card.topic,
        "region": card.region,
        "published_at": published_at,
        "event_key": event_key,
        "event_key_strength": event_key_strength,
    }


def _event_signatures_from_cards(cards: list[CardRecord]) -> list[dict]:
    return [_build_event_signature(card) for card in cards]


def _build_debug_state() -> dict:
    return {
        "suppressed": [],
        "suppressed_by_bucket": {},
        "strength_counts": {"strong_same_event": 0, "moderate_same_event": 0},
        "recorded_keys": set(),
    }


def _debug_story_entry(card: CardRecord, signature: dict | None = None) -> dict:
    resolved_signature = signature or _build_event_signature(card)
    return {
        "event_id": card.event_id,
        "source": _source_label(card),
        "headline": card.headline,
        "topic": card.topic,
        "score": float(card.importance_score),
        "event_key": resolved_signature.get("event_key", ""),
        "anchors": sorted(resolved_signature.get("anchor_tokens", [])),
    }


def _debug_signature_entry(signature: dict) -> dict:
    return {
        "event_id": signature.get("event_id", ""),
        "source": signature.get("source", ""),
        "headline": signature.get("headline", ""),
        "topic": signature.get("topic", ""),
        "score": float(signature.get("score", 0.0)),
        "event_key": signature.get("event_key", ""),
        "anchors": sorted(signature.get("anchor_tokens", [])),
    }


def _record_suppressed_candidate(
    debug_state: dict | None,
    bucket: str,
    candidate: CardRecord,
    candidate_signature: dict,
    match: dict | None,
) -> None:
    if not debug_state or not match or match.get("match_class") not in {"strong_same_event", "moderate_same_event"}:
        return
    reference_signature = match["reference_signature"]
    record_key = (bucket, candidate.event_id, reference_signature.get("event_id", ""), match["match_class"])
    if record_key in debug_state["recorded_keys"]:
        return
    if len(debug_state["suppressed"]) >= MAX_DEBUG_SUPPRESSED:
        return
    bucket_count = debug_state["suppressed_by_bucket"].get(bucket, 0)
    if bucket_count >= MAX_DEBUG_SUPPRESSED_PER_BUCKET:
        return

    shared_anchors = sorted(candidate_signature["anchor_tokens"] & reference_signature["anchor_tokens"])
    debug_state["suppressed"].append(
        {
            "bucket": bucket,
            "candidate": _debug_story_entry(candidate, candidate_signature),
            "matched_reference": _debug_signature_entry(reference_signature),
            "reason": match["match_class"],
            "same_event_strength": match["same_event_strength"],
            "match_class": match["match_class"],
            "match_rule": match.get("match_rule", ""),
            "action": "suppressed",
            "shared_anchors": shared_anchors,
            "event_key": candidate_signature.get("event_key", ""),
        }
    )
    debug_state["recorded_keys"].add(record_key)
    debug_state["suppressed_by_bucket"][bucket] = bucket_count + 1
    debug_state["strength_counts"][match["match_class"]] = debug_state["strength_counts"].get(match["match_class"], 0) + 1


def _finalize_debug_suppression_actions(debug_state: dict | None, selected_event_ids: set[str]) -> dict[str, int]:
    if not debug_state:
        return {
            "suppressed": 0,
            "selected_after_fallback": 0,
            "strong_selected_after_fallback": 0,
            "moderate_selected_after_fallback": 0,
        }

    counts = {
        "suppressed": 0,
        "selected_after_fallback": 0,
        "strong_selected_after_fallback": 0,
        "moderate_selected_after_fallback": 0,
    }
    for record in debug_state["suppressed"]:
        candidate_event_id = record.get("candidate", {}).get("event_id", "")
        if candidate_event_id and candidate_event_id in selected_event_ids:
            record["action"] = "selected_after_fallback"
            counts["selected_after_fallback"] += 1
            if record.get("match_class") == "strong_same_event":
                counts["strong_selected_after_fallback"] += 1
            elif record.get("match_class") == "moderate_same_event":
                counts["moderate_selected_after_fallback"] += 1
        else:
            record["action"] = "suppressed"
            counts["suppressed"] += 1
    return counts


def _count_cards_by_source(cards: list[CardRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for card in cards:
        source = _source_label(card) or "Unknown"
        counts[source] = counts.get(source, 0) + 1
    return counts


def _same_event_overlap(candidate_tokens: set[str], reference_tokens: set[str]) -> float:
    shared_tokens = candidate_tokens & reference_tokens
    if len(shared_tokens) < SAME_EVENT_MIN_SHARED_TOKENS:
        return 0.0

    smaller_size = min(len(candidate_tokens), len(reference_tokens))
    if not smaller_size:
        return 0.0

    return len(shared_tokens) / smaller_size


def _hours_between_signatures(candidate_signature: dict, reference_signature: dict) -> float:
    return abs((candidate_signature["published_at"] - reference_signature["published_at"]).total_seconds()) / 3600


def _cards_share_event_key(candidate_signature: dict, reference_signature: dict) -> bool:
    if not candidate_signature["event_key"] or not reference_signature["event_key"]:
        return False
    if candidate_signature["event_key"] != reference_signature["event_key"]:
        return False
    if not _topics_are_compatible(candidate_signature["topic"], reference_signature["topic"]):
        return False
    return _hours_between_signatures(candidate_signature, reference_signature) <= EVENT_SIGNATURE_MODERATE_TIME_WINDOW_HOURS


def _same_event_match(candidate: CardRecord, reference_signatures: list[dict]) -> dict | None:
    candidate_signature = _build_event_signature(candidate)
    candidate_headline_tokens = candidate_signature["headline_tokens"]
    candidate_signature_tokens = candidate_signature["signature_tokens"]
    if len(candidate_signature_tokens) < SAME_EVENT_MIN_SHARED_TOKENS:
        return None

    best_moderate_match: dict | None = None
    best_moderate_score = (0.0, 0.0, 0)
    best_related_theme_match: dict | None = None
    best_related_theme_score = (0.0, 0)

    for reference_signature in reference_signatures:
        if not _topics_are_compatible(candidate_signature["topic"], reference_signature["topic"]):
            continue

        headline_overlap = _same_event_overlap(candidate_headline_tokens, reference_signature["headline_tokens"])
        signature_overlap = _same_event_overlap(candidate_signature_tokens, reference_signature["signature_tokens"])
        shared_strong_anchors = candidate_signature["strong_anchor_tokens"] & reference_signature["strong_anchor_tokens"]
        shared_weak_anchors = candidate_signature["weak_anchor_tokens"] & reference_signature["weak_anchor_tokens"]
        shared_headline_strong_anchors = candidate_signature["headline_strong_anchor_tokens"] & reference_signature["headline_strong_anchor_tokens"]
        shared_headline_weak_anchors = candidate_signature["headline_weak_anchor_tokens"] & reference_signature["headline_weak_anchor_tokens"]
        shared_headline_actions = candidate_signature["headline_action_tokens"] & reference_signature["headline_action_tokens"]
        shared_summary_only_anchors = (
            (candidate_signature["summary_anchor_tokens"] & reference_signature["summary_anchor_tokens"])
            - shared_headline_strong_anchors
            - shared_headline_weak_anchors
        )
        shared_anchor_total = len(shared_strong_anchors) + len(shared_weak_anchors)
        topic_group = _topic_event_group(candidate_signature["topic"])
        time_gap_hours = _hours_between_signatures(candidate_signature, reference_signature)
        regions_compatible = _regions_are_compatible(
            candidate_signature["region"],
            reference_signature["region"],
            topic_group=topic_group,
            shared_strong_anchor_count=len(shared_headline_strong_anchors),
            headline_overlap=headline_overlap,
        )
        shared_event_key = _cards_share_event_key(candidate_signature, reference_signature)

        if (
            shared_event_key
            and candidate_signature["event_key_strength"] == "strong"
            and reference_signature.get("event_key_strength") == "strong"
            and regions_compatible
            and (
                len(shared_headline_strong_anchors) >= 1
                or (
                    len(shared_headline_weak_anchors) >= EVENT_SIGNATURE_MIN_SHARED_WEAK_ANCHORS
                    and len(shared_headline_actions) >= 1
                )
                or headline_overlap >= STRONG_SAME_EVENT_OVERLAP_THRESHOLD
            )
        ):
            return {
                "match_class": "strong_same_event",
                "same_event_strength": "strong",
                "match_rule": "shared_event_key_strong",
                "reference_signature": reference_signature,
                "candidate_signature": candidate_signature,
                "headline_overlap": headline_overlap,
                "signature_overlap": signature_overlap,
                "shared_anchors": sorted(candidate_signature["anchor_tokens"] & reference_signature["anchor_tokens"]),
            }

        if (
            regions_compatible
            and time_gap_hours <= EVENT_SIGNATURE_STRONG_TIME_WINDOW_HOURS
            and len(shared_headline_strong_anchors) >= 1
            and (
                headline_overlap >= 0.34
                or (
                    headline_overlap >= 0.2
                    and signature_overlap >= STRONG_SAME_EVENT_OVERLAP_THRESHOLD
                    and len(shared_headline_actions) >= 1
                )
            )
        ):
            return {
                "match_class": "strong_same_event",
                "same_event_strength": "strong",
                "match_rule": "strong_anchor_time_region",
                "reference_signature": reference_signature,
                "candidate_signature": candidate_signature,
                "headline_overlap": headline_overlap,
                "signature_overlap": signature_overlap,
                "shared_anchors": sorted(candidate_signature["anchor_tokens"] & reference_signature["anchor_tokens"]),
            }

        if (
            candidate_signature["topic"] == reference_signature["topic"]
            and regions_compatible
            and time_gap_hours <= EVENT_SIGNATURE_STRONG_TIME_WINDOW_HOURS
            and len(shared_headline_weak_anchors) >= EVENT_SIGNATURE_MIN_SHARED_WEAK_ANCHORS
            and len(shared_headline_actions) >= 1
            and headline_overlap >= STRONG_SAME_EVENT_OVERLAP_THRESHOLD
        ):
            return {
                "match_class": "strong_same_event",
                "same_event_strength": "strong",
                "match_rule": "strong_headline_overlap",
                "reference_signature": reference_signature,
                "candidate_signature": candidate_signature,
                "headline_overlap": headline_overlap,
                "signature_overlap": signature_overlap,
                "shared_anchors": sorted(candidate_signature["anchor_tokens"] & reference_signature["anchor_tokens"]),
            }

        if (
            shared_event_key
            and regions_compatible
            and (
                candidate_signature["event_key_strength"] == "strong"
                or reference_signature.get("event_key_strength") == "strong"
                or len(shared_headline_strong_anchors) >= 1
                or (
                    len(shared_headline_weak_anchors) >= EVENT_SIGNATURE_MIN_SHARED_WEAK_ANCHORS
                    and headline_overlap >= 0.26
                )
            )
        ):
            moderate_match = {
                "match_class": "moderate_same_event",
                "same_event_strength": "moderate",
                "match_rule": "shared_event_key_moderate",
                "reference_signature": reference_signature,
                "candidate_signature": candidate_signature,
                "headline_overlap": headline_overlap,
                "signature_overlap": signature_overlap,
                "shared_anchors": sorted(candidate_signature["anchor_tokens"] & reference_signature["anchor_tokens"]),
            }
        elif (
            regions_compatible
            and time_gap_hours <= EVENT_SIGNATURE_MODERATE_TIME_WINDOW_HOURS
            and (
                (len(shared_headline_strong_anchors) >= 1 and (headline_overlap >= 0.18 or signature_overlap >= 0.26))
                or (
                    headline_overlap >= MODERATE_SAME_EVENT_OVERLAP_THRESHOLD
                    or (
                        len(shared_headline_weak_anchors) >= EVENT_SIGNATURE_MIN_SHARED_WEAK_ANCHORS
                        and signature_overlap >= 0.34
                        and candidate_signature["topic"] == reference_signature["topic"]
                    )
                )
            )
        ):
            moderate_match = {
                "match_class": "moderate_same_event",
                "same_event_strength": "moderate",
                "match_rule": "moderate_anchor_overlap" if len(shared_headline_strong_anchors) >= 1 else "moderate_signature_overlap",
                "reference_signature": reference_signature,
                "candidate_signature": candidate_signature,
                "headline_overlap": headline_overlap,
                "signature_overlap": signature_overlap,
                "shared_anchors": sorted(candidate_signature["anchor_tokens"] & reference_signature["anchor_tokens"]),
            }
        else:
            moderate_match = None

        if moderate_match:
            moderate_score = (
                moderate_match["headline_overlap"],
                moderate_match["signature_overlap"],
                len(shared_headline_strong_anchors),
            )
            is_better_match = best_moderate_match is None or moderate_score > best_moderate_score
            if is_better_match:
                best_moderate_match = moderate_match
                best_moderate_score = moderate_score
            continue

        related_theme_match = None
        if (
            shared_summary_only_anchors
            or (len(shared_weak_anchors) >= 1 and len(shared_headline_weak_anchors) == 0)
            or (headline_overlap < 0.2 and signature_overlap >= 0.26)
            or (
                len(shared_headline_weak_anchors) >= 1
                and len(shared_headline_strong_anchors) == 0
                and headline_overlap < MODERATE_SAME_EVENT_OVERLAP_THRESHOLD
            )
        ):
            if shared_summary_only_anchors:
                match_rule = "summary_anchor_theme"
            elif len(shared_headline_weak_anchors) == 0 and len(shared_weak_anchors) >= 1:
                match_rule = "weak_anchor_theme"
            else:
                match_rule = "signature_theme_overlap"
            related_theme_match = {
                "match_class": "related_theme",
                "same_event_strength": "",
                "match_rule": match_rule,
                "reference_signature": reference_signature,
                "candidate_signature": candidate_signature,
                "headline_overlap": headline_overlap,
                "signature_overlap": signature_overlap,
                "shared_anchors": sorted(candidate_signature["anchor_tokens"] & reference_signature["anchor_tokens"]),
            }

        if related_theme_match:
            related_theme_score = (
                related_theme_match["signature_overlap"],
                len(shared_summary_only_anchors) + len(shared_weak_anchors),
            )
            if best_related_theme_match is None or related_theme_score > best_related_theme_score:
                best_related_theme_match = related_theme_match
                best_related_theme_score = related_theme_score

    if best_moderate_match:
        return best_moderate_match
    if best_related_theme_match:
        return best_related_theme_match
    return None


def _same_event_strength(candidate: CardRecord, reference_signatures: list[dict]) -> str | None:
    match = _same_event_match(candidate, reference_signatures)
    return match["match_class"] if match else None


def _select_cards_with_suppression(
    cards: list[CardRecord],
    max_items: int,
    blocked_ids: set[str] | None = None,
    reference_signatures: list[dict] | None = None,
    topic_soft_caps: dict[str, int] | None = None,
    exposure_penalties: dict[str, float] | None = None,
    debug_state: dict | None = None,
    bucket_name: str = "",
) -> list[CardRecord]:
    sorted_cards = _sorted_cards(cards, exposure_penalties)
    selected_cards: list[CardRecord] = []
    selected_ids = set(blocked_ids or set())
    selected_signatures = list(reference_signatures or [])
    selected_topic_counts: dict[str, int] = {}

    def can_take(card: CardRecord, allowed_classes: set[str | None], enforce_topic_caps: bool) -> tuple[bool, dict | None]:
        if card.event_id in selected_ids:
            return False, None
        if enforce_topic_caps and topic_soft_caps:
            topic_limit = topic_soft_caps.get(card.topic)
            if topic_limit is not None and selected_topic_counts.get(card.topic, 0) >= topic_limit:
                return False, None
        match = _same_event_match(card, selected_signatures)
        match_class = match["match_class"] if match else None
        return match_class in allowed_classes, match

    def add_card(card: CardRecord) -> None:
        selected_cards.append(card)
        selected_ids.add(card.event_id)
        selected_signatures.append(_build_event_signature(card))
        selected_topic_counts[card.topic] = selected_topic_counts.get(card.topic, 0) + 1

    selection_passes = (
        ({"exact_only": False, "allowed_classes": {None, "related_theme"}, "enforce_topic_caps": True}),
        ({"exact_only": False, "allowed_classes": {None, "related_theme"}, "enforce_topic_caps": False}),
        ({"exact_only": False, "allowed_classes": {None, "related_theme", "moderate_same_event"}, "enforce_topic_caps": False}),
    )

    for selection_pass in selection_passes:
        for card in sorted_cards:
            if card.event_id in selected_ids:
                continue
            can_select, match = can_take(card, selection_pass["allowed_classes"], selection_pass["enforce_topic_caps"])
            if can_select:
                add_card(card)
            elif match and selection_pass["allowed_classes"] == {None, "related_theme"}:
                _record_suppressed_candidate(
                    debug_state,
                    bucket_name,
                    card,
                    match["candidate_signature"],
                    match,
                )
            if len(selected_cards) >= max_items:
                return selected_cards

    return selected_cards


def _select_top_stories_with_guardrail(
    cards: list[CardRecord],
    exposure_penalties: dict[str, float],
    debug_state: dict | None = None,
) -> list[CardRecord]:
    if not cards:
        return []

    reference_time = datetime.now(_parse_card_time(cards[0].published_at).tzinfo)
    selected_cards: list[CardRecord] = []
    selected_ids: set[str] = set()
    selected_signatures: list[dict] = []
    selected_topic_counts: dict[str, int] = {}

    def add_card(card: CardRecord) -> None:
        selected_cards.append(card)
        selected_ids.add(card.event_id)
        selected_signatures.append(_build_event_signature(card))
        selected_topic_counts[card.topic] = selected_topic_counts.get(card.topic, 0) + 1

    selection_passes = (
        {"allowed_classes": {None, "related_theme"}, "minimum_selected_before_skip": 0},
        {"allowed_classes": {None, "related_theme", "moderate_same_event"}, "minimum_selected_before_skip": TOP_STORY_MIN_MODERATE_FALLBACK_COUNT},
    )

    for selection_pass in selection_passes:
        allowed_classes = selection_pass["allowed_classes"]
        minimum_selected_before_skip = selection_pass["minimum_selected_before_skip"]
        if len(selected_cards) >= minimum_selected_before_skip and minimum_selected_before_skip:
            continue
        while len(selected_cards) < MAX_TOP_STORIES:
            candidates = []
            for card in cards:
                if card.event_id in selected_ids:
                    continue
                match = _same_event_match(card, selected_signatures)
                match_class = match["match_class"] if match else None
                if match_class in allowed_classes:
                    candidates.append(card)
                elif match and allowed_classes == {None, "related_theme", "moderate_same_event"}:
                    _record_suppressed_candidate(
                        debug_state,
                        "top_stories",
                        card,
                        match["candidate_signature"],
                        match,
                    )
            if not candidates:
                break

            best_candidate = max(
                candidates,
                key=lambda card: (
                    _top_story_adjusted_score(card, selected_topic_counts, exposure_penalties, reference_time),
                    float(card.importance_score),
                    _parse_card_time(card.updated_at),
                    _parse_card_time(card.published_at),
                ),
            )
            add_card(best_candidate)

    return selected_cards[:MAX_TOP_STORIES]


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


def build_homepage_payload(include_debug: bool = False) -> dict:
    cards, meta = _resolve_cards_and_meta()
    exposure_history = _load_exposure_history()
    exposure_penalties = _build_exposure_penalties(exposure_history)
    debug_state = _build_debug_state() if include_debug else None
    by_region = _blank_buckets(REGION_BUCKETS)
    by_topic = _blank_buckets(TOPIC_BUCKETS)
    top_story_cards: list[CardRecord] = []
    watchlist_cards: list[CardRecord] = []
    selection_generated_at = datetime.now().astimezone().replace(microsecond=0).isoformat()

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

    selected_top_stories = _select_top_stories_with_guardrail(
        top_story_cards,
        exposure_penalties,
        debug_state=debug_state,
    )
    top_story_ids = {card.event_id for card in selected_top_stories}
    top_story_signatures = _event_signatures_from_cards(selected_top_stories)

    top_stories = [card.to_api_dict() for card in selected_top_stories]
    top_stories = enrich_top_stories_with_llm_explanations(top_stories, str(meta.get("last_updated", "")))
    downstream_blocked_ids = set(top_story_ids)
    downstream_reference_signatures = list(top_story_signatures)
    selected_topic_cards_all: list[CardRecord] = []
    selected_region_cards_all: list[CardRecord] = []

    limited_topic = {}
    for name, topic_cards in by_topic.items():
        selected_topic_cards = _select_cards_with_suppression(
            topic_cards,
            MAX_TOPIC_STORIES,
            blocked_ids=downstream_blocked_ids,
            reference_signatures=downstream_reference_signatures,
            exposure_penalties=exposure_penalties,
            debug_state=debug_state,
            bucket_name=f"by_topic:{name}",
        )
        limited_topic[name] = [card.to_api_dict() for card in selected_topic_cards]
        selected_topic_cards_all.extend(selected_topic_cards)
        downstream_blocked_ids.update(card.event_id for card in selected_topic_cards)
        downstream_reference_signatures.extend(_event_signatures_from_cards(selected_topic_cards))

    limited_region = {}
    for name, region_cards in by_region.items():
        selected_region_cards = _select_cards_with_suppression(
            region_cards,
            MAX_REGION_STORIES,
            blocked_ids=downstream_blocked_ids,
            reference_signatures=downstream_reference_signatures,
            exposure_penalties=exposure_penalties,
            debug_state=debug_state,
            bucket_name=f"by_region:{name}",
        )
        limited_region[name] = [card.to_api_dict() for card in selected_region_cards]
        selected_region_cards_all.extend(selected_region_cards)
        downstream_blocked_ids.update(card.event_id for card in selected_region_cards)
        downstream_reference_signatures.extend(_event_signatures_from_cards(selected_region_cards))

    selected_watchlist_cards = _select_cards_with_suppression(
        watchlist_cards,
        MAX_WATCHLIST,
        blocked_ids=downstream_blocked_ids,
        reference_signatures=downstream_reference_signatures,
        exposure_penalties=exposure_penalties,
        debug_state=debug_state,
        bucket_name="watchlist",
    )
    watchlist = [card.to_api_dict() for card in selected_watchlist_cards]
    final_selected_cards = selected_top_stories + selected_topic_cards_all + selected_region_cards_all + selected_watchlist_cards
    selected_cards_by_event_id = {card.event_id: card for card in final_selected_cards}

    exposed_event_ids = top_story_ids | {item["event_id"] for item in watchlist}
    for bucket_items in limited_region.values():
        exposed_event_ids.update(item["event_id"] for item in bucket_items)
    for bucket_items in limited_topic.values():
        exposed_event_ids.update(item["event_id"] for item in bucket_items)
    _record_homepage_exposure(exposure_history, str(meta.get("last_updated", "")), exposed_event_ids)

    debug_action_counts = _finalize_debug_suppression_actions(debug_state, exposed_event_ids)

    payload = {
        "meta": meta,
        "top_stories": top_stories,
        "by_region": limited_region,
        "by_topic": limited_topic,
        "watchlist": watchlist,
    }

    if include_debug and debug_state is not None:
        payload["debug"] = {
            "summary": {
                "selection_generated_at": selection_generated_at,
                "candidate_count": len(cards),
                "source_counts": _count_cards_by_source(cards),
                "selected_source_counts": _count_cards_by_source(list(selected_cards_by_event_id.values())),
                "selected_top_count": len(selected_top_stories),
                "suppressed_count": debug_action_counts["suppressed"],
                "final_suppressed_count": debug_action_counts["suppressed"],
                "selected_after_fallback_count": debug_action_counts["selected_after_fallback"],
                "strong_selected_after_fallback_count": debug_action_counts["strong_selected_after_fallback"],
                "moderate_selected_after_fallback_count": debug_action_counts["moderate_selected_after_fallback"],
                "strong_same_event_count": debug_state["strength_counts"].get("strong_same_event", 0),
                "moderate_same_event_count": debug_state["strength_counts"].get("moderate_same_event", 0),
                "suppressed_by_bucket": debug_state["suppressed_by_bucket"],
            },
            "selected_top_stories": [
                _debug_story_entry(card)
                for card in selected_top_stories
            ],
            "suppressed": debug_state["suppressed"],
        }

    return payload
