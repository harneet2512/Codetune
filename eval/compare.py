"""Compare evaluation results between two models and generate a markdown report."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_results(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def format_value(v) -> str:
    if isinstance(v, float):
        if v < 1:
            return f"{v * 100:.1f}%"
        return f"{v:.2f}"
    return str(v)


def format_delta(base_v, ft_v) -> str:
    if isinstance(base_v, float) and isinstance(ft_v, float):
        delta = ft_v - base_v
        if abs(base_v) < 1 and abs(ft_v) < 1:  # Percentage-like
            return f"{delta * 100:+.1f}%"
        return f"{delta:+.2f}"
    if isinstance(base_v, int) and isinstance(ft_v, int):
        return f"{ft_v - base_v:+d}"
    return "—"


def compare(base_path: str, finetuned_path: str, output: str | None = None) -> str:
    """Generate a markdown comparison report."""
    base = load_results(base_path)
    ft = load_results(finetuned_path)

    base_name = base.get("model", "Base Model").split("/")[-1]
    ft_name = ft.get("model", "Fine-tuned Model").split("/")[-1]

    lines = [
        f"## CodeTune Evaluation: {base_name} vs {ft_name}",
        "",
        f"| Metric | {base_name} | {ft_name} | Delta |",
        "|--------|------------|-----------|-------|",
    ]

    # Collect all metrics from both runs
    all_suites = set(list(base.get("suites", {}).keys()) + list(ft.get("suites", {}).keys()))

    for suite_name in sorted(all_suites):
        base_suite = base.get("suites", {}).get(suite_name, {})
        ft_suite = ft.get("suites", {}).get(suite_name, {})

        base_metrics = base_suite.get("metrics", {})
        ft_metrics = ft_suite.get("metrics", {})

        all_metric_keys = set(list(base_metrics.keys()) + list(ft_metrics.keys()))

        for key in sorted(all_metric_keys):
            # Skip non-numeric and nested dict metrics for main table
            base_v = base_metrics.get(key)
            ft_v = ft_metrics.get(key)

            if isinstance(base_v, dict) or isinstance(ft_v, dict):
                continue
            if isinstance(base_v, str) or isinstance(ft_v, str):
                continue

            if base_v is None:
                base_v = "—"
                delta = "—"
            elif ft_v is None:
                ft_v = "—"
                delta = "—"
            else:
                delta = format_delta(base_v, ft_v)

            display_name = f"{suite_name}: {key}"
            lines.append(
                f"| {display_name} | {format_value(base_v)} | {format_value(ft_v)} | {delta} |"
            )

    # Add category breakdowns for custom suite
    for suite_name in ["custom"]:
        for results_dict, label in [(base, base_name), (ft, ft_name)]:
            suite = results_dict.get("suites", {}).get(suite_name, {})
            by_cat = suite.get("metrics", {}).get("by_category", {})
            if by_cat:
                lines.append("")
                lines.append(f"### Custom Eval by Category ({label})")
                lines.append("")
                lines.append("| Category | Score |")
                lines.append("|----------|-------|")
                for cat, score in sorted(by_cat.items()):
                    lines.append(f"| {cat} | {score * 100:.1f}% |")

    # Metadata
    lines.extend([
        "",
        "---",
        "",
        f"*Base model evaluated: {base.get('timestamp', 'unknown')}*  ",
        f"*Fine-tuned model evaluated: {ft.get('timestamp', 'unknown')}*  ",
        f"*Hardware: {base.get('hardware', {}).get('gpu', 'unknown')}*",
    ])

    report = "\n".join(lines)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)
        logger.info(f"Comparison report saved to {output_path}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two eval result files")
    parser.add_argument("base", help="Path to base model results JSON")
    parser.add_argument("finetuned", help="Path to fine-tuned model results JSON")
    parser.add_argument("--output", help="Output markdown file path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    report = compare(args.base, args.finetuned, args.output)
    print(report)


if __name__ == "__main__":
    main()
