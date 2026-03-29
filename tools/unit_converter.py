"""Deterministic unit conversion tool."""

from __future__ import annotations


def run(value: float, from_unit: str, to_unit: str) -> str:
    source = from_unit.strip().lower()
    target = to_unit.strip().lower()

    if source == "celsius" and target == "fahrenheit":
        return str(round((value * 9 / 5) + 32, 2))
    if source == "fahrenheit" and target == "celsius":
        return str(round((value - 32) * 5 / 9, 2))
    if source == "pounds" and target in {"kilograms", "kg"}:
        return str(round(value * 0.453592, 4))
    if source in {"kilometers", "km"} and target == "miles":
        return str(round(value * 0.621371, 4))
    if source == "miles" and target in {"kilometers", "km"}:
        return str(round(value / 0.621371, 4))
    if source == "gallons" and target == "liters":
        return str(round(value * 3.78541, 4))
    return '{"error": "Unsupported unit conversion"}'
