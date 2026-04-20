# 24H World Facts — Architecture Freeze v1

## 1. Document Status

This document freezes the current v1 architecture of **24H World Facts** as implemented in the local MVP codebase.

It describes the system **as it currently exists**, not the eventual target system.  
Where the implementation is intentionally provisional, this document marks it as such.

This freeze is meant to establish a stable baseline before:
- introducing heavier cross-source duplicate control,
- improving ranking and scoring,
- or expanding topic coverage.

---

## 2. Product Goal at v1

24H World Facts is currently a **local multi-source factual briefing MVP** focused on surfacing important hard-news stories from the last 24 hours.

The product goal at this stage is:

- keep only a smaller set of factual, high-value, recent stories,
- suppress soft content, opinion-like drift, entertainment, obituary-like items, and low-value features,
- present a compact homepage that behaves more like a briefing layer than a news portal,
- keep implementation simple, inspectable, and controllable.

At v1, the system is **article-level**, not event-level.  
It does **not** yet attempt true event clustering, cross-source story merging, embedding retrieval, or LLM summarization.

---

## 3. Current System Boundary

### Included in v1

The current system includes:

- FastAPI backend
- local SQLite storage
- real-source ingest from BBC RSS, NHK World English list JSON, and NPR RSS
- a 4-step refresh chain:
  - ingest
  - normalize
  - filter
  - publish
- homepage API payload generation
- homepage exposure control v0.2
- mock fallback when real cards are insufficient
- first-pass heuristic topic / region classification
- first-pass quality filtering
- temporary article-level scoring and watchlist logic
- local frontend consumption through `/api/home`

### Explicitly not included in v1

The current architecture does **not** include:

- cross-source event deduplication
- story clustering
- embedding-based similarity or retrieval
- LLM summaries or LLM-generated ranking
- background jobs / scheduler / async workers
- user accounts
- personalization
- favorites / saved stories
- backend search
- production-grade source weighting model
- mature rules module separation for topic / region / scoring

---

## 4. Runtime Topology

### 4.1 Deployment shape

The current system is a **local development MVP**.

Core runtime pieces:

- FastAPI backend
- React + Vite frontend
- SQLite database in local `data/`
- manual or endpoint-triggered refresh

### 4.2 API shape

Current backend routers are mounted under `settings.api_prefix`.

The system currently exposes at least:

- `GET /api/health`
- `GET /api/home`
- `POST /api/admin/refresh`

### 4.3 CORS / local network scope

The backend is configured for localhost and LAN-style development access, including common local Vite origins and local IP-based access patterns. This supports same-network phone testing during MVP development.

---

## 5. High-Level Flow

The current refresh and homepage flow is:

1. ingest real source items into `article_raw`
2. normalize raw source records into a shared article shape in `article_normalized`
3. run quality filters and persist decisions into `article_filtered`
4. publish passing articles into `final_cards`
5. update `app_meta`
6. `/api/home` reads real cards and, if necessary, supplements with mock cards to avoid a sparse homepage

In short:

`source adapters -> article_raw -> article_normalized -> article_filtered -> final_cards -> /api/home`

---

## 6. Architecture Layers

## 6.1 Source Adapter Layer

### Role

The source adapter layer converts publisher-specific feeds into a minimal shared raw-item contract.

### Current contract

Each source returns a list of `RawArticleItem` records with:

- `source`
- `feed_name`
- `title_raw`
- `url`
- `published_at_raw`
- `excerpt_raw`
- `fetched_at`

### Current source adapters

#### BBC
BBC uses RSS feeds:
- world
- business
- technology
- politics

#### NHK
NHK uses the public NHK World English list JSON and is currently scoped to:
- world
- japan
- asia
- biztch

#### NPR
NPR uses public RSS feeds and is currently scoped to:
- news
- politics
- business
- technology

### Design intent

The adapter layer is deliberately lightweight:
- no deep publisher-specific parsing,
- no article-body crawling,
- no source-specific event modeling,
- only enough shape normalization to feed the shared pipeline.

This adapter pattern is the intended baseline for future real sources.

---

## 6.2 Ingest Layer

### Role

The ingest layer fetches the current source items and persists them into `article_raw`.

### Current behavior

- initializes the database if needed
- instantiates BBC, NHK, and NPR source classes
- fetches their current items
- inserts new rows into `article_raw`
- returns source-level counts

### Current dedup behavior at ingest

`article_raw` enforces uniqueness on `(source, url)`.

This means ingest-level dedup is currently:
- **source-local**
- **URL-based**
- **not cross-source**

This is intentional at v1.

---

## 6.3 Normalize Layer

### Role

The normalize layer converts raw source records into a minimal shared article representation suitable for filtering and homepage publishing.

### Current operations

Normalization currently includes:

- HTML cleanup / text cleanup
- excerpt fallback behavior
- URL canonicalization
- published time parsing and normalization to UTC ISO format
- first-pass `topic_guess`
- first-pass `region_guess`

### Current classification method

Classification is heuristic and article-level.

Inputs used:
- source
- feed name
- title + excerpt keyword matching

### Current frozen topic buckets

The current v1 system only supports these 4 top-level topics:

- `Policy / Politics`
- `Economy / Markets`
- `Business / Tech / Industry`
- `Conflict / Security`

### Current frozen region buckets

Homepage-facing region buckets are currently:

- `North America`
- `Europe`
- `Japan / East Asia`
- `Global Markets`

### Important limitation

At v1, topic and region logic is embedded mainly in the normalize pipeline and keyword heuristics.  
The separate `topic_rules.py` and `region_rules.py` modules are still placeholders and are **not** the real source of classification truth yet.

This is an intentional marker that the rules layer is not yet fully modularized.

---

## 6.4 Filter Layer

### Role

The filter layer is the current product-quality gate.

Its job is not ranking. Its job is to decide whether a normalized article is even eligible to survive into the homepage publish pool.

### Current filter checks

The current filter layer evaluates:

- valid title
- valid excerpt
- valid URL
- 24-hour time window pass
- supported topic pass

Then applies exclusion logic for:

- obituary-like stories
- entertainment-like stories
- low-value soft stories
- non-hard-news candidates

### Current retention philosophy

The filter layer is intentionally biased toward **hard-news briefing retention**, not general-interest completeness.

It is designed to preserve:
- policy moves
- court / government / regulator actions
- conflict / security developments
- economy / market developments
- trade / tariff / supply-chain developments
- technology / chip / industrial stories
- Japan / East Asia developments important to the briefing product

### Current balancing logic

The filter rules explicitly include exceptions and wider retention support so that the homepage does not become overly narrow after strict filtering.

In practice this means:
- top stories and watchlist stay relatively strict,
- but East Asia, tech, industry, trade, and supply-chain stories get a better chance to survive,
- especially where NHK improves coverage that BBC alone would underrepresent.

### Important limitation

The filter layer is still article-level and keyword-driven.
It is not semantic ranking, not clustering, and not true editorial selection.

---

## 6.5 Publish Layer

### Role

The publish layer converts passing filtered articles into the homepage-facing `final_cards` model.

### Current operations

For each passing candidate within the 24-hour cutoff, publish currently derives:

- `event_id`
- `headline`
- `summary`
- `why_it_matters`
- `region`
- `topic`
- `status`
- `importance_score`
- `published_at`
- `updated_at`
- `source_list`
- `is_top_story`
- `is_watchlist`

### Important architectural truth

Despite the field name `event_id`, the current publish system is still **article-level**.

Current `event_id` format is:
- `bbc:{article_normalized_id}`
- `nhk:{article_normalized_id}`
- `npr:{article_normalized_id}`

So:
- one article becomes one card,
- one card becomes one pseudo-event,
- there is no cross-source event merge yet.

### Current `why_it_matters`

`why_it_matters` is currently:
- deterministic
- keyword-driven
- template-based
- not LLM-generated

This is the correct v1 behavior and should be treated as frozen for the current phase.

### Current scoring

Scoring is temporary and article-level.

The current score:
- is displayed on a 10-point-style scale,
- is based mainly on topic plus selected high-signal keywords,
- is explicitly a temporary heuristic until stronger event-level ranking exists.

### Current top story and watchlist logic

`is_top_story` currently depends on score threshold.

`is_watchlist` currently depends on:
- conflict/security topic,
- or high score plus certain ongoing-risk keywords.

This logic is provisional but frozen as the current v1 behavior.

### Important limitation

The publish layer does not yet:
- merge related source items,
- de-duplicate near-identical stories,
- compute source consensus,
- or assign event-level importance.

---

## 6.6 Homepage Composition Layer

### Role

The homepage composition layer builds the frontend payload returned by `/api/home`.

At the current freeze point, this layer also owns **homepage exposure control v0.2**.

### Frozen homepage sections

The current homepage response contains:

- `meta`
- `top_stories`
- `by_region`
- `by_topic`
- `watchlist`

### Frozen homepage caps

The current caps are:

- Top Stories: `MAX_TOP_STORIES = 8`
- Watchlist: `MAX_WATCHLIST = 4`
- By Region: `MAX_REGION_STORIES = 3` per bucket
- By Topic: `MAX_TOPIC_STORIES = 3` per bucket

### Frozen homepage buckets

#### Region
- North America
- Europe
- Japan / East Asia
- Global Markets

#### Topic
- Policy / Politics
- Economy / Markets
- Business / Tech / Industry
- Conflict / Security

### Sorting

Cards are sorted primarily by:
- `importance_score`
- `updated_at`
- `published_at`

### Exposure control v0.2

Homepage exposure control is intentionally lightweight and deterministic.

It currently does two things:

- exact article re-exposure control:
  - an article already selected into `top_stories` is not shown again in `watchlist`, `by_region`, or `by_topic`
- same-event-like suppression against `top_stories`:
  - later buckets use a title-normalization and token-overlap heuristic to reduce obvious repeated coverage of the same event

This is **not** full deduplication.
It does not merge records, change stored data, or introduce clustering.

If a bucket becomes too sparse after same-event-like suppression, the homepage falls back to ordinary eligible candidates while still keeping exact top-story article repeats excluded.

### Mock supplementation

If real cards are below the minimum threshold, the homepage merges real cards with mock cards while avoiding simple duplicate headlines.

This is a temporary UX continuity layer so the homepage does not collapse when the real-source pool is still small.

---

## 7. Data Model Freeze

## 7.1 `article_raw`

### Role
Publisher-specific raw ingest store.

### Purpose
Keeps the original source payload in a minimal shared raw schema before classification and filtering.

### Key properties
- one row per source-local URL
- unique on `(source, url)`
- preserves source and feed identity

---

## 7.2 `article_normalized`

### Role
Minimal normalized article layer.

### Purpose
Stores the shared article shape after cleanup and heuristic topic / region assignment.

### Key properties
- one normalized row per raw row
- unique on `article_raw_id`
- canonical URL stored here
- topic / region guesses frozen here for downstream use

---

## 7.3 `article_filtered`

### Role
Filter decision layer.

### Purpose
Separates article eligibility decisions from normalization and publish.

### Key properties
- one filter decision per normalized article
- records:
  - pass / fail
  - filter reason
  - time window pass
  - topic pass
  - filtered timestamp

This table is important because it preserves the decision boundary instead of making filtering a hidden in-memory step.

---

## 7.4 `final_cards`

### Role
Homepage-facing card store.

### Purpose
Stores the published card set used by `/api/home`.

### Key properties
- one published card per current pseudo-event/article
- `event_id` unique
- stores card fields already shaped for API output
- stores source list as JSON
- stores top-story and watchlist flags

### Important caveat
This is currently a **published article-card table**, not a true event table.

---

## 7.5 `app_meta`

### Role
Homepage metadata store.

### Purpose
Stores:
- last updated time
- window hours
- total published events/cards

At v1 this is a very small singleton-style metadata table.

---

## 8. Refresh Model Freeze

### Current execution model

Refresh is currently:
- manual script-driven, or
- manually triggered through `POST /api/admin/refresh`

### Current orchestration

The refresh service runs in strict sequence:

1. ingest
2. normalize
3. filter
4. publish

### Explicit non-features at v1

There is currently no:
- scheduler
- cron-like service inside the app
- background task queue
- worker pool
- retry orchestration
- source health scoring

This is acceptable and intentional for the current MVP phase.

---

## 9. Current Contracts That Should Be Treated as Frozen

The following should be treated as frozen until a deliberate v1.1 change:

### Product contract
- hard-news factual briefing focus
- 24-hour recency window
- compact homepage instead of broad aggregation

### Source contract
- adapters return `RawArticleItem`
- source-specific logic stays inside adapters, not in homepage layer

### Topic contract
Only these 4 homepage topics:
- Policy / Politics
- Economy / Markets
- Business / Tech / Industry
- Conflict / Security

### Region contract
Current homepage regions:
- North America
- Europe
- Japan / East Asia
- Global Markets

### Homepage contract
Response shape:
- meta
- top_stories
- by_region
- by_topic
- watchlist

### Quality contract
The product should remain:
- anti-soft-story
- anti-entertainment drift
- anti-obituary drift
- anti-portal-bloat

### Architecture contract
The system remains:
- simple
- local
- inspectable
- deterministic-first

---

## 10. Known Limitations at Freeze Time

The following are known and accepted in v1:

1. topic classification is heuristic and imperfect  
2. region classification is heuristic and imperfect  
3. `event_id` is article-based, not event-based  
4. cross-source duplicates can still appear  
5. ranking is temporary and not yet source-aware  
6. watchlist logic is still simple  
7. `why_it_matters` is better than a broad template, but still deterministic copy logic  
8. mock supplementation remains necessary when real volume is sparse  
9. rules modules for topic / region / scoring are not yet the canonical implementation point

These are not hidden flaws; they are explicit v1 constraints.

---

## 11. What v1 Should Not Expand Into Yet

Before v1.1, the system should **not** expand into:

- heavy event clustering
- embedding-based dedup
- generalized summarization
- full LLM rewrite layer
- user personalization
- large topic taxonomy expansion
- admin CMS complexity
- production infra complexity

That would increase architectural surface area before the current deterministic multi-source core is stable enough.

---

## 12. v1 Exit Condition

This v1 freeze should remain valid until one of the following is intentionally changed:

- a 4th real source is added,
- homepage duplicate control moves beyond the current exposure-control-only v0.1 layer,
- scoring becomes source-aware or event-aware,
- the topic / region rules move into mature dedicated rule modules,
- or `final_cards` stops behaving as an article-level pseudo-event store.

Until then, this document is the baseline architecture reference.
