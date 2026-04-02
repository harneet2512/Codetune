"""CLI entry point for ToolTune eval.

Usage:
    tooltune-eval run --suite evals/function_calling.yaml --traces results/traces/grpo.json
    tooltune-eval compare --suite evals/ --variants base=traces/base.json sft=traces/sft.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tooltune.eval.report import (
    category_breakdown,
    comparison_table,
    comparison_to_json,
    difficulty_breakdown,
    failure_analysis,
    save_json,
    summary_table,
)
from tooltune.eval.runner import EvalRunner
from tooltune.eval.schema import ScoreWeights
from tooltune.eval.suite import EvalSuite, load_traces


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tooltune-eval",
        description="ToolTune eval SDK — measure function-calling quality in LLMs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- run ---
    run_p = sub.add_parser("run", help="Run an eval suite against a single trace file.")
    run_p.add_argument(
        "--suite", required=True, help="Path to a YAML/JSON eval file or directory."
    )
    run_p.add_argument("--traces", required=True, help="Path to a JSON traces file.")
    run_p.add_argument("--variant", default="", help="Label for this variant.")
    run_p.add_argument("--threshold", type=float, default=0.5, help="Pass threshold (0-1).")
    run_p.add_argument("--output", help="Path to write JSON results.")
    run_p.add_argument(
        "--failures-only", action="store_true", help="Only show failure analysis."
    )

    # --- compare ---
    cmp_p = sub.add_parser("compare", help="Compare multiple variants on the same suite.")
    cmp_p.add_argument(
        "--suite", required=True, help="Path to a YAML/JSON eval file or directory."
    )
    cmp_p.add_argument(
        "--variants",
        nargs="+",
        required=True,
        metavar="NAME=PATH",
        help="Variant specifications as name=path pairs.",
    )
    cmp_p.add_argument("--threshold", type=float, default=0.5, help="Pass threshold (0-1).")
    cmp_p.add_argument("--output", help="Path to write JSON results.")

    return parser


def _load_suite(path_str: str) -> EvalSuite:
    p = Path(path_str)
    if p.is_dir():
        return EvalSuite.load_dir(p)
    return EvalSuite.load(p)


def _parse_variants(variant_args: list[str]) -> dict[str, str]:
    """Parse 'name=path' pairs into a dict."""
    result: dict[str, str] = {}
    for arg in variant_args:
        if "=" not in arg:
            print(f"Error: variant must be in NAME=PATH format, got: {arg}", file=sys.stderr)
            sys.exit(1)
        name, path = arg.split("=", 1)
        result[name.strip()] = path.strip()
    return result


def cmd_run(args: argparse.Namespace) -> None:
    suite = _load_suite(args.suite)
    traces = load_traces(args.traces)
    runner = EvalRunner(pass_threshold=args.threshold)

    results = runner.run(suite, traces, variant=args.variant)

    if args.failures_only:
        print(failure_analysis(results))
    else:
        print(summary_table(results))
        print()
        print(category_breakdown(results))
        print()
        print(difficulty_breakdown(results))
        print()
        print(failure_analysis(results))

    if args.output:
        save_json(results, args.output)
        print(f"\nResults written to {args.output}")


def cmd_compare(args: argparse.Namespace) -> None:
    suite = _load_suite(args.suite)
    variant_paths = _parse_variants(args.variants)
    runner = EvalRunner(pass_threshold=args.threshold)

    variant_traces = {name: load_traces(path) for name, path in variant_paths.items()}
    comparison = runner.compare(suite, variant_traces)

    print(comparison_table(comparison))

    # Per-variant details.
    for name, vr in comparison.variants.items():
        print(f"\n--- {name} ---")
        print(failure_analysis(vr))

    if args.output:
        save_json(comparison, args.output)
        print(f"\nResults written to {args.output}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "compare":
        cmd_compare(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
