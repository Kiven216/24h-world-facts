"""Quality filters for keeping BBC single-source output closer to hard-news briefing content."""

from datetime import datetime, timedelta, timezone
import re


SUPPORTED_TOPICS = {
    "Policy / Politics",
    "Economy / Markets",
    "Business / Tech / Industry",
    "Conflict / Security",
}

POLICY_TERMS = (
    "government",
    "minister",
    "president",
    "prime minister",
    "court",
    "supreme court",
    "election",
    "vote",
    "policy",
    "parliament",
    "congress",
    "senate",
    "deportees",
    "detention",
    "diplomacy",
    "ceasefire",
    "negotiation",
    "sanction",
    "sanctions",
)

ECONOMY_TERMS = (
    "market",
    "markets",
    "inflation",
    "tariff",
    "tariffs",
    "trade",
    "economy",
    "stocks",
    "bank",
    "banks",
    "interest rate",
    "fuel duty",
    "prices rise",
    "oil prices",
    "growth",
    "exports",
)

TECH_INDUSTRY_TERMS = (
    "technology",
    "tech",
    "ai",
    "chip",
    "chips",
    "semiconductor",
    "software",
    "platform",
    "industry",
    "industrial",
    "factory",
    "company",
    "companies",
    "digital",
    "cyber",
    "telecom",
    "cloud",
    "data center",
    "data centres",
    "supply chain",
    "export controls",
)

SECURITY_TERMS = (
    "attack",
    "war",
    "strike",
    "strikes",
    "bombing",
    "military",
    "security",
    "hostage",
    "hostages",
    "missile",
    "missiles",
    "troops",
    "conflict",
    "iran",
    "gaza",
    "ukraine",
    "russia",
    "airman",
    "rescue",
)

EAST_ASIA_TERMS = (
    "japan",
    "china",
    "taiwan",
    "korea",
    "tokyo",
    "beijing",
    "seoul",
    "taipei",
    "south china sea",
    "east china sea",
    "indo-pacific",
)

TRADE_SUPPLY_CHAIN_TERMS = (
    "trade",
    "tariff",
    "tariffs",
    "exports",
    "supply chain",
    "manufacturing",
    "factory",
    "export controls",
)

SPORTS_TERMS = (
    "football",
    "footballers",
    "match",
    "matches",
    "tournament",
    "league",
    "goal",
    "coach",
)

PUBLIC_HEALTH_TERMS = (
    "measles",
    "outbreak",
    "jabs",
    "vaccination",
    "vaccine",
    "virus",
    "health emergency",
)

OBITUARY_TERMS = (
    "dies",
    "died",
    "dead at",
    "obituary",
    "mourned",
    "funeral",
    "tribute",
    "dies aged",
    "died aged",
)

ENTERTAINMENT_TERMS = (
    "celebrity",
    "showbiz",
    "entertainment",
    "actor",
    "actress",
    "singer",
    "musician",
    "rapper",
    "movie",
    "film",
    "tv star",
    "lifestyle",
    "arts",
)

LOW_VALUE_SOFT_TERMS = (
    "wise elder",
    "learns to cope",
    "personal story",
    "profile",
    "holiday photos",
    "first glimpse",
    "journey so far",
    "stunning moon pictures",
    "what we know so far",
    "watch:",
    "mental health programme",
    "tourism",
    "football",
    "footballers",
    "international match",
    "match",
)

HARD_NEWS_EXCEPTION_TERMS = (
    "attack",
    "war",
    "strike",
    "bombing",
    "military",
    "sanction",
    "sanctions",
    "court",
    "supreme court",
    "election",
    "policy",
    "inflation",
    "tariff",
    "tariffs",
    "trade",
    "security",
    "diplomacy",
    "hostage",
    "conflict",
    "missile",
    "troops",
    "ceasefire",
    "outbreak",
    "measles",
    "vaccine",
    "jabs",
)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    for phrase in phrases:
        if re.search(r"[^\w\s]", phrase):
            if phrase in text:
                return True
            continue
        if re.search(rf"\b{re.escape(phrase)}\b", text):
            return True
    return False


def _contains_age_pattern(text: str) -> bool:
    return bool(re.search(r"\baged\s+\d{2,3}\b", text))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def has_valid_title(title: str) -> bool:
    return bool(title and len(title.strip()) >= 12)


def has_valid_excerpt(excerpt: str) -> bool:
    return bool(excerpt and excerpt.strip())


def has_valid_url(url: str) -> bool:
    return bool(url and (url.startswith("http://") or url.startswith("https://")))


def passes_time_window(published_at: str, now: datetime | None = None, window_hours: int = 24) -> bool:
    comparison_time = now or _utc_now()
    return parse_iso_datetime(published_at) >= comparison_time - timedelta(hours=window_hours)


def is_supported_topic(topic: str) -> bool:
    return topic in SUPPORTED_TOPICS


def has_hard_news_exception(title: str, excerpt: str, topic: str, region: str | None = None) -> bool:
    text = _normalize_text(f"{title} {excerpt}")
    if topic == "Conflict / Security":
        return True
    if topic == "Business / Tech / Industry" and _contains_any(text, TECH_INDUSTRY_TERMS + TRADE_SUPPLY_CHAIN_TERMS):
        return True
    if region == "Japan / East Asia" and _contains_any(text, EAST_ASIA_TERMS + TRADE_SUPPLY_CHAIN_TERMS + SECURITY_TERMS + POLICY_TERMS):
        return True
    return _contains_any(text, HARD_NEWS_EXCEPTION_TERMS)


def is_obituary_like(title: str, excerpt: str, topic: str, region: str | None = None) -> bool:
    text = _normalize_text(f"{title} {excerpt}")
    if has_hard_news_exception(title, excerpt, topic, region):
        return False
    return _contains_any(text, OBITUARY_TERMS) or _contains_age_pattern(text)


def is_entertainment_like(title: str, excerpt: str, topic: str, region: str | None = None) -> bool:
    text = _normalize_text(f"{title} {excerpt}")
    if has_hard_news_exception(title, excerpt, topic, region):
        return False
    return _contains_any(text, ENTERTAINMENT_TERMS)


def is_hard_news_candidate(title: str, excerpt: str, topic: str, region: str | None = None) -> bool:
    text = _normalize_text(f"{title} {excerpt}")
    if topic == "Policy / Politics":
        if region == "Japan / East Asia":
            return _contains_any(text, POLICY_TERMS + SECURITY_TERMS + PUBLIC_HEALTH_TERMS + EAST_ASIA_TERMS + TRADE_SUPPLY_CHAIN_TERMS + TECH_INDUSTRY_TERMS)
        return _contains_any(text, POLICY_TERMS + SECURITY_TERMS + PUBLIC_HEALTH_TERMS)
    if topic == "Economy / Markets":
        if region == "Japan / East Asia":
            return _contains_any(text, ECONOMY_TERMS + POLICY_TERMS + EAST_ASIA_TERMS + TRADE_SUPPLY_CHAIN_TERMS)
        return _contains_any(text, ECONOMY_TERMS + POLICY_TERMS)
    if topic == "Business / Tech / Industry":
        return _contains_any(text, TECH_INDUSTRY_TERMS + ECONOMY_TERMS + POLICY_TERMS + TRADE_SUPPLY_CHAIN_TERMS + EAST_ASIA_TERMS)
    if topic == "Conflict / Security":
        return _contains_any(text, SECURITY_TERMS + POLICY_TERMS + EAST_ASIA_TERMS)
    return False


def is_low_value_soft_story(title: str, excerpt: str, topic: str, region: str | None = None) -> bool:
    text = _normalize_text(f"{title} {excerpt}")
    if has_hard_news_exception(title, excerpt, topic, region):
        return False
    if _contains_any(text, SPORTS_TERMS):
        return True
    if _contains_any(text, LOW_VALUE_SOFT_TERMS):
        return True
    return not is_hard_news_candidate(title, excerpt, topic, region)


def evaluate_article_filters(*, title: str, excerpt: str, url: str, topic: str, published_at: str, region: str | None = None, now: datetime | None = None) -> dict[str, bool | str]:
    current_time = now or _utc_now()
    time_window_pass = passes_time_window(published_at, now=current_time)
    topic_pass = is_supported_topic(topic)

    if not has_valid_title(title):
        return {"passed_filter": False, "filter_reason": "invalid_title", "time_window_pass": time_window_pass, "topic_pass": topic_pass}
    if not has_valid_excerpt(excerpt):
        return {"passed_filter": False, "filter_reason": "missing_excerpt", "time_window_pass": time_window_pass, "topic_pass": topic_pass}
    if not has_valid_url(url):
        return {"passed_filter": False, "filter_reason": "invalid_url", "time_window_pass": time_window_pass, "topic_pass": topic_pass}
    if not time_window_pass:
        return {"passed_filter": False, "filter_reason": "out_of_time_window", "time_window_pass": time_window_pass, "topic_pass": topic_pass}
    if not topic_pass:
        return {"passed_filter": False, "filter_reason": "unsupported_topic", "time_window_pass": time_window_pass, "topic_pass": topic_pass}
    if is_obituary_like(title, excerpt, topic, region):
        return {"passed_filter": False, "filter_reason": "obituary_like_soft_story", "time_window_pass": time_window_pass, "topic_pass": topic_pass}
    if is_entertainment_like(title, excerpt, topic, region):
        return {"passed_filter": False, "filter_reason": "entertainment_like_story", "time_window_pass": time_window_pass, "topic_pass": topic_pass}
    if is_low_value_soft_story(title, excerpt, topic, region):
        return {"passed_filter": False, "filter_reason": "low_value_soft_story", "time_window_pass": time_window_pass, "topic_pass": topic_pass}
    return {"passed_filter": True, "filter_reason": "passed", "time_window_pass": time_window_pass, "topic_pass": topic_pass}
