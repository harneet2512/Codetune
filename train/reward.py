"""Reward helpers and trace analysis for ToolTune GRPO."""

from __future__ import annotations

import re

from train.agentic_loop import extract_answer, extract_observations, extract_think_blocks, extract_tool_calls

VALID_TOOLS = {"calculator", "wikipedia", "weather", "code_executor", "unit_converter"}


def normalize_answer(text: str) -> str:
    return " ".join(text.strip().lower().split())


def is_correct(predicted: str, expected: str) -> bool:
    predicted_norm = normalize_answer(predicted)
    expected_norm = normalize_answer(expected)
    if predicted_norm == expected_norm:
        return True

    # Numeric tolerance for simple decimal comparisons.
    try:
        return abs(float(re.sub(r"[^0-9.\-]", "", predicted_norm)) - float(re.sub(r"[^0-9.\-]", "", expected_norm))) < 0.05
    except ValueError:
        return expected_norm in predicted_norm or predicted_norm in expected_norm


def validate_args(tool_call) -> bool:
    if tool_call.name not in VALID_TOOLS:
        return False
    return bool(tool_call.arguments)


def has_numbered_steps(think_block: str) -> bool:
    return bool(re.search(r"\b1\.", think_block) or re.search(r"\bplan\b", think_block.lower()))


def reward_trace(trace: str, ground_truth_answer: str, expected_tools: list[str] | None = None) -> float:
    final_answer = extract_answer(trace)
    task_reward = 1.0 if is_correct(final_answer, ground_truth_answer) else 0.0

    tool_calls = extract_tool_calls(trace)
    tool_reward = 0.0
    if expected_tools is not None:
        called_correct = all(tc.name in VALID_TOOLS for tc in tool_calls)
        args_valid = all(validate_args(tc) for tc in tool_calls) if tool_calls else expected_tools == []
        no_hallucination = not any(tc.name not in VALID_TOOLS for tc in tool_calls)
        tool_reward = (0.1 if called_correct else 0.0) + (0.1 if args_valid else 0.0) + (0.1 if no_hallucination else 0.0)

    restraint_reward = 0.1 if expected_tools == [] and len(tool_calls) == 0 else 0.0

    think_blocks = extract_think_blocks(trace)
    plan_reward = 0.1 if any(has_numbered_steps(block) for block in think_blocks) else 0.0

    observations = extract_observations(trace)
    had_error = any("error" in observation.lower() for observation in observations)
    recovery_reward = 0.1 if had_error and task_reward == 1.0 else 0.0

    excess_calls = max(0, len(tool_calls) - 5)
    loop_penalty = -0.1 * excess_calls

    return task_reward + tool_reward + restraint_reward + plan_reward + recovery_reward + loop_penalty


def reward_fn(completions, prompts=None, ground_truth=None, expected_tools=None, **kwargs):
    import json as _json

    rewards: list[float] = []
    for index, completion in enumerate(completions):
        answer = ground_truth[index] if ground_truth else ""
        tools_raw = expected_tools[index] if expected_tools else None
        # HF Datasets serializes lists as JSON strings; deserialize if needed.
        if isinstance(tools_raw, str):
            try:
                tools_raw = _json.loads(tools_raw)
            except (ValueError, TypeError):
                tools_raw = None
        rewards.append(reward_trace(completion, answer, tools_raw))
    return rewards
