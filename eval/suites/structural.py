"""GroundTruth structural verification eval suite.

Measures whether generated code uses real symbols, correct imports, and valid
references — beyond functional correctness. This is the unique eval signal
that ties CodeTune to the GroundTruth project.
"""

from __future__ import annotations

import importlib
import json
import logging
import tempfile
from pathlib import Path

import torch

logger = logging.getLogger(__name__)

# Coding problems that require importing/referencing real-world patterns
STRUCTURAL_PROBLEMS = [
    {
        "id": "struct_001",
        "prompt": "Write a Python function that reads a CSV file and returns a list of dictionaries using the csv module.",
        "expected_imports": ["csv"],
        "expected_symbols": ["csv.DictReader"],
    },
    {
        "id": "struct_002",
        "prompt": "Write a Python function that makes an HTTP GET request and returns the JSON response.",
        "expected_imports": ["requests"],
        "expected_symbols": ["requests.get"],
    },
    {
        "id": "struct_003",
        "prompt": "Write a Python function that creates a temporary directory, writes a file in it, reads it back, and cleans up.",
        "expected_imports": ["tempfile", "os"],
        "expected_symbols": ["tempfile.mkdtemp"],
    },
    {
        "id": "struct_004",
        "prompt": "Write a Python function that parses command-line arguments for a script that takes --input and --output file paths.",
        "expected_imports": ["argparse"],
        "expected_symbols": ["argparse.ArgumentParser"],
    },
    {
        "id": "struct_005",
        "prompt": "Write a Python function that walks a directory tree and returns all .py file paths.",
        "expected_imports": ["os", "pathlib"],
        "expected_symbols": [],
    },
    {
        "id": "struct_006",
        "prompt": "Write a Python async function that fetches multiple URLs concurrently using aiohttp.",
        "expected_imports": ["aiohttp", "asyncio"],
        "expected_symbols": ["aiohttp.ClientSession"],
    },
    {
        "id": "struct_007",
        "prompt": "Write a Python function that serializes a dataclass to JSON and deserializes it back.",
        "expected_imports": ["dataclasses", "json"],
        "expected_symbols": ["dataclasses.dataclass", "dataclasses.asdict"],
    },
    {
        "id": "struct_008",
        "prompt": "Write a Python function that validates an email address using a regex pattern.",
        "expected_imports": ["re"],
        "expected_symbols": ["re.compile", "re.match"],
    },
    {
        "id": "struct_009",
        "prompt": "Write a Python function that creates a SQLite database, inserts a row, and queries it.",
        "expected_imports": ["sqlite3"],
        "expected_symbols": ["sqlite3.connect"],
    },
    {
        "id": "struct_010",
        "prompt": "Write a Python function that spawns a subprocess, captures stdout, and returns it.",
        "expected_imports": ["subprocess"],
        "expected_symbols": ["subprocess.run"],
    },
    {
        "id": "struct_011",
        "prompt": "Write a Python function that compresses a string using gzip and returns the base64-encoded result.",
        "expected_imports": ["gzip", "base64"],
        "expected_symbols": ["gzip.compress", "base64.b64encode"],
    },
    {
        "id": "struct_012",
        "prompt": "Write a Python function that uses logging to log messages at different levels to a file.",
        "expected_imports": ["logging"],
        "expected_symbols": ["logging.getLogger", "logging.FileHandler"],
    },
    {
        "id": "struct_013",
        "prompt": "Write a Python function that uses collections.Counter to find the most common words in a text.",
        "expected_imports": ["collections"],
        "expected_symbols": ["collections.Counter"],
    },
    {
        "id": "struct_014",
        "prompt": "Write a Python function that calculates the SHA-256 hash of a file.",
        "expected_imports": ["hashlib"],
        "expected_symbols": ["hashlib.sha256"],
    },
    {
        "id": "struct_015",
        "prompt": "Write a Python function that uses datetime to parse a date string and calculate days between two dates.",
        "expected_imports": ["datetime"],
        "expected_symbols": ["datetime.datetime.strptime"],
    },
    {
        "id": "struct_016",
        "prompt": "Write a Python function that uses itertools to generate all combinations of a list.",
        "expected_imports": ["itertools"],
        "expected_symbols": ["itertools.combinations"],
    },
    {
        "id": "struct_017",
        "prompt": "Write a Python function that creates a thread pool and runs tasks in parallel.",
        "expected_imports": ["concurrent.futures"],
        "expected_symbols": ["concurrent.futures.ThreadPoolExecutor"],
    },
    {
        "id": "struct_018",
        "prompt": "Write a Python context manager that measures execution time of a code block.",
        "expected_imports": ["time", "contextlib"],
        "expected_symbols": [],
    },
    {
        "id": "struct_019",
        "prompt": "Write a Python function that uses functools.lru_cache to memoize a recursive fibonacci function.",
        "expected_imports": ["functools"],
        "expected_symbols": ["functools.lru_cache"],
    },
    {
        "id": "struct_020",
        "prompt": "Write a Python function that uses typing to define a generic stack data structure.",
        "expected_imports": ["typing"],
        "expected_symbols": ["typing.Generic", "typing.TypeVar"],
    },
]


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


def check_imports(code: str, expected_imports: list[str]) -> list[str]:
    """Check which expected imports are present in the generated code."""
    missing = []
    for imp in expected_imports:
        # Check various import patterns
        patterns = [
            f"import {imp}",
            f"from {imp} import",
            f"from {imp}.",
        ]
        if not any(p in code for p in patterns):
            missing.append(imp)
    return missing


def check_symbols(code: str, expected_symbols: list[str]) -> list[str]:
    """Check which expected symbols are referenced in the generated code."""
    missing = []
    for sym in expected_symbols:
        # Check for the symbol or its short form
        parts = sym.split(".")
        short_form = parts[-1]
        if sym not in code and short_form not in code:
            missing.append(sym)
    return missing


def check_hallucinated_imports(code: str) -> list[str]:
    """Detect imports of modules that don't exist in Python stdlib or common packages."""
    import ast

    hallucinated = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return hallucinated

    known_modules = {
        "os", "sys", "json", "csv", "re", "math", "random", "time", "datetime",
        "pathlib", "typing", "collections", "itertools", "functools", "hashlib",
        "base64", "gzip", "subprocess", "tempfile", "logging", "argparse",
        "sqlite3", "unittest", "dataclasses", "abc", "io", "string", "textwrap",
        "copy", "enum", "contextlib", "concurrent", "asyncio", "socket",
        "http", "urllib", "xml", "html", "email", "struct", "array",
        # Common third-party
        "requests", "aiohttp", "numpy", "pandas", "flask", "fastapi",
        "pydantic", "pytest", "rich", "click", "tqdm",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_module = alias.name.split(".")[0]
                if top_module not in known_modules:
                    try:
                        importlib.import_module(top_module)
                    except ImportError:
                        hallucinated.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top_module = node.module.split(".")[0]
                if top_module not in known_modules:
                    try:
                        importlib.import_module(top_module)
                    except ImportError:
                        hallucinated.append(node.module)

    return hallucinated


def try_gt_validation(code: str, gt_path: str | None) -> dict | None:
    """Attempt to use GroundTruth for structural validation if available."""
    if not gt_path:
        return None

    try:
        import sys
        gt_src = str(Path(gt_path) / "src")
        if gt_src not in sys.path:
            sys.path.insert(0, gt_src)

        from groundtruth.core.validator import Validator
        from groundtruth.core.store import SymbolStore

        # Create a temp scaffold and validate
        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "generated.py"
            code_file.write_text(code, encoding="utf-8")

            # Try to run GT validation
            store = SymbolStore(Path(tmpdir) / ".gt.db")
            validator = Validator(store)
            result = validator.validate_file(str(code_file))
            return {
                "gt_available": True,
                "errors": [str(e) for e in result.errors] if hasattr(result, "errors") else [],
                "valid": result.valid if hasattr(result, "valid") else True,
            }
    except Exception as e:
        logger.debug(f"GT validation unavailable: {e}")
        return None


def run(model, tokenizer, suite_config: dict | None = None, gen_config: dict | None = None) -> dict:
    """Run structural verification eval."""
    suite_config = suite_config or {}
    gen_config = gen_config or {}

    max_new_tokens = suite_config.get("max_new_tokens", gen_config.get("max_new_tokens", 512))
    temperature = suite_config.get("temperature", gen_config.get("temperature", 0.0))
    gt_path = suite_config.get("groundtruth_path")

    total = 0
    structural_pass = 0
    total_missing_imports = 0
    total_missing_symbols = 0
    total_hallucinated = 0
    total_issues = 0
    per_problem: list[dict] = []

    for problem in STRUCTURAL_PROBLEMS:
        instruction = (
            f"Write the requested Python code. Include all necessary imports. "
            f"Return ONLY the code, no explanation.\n\n{problem['prompt']}"
        )
        messages = [{"role": "user", "content": instruction}]
        chat_prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
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

        # Check structural properties
        missing_imports = check_imports(code, problem["expected_imports"])
        missing_symbols = check_symbols(code, problem["expected_symbols"])
        hallucinated = check_hallucinated_imports(code)

        issues = len(missing_imports) + len(missing_symbols) + len(hallucinated)
        is_pass = issues == 0

        # Try GT validation if available
        gt_result = try_gt_validation(code, gt_path)

        result = {
            "id": problem["id"],
            "passed": is_pass,
            "missing_imports": missing_imports,
            "missing_symbols": missing_symbols,
            "hallucinated_imports": hallucinated,
            "issue_count": issues,
            "completion_preview": code[:300],
        }
        if gt_result:
            result["groundtruth"] = gt_result

        per_problem.append(result)

        if is_pass:
            structural_pass += 1
        total_missing_imports += len(missing_imports)
        total_missing_symbols += len(missing_symbols)
        total_hallucinated += len(hallucinated)
        total_issues += issues
        total += 1

    structural_pass_rate = structural_pass / total if total > 0 else 0.0
    avg_issues = total_issues / total if total > 0 else 0.0

    return {
        "metrics": {
            "structural_pass_rate": round(structural_pass_rate, 4),
            "avg_issues_per_output": round(avg_issues, 4),
            "hallucinated_symbols": total_hallucinated,
            "missing_imports": total_missing_imports,
            "missing_symbols": total_missing_symbols,
            "total_evaluated": total,
        },
        "per_problem": per_problem,
    }
