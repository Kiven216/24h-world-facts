"""Minimal NPR RSS connector used for exploratory third-source validation."""

from datetime import datetime, timezone

import feedparser

from .base import BaseSource, RawArticleItem


# These feeds map closely to the existing homepage taxonomy without adding
# new source-specific contracts. This stays intentionally narrow for validation.
NPR_FEEDS = {
    "news": "https://feeds.npr.org/1001/rss.xml",
    "politics": "https://feeds.npr.org/1014/rss.xml",
    "business": "https://feeds.npr.org/1006/rss.xml",
    "technology": "https://feeds.npr.org/1019/rss.xml",
}


class NPRSource(BaseSource):
    name = "npr"

    def fetch_items(self) -> list[RawArticleItem]:
        fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        items: list[RawArticleItem] = []

        for feed_name, feed_url in NPR_FEEDS.items():
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
