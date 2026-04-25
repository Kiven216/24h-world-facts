"""LLM explanation layer for top stories with cache-first fallback-safe behavior."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import settings


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
LLM_CACHE_VERSION = "v0.5"
LLM_CACHE_MAX_ITEMS = 512
LLM_MAX_WORKERS = 4
LLM_MAX_OUTPUT_TOKENS = 88
LLM_MIN_WORDS = 8
LLM_TARGET_MIN_WORDS = 25
LLM_TARGET_MAX_WORDS = 65
LLM_RETRY_TRIGGER_WORDS = 66
LLM_HARD_MAX_WORDS = 72
GENERIC_PHRASE_MARKERS = (
    "broader political trends",
    "regional stability",
    "broader market dynamics",
    "long-term geopolitical consequences",
    "broader economic pressures",
    "interconnectedness of",
    "wider pressures",
    "broader trends",
    "global significance",
    "eu integration efforts",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").replace("\n", " ").split()).strip().strip('"')


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _extract_complete_sentences(text: str) -> list[str]:
    matches = re.findall(r"[^.!?]+[.!?]", text)
    return [_normalize_text(match) for match in matches if _normalize_text(match)]


def _looks_incomplete(text: str) -> bool:
    cleaned = _normalize_text(text)
    if not cleaned:
        return True
    if cleaned[-1] not in ".!?":
        return True
    if cleaned.endswith((" ,", " ;", " :", " -")):
        return True
    if re.search(r"(?:\b[A-Z]\.\s*){2,}$", cleaned):
        return True
    return False


def _contains_generic_phrase(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in GENERIC_PHRASE_MARKERS)


def _load_cache() -> dict[str, dict[str, Any]]:
    cache_path = settings.llm_cache_path
    if not cache_path.exists():
        return {}

    try:
        with cache_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def _save_cache(cache: dict[str, dict[str, Any]]) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    cache_path = settings.llm_cache_path
    sorted_items = sorted(cache.items(), key=lambda item: item[1].get("saved_at", ""), reverse=True)[:LLM_CACHE_MAX_ITEMS]
    with cache_path.open("w", encoding="utf-8") as file:
        json.dump({key: value for key, value in sorted_items}, file, ensure_ascii=True, indent=2)


def _cache_key(story: dict[str, Any]) -> str:
    return str(story.get("event_id") or story.get("article_url") or story.get("headline") or "").strip()


def _build_story_input(story: dict[str, Any], edition_time: str, peer_titles: list[str]) -> str:
    source_label = " / ".join(story.get("source_list", [])) or "Unknown source"
    peer_lines = "\n".join(f"- {title}" for title in peer_titles[:6]) or "- None"
    return (
        f"Edition time: {edition_time}\n"
        f"Story title: {story.get('headline', '')}\n"
        f"Summary: {story.get('summary', '')}\n"
        f"Source: {source_label}\n"
        f"Topic: {story.get('topic', '')}\n"
        f"Region: {story.get('region', '')}\n"
        f"Published at: {story.get('published_at', '')}\n"
        "Other top stories in this edition:\n"
        f"{peer_lines}\n"
        "Write one short why-it-matters-now note."
    )


def _parse_response_text(payload: dict[str, Any]) -> str:
    if payload.get("status") == "incomplete" or payload.get("incomplete_details"):
        return ""

    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content_item in item.get("content", []):
            if content_item.get("type") == "output_text":
                return _normalize_text(content_item.get("text", ""))
    return ""


def _call_openai(payload: dict[str, Any]) -> str:
    request = Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=settings.llm_timeout_seconds) as response:
        response_payload = json.loads(response.read().decode("utf-8"))
    return _parse_response_text(response_payload)


def _call_openai_for_story(story: dict[str, Any], edition_time: str, peer_titles: list[str]) -> str:
    payload = {
        "model": settings.openai_model,
        "instructions": (
            "You write a concise why-it-matters-now note for a world news briefing. "
            "Prefer 1 sentence, but 2 short sentences are allowed if they keep the note clearer and more specific. "
            "A usable answer is usually around 25 to 65 words, and may approach 70 words for a more complex story. "
            "Stay close to the headline and summary. Explain the immediate relevance now, not downstream ripple effects. "
            "Only mention effects directly supported by the headline and summary. Do not infer second-order or long-range consequences unless they are explicit. "
            "For local or narrowly scoped stories, keep the explanation narrow and immediate. Do not generalize to national, regional, market-wide, or strategic implications unless clearly stated. "
            "Anchor the note in a concrete layer such as a legal signal, policy signal, alliance tension, institutional constraint, supply concern, regional security development, immediate political test, or near-term market sensitivity when supported. "
            "Do not repeat the headline or summary. "
            "Avoid broad phrases such as broader political trends, regional stability, broader market dynamics, long-term geopolitical consequences, or EU integration efforts unless the article clearly supports them. "
            "Be factual, restrained, specific, non-hype, non-opinionated, and non-investment-advice."
        ),
        "input": _build_story_input(story, edition_time, peer_titles),
        "max_output_tokens": LLM_MAX_OUTPUT_TOKENS,
        "temperature": 0.2,
        "store": False,
    }
    return _call_openai(payload)


def _call_openai_shorten_retry(story: dict[str, Any], draft: str) -> str:
    payload = {
        "model": settings.openai_model,
        "instructions": (
            "Rewrite the draft into a tighter why-it-matters-now note for a world news briefing. "
            "Prefer 1 sentence. Keep only the most immediate relevance. "
            "Target roughly 18 to 38 words. "
            "Stay evidence-close to the headline and summary. "
            "Remove broad framing, second-order inference, loose filler, and repeated setup. "
            "If the original draft is already specific and readable, keep its core point rather than flattening it into a template."
        ),
        "input": (
            f"Headline: {story.get('headline', '')}\n"
            f"Summary: {story.get('summary', '')}\n"
            f"Draft explanation: {draft}\n"
            "Return the tightened explanation only."
        ),
        "max_output_tokens": 56,
        "temperature": 0.1,
        "store": False,
    }
    return _call_openai(payload)


def _prepare_candidate(text: str) -> str:
    cleaned = _normalize_text(text)
    if not cleaned or _looks_incomplete(cleaned):
        return ""

    sentences = _extract_complete_sentences(cleaned)
    if not sentences:
        return ""

    candidate = sentences[0]
    if len(sentences) > 1:
        combined = f"{sentences[0]} {sentences[1]}".strip()
        if _word_count(combined) <= LLM_HARD_MAX_WORDS:
            candidate = combined

    return candidate if not _looks_incomplete(candidate) else ""


def _assess_explanation(text: str, summary: str) -> tuple[str, str]:
    candidate = _prepare_candidate(text)
    if not candidate:
        return "reject", ""

    word_count = _word_count(candidate)
    summary_word_count = _word_count(summary)

    if word_count < LLM_MIN_WORDS:
        return "reject", ""
    if word_count > LLM_HARD_MAX_WORDS:
        return "retry", candidate
    if summary_word_count and word_count > summary_word_count + 8:
        return "retry", candidate
    if _contains_generic_phrase(candidate):
        return "retry", candidate
    if word_count >= LLM_RETRY_TRIGGER_WORDS:
        return "retry", candidate

    return "accept", candidate


def _generate_story_explanation(story: dict[str, Any], edition_time: str, top_stories: list[dict[str, Any]]) -> str:
    peer_titles = [item.get("headline", "") for item in top_stories if item.get("event_id") != story.get("event_id")]
    try:
        original = _call_openai_for_story(story, edition_time, peer_titles)
        original_status, original_candidate = _assess_explanation(original, str(story.get("summary", "")))
        if original_status == "accept":
            return original_candidate
        if original_status == "retry":
            shortened = _call_openai_shorten_retry(story, original_candidate or original)
            retry_status, retry_candidate = _assess_explanation(shortened, str(story.get("summary", "")))
            if retry_status == "accept":
                return retry_candidate
            if original_candidate:
                return original_candidate
        return ""
    except (HTTPError, URLError, OSError, TimeoutError, json.JSONDecodeError, ValueError):
        return ""


def enrich_top_stories_with_llm_explanations(top_stories: list[dict[str, Any]], edition_time: str) -> list[dict[str, Any]]:
    if not top_stories:
        return top_stories
    if not settings.enable_llm_why_it_matters or not settings.openai_api_key:
        return top_stories

    enriched_stories = [dict(story) for story in top_stories]
    for story in enriched_stories:
        story["why_it_matters"] = ""
    cache = _load_cache()
    cache_dirty = False
    pending_items: list[tuple[int, dict[str, Any], str]] = []

    for index, story in enumerate(enriched_stories):
        cache_key = _cache_key(story)
        if not cache_key:
            continue

        cached_entry = cache.get(cache_key)
        cached_status, cached_text = _assess_explanation(cached_entry.get("text", "") if cached_entry else "", str(story.get("summary", "")))
        if (
            cached_entry
            and cached_entry.get("version") == LLM_CACHE_VERSION
            and cached_entry.get("model") == settings.openai_model
            and cached_entry.get("headline") == story.get("headline")
            and cached_entry.get("article_url") == story.get("article_url")
            and cached_status in {"accept", "retry"}
            and cached_text
        ):
            story["why_it_matters"] = cached_text
            continue

        pending_items.append((index, story, cache_key))

    if pending_items:
        with ThreadPoolExecutor(max_workers=min(LLM_MAX_WORKERS, len(pending_items))) as executor:
            future_map = {
                executor.submit(_generate_story_explanation, story, edition_time, enriched_stories): (index, story, cache_key)
                for index, story, cache_key in pending_items
            }
            for future in as_completed(future_map):
                index, story, cache_key = future_map[future]
                explanation = future.result() or ""
                if explanation:
                    enriched_stories[index]["why_it_matters"] = explanation
                    cache[cache_key] = {
                        "version": LLM_CACHE_VERSION,
                        "text": explanation,
                        "model": settings.openai_model,
                        "headline": story.get("headline"),
                        "article_url": story.get("article_url"),
                        "saved_at": _utc_now_iso(),
                    }
                    cache_dirty = True

    if cache_dirty:
        _save_cache(cache)

    return enriched_stories
