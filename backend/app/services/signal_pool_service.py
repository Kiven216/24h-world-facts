import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import email.utils
import html
from pathlib import Path
import re
from typing import Any

import feedparser
import requests

from ..config import settings


MAX_SIGNAL_POOL_ITEMS = 24
MAX_SIGNAL_POOL_TAGS = 6
MIN_SIGNAL_RELEVANCE_SCORE = 4.0
FETCH_TIMEOUT_SECONDS = 10
MIN_RAW_ITEMS_FOR_SIGNAL_FALLBACK = 20
MIN_SIGNAL_FALLBACK_ITEMS = 5
MIN_MARKET_BUCKET_SHARE_NUM = 1
MIN_MARKET_BUCKET_SHARE_DEN = 3
MAX_GEO_ENERGY_SHARE_NUM = 1
MAX_GEO_ENERGY_SHARE_DEN = 2

MARKET_PRIORITY_BUCKETS = {
    "macro_liquidity",
    "market_structure",
    "crypto_policy",
    "btc_thesis",
    "tech_ai",
}
GEO_ENERGY_BUCKETS = {"geopolitics", "energy"}

SIGNAL_SOURCE_DEFINITIONS = (
    {
        "id": "coindesk",
        "source_name": "CoinDesk",
        "enabled_attr": "enable_signal_source_coindesk",
        "feeds": ("https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",),
    },
    {
        "id": "cnbc",
        "source_name": "CNBC",
        "enabled_attr": "enable_signal_source_cnbc",
        "feeds": (
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910",
        ),
    },
    {
        "id": "oilprice",
        "source_name": "OilPrice",
        "enabled_attr": "enable_signal_source_oilprice",
        "feeds": ("https://oilprice.com/rss/main",),
    },
)

BUCKET_RULES = {
    "crypto_policy": (
        "bitcoin",
        "crypto",
        "etf",
        "regulatory",
        "sec",
        "cftc",
        "stablecoin",
        "crypto bill",
        "regulation",
        "custody",
        "exchange",
        "coinbase",
        "binance",
        "blackrock bitcoin etf",
        "spot bitcoin etf",
    ),
    "btc_thesis": (
        "bitcoin adoption",
        "institutional adoption",
        "bitcoin treasury",
        "bitcoin inflow",
        "bitcoin reserve",
        "sovereign bitcoin",
        "strategic reserve",
        "institutional bitcoin",
        "bitcoin etf inflows",
        "digital gold",
        "treasury bitcoin",
        "corporate bitcoin",
    ),
    "macro_liquidity": (
        "fed",
        "fed chair",
        "rate cut",
        "rate hike",
        "rate hold",
        "interest rate",
        "consumer sentiment",
        "consumer spending",
        "cpi",
        "treasury",
        "treasury yield",
        "treasury yields",
        "usd",
        "fomc",
        "inflation",
        "cpi",
        "earnings",
        "treasury yields",
        "dollar",
        "liquidity",
        "balance sheet",
        "jobs",
        "payrolls",
    ),
    "credit": (
        "credit stress",
        "banking stress",
        "default",
        "high yield",
        "spread",
        "bank failure",
        "commercial real estate",
        "liquidity crunch",
    ),
    "energy": (
        "oil",
        "brent",
        "crude",
        "hormuz",
        "shipping",
        "oil surge",
        "defense stocks",
        "energy shock",
        "gas prices",
        "sanctions oil",
        "opec",
    ),
    "tech_ai": (
        "chief ai officer",
        "ai officer",
        "ai boardrooms",
        "boardrooms",
        "ai governance",
        "ai strategy",
        "ai adoption",
        "enterprise adoption",
        "ai enterprise adoption",
        "ai capex",
        "data center",
        "semis",
        "gpu",
        "chips",
        "semiconductor",
        "export controls",
        "nvidia",
        "openai",
        "cloud capex",
        "ai infrastructure",
    ),
    "market_structure": (
        "market structure",
        "market",
        "stocks",
        "risk assets",
        "market rally",
        "consumer sentiment",
        "etf flows",
        "volatility",
        "liquidity",
        "stocks slide",
        "record high",
        "nasdaq",
        "equities",
        "asia markets",
        "kospi",
        "exchange outage",
        "custody",
        "clearing",
        "settlement",
        "systemic risk",
    ),
    "geopolitics": (
        "trump xi summit",
        "trump-xi summit",
        "trump xi",
        "summit",
        "iran",
        "israel",
        "ukraine",
        "russia",
        "china",
        "taiwan",
        "sanctions",
        "peace talks",
        "trade",
        "shipping",
        "war",
        "conflict",
        "oil supply",
        "trade war",
    ),
}

TRANSMISSION_RULES = {
    "btc_thesis": ("bitcoin", "btc", "etf", "reserve", "custody", "institutional"),
    "risk_appetite": (
        "volatility",
        "risk",
        "equities",
        "stocks",
        "nasdaq",
        "selloff",
        "drawdown",
        "stress",
        "risk assets",
        "consumer sentiment",
        "consumer spending",
        "gloomy",
    ),
    "liquidity": ("fed", "rate", "liquidity", "balance sheet", "treasury", "dollar"),
    "credit_stress": ("credit", "default", "spread", "bank", "failure"),
    "policy_regulation": ("regulation", "bill", "policy", "sec", "cftc", "sanction"),
    "energy_inflation": ("oil", "energy", "gas", "brent", "inflation", "shipping"),
    "ai_capex": (
        "ai",
        "gpu",
        "chip",
        "semiconductor",
        "data center",
        "cloud",
        "ai officer",
        "ai governance",
        "ai strategy",
        "enterprise adoption",
    ),
    "cross_asset": ("etf", "dollar", "yield", "equities", "commodities"),
}

STRATEGIC_COMBO_RULES = (
    (
        "geo_energy_market",
        ("iran", "hormuz", "oil", "shipping", "energy"),
        ("market", "stocks", "defense", "equities", "volatility"),
    ),
    (
        "macro_market_crypto",
        ("fed", "rate", "inflation", "yield", "yields", "dollar"),
        ("crypto", "bitcoin", "btc", "market", "equities"),
    ),
    (
        "crypto_policy",
        ("crypto", "bitcoin", "btc", "etf", "stablecoin"),
        ("coinbase", "binance", "sec", "regulation", "cftc"),
    ),
    (
        "ai_chip_cycle",
        ("ai", "chips", "chip", "data center", "semis", "nvidia"),
        ("export controls", "cloud", "infrastructure", "capex", "semiconductor"),
    ),
    (
        "trade_transmission",
        ("tariff", "trade war", "sanctions"),
        ("market", "supply chain", "inflation", "energy"),
    ),
    (
        "bitcoin_nasdaq_consumer_sentiment",
        ("bitcoin", "btc", "nasdaq", "stocks", "equities", "risk assets"),
        ("consumer", "consumers", "consumer sentiment", "consumer spending", "gloomy", "weakness"),
    ),
    (
        "ai_enterprise_adoption",
        ("ai", "artificial intelligence", "chief ai officer", "ai officer"),
        ("boardroom", "boardrooms", "governance", "strategy", "adoption", "enterprise"),
    ),
    (
        "summit_trade_transmission",
        ("trump xi summit", "trump-xi summit", "summit"),
        ("trade", "tariff", "supply chain", "markets", "stocks", "exports", "semiconductor", "chips", "sanctions", "currency", "dollar", "inflation", "oil"),
    ),
)

SUPPORTIVE_TERMS = (
    "approval",
    "approved",
    "adoption",
    "inflow",
    "launch",
    "progress",
    "eases",
    "support",
    "stimulus",
    "celebrating",
    "rally",
)

CAUTIOUS_TERMS = (
    "warning",
    "uncertain",
    "uncertainty",
    "slowdown",
    "hawkish",
    "headwind",
    "hold rates",
    "delays",
    "gloomy",
    "consumer weakness",
    "weakness",
)

RISK_TERMS = (
    "ban",
    "hack",
    "outage",
    "default",
    "failure",
    "stress",
    "attack",
    "strike",
    "conflict",
    "disruption",
    "sanctions",
    "crunch",
)

SHORT_HORIZON_TERMS = ("attack", "strike", "outage", "liquidation", "shipping warning", "oil shock")
LONG_HORIZON_TERMS = ("reserve", "adoption", "structural", "capex", "infrastructure", "regime shift")

DROP_TERMS = (
    "meme coin",
    "memecoin",
    "nft",
    "price prediction",
    "opinion",
    "celebrity",
    "lifestyle",
)

STOPWORDS = {
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
    "to",
    "with",
}


@dataclass(slots=True)
class SignalCandidate:
    id: str
    published_at: datetime
    source_name: str
    source_url: str
    title: str
    summary: str


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean_html(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_text(value: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", _clean_html(value).lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _has_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase.lower())
    if " " in phrase:
        return bool(re.search(rf"\b{escaped}\b", text))
    return bool(re.search(rf"\b{escaped}\b", text))


def _matches_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_has_phrase(text, phrase) for phrase in phrases)


def _count_matches(text: str, phrases: tuple[str, ...]) -> int:
    return sum(1 for phrase in phrases if _has_phrase(text, phrase))


def _source_enabled(source_definition: dict[str, Any]) -> bool:
    return bool(getattr(settings, source_definition["enabled_attr"], False))


def _parse_datetime_from_entry(entry: dict[str, Any]) -> datetime:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc)

    for key in ("published", "updated"):
        raw_value = str(entry.get(key, "")).strip()
        if not raw_value:
            continue
        try:
            return datetime.fromisoformat(raw_value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            pass
        try:
            parsed_dt = email.utils.parsedate_to_datetime(raw_value)
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
            return parsed_dt.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue

    return _now_utc()


def _normalize_candidate(source_name: str, entry: dict[str, Any]) -> SignalCandidate | None:
    title = _clean_html(str(entry.get("title", "")))
    source_url = str(entry.get("link", "")).strip()
    if not title or not source_url:
        return None
    summary = _clean_html(str(entry.get("summary", "") or entry.get("description", "")))
    published_at = _parse_datetime_from_entry(entry)
    guid = str(entry.get("id", "") or entry.get("guid", "")).strip()
    stable_id = guid or source_url
    return SignalCandidate(
        id=f"{source_name.lower()}:{stable_id}",
        published_at=published_at,
        source_name=source_name,
        source_url=source_url,
        title=title,
        summary=summary,
    )


def _fetch_feed_entries(feed_url: str) -> tuple[list[Any], list[str]]:
    notes: list[str] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; 24HWorldFacts/1.0; +https://24h.worthylab.tech)",
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }
    try:
        response = requests.get(feed_url, headers=headers, timeout=FETCH_TIMEOUT_SECONDS)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if getattr(parsed, "bozo", False) and getattr(parsed, "bozo_exception", None):
            notes.append(f"parse_note:{parsed.bozo_exception}")
        return list(parsed.entries), notes
    except Exception as exc:
        notes.append(f"requests_failed:{exc}")

    try:
        fallback_parsed = feedparser.parse(feed_url)
        if getattr(fallback_parsed, "bozo", False) and getattr(fallback_parsed, "bozo_exception", None):
            notes.append(f"fallback_parse_note:{fallback_parsed.bozo_exception}")
        if getattr(fallback_parsed, "entries", None):
            notes.append("fallback_feedparser_url_ok")
            return list(fallback_parsed.entries), notes
        notes.append("fallback_feedparser_url_empty")
    except Exception as exc:
        notes.append(f"fallback_feedparser_url_failed:{exc}")
    return [], notes


def _determine_bucket(text: str) -> tuple[str, list[str]]:
    best_bucket = ""
    best_hits: list[str] = []
    for bucket, terms in BUCKET_RULES.items():
        hits = [term for term in terms if _has_phrase(text, term)]
        if len(hits) > len(best_hits):
            best_bucket = bucket
            best_hits = hits
    return best_bucket, best_hits


def _strategic_combo_hits(text: str) -> list[str]:
    hits: list[str] = []
    for rule_name, left_terms, right_terms in STRATEGIC_COMBO_RULES:
        if _matches_any(text, left_terms) and _matches_any(text, right_terms):
            hits.append(rule_name)
    return hits


def _fallback_bucket_from_combo(combo_hits: list[str]) -> str:
    if not combo_hits:
        return ""
    combo_to_bucket = {
        "geo_energy_market": "energy",
        "macro_market_crypto": "macro_liquidity",
        "crypto_policy": "crypto_policy",
        "ai_chip_cycle": "tech_ai",
        "trade_transmission": "market_structure",
        "bitcoin_nasdaq_consumer_sentiment": "market_structure",
        "ai_enterprise_adoption": "tech_ai",
        "summit_trade_transmission": "market_structure",
    }
    for combo in combo_hits:
        mapped = combo_to_bucket.get(combo, "")
        if mapped:
            return mapped
    return ""


def _determine_signal_type(bucket: str, text: str) -> str:
    if bucket == "crypto_policy":
        return "regulation" if _matches_any(text, ("regulation", "sec", "cftc", "bill")) else "policy"
    if bucket == "btc_thesis":
        return "adoption"
    if bucket == "macro_liquidity":
        return "liquidity"
    if bucket == "credit":
        return "event_risk"
    if bucket == "energy":
        return "energy_shock"
    if bucket == "tech_ai":
        if _matches_any(text, ("ai officer", "chief ai officer", "ai governance", "ai strategy", "enterprise adoption", "adoption")):
            return "adoption"
        return "news"
    if bucket == "market_structure":
        return "market_structure"
    if bucket == "geopolitics":
        if _matches_any(text, ("trade", "tariff", "sanctions", "policy")):
            return "policy"
        return "event_risk"
    return "news"


def _determine_direction(text: str) -> str:
    supportive_hits = _count_matches(text, SUPPORTIVE_TERMS)
    cautious_hits = _count_matches(text, CAUTIOUS_TERMS)
    risk_hits = _count_matches(text, RISK_TERMS)

    if supportive_hits and risk_hits:
        return "mixed"
    if risk_hits >= max(1, supportive_hits):
        return "risk"
    if cautious_hits and cautious_hits >= supportive_hits:
        return "cautious"
    if supportive_hits:
        return "supportive"
    return "neutral"


def _determine_horizon(text: str, bucket: str) -> str:
    if _matches_any(text, SHORT_HORIZON_TERMS):
        return "short"
    if _matches_any(text, LONG_HORIZON_TERMS):
        return "long"
    if bucket in {"btc_thesis", "tech_ai"}:
        return "long"
    return "medium"


def _determine_confidence(bucket_match_count: int, transmission_hits: int, relevance_score: float) -> str:
    if bucket_match_count >= 2 and transmission_hits >= 2 and relevance_score >= 8.2:
        return "high"
    if bucket_match_count >= 1 and transmission_hits >= 1 and relevance_score >= 6.2:
        return "medium"
    return "low"


def _collect_tags(text: str, bucket: str, matched_bucket_terms: list[str]) -> list[str]:
    ordered_tags: list[str] = []
    if bucket:
        ordered_tags.append(bucket)
    for term in matched_bucket_terms:
        normalized = term.replace(" ", "_")
        if normalized not in ordered_tags:
            ordered_tags.append(normalized)
    for label, terms in TRANSMISSION_RULES.items():
        if _matches_any(text, terms) and label not in ordered_tags:
            ordered_tags.append(label)
    return ordered_tags[:MAX_SIGNAL_POOL_TAGS]


def _calculate_relevance(
    bucket: str,
    bucket_match_count: int,
    transmission_hits: int,
    combo_hit_count: int,
    text: str,
) -> float:
    score = 0.0
    score += min(bucket_match_count, 3) * 1.6
    score += min(transmission_hits, 4) * 1.1
    score += min(combo_hit_count, 2) * 1.3
    if bucket in MARKET_PRIORITY_BUCKETS:
        score += 0.5
    if _matches_any(text, ("bitcoin etf", "rate cut", "rate hold", "oil supply", "export controls", "stablecoin", "stocks slide")):
        score += 0.6
    return round(min(score, 10.0), 1)


def _build_dedup_key(bucket: str, text: str, published_at: datetime) -> str:
    tokens = [token for token in text.split() if len(token) > 2 and token not in STOPWORDS]
    anchors: list[str] = []
    whitelist = {
        "bitcoin",
        "btc",
        "etf",
        "fed",
        "rate",
        "inflation",
        "oil",
        "brent",
        "openai",
        "chip",
        "semiconductor",
        "sanctions",
        "stablecoin",
        "liquidity",
    }
    for token in tokens:
        if token in anchors:
            continue
        if token in whitelist:
            anchors.append(token)
        if len(anchors) >= 3:
            break
    if not anchors:
        anchors = tokens[:3]
    return f"{bucket}|{'-'.join(anchors)}|{published_at.date().isoformat()}"


def _why_it_matters(bucket: str, direction: str, horizon: str, tags: list[str]) -> str:
    tag_hint = ", ".join(tags[:2]) if tags else "strategic transmission"
    return (
        f"This may shift {bucket.replace('_', ' ')} expectations through {tag_hint}. "
        f"Current read is {direction} with a {horizon}-term horizon."
    )


def _select_with_bucket_balance(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if not candidates or limit <= 0:
        return []

    ordered = sorted(candidates, key=lambda item: (item["relevance_score"], item["published_at"]), reverse=True)
    final_limit = min(limit, len(ordered))
    min_market = (final_limit * MIN_MARKET_BUCKET_SHARE_NUM + MIN_MARKET_BUCKET_SHARE_DEN - 1) // MIN_MARKET_BUCKET_SHARE_DEN
    max_geo_energy = (final_limit * MAX_GEO_ENERGY_SHARE_NUM) // MAX_GEO_ENERGY_SHARE_DEN

    selected_ids: set[str] = set()
    selected: list[dict[str, Any]] = []
    geo_energy_count = 0
    market_count = 0
    deferred_geo_energy: list[dict[str, Any]] = []

    # Pass 1: ensure market-oriented buckets get a fair minimum share.
    for item in ordered:
        if len(selected) >= final_limit or market_count >= min_market:
            break
        if item["bucket"] not in MARKET_PRIORITY_BUCKETS:
            continue
        selected.append(item)
        selected_ids.add(item["id"])
        market_count += 1
        if item["bucket"] in GEO_ENERGY_BUCKETS:
            geo_energy_count += 1

    # Pass 2: fill remaining slots by score, with a soft cap on geo/energy concentration.
    for item in ordered:
        if len(selected) >= final_limit:
            break
        if item["id"] in selected_ids:
            continue
        if item["bucket"] in GEO_ENERGY_BUCKETS and geo_energy_count >= max_geo_energy:
            deferred_geo_energy.append(item)
            continue
        selected.append(item)
        selected_ids.add(item["id"])
        if item["bucket"] in GEO_ENERGY_BUCKETS:
            geo_energy_count += 1
        if item["bucket"] in MARKET_PRIORITY_BUCKETS:
            market_count += 1

    # Pass 3 fallback: if we still have empty slots, allow deferred geo/energy items.
    if len(selected) < final_limit:
        for item in deferred_geo_energy:
            if len(selected) >= final_limit:
                break
            if item["id"] in selected_ids:
                continue
            selected.append(item)
            selected_ids.add(item["id"])
            if item["bucket"] in GEO_ENERGY_BUCKETS:
                geo_energy_count += 1
            if item["bucket"] in MARKET_PRIORITY_BUCKETS:
                market_count += 1

    return sorted(selected, key=lambda item: (item["relevance_score"], item["published_at"]), reverse=True)


def _cache_path() -> Path:
    return settings.signal_pool_cache_path


def _load_cache() -> dict[str, Any] | None:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(payload: dict[str, Any]) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _build_empty_payload(status: str, warnings: list[str]) -> dict[str, Any]:
    return {
        "meta": {
            "generated_at": _to_iso(_now_utc()),
            "window_hours": settings.signal_pool_window_hours,
            "item_count": 0,
            "source_count": 0,
            "status": status,
            "warnings": warnings,
        },
        "items": [],
    }


def build_signal_pool_payload(include_debug_stats: bool = False) -> dict[str, Any]:
    if not settings.enable_signal_pool:
        payload = _build_empty_payload("empty", ["signal_pool_disabled"])
        if include_debug_stats:
            payload["_debug"] = {
                "sources": 0,
                "raw_count": 0,
                "kept_count": 0,
                "dropped_count": 0,
                "dedup_removed_count": 0,
                "bucket_distribution": {},
                "drop_reasons": {},
                "top_kept_items": [],
                "top_dropped_items": [],
                "warnings": [],
                "cache_status": payload["meta"]["status"],
            }
        return payload

    now = _now_utc()
    cutoff = now - timedelta(hours=settings.signal_pool_window_hours)
    warnings: list[str] = []
    raw_candidates: list[SignalCandidate] = []
    enabled_sources = 0

    for source_definition in SIGNAL_SOURCE_DEFINITIONS:
        if not _source_enabled(source_definition):
            continue
        enabled_sources += 1
        source_had_entries = False
        for feed_url in source_definition["feeds"]:
            entries, feed_notes = _fetch_feed_entries(feed_url)
            for note in feed_notes:
                warnings.append(f"{source_definition['id']}:{note}")
            if not entries:
                continue
            source_had_entries = True
            for entry in entries:
                candidate = _normalize_candidate(source_definition["source_name"], entry)
                if not candidate or candidate.published_at < cutoff:
                    continue
                raw_candidates.append(candidate)
        if not source_had_entries:
            warnings.append(f"{source_definition['id']}:no_usable_feed")

    kept_items: list[dict[str, Any]] = []
    fallback_candidates: list[dict[str, Any]] = []
    dropped_count = 0
    drop_reasons: dict[str, int] = {}
    bucket_distribution: dict[str, int] = {}
    dropped_samples: list[dict[str, str]] = []

    for candidate in sorted(raw_candidates, key=lambda item: item.published_at, reverse=True):
        text = _normalize_text(f"{candidate.title} {candidate.summary}")
        combo_hits = _strategic_combo_hits(text)
        if _matches_any(text, DROP_TERMS):
            dropped_count += 1
            reason = "drop:low_signal_or_opinion"
            drop_reasons[reason] = drop_reasons.get(reason, 0) + 1
            if len(dropped_samples) < 8:
                dropped_samples.append({"source": candidate.source_name, "title": candidate.title, "reason": reason})
            continue

        bucket, bucket_terms = _determine_bucket(text)
        if not bucket:
            bucket = _fallback_bucket_from_combo(combo_hits)
            if bucket:
                bucket_terms = [f"combo:{combo_hits[0]}"]

        if not bucket:
            dropped_count += 1
            reason = "drop:no_bucket_match"
            drop_reasons[reason] = drop_reasons.get(reason, 0) + 1
            if len(dropped_samples) < 8:
                dropped_samples.append({"source": candidate.source_name, "title": candidate.title, "reason": reason})
            continue

        transmission_hits = sum(1 for _, terms in TRANSMISSION_RULES.items() if _matches_any(text, terms))
        relevance_score = _calculate_relevance(bucket, len(bucket_terms), transmission_hits, len(combo_hits), text)
        has_strategic_transmission = bool(
            combo_hits
            or (transmission_hits >= 1 and len(bucket_terms) >= 1 and relevance_score >= MIN_SIGNAL_RELEVANCE_SCORE)
        )
        if not has_strategic_transmission:
            dropped_count += 1
            reason = "drop:no_strategic_transmission"
            drop_reasons[reason] = drop_reasons.get(reason, 0) + 1
            if len(dropped_samples) < 8:
                dropped_samples.append({"source": candidate.source_name, "title": candidate.title, "reason": reason})
            fallback_candidates.append(
                {
                    "candidate": candidate,
                    "bucket": bucket,
                    "bucket_terms": bucket_terms,
                    "transmission_hits": transmission_hits,
                    "combo_hits": combo_hits,
                    "relevance_score": relevance_score,
                    "text": text,
                }
            )
            continue

        direction = _determine_direction(text)
        horizon = _determine_horizon(text, bucket)
        confidence = _determine_confidence(len(bucket_terms), transmission_hits, relevance_score)
        signal_type = _determine_signal_type(bucket, text)
        tags = _collect_tags(text, bucket, bucket_terms)
        dedup_key = _build_dedup_key(bucket, text, candidate.published_at)
        filter_reason = (
            f"matched bucket={bucket};transmission_hits={transmission_hits};"
            f"combo_hits={','.join(combo_hits[:2]) or 'none'};terms={','.join(bucket_terms[:3])}"
        )

        kept_items.append(
            {
                "id": candidate.id,
                "published_at": _to_iso(candidate.published_at),
                "source_name": candidate.source_name,
                "source_url": candidate.source_url,
                "title": candidate.title,
                "summary": candidate.summary,
                "bucket": bucket,
                "signal_type": signal_type,
                "direction": direction,
                "horizon": horizon,
                "confidence": confidence,
                "relevance_score": relevance_score,
                "tags": tags,
                "why_it_matters": _why_it_matters(bucket, direction, horizon, tags),
                "filter_reason": filter_reason,
                "dedup_key": dedup_key,
            }
        )
        bucket_distribution[bucket] = bucket_distribution.get(bucket, 0) + 1

    if len(kept_items) < MIN_SIGNAL_FALLBACK_ITEMS and len(raw_candidates) > MIN_RAW_ITEMS_FOR_SIGNAL_FALLBACK and fallback_candidates:
        if len(kept_items) == 0:
            fallback_keep_count = min(MIN_SIGNAL_FALLBACK_ITEMS, len(fallback_candidates), MAX_SIGNAL_POOL_ITEMS)
            fallback_keep_count = max(min(fallback_keep_count, MIN_SIGNAL_FALLBACK_ITEMS), min(3, len(fallback_candidates)))
        else:
            needed = MIN_SIGNAL_FALLBACK_ITEMS - len(kept_items)
            fallback_keep_count = min(max(needed, 0), len(fallback_candidates), MAX_SIGNAL_POOL_ITEMS)
        sorted_fallback = sorted(
            fallback_candidates,
            key=lambda entry: (entry["relevance_score"], entry["transmission_hits"], len(entry["combo_hits"])),
            reverse=True,
        )[:fallback_keep_count]
        for entry in sorted_fallback:
            candidate = entry["candidate"]
            bucket = entry["bucket"]
            text = entry["text"]
            direction = _determine_direction(text)
            horizon = _determine_horizon(text, bucket)
            signal_type = _determine_signal_type(bucket, text)
            tags = _collect_tags(text, bucket, entry["bucket_terms"])
            dedup_key = _build_dedup_key(bucket, text, candidate.published_at)
            kept_items.append(
                {
                    "id": candidate.id,
                    "published_at": _to_iso(candidate.published_at),
                    "source_name": candidate.source_name,
                    "source_url": candidate.source_url,
                    "title": candidate.title,
                    "summary": candidate.summary,
                    "bucket": bucket,
                    "signal_type": signal_type,
                    "direction": direction,
                    "horizon": horizon,
                    "confidence": "low",
                    "relevance_score": max(entry["relevance_score"], MIN_SIGNAL_RELEVANCE_SCORE),
                    "tags": tags,
                    "why_it_matters": _why_it_matters(bucket, direction, horizon, tags),
                    "filter_reason": "kept_by_minimum_signal_fallback",
                    "dedup_key": dedup_key,
                }
            )
            bucket_distribution[bucket] = bucket_distribution.get(bucket, 0) + 1

    dedup_map: dict[str, dict[str, Any]] = {}
    dedup_removed_count = 0
    for item in kept_items:
        existing = dedup_map.get(item["dedup_key"])
        if not existing:
            dedup_map[item["dedup_key"]] = item
            continue
        keep_new = (
            item["relevance_score"] > existing["relevance_score"]
            or (
                item["relevance_score"] == existing["relevance_score"]
                and len(item["summary"]) > len(existing["summary"])
            )
        )
        if keep_new:
            dedup_map[item["dedup_key"]] = item
        dedup_removed_count += 1

    dedup_items = list(dedup_map.values())
    items = _select_with_bucket_balance(dedup_items, MAX_SIGNAL_POOL_ITEMS)
    selected_bucket_distribution: dict[str, int] = {}
    for item in items:
        selected_bucket_distribution[item["bucket"]] = selected_bucket_distribution.get(item["bucket"], 0) + 1

    if items:
        status = "fresh" if not warnings else "partial"
        payload = {
            "meta": {
                "generated_at": _to_iso(now),
                "window_hours": settings.signal_pool_window_hours,
                "item_count": len(items),
                "source_count": len({item["source_name"] for item in items}),
                "status": status,
                "warnings": warnings,
            },
            "items": items,
        }
        _write_cache(payload)
    else:
        cached_payload = _load_cache()
        if cached_payload:
            payload = {
                "meta": {
                    **cached_payload.get("meta", {}),
                    "status": "stale_cache",
                    "warnings": (cached_payload.get("meta", {}).get("warnings", []) + warnings + ["using_stale_cache"]),
                },
                "items": cached_payload.get("items", []),
            }
        else:
            payload = _build_empty_payload("empty", warnings + ["no_signal_items"])

    if include_debug_stats:
        payload["_debug"] = {
            "sources": enabled_sources,
            "raw_count": len(raw_candidates),
            "kept_count": len(kept_items),
            "dropped_count": dropped_count,
            "dedup_removed_count": dedup_removed_count,
            "bucket_distribution": bucket_distribution,
            "selected_bucket_distribution": selected_bucket_distribution,
            "drop_reasons": drop_reasons,
            "top_kept_items": [
                {
                    "source": item["source_name"],
                    "title": item["title"],
                    "bucket": item["bucket"],
                    "score": item["relevance_score"],
                }
                for item in items[:5]
            ],
            "top_dropped_items": dropped_samples,
            "warnings": warnings,
            "cache_status": payload["meta"]["status"],
        }

    return payload
