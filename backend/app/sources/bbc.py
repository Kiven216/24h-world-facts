"""Minimal BBC RSS connector for the first real ingest path."""

from datetime import datetime, timezone

import feedparser

from .base import BaseSource, RawArticleItem


BBC_FEEDS = {
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "politics": "https://feeds.bbci.co.uk/news/politics/rss.xml",
}


class BBCSource(BaseSource):
    name = "bbc"

    def fetch_items(self) -> list[RawArticleItem]:
        fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        items: list[RawArticleItem] = []

        for feed_name, feed_url in BBC_FEEDS.items():
            parsed_feed = feedparser.parse(feed_url)

            for entry in parsed_feed.entries:
                items.append(
                    RawArticleItem(
                        source=self.name,
                        feed_name=feed_name,
                        title_raw=str(entry.get("title", "")).strip(),
                        url=str(entry.get("link", "")).strip(),
                        published_at_raw=str(entry.get("published", "") or entry.get("updated", "")).strip(),
                        excerpt_raw=str(entry.get("summary", "") or entry.get("description", "")).strip(),
                        fetched_at=fetched_at,
                    )
                )

        return items
