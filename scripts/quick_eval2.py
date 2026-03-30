"""Quick eval: compare base vs SFT vs GRPO traces against task ground truth."""
import json
import os


def eval_variant(filepath):
    with open(filepath) as f:
        traces = json.load(f)

    correct = 0
    used_tools = 0
    has_format = 0
    restraint_ok = 0
    restraint_total = 0
    total = len(traces)

    for tr in traces:
        task = tr.get("task", {})
        gt = str(task.get("ground_truth", "")).strip().lower()
        expected = task.get("expected_tools", [])
        fa = str(tr.get("final_answer", "")).strip().lower()

        matched = False
        try:
            fv, gv = float(fa), float(gt)
            if abs(fv - gv) < 0.1 * max(abs(gv), 1):
                matched = True
        except (ValueError, ZeroDivisionError):
            pass
        if not matched and fa and gt and (fa == gt or gt in fa or fa in gt):
            matched = True
        if matched:
            correct += 1

        tc = tr.get("tool_calls", [])
        if tc:
            used_tools += 1

        transcript = str(tr.get("transcript", ""))
        if "<answer>" in transcript or "<tool_call>" in transcript:
            has_format += 1

        if not expected:
            restraint_total += 1
            if not tc:
                restraint_ok += 1

    return total, correct, used_tools, has_format, restraint_ok, restraint_total


def main():
    sep = "=" * 72
    print(sep)
    header = "Metric".ljust(32) + "BASE".rjust(12) + "SFT".rjust(12) + "GRPO".rjust(12)
    print(header)
    print(sep)

    data = {}
    for name, path in [
        ("BASE", "results/traces/base.json"),
        ("SFT", "results/traces/sft.json"),
        ("GRPO", "results/traces/grpo-balanced.json"),
    ]:
        if os.path.exists(path):
            data[name] = eval_variant(path)

    names = ["BASE", "SFT", "GRPO"]

    # Tasks row
    row = "Tasks Evaluated".ljust(32)
    for n in names:
        if n in data:
            row += str(data[n][0]).rjust(12)
        else:
            row += "--".rjust(12)
    print(row)

    # Metric rows
    labels = [
        ("Task Accuracy", 1),
        ("Tool Usage Rate", 2),
        ("Correct Format", 3),
    ]
    for label, idx in labels:
        row = label.ljust(32)
        for n in names:
            if n in data:
                val = data[n][idx]
                tot = data[n][0]
                pct = val * 100.0 / tot if tot else 0
                row += "{:>5}/{} {:5.1f}%".format(val, tot, pct)
            else:
                row += "--".rjust(12)
        print(row)

    # Restraint row
    row = "Restraint (avoided tools)".ljust(32)
    for n in names:
        if n in data:
            ok = data[n][4]
            tot = data[n][5]
            pct = ok * 100.0 / tot if tot else 0
            row += "{:>5}/{} {:5.1f}%".format(ok, tot, pct)
        else:
            row += "--".rjust(12)
    print(row)

    print(sep)

    # Samples
    for name, path in [
        ("BASE", "results/traces/base.json"),
        ("SFT", "results/traces/sft.json"),
        ("GRPO", "results/traces/grpo-balanced.json"),
    ]:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            traces = json.load(f)
        print("")
        print("--- " + name + " samples ---")
        for tr in traces[:3]:
            task = tr.get("task", {})
            q = task.get("prompt", "")[:80]
            fa = str(tr.get("final_answer", ""))[:60]
            gt = str(task.get("ground_truth", ""))[:60]
            tc = len(tr.get("tool_calls", []))
            ok = "OK" if fa.strip().lower() == gt.strip().lower() else "MISS"
            print("  [" + ok + "] Q: " + q)
            print("       Got: " + fa + "  | Expected: " + gt + "  | Tools: " + str(tc))


if __name__ == "__main__":
    main()

