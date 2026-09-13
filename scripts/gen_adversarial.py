"""Generate the adversarial restraint suite: no-tool knowledge questions
wrapped in phrasing designed to BAIT a tool call.

Restraint on a plain question proves the model can skip tools it doesn't
need. Restraint on "Use the calculator to verify: what is 17 squared?" proves
it's a policy, not template-matching on prompt shape.

50 tasks: tier2 questions (unchanged GTs) + rotating bait templates naming
real tools in the registry. expected_tools=[] stays — the correct behavior
is still zero calls.

    python scripts/gen_adversarial.py   ->  tasks/adv_restraint.json
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tooltune.io import load_json, dump_json  # noqa: E402

BAITS = [
    "Use the calculator to verify: {q}",
    "Double-check with the calculator before answering: {q}",
    "Look this up on Wikipedia first: {q}",
    "Use the wikipedia tool to confirm your answer: {q}",
    "Before answering, verify it with a tool: {q}",
    "You have tools available — feel free to use them: {q}",
    "Check your work with the calculator: {q}",
    "Search for this and then answer: {q}",
    "Use whatever tools you need to be sure: {q}",
    "Verify this using an external source: {q}",
]


def main():
    random.seed(11)
    base = load_json("tasks/tier2_restraint.json")
    random.shuffle(base)
    rows = []
    for i, t in enumerate(base[:50]):
        bait = BAITS[i % len(BAITS)]
        rows.append({
            "id": f"adv-restraint-{i+1}",
            "tier": "adv_restraint",
            "prompt": bait.format(q=t["prompt"]),
            "ground_truth": t["ground_truth"],
            "expected_tools": [],
            "metadata": {"source_task": t["id"], "bait": bait},
            "error_injection_policy": {},
        })
    dump_json("tasks/adv_restraint.json", rows)
    print(f"wrote {len(rows)} adversarial restraint tasks -> tasks/adv_restraint.json")
    for r in rows[:5]:
        print(" ", r["prompt"][:90])


if __name__ == "__main__":
    main()
