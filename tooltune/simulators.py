"""Deterministic variant simulators for demo mode and local verification."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from train.agentic_loop import TextGenerator

OBS_BLOCK_RE = re.compile(r"<observation>.*?</observation>", re.DOTALL)


def _extract_task(prompt: str) -> str:
    marker = "User:"
    if marker in prompt:
        return prompt.split(marker, maxsplit=1)[1].strip()
    return prompt.strip()


@dataclass(slots=True)
class HeuristicGenerator(TextGenerator):
    variant: str

    def generate(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.0) -> str:
        task = _extract_task(prompt)
        if not OBS_BLOCK_RE.search(prompt):
            return self._first_step(task)
        return self._followup(task, prompt)

    def _first_step(self, task: str) -> str:
        task_lower = task.lower()
        if self.variant == "base":
            return self._base_first_step(task)
        if self.variant == "sft":
            return self._sft_first_step(task)
        if self.variant == "grpo-toolheavy":
            if "2 + 2" in task_lower:
                return (
                    "<think>\nI'll use a tool to be safe.\n</think>\n"
                    '<tool_call>\n{"name": "calculator", "arguments": {"expression": "2 + 2"}}\n</tool_call>\n'
                )
            return self._balanced_first_step(task)
        return self._balanced_first_step(task)

    def _followup(self, task: str, prompt: str) -> str:
        observations = re.findall(r"<observation>(.*?)</observation>", prompt, re.DOTALL)
        last_observation = observations[-1].strip() if observations else ""
        if self.variant == "base":
            return self._base_answer(task)
        if self.variant == "sft":
            return f"<think>\nI have enough structure.\n</think>\n<answer>\n{self._degraded_answer(task)}\n</answer>\n"
        if self.variant == "grpo-exec":
            return self._exec_followup(task, last_observation)
        if self.variant == "grpo-toolheavy":
            return self._toolheavy_followup(task, last_observation)
        return self._balanced_followup(task, last_observation)

    def _base_first_step(self, task: str) -> str:
        if "driving distance" in task.lower():
            return "<think>\nI'll estimate the distance and compute mentally.\n</think>\n<answer>\nAbout $50 in gas.\n</answer>\n"
        if "2 + 2" in task:
            return "<think>\nThis is trivial.\n</think>\n<answer>\n4\n</answer>\n"
        return "<think>\nI can probably answer from memory.\n</think>\n<answer>\nI'm not fully sure, but here is my best guess.\n</answer>\n"

    def _base_answer(self, task: str) -> str:
        return f"<answer>\n{self._degraded_answer(task)}\n</answer>\n"

    def _sft_first_step(self, task: str) -> str:
        if "population of france divided by the population of belgium" in task.lower():
            return (
                "<think>\nPlan:\n1. Call wikipedia.\n2. Answer quickly.\n</think>\n"
                '<tool_call>\n{"name": "wikipedia", "arguments": {"query": "population of France"}}\n</tool_call>\n'
            )
        return self._balanced_first_step(task)

    def _balanced_first_step(self, task: str) -> str:
        task_lower = task.lower()
        if "population of france divided by the population of belgium" in task_lower:
            return (
                "<think>\nPlan:\n1. Look up the population of France.\n2. Look up the population of Belgium.\n3. Divide the two values.\n</think>\n"
                '<tool_call>\n{"name": "wikipedia", "arguments": {"query": "population of France"}}\n</tool_call>\n'
            )
        if "convert the current temperature in tokyo from celsius to fahrenheit" in task_lower:
            return (
                "<think>\nPlan:\n1. Get Tokyo weather.\n2. Convert Celsius to Fahrenheit.\n</think>\n"
                '<tool_call>\n{"name": "weather", "arguments": {"city": "Tokyo"}}\n</tool_call>\n'
            )
        if "driving distance from pittsburgh to nyc" in task_lower:
            return (
                "<think>\nPlan:\n1. Look up the driving distance.\n2. Divide by 28 mpg.\n3. Multiply by 3.50.\n</think>\n"
                '<tool_call>\n{"name": "wikipedia", "arguments": {"query": "driving distance Pittsburgh to New York City"}}\n</tool_call>\n'
            )
        if "2 + 2" in task_lower:
            return "<think>\nThis is common knowledge.\n</think>\n<answer>\n4\n</answer>\n"
        if "romeo and juliet" in task_lower:
            return "<think>\nThis is common knowledge.\n</think>\n<answer>\nWilliam Shakespeare\n</answer>\n"
        if "water h2o or h2so4" in task_lower:
            return "<think>\nThis is basic science.\n</think>\n<answer>\nH2O\n</answer>\n"
        if "len() function" in task_lower:
            return "<think>\nThis is a Python built-in.\n</think>\n<answer>\nIt returns the number of items in an object.\n</answer>\n"
        if "what continent is japan on" in task_lower:
            return "<think>\nThis is common geography knowledge.\n</think>\n<answer>\nAsia\n</answer>\n"
        return "<think>\nI should answer carefully.\n</think>\n<answer>\nI need a more specific demo trace for this task.\n</answer>\n"

    def _balanced_followup(self, task: str, observation: str) -> str:
        task_lower = task.lower()
        if "population of france divided by the population of belgium" in task_lower:
            if "france" in observation.lower():
                return (
                    "<think>\nI have France. Next I need Belgium.\n</think>\n"
                    '<tool_call>\n{"name": "wikipedia", "arguments": {"query": "population of Belgium"}}\n</tool_call>\n'
                )
            if "belgium" in observation.lower():
                return (
                    "<think>\nNow I can divide 68.4 by 11.7.\n</think>\n"
                    '<tool_call>\n{"name": "calculator", "arguments": {"expression": "68.4 / 11.7"}}\n</tool_call>\n'
                )
            return "<think>\nThe ratio is ready.\n</think>\n<answer>\n5.85\n</answer>\n"
        if "convert the current temperature in tokyo from celsius to fahrenheit" in task_lower:
            if "temp_celsius" in observation:
                payload = json.dumps({"name": "unit_converter", "arguments": {"value": 18, "from_unit": "celsius", "to_unit": "fahrenheit"}})
                return f"<think>\nTokyo is 18C. I should convert it.\n</think>\n<tool_call>\n{payload}\n</tool_call>\n"
            return "<think>\nI have the converted temperature.\n</think>\n<answer>\n64.4\n</answer>\n"
        if "driving distance from pittsburgh to nyc" in task_lower:
            if "370" in observation:
                return (
                    "<think>\nI have the distance. Now calculate 370 / 28 * 3.50.\n</think>\n"
                    '<tool_call>\n{"name": "calculator", "arguments": {"expression": "370 / 28 * 3.50"}}\n</tool_call>\n'
                )
            return "<think>\nI have the cost.\n</think>\n<answer>\nIt would cost approximately $46.25 in gas.\n</answer>\n"
        return "<answer>\nI do not have a demo followup for this task.\n</answer>\n"

    def _exec_followup(self, task: str, observation: str) -> str:
        if "2 + 2" in task:
            return "<answer>\n4\n</answer>\n"
        return self._balanced_followup(task, observation)

    def _toolheavy_followup(self, task: str, observation: str) -> str:
        if "2 + 2" in task:
            return "<think>\nThe calculator confirmed it.\n</think>\n<answer>\n4\n</answer>\n"
        return self._balanced_followup(task, observation)

    def _degraded_answer(self, task: str) -> str:
        if "driving distance from pittsburgh to nyc" in task.lower():
            return "About $50 in gas."
        if "population of france divided by the population of belgium" in task.lower():
            return "About 6.2"
        return "I think the answer is around the right range."
