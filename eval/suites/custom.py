"""Custom coding quality evals: type hints, docstrings, error handling, Pythonic style."""

from __future__ import annotations

import ast
import json
import logging
from pathlib import Path

import torch

logger = logging.getLogger(__name__)


def generate_completion(
    model, tokenizer, prompt: str, max_new_tokens: int = 512, temperature: float = 0.0
) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            pad_token_id=tokenizer.pad_token_id,
        )
    generated = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(generated, skip_special_tokens=True)


# --- Checks ---

def check_contains_type_hints(code: str) -> bool:
    """Check if function parameters have type annotations."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if any arg (besides self) has annotation
                args = node.args
                annotated = sum(
                    1 for arg in args.args
                    if arg.annotation is not None and arg.arg != "self"
                )
                non_self_args = sum(1 for arg in args.args if arg.arg != "self")
                if non_self_args > 0 and annotated > 0:
                    return True
        return False
    except SyntaxError:
        return False


def check_has_return_type(code: str) -> bool:
    """Check if function has return type annotation."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.returns is not None:
                    return True
        return False
    except SyntaxError:
        return False


def check_has_docstring(code: str) -> bool:
    """Check if function has a docstring."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Constant, ast.Str))
                ):
                    return True
        return False
    except SyntaxError:
        return False


def check_handles_edge_cases(code: str) -> bool:
    """Check if code includes edge case handling (None checks, empty checks, ValueError)."""
    patterns = [
        "if not ", "if len(", "is None", "is not None",
        "ValueError", "TypeError", "IndexError",
        "if len(", "== 0", "== []", "== {}", '== ""',
    ]
    return any(p in code for p in patterns)


def check_no_bare_except(code: str) -> bool:
    """Check that code doesn't use bare except clauses."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    return False
        return True
    except SyntaxError:
        return True  # Can't parse = can't have bare except


def check_uses_list_comprehension(code: str) -> bool:
    """Check if code uses list comprehensions (Pythonic pattern)."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                return True
        return False
    except SyntaxError:
        return False


CHECK_FUNCTIONS = {
    "contains_type_hints": check_contains_type_hints,
    "has_return_type": check_has_return_type,
    "has_docstring": check_has_docstring,
    "handles_edge_cases": check_handles_edge_cases,
    "no_bare_except": check_no_bare_except,
    "uses_list_comprehension": check_uses_list_comprehension,
}

# Built-in test cases (used if no external test_cases dir)
BUILTIN_TEST_CASES = [
    {
        "id": "type_hints_001",
        "category": "type_hints",
        "prompt": "Write a function that merges two sorted lists into one sorted list.",
        "checks": ["contains_type_hints", "has_return_type", "has_docstring"],
    },
    {
        "id": "type_hints_002",
        "category": "type_hints",
        "prompt": "Write a function that finds all duplicates in a list of integers.",
        "checks": ["contains_type_hints", "has_return_type"],
    },
    {
        "id": "type_hints_003",
        "category": "type_hints",
        "prompt": "Write a function that converts a nested dictionary to a flat dictionary with dot-separated keys.",
        "checks": ["contains_type_hints", "has_return_type", "has_docstring"],
    },
    {
        "id": "docstring_001",
        "category": "docstrings",
        "prompt": "Write a function that implements binary search on a sorted list.",
        "checks": ["has_docstring", "contains_type_hints"],
    },
    {
        "id": "docstring_002",
        "category": "docstrings",
        "prompt": "Write a function that validates a credit card number using the Luhn algorithm.",
        "checks": ["has_docstring", "contains_type_hints", "has_return_type"],
    },
    {
        "id": "docstring_003",
        "category": "docstrings",
        "prompt": "Write a class that implements an LRU cache with get and put methods.",
        "checks": ["has_docstring"],
    },
    {
        "id": "error_001",
        "category": "error_handling",
        "prompt": "Write a function that reads a JSON file and returns the parsed contents, handling file not found and invalid JSON.",
        "checks": ["handles_edge_cases", "no_bare_except"],
    },
    {
        "id": "error_002",
        "category": "error_handling",
        "prompt": "Write a function that divides two numbers, handling division by zero and non-numeric inputs.",
        "checks": ["handles_edge_cases", "no_bare_except"],
    },
    {
        "id": "error_003",
        "category": "error_handling",
        "prompt": "Write a function that fetches a URL with retries and exponential backoff.",
        "checks": ["handles_edge_cases", "no_bare_except"],
    },
    {
        "id": "error_004",
        "category": "error_handling",
        "prompt": "Write a function that parses a date string in multiple formats and returns a datetime object.",
        "checks": ["handles_edge_cases", "no_bare_except", "has_docstring"],
    },
    {
        "id": "style_001",
        "category": "pythonic_style",
        "prompt": "Write a function that filters a list of strings to only those longer than n characters.",
        "checks": ["uses_list_comprehension", "contains_type_hints"],
    },
    {
        "id": "style_002",
        "category": "pythonic_style",
        "prompt": "Write a function that creates a dictionary mapping words to their frequencies in a text.",
        "checks": ["uses_list_comprehension", "contains_type_hints"],
    },
    {
        "id": "style_003",
        "category": "pythonic_style",
        "prompt": "Write a function that transposes a 2D matrix represented as a list of lists.",
        "checks": ["uses_list_comprehension", "contains_type_hints", "has_return_type"],
    },
    {
        "id": "style_004",
        "category": "pythonic_style",
        "prompt": "Write a function that extracts all unique email addresses from a text string.",
        "checks": ["uses_list_comprehension", "contains_type_hints", "has_docstring"],
    },
    {
        "id": "combined_001",
        "category": "combined",
        "prompt": "Write a function that reads a CSV file and returns rows where a specified column value exceeds a threshold.",
        "checks": ["contains_type_hints", "has_return_type", "has_docstring", "handles_edge_cases"],
    },
    {
        "id": "combined_002",
        "category": "combined",
        "prompt": "Write a function that recursively finds all files matching a glob pattern in a directory.",
        "checks": ["contains_type_hints", "has_return_type", "has_docstring"],
    },
    {
        "id": "combined_003",
        "category": "combined",
        "prompt": "Write a class that implements a thread-safe counter with increment, decrement, and get_value methods.",
        "checks": ["has_docstring", "contains_type_hints", "no_bare_except"],
    },
    {
        "id": "combined_004",
        "category": "combined",
        "prompt": "Write a function that batches an iterable into chunks of size n.",
        "checks": ["contains_type_hints", "has_return_type", "has_docstring", "uses_list_comprehension"],
    },
    {
        "id": "combined_005",
        "category": "combined",
        "prompt": "Write a decorator that caches function results with a TTL (time-to-live) expiration.",
        "checks": ["has_docstring", "contains_type_hints"],
    },
    {
        "id": "combined_006",
        "category": "combined",
        "prompt": "Write a function that compares two directory trees and returns the differences.",
        "checks": ["contains_type_hints", "has_return_type", "has_docstring", "handles_edge_cases"],
    },
]


def load_test_cases(test_cases_dir: str | None) -> list[dict]:
    """Load test cases from directory or fall back to built-in."""
    if test_cases_dir:
        dir_path = Path(test_cases_dir)
        if dir_path.exists():
            cases = []
            for f in sorted(dir_path.glob("*.json")):
                with open(f, encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        cases.extend(data)
                    else:
                        cases.append(data)
            if cases:
                logger.info(f"Loaded {len(cases)} test cases from {test_cases_dir}")
                return cases

    logger.info(f"Using {len(BUILTIN_TEST_CASES)} built-in test cases")
    return BUILTIN_TEST_CASES


def run(model, tokenizer, suite_config: dict | None = None, gen_config: dict | None = None) -> dict:
    """Run custom coding quality evals."""
    suite_config = suite_config or {}
    gen_config = gen_config or {}

    max_new_tokens = suite_config.get("max_new_tokens", gen_config.get("max_new_tokens", 512))
    temperature = suite_config.get("temperature", gen_config.get("temperature", 0.0))
    test_cases_dir = suite_config.get("test_cases_dir")

    test_cases = load_test_cases(test_cases_dir)

    total_checks = 0
    passed_checks = 0
    category_stats: dict[str, dict[str, int]] = {}
    per_problem: list[dict] = []

    for case in test_cases:
        instruction = (
            f"Write the requested Python code. Use type hints, docstrings, and proper error handling. "
            f"Return ONLY the code, no explanation.\n\n{case['prompt']}"
        )
        chat_prompt = (
            f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n"
            f"{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        )

        completion = generate_completion(model, tokenizer, chat_prompt, max_new_tokens, temperature)

        # Strip markdown fences
        code = completion.strip()
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        # Run checks
        check_results: dict[str, bool] = {}
        for check_name in case["checks"]:
            check_fn = CHECK_FUNCTIONS.get(check_name)
            if check_fn:
                result = check_fn(code)
                check_results[check_name] = result
                total_checks += 1
                if result:
                    passed_checks += 1

                # Track by category
                category = case.get("category", "unknown")
                if category not in category_stats:
                    category_stats[category] = {"total": 0, "passed": 0}
                category_stats[category]["total"] += 1
                if result:
                    category_stats[category]["passed"] += 1

        per_problem.append({
            "id": case["id"],
            "category": case.get("category", "unknown"),
            "checks": check_results,
            "all_passed": all(check_results.values()),
            "completion_preview": code[:300],
        })

    overall_score = passed_checks / total_checks if total_checks > 0 else 0.0
    by_category = {
        cat: round(s["passed"] / s["total"], 4) if s["total"] > 0 else 0.0
        for cat, s in category_stats.items()
    }

    return {
        "metrics": {
            "overall_score": round(overall_score, 4),
            "by_category": by_category,
            "total_checks_passed": passed_checks,
            "total_checks_run": total_checks,
        },
        "per_problem": per_problem,
    }
