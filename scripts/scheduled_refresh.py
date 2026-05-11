import os
import sys
from urllib.parse import urlencode

import requests


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _build_url(base_url: str, scope: str) -> str:
    normalized = base_url.rstrip("/")
    query = urlencode({"scope": scope})
    return f"{normalized}/api/admin/refresh?{query}"


def main() -> int:
    base_url = _env("BACKEND_BASE_URL")
    if not base_url:
        print("ERROR: BACKEND_BASE_URL is required.")
        return 2

    token = _env("ADMIN_REFRESH_TOKEN")
    scope = _env("SCHEDULED_REFRESH_SCOPE", "all") or "all"
    url = _build_url(base_url, scope)

    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.post(url, headers=headers, timeout=60)
    except Exception as exc:
        print(f"ERROR: request_failed: {exc}")
        return 1

    print(f"HTTP status: {response.status_code}")
    if not response.ok:
        print(f"ERROR: non_2xx_response body={response.text[:500]}")
        return 1

    try:
        payload = response.json()
    except ValueError:
        print("ERROR: response_not_json")
        return 1

    overall_status = str(payload.get("status", "error"))
    print(f"refresh status: {overall_status}")
    print(f"scope: {payload.get('scope', '')}")
    print(f"generated_at: {payload.get('generated_at', '')}")

    home = payload.get("home")
    if isinstance(home, dict):
        print(
            f"home: status={home.get('status', '')} item_count={home.get('item_count', 0)} "
            f"source_count={home.get('source_count', 0)}"
        )
        warnings = home.get("warnings", [])
        if warnings:
            print(f"home warnings: {warnings}")

    signal_pool = payload.get("signal_pool")
    if isinstance(signal_pool, dict):
        print(
            f"signal_pool: status={signal_pool.get('status', '')} item_count={signal_pool.get('item_count', 0)} "
            f"source_count={signal_pool.get('source_count', 0)}"
        )
        warnings = signal_pool.get("warnings", [])
        if warnings:
            print(f"signal_pool warnings: {warnings}")

    if overall_status == "error":
        return 1
    if overall_status == "partial":
        print("WARNING: partial refresh status")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
