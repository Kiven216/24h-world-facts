# 24H World Facts

24H World Facts is a local MVP for browsing important factual stories from the last 24 hours. The project now includes a first real-source path using BBC RSS, while still falling back to mock data when real cards are not yet sufficient for the homepage.

## Current Stage

This repository is currently a scaffold version:

- FastAPI backend with `/api/health` and `/api/home`
- React + Vite frontend homepage with basic responsive layout
- SQLite schema for `final_cards` and `app_meta`
- SQLite article pipeline tables: `article_raw`, `article_normalized`, `article_filtered`
- Mock data scripts for local initialization
- First real news source: BBC RSS (`world`, `business`, `technology`, `politics`)
- Refresh chain: `ingest -> normalize -> filter -> publish`
- Homepage content caps for top stories, watchlist, region, and topic blocks
- First-pass heuristic fixes for region/topic classification
- Frontend-local FilterBar interactions for region, topic, confidence, and sort order
- Score display kept on a 10-point UI scale
- Placeholder source, pipeline, rule, and job modules for future rounds

It still does **not** include complex clustering, event deduplication, embedding workflows, or LLM summarization.

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
python -m venv .venv
.\.venv\Scripts\Activate.ps1
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

### 3. Run one BBC refresh

Run the minimal real-source chain:

```bash
python scripts/run_refresh.py
```

Or call the local dev endpoint:

```bash
curl -X POST http://127.0.0.1:8000/api/admin/refresh
```

The refresh flow is:

```text
ingest -> normalize -> filter -> publish
```

`/api/home` now prefers real BBC-generated `final_cards`. If there are too few real cards for the homepage, it supplements with mock cards so the UI does not go blank.

Homepage sections are intentionally capped so the default page stays shorter and more readable, especially on mobile:

- Top Stories: up to 8
- Watchlist: up to 4
- By Region: up to 3 per bucket
- By Topic: up to 3 per bucket

`region` and `topic` are still heuristic guesses, but the first-pass keyword rules have been tightened to reduce obvious misclassification.

### 4. Frontend setup

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

### 5. Mobile / LAN access

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
- `POST /api/admin/refresh` runs one local BBC refresh cycle

If there are not enough real BBC-generated cards yet, `/api/home` supplements the response with `data/mock_cards.json`.

## Not Implemented Yet

- Additional RSS or publisher integrations beyond BBC
- Refresh jobs and background scheduling
- Story clustering and event deduplication
- Production-grade scoring and confidence logic
- LLM summaries
- Search, login, favorites, personalization
- Backend-driven filtering behavior in the frontend
