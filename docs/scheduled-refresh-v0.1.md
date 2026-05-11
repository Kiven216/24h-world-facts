# Scheduled Refresh Support v0.1

## Goal
- Keep manual refresh available.
- Add scheduled refresh support for New York 09:00 / 21:00.
- Refresh both homepage cache and signal-pool cache with `scope=all`.

## Admin Refresh API
Endpoint:
- `GET /api/admin/refresh`
- `POST /api/admin/refresh`

Query params:
- `scope=home|signal_pool|all` (default: `home`)
- optional `token=<ADMIN_REFRESH_TOKEN>` for cron/webcron fallback

Auth:
- Preferred: `Authorization: Bearer <ADMIN_REFRESH_TOKEN>`
- If `ADMIN_REFRESH_TOKEN` is set, token is required and validated.
- If `ADMIN_REFRESH_TOKEN` is not set (local dev), refresh is allowed and response warnings include `admin_refresh_token_not_set_dev_mode`.

## Scope behavior
- `scope=home`: runs ingest → normalize → filter → publish for `/api/home`.
- `scope=signal_pool`: refreshes strategic signal pool cache only.
- `scope=all`: runs both and returns combined status.

## Combined status
- `ok`: all requested scopes successful.
- `partial`: mixed success (for example, home ok but signal_pool partial/error).
- `source_fetch_failed`: home scope fetched no source items.
- `error`: all requested scopes failed.

## Scheduled runner script
Script:
- `scripts/scheduled_refresh.py`

Required env vars:
- `BACKEND_BASE_URL=https://your-render-backend.onrender.com`
- `ADMIN_REFRESH_TOKEN=...` (required in staging/production)

Optional:
- `SCHEDULED_REFRESH_SCOPE=all` (default: `all`)

Run:
```bash
python scripts/scheduled_refresh.py
```

## Render Cron Job setup
Recommended: create two Render Cron Jobs.

Example names:
- `24h-world-facts-refresh-ny-9am`
- `24h-world-facts-refresh-ny-9pm`

Command:
```bash
python scripts/scheduled_refresh.py
```

### UTC schedule mapping (DST caveat)
Render cron uses UTC. New York has DST, so the UTC hour changes:

- During EDT (summer):
  - NY 09:00 → `13:00 UTC` (`0 13 * * *`)
  - NY 21:00 → `01:00 UTC` next day (`0 1 * * *`)
- During EST (winter):
  - NY 09:00 → `14:00 UTC` (`0 14 * * *`)
  - NY 21:00 → `02:00 UTC` next day (`0 2 * * *`)

v0.1 uses fixed UTC schedules and requires manual adjustment on DST switch dates.

## Boundary guarantees
- `/api/home` output schema remains unchanged.
- `/api/signal-pool` output schema remains unchanged.
- Homepage ranking/dedup/topic balance logic unchanged.
- Signal-pool and homepage remain separate outputs.
