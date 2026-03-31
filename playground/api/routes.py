"""API routes for the ToolTune playground v2."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from playground.api.data import get_data
from playground.api.models import GenerateRequest, VerifyRequest

router = APIRouter()


@router.get("/tasks")
def tasks():
    data = get_data()
    return {"version": data.version, "models": data.models, "tasks": data.list_tasks()}


@router.get("/traces/{task_id}/{model}")
def trace(task_id: str, model: str):
    return get_data().get_trace(task_id, model)


@router.get("/showcase")
def showcase():
    return get_data().showcase_payload()


@router.get("/model-card")
def model_card():
    return get_data().load_model_card()


@router.get("/reward-lab/{experiment}")
def reward_lab(experiment: str):
    return get_data().load_reward_lab(experiment)


@router.post("/generate")
def generate(request: GenerateRequest):
    data = get_data()
    return JSONResponse(data.get_trace(request.task, request.model))


@router.post("/verify")
def verify(request: VerifyRequest):
    trace = request.trace or {}
    return {
        "correct": trace.get("correct", False),
        "verdict": trace.get("verdict", "fail"),
        "tool_calls_used": trace.get("tool_calls_used", 0),
        "steps": trace.get("steps", 0),
    }


@router.get("/health")
def health():
    data = get_data()
    return {"mode": "demo", "version": data.version}
