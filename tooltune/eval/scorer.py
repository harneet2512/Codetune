"""Scoring functions for tool-use evaluation.

Each scorer takes trace data and expected values, returning a float in [0, 1].
The composite scorer combines them with configurable weights.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from tooltune.eval.schema import (
    EvalCase,
    ExpectedToolCall,
    ScoreBreakdown,
    ScoreWeights,
    TraceRecord,
    TraceToolCall,
)

# Default weights used when the eval case does not specify overrides.
DEFAULT_WEIGHTS = ScoreWeights()

# Composite score threshold for pass/fail.
PASS_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Individual scorers
# ---------------------------------------------------------------------------


def score_tool_accuracy(
    tool_calls: list[TraceToolCall],
    expected: list[ExpectedToolCall],
) -> tuple[float, list[str]]:
    """Score whether the model called the right tools with the right args.

    Returns (score, failure_reasons).
    """
    if not expected:
        # No tools expected — full marks if none were called, partial otherwise.
        return (1.0, []) if not tool_calls else (0.5, ["called tools when none expected"])

    failures: list[str] = []
    matched = 0

    for exp in expected:
        match = _find_best_match(exp, tool_calls)
        if match is None:
            failures.append(f"missing expected tool call: {exp.name}")
            continue

        # Check arg constraints.
        args_ok = _check_args_contains(match.arguments, exp.args_contains)
        if args_ok:
            matched += 1
        else:
            failures.append(
                f"tool {exp.name} called but args mismatch — "
                f"expected {exp.args_contains} in {match.arguments}"
            )
            matched += 0.5  # Partial credit for right tool, wrong args.

    score = matched / len(expected) if expected else 1.0
    return min(score, 1.0), failures


def score_restraint(
    tool_calls: list[TraceToolCall],
    expected_tools: list[ExpectedToolCall],
    forbidden_tools: list[str] | None = None,
) -> tuple[float, list[str]]:
    """Score whether the model avoided unnecessary or forbidden tool calls.

    Returns (score, failure_reasons).
    """
    failures: list[str] = []
    penalties = 0.0
    forbidden = set(forbidden_tools or [])

    # Penalize forbidden tool usage.
    for tc in tool_calls:
        if tc.name in forbidden:
            penalties += 0.5
            failures.append(f"called forbidden tool: {tc.name}")

    # Penalize excess calls beyond what was expected.
    expected_names = [e.name for e in expected_tools]
    called_names = [tc.name for tc in tool_calls]
    unexpected = [n for n in called_names if n not in expected_names]
    if unexpected:
        penalties += 0.2 * len(unexpected)
        failures.append(f"unexpected tools called: {unexpected}")

    score = max(0.0, 1.0 - penalties)
    return score, failures


def score_answer(predicted: str, ground_truth: str) -> tuple[float, list[str]]:
    """Fuzzy answer matching — exact, contains, numeric tolerance, similarity.

    Returns (score, failure_reasons).
    """
    if not ground_truth:
        return 1.0, []  # No expected answer — skip.

    pred_norm = _normalize(predicted)
    gt_norm = _normalize(ground_truth)

    # Exact match.
    if pred_norm == gt_norm:
        return 1.0, []

    # Regex match (ground truth can be a regex pattern).
    try:
        if re.fullmatch(gt_norm, pred_norm):
            return 1.0, []
    except re.error:
        pass

    # Contains match.
    if gt_norm in pred_norm or pred_norm in gt_norm:
        return 0.8, []

    # Numeric tolerance.
    try:
        pred_num = float(re.sub(r"[^0-9.\-]", "", pred_norm))
        gt_num = float(re.sub(r"[^0-9.\-]", "", gt_norm))
        if abs(pred_num - gt_num) < 0.05:
            return 1.0, []
    except (ValueError, TypeError):
        pass

    # Sequence similarity.
    ratio = SequenceMatcher(None, pred_norm, gt_norm).ratio()
    if ratio >= 0.8:
        return ratio, []

    return 0.0, [f"answer mismatch: predicted={predicted!r}, expected={ground_truth!r}"]


def score_efficiency(
    tool_calls: list[TraceToolCall],
    max_tool_calls: int,
) -> tuple[float, list[str]]:
    """Score tool call count vs the maximum allowed.

    Returns (score, failure_reasons).
    """
    n_calls = len(tool_calls)
    if n_calls == 0 and max_tool_calls == 0:
        return 1.0, []

    if n_calls <= max_tool_calls:
        # Linear reward: fewer calls = better.
        return 1.0 - 0.5 * (n_calls / max(max_tool_calls, 1)), []

    excess = n_calls - max_tool_calls
    return 0.0, [f"exceeded max tool calls: {n_calls} > {max_tool_calls} (excess: {excess})"]


def score_ordering(
    tool_calls: list[TraceToolCall],
    expected_tools: list[ExpectedToolCall],
) -> tuple[float, list[str]]:
    """Score whether tools were called in the expected sequence.

    Uses longest common subsequence ratio against the expected order.
    Returns (score, failure_reasons).
    """
    if len(expected_tools) <= 1:
        return 1.0, []  # Ordering is trivial.

    expected_names = [e.name for e in expected_tools]
    actual_names = [tc.name for tc in tool_calls]

    lcs_len = _lcs_length(expected_names, actual_names)
    score = lcs_len / len(expected_names)

    failures: list[str] = []
    if score < 1.0:
        failures.append(
            f"tool ordering mismatch: expected {expected_names}, got {actual_names}"
        )

    return score, failures


# ---------------------------------------------------------------------------
# Composite scorer
# ---------------------------------------------------------------------------


def composite_score(
    trace: TraceRecord,
    case: EvalCase,
    weights: ScoreWeights | None = None,
) -> tuple[ScoreBreakdown, list[str]]:
    """Compute all dimension scores and a weighted composite.

    Returns (ScoreBreakdown, all_failure_reasons).
    """
    w = weights or case.weights or DEFAULT_WEIGHTS
    all_failures: list[str] = []

    ta, ta_f = score_tool_accuracy(trace.tool_calls, case.expected_tools)
    all_failures.extend(ta_f)

    rs, rs_f = score_restraint(trace.tool_calls, case.expected_tools, case.forbidden_tools)
    all_failures.extend(rs_f)

    an, an_f = score_answer(trace.answer, case.expected_answer)
    all_failures.extend(an_f)

    ef, ef_f = score_efficiency(trace.tool_calls, case.max_tool_calls)
    all_failures.extend(ef_f)

    od, od_f = score_ordering(trace.tool_calls, case.expected_tools)
    all_failures.extend(od_f)

    comp = (
        w.tool_accuracy * ta
        + w.restraint * rs
        + w.answer * an
        + w.efficiency * ef
        + w.ordering * od
    )

    breakdown = ScoreBreakdown(
        tool_accuracy=round(ta, 4),
        restraint=round(rs, 4),
        answer=round(an, 4),
        efficiency=round(ef, 4),
        ordering=round(od, 4),
        composite=round(comp, 4),
    )
    return breakdown, all_failures


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _find_best_match(
    expected: ExpectedToolCall,
    tool_calls: list[TraceToolCall],
) -> TraceToolCall | None:
    """Find the first tool call matching the expected name."""
    for tc in tool_calls:
        if tc.name == expected.name:
            return tc
    return None


def _check_args_contains(actual: dict[str, Any], required: dict[str, Any]) -> bool:
    """Check that all required key-value pairs appear in actual args."""
    for key, value in required.items():
        if key not in actual:
            return False
        actual_val = actual[key]
        # String containment for string values.
        if isinstance(value, str) and isinstance(actual_val, str):
            if value.lower() not in actual_val.lower():
                return False
        elif actual_val != value:
            return False
    return True


def _lcs_length(a: list[str], b: list[str]) -> int:
    """Longest common subsequence length."""
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]
