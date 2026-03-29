"""Reasoning quality metrics for ToolTune traces."""

from __future__ import annotations

from train.agentic_loop import extract_think_blocks


def run(traces: list[dict]) -> dict:
    reasoning = 0
    tokens = []
    edge_mentions = 0
    success_with_reasoning = 0
    success_without_reasoning = 0
    with_reasoning = 0
    without_reasoning = 0

    for trace in traces:
        think_blocks = extract_think_blocks(trace.get("transcript", ""))
        if think_blocks:
            reasoning += 1
            with_reasoning += 1
            joined = " ".join(think_blocks)
            tokens.append(len(joined.split()))
            if any(word in joined.lower() for word in ["error", "edge", "retry", "if"]):
                edge_mentions += 1
            if trace.get("verification", {}).get("correct"):
                success_with_reasoning += 1
        else:
            without_reasoning += 1
            if trace.get("verification", {}).get("correct"):
                success_without_reasoning += 1

    total = len(traces) or 1
    avg_length = round(sum(tokens) / len(tokens), 2) if tokens else 0.0
    corr = (success_with_reasoning / with_reasoning) - (success_without_reasoning / without_reasoning) if with_reasoning and without_reasoning else 0.0
    return {
        "metrics": {
            "reasoning_rate": round(reasoning / total, 4),
            "avg_reasoning_length": avg_length,
            "edge_case_mention_rate": round(edge_mentions / total, 4),
            "reasoning_correctness_delta": round(corr, 4),
        },
        "per_problem": traces,
    }
