# NPR Source Validation

## Scope

This is a minimal, reversible validation of NPR as a third real source inside the existing v1 pipeline:

`ingest -> normalize -> filter -> publish`

The validation keeps the current source adapter contract, does not crawl article bodies, does not add deduplication, and does not expand homepage buckets or taxonomy.

## Chosen NPR Entrypoints

The validation uses four public RSS feeds:

- `news` -> `https://feeds.npr.org/1001/rss.xml`
- `politics` -> `https://feeds.npr.org/1014/rss.xml`
- `business` -> `https://feeds.npr.org/1006/rss.xml`
- `technology` -> `https://feeds.npr.org/1019/rss.xml`

## Why These Entrypoints

- They fit the existing project focus: general news, politics, business/economy, and technology.
- They align with the current `feed_name` mapping style already used by BBC and NHK.
- They are standard RSS endpoints, which means they fit the current `feedparser`-based adapter pattern with minimal code.
- They allow validation without introducing section-page scraping or unstable client-side JSON parsing.

## Entrypoints Explicitly Not Used

These categories were intentionally left out during validation:

- Culture / arts
- Podcasts / shows / radio program feeds
- Lifestyle / softer human-interest sections
- Opinion / commentary-oriented sections

They were excluded because they are more likely to introduce soft content that conflicts with the current hard-news filtering goals.

## Expected Bucket Contribution

If retained as a formal third source, NPR is most likely to strengthen:

- `North America`
- `Policy / Politics`
- `Economy / Markets`
- `Business / Tech / Industry`

It is less likely to materially strengthen:

- `Japan / East Asia`

That remains a better fit for NHK.

## Expected Repeat Patterns vs. BBC

The most likely overlap patterns are:

- U.S. politics and election coverage
- Federal court / regulatory / executive-branch stories
- Inflation, tariffs, growth, and central-bank-adjacent market stories
- AI, platform, cybersecurity, and major technology policy stories

At the current stage, this overlap is acceptable because the product still does not perform cross-source event clustering or deduplication.

## Current Recommendation

NPR appears viable for a minimal third-source validation because it offers public RSS endpoints that fit the existing adapter model.

However, it should be kept in an observation phase first, because:

- `news` is broad and may introduce a higher share of domestic U.S. general-interest stories.
- NPR is more likely than NHK to overlap with BBC on politics, business, and technology headlines.
- The current pipeline still treats one article as one final card, so duplicate event coverage can accumulate across sources.

## Validation Outcome

If the refresh pipeline continues to ingest and filter NPR cleanly during manual observation, NPR is a reasonable candidate to keep as the formal third source.

Current status:

`Completed minimal integration validation; ready for manual observation.`

## Current Status

- minimum integration validation passed
- `/api/home` homepage display has been confirmed
- NPR is now in observation phase
- the final keep / revert / formalize decision is still pending
