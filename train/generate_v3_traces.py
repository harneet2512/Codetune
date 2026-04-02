"""Generate SFT training traces for ToolTune v3 using mock connector tools.

For each task, an oracle (rule-based agent) makes optimal tool calls and
constructs the full training trace in the structured format:
  <think>...</think> <tool_call>...</tool_call> <observation>...</observation> <answer>...</answer>

The oracle knows the correct tool calls from the task metadata (expected_tools
+ step definitions), so no LLM inference is needed.

Usage::

    python -m train.generate_v3_traces
    python -m train.generate_v3_traces --output train/v3_traces.json
    python -m train.generate_v3_traces --validate-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tooltune.contracts import TaskRecord, ToolCall, ToolObservation, AgentPhase, TraceStep
from tooltune.io import dump_json, load_json
from tooltune.paths import TASKS_DIR
from tools.connectors.mock import MockConnectorRegistry
from tools.connectors.schemas import CONNECTOR_TOOL_SCHEMAS
from train.agentic_loop import AgenticTrace, steps_from_transcript, extract_tool_calls, extract_answer

# ---------------------------------------------------------------------------
# Oracle trace generator
# ---------------------------------------------------------------------------

_SCHEMA_BY_NAME = {s["name"]: s for s in CONNECTOR_TOOL_SCHEMAS}
_REGISTRY = MockConnectorRegistry()


def _generate_think_block(task: TaskRecord, step_index: int, total_steps: int) -> str:
    """Generate a realistic thinking block for the oracle."""
    if task.tier == "tier2_restraint":
        return (
            f"The user is asking: \"{task.prompt}\"\n"
            "This is a knowledge question I can answer directly from my training. "
            "I don't need to use any tools for this."
        )

    if task.tier == "tier4_error_recovery" and step_index == 1:
        return (
            "The previous tool call didn't return the expected results. "
            "Let me try a different approach — I'll broaden my search or try an alternative."
        )

    steps = task.metadata.get("steps", [])
    if step_index < len(steps):
        step = steps[step_index]
        tool_name = step["tool"]
        args = step.get("args", {})
        args_desc = ", ".join(f"{k}={v!r}" for k, v in args.items() if v)
        return (
            f"I need to use {tool_name} to help answer this question. "
            f"I'll call it with {args_desc}."
        )

    # Fallback for single-tool tasks
    if task.expected_tools:
        tool = task.expected_tools[min(step_index, len(task.expected_tools) - 1)]
        args = task.metadata.get("args", {})
        args_desc = ", ".join(f"{k}={v!r}" for k, v in args.items() if v)
        if step_index == 0:
            return (
                f"The user wants me to look something up. I'll use {tool}"
                + (f" with {args_desc}" if args_desc else "")
                + " to find the answer."
            )
        return f"Let me process the results and formulate my answer."

    return "Let me think about this carefully and provide a direct answer."


def _build_tool_call_json(tool_name: str, arguments: dict[str, Any]) -> str:
    """Build a clean tool call JSON payload."""
    return json.dumps({"name": tool_name, "arguments": arguments}, ensure_ascii=True)


def _generate_answer_block(task: TaskRecord, observations: list[str]) -> str:
    """Generate the final answer based on task ground truth and observations."""
    return task.ground_truth


def _validate_tool_args(tool_name: str, args: dict[str, Any]) -> list[str]:
    """Validate tool call arguments against the schema. Return error list."""
    errors = []
    schema = _SCHEMA_BY_NAME.get(tool_name)
    if schema is None:
        errors.append(f"Unknown tool: {tool_name}")
        return errors

    params = schema.get("parameters", {})
    for param_name, param_spec in params.items():
        if param_name not in args and "default" not in param_spec:
            # Only flag as error if it's truly required (no default)
            # For our schemas, most params without defaults are required
            if param_name in ("repo", "query", "file_id", "message_id", "to",
                              "subject", "body", "path", "branch_name",
                              "content", "message", "branch", "title",
                              "head_branch", "pr_number"):
                errors.append(f"Missing required arg '{param_name}' for {tool_name}")

    return errors


def generate_trace_for_task(task: TaskRecord) -> dict[str, Any]:
    """Generate a complete SFT training trace for a single task.

    Returns a dict with the trace data ready for JSON serialization.
    """
    transcript_parts: list[str] = []
    tool_calls_made: list[dict[str, Any]] = []
    observations: list[str] = []
    validation_errors: list[str] = []

    # --- Restraint tasks: answer directly ---
    if task.tier == "tier2_restraint" or not task.expected_tools:
        think = _generate_think_block(task, 0, 0)
        answer = _generate_answer_block(task, [])

        transcript_parts.append(f"<think>{think}</think>")
        transcript_parts.append(f"<answer>{answer}</answer>")

        transcript = "\n".join(transcript_parts)
        return {
            "task_id": task.id,
            "tier": task.tier,
            "prompt": task.prompt,
            "transcript": transcript,
            "steps": [
                {"phase": "think", "content": think, "index": 0},
                {"phase": "answer", "content": answer, "index": 1},
            ],
            "final_answer": answer,
            "tool_calls": [],
            "observations": [],
            "validation_errors": validation_errors,
        }

    # --- Tool-using tasks ---
    steps_spec = task.metadata.get("steps", [])
    step_index = 0

    if steps_spec:
        # Multi-step and error recovery: use explicit step definitions
        for i, step in enumerate(steps_spec):
            tool_name = step["tool"]
            args = dict(step.get("args", {}))

            # Think
            think = _generate_think_block(task, i, len(steps_spec))
            transcript_parts.append(f"<think>{think}</think>")

            # Validate
            errs = _validate_tool_args(tool_name, args)
            validation_errors.extend(errs)

            # Tool call
            tc_json = _build_tool_call_json(tool_name, args)
            transcript_parts.append(f"<tool_call>{tc_json}</tool_call>")
            tool_calls_made.append({"name": tool_name, "arguments": args})

            # Execute against mock
            tc = ToolCall(name=tool_name, arguments=args, raw=tc_json, valid=True)
            obs: ToolObservation = _REGISTRY.execute_tool_call(tc)
            observations.append(obs.content)
            transcript_parts.append(f"<observation>{obs.content}</observation>")

            step_index += 1
    else:
        # Single-tool tasks: use expected_tools + args from metadata
        tool_name = task.expected_tools[0]
        args = dict(task.metadata.get("args", {}))

        # Think
        think = _generate_think_block(task, 0, 1)
        transcript_parts.append(f"<think>{think}</think>")

        # Validate
        errs = _validate_tool_args(tool_name, args)
        validation_errors.extend(errs)

        # Tool call
        tc_json = _build_tool_call_json(tool_name, args)
        transcript_parts.append(f"<tool_call>{tc_json}</tool_call>")
        tool_calls_made.append({"name": tool_name, "arguments": args})

        # Execute
        tc = ToolCall(name=tool_name, arguments=args, raw=tc_json, valid=True)
        obs = _REGISTRY.execute_tool_call(tc)
        observations.append(obs.content)
        transcript_parts.append(f"<observation>{obs.content}</observation>")

    # Final answer
    think_final = "Now I have all the information I need to answer the user's question."
    transcript_parts.append(f"<think>{think_final}</think>")
    answer = _generate_answer_block(task, observations)
    transcript_parts.append(f"<answer>{answer}</answer>")

    transcript = "\n".join(transcript_parts)

    # Build step list
    steps: list[dict[str, Any]] = []
    idx = 0
    for part in transcript_parts:
        if part.startswith("<think>"):
            steps.append({"phase": "think", "content": part[7:-8], "index": idx})
        elif part.startswith("<tool_call>"):
            steps.append({"phase": "tool_call", "content": part[11:-12], "index": idx})
        elif part.startswith("<observation>"):
            steps.append({"phase": "observation", "content": part[13:-14], "index": idx})
        elif part.startswith("<answer>"):
            steps.append({"phase": "answer", "content": part[8:-9], "index": idx})
        idx += 1

    return {
        "task_id": task.id,
        "tier": task.tier,
        "prompt": task.prompt,
        "transcript": transcript,
        "steps": steps,
        "final_answer": answer,
        "tool_calls": tool_calls_made,
        "observations": observations,
        "validation_errors": validation_errors,
    }


def _load_tasks_from_json(path: Path) -> list[TaskRecord]:
    """Load TaskRecords from a JSON file."""
    raw = load_json(path)
    tasks = []
    for item in raw:
        tasks.append(TaskRecord(
            id=item["id"],
            tier=item["tier"],
            prompt=item["prompt"],
            ground_truth=item["ground_truth"],
            expected_tools=item["expected_tools"],
            metadata=item.get("metadata", {}),
            error_injection_policy=item.get("error_injection_policy", {}),
        ))
    return tasks


def validate_traces(traces: list[dict[str, Any]]) -> tuple[int, int, list[str]]:
    """Validate all generated traces. Returns (valid, invalid, error_messages)."""
    valid = 0
    invalid = 0
    errors: list[str] = []

    for trace in traces:
        task_id = trace["task_id"]
        trace_errors: list[str] = []

        # Check transcript is non-empty
        if not trace.get("transcript"):
            trace_errors.append(f"{task_id}: empty transcript")

        # Check final answer exists
        if not trace.get("final_answer"):
            trace_errors.append(f"{task_id}: missing final_answer")

        # Validate tool calls have valid JSON
        for tc in trace.get("tool_calls", []):
            if not tc.get("name"):
                trace_errors.append(f"{task_id}: tool call missing name")
            if not isinstance(tc.get("arguments", {}), dict):
                trace_errors.append(f"{task_id}: tool call arguments not a dict")

            # Check tool name is valid
            if tc.get("name") and tc["name"] not in _SCHEMA_BY_NAME:
                trace_errors.append(f"{task_id}: unknown tool '{tc['name']}'")

        # Validate tool call JSON in transcript
        transcript = trace.get("transcript", "")
        import re
        tc_matches = re.findall(r"<tool_call>(.*?)</tool_call>", transcript, re.DOTALL)
        for raw in tc_matches:
            try:
                payload = json.loads(raw.strip())
                if "name" not in payload:
                    trace_errors.append(f"{task_id}: tool_call JSON missing 'name'")
                if "arguments" not in payload:
                    trace_errors.append(f"{task_id}: tool_call JSON missing 'arguments'")
            except json.JSONDecodeError as e:
                trace_errors.append(f"{task_id}: malformed tool_call JSON: {e}")

        # Restraint checks
        if trace["tier"] == "tier2_restraint":
            if trace.get("tool_calls"):
                trace_errors.append(f"{task_id}: restraint task should have no tool calls")

        # Check for schema-level validation errors
        trace_errors.extend(trace.get("validation_errors", []))

        if trace_errors:
            invalid += 1
            errors.extend(trace_errors)
        else:
            valid += 1

    return valid, invalid, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SFT traces for ToolTune v3")
    parser.add_argument("--output", type=str, default="train/v3_traces.json",
                        help="Output path for traces (default: train/v3_traces.json)")
    parser.add_argument("--validate-only", action="store_true",
                        help="Only validate existing traces, don't regenerate")
    parser.add_argument("--tier", type=str, default=None,
                        help="Generate traces for a specific tier only (e.g., tier1, tier2)")
    args = parser.parse_args()

    output_path = ROOT / args.output

    if args.validate_only:
        if not output_path.exists():
            print(f"  ERROR: {output_path} does not exist")
            sys.exit(1)
        traces = load_json(output_path)
        valid, invalid, errors = validate_traces(traces)
        print(f"  Validation: {valid} valid, {invalid} invalid")
        if errors:
            for e in errors[:20]:
                print(f"    {e}")
            if len(errors) > 20:
                print(f"    ... and {len(errors) - 20} more errors")
        sys.exit(1 if invalid > 0 else 0)

    # Load task files
    tier_files = {
        "tier1": TASKS_DIR / "v3_tier1.json",
        "tier2": TASKS_DIR / "v3_tier2.json",
        "tier3": TASKS_DIR / "v3_tier3.json",
        "tier4": TASKS_DIR / "v3_tier4.json",
    }

    all_tasks: list[TaskRecord] = []
    for tier_name, path in tier_files.items():
        if args.tier and args.tier != tier_name:
            continue
        if not path.exists():
            print(f"  WARNING: {path} not found — run generate_v3_tasks.py first")
            continue
        tasks = _load_tasks_from_json(path)
        all_tasks.extend(tasks)
        print(f"  Loaded {len(tasks)} tasks from {path.name}")

    if not all_tasks:
        print("  ERROR: No tasks loaded. Run 'python -m tasks.generate_v3_tasks' first.")
        sys.exit(1)

    print(f"\n  Generating traces for {len(all_tasks)} tasks...")

    # Generate traces
    traces: list[dict[str, Any]] = []
    tier_counts: dict[str, int] = {}
    for task in all_tasks:
        trace = generate_trace_for_task(task)
        traces.append(trace)
        tier = task.tier
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    # Validate
    valid, invalid, errors = validate_traces(traces)
    print(f"\n  Validation: {valid} valid, {invalid} invalid out of {len(traces)} traces")
    if errors:
        print(f"  Validation errors ({len(errors)}):")
        for e in errors[:10]:
            print(f"    {e}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")

    # Save
    dump_json(output_path, traces)
    print(f"\n  Wrote {len(traces)} traces to {output_path}")

    # Summary
    print("\n  Summary by tier:")
    for tier, count in sorted(tier_counts.items()):
        print(f"    {tier}: {count} traces")

    restraint = tier_counts.get("tier2_restraint", 0)
    pct = restraint / len(traces) * 100 if traces else 0
    print(f"\n  Restraint ratio: {restraint}/{len(traces)} = {pct:.1f}%")
    if pct >= 30:
        print("  Restraint ratio meets >=30% requirement")
    else:
        print(f"  WARNING: Restraint below 30% ({pct:.1f}%)")

    # Tool call stats
    total_tc = sum(len(t["tool_calls"]) for t in traces)
    no_tool = sum(1 for t in traces if not t["tool_calls"])
    print(f"\n  Total tool calls across all traces: {total_tc}")
    print(f"  Traces with no tool calls (restraint): {no_tool}")

    tool_freq: dict[str, int] = {}
    for t in traces:
        for tc in t["tool_calls"]:
            name = tc["name"]
            tool_freq[name] = tool_freq.get(name, 0) + 1
    print("  Tool usage frequency:")
    for tool, count in sorted(tool_freq.items(), key=lambda x: -x[1]):
        print(f"    {tool}: {count}")


if __name__ == "__main__":
    main()
