"""API routes for the ToolTune playground."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from playground.api.agent import AgentRunner
from playground.api.data import PlaygroundData
from playground.api.models import GenerateRequest, VerifyRequest

router = APIRouter()
runner = AgentRunner()
data = PlaygroundData()


@router.post("/generate")
async def generate(request: GenerateRequest):
    trace, mode = runner.run(request.task, request.model, request.inject_errors, request.demo_override)
    verification = runner.verify(trace)

    async def event_stream():
        for event in runner.sse_payload(trace, mode):
            if event["type"] == "verification":
                event["data"] = verification
            await asyncio.sleep(0.02)
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/verify")
def verify(request: VerifyRequest):
    trace = request.trace
    if "verification" in trace:
        return JSONResponse(trace["verification"])
    return JSONResponse({"correct": False, "reason": "Missing verification payload"}, status_code=400)


@router.get("/showcase")
def showcase():
    return {"examples": data.showcase, "variants": data.variants}


@router.get("/model-card")
def model_card():
    return data.load_model_card()


@router.get("/reward-lab/{experiment}")
def reward_lab(experiment: str):
    return data.load_reward_lab(experiment)


@router.get("/health")
def health():
    return {"mode": "demo"}

