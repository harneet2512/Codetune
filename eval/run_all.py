"""Run all ToolTune evaluation suites over stored traces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.suites import agentic_behavior, reasoning_quality, task_completion, tool_quality
from tooltune.io import dump_json, load_json

SUITES = {
    "task_completion": task_completion.run,
    "tool_quality": tool_quality.run,
    "agentic_behavior": agentic_behavior.run,
    "reasoning_quality": reasoning_quality.run,
}


def run_all(input_path: str, output_path: str) -> dict:
    traces = load_json(input_path)
    results = {
        "input": input_path,
        "total_traces": len(traces),
        "suites": {},
    }
    for name, runner in SUITES.items():
        results["suites"][name] = runner(traces)
    dump_json(output_path, results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ToolTune eval suites")
    parser.add_argument("--input", required=True, help="Path to trace JSON")
    parser.add_argument("--output", default="results/eval/tooltune_eval.json")
    args = parser.parse_args()

    results = run_all(args.input, args.output)
    print(json.dumps(results["suites"], indent=2))


if __name__ == "__main__":
    main()
