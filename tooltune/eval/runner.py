"""EvalRunner — execute an eval suite against model traces and produce results."""

from __future__ import annotations

from tooltune.eval.schema import (
    AggregateScores,
    ComparisonResults,
    EvalResult,
    EvalSuiteResults,
    ScoreWeights,
    TraceRecord,
)
from tooltune.eval.scorer import PASS_THRESHOLD, composite_score
from tooltune.eval.suite import EvalSuite


class EvalRunner:
    """Run eval suites against model traces and produce structured results.

    Parameters
    ----------
    weights:
        Optional global weight overrides. Per-case weights in the suite
        take precedence over this.
    pass_threshold:
        Composite score threshold for a case to be considered passing.
    """

    def __init__(
        self,
        weights: ScoreWeights | None = None,
        pass_threshold: float = PASS_THRESHOLD,
    ) -> None:
        self.weights = weights
        self.pass_threshold = pass_threshold

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------

    def run(
        self,
        suite: EvalSuite,
        traces: list[TraceRecord],
        variant: str = "",
    ) -> EvalSuiteResults:
        """Run every eval case against its matching trace.

        Traces are matched to cases by ``id``. Cases with no matching trace
        are scored as zero (failure).
        """
        trace_map: dict[str, TraceRecord] = {t.id: t for t in traces}
        results: list[EvalResult] = []

        for case in suite:
            trace = trace_map.get(case.id)
            if trace is None:
                results.append(
                    EvalResult(
                        case_id=case.id,
                        category=case.category,
                        difficulty=case.difficulty,
                        tags=case.tags,
                        passed=False,
                        failure_reasons=["no matching trace found"],
                    )
                )
                continue

            breakdown, failures = composite_score(trace, case, self.weights)
            passed = breakdown.composite >= self.pass_threshold

            results.append(
                EvalResult(
                    case_id=case.id,
                    category=case.category,
                    difficulty=case.difficulty,
                    tags=case.tags,
                    passed=passed,
                    scores=breakdown,
                    failure_reasons=failures,
                )
            )

        aggregate = _compute_aggregate(results)
        return EvalSuiteResults(
            suite_name=suite.name,
            variant=variant,
            results=results,
            aggregate=aggregate,
        )

    # ------------------------------------------------------------------
    # Comparison across variants
    # ------------------------------------------------------------------

    def compare(
        self,
        suite: EvalSuite,
        variants: dict[str, list[TraceRecord]],
    ) -> ComparisonResults:
        """Evaluate the same suite against multiple model variants.

        Parameters
        ----------
        variants:
            Mapping of variant name to its list of traces.

        Returns a ComparisonResults with per-variant EvalSuiteResults.
        """
        variant_results: dict[str, EvalSuiteResults] = {}
        for name, traces in variants.items():
            variant_results[name] = self.run(suite, traces, variant=name)
        return ComparisonResults(suite_name=suite.name, variants=variant_results)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _compute_aggregate(results: list[EvalResult]) -> AggregateScores:
    if not results:
        return AggregateScores()

    n = len(results)
    return AggregateScores(
        mean_composite=round(sum(r.scores.composite for r in results) / n, 4),
        mean_tool_accuracy=round(sum(r.scores.tool_accuracy for r in results) / n, 4),
        mean_restraint=round(sum(r.scores.restraint for r in results) / n, 4),
        mean_answer=round(sum(r.scores.answer for r in results) / n, 4),
        mean_efficiency=round(sum(r.scores.efficiency for r in results) / n, 4),
        mean_ordering=round(sum(r.scores.ordering for r in results) / n, 4),
        pass_rate=round(sum(1 for r in results if r.passed) / n, 4),
        total=n,
    )
