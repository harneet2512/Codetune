"""Demo mode endpoints — serve pre-computed traces."""

import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException

from config import DEMO_TRACES_DIR

router = APIRouter(tags=["demo"])

# Cache loaded traces
_trace_cache: dict = {}


def _load_showcase() -> dict:
    """Load showcase.json from the demo traces directory."""
    if "showcase" in _trace_cache:
        return _trace_cache["showcase"]

    path = Path(DEMO_TRACES_DIR) / "showcase.json"
    if not path.exists():
        return {"version": "3.0", "models": [], "tasks": []}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _trace_cache["showcase"] = data
    return data


@router.get("/run/demo/tasks")
async def list_demo_tasks():
    """List available demo tasks."""
    data = _load_showcase()
    tasks = []
    for t in data.get("tasks", []):
        tasks.append({
            "id": t["id"],
            "title": t["title"],
            "category": t.get("category", ""),
            "difficulty": t.get("difficulty", "Medium"),
            "prompt": t.get("prompt", ""),
        })
    return {"tasks": tasks, "models": data.get("models", [])}


@router.get("/run/demo/trace/{task_id}/{model}")
async def get_demo_trace(task_id: str, model: str):
    """Get a pre-computed trace for a specific task and model."""
    data = _load_showcase()
    for t in data.get("tasks", []):
        if t["id"] == task_id:
            trace = t.get("traces", {}).get(model)
            if trace:
                return {
                    "task_id": task_id,
                    "model": model,
                    "trace": trace,
                    "source": "demo",
                }
            raise HTTPException(404, f"No trace for model '{model}' on task '{task_id}'")
    raise HTTPException(404, f"Task '{task_id}' not found")


@router.get("/run/demo/stats")
async def get_demo_stats():
    """Get aggregate stats across demo traces."""
    data = _load_showcase()
    return data.get("stats", {})
