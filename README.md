# 24H World Facts

24H World Facts is a local v1 MVP for browsing important factual stories from the last 24 hours.

The project now includes a usable multi-source real ingest path using BBC RSS, NHK World English news, and NPR RSS, while still falling back to mock data when real cards are not yet sufficient for the homepage.

It is best understood at this stage as:
- a local multi-source factual briefing prototype,
- a compact homepage product focused on hard-news filtering and homepage curation,
- and an article-level pipeline that has not yet evolved into true event-level aggregation.

## Current Stage

This repository is currently a **local v1 prototype**, not just a scaffold.

It already includes:
- FastAPI backend with `/api/health`, `/api/home`, and `/api/admin/refresh`
- React + Vite frontend homepage
- SQLite schema for:
  - `article_raw`
  - `article_normalized`
  - `article_filtered`
  - `final_cards`
  - `app_meta`
- Real news sources:
  - BBC RSS (`world`, `business`, `technology`, `politics`)
  - NHK World English (`world`, `japan`, `asia`, `biztch`)
  - NPR RSS (`news`, `politics`, `business`, `technology`) under observation after minimum validation
- Refresh chain:
  - `ingest -> normalize -> filter -> publish`
- Homepage caps for:
  - top stories
  - watchlist
  - by-region buckets
  - by-topic buckets
- First-pass heuristic topic / region classification
- A real quality-filtering layer biased toward hard-news retention
- Lightweight keyword-driven `why_it_matters`
- Mock fallback when real cards are still insufficient
- NPR has completed minimum integration validation and is now in observation phase as the newly validated third-source candidate

The system is still intentionally limited:
- publish is currently article-level, not true event-level
- there is no cross-source deduplication yet
- there is no clustering or LLM summarization yet
- scoring and watchlist logic are still temporary heuristics
- staging deployment is supported in a minimal Vercel + Render + SQLite-on-disk setup

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

### 3. Run one real-data refresh

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

`/api/home` now prefers real BBC + NHK + NPR-generated `final_cards`. If there are too few real cards for the homepage, it supplements with mock cards so the UI does not go blank.

Homepage sections are intentionally capped so the default page stays shorter and more readable, especially on mobile:

- Top Stories: up to 8
- Watchlist: up to 4
- By Region: up to 3 per bucket
- By Topic: up to 3 per bucket

`region` and `topic` are still heuristic guesses, but the first-pass keyword rules have been tightened to reduce obvious misclassification.

The filter layer now leans toward hard-news retention and is stricter about excluding obituary-like stories, entertainment-like items, soft features, and other low-value world stories that do not fit the briefing product.

The current balance is intentionally layered: top stories and watchlist remain strict, while qualified technology, industry, trade, and East Asia stories have a better chance of surviving into By Topic / By Region buckets. NHK is mainly used to strengthen Japan / East Asia coverage without loosening the homepage caps.

`why_it_matters` has also been upgraded from broad topic templates to lightweight keyword-driven templates so the card copy is more specific without introducing LLM dependencies.

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

The frontend supports an explicit API base override through `VITE_API_BASE_URL`.

Examples:

- Local:
  - leave `VITE_API_BASE_URL` unset and the app will keep using `http://<current-hostname>:8000/api`
- Staging:
  - set `VITE_API_BASE_URL=https://<your-render-backend-domain>/api`

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

## Minimal Staging

The project now supports a minimal staging deployment:

- frontend on Vercel
- backend on Render Web Service
- SQLite on a Render persistent disk
- manual refresh through `POST /api/admin/refresh`

For staging steps and environment variables, see [staging-deploy.md](/Users/Kin%20Chueng/PyCharmMiscProject/24h_world_facts/docs/staging-deploy.md).

## API Endpoints

- `GET /api/health` returns a simple health payload
- `GET /api/home` returns homepage sections:
  - `meta`
  - `top_stories`
  - `by_region`
  - `by_topic`
  - `watchlist`
- `POST /api/admin/refresh` runs one local BBC + NHK + NPR refresh cycle

In staging, refresh is still intended to be manual rather than scheduled.

If there are not enough real BBC / NHK / NPR-generated cards yet, `/api/home` supplements the response with `data/mock_cards.json`.

## Not Implemented Yet

- Additional RSS or publisher integrations beyond BBC, NHK, and the observed NPR validation source
- Refresh jobs and background scheduling
- Story clustering and event deduplication
- Production-grade scoring and confidence logic
- LLM summaries
- Search, login, favorites, personalization
- Backend-driven filtering behavior in the frontend
