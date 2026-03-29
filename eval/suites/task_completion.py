"""ToolTune task completion evaluation."""

from __future__ import annotations

from collections import defaultdict

from train.reward import is_correct


def run(traces: list[dict]) -> dict:
    by_tier: dict[str, list[bool]] = defaultdict(list)
    for trace in traces:
        passed = is_correct(trace.get("final_answer", ""), trace["task"]["ground_truth"])
        by_tier[trace["task"]["tier"]].append(passed)

    metrics = {}
    total_passed = 0
    total_count = 0
    for tier, values in by_tier.items():
        accuracy = sum(values) / len(values) if values else 0.0
        metrics[f"{tier}_accuracy"] = round(accuracy, 4)
        total_passed += sum(values)
        total_count += len(values)
    metrics["overall_accuracy"] = round(total_passed / total_count, 4) if total_count else 0.0
    return {"metrics": metrics, "per_problem": traces}
