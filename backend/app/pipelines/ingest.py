"""Ingest the first real source and persist raw BBC RSS articles."""

from dataclasses import asdict

from ..db import init_database, insert_article_raw
from ..sources.bbc import BBCSource


def run_ingest() -> dict[str, int]:
    init_database()
    source = BBCSource()
    items = source.fetch_items()
    inserted = insert_article_raw([asdict(item) for item in items])
    return {"fetched_count": len(items), "inserted_count": inserted}
