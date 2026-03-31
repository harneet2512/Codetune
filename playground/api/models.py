"""Typed API models for the ToolTune playground."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    task: str
    model: str = Field(default="grpo")
    inject_errors: bool = False
    demo_override: bool = True


class VerifyRequest(BaseModel):
    task: dict
    trace: dict
    model: str


class HealthResponse(BaseModel):
    mode: str
    version: str
