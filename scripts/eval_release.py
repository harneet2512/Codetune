"""Evaluate a merged ToolTune/Restraint checkpoint via llama.cpp server.

Reproduces the committed 50-task trace sample by default (same task IDs as
results/traces/*.json) so numbers are directly comparable across variants.

Usage:
    # terminal 1
    D:\\llamacpp\\llama-server.exe -m D:\\release\\restraint-7b-q4km.gguf -ngl 35 -c 4096 --port 8085

    # terminal 2
    python scripts/eval_release.py --tasks-same-as results/traces/base.json \
        --out results/traces_release/restraint-7b.json
"""

import argparse
import json
import random
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tooltune.contracts import TaskRecord
from tooltune.io import load_json, dump_json
from tools.registry import ToolRegistry
from train.agentic_loop import generate_agentic_completion
from train.reward import is_correct


class LlamaCppGenerator:
    """TextGenerator over llama-server's raw /completion endpoint."""

    def __init__(self, base_url="http://127.0.0.1:8085"):
        self.base_url = base_url.rstrip("/")
        self.tokens_predicted = 0
        self.tokens_evaluated = 0

    def generate(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.0) -> str:
        body = json.dumps({
            "prompt": prompt,
            "n_predict": max_new_tokens,
            "temperature": temperature,
            "top_p": 1.0,
            "stop": ["<|im_end|>", "\nUser:", "</answer>", "</tool_call>", "<observation>"],
            "cache_prompt": False,
        }).encode()
        req = urllib.request.Request(
            self.base_url + "/completion",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=600) as r:
            out = json.loads(r.read())
        content = out.get("content", "")
        self.tokens_predicted += out.get("tokens_predicted", 0)
        self.tokens_evaluated += out.get("tokens_evaluated", 0)
        # /completion stops before emitting stop strings; re-emit </answer> if truncated there
        if "<answer>" in content and "</answer>" not in content:
            content += "</answer>"
        if "<tool_call>" in content and "</tool_call>" not in content:
            content += "</tool_call>"
        return content


class ConnectorAdapter:
    """Adapts MockConnectorRegistry (GitHub/Drive/Gmail) to the ToolRegistry
    interface the agentic loop expects. Used for the unseen-tool-ecosystem
    eval: v3 task files, zero-shot schema transfer."""

    def __init__(self):
        from tools.connectors.mock import MockConnectorRegistry
        self._inner = MockConnectorRegistry()

    def tool_definitions(self):
        return self._inner.list_tools()

    def execute(self, tool_call, inject_errors=False, error_probability=0.2, random_seed=None):
        if inject_errors:
            rng = random.Random(random_seed)
            if rng.random() < error_probability:
                from tooltune.contracts import ToolObservation
                return ToolObservation(
                    tool_name=tool_call.name,
                    content=json.dumps({"error": "Service temporarily unavailable"}),
                    is_error=True,
                )
        return self._inner.execute(tool_call.name, tool_call.arguments)


def score(traces, gt_fixes=None):
    """Canonical scorer: is_correct from train/reward.py (numeric tolerance,
    normalized match) — the same function the original pipeline used."""
    gt_fixes = gt_fixes or {}
    n = len(traces)
    correct = used_tools = total_calls = 0
    restraint_n = restraint_ok = 0
    per_tier = {}
    for t in traces:
        task = t["task"]
        tier = task.get("tier", "?")
        per_tier.setdefault(tier, [0, 0])
        per_tier[tier][1] += 1
        gt = str(gt_fixes.get(task["id"], task.get("ground_truth", ""))).strip()
        fa = str(t.get("final_answer", "")).strip()
        if gt and fa and is_correct(fa, gt):
            correct += 1
            per_tier[tier][0] += 1
        calls = t.get("tool_calls") or []
        total_calls += len(calls)
        if calls:
            used_tools += 1
        if not (task.get("expected_tools") or []):
            restraint_n += 1
            if not calls:
                restraint_ok += 1
    return {
        "n": n,
        "task_accuracy": correct / n if n else 0,
        "tool_use_rate": used_tools / n if n else 0,
        "total_tool_calls": total_calls,
        "restraint": f"{restraint_ok}/{restraint_n}",
        "restraint_rate": restraint_ok / restraint_n if restraint_n else None,
        "per_tier": {k: f"{v[0]}/{v[1]}" for k, v in sorted(per_tier.items())},
        "held_out_tier4": per_tier.get("tier4_error_recovery"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8085")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--tasks-same-as", default=None,
                    help="JSON trace file to copy the task-ID sample from (for comparability)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tasks-glob", default="tier*.json",
                    help="glob under tasks/ (default tier*.json; use v3_tier*.json for unseen-tools eval)")
    ap.add_argument("--registry", choices=["v1", "v3", "live"], default="v1",
                    help="v1 = trained 5-tool set (simulated); v3 = unseen GitHub/Drive/Gmail "
                         "ecosystem; live = v1 schemas backed by real Open-Meteo/Wikipedia APIs")
    args = ap.parse_args()

    all_tasks = []
    for f in sorted(Path("tasks").glob(args.tasks_glob)):
        for item in load_json(f):
            all_tasks.append(TaskRecord(**item))

    if args.tasks_same_as:
        ref = json.loads(Path(args.tasks_same_as).read_text())
        want = {t["task"]["id"] for t in ref}
        tasks = [t for t in all_tasks if t.id in want][: args.n]
        print(f"matched {len(tasks)} task IDs from {args.tasks_same_as} (cap n={args.n})")
    else:
        random.seed(args.seed)
        random.shuffle(all_tasks)
        tasks = all_tasks[: args.n]

    gen = LlamaCppGenerator(args.url)
    if args.registry == "v1":
        registry = ToolRegistry()
    elif args.registry == "live":
        from tools.live_registry import LiveToolRegistry
        registry = LiveToolRegistry()
    else:
        registry = ConnectorAdapter()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    traces = []
    done_ids = set()
    if out.exists():
        traces = json.loads(out.read_text())
        done_ids = {t["task"]["id"] for t in traces}
        print(f"resuming: {len(done_ids)} traces already in {out}")
    for i, task in enumerate(tasks):
        if task.id in done_ids:
            continue
        print(f"[{i+1}/{len(tasks)}] {task.id}", flush=True)
        trace = generate_agentic_completion(
            generator=gen, task=task, registry=registry, max_steps=5, temperature=0.0
        )
        traces.append(trace.to_dict())
        dump_json(out, traces)  # persist after every task — resumable

    dump_json(out, traces)
    gt_fixes = {}
    fix_path = Path("results/gt_repair.json")
    if fix_path.exists():
        gt_fixes = json.loads(fix_path.read_text())
        print(f"applying {len(gt_fixes)} re-derived ground truths")
    scores = score(traces, gt_fixes)
    scores["tokens_generated_total"] = gen.tokens_predicted
    scores["tokens_prompt_total"] = gen.tokens_evaluated
    scores["gen_tokens_per_correct_task"] = (
        round(gen.tokens_predicted / scores["n"] / scores["task_accuracy"], 1)
        if scores["task_accuracy"] else None
    )
    print("\nSCORES:", json.dumps(scores, indent=2))
    print("saved ->", out)


if __name__ == "__main__":
    main()
