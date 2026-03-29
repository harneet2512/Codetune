"""Tool schema registry and execution dispatcher."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any

from tooltune.contracts import ToolCall, ToolObservation

from . import calculator, code_executor, unit_converter, weather, wikipedia


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, dict[str, str]]

    def to_openai_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools = {
            "calculator": (
                ToolSpec(
                    name="calculator",
                    description="Evaluates a mathematical expression and returns the result.",
                    parameters={"expression": {"type": "string", "description": "Math expression"}},
                ),
                lambda arguments: calculator.run(arguments["expression"]),
            ),
            "wikipedia": (
                ToolSpec(
                    name="wikipedia",
                    description="Looks up a topic and returns a short factual summary.",
                    parameters={"query": {"type": "string", "description": "Topic to look up"}},
                ),
                lambda arguments: wikipedia.run(arguments["query"]),
            ),
            "weather": (
                ToolSpec(
                    name="weather",
                    description="Returns current weather for a city.",
                    parameters={"city": {"type": "string", "description": "City name"}},
                ),
                lambda arguments: weather.run(arguments["city"]),
            ),
            "code_executor": (
                ToolSpec(
                    name="code_executor",
                    description="Runs Python code and returns stdout/stderr.",
                    parameters={"code": {"type": "string", "description": "Python code to execute"}},
                ),
                lambda arguments: code_executor.run(arguments["code"]),
            ),
            "unit_converter": (
                ToolSpec(
                    name="unit_converter",
                    description="Converts a value from one unit to another.",
                    parameters={
                        "value": {"type": "number", "description": "Value to convert"},
                        "from_unit": {"type": "string", "description": "Source unit"},
                        "to_unit": {"type": "string", "description": "Target unit"},
                    },
                ),
                lambda arguments: unit_converter.run(
                    float(arguments["value"]),
                    arguments["from_unit"],
                    arguments["to_unit"],
                ),
            ),
        }

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [spec.to_openai_json() for spec, _ in self._tools.values()]

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def validate_call(self, tool_call: ToolCall) -> ToolCall:
        if tool_call.name not in self._tools:
            tool_call.valid = False
            tool_call.error = "Unknown tool"
            return tool_call

        spec, _ = self._tools[tool_call.name]
        for field_name in spec.parameters:
            if field_name not in tool_call.arguments:
                tool_call.valid = False
                tool_call.error = f"Missing required argument: {field_name}"
                return tool_call
        tool_call.valid = True
        return tool_call

    def execute(
        self,
        tool_call: ToolCall,
        inject_errors: bool = False,
        error_probability: float = 0.2,
        random_seed: int | None = None,
    ) -> ToolObservation:
        validated = self.validate_call(tool_call)
        if not validated.valid:
            return ToolObservation(
                tool_name=tool_call.name,
                content=json.dumps({"error": validated.error}),
                is_error=True,
            )

        rng = random.Random(random_seed)
        if inject_errors and rng.random() < error_probability:
            error_message = rng.choice(
                [
                    "Tool timed out after 5 seconds",
                    "No results found for query",
                    "Invalid expression: division by zero",
                    "Service temporarily unavailable",
                ]
            )
            return ToolObservation(
                tool_name=tool_call.name,
                content=json.dumps({"error": error_message}),
                is_error=True,
            )

        _, runner = self._tools[tool_call.name]
        content = runner(tool_call.arguments)
        is_error = "error" in content.lower()
        return ToolObservation(tool_name=tool_call.name, content=content, is_error=is_error)
