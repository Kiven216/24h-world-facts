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

NPR has passed the minimum validation window and the initial observation phase.

It should now be retained as the stable third source because:

- the public RSS integration path has remained simple and usable
- homepage visibility has been confirmed consistently
- North America / U.S. complement value is real
- no material low-fit or soft-story drift was observed during the observation window

The main caveat remains that NPR is a complement source, not necessarily the fastest-refreshing source in the stack.

## Validation Outcome

The refresh pipeline ingests and filters NPR cleanly enough to retain it as the formal stable third source.

Current status:

`Completed minimal integration validation and passed the initial observation window.`

## Current Status

- minimum integration validation passed
- `/api/home` homepage display has been confirmed
- homepage display confirmation has been followed by stable observation
- NPR is now retained as the stable third source
- the remaining open work is homepage duplicate/exposure control, not source keep/revert status
