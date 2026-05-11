# Strategic Signal Pool v0.1

## Purpose
Hidden strategic signal API for future Sentiment Terminal / Strategic Layer usage.

## Boundary
- Does not affect `/api/home`.
- Does not change homepage ranking / dedup / topic balance.
- Does not produce investment advice.
- Does not use LLM in v0.1.

## API
`GET /api/signal-pool`

## Response Schema
- `meta.generated_at`
- `meta.window_hours`
- `meta.item_count`
- `meta.source_count`
- `meta.status`: `fresh | partial | stale_cache | empty`
- `meta.warnings`
- `items[]` fields:
  - `id`
  - `published_at`
  - `source_name`
  - `source_url`
  - `title`
  - `summary`
  - `bucket`
  - `signal_type`
  - `direction`
  - `horizon`
  - `confidence`
  - `relevance_score`
  - `tags`
  - `why_it_matters` (deterministic)
  - `filter_reason`
  - `dedup_key`

## Sources (v0.1)
- CoinDesk (enabled by default)
- CNBC feeds (enabled by default)
- OilPrice (optional, disabled by default)

## Relevance Gate
Flow:
1. fetch raw feed items
2. normalize headline/summary/time/url
3. strategic relevance gate (bucket + transmission checks)
4. classify signal fields
5. lightweight dedup
6. cache and return

Items without strategic transmission path are dropped.

## Cache / Fallback
- Cache file: `data/signal_pool_cache.json`
- Fresh/partial fetch success: return result and update cache
- No live items but cache exists: return `stale_cache` with warnings
- No cache and no items: return `empty`

## Debug Script
Run:

```bash
python scripts/debug_signal_pool.py
```

It prints:
- source count
- raw/kept/dropped counts
- dedup removed
- bucket distribution
- top kept / dropped examples
- drop reasons
- cache status and warnings

## Future To Do
- Sentiment Terminal integration
- LLM relevance refinement
- LLM strategic synthesis
- event-aware signal clustering
- source quality scoring
- source expansion
