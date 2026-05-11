"""Run the current multi-source refresh chain in sequence."""

from datetime import datetime, timezone

from ..pipelines.filter import run_filter
from ..pipelines.ingest import run_ingest
from ..pipelines.normalize import run_normalize
from ..pipelines.publish import run_publish
from .signal_pool_service import build_signal_pool_payload


VALID_REFRESH_SCOPES = {"home", "signal_pool", "all"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _refresh_home() -> dict[str, object]:
    ingest_result = run_ingest()
    normalize_result = run_normalize()
    filter_result = run_filter()
    publish_result = run_publish()

    fetched_count = int(ingest_result.get("fetched_count", 0))
    source_stats = ingest_result.get("sources", {})
    source_count = len(source_stats)
    sources_with_zero_fetch = [name for name, stats in source_stats.items() if int(stats.get("fetched_count", 0)) <= 0]
    warnings: list[str] = []

    if fetched_count <= 0:
        status = "source_fetch_failed"
        warnings.append("no_sources_fetched_items")
    elif sources_with_zero_fetch:
        status = "partial"
        warnings.append(f"sources_with_zero_fetch:{','.join(sorted(sources_with_zero_fetch))}")
    else:
        status = "ok"

    return {
        "status": status,
        "item_count": int(publish_result.get("published_count", 0)),
        "source_count": source_count,
        "warnings": warnings,
        "steps": {
            "ingest": ingest_result,
            "normalize": normalize_result,
            "filter": filter_result,
            "publish": publish_result,
        },
    }


def _refresh_signal_pool() -> dict[str, object]:
    payload = build_signal_pool_payload(include_debug_stats=False)
    meta = payload.get("meta", {})
    pool_status = str(meta.get("status", "empty"))
    warnings = list(meta.get("warnings", [])) if isinstance(meta.get("warnings"), list) else []
    status_map = {
        "fresh": "ok",
        "partial": "partial",
        "stale_cache": "partial",
        "empty": "error",
    }
    return {
        "status": status_map.get(pool_status, "error"),
        "item_count": int(meta.get("item_count", 0) or 0),
        "source_count": int(meta.get("source_count", 0) or 0),
        "warnings": warnings,
        "meta_status": pool_status,
    }


def _combine_refresh_status(scope: str, home_status: str | None, signal_pool_status: str | None) -> str:
    statuses = [status for status in (home_status, signal_pool_status) if status is not None]
    if not statuses:
        return "error"
    if all(status == "ok" for status in statuses):
        return "ok"
    if any(status == "error" for status in statuses):
        if any(status in {"ok", "partial"} for status in statuses):
            return "partial"
        return "error"
    if any(status == "partial" for status in statuses):
        return "partial"
    if scope == "home" and statuses == ["source_fetch_failed"]:
        return "source_fetch_failed"
    return "partial"


def trigger_refresh(scope: str = "home") -> dict[str, object]:
    if scope not in VALID_REFRESH_SCOPES:
        raise ValueError(f"Invalid refresh scope: {scope}")

    response: dict[str, object] = {
        "scope": scope,
        "generated_at": _now_iso(),
    }
    home_result: dict[str, object] | None = None
    signal_pool_result: dict[str, object] | None = None

    if scope in {"home", "all"}:
        home_result = _refresh_home()
        response["home"] = {
            "status": home_result.get("status", "error"),
            "item_count": home_result.get("item_count", 0),
            "source_count": home_result.get("source_count", 0),
            "warnings": home_result.get("warnings", []),
        }
        response["steps"] = home_result.get("steps", {})

    if scope in {"signal_pool", "all"}:
        signal_pool_result = _refresh_signal_pool()
        response["signal_pool"] = {
            "status": signal_pool_result.get("status", "error"),
            "item_count": signal_pool_result.get("item_count", 0),
            "source_count": signal_pool_result.get("source_count", 0),
            "warnings": signal_pool_result.get("warnings", []),
        }

    response["status"] = _combine_refresh_status(
        scope,
        str(home_result.get("status")) if home_result else None,
        str(signal_pool_result.get("status")) if signal_pool_result else None,
    )
    return response
