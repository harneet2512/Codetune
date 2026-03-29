"""Agentic serving helpers for the ToolTune playground."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from tooltune.contracts import TaskRecord
from tooltune.io import load_json
from tooltune.paths import CONFIGS_DIR, TASKS_DIR
from tooltune.simulators import HeuristicGenerator
from train.agentic_loop import AgenticTrace, generate_agentic_completion, trace_to_sse_events
from train.reward import is_correct
from tools.registry import ToolRegistry

VALID_TOOL_NAMES = {"calculator", "wikipedia", "weather", "code_executor", "unit_converter"}


class LiveCompletionClient:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint.rstrip("/")

    def generate(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.0) -> str:
        payload = {
            "model": "tooltune",
            "prompt": prompt,
            "max_tokens": max_new_tokens,
            "temperature": temperature,
            "stream": False,
        }
        request = urllib.request.Request(
            f"{self.endpoint}/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("choices", [{}])[0].get("text", "")


class AgentRunner:
    def __init__(self) -> None:
        self.registry = ToolRegistry()
        self.variant_config = {item["key"]: item for item in load_json(CONFIGS_DIR / "variants.json")["variants"]}
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> dict[str, dict]:
        tasks = {}
        for path in TASKS_DIR.glob("tier*.json"):
            for task in load_json(path):
                tasks[task["id"]] = task
        return tasks

    def build_task(self, prompt: str, inject_errors: bool = False) -> TaskRecord:
        for task in self.tasks.values():
            if task["prompt"] == prompt:
                record = TaskRecord(**task)
                if inject_errors and not record.error_injection_policy:
                    record.error_injection_policy = {"enabled": True, "probability": 0.2, "seed": 1}
                return record
        return TaskRecord(
            id="adhoc-task",
            tier="adhoc",
            prompt=prompt,
            ground_truth="",
            expected_tools=[],
            metadata={"source": "adhoc"},
            error_injection_policy={"enabled": inject_errors, "probability": 0.2, "seed": 1},
        )

    def _generator_for(self, model_key: str, demo_override: bool = False):
        config = self.variant_config.get(model_key, self.variant_config["grpo-balanced"])
        if demo_override:
            return HeuristicGenerator(model_key), "demo"
        endpoint = config.get("endpoint")
        if endpoint:
            return LiveCompletionClient(endpoint), "live"
        return HeuristicGenerator(model_key), "demo"

    def run(self, prompt: str, model_key: str, inject_errors: bool = False, demo_override: bool = False) -> tuple[AgenticTrace, str]:
        task = self.build_task(prompt, inject_errors=inject_errors)
        generator, mode = self._generator_for(model_key, demo_override=demo_override)
        try:
            trace = generate_agentic_completion(
                generator=generator,
                task=task,
                registry=self.registry,
                max_steps=5,
                inject_errors=inject_errors,
                error_probability=task.error_injection_policy.get("probability", 0.2),
            )
        except Exception:
            trace = generate_agentic_completion(
                generator=HeuristicGenerator(model_key),
                task=task,
                registry=self.registry,
                max_steps=5,
                inject_errors=inject_errors,
                error_probability=task.error_injection_policy.get("probability", 0.2),
            )
            mode = "demo"
        return trace, mode

    def verify(self, trace: AgenticTrace) -> dict[str, Any]:
        expected = trace.task.expected_tools
        actual = [call.name for call in trace.tool_calls]
        return {
            "correct": is_correct(trace.final_answer, trace.task.ground_truth) if trace.task.ground_truth else bool(trace.final_answer),
            "expected_tools": expected,
            "actual_tools": actual,
            "tool_hallucination": any(name not in VALID_TOOL_NAMES for name in actual),
            "overtooling": expected == [] and bool(actual),
            "arg_validity": all(bool(call.arguments) for call in trace.tool_calls),
            "loop_count": len(trace.tool_calls),
        }

    def sse_payload(self, trace: AgenticTrace, mode: str) -> list[dict[str, Any]]:
        payload = [event.to_dict() for event in trace_to_sse_events(trace)]
        payload.append({"type": "verification", "data": self.verify(trace)})
        payload.append({"type": "run_completed", "data": {"mode": mode}})
        return payload
