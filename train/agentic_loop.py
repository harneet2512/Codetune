"""Agentic generation loop for ToolTune training and serving."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from tooltune.contracts import AgentPhase, SSEEvent, SSEEventType, TaskRecord, ToolCall, TraceStep
from tools.registry import ToolRegistry

THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)
TOOL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
ANSWER_RE = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
OBS_RE = re.compile(r"<observation>(.*?)</observation>", re.DOTALL)
STEP_RE = re.compile(r"<(think|tool_call|observation|answer)>(.*?)</\1>", re.DOTALL)


class TextGenerator(Protocol):
    def generate(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.0) -> str:
        ...


class ModelTextGenerator:
    """Wraps a HuggingFace model as a TextGenerator for the agentic loop."""

    def __init__(self, model, tokenizer, device="cuda"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    def generate(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.0) -> str:
        import torch
        inputs = self.tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        ).to(self.device)
        with torch.no_grad():
            ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=temperature > 0,
                temperature=max(temperature, 0.01),
                pad_token_id=self.tokenizer.pad_token_id,
            )
        new_tokens = ids[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True)


@dataclass(slots=True)
class AgenticTrace:
    task: TaskRecord
    prompt: str
    transcript: str
    steps: list[TraceStep]
    final_answer: str
    tool_calls: list[ToolCall]
    observations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task.to_dict(),
            "prompt": self.prompt,
            "transcript": self.transcript,
            "steps": [step.to_dict() for step in self.steps],
            "final_answer": self.final_answer,
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "observations": self.observations,
        }


def build_system_prompt(task: TaskRecord, registry: ToolRegistry) -> str:
    tools_json = json.dumps(registry.tool_definitions(), ensure_ascii=True, indent=2)
    return (
        "You are a helpful assistant with access to the following tools:\n\n"
        f"{tools_json}\n\n"
        "To use a tool, write a <tool_call> block with JSON. "
        "You will receive the result in an <observation> block.\n\n"
        "Think step by step inside <think></think> tags. "
        "When you have enough information, give your final answer inside <answer></answer> tags.\n"
        "If a tool returns an error, try a different approach.\n\n"
        f"User: {task.prompt}\n"
    )


def extract_tool_calls(trace: str) -> list[ToolCall]:
    tool_calls: list[ToolCall] = []
    for match in TOOL_RE.finditer(trace):
        raw = match.group(1)
        try:
            payload = json.loads(raw)
            tool_calls.append(
                ToolCall(
                    name=payload.get("name", "INVALID"),
                    arguments=payload.get("arguments", {}),
                    raw=raw,
                    valid=True,
                )
            )
        except json.JSONDecodeError:
            tool_calls.append(ToolCall(name="INVALID", arguments={}, raw=raw, valid=False, error="Malformed JSON"))
    return tool_calls


def extract_answer(trace: str) -> str:
    match = ANSWER_RE.search(trace)
    if match:
        return match.group(1).strip()
    return trace.strip()


def extract_think_blocks(trace: str) -> list[str]:
    return [block.strip() for block in THINK_RE.findall(trace)]


def extract_observations(trace: str) -> list[str]:
    return [block.strip() for block in OBS_RE.findall(trace)]


def steps_from_transcript(trace: str) -> list[TraceStep]:
    phase_map = {
        "think": AgentPhase.THINK,
        "tool_call": AgentPhase.TOOL_CALL,
        "observation": AgentPhase.OBSERVATION,
        "answer": AgentPhase.ANSWER,
    }
    steps: list[TraceStep] = []
    for index, match in enumerate(STEP_RE.finditer(trace)):
        phase_name, content = match.groups()
        steps.append(TraceStep(phase=phase_map[phase_name], content=content.strip(), index=index))
    return steps


def generate_agentic_completion(
    generator: TextGenerator,
    task: TaskRecord,
    registry: ToolRegistry,
    max_steps: int = 5,
    inject_errors: bool = False,
    error_probability: float = 0.2,
    temperature: float = 0.0,
) -> AgenticTrace:
    prompt = build_system_prompt(task, registry)
    conversation = prompt
    transcript_parts: list[str] = []

    for step_index in range(max_steps):
        output = generator.generate(conversation, max_new_tokens=256, temperature=temperature)
        transcript_parts.append(output)
        conversation += output

        if "<answer>" in output:
            break

        tool_calls = extract_tool_calls(output)
        if not tool_calls:
            break

        current = tool_calls[-1]
        observation = registry.execute(
            current,
            inject_errors=inject_errors or bool(task.error_injection_policy.get("enabled")),
            error_probability=task.error_injection_policy.get("probability", error_probability),
            random_seed=task.error_injection_policy.get("seed", step_index),
        )
        observation_block = f"\n<observation>\n{observation.content}\n</observation>\n"
        transcript_parts.append(observation_block)
        conversation += observation_block

    transcript = "".join(transcript_parts)
    return AgenticTrace(
        task=task,
        prompt=prompt,
        transcript=transcript,
        steps=steps_from_transcript(transcript),
        final_answer=extract_answer(transcript),
        tool_calls=extract_tool_calls(transcript),
        observations=extract_observations(transcript),
    )


def trace_to_sse_events(trace: AgenticTrace) -> list[SSEEvent]:
    events = [SSEEvent(type=SSEEventType.RUN_STARTED, data={"task_id": trace.task.id, "tier": trace.task.tier})]
    for step in trace.steps:
        events.append(SSEEvent(type=SSEEventType.PHASE_STARTED, data={"phase": step.phase.value, "index": step.index}))
        events.append(SSEEvent(type=SSEEventType.TOKEN, data={"phase": step.phase.value, "text": step.content}))
        if step.phase == AgentPhase.TOOL_CALL:
            events.append(SSEEvent(type=SSEEventType.TOOL_CALL, data={"raw": step.content, "index": step.index}))
        if step.phase == AgentPhase.OBSERVATION:
            events.append(SSEEvent(type=SSEEventType.OBSERVATION, data={"text": step.content, "index": step.index}))
    return events
