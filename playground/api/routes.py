"""API routes for the ToolTune playground."""

from __future__ import annotations

from fastapi import APIRouter
from playground.api.data import get_data

router = APIRouter()


@router.get("/tasks")
def tasks():
    data = get_data()
    return {"version": data.version, "models": data.models, "tasks": data.list_tasks()}


@router.get("/traces/{task_id}/{model}")
def trace(task_id: str, model: str):
    return get_data().get_trace(task_id, model)


@router.get("/stats")
def stats():
    return get_data().get_stats()


@router.get("/eval")
def eval_data():
    """Return full task data with embedded traces for the eval dashboard."""
    return get_data().get_eval_data()


@router.get("/health")
def health():
    data = get_data()
    return {"mode": "demo", "version": data.version, "tasks": len(data.tasks)}
