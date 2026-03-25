"""Analyze benchmark results and generate comparison tables."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    return float(np.percentile(values, p))


def analyze_endpoint(results: list[dict], batch_size: int) -> dict:
    """Compute aggregate metrics for an endpoint at a specific batch size."""
    filtered = [r for r in results if r.get("batch_size") == batch_size and "error" not in r]

    if not filtered:
        return {"error": f"No results for batch_size={batch_size}"}

    ttfts = [r["ttft_ms"] for r in filtered if r.get("ttft_ms") is not None]
    total_times = [r["total_time_ms"] for r in filtered]
    tps_values = [r["tokens_per_second"] for r in filtered if r.get("tokens_per_second", 0) > 0]
    tpot_values = [r["time_per_output_token_ms"] for r in filtered if r.get("time_per_output_token_ms", 0) > 0]
    total_tokens = sum(r.get("tokens_generated", 0) for r in filtered)

    return {
        "batch_size": batch_size,
        "num_requests": len(filtered),
        "ttft_p50_ms": round(percentile(ttfts, 50), 2) if ttfts else None,
        "ttft_p99_ms": round(percentile(ttfts, 99), 2) if ttfts else None,
        "throughput_tokens_per_sec": round(float(np.mean(tps_values)), 2) if tps_values else 0,
        "tpot_p50_ms": round(percentile(tpot_values, 50), 2) if tpot_values else None,
        "tpot_p99_ms": round(percentile(tpot_values, 99), 2) if tpot_values else None,
        "total_tokens_generated": total_tokens,
        "avg_total_time_ms": round(float(np.mean(total_times)), 2) if total_times else 0,
    }


def compute_cost(throughput_tps: float, gpu_hourly_rate: float = 3.67) -> float:
    """Compute cost per 1M output tokens."""
    if throughput_tps <= 0:
        return float("inf")
    seconds_per_1m_tokens = 1_000_000 / throughput_tps
    hours = seconds_per_1m_tokens / 3600
    return round(hours * gpu_hourly_rate, 2)


def generate_report(all_results: dict, gpu_hourly_rate: float = 3.67) -> str:
    """Generate a markdown comparison report."""
    # Parse endpoint names into framework + quantization
    endpoint_map: dict[str, dict[str, dict]] = {}  # framework -> quant -> metrics

    for endpoint_name, results in all_results.items():
        parts = endpoint_name.split("_", 1)
        if len(parts) == 2:
            framework, quant = parts
        else:
            framework, quant = endpoint_name, "unknown"

        if framework not in endpoint_map:
            endpoint_map[framework] = {}

        # Use batch_size=4 as the default comparison point
        metrics = analyze_endpoint(results, batch_size=4)
        if "error" in metrics:
            metrics = analyze_endpoint(results, batch_size=1)
        endpoint_map[framework][quant] = metrics

    frameworks = sorted(endpoint_map.keys())
    quant_levels = ["fp16", "int8", "int4"]

    lines = [
        "## Serving Benchmark: CodeTune 8B",
        "",
        "### Throughput (tokens/sec, batch_size=4)",
        "",
        "| Framework | " + " | ".join(q.upper() for q in quant_levels) + " |",
        "|-----------|" + "|".join("------" for _ in quant_levels) + "|",
    ]

    for fw in frameworks:
        values = []
        for q in quant_levels:
            m = endpoint_map.get(fw, {}).get(q, {})
            tps = m.get("throughput_tokens_per_sec", "—")
            values.append(str(tps))
        lines.append(f"| {fw} | " + " | ".join(values) + " |")

    lines.extend(["", "### TTFT p99 (ms, batch_size=4)", ""])
    lines.append("| Framework | " + " | ".join(q.upper() for q in quant_levels) + " |")
    lines.append("|-----------|" + "|".join("------" for _ in quant_levels) + "|")

    for fw in frameworks:
        values = []
        for q in quant_levels:
            m = endpoint_map.get(fw, {}).get(q, {})
            ttft = m.get("ttft_p99_ms", "—")
            values.append(str(ttft))
        lines.append(f"| {fw} | " + " | ".join(values) + " |")

    lines.extend([
        "",
        f"### Cost per 1M tokens (GCP A100 @ ${gpu_hourly_rate}/hr, batch_size=4)",
        "",
        "| Framework | " + " | ".join(q.upper() for q in quant_levels) + " |",
        "|-----------|" + "|".join("------" for _ in quant_levels) + "|",
    ])

    for fw in frameworks:
        values = []
        for q in quant_levels:
            m = endpoint_map.get(fw, {}).get(q, {})
            tps = m.get("throughput_tokens_per_sec", 0)
            if tps and tps > 0:
                cost = compute_cost(tps, gpu_hourly_rate)
                values.append(f"${cost}")
            else:
                values.append("—")
        lines.append(f"| {fw} | " + " | ".join(values) + " |")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze benchmark results")
    parser.add_argument("--input", default="results/bench/all_results.json", help="Results JSON")
    parser.add_argument("--output", default="results/bench/comparison.md", help="Output markdown")
    parser.add_argument("--gpu-rate", type=float, default=3.67, help="GPU hourly rate ($)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    with open(args.input) as f:
        all_results = json.load(f)

    report = generate_report(all_results, args.gpu_rate)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)

    print(report)
    logger.info(f"Report saved to {output_path}")


if __name__ == "__main__":
    main()
