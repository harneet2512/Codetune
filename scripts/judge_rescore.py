"""Secondary judge scorer: rescore canonical-failures via a judge model.

The canonical scorer (is_correct) is exact/tolerance-based and marks
semantically-correct paraphrases as wrong (e.g. "government by the people"
vs reference "power is held by the people"). This script sends every
canonical failure to a judge model through OpenRouter and asks for a binary
equivalence verdict. Canonical score stays the headline; this produces the
secondary number that quantifies scorer strictness.

The judge prompt and model are committed here so the secondary score is
reproducible.

Usage:
    OPENROUTER_API_KEY=sk-or-... python scripts/judge_rescore.py \
        results/traces_release/restraint-7b-v2-fixed.json
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_release import score  # noqa: E402
from train.reward import is_correct  # noqa: E402

JUDGE_MODEL = "openai/gpt-4o-mini"  # pinned judge; change = different secondary score

PROMPT = """You are grading whether a model's answer is semantically equivalent to a reference answer.

Question: {question}
Reference answer: {gt}
Model answer: {pred}

Equivalent means: same factual claim, allowing different wording, different level of detail, and numeric values within rounding. Extra correct detail does not make it wrong. A wrong or missing core fact makes it wrong.

Reply with exactly one word: CORRECT or INCORRECT."""


def judge(question, gt, pred, key):
    body = json.dumps({
        "model": JUDGE_MODEL,
        "messages": [{"role": "user",
                      "content": PROMPT.format(question=question, gt=gt, pred=pred)}],
        "max_tokens": 5,
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    return out["choices"][0]["message"]["content"].strip().upper()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("traces")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY not set")

    traces = json.loads(Path(args.traces).read_text())
    gt_fixes = {}
    fix_path = Path("results/gt_repair.json")
    if fix_path.exists():
        gt_fixes = json.loads(fix_path.read_text())

    canonical = score(traces, gt_fixes)
    failures, judged_correct = [], 0
    for t in traces:
        task = t["task"]
        gt = str(gt_fixes.get(task["id"], task.get("ground_truth", ""))).strip()
        fa = str(t.get("final_answer") or "").strip()
        if not gt or not fa or is_correct(fa, gt):
            continue
        verdict = judge(task.get("prompt", ""), gt, fa, key)
        failures.append({"id": task["id"], "gt": gt, "answer": fa, "verdict": verdict})
        judged_correct += verdict == "CORRECT"
        print(f"{task['id']}: {verdict}  (gt={gt!r} vs {fa[:60]!r})", flush=True)

    n = canonical["n"]
    canon_correct = round(canonical["task_accuracy"] * n)
    result = {
        "canonical": canonical["task_accuracy"],
        "canonical_correct": f"{canon_correct}/{n}",
        "canonical_failures_judged": len(failures),
        "judge_overturned": judged_correct,
        "secondary_accuracy": round((canon_correct + judged_correct) / n, 4),
        "judge_model": JUDGE_MODEL,
        "failures": failures,
    }
    out = Path(args.out or Path(args.traces).with_suffix(".judge.json"))
    out.write_text(json.dumps(result, indent=2))
    print("\n" + json.dumps({k: v for k, v in result.items() if k != "failures"},
                            indent=2))
    print("saved ->", out)


if __name__ == "__main__":
    main()
