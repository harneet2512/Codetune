"""Resolved project paths used by ToolTune modules."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = ROOT / "configs" / "tooltune"
DATA_DIR = ROOT / "tooltune_data"
TASKS_DIR = ROOT / "tasks"
PLAYGROUND_DATA_DIR = ROOT / "playground" / "data"
