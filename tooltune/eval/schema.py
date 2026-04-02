"""Pydantic v2 models for eval cases, traces, and results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Eval case definitions (loaded from YAML / JSON)
# ---------------------------------------------------------------------------


class ExpectedToolCall(BaseModel):
    """A single expected tool invocation with optional argument constraints."""

    name: str
    args_contains: dict[str, Any] = Field(default_factory=dict)


class EvalCase(BaseModel):
    """One evaluation case — a prompt plus ground-truth expectations."""

    id: str
    prompt: str
    category: str = "general"
    difficulty: str = "medium"
    expected_answer: str = ""
    expected_tools: list[ExpectedToolCall] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    max_tool_calls: int = 10
    tags: list[str] = Field(default_factory=list)
    weights: ScoreWeights | None = None

    model_config = {"extra": "ignore"}


class ScoreWeights(BaseModel):
    """Per-case weight overrides for the composite scorer."""

    tool_accuracy: float = 0.30
    restraint: float = 0.15
    answer: float = 0.30
    efficiency: float = 0.15
    ordering: float = 0.10


# Allow forward-ref resolution for EvalCase.weights
EvalCase.model_rebuild()


# ---------------------------------------------------------------------------
# Trace records (model outputs to evaluate)
# ---------------------------------------------------------------------------


class TraceToolCall(BaseModel):
    """A tool call recorded in a model trace."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class TraceRecord(BaseModel):
    """A single model trace to evaluate against an EvalCase."""

    id: str
    answer: str = ""
    tool_calls: list[TraceToolCall] = Field(default_factory=list)
    raw: str = ""

    model_config = {"extra": "ignore"}


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


class ScoreBreakdown(BaseModel):
    """Individual dimension scores for a single eval case."""

    tool_accuracy: float = 0.0
    restraint: float = 0.0
    answer: float = 0.0
    efficiency: float = 0.0
    ordering: float = 0.0
    composite: float = 0.0


class EvalResult(BaseModel):
    """Result of evaluating one trace against one eval case."""

    case_id: str
    category: str = "general"
    difficulty: str = "medium"
    tags: list[str] = Field(default_factory=list)
    passed: bool = False
    scores: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    failure_reasons: list[str] = Field(default_factory=list)


class AggregateScores(BaseModel):
    """Aggregate scores across a suite run."""

    mean_composite: float = 0.0
    mean_tool_accuracy: float = 0.0
    mean_restraint: float = 0.0
    mean_answer: float = 0.0
    mean_efficiency: float = 0.0
    mean_ordering: float = 0.0
    pass_rate: float = 0.0
    total: int = 0


class EvalSuiteResults(BaseModel):
    """Full results of running an eval suite against one set of traces."""

    suite_name: str = ""
    variant: str = ""
    results: list[EvalResult] = Field(default_factory=list)
    aggregate: AggregateScores = Field(default_factory=AggregateScores)


class ComparisonResults(BaseModel):
    """Results of comparing multiple variants on the same suite."""

    suite_name: str = ""
    variants: dict[str, EvalSuiteResults] = Field(default_factory=dict)
