"""Live mode endpoints — real inference with SSE streaming."""

import asyncio
import json
import time
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from inference.huggingface import call_model
from connectors.router import execute_tool
from traces.builder import parse_model_output, build_block

router = APIRouter(tags=["live"])


class LiveRunRequest(BaseModel):
    prompt: str
    model: str = "grpo"  # default to GRPO for live
    max_iterations: int = 8


@router.post("/run/live")
async def run_live(req: LiveRunRequest, request: Request):
    """Run live inference with real tool calls. Streams blocks via SSE."""

    async def event_generator():
        messages = [{"role": "user", "content": req.prompt}]
        tool_schemas = _get_tool_schemas()
        trace_start = time.time()
        block_index = 0

        for iteration in range(req.max_iterations):
            if await request.is_disconnected():
                break

            # Step 1: Call model
            t0 = time.time()
            try:
                response = await call_model(messages, tool_schemas)
            except Exception as e:
                yield {
                    "event": "block",
                    "data": json.dumps({
                        "id": f"err-{block_index}",
                        "type": "failed",
                        "title": "Inference error",
                        "detail": str(e),
                        "timestamp_ms": int((time.time() - trace_start) * 1000),
                    }),
                }
                yield {"event": "done", "data": json.dumps({"reason": "error"})}
                return

            inference_ms = int((time.time() - t0) * 1000)

            # Step 2: Parse model output into segments
            segments = parse_model_output(response["output"])

            for segment in segments:
                if await request.is_disconnected():
                    return

                block = build_block(
                    block_index,
                    segment,
                    timestamp_ms=int((time.time() - trace_start) * 1000),
                )
                block_index += 1

                # Send the block to the frontend
                yield {"event": "block", "data": json.dumps(block)}

                if segment["type"] == "tool_call":
                    # Step 3: Execute real tool call
                    tool_name = segment.get("tool_name", "")
                    tool_args = segment.get("tool_args", {})

                    try:
                        result = await execute_tool(tool_name, tool_args)
                    except Exception as e:
                        result = {"error": str(e)}

                    # Send result block
                    result_block = build_block(
                        block_index,
                        {"type": "result", "content": json.dumps(result, indent=2)},
                        timestamp_ms=int((time.time() - trace_start) * 1000),
                        parent_id=block["id"],
                    )
                    block_index += 1
                    yield {"event": "block", "data": json.dumps(result_block)}

                    # Feed result back into conversation
                    messages.append({"role": "assistant", "content": response["output"]})
                    messages.append({"role": "tool", "content": json.dumps(result)})

                elif segment["type"] == "answer":
                    # Done — model gave final answer
                    yield {
                        "event": "done",
                        "data": json.dumps({
                            "reason": "complete",
                            "total_blocks": block_index,
                            "total_ms": int((time.time() - trace_start) * 1000),
                            "inference_ms": inference_ms,
                        }),
                    }
                    return

                # Small delay between blocks for visual pacing
                await asyncio.sleep(0.1)

        # Hit max iterations
        yield {
            "event": "done",
            "data": json.dumps({"reason": "max_iterations", "total_blocks": block_index}),
        }

    return EventSourceResponse(event_generator())


def _get_tool_schemas() -> list[dict]:
    """Return tool schemas the model can call."""
    return [
        {
            "name": "github.search_repos",
            "description": "Search GitHub repositories by query",
            "parameters": {"query": {"type": "string"}, "language": {"type": "string"}},
        },
        {
            "name": "github.read_file",
            "description": "Read a file from a GitHub repository",
            "parameters": {"repo": {"type": "string"}, "path": {"type": "string"}},
        },
        {
            "name": "github.get_commit_history",
            "description": "Get recent commits for a repository",
            "parameters": {"repo": {"type": "string"}, "branch": {"type": "string"}},
        },
        {
            "name": "github.list_pull_requests",
            "description": "List pull requests for a repository",
            "parameters": {"repo": {"type": "string"}, "state": {"type": "string"}},
        },
        {
            "name": "github.create_issue",
            "description": "Create a GitHub issue",
            "parameters": {"repo": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}},
        },
        {
            "name": "gmail.search_emails",
            "description": "Search Gmail by query",
            "parameters": {"query": {"type": "string"}, "from": {"type": "string"}},
        },
        {
            "name": "gmail.read_email",
            "description": "Read a Gmail message by ID",
            "parameters": {"id": {"type": "string"}},
        },
        {
            "name": "drive.search_files",
            "description": "Search Google Drive files",
            "parameters": {"query": {"type": "string"}, "type": {"type": "string"}},
        },
        {
            "name": "drive.read_document",
            "description": "Read a Google Drive document",
            "parameters": {"file_id": {"type": "string"}},
        },
    ]
