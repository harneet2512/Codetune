"""Live-tool registry: same 5 tool schemas as ToolRegistry, but weather and
wikipedia call real public APIs (Open-Meteo + Wikipedia REST, both keyless).
calculator, code_executor, and unit_converter are already real
implementations, not simulators — they are reused unchanged.

Because live observations are non-static, traces from this registry are
scored by faithfulness-to-observation (scripts/score_live.py) rather than
the canned ground truths.
"""

from __future__ import annotations

import json
import random
import urllib.parse

import requests

from tooltune.contracts import ToolCall, ToolObservation

from . import calculator, code_executor, unit_converter
from .registry import ToolSpec

_UA = {"User-Agent": "restraint-7b-eval/1.0 (github.com/harneet2512/Codetune)"}


def _get_json(url: str, timeout: int = 15) -> dict:
    r = requests.get(url, headers=_UA, timeout=timeout)
    r.raise_for_status()
    return r.json()


def live_weather(city: str) -> str:
    """Open-Meteo: geocode city -> current conditions. No API key."""
    geo = _get_json(
        "https://geocoding-api.open-meteo.com/v1/search?name="
        + urllib.parse.quote(city)
        + "&count=1&language=en&format=json"
    )
    results = geo.get("results") or []
    if not results:
        return json.dumps({"error": f"Unknown city: {city}"})
    loc = results[0]
    wx = _get_json(
        "https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}"
        "&current=temperature_2m,weather_code,wind_speed_10m&temperature_unit=celsius"
        .format(loc["latitude"], loc["longitude"])
    )
    cur = wx.get("current", {})
    return json.dumps(
        {
            "city": loc.get("name", city),
            "country": loc.get("country", ""),
            "temperature_c": cur.get("temperature_2m"),
            "wind_kmh": cur.get("wind_speed_10m"),
            "weather_code": cur.get("weather_code"),
            "source": "open-meteo (live)",
        }
    )


_WMO = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    85: "Light snow showers", 86: "Snow showers", 95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def live_weather_text(city: str) -> str:
    raw = json.loads(live_weather(city))
    if "error" in raw:
        return json.dumps(raw)
    raw["condition"] = _WMO.get(raw.get("weather_code"), "Unknown")
    return json.dumps(raw)


def live_wikipedia(query: str) -> str:
    """Wikipedia REST summary API. No API key."""
    title = urllib.parse.quote(query.replace(" ", "_"))
    try:
        data = _get_json(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
        )
    except Exception:
        # fall back to search -> first hit
        hits = _get_json(
            "https://en.wikipedia.org/w/rest.php/v1/search/title?q="
            + urllib.parse.quote(query)
            + "&limit=1"
        )
        pages = hits.get("pages") or []
        if not pages:
            return json.dumps({"error": f"No results found for query: {query}"})
        data = _get_json(
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(pages[0]["title"])
        )
    extract = data.get("extract", "")
    if not extract:
        return json.dumps({"error": f"No summary for: {query}"})
    return json.dumps(
        {
            "title": data.get("title", query),
            "summary": extract[:600],
            "source": "en.wikipedia.org REST (live)",
        }
    )


class LiveToolRegistry:
    """Drop-in replacement for ToolRegistry backed by live APIs where the
    simulated tools had canned data."""

    def __init__(self) -> None:
        self._tools = {
            "calculator": (
                ToolSpec(
                    name="calculator",
                    description="Evaluates a mathematical expression and returns the result.",
                    parameters={"expression": {"type": "string", "description": "Math expression"}},
                ),
                lambda a: calculator.run(a["expression"]),
            ),
            "wikipedia": (
                ToolSpec(
                    name="wikipedia",
                    description="Looks up a topic and returns a short factual summary.",
                    parameters={"query": {"type": "string", "description": "Topic to look up"}},
                ),
                lambda a: live_wikipedia(a["query"]),
            ),
            "weather": (
                ToolSpec(
                    name="weather",
                    description="Returns current weather for a city.",
                    parameters={"city": {"type": "string", "description": "City name"}},
                ),
                lambda a: live_weather_text(a["city"]),
            ),
            "code_executor": (
                ToolSpec(
                    name="code_executor",
                    description="Runs Python code and returns stdout/stderr.",
                    parameters={"code": {"type": "string", "description": "Python code to execute"}},
                ),
                lambda a: code_executor.run(a["code"]),
            ),
            "unit_converter": (
                ToolSpec(
                    name="unit_converter",
                    description="Converts a value from one unit to another.",
                    parameters={
                        "value": {"type": "number", "description": "Value to convert"},
                        "from_unit": {"type": "string", "description": "Source unit"},
                        "to_unit": {"type": "string", "description": "Target unit"},
                    },
                ),
                lambda a: unit_converter.run(
                    float(a["value"]), a["from_unit"], a["to_unit"]
                ),
            ),
        }

    def tool_definitions(self):
        return [spec.to_openai_json() for spec, _ in self._tools.values()]

    def execute(
        self,
        tool_call: ToolCall,
        inject_errors: bool = False,
        error_probability: float = 0.2,
        random_seed: int | None = None,
    ) -> ToolObservation:
        if tool_call.name not in self._tools:
            return ToolObservation(
                tool_name=tool_call.name,
                content=json.dumps({"error": "Unknown tool"}),
                is_error=True,
            )
        _, runner = self._tools[tool_call.name]
        try:
            content = runner(tool_call.arguments)
        except Exception as e:  # live APIs fail in real ways: timeouts, 429, 404
            return ToolObservation(
                tool_name=tool_call.name,
                content=json.dumps({"error": f"{type(e).__name__}: {e}"}),
                is_error=True,
            )
        is_error = '"error"' in content.lower()
        return ToolObservation(tool_name=tool_call.name, content=content, is_error=is_error)
