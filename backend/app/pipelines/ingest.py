"""Ingest the current real sources and persist raw source items."""

from dataclasses import asdict

from ..db import init_database, insert_article_raw
from ..sources.bbc import BBCSource
from ..sources.nhk import NHKSource


def run_ingest() -> dict[str, object]:
    init_database()
    fetched_count = 0
    inserted_count = 0
    source_stats: dict[str, dict[str, int]] = {}

    for source in (BBCSource(), NHKSource()):
        items = source.fetch_items()
        inserted = insert_article_raw([asdict(item) for item in items])
        fetched_count += len(items)
        inserted_count += inserted
        source_stats[source.name] = {
            "fetched_count": len(items),
            "inserted_count": inserted,
        }

    return {
        "fetched_count": fetched_count,
        "inserted_count": inserted_count,
        "sources": source_stats,
    }
