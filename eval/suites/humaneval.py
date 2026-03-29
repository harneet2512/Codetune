"""HumanEval pass@1 evaluation suite."""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

import torch

logger = logging.getLogger(__name__)


def generate_completion(
    model, tokenizer, prompt: str, max_new_tokens: int = 512, temperature: float = 0.0
) -> str:
    """Generate a code completion for a HumanEval prompt."""
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


def extract_code(completion: str) -> str:
    """Extract Python code from a completion, handling markdown fences and explanations."""
    # Strip markdown code fences
    code = completion.strip()
    if "```python" in code:
        match = re.search(r"```python\n(.*?)```", code, re.DOTALL)
        if match:
            code = match.group(1).strip()
    elif "```" in code:
        match = re.search(r"```\n?(.*?)```", code, re.DOTALL)
        if match:
            code = match.group(1).strip()

    # Stop at explanations (lines starting without indentation that aren't code)
    lines = code.split("\n")
    result: list[str] = []
    in_function = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            in_function = True
        if in_function and result and not line.startswith((" ", "\t", "def ", "class ", "@")):
            if stripped and not stripped.startswith(("#", "import ", "from ")):
                break
        result.append(line)
    return "\n".join(result)


def run_test_case(
    code: str, test: str, entry_point: str, timeout: int = 10
) -> bool:
    """Run a single HumanEval test case in a subprocess."""
    # The code should contain the full function; append test
    program = code + "\n\n" + test + f"\n\ncheck({entry_point})\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(program)
        f.flush()
        try:
            result = subprocess.run(
                ["python3", f.name],
                capture_output=True,
                timeout=timeout,
                text=True,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
            return False
        finally:
            Path(f.name).unlink(missing_ok=True)


def run(model, tokenizer, suite_config: dict | None = None, gen_config: dict | None = None) -> dict:
    """Run HumanEval evaluation."""
    suite_config = suite_config or {}
    gen_config = gen_config or {}

    max_new_tokens = suite_config.get("max_new_tokens", gen_config.get("max_new_tokens", 512))
    temperature = suite_config.get("temperature", gen_config.get("temperature", 0.0))
    timeout = suite_config.get("timeout_seconds", 10)

    # Load HumanEval problems
    try:
        from human_eval.data import read_problems
        problems = read_problems()
    except ImportError:
        try:
            from evalplus.data import get_human_eval_plus
            problems = get_human_eval_plus()
        except ImportError:
            logger.warning(
                "Neither human_eval nor evalplus installed. "
                "Install with: pip install evalplus"
            )
            return {
                "metrics": {"pass_at_1": 0.0, "error": "humaneval package not installed"},
                "per_problem": [],
            }

    passed = 0
    total = 0
    per_problem: list[dict] = []

    for task_id, problem in problems.items():
        prompt_stub = problem["prompt"]  # e.g. "def has_close_elements(..."
        test = problem["test"]
        entry_point = problem["entry_point"]

        # Ask the model to write the complete function
        instruction = (
            f"Write a Python function that solves the following problem. "
            f"Return ONLY the complete function, no explanation.\n\n{prompt_stub}"
        )
        messages = [{"role": "user", "content": instruction}]
        chat_prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        completion = generate_completion(model, tokenizer, chat_prompt, max_new_tokens, temperature)
        code = extract_code(completion)

        # If the model didn't include the function signature, prepend it
        if f"def {entry_point}" not in code:
            code = prompt_stub + "\n" + code

        success = run_test_case(code, test, entry_point, timeout)

        per_problem.append({
            "task_id": task_id,
            "passed": success,
            "completion_preview": code[:200],
        })

        if success:
            passed += 1
        total += 1

        if total % 20 == 0:
            logger.info(f"HumanEval progress: {total}/{len(problems)} ({passed}/{total} passed)")

    pass_at_1 = passed / total if total > 0 else 0.0

    return {
        "metrics": {
            "pass_at_1": round(pass_at_1, 4),
            "total_problems": total,
            "passed": passed,
            "failed": total - passed,
        },
        "per_problem": per_problem,
    }
