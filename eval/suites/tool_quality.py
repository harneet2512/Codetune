"""Tool-use quality evaluation."""

from __future__ import annotations

from train.reward import VALID_TOOLS


def run(traces: list[dict]) -> dict:
    total_calls = 0
    correct_calls = 0
    valid_args = 0
    hallucinations = 0
    overtool = 0
    restraint_cases = 0

    for trace in traces:
        expected = trace["task"].get("expected_tools", [])
        calls = trace.get("tool_calls", [])
        total_calls += len(calls)
        if expected == []:
            restraint_cases += 1
            if calls:
                overtool += 1
        for index, call in enumerate(calls):
            if call.get("name") in VALID_TOOLS:
                correct_calls += 1
            else:
                hallucinations += 1
            if call.get("arguments"):
                valid_args += 1

    return {
        "metrics": {
            "tool_selection_accuracy": round(correct_calls / total_calls, 4) if total_calls else 0.0,
            "argument_validity": round(valid_args / total_calls, 4) if total_calls else 0.0,
            "tool_hallucination_rate": round(hallucinations / total_calls, 4) if total_calls else 0.0,
            "overtooling_rate": round(overtool / restraint_cases, 4) if restraint_cases else 0.0,
        },
        "per_problem": traces,
    }
