"""Merge chunked eval traces from the Modal `restraint-eval` volume and score.

Chunks are written by scripts/modal_eval.py as
  traces/{suite}-{model}-chunk{i}.json       (list of trace dicts)
  traces/{suite}-{model}-chunk{i}.meta.json  ({"tokens_predicted": ..., "tokens_evaluated": ...})

Usage:
    modal volume get restraint-eval traces/ results/traces_modal/ --force
    python scripts/merge_eval_chunks.py v1-v2 --out results/traces_release/v1-200-v2.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_release import score  # noqa: E402


def wilson(k, n, z=1.96):
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return round(center - half, 4), round(center + half, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="chunk prefix, e.g. v1-v2, v1-baseline, v3-v2, paired50-v2-bf16")
    ap.add_argument("--dir", default="results/traces_modal/traces")
    ap.add_argument("--out", default=None, help="merged trace output path")
    args = ap.parse_args()

    src = Path(args.dir)
    chunks = sorted(src.glob(f"{args.name}-chunk*.json"))
    metas = sorted(src.glob(f"{args.name}-chunk*.meta.json"))
    if not chunks:
        sys.exit(f"no chunks matching {src}/{args.name}-chunk*.json")

    traces, seen = [], set()
    for f in chunks:
        if f.name.endswith(".meta.json"):
            continue
        for t in json.loads(f.read_text()):
            tid = t["task"]["id"]
            if tid in seen:
                print(f"WARNING duplicate task id {tid} across chunks", file=sys.stderr)
                continue
            seen.add(tid)
            traces.append(t)

    tokens_pred = tokens_eval = 0
    for f in metas:
        m = json.loads(f.read_text())
        tokens_pred += m.get("tokens_predicted", 0)
        tokens_eval += m.get("tokens_evaluated", 0)

    out = Path(args.out or f"results/traces_release/{args.name}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(traces))

    gt_fixes = {}
    fix_path = Path("results/gt_repair.json")
    if fix_path.exists() and "v3" not in args.name:
        gt_fixes = json.loads(fix_path.read_text())

    scores = score(traces, gt_fixes)
    correct = round(scores["task_accuracy"] * scores["n"])
    scores["task_accuracy_ci95"] = wilson(correct, scores["n"])
    if scores["restraint"] and "/" in scores["restraint"]:
        ok, tot = (int(x) for x in scores["restraint"].split("/"))
        scores["restraint_ci95"] = wilson(ok, tot)
    scores["tokens_generated_total"] = tokens_pred
    scores["tokens_prompt_total"] = tokens_eval
    scores["gen_tokens_per_correct_task"] = (
        round(tokens_pred / correct, 1) if correct else None)
    scores["total_tokens_per_correct_task"] = (
        round((tokens_pred + tokens_eval) / correct, 1) if correct else None)

    print(f"merged {len(traces)} traces from {len(chunks)} chunks -> {out}")
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
