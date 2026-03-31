"""Quick eval script to compare base vs SFT vs GRPO traces."""
import json
import sys
from pathlib import Path


def eval_traces(filepath):
    with open(filepath) as f:
        traces = json.load(f)

    correct = 0
    used_tools = 0
    tool_calls_total = 0
    has_think = 0
    total = len(traces)

    for t in traces:
        fa = str(t.get("final_answer", "")).strip().lower()
        gt = str(t.get("ground_truth", "")).strip().lower()

        # Numeric comparison
        try:
            fv = float(fa)
            gv = float(gt)
            if abs(fv - gv) < 0.1 * max(abs(gv), 1):
                correct += 1
                continue
        except (ValueError, ZeroDivisionError):
            pass

        if fa and gt and (fa == gt or gt in fa or fa in gt):
            correct += 1

        tc = t.get("tool_calls", [])
        if tc:
            used_tools += 1
        tool_calls_total += len(tc) if tc else 0

        transcript = str(t.get("transcript", ""))
        if "<think>" in transcript:
            has_think += 1

    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total * 100 if total else 0,
        "tool_usage_rate": used_tools / total * 100 if total else 0,
        "avg_tool_calls": tool_calls_total / total if total else 0,
        "think_rate": has_think / total * 100 if total else 0,
    }


def main():
    traces_dir = Path("results/traces")
    variants = ["base", "sft", "grpo-balanced"]

    print("=" * 70)
    print(f"{'Metric':<25} ", end="")
    for v in variants:
        print(f"{'BASE':>12}" if v == "base" else f"{'SFT':>12}" if v == "sft" else f"{'GRPO':>12}", end="")
    print()
    print("=" * 70)

    results = {}
    for v in variants:
        fp = traces_dir / f"{v}.json"
        if fp.exists():
            results[v] = eval_traces(fp)
        else:
            results[v] = None
            print(f"  [{v}] not found yet")

    metrics = [
        ("Task Accuracy (%)", "accuracy"),
        ("Tool Usage Rate (%)", "tool_usage_rate"),
        ("Avg Tool Calls/Task", "avg_tool_calls"),
        ("Think Rate (%)", "think_rate"),
        ("Tasks Evaluated", "total"),
    ]

    for label, key in metrics:
        print(f"{label:<25} ", end="")
        for v in variants:
            if results.get(v):
                val = results[v][key]
                if isinstance(val, float):
                    print(f"{val:>12.1f}", end="")
                else:
                    print(f"{val:>12}", end="")
            else:
                print(f"{'--':>12}", end="")
        print()

    print("=" * 70)

    # Show sample traces from each variant
    for v in variants:
        fp = traces_dir / f"{v}.json"
        if not fp.exists():
            continue
        with open(fp) as f:
            traces = json.load(f)
        print(f"\n--- Sample from {v.upper()} ---")
        for t in traces[:3]:
            prompt = t.get("prompt", "")[:80]
            fa = str(t.get("final_answer", ""))[:50]
            gt = str(t.get("ground_truth", ""))[:50]
            tc = len(t.get("tool_calls", []))
            print(f"  Q: {prompt}")
            print(f"  A: {fa}  | Expected: {gt}  | Tools: {tc}")
            print()


if __name__ == "__main__":
    main()
