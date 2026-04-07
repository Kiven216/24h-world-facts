"""Base contracts for future news source connectors."""


class BaseSource:
    name = "base"

    def fetch_items(self) -> list[dict]:
        """Return source items when real ingestion is implemented."""
        return []

