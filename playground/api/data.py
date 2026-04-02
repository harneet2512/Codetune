"""Data access for ToolTune playground v3."""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from tooltune.io import load_json
from tooltune.paths import PLAYGROUND_DATA_DIR


class PlaygroundData:
    def __init__(self) -> None:
        path = PLAYGROUND_DATA_DIR / "showcase.json"
        if not path.exists():
            path = PLAYGROUND_DATA_DIR / "v2_traces.json"
        payload = load_json(path)
        self.version = payload.get("version", "3.0")
        self.models = payload.get("models", [])
        self.stats = payload.get("stats", {})
        self.tasks = payload.get("tasks", [])
        self._task_index = {task["id"]: task for task in self.tasks}
        self._model_index = {model["key"]: model for model in self.models}

    def list_tasks(self) -> list[dict]:
        items: list[dict] = []
        for task in self.tasks:
            items.append({
                "id": task["id"],
                "title": task["title"],
                "category": task["category"],
                "difficulty": task["difficulty"],
                "tier": task.get("tier", ""),
                "icon": task.get("icon", "circle"),
                "prompt": task["prompt"],
                "ground_truth": task.get("ground_truth", ""),
                "expected_tools": task.get("expected_tools", []),
                "available_models": list(task.get("traces", {}).keys()),
            })
        return items

    def get_trace(self, task_id: str, model_key: str) -> dict:
        task = self._task_index.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")
        trace = task.get("traces", {}).get(model_key)
        if not trace:
            raise HTTPException(status_code=404, detail=f"No trace for {model_key}/{task_id}")
        return {
            "task": {
                "id": task["id"],
                "title": task["title"],
                "category": task["category"],
                "difficulty": task["difficulty"],
                "prompt": task["prompt"],
                "ground_truth": task.get("ground_truth", ""),
                "expected_tools": task.get("expected_tools", []),
            },
            "model": self._model_index.get(model_key, {"key": model_key, "label": model_key.upper()}),
            "trace": trace,
        }

    def get_stats(self) -> dict:
        return self.stats

    def get_eval_data(self) -> dict:
        """Return full task objects with traces for the eval dashboard."""
        return {
            "version": self.version,
            "stats": self.stats,
            "tasks": self.tasks,
        }


@lru_cache(maxsize=1)
def get_data() -> PlaygroundData:
    return PlaygroundData()
