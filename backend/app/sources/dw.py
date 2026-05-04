"""Minimal DW English RSS connector used as a feature-flagged trial source."""

from datetime import datetime, timezone

import feedparser

from .base import BaseSource, RawArticleItem


DW_ENABLED_FEEDS = {
    "business": "https://rss.dw.com/rdf/rss-en-bus",
    "germany": "https://rss.dw.com/rdf/rss-en-ger",
}

# Keep the broader feed visible for future trial tuning, but do not enable it
# by default in v0.1 because it is more likely to introduce soft or duplicate items.
DW_OPTIONAL_FEEDS = {
    "all": "https://rss.dw.com/rdf/rss-en-all",
}


class DWSource(BaseSource):
    name = "dw"

    def fetch_items(self) -> list[RawArticleItem]:
        fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        items: list[RawArticleItem] = []

        for feed_name, feed_url in DW_ENABLED_FEEDS.items():
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
