"""Re-derive task ground truths from the simulated environment.

Found in eval audit: task GTs drifted from the canned simulator data —
e.g. weather GT says 32.0F but weather.json returns 33.8F; wiki GT says
11.7M but wikipedia_facts returns 11.8M. Models answering faithfully from
tool output were scored wrong.

This emits results/gt_repair.json = {task_id: new_ground_truth} plus a
human-readable diff report. Originals are NOT mutated — eval_release.py
applies the sidecar map. Restraint (tier2) GTs are knowledge answers, no
env involved — left untouched.

Usage: python scripts/repair_ground_truth.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tooltune.io import load_json, dump_json
from tooltune.paths import DATA_DIR
from tools import weather as weather_tool
from tools import wikipedia as wiki_tool
from tools import calculator, unit_converter, code_executor

_OP_WORDS = {"multiplied": "*", "times": "*", "plus": "+", "minus": "-", "divided": "/"}


def _extract_expression(prompt: str) -> str:
    """Same logic as train/sft_tooltune.py (inlined — avoids the trl import)."""
    m = re.search(r"(\d+)\s*([+\-*/])\s*(\d+)", prompt)
    if m:
        return f"{m.group(1)} {m.group(2)} {m.group(3)}"
    for word, op in _OP_WORDS.items():
        m = re.search(rf"(\d+)\s+{word}\s+(?:by\s+)?(\d+)", prompt, re.IGNORECASE)
        if m:
            return f"{m.group(1)} {op} {m.group(2)}"
    nums = re.findall(r"\d+", prompt)
    if len(nums) >= 2:
        return f"{nums[0]} + {nums[1]}"
    return prompt

OUT = Path("results/gt_repair.json")
REPORT = Path("results/gt_repair_report.txt")

WEATHER = load_json(DATA_DIR / "weather.json")
FACTS = load_json(DATA_DIR / "wikipedia_facts.json")


def parse_pop(fact: str) -> float:
    """Extract 'approximately N million' (or plain N) from a wiki fact."""
    m = re.search(r"approximately\s+([\d.]+)\s+million", fact)
    if m:
        return float(m.group(1))
    m = re.search(r"approximately\s+([\d.]+)", fact)
    if m:
        return float(m.group(1))
    m = re.search(r"([\d.]+)", fact)
    if not m:
        raise ValueError(f"no number in fact: {fact!r}")
    return float(m.group(1))


def derive(task: dict) -> str:
    md = task.get("metadata") or {}
    cat = md.get("category", "")
    pat = md.get("pattern", "")
    tools = task.get("expected_tools") or []

    if cat == "weather":
        w = WEATHER[md["city"].strip().lower()]
        return f"{w['conditions']}, {w['temp_celsius']}C"

    if cat == "calculator":
        return calculator.run(_extract_expression(task["prompt"]))

    if cat == "unit_converter":
        return unit_converter.run(float(md["value"]), md["from_unit"], md["to_unit"])

    if cat == "wikipedia":
        return FACTS[md["query_key"].strip().lower()]

    if cat == "code_executor":
        return code_executor.run(md["code"]).strip()

    if cat == "restraint" or not tools:
        return task["ground_truth"]  # no env — keep

    # ---- multi-step / error-recovery patterns (same GT derivation) ----
    if pat == "weather_convert":
        w = WEATHER[md["city"].strip().lower()]
        return unit_converter.run(float(w["temp_celsius"]), "celsius", "fahrenheit")

    if pat == "pop_ratio":
        a = parse_pop(wiki_tool.run(md["query_a"]))
        b = parse_pop(wiki_tool.run(md["query_b"]))
        return str(round(a / b, 1))

    if pat == "distance_cost":
        cost = md["miles"] / md["mpg"] * md["price"]
        return str(round(cost, 2))

    if pat == "temp_diff":
        a = WEATHER[md["city_a"].strip().lower()]["temp_celsius"]
        b = WEATHER[md["city_b"].strip().lower()]["temp_celsius"]
        d = abs(a - b)
        return str(int(d)) if float(d).is_integer() else str(round(d, 1))

    if pat == "wiki_code":
        pop = parse_pop(wiki_tool.run(md["query_key"]))
        val = pop * (1 + md["rate"] / 100) ** md["years"]
        return str(round(val, 2))

    raise ValueError(f"unhandled task shape: {task['id']} cat={cat} pat={pat}")


def main():
    fixes, report, errors = {}, [], []
    for f in sorted(Path("tasks").glob("tier*.json")):
        for t in load_json(f):
            try:
                new_gt = derive(t)
            except Exception as e:
                errors.append((t["id"], str(e)))
                continue
            if str(new_gt).strip() != str(t["ground_truth"]).strip():
                fixes[t["id"]] = new_gt
                report.append(
                    f"{t['id']}\n  old: {t['ground_truth']!r}\n  new: {new_gt!r}")

    dump_json(OUT, fixes)
    REPORT.write_text(
        f"{len(fixes)} ground truths re-derived from environment\n"
        f"{len(errors)} tasks could not be auto-derived\n\n"
        + "\n".join(report))
    print(f"wrote {OUT}: {len(fixes)} fixes | errors: {len(errors)}")
    for e in errors[:10]:
        print("  ERR", e)


if __name__ == "__main__":
    main()
