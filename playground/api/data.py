"""Data access helpers for ToolTune playground v2."""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from tooltune.io import load_json
from tooltune.paths import PLAYGROUND_DATA_DIR


class PlaygroundData:
    def __init__(self) -> None:
        payload = self.load_showcase()
        self.version = payload.get("version", "2.0")
        self.models = payload.get("models", [])
        self.tasks = payload.get("tasks", [])
        self._task_index = {task["id"]: task for task in self.tasks}
        self._model_index = {model["key"]: model for model in self.models}

    def load_showcase(self) -> dict:
        return load_json(PLAYGROUND_DATA_DIR / "v2_traces.json")

    def list_tasks(self) -> list[dict]:
        items: list[dict] = []
        for task in self.tasks:
            items.append(
                {
                    "id": task["id"],
                    "title": task["title"],
                    "category": task["category"],
                    "difficulty": task["difficulty"],
                    "icon": task.get("icon", "circle"),
                    "prompt": task["prompt"],
                    "available_models": list(task.get("traces", {}).keys()),
                }
            )
        return items

    def get_task(self, task_id: str) -> dict:
        task = self._task_index.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")
        return task

    def get_trace(self, task_id: str, model_key: str) -> dict:
        task = self.get_task(task_id)
        trace = task.get("traces", {}).get(model_key)
        if not trace:
            raise HTTPException(status_code=404, detail=f"Unknown model '{model_key}' for task '{task_id}'")
        return {
            "version": self.version,
            "task": {
                "id": task["id"],
                "title": task["title"],
                "category": task["category"],
                "difficulty": task["difficulty"],
                "icon": task.get("icon", "circle"),
                "prompt": task["prompt"],
            },
            "model": self._model_index.get(model_key, {"key": model_key, "label": model_key.upper()}),
            "trace": trace,
        }

    def showcase_payload(self) -> dict:
        return {
            "version": self.version,
            "models": self.models,
            "tasks": [
                {
                    **task,
                    "trace_summaries": {
                        key: {
                            "verdict": value["verdict"],
                            "tool_calls_used": value["tool_calls_used"],
                            "steps": value["steps"],
                            "summary": value["summary"],
                        }
                        for key, value in task.get("traces", {}).items()
                    },
                }
                for task in self.tasks
            ],
        }

    def load_model_card(self) -> dict:
        return {
            "base_model": "Base -> SFT -> GRPO",
            "training_method": "Demo-mode hardcoded traces for reasoning debugger",
            "tool_set": [
                "log_search",
                "read_spec",
                "read_code",
                "run_tests",
                "codebase_search",
                "feature_flags",
                "calculator",
                "search_docs",
            ],
            "task_suite": "V2 engineering workflow showcase",
            "variants": self.models,
        }

    def load_reward_lab(self, experiment: str) -> dict:
        return {
            "experiment": experiment,
            "title": experiment.replace("-", " ").title(),
            "items": [],
        }


@lru_cache(maxsize=1)
def get_data() -> PlaygroundData:
    return PlaygroundData()
