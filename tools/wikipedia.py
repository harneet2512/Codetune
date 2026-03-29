"""Deterministic fact lookup tool."""

from __future__ import annotations

from tooltune.io import load_json
from tooltune.paths import DATA_DIR

FACTS = load_json(DATA_DIR / "wikipedia_facts.json")


def normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def run(query: str) -> str:
    normalized = normalize_query(query)
    if normalized in FACTS:
        return FACTS[normalized]

    for key, value in FACTS.items():
        if normalized in key or key in normalized:
            return value

    return '{"error": "No results found for query"}'
