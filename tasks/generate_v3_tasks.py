"""Generate and save ToolTune v3 task suites across all 4 tiers.

Generates tasks for the 17 connector tools (GitHub, Drive, Gmail) and saves
them as JSON files in the tasks/ directory.

Usage::

    python -m tasks.generate_v3_tasks
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tooltune.io import dump_json
from tooltune.paths import TASKS_DIR
from tasks.v3_tasks import build_tier1, build_tier2, build_tier3, build_tier4


def main() -> None:
    suites = {
        "v3_tier1.json": build_tier1(100),
        "v3_tier2.json": build_tier2(80),
        "v3_tier3.json": build_tier3(50),
        "v3_tier4.json": build_tier4(20),
    }

    total = 0
    restraint_count = 0
    for filename, records in suites.items():
        payload = [r.to_dict() for r in records]
        dump_json(TASKS_DIR / filename, payload)
        n = len(payload)
        total += n
        if "tier2" in filename:
            restraint_count = n
        print(f"  {filename}: {n} tasks")

    print(f"\n  Total: {total} tasks")
    restraint_pct = restraint_count / total * 100 if total > 0 else 0
    print(f"  Restraint (Tier 2): {restraint_count}/{total} = {restraint_pct:.1f}%")

    if restraint_pct < 30:
        print(f"  WARNING: Restraint tasks below 30% threshold ({restraint_pct:.1f}%)")
    else:
        print(f"  Restraint ratio meets >=30% requirement")

    # Summary by category
    print("\n  Breakdown:")
    all_records = []
    for records in suites.values():
        all_records.extend(records)

    categories: dict[str, int] = {}
    tools_used: dict[str, int] = {}
    for r in all_records:
        cat = r.metadata.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        for t in r.expected_tools:
            tools_used[t] = tools_used.get(t, 0) + 1

    print("  By category:")
    for cat, count in sorted(categories.items()):
        print(f"    {cat}: {count}")

    print("  By tool (expected_tools):")
    for tool, count in sorted(tools_used.items(), key=lambda x: -x[1]):
        print(f"    {tool}: {count}")
    if not tools_used:
        # restraint tasks have no tools
        pass
    print(f"    (no tools / restraint): {restraint_count}")


if __name__ == "__main__":
    main()
