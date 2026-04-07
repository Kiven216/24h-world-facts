# 24H World Facts — Source Evaluation for v1.1

## Status Update

NPR was selected as the first v1.1 third-source candidate.

Its minimum adapter validation has now been completed:
- the NPR source adapter has been added
- NPR now runs through the existing `ingest -> normalize -> filter -> publish` chain
- homepage visibility through `/api/home` has been confirmed

The current next step is observation, not immediate full promotion.

This means NPR is now treated as:
- a validated third-source candidate already connected to the product
- a source under manual observation
- not yet a fully established stable source

## 1. Purpose

This document defines how new real sources should be evaluated for **v1.1**.

At v1, the system already has two real sources:
- BBC
- NHK World English

The next step is not “add as many sources as possible.”
The next step is to add the **right** 3rd source in a way that improves coverage without breaking homepage quality, increasing duplication too aggressively, or forcing premature complexity.

---

## 2. Current Source Baseline

## 2.1 BBC

### Current value
BBC is currently the main general hard-news backbone.

It contributes reliable coverage across:
- world developments
- politics / policy
- business
- technology

### Current strengths
- broad international range
- stable structured RSS feeds
- low adapter friction
- suitable for hard-news briefing use

### Current limitations
- can underrepresent East Asia emphasis relative to product needs
- can drift toward broad mainstream world coverage without enough regional specialty depth
- alone, it does not guarantee stable Japan / East Asia representation

---

## 2.2 NHK World English

### Current value
NHK is currently the regional specialist source that materially improves:
- Japan coverage
- East Asia coverage
- selected business / technology / industry coverage tied to the region

### Current strengths
- strong supplement for Japan / East Asia
- improves balance where BBC alone can leave gaps
- useful for trade / manufacturing / regional policy read-through
- fits the briefing product better than a generic “more content” source

### Current limitations
- narrower global breadth than BBC
- not a full replacement for a broad wire-like source
- as a second source, it improves balance but does not yet create a fully rounded 3-source global mix

---

## 3. Why v1.1 Should Add Exactly One New Real Source First

v1.1 should prefer adding **one** well-chosen new real source, not several.

Reason:

1. the current architecture is still article-level  
2. there is no cross-source duplicate control yet  
3. there is no event clustering yet  
4. source weighting is still immature  
5. adding many sources at once would increase noise faster than quality

So v1.1 should ask:

- which source fills the most important current gap?
- which source fits the current lightweight adapter pattern?
- which source gives the best coverage gain per unit of complexity?

---

## 4. Source Evaluation Criteria

Any candidate source for v1.1 should be judged on these dimensions.

## 4.1 Coverage complementarity

A new source should fill a real gap, not merely repeat BBC.

Examples of useful complementarity:
- stronger North America public-policy coverage
- stronger hard-news wire coverage
- better business / market / policy continuity
- better international policy framing

A source that mostly duplicates BBC headlines without adding a different strength is lower priority.

---

## 4.2 Hard-news fit

The product is a factual briefing tool, not a broad media reader.

So a source is preferable when it naturally contributes:
- policy actions
- court / regulator / government developments
- economy / markets
- industry / technology
- conflict / security
- major public-health hard news where relevant

Sources that lean heavily toward:
- lifestyle,
- culture,
- opinion,
- personal storytelling,
- or soft magazine-style features

will impose more filtering pressure and reduce quality efficiency.

---

## 4.3 Adapter simplicity

At v1.1, source integration should still be simple.

Preferred:
- stable RSS feed
- public list JSON
- predictable structured markup
- minimal need for article-page crawling

Not preferred yet:
- brittle scraping
- complicated anti-bot workarounds
- heavy page-render dependence
- frequent parser break risk

The source adapter layer should remain lightweight.

---

## 4.4 Duplicate pressure

The source should be evaluated not only on its own quality, but on how much it increases duplicate pressure before dedup exists.

A source that adds coverage while creating tolerable duplication is more suitable than a source that floods the homepage with near-identical versions of already-covered events.

---

## 4.5 Region / topic fit with current homepage buckets

The current homepage is intentionally small and uses only:

### Regions
- North America
- Europe
- Japan / East Asia
- Global Markets

### Topics
- Policy / Politics
- Economy / Markets
- Business / Tech / Industry
- Conflict / Security

So the best next source is one that fits these buckets naturally.

A source requiring an expanded taxonomy immediately is less suitable for v1.1.

---

## 5. Recommended v1.1 Candidate Order

## 5.1 Recommended first choice: NPR

### Why NPR is the best current fit

NPR is a strong v1.1 candidate because it likely offers:

- useful North America and U.S. public-policy reinforcement
- public-media style reporting that is usually more compatible with briefing use than many commercial softer sources
- a complement to BBC rather than a total duplicate of BBC
- lower integration friction than many more ambitious sources
- a better coverage triangle with BBC + NHK:
  - BBC = broad global backbone
  - NHK = East Asia specialist
  - NPR = North America / U.S. policy-public-media complement

### Why NPR is attractive now
NPR is not being chosen because it is “bigger” or “more prestigious.”
It is being chosen because it may improve the current source mix with manageable complexity.

### What to validate before final adoption
Before finalizing NPR, validate:

- feed stability
- adapter simplicity
- hard-news density
- homepage duplicate pressure versus BBC
- actual improvement in North America / policy balance

---

## 5.2 Second-tier candidate: Reuters or AP

### Why Reuters / AP are attractive
Reuters or AP would strengthen:
- hard-news backbone
- international policy / market urgency
- more wire-like “factual event layer”

### Why they are not the immediate first recommendation
They are not first recommendation **at this phase** because:

- public-access integration path may be less straightforward
- implementation friction may be higher than BBC/NHK/NPR-style adapters
- before dedup exists, wire-like overlap can increase duplicate pressure quickly
- the current architecture still lacks event-level controls

### Strategic interpretation
Reuters / AP remain strong future candidates, but are better added when:
- the 3-source baseline is already stable,
- or homepage duplicate suppression has begun.

---

## 5.3 Lower-priority categories for now

These are lower priority for v1.1:

- sources dominated by lifestyle / features
- sources that require brittle scraping
- sources whose main value would require topic expansion immediately
- sources with very high overlap but little complementarity
- sources that would push the product toward a portal rather than a briefing

---

## 6. How the 3rd Source Should Be Judged After Integration

After integrating a 3rd source, success should not be measured by raw article volume.

It should be judged by these product-facing outcomes:

### 6.1 Coverage improvement
Does the homepage gain better representation in under-covered buckets?

Examples:
- North America
- policy follow-through
- selected markets / industry continuity

### 6.2 Quality retention
Does the homepage remain selective, compact, and briefing-like?

### 6.3 Duplicate pressure
Does the source create tolerable duplication, or does it immediately make homepage repetition obvious?

### 6.4 Classification stability
Does the source fit current topic / region heuristics reasonably well, or does it generate excessive misclassification?

### 6.5 Adapter maintainability
Does it fit the current lightweight source-adapter model?

---

## 7. What v1.1 Should Not Do During Source Expansion

When the 3rd source is added, v1.1 should **not** simultaneously do all of the following:

- add several more sources
- redesign the entire topic taxonomy
- introduce LLM summarization
- rebuild ranking from scratch
- add heavy clustering
- add full event graph logic

That would make it too hard to see what the source itself improved or broke.

---

## 8. Recommended Decision

### Current recommendation
For v1.1, the preferred sequence is:

1. prepare 3rd-source evaluation
2. integrate one new source only
3. validate homepage behavior
4. observe it in production-like local refresh cycles
5. then begin light duplicate control afterward

### Best current 3rd-source candidate
**NPR**

### Rationale
NPR currently offers the best balance of:
- complementarity
- manageable adapter complexity
- likely hard-news usefulness
- acceptable fit with current homepage buckets
- lower risk of prematurely forcing a heavier architecture

### Current phase
NPR has now passed minimum integration validation and moved into an observation phase.

That means the current decision is no longer “whether NPR can be connected.”
The current decision is:

- whether NPR should be kept after observation
- whether overlap with BBC remains acceptable
- whether it continues to improve North America / policy / tech coverage without materially lowering homepage quality

Reuters and AP remain relevant later candidates, but they should stay in the queue until the NPR observation phase is complete.

---

## 9. One-line Summary

v1.1 selected **NPR** as the first third-source candidate; minimum validation is complete, homepage visibility is confirmed, and the source is now in observation phase rather than fully established stable-source status.
