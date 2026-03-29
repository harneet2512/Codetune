"""Deterministic weather lookup tool."""

from __future__ import annotations

import json

from tooltune.io import load_json
from tooltune.paths import DATA_DIR

WEATHER = load_json(DATA_DIR / "weather.json")


def run(city: str) -> str:
    normalized = city.strip().lower()
    if normalized not in WEATHER:
        return '{"error": "No weather data found for city"}'
    return json.dumps(WEATHER[normalized], ensure_ascii=True)
