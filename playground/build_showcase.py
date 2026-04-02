"""Convert raw training traces into playground showcase format.

Reads results/traces/{base,sft,grpo-balanced}.json and produces
playground/data/showcase.json with the structure the frontend expects.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACES_DIR = ROOT / "results" / "traces"
OUT = ROOT / "playground" / "data" / "showcase.json"

CATEGORY_META = {
    "calculator": {"icon": "hash", "label": "Calculator", "difficulty": "Easy"},
    "unit_converter": {"icon": "repeat", "label": "Unit Conversion", "difficulty": "Easy"},
    "weather": {"icon": "cloud", "label": "Weather Lookup", "difficulty": "Easy"},
    "wikipedia": {"icon": "book-open", "label": "Knowledge Lookup", "difficulty": "Easy"},
    "code_executor": {"icon": "terminal", "label": "Code Execution", "difficulty": "Medium"},
    "restraint": {"icon": "shield", "label": "Restraint", "difficulty": "Medium"},
    "multi_step": {"icon": "git-branch", "label": "Multi-step", "difficulty": "Hard"},
    "error_recovery": {"icon": "alert-triangle", "label": "Error Recovery", "difficulty": "Hard"},
}

TIER_LABELS = {
    "tier1_single_tool": "Tier 1 — Single Tool",
    "tier2_restraint": "Tier 2 — Restraint",
    "tier3_multi_step": "Tier 3 — Multi-step",
    "tier4_error_recovery": "Tier 4 — Error Recovery",
}


def parse_steps_to_nodes(steps: list[dict], transcript: str) -> list[dict]:
    """Convert raw steps into flowchart nodes."""
    nodes = []
    for i, step in enumerate(steps):
        phase = step["phase"]
        content = step["content"]
        node_id = f"n{i}"

        if phase == "think":
            nodes.append({
                "id": node_id,
                "type": "think",
                "title": "Reasoning",
                "summary": content[:120] + ("..." if len(content) > 120 else ""),
                "content": content,
                "decision": _extract_decision(content),
            })
        elif phase == "tool_call":
            try:
                call = json.loads(content)
                tool_name = call.get("name", "unknown")
                args = call.get("arguments", {})
                args_str = ", ".join(f'{k}="{v}"' for k, v in args.items())
                nodes.append({
                    "id": node_id,
                    "type": "tool_call",
                    "title": f"{tool_name}({args_str})"[:80],
                    "summary": f"Calling {tool_name} tool",
                    "content": json.dumps(call, indent=2),
                    "status": "executed",
                })
            except (json.JSONDecodeError, TypeError):
                nodes.append({
                    "id": node_id,
                    "type": "tool_call",
                    "title": "Tool Call",
                    "summary": content[:100],
                    "content": content,
                    "status": "malformed",
                })
        elif phase == "observation":
            nodes.append({
                "id": node_id,
                "type": "observation",
                "title": "Observation",
                "summary": content[:120] + ("..." if len(content) > 120 else ""),
                "content": content,
            })
        elif phase == "answer":
            nodes.append({
                "id": node_id,
                "type": "answer",
                "title": "Final Answer",
                "summary": content[:120] + ("..." if len(content) > 120 else ""),
                "content": content,
            })

    # If no steps parsed (base model), synthesize from transcript
    if not nodes and transcript:
        nodes = _nodes_from_raw_transcript(transcript)

    return nodes


def _nodes_from_raw_transcript(transcript: str) -> list[dict]:
    """Parse raw transcript text into nodes when steps are empty (base model)."""
    nodes = []
    ni = 0

    # Extract think blocks
    thinks = re.findall(r"<think>(.*?)</think>", transcript, re.DOTALL)
    for t in thinks:
        t = t.strip()
        if t:
            nodes.append({
                "id": f"n{ni}", "type": "think", "title": "Reasoning",
                "summary": t[:120], "content": t,
            })
            ni += 1

    # The rest is the raw output
    clean = re.sub(r"<think>.*?</think>", "", transcript, flags=re.DOTALL).strip()
    if clean:
        # Check if it looks like a JSON tool call attempt
        if clean.lstrip().startswith("{") or "tool" in clean.lower()[:50]:
            nodes.append({
                "id": f"n{ni}", "type": "failure_terminal",
                "title": "Malformed Output",
                "summary": "Model output raw JSON instead of using tool format",
                "content": clean[:500],
            })
        else:
            # Extract answer if present
            ans_match = re.search(r"<answer>(.*?)</answer>", clean, re.DOTALL)
            if ans_match:
                nodes.append({
                    "id": f"n{ni}", "type": "answer",
                    "title": "Final Answer",
                    "summary": ans_match.group(1).strip()[:120],
                    "content": ans_match.group(1).strip(),
                })
            else:
                nodes.append({
                    "id": f"n{ni}", "type": "failure_terminal",
                    "title": "Unstructured Output",
                    "summary": clean[:120],
                    "content": clean[:500],
                })

    if not nodes:
        nodes.append({
            "id": "n0", "type": "failure_terminal",
            "title": "No Output",
            "summary": "Model produced empty output",
            "content": "",
        })

    return nodes


def _extract_decision(text: str) -> str | None:
    """Try to extract a decision statement from think text."""
    for pattern in [r"I (?:should|need to|will) (.+?)(?:\.|$)", r"(?:Let me|Let's) (.+?)(?:\.|$)"]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return None


def is_correct(predicted: str, expected: str) -> bool:
    p, e = predicted.strip().lower(), expected.strip().lower()
    if p == e or e in p or p in e:
        return True
    try:
        return abs(float(re.sub(r"[^0-9.\-]", "", p)) - float(re.sub(r"[^0-9.\-]", "", e))) < 0.1 * max(abs(float(re.sub(r"[^0-9.\-]", "", e))), 1)
    except (ValueError, ZeroDivisionError):
        return False


def build_trace_entry(raw_trace: dict, ground_truth: str, expected_tools: list[str]) -> dict:
    """Build a single model trace for a task."""
    transcript = raw_trace.get("transcript", "")
    steps = raw_trace.get("steps", [])
    tool_calls = raw_trace.get("tool_calls", [])
    final_answer = str(raw_trace.get("final_answer", ""))

    nodes = parse_steps_to_nodes(steps, transcript)
    correct = is_correct(final_answer, ground_truth)

    # Determine restraint
    if not expected_tools:
        restraint = "strong" if len(tool_calls) == 0 else "none"
    else:
        restraint = "n/a"

    # Determine verdict
    if correct:
        verdict = "correct"
    elif tool_calls and any(n["type"] == "observation" for n in nodes):
        verdict = "partial"
    else:
        verdict = "fail"

    # Detect behaviors
    behaviors = []
    if not tool_calls and expected_tools:
        behaviors.append("no tool usage")
    if any('"tool"' in transcript[:200] and '"tool_params"' in transcript[:300] for _ in [1]):
        behaviors.append("raw json output")
    if not expected_tools and tool_calls:
        behaviors.append("over-tooling")
    if correct:
        behaviors.append("correct answer")
    if len(tool_calls) > len(expected_tools or [1]):
        behaviors.append("excess tool calls")

    return {
        "verdict": verdict,
        "correct": correct,
        "tool_calls_used": len(tool_calls),
        "optimal_tool_calls": len(expected_tools) if expected_tools else 0,
        "steps": len(nodes),
        "restraint": restraint,
        "recovery": "none",
        "behaviors_detected": behaviors[:4],
        "confidence": "high" if correct else "low",
        "evidence_count": len([n for n in nodes if n["type"] == "observation"]),
        "summary": _build_summary(verdict, tool_calls, expected_tools, final_answer),
        "raw_trace": transcript,
        "nodes": nodes,
    }


def _build_summary(verdict, tool_calls, expected_tools, final_answer) -> str:
    if verdict == "correct":
        if tool_calls:
            return f"Correctly used {len(tool_calls)} tool(s) to arrive at the answer"
        return "Answered correctly without using tools"
    if verdict == "partial":
        return f"Used tools but got incorrect answer: {final_answer[:60]}"
    if not tool_calls and expected_tools:
        return "Failed to use tools — output raw text instead of calling tools"
    return f"Incorrect result: {final_answer[:60]}"


def make_title(task_id: str, prompt: str) -> str:
    """Create a readable task title."""
    if len(prompt) <= 50:
        return prompt
    return prompt[:47] + "..."


def main():
    # Load all traces
    variants = {}
    for name, filename in [("base", "base.json"), ("sft", "sft.json"), ("grpo", "grpo-balanced.json")]:
        path = TRACES_DIR / filename
        if not path.exists():
            print(f"Missing {path}", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            raw = json.load(f)
        variants[name] = {t["task"]["id"]: t for t in raw}

    # Get all unique task IDs (in order from base)
    with open(TRACES_DIR / "base.json") as f:
        all_tasks_ordered = [t["task"] for t in json.load(f)]

    # Build showcase tasks — pick best 15 diverse tasks
    selected_ids = _select_showcase_tasks(all_tasks_ordered)

    tasks = []
    for task_meta in all_tasks_ordered:
        tid = task_meta["id"]
        if tid not in selected_ids:
            continue

        cat = task_meta.get("metadata", {}).get("category", "unknown")
        cat_meta = CATEGORY_META.get(cat, {"icon": "circle", "label": cat.title(), "difficulty": "Medium"})
        tier = task_meta.get("tier", "")

        traces = {}
        for model_key in ["base", "sft", "grpo"]:
            raw = variants[model_key].get(tid)
            if raw:
                traces[model_key] = build_trace_entry(
                    raw,
                    task_meta.get("ground_truth", ""),
                    task_meta.get("expected_tools", []),
                )

        tasks.append({
            "id": tid,
            "title": make_title(tid, task_meta["prompt"]),
            "category": cat_meta["label"],
            "difficulty": cat_meta["difficulty"],
            "tier": TIER_LABELS.get(tier, tier),
            "icon": cat_meta["icon"],
            "prompt": task_meta["prompt"],
            "ground_truth": task_meta.get("ground_truth", ""),
            "expected_tools": task_meta.get("expected_tools", []),
            "traces": traces,
        })

    showcase = {
        "version": "3.0",
        "models": [
            {"key": "base", "label": "BASE", "accent": "base",
             "description": "Raw Qwen 7B — no tool training. Outputs JSON blobs instead of calling tools."},
            {"key": "sft", "label": "SFT", "accent": "sft",
             "description": "Supervised fine-tuned — learns ReAct format, calls tools correctly, but over-tools."},
            {"key": "grpo", "label": "GRPO", "accent": "grpo",
             "description": "GRPO reward-tuned — maintains accuracy with improved tool selection."},
        ],
        "stats": _compute_stats(variants, selected_ids),
        "tasks": tasks,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(showcase, f, indent=2)
    print(f"Wrote {len(tasks)} tasks to {OUT}")


def _select_showcase_tasks(all_tasks: list[dict]) -> set[str]:
    """Pick ~15 diverse tasks across categories."""
    by_cat: dict[str, list[str]] = {}
    for t in all_tasks:
        cat = t.get("metadata", {}).get("category", "unknown")
        by_cat.setdefault(cat, []).append(t["id"])

    selected = set()
    # Take 2 from each category, prioritizing variety
    for cat, ids in sorted(by_cat.items()):
        for tid in ids[:2]:
            selected.add(tid)
            if len(selected) >= 16:
                break

    return selected


def _compute_stats(variants: dict, selected_ids: set[str]) -> dict:
    """Compute aggregate stats for the stats bar."""
    stats = {}
    for model_key, traces in variants.items():
        correct = 0
        tool_usage = 0
        restraint_ok = 0
        restraint_total = 0
        total = 0
        for tid in selected_ids:
            t = traces.get(tid)
            if not t:
                continue
            total += 1
            gt = t["task"].get("ground_truth", "")
            fa = str(t.get("final_answer", ""))
            et = t["task"].get("expected_tools", [])
            if is_correct(fa, gt):
                correct += 1
            if t.get("tool_calls"):
                tool_usage += 1
            if not et:
                restraint_total += 1
                if not t.get("tool_calls"):
                    restraint_ok += 1

        stats[model_key] = {
            "accuracy": round(correct / total * 100, 1) if total else 0,
            "tool_usage": round(tool_usage / total * 100, 1) if total else 0,
            "restraint": round(restraint_ok / restraint_total * 100, 1) if restraint_total else 0,
            "total": total,
        }
    return stats


if __name__ == "__main__":
    main()
