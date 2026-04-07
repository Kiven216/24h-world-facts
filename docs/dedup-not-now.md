# 24H World Facts — Why Cross-Source Dedup Is Not a v1 Task

## 1. Purpose

This document records a deliberate architecture decision:

**Cross-source deduplication should not be implemented yet in v1.**

This is not because deduplication is unimportant.
It is because the current system has not yet reached the point where dedup is the highest-value next move.

The correct next step is:
- stabilize the current deterministic multi-source architecture,
- add one more real source,
- observe the real duplicate pattern,
- then introduce a lightweight homepage duplicate-control layer in v1.1 or shortly after.

---

## 2. Current Truth About the System

The current system is:

- multi-source
- real-source
- article-level
- heuristic-classification-based
- deterministic-first
- homepage-capped
- still using temporary article-level scoring

It is **not** yet:
- event-level,
- source-consensus-aware,
- embedding-based,
- or cluster-based.

This matters because dedup is easiest to overbuild when the system is still immature.

---

## 3. Why Dedup Is Not the Best Immediate Next Step

## 3.1 There are only two real sources today

Current real sources:
- BBC
- NHK

At this stage, duplication exists, but it is still limited enough to tolerate while the system remains small.

This means the current problem is real but not yet severe enough to justify adding a new architecture layer immediately.

---

## 3.2 The duplicate pattern is not fully visible yet

If dedup were implemented now, it would be based on only a partial view of future duplication behavior.

But the real duplication pattern will change materially once a 3rd and 4th source exist.

Examples:
- BBC vs NHK duplicate patterns
- BBC vs NPR duplicate patterns
- BBC vs Reuters/AP duplicate patterns
- specialist-source vs broad-source duplicate patterns

Designing dedup too early risks locking in rules that are specific to the current two-source phase and will need to be revised soon.

---

## 3.3 The current product bottleneck is still source mix and architecture stabilization

The current system benefits more from:
- source mix improvement,
- architecture freeze,
- stronger ranking logic,
- and cleaner source expansion discipline

than from early dedup sophistication.

In other words:
the system still gains more from choosing the right stories than from merging near-identical ones perfectly.

---

## 3.4 Current cards are article-level, not true events

The publish layer currently emits one card per passing article.

`event_id` is only a pseudo-event ID:
- `bbc:{article_normalized_id}`
- `nhk:{article_normalized_id}`

This means the system currently lacks a real event identity model.

Adding heavier dedup on top of article-level pseudo-events too early would create awkward logic:
- duplicate suppression without stable event identity,
- similarity logic without cluster semantics,
- cross-source merging without a trustworthy canonical event layer.

That is possible, but premature.

---

## 3.5 Early dedup can hide more important architecture problems

If dedup is added too early, it can mask issues such as:

- poor source complementarity
- weak topic / region classification
- overbroad source selection
- poor homepage ranking
- unstable bucket balance

These issues should remain visible long enough to be corrected directly.

Dedup should not become a bandage for upstream weakness.

---

## 4. Why “Not Now” Does Not Mean “Not Needed”

Cross-source dedup **will** be needed.

As the source count grows, the following problems will expand:

- same event appearing multiple times across homepage sections
- same event represented by different publisher headlines
- top stories feeling repetitive
- regional or topical buckets being occupied by near-identical variants
- noisy source overlap reducing homepage precision

So the decision is not:
“dedup is unnecessary.”

The decision is:
“dedup should be introduced at the right maturity point.”

---

## 5. The Correct Timing for Dedup

Dedup should begin when at least one of these becomes true:

1. a 3rd real source is integrated and homepage repetition becomes noticeable  
2. top stories regularly show near-duplicate cards from different sources  
3. bucket diversity starts degrading due to repeated event variants  
4. source expansion is slowed not by source integration but by repetition pressure

In practical terms, the most likely trigger is:

**after the 3rd source is added and validated.**

---

## 6. What Should Be Built First When Dedup Begins

When dedup begins, it should start as **lightweight homepage duplicate control**, not full event clustering.

This distinction is important.

### Do first
- headline similarity checks
- entity + action-word near-match checks
- same-source-date / same-region / same-topic suppression heuristics
- top-stories duplicate suppression
- controlled retention of only one dominant version in the most prominent homepage slots

### Do not do first
- embedding-based clustering
- graph-based event modeling
- full canonical event resolution
- source-consensus summarization
- multi-stage cluster ranking pipelines

The first dedup system should be small, legible, and homepage-oriented.

---

## 7. What the First Dedup Layer Should Try to Achieve

The first dedup layer should aim for:

### 7.1 Better homepage distinctness
Top Stories should feel like a set of different developments, not multiple headlines about the same development.

### 7.2 Better section diversity
By Region and By Topic should show more distinct signals rather than publisher repetition.

### 7.3 Limited, not absolute, suppression
Dedup should not mean “delete every similar card.”

Sometimes different sources add different value:
- one headline captures the policy action,
- another captures the market or regional implication.

So the right model is:
- suppress duplication in the most prominent slots,
- allow selective secondary retention where it adds viewpoint or follow-up value.

---

## 8. What Dedup Should Not Become

At the first implementation stage, dedup should not become:

- a large infrastructure project
- an opaque ML pipeline
- a cluster graph system
- an excuse to delay source expansion forever
- a replacement for better ranking
- a replacement for better source choice

Dedup is a quality-control layer, not the product core.

The product core is still:
- selecting important recent factual developments,
- filtering noise,
- and presenting a compact briefing homepage.

---

## 9. Interim Strategy Before Dedup Exists

Until dedup is implemented, the system should rely on:

- strong homepage caps
- good source discipline
- selective source expansion
- strict filtering
- controlled top-story thresholds
- visible manual observation of repeated patterns

This is sufficient for the current phase.

The existing homepage cap strategy is already part of why dedup can wait briefly without the homepage becoming unbounded.

---

## 10. Decision Summary

### Current decision
Do **not** implement cross-source dedup in v1.

### Reason
The system is still:
- only two real sources deep,
- article-level,
- heuristic-based,
- and better served by source expansion plus architecture stabilization first.

### Revisit trigger
Revisit dedup immediately after:
- the 3rd source is integrated,
- or homepage repetition becomes visibly intrusive.

### First implementation scope
When dedup begins, start with:
- lightweight headline / entity duplicate suppression,
- homepage prominence control,
- and top-story repeat reduction.

Not with heavy clustering.

---

## 11. One-line Summary

Cross-source dedup is necessary in the medium term, but it is not the correct immediate next step; the right move is to stabilize v1, add one more real source, observe real duplicate behavior, and then implement a lightweight homepage duplicate-control layer rather than a heavy clustering system.