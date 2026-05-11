from collections import Counter
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.signal_pool_service import build_signal_pool_payload


def main() -> None:
    payload = build_signal_pool_payload(include_debug_stats=True)
    debug_stats = payload.get("_debug", {})
    items = payload.get("items", [])

    print("Signal Pool Debug")
    print(f"Sources: {debug_stats.get('sources', 0)}")
    print(f"Raw items: {debug_stats.get('raw_count', 0)}")
    print(f"Kept: {debug_stats.get('kept_count', 0)}")
    print(f"Dropped: {debug_stats.get('dropped_count', 0)}")
    print(f"Dedup removed: {debug_stats.get('dedup_removed_count', 0)}")
    print("")

    print("Buckets:")
    bucket_distribution = debug_stats.get("selected_bucket_distribution") or debug_stats.get("bucket_distribution", {})
    for bucket_name, count in sorted(bucket_distribution.items(), key=lambda item: item[1], reverse=True):
        print(f"- {bucket_name}: {count}")
    if not bucket_distribution:
        print("- none")
    print("")

    print("Top kept:")
    for index, item in enumerate(debug_stats.get("top_kept_items", [])[:5], start=1):
        print(
            f"{index}. {item.get('source', 'Unknown')} | {item.get('title', '')} | "
            f"{item.get('bucket', 'unknown')} | score={item.get('score', 0)}"
        )
    if not debug_stats.get("top_kept_items"):
        print("- none")
    print("")

    print("Top dropped:")
    for index, item in enumerate(debug_stats.get("top_dropped_items", [])[:5], start=1):
        print(
            f"{index}. {item.get('source', 'Unknown')} | {item.get('title', '')} | "
            f"drop={item.get('reason', 'unknown')}"
        )
    if not debug_stats.get("top_dropped_items"):
        print("- none")
    print("")

    print("Drop reasons:")
    drop_reasons = Counter(debug_stats.get("drop_reasons", {}))
    for reason, count in drop_reasons.most_common():
        print(f"- {reason}: {count}")
    if not drop_reasons:
        print("- none")
    print("")

    print(f"Cache status: {debug_stats.get('cache_status', payload.get('meta', {}).get('status', 'unknown'))}")
    warnings = debug_stats.get("warnings", [])
    if warnings:
        print("Warnings:")
        for warning in warnings[:10]:
            print(f"- {warning}")
    else:
        print("Warnings: none")

    print("")
    print(f"Returned items: {len(items)}")


if __name__ == "__main__":
    main()
