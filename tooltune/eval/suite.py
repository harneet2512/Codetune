"""EvalSuite — load and manage collections of eval cases from YAML/JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import yaml

from tooltune.eval.schema import EvalCase, TraceRecord


class EvalSuite:
    """A named collection of eval cases loaded from one or more files.

    Supports YAML and JSON. Files may contain a list of cases at the top level,
    or a dict with a ``cases`` key.
    """

    def __init__(self, name: str, cases: list[EvalCase] | None = None) -> None:
        self.name = name
        self.cases: list[EvalCase] = cases or []

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> "EvalSuite":
        """Load a suite from a single YAML or JSON file."""
        p = Path(path)
        raw = _load_raw(p)
        cases = _parse_cases(raw)
        return cls(name=p.stem, cases=cases)

    @classmethod
    def load_dir(cls, directory: str | Path, pattern: str = "*.yaml") -> "EvalSuite":
        """Load all matching files in a directory into one suite."""
        d = Path(directory)
        if not d.is_dir():
            raise FileNotFoundError(f"Suite directory not found: {d}")

        all_cases: list[EvalCase] = []
        for fp in sorted(d.glob(pattern)):
            raw = _load_raw(fp)
            all_cases.extend(_parse_cases(raw))

        # Also pick up JSON files if the pattern is YAML-only.
        if pattern in ("*.yaml", "*.yml"):
            for fp in sorted(d.glob("*.json")):
                raw = _load_raw(fp)
                all_cases.extend(_parse_cases(raw))

        return cls(name=d.name, cases=all_cases)

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.cases)

    def __iter__(self) -> Iterator[EvalCase]:
        return iter(self.cases)

    def __getitem__(self, index: int) -> EvalCase:
        return self.cases[index]

    def by_id(self, case_id: str) -> EvalCase | None:
        """Look up a case by its id."""
        for case in self.cases:
            if case.id == case_id:
                return case
        return None

    def filter(
        self,
        *,
        category: str | None = None,
        difficulty: str | None = None,
        tags: list[str] | None = None,
    ) -> list[EvalCase]:
        """Return cases matching the given filters."""
        result = self.cases
        if category:
            result = [c for c in result if c.category == category]
        if difficulty:
            result = [c for c in result if c.difficulty == difficulty]
        if tags:
            tag_set = set(tags)
            result = [c for c in result if tag_set.issubset(set(c.tags))]
        return result

    @property
    def categories(self) -> list[str]:
        return sorted({c.category for c in self.cases})

    @property
    def difficulties(self) -> list[str]:
        return sorted({c.difficulty for c in self.cases})


# ------------------------------------------------------------------
# Trace loading helpers
# ------------------------------------------------------------------


def load_traces(path: str | Path) -> list[TraceRecord]:
    """Load model traces from a JSON file.

    Expects a JSON array of objects, each with at least ``id`` and ``tool_calls``.
    """
    p = Path(path)
    with open(p, encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        return [TraceRecord.model_validate(item) for item in raw]
    if isinstance(raw, dict) and "traces" in raw:
        return [TraceRecord.model_validate(item) for item in raw["traces"]]
    raise ValueError(f"Unexpected trace format in {p}")


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _load_raw(path: Path) -> list[dict] | dict:
    with open(path, encoding="utf-8") as f:
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f)
        return json.load(f)


def _parse_cases(raw: list | dict) -> list[EvalCase]:
    if isinstance(raw, list):
        return [EvalCase.model_validate(item) for item in raw]
    if isinstance(raw, dict):
        items = raw.get("cases", raw.get("items", []))
        return [EvalCase.model_validate(item) for item in items]
    raise ValueError(f"Cannot parse eval cases from {type(raw)}")
