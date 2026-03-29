"""Data access helpers for ToolTune playground assets."""

from __future__ import annotations

from tooltune.io import dump_json, load_json
from tooltune.paths import CONFIGS_DIR, DATA_DIR, PLAYGROUND_DATA_DIR, TASKS_DIR


class PlaygroundData:
    def __init__(self) -> None:
        self.variants = load_json(CONFIGS_DIR / "variants.json")["variants"]
        self.showcase = load_json(DATA_DIR / "showcase_examples.json")

    def load_tasks(self) -> list[dict]:
        tasks = []
        for path in sorted(TASKS_DIR.glob("tier*.json")):
            tasks.extend(load_json(path))
        return tasks

    def load_model_card(self) -> dict:
        card_path = PLAYGROUND_DATA_DIR / "model_card.json"
        if card_path.exists():
            return load_json(card_path)
        return {
            "base_model": "Qwen2.5-Coder-7B-Instruct",
            "training_method": "GRPO with composite reward",
            "tool_set": ["calculator", "wikipedia", "weather", "code_executor", "unit_converter"],
            "task_suite": "ToolTune task tiers",
            "variants": self.variants,
        }

    def load_reward_lab(self, experiment: str) -> dict:
        reward_path = PLAYGROUND_DATA_DIR / f"reward_lab_{experiment}.json"
        if reward_path.exists():
            return load_json(reward_path)
        return {
            "experiment": experiment,
            "title": experiment.replace("-", " ").title(),
            "items": [],
        }

    def persist_json(self, filename: str, payload: dict | list) -> None:
        dump_json(PLAYGROUND_DATA_DIR / filename, payload)
