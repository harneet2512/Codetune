"""Report generation for eval results — tables, failure analysis, JSON export."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from tooltune.eval.schema import ComparisonResults, EvalResult, EvalSuiteResults


# ---------------------------------------------------------------------------
# Text summary table
# ---------------------------------------------------------------------------


def summary_table(results: EvalSuiteResults) -> str:
    """Render a text table summarizing suite results, similar to quick_eval output."""
    agg = results.aggregate
    lines = [
        f"=== Eval Suite: {results.suite_name} ===",
        f"Variant: {results.variant or '(default)'}",
        f"Cases: {agg.total}  |  Pass rate: {agg.pass_rate:.1%}",
        "",
        f"  {'Metric':<20} {'Score':>8}",
        f"  {'-' * 20} {'-' * 8}",
        f"  {'Composite':<20} {agg.mean_composite:>8.3f}",
        f"  {'Tool Accuracy':<20} {agg.mean_tool_accuracy:>8.3f}",
        f"  {'Restraint':<20} {agg.mean_restraint:>8.3f}",
        f"  {'Answer':<20} {agg.mean_answer:>8.3f}",
        f"  {'Efficiency':<20} {agg.mean_efficiency:>8.3f}",
        f"  {'Ordering':<20} {agg.mean_ordering:>8.3f}",
    ]
    return "\n".join(lines)


def comparison_table(comparison: ComparisonResults) -> str:
    """Render a side-by-side comparison table across variants."""
    variants = list(comparison.variants.keys())
    if not variants:
        return "(no variants to compare)"

    # Header.
    header = f"  {'Metric':<20}"
    for v in variants:
        header += f" {v:>12}"
    sep = f"  {'-' * 20}" + "".join(f" {'-' * 12}" for _ in variants)

    rows = []
    for field_name, label in [
        ("mean_composite", "Composite"),
        ("mean_tool_accuracy", "Tool Accuracy"),
        ("mean_restraint", "Restraint"),
        ("mean_answer", "Answer"),
        ("mean_efficiency", "Efficiency"),
        ("mean_ordering", "Ordering"),
        ("pass_rate", "Pass Rate"),
    ]:
        row = f"  {label:<20}"
        for v in variants:
            agg = comparison.variants[v].aggregate
            val = getattr(agg, field_name)
            if field_name == "pass_rate":
                row += f" {val:>11.1%}"
            else:
                row += f" {val:>12.3f}"
        rows.append(row)

    lines = [
        f"=== Comparison: {comparison.suite_name} ===",
        "",
        header,
        sep,
        *rows,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Failure analysis
# ---------------------------------------------------------------------------


def failure_analysis(results: EvalSuiteResults) -> str:
    """List all failed cases with their failure reasons."""
    failed = [r for r in results.results if not r.passed]
    if not failed:
        return "All cases passed."

    lines = [f"Failed cases: {len(failed)} / {results.aggregate.total}", ""]
    for r in failed:
        lines.append(f"  [{r.case_id}] (category={r.category}, difficulty={r.difficulty})")
        lines.append(f"    composite={r.scores.composite:.3f}")
        for reason in r.failure_reasons:
            lines.append(f"    - {reason}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Category breakdown
# ---------------------------------------------------------------------------


def category_breakdown(results: EvalSuiteResults) -> str:
    """Scores grouped by task category."""
    by_cat: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results.results:
        by_cat[r.category].append(r)

    lines = [
        f"=== Category Breakdown: {results.suite_name} ===",
        "",
        f"  {'Category':<25} {'Count':>6} {'Composite':>10} {'Pass Rate':>10}",
        f"  {'-' * 25} {'-' * 6} {'-' * 10} {'-' * 10}",
    ]

    for cat in sorted(by_cat.keys()):
        group = by_cat[cat]
        n = len(group)
        avg = sum(r.scores.composite for r in group) / n
        pr = sum(1 for r in group if r.passed) / n
        lines.append(f"  {cat:<25} {n:>6} {avg:>10.3f} {pr:>9.1%}")

    return "\n".join(lines)


def difficulty_breakdown(results: EvalSuiteResults) -> str:
    """Scores grouped by difficulty level."""
    by_diff: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results.results:
        by_diff[r.difficulty].append(r)

    order = {"easy": 0, "medium": 1, "hard": 2}
    lines = [
        f"=== Difficulty Breakdown: {results.suite_name} ===",
        "",
        f"  {'Difficulty':<15} {'Count':>6} {'Composite':>10} {'Pass Rate':>10}",
        f"  {'-' * 15} {'-' * 6} {'-' * 10} {'-' * 10}",
    ]

    for diff in sorted(by_diff.keys(), key=lambda d: order.get(d, 99)):
        group = by_diff[diff]
        n = len(group)
        avg = sum(r.scores.composite for r in group) / n
        pr = sum(1 for r in group if r.passed) / n
        lines.append(f"  {diff:<15} {n:>6} {avg:>10.3f} {pr:>9.1%}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------


def to_json(results: EvalSuiteResults) -> str:
    """Export full results as formatted JSON for dashboard consumption."""
    return results.model_dump_json(indent=2)


def to_dict(results: EvalSuiteResults) -> dict[str, Any]:
    """Export full results as a dictionary."""
    return results.model_dump()


def comparison_to_json(comparison: ComparisonResults) -> str:
    """Export comparison results as JSON."""
    return comparison.model_dump_json(indent=2)


def save_json(results: EvalSuiteResults | ComparisonResults, path: str) -> None:
    """Write results to a JSON file."""
    data = results.model_dump_json(indent=2)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
