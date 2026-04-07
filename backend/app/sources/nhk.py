"""Minimal NHK World English news connector backed by the public list JSON."""

from datetime import datetime, timezone
import json
from urllib.parse import urljoin
from urllib.request import urlopen

from .base import BaseSource, RawArticleItem


NHK_NEWS_LIST_URL = "https://www3.nhk.or.jp/nhkworld/data/en/news/all.json"
NHK_PAGE_BASE_URL = "https://www3.nhk.or.jp"

# Keep the source scoped to the NHK World English sections that fit the MVP.
NHK_CATEGORY_MAP = {
    "WORLD": "world",
    "JAPAN": "japan",
    "ASIA": "asia",
    "BIZTCH": "biztch",
}


class NHKSource(BaseSource):
    name = "nhk"

    def fetch_items(self) -> list[RawArticleItem]:
        fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        payload = json.loads(urlopen(NHK_NEWS_LIST_URL, timeout=20).read().decode("utf-8", "ignore"))
        items: list[RawArticleItem] = []
        seen_urls: set[str] = set()

        for entry in payload.get("data", []):
            category_name = str(entry.get("categories", {}).get("name", "")).upper()
            feed_name = NHK_CATEGORY_MAP.get(category_name)
            page_url = urljoin(NHK_PAGE_BASE_URL, str(entry.get("page_url", "")).strip())

            if not feed_name or not page_url or page_url in seen_urls:
                continue

            seen_urls.add(page_url)
            items.append(
                RawArticleItem(
                    source=self.name,
                    feed_name=feed_name,
                    title_raw=str(entry.get("title", "")).strip(),
                    url=page_url,
                    published_at_raw=str(entry.get("updated_at", "")).strip(),
                    excerpt_raw=str(entry.get("description", "")).strip(),
                    fetched_at=fetched_at,
                )
            )

        return items
