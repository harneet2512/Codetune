"""Trace builder — parses raw model output into structured blocks."""

import json
import re


def parse_model_output(raw: str) -> list[dict]:
    """Parse raw model output with XML-like tags into segments.

    Expected format:
      <think>reasoning text</think>
      <tool_call>{"name": "tool.method", "args": {...}}</tool_call>
      <observation>tool result</observation>
      <answer>final answer</answer>
    """
    segments = []

    # Match all tagged segments
    pattern = r"<(think|tool_call|observation|answer)>(.*?)</\1>"
    matches = re.finditer(pattern, raw, re.DOTALL)

    for match in matches:
        tag = match.group(1)
        content = match.group(2).strip()

        if tag == "think":
            segments.append({"type": "think", "content": content})

        elif tag == "tool_call":
            try:
                call_data = json.loads(content)
                segments.append({
                    "type": "tool_call",
                    "content": content,
                    "tool_name": call_data.get("name", ""),
                    "tool_args": call_data.get("args", {}),
                })
            except json.JSONDecodeError:
                segments.append({
                    "type": "tool_call",
                    "content": content,
                    "tool_name": "unknown",
                    "tool_args": {},
                })

        elif tag == "observation":
            segments.append({"type": "result", "content": content})

        elif tag == "answer":
            segments.append({"type": "answer", "content": content})

    # If no tags found, treat entire output as a think segment
    if not segments and raw.strip():
        segments.append({"type": "think", "content": raw.strip()})

    return segments


def build_block(
    index: int,
    segment: dict,
    timestamp_ms: int = 0,
    parent_id: str | None = None,
) -> dict:
    """Convert a parsed segment into a block object for the frontend."""
    block_type = segment["type"]
    content = segment.get("content", "")

    # Generate title from content
    title = _extract_title(content, block_type)
    detail = content if len(content) > 60 else None

    block = {
        "id": f"live-{index}",
        "type": _map_type(block_type),
        "title": title,
        "detail": detail,
        "timestamp_ms": timestamp_ms,
    }

    if parent_id:
        block["parentId"] = parent_id

    # Add source tag for result blocks
    if block_type == "result":
        block["sourceTag"] = f"→ Step {index}"

    # Add tool info for tool_call blocks
    if block_type == "tool_call":
        tool_name = segment.get("tool_name", "")
        block["title"] = f"Call {tool_name}" if tool_name else title

    return block


def _map_type(segment_type: str) -> str:
    """Map parser segment types to frontend block types."""
    mapping = {
        "think": "think",
        "tool_call": "tool",
        "result": "result",
        "answer": "answer",
        "failed": "failed",
        "partial": "partial",
    }
    return mapping.get(segment_type, "think")


def _extract_title(content: str, block_type: str) -> str:
    """Extract a short title from block content."""
    # Take first sentence or first 60 chars
    first_line = content.split("\n")[0].strip()

    # For tool calls, try to extract the tool name
    if block_type == "tool_call":
        try:
            data = json.loads(content)
            return f"Call {data.get('name', 'tool')}"
        except json.JSONDecodeError:
            pass

    if len(first_line) <= 60:
        return first_line
    return first_line[:57] + "..."
