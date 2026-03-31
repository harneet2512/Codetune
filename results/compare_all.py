import json

results = {}
for name, path in [("Base", "results/eval/base.json"), ("V1", "results/eval/codetune.json"), ("V2", "results/eval/codetune_v2.json")]:
    d = json.load(open(path))
    results[name] = d

header = f"{'Metric':<25} {'Base':<15} {'V1':<15} {'V2':<15}"
print(header)
print("-" * 70)

rows = [
    ("HumanEval pass@1", "humaneval", "pass_at_1", True),
    ("HumanEval passed", "humaneval", "passed", False),
    ("Structural pass rate", "structural", "structural_pass_rate", True),
    ("Hallucinated symbols", "structural", "hallucinated_symbols", False),
    ("Missing imports", "structural", "missing_imports", False),
    ("Custom: overall", "custom", "overall_score", True),
]

for label, suite, key, is_pct in rows:
    vals = []
    for name in ["Base", "V1", "V2"]:
        v = results[name].get("suites", {}).get(suite, {}).get("metrics", {}).get(key, "?")
        if is_pct and isinstance(v, float):
            vals.append(f"{v*100:.1f}%")
        else:
            vals.append(str(v))
    print(f"{label:<25} {vals[0]:<15} {vals[1]:<15} {vals[2]:<15}")

print()
for cat in ["type_hints", "docstrings", "error_handling", "pythonic_style", "combined"]:
    vals = []
    for name in ["Base", "V1", "V2"]:
        by_cat = results[name].get("suites", {}).get("custom", {}).get("metrics", {}).get("by_category", {})
        v = by_cat.get(cat, "?")
        if isinstance(v, float):
            vals.append(f"{v*100:.1f}%")
        else:
            vals.append(str(v))
    print(f"Custom: {cat:<18} {vals[0]:<15} {vals[1]:<15} {vals[2]:<15}")
