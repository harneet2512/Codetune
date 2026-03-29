"""Agentic behavior metrics for ToolTune traces."""

from __future__ import annotations

from train.agentic_loop import extract_think_blocks


def run(traces: list[dict]) -> dict:
    planning = 0
    adherence = 0
    recovery = 0
    total_loops = 0
    termination_failures = 0

    for trace in traces:
        transcript = trace.get("transcript", "")
        think_blocks = extract_think_blocks(transcript)
        if any("plan" in block.lower() or "1." in block for block in think_blocks):
            planning += 1
            if len(trace.get("tool_calls", [])) >= max(1, len(trace["task"].get("expected_tools", [])) - 1):
                adherence += 1
        if any("error" in observation.lower() for observation in trace.get("observations", [])):
            if trace.get("verification", {}).get("correct"):
                recovery += 1
        total_loops += len(trace.get("tool_calls", []))
        if not trace.get("final_answer"):
            termination_failures += 1

    total = len(traces) or 1
    return {
        "metrics": {
            "planning_rate": round(planning / total, 4),
            "plan_adherence": round(adherence / planning, 4) if planning else 0.0,
            "error_recovery_rate": round(recovery / total, 4),
            "avg_loop_length": round(total_loops / total, 4),
            "premature_termination_rate": round(termination_failures / total, 4),
        },
        "per_problem": traces,
    }
