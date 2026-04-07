# Staging Deploy

## Deployment Goal

Use the current app with the smallest possible staging setup:

- frontend on Vercel
- backend on Render Web Service
- SQLite on a Render persistent disk
- refresh triggered manually through `POST /api/admin/refresh`

## Why This Is the Current Staging Choice

- simple
- externally accessible
- still close to the current local architecture
- avoids introducing Postgres, queues, or a scheduler before they are needed

## Frontend Deploy Steps

1. Create a Vercel project pointing at the `frontend/` directory.
2. Build command: `npm run build`
3. Output directory: `dist`
4. Set:
   - `VITE_API_BASE_URL=https://<your-render-backend-domain>/api`

### Frontend Env Examples

- Local:
  - leave `VITE_API_BASE_URL` unset
  - frontend falls back to `http://<current-hostname>:8000/api`
- Staging:
  - `VITE_API_BASE_URL=https://your-backend.onrender.com/api`

## Backend Deploy Steps

1. Create a Render Web Service from the repo root.
2. Build Command:
   - `pip install -r backend/requirements.txt`
3. Start Command:
   - `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
4. Add a persistent disk.
   - mount path example: `/var/data`

## Required Environment Variables

### Backend

- `DATABASE_PATH=/var/data/app.db`

### Recommended Backend Variables

- `APP_NAME=24H World Facts`
- `API_PREFIX=/api`
- `MOCK_DATA_PATH=data/mock_cards.json`
- `CORS_ALLOWED_ORIGINS=https://<your-vercel-domain>`
- `CORS_ALLOWED_ORIGIN_REGEX=^https://.*\\.vercel\\.app$`

### Frontend

- `VITE_API_BASE_URL=https://<your-render-backend-domain>/api`

## Persistent Disk Note

The backend now initializes SQLite tables on application startup, so the first boot on Render can create the database file if it does not already exist.

The important part is that the database path points at the mounted disk, not at the ephemeral service filesystem.

Example:

- disk mount path: `/var/data`
- `DATABASE_PATH=/var/data/app.db`

## Manual Refresh Note

Staging currently uses manual refresh only.

Use:

- `POST /api/admin/refresh`

This can be triggered from the existing frontend refresh action or with a direct HTTP request.

## Explicit Non-Goals

- no Postgres yet
- no cron yet
- no dedup changes
- no clustering changes
- no ranking redesign
- no production hardening pass
