"""Training utilities."""

from __future__ import annotations

import json
from pathlib import Path


def load_jsonl(path: str | Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def count_parameters(model) -> tuple[int, int]:
    """Return (trainable_params, total_params)."""
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    return trainable, total
