# Holiday Observation Pack v0.3

## Current Scope

This pack extends the current homepage observation workflow with:

- cross-source deduplication refinement
- homepage debug visibility
- signal tags for lightweight card inspection
- a trial DW English source for short observation windows

## DW Trial Source

DW is added here as a **trial source**, not a stable fourth source.

Enabled trial feeds in v0.1:

- DW Business: `https://rss.dw.com/rdf/rss-en-bus`
- DW Germany: `https://rss.dw.com/rdf/rss-en-ger`

Not enabled by default in this pack:

- DW All: `https://rss.dw.com/rdf/rss-en-all`

Reason:

- Business and Germany are the cleaner first test for Europe / Germany / economy coverage
- the broader all-feed is more likely to increase duplicate pressure and soft-content leakage

Runtime control:

- `ENABLE_DW_SOURCE=true` enables DW ingest
- with the flag off, the current stable set remains BBC + NHK + NPR

## Not Done In This Pack / Future To Do

- DW is a trial source, not yet a stable fourth source.
- AP / Reuters are not added because their stable official access is more complex than lightweight RSS.
- Full event clustering is not implemented.
- Embedding-based similarity is not implemented.
- LLM-based deduplication is not implemented.
- Source-aware ranking is not implemented.
- Topic taxonomy expansion is not implemented.
- Signal tags are display-only and do not affect ranking.
- DW quality, duplicate pressure, and fit should be observed for 2–3 days before deciding whether to keep it.
