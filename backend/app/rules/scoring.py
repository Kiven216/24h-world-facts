"""Placeholder scoring rules."""


def calculate_importance(item: dict) -> float:
    return float(item.get("importance_score", 0))

