"""Score a live-registry trace file by faithfulness, not canned ground truth.

Live tool outputs are non-static (real weather, real Wikipedia extracts), so
the deterministic is_correct against stored GTs is meaningless there. The
honest metrics for live runs are:

  completion_rate      - produced a final <answer>
  tool_call_validity   - tool calls parsed + executed without harness error
  faithfulness         - the answer's key content appears in the observations
                         (answer reports what the tool actually returned)
  restraint            - knowledge questions answered with zero tool calls

Faithfulness check: tokenize the answer and the concatenated observations;
the answer is faithful if >=60% of its content tokens (len>2, stopword-
filtered) appear in the observation text. Conservative and auditable — every
verdict can be eyeballed in the trace.

Usage: python scripts/score_live.py results/traces_release/v1-live-v2.json
"""

import json
import re
import sys
from pathlib import Path

STOP = {
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "of", "to",
    "for", "and", "or", "it", "its", "that", "this", "with", "as", "at",
    "by", "from", "be", "has", "have", "what", "which",
}


def tokens(text):
    return {t for t in re.findall(r"[a-z0-9\.\-]+", text.lower())
            if len(t) > 2 and t not in STOP}


def main():
    traces = json.loads(Path(sys.argv[1]).read_text())
    n = len(traces)
    completed = faithful = tool_ok = calls_total = 0
    restraint_n = restraint_ok = 0
    failures = []

    for t in traces:
        task = t["task"]
        calls = t.get("tool_calls") or []
        transcript = t.get("transcript", "")
        answer = (t.get("final_answer") or "").strip()

        calls_total += len(calls)
        obs_text = " ".join(
            m.group(1) for m in re.finditer(r"<observation>(.*?)</observation>",
                                            transcript, re.S)
        )
        for c in calls:
            if not c.get("error") and '"error"' not in obs_text.lower():
                tool_ok += 1
                break

        expected = task.get("expected_tools") or []
        if not expected:
            restraint_n += 1
            if not calls:
                restraint_ok += 1

        if answer:
            completed += 1
            if calls:
                a_toks, o_toks = tokens(answer), tokens(obs_text)
                if a_toks and len(a_toks & o_toks) / len(a_toks) >= 0.6:
                    faithful += 1
                elif a_toks:
                    failures.append((task["id"], answer[:80],
                                     sorted(a_toks - o_toks)[:6]))

    tool_tasks = n - restraint_n
    print(json.dumps({
        "n": n,
        "completion_rate": round(completed / n, 3),
        "tool_executed_cleanly": tool_ok,
        "faithfulness_on_tool_tasks": f"{faithful}/{tool_tasks}",
        "restraint": f"{restraint_ok}/{restraint_n}",
        "total_tool_calls": calls_total,
    }, indent=2))
    if failures:
        print("\nunfaithful answers (answer tokens missing from observations):")
        for tid, ans, missing in failures:
            print(f"  {tid}: {ans!r} missing={missing}")


if __name__ == "__main__":
    main()
