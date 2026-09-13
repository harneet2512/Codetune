"""Release gate: score a trace file against hard thresholds, exit 1 on breach.

This is how the eval becomes a CI gate for model changes — any candidate
checkpoint produces traces (eval_release.py / modal_eval.py), then:

    python scripts/model_gate.py results/traces_release/v1-v2.json

Gates (thresholds chosen from measured results, not aspirations):
  - restraint_rate   >= 0.80   (the headline behavior)
  - tier1 accuracy   >= 0.95   (core tool use must not regress)
  - task_accuracy    >= 0.75
  - parse failures   <= 10%    (final_answer containing raw markup = the loop
                                couldn't parse the model's output)
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_release import score  # noqa: E402

GATES = [
    ("restraint_rate", ">=", 0.80),
    ("tier1_acc", ">=", 0.95),
    ("task_accuracy", ">=", 0.75),
    ("parse_failure_rate", "<=", 0.10),
]


def metrics(traces):
    s = score(traces)
    t1 = s["per_tier"].get("tier1_single_tool", "0/0")
    t1_ok, t1_n = (int(x) for x in t1.split("/"))
    parse_fail = sum(
        1 for t in traces
        if "<" in str(t.get("final_answer") or "")
    )
    return {
        "restraint_rate": s["restraint_rate"],
        # None when the suite has no tier1 tasks (e.g. adversarial-only)
        "tier1_acc": (t1_ok / t1_n) if t1_n else None,
        "task_accuracy": s["task_accuracy"],
        "parse_failure_rate": parse_fail / len(traces) if traces else 1.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("traces")
    args = ap.parse_args()

    traces = json.loads(Path(args.traces).read_text())
    m = metrics(traces)
    ok = True
    print(f"gate: {args.traces}  (n={len(traces)})")
    for key, op, thr in GATES:
        v = m[key]
        if v is None:
            print(f"  SKIP  {key}  (not present in suite)")
            continue
        passed = (v >= thr) if op == ">=" else (v <= thr)
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {key}={v:.3f}  {op} {thr}")
    if not ok:
        sys.exit("GATE FAILED")
    print("GATE PASSED")


if __name__ == "__main__":
    main()
