# 24H World Facts

24H World Facts is a local MVP for browsing important factual stories from the last 24 hours. This first round is intentionally limited to a scaffolded backend, a scaffolded frontend, a minimal SQLite data layer, and a homepage fed by mock data.

## Current Stage

This repository is currently a scaffold version:

- FastAPI backend with `/api/health` and `/api/home`
- React + Vite frontend homepage with basic responsive layout
- SQLite schema for `final_cards` and `app_meta`
- Mock data scripts for local initialization
- Frontend-local FilterBar interactions for region, topic, confidence, and sort order
- Score display kept on a 10-point UI scale
- Placeholder source, pipeline, rule, and job modules for future rounds

It does **not** yet connect to real news sources, clustering, scoring pipelines, or LLM summarization.

## Directory Overview

```text
24h_world_facts/
  backend/        FastAPI app, services, schemas, placeholders
  frontend/       React + Vite homepage scaffold
  data/           Mock JSON and local SQLite database
  docs/           Project notes
  scripts/        Database init and mock seeding scripts
```

## Local Run

### 1. Backend setup

From the project root:

```bash
python -m pip install -r backend/requirements.txt
```

Start the API server:

```bash
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://127.0.0.1:8000`.

### 2. Database initialization

Create the SQLite tables:

```bash
python scripts/init_db.py
```

Write the mock homepage dataset into SQLite:

```bash
python scripts/seed_mock_data.py
```

The database file is created at `data/app.db`.

### 3. Frontend setup

Install frontend dependencies:

```bash
cd frontend
npm install
```

Start the Vite dev server:

```bash
npm run dev
```

The frontend will be available at `http://127.0.0.1:5173`.

### 4. Mobile / LAN access

For phone testing on the same local network:

- Start the backend with `--host 0.0.0.0`
- Start the frontend normally after the Vite host update in this repo
- Open `http://<your-lan-ip>:5173` on your phone

Example:

```text
http://192.168.3.2:5173
```

The frontend now defaults to calling the backend on the same hostname at port `8000`, so a phone visiting `http://192.168.3.2:5173` will request `http://192.168.3.2:8000/api/home`.

## API Endpoints

- `GET /api/health` returns a simple health payload
- `GET /api/home` returns homepage sections:
  - `meta`
  - `top_stories`
  - `by_region`
  - `by_topic`
  - `watchlist`

If SQLite has no rows yet, `/api/home` falls back to `data/mock_cards.json`.

## Not Implemented Yet

- Real RSS or publisher integrations
- Refresh jobs and background scheduling
- Story clustering and event deduplication
- Weighted scoring and confidence logic
- LLM summaries
- Search, login, favorites, personalization
- Backend-driven filtering behavior in the frontend
