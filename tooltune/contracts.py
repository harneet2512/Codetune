"""Stable data contracts shared across training, eval, and the playground."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class AgentPhase(str, Enum):
    THINK = "think"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    ANSWER = "answer"


class SSEEventType(str, Enum):
    RUN_STARTED = "run_started"
    TOKEN = "token"
    PHASE_STARTED = "phase_started"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    VERIFICATION = "verification"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    raw: str = ""
    valid: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ToolObservation:
    tool_name: str
    content: str
    is_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TraceStep:
    phase: AgentPhase
    content: str
    index: int
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["phase"] = self.phase.value
        return payload


@dataclass(slots=True)
class TaskRecord:
    id: str
    tier: str
    prompt: str
    ground_truth: str
    expected_tools: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    error_injection_policy: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VariantConfig:
    key: str
    label: str
    model_path: str
    mode: str = "live"
    endpoint: str | None = None
    reward_profile: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SSEEvent:
    type: SSEEventType
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type.value, "data": self.data}
