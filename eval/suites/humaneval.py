"""HumanEval pass@1 evaluation suite."""

from __future__ import annotations

import logging
import subprocess
import tempfile
import textwrap
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
    # Decode only the generated tokens (not the prompt)
    generated = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(generated, skip_special_tokens=True)


def extract_function_body(completion: str, entry_point: str) -> str:
    """Extract the function body from a completion, stopping at the next function or class."""
    lines = completion.split("\n")
    result_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Stop at next function/class definition (not nested)
        if result_lines and (stripped.startswith("def ") or stripped.startswith("class ")):
            if not line.startswith(" ") and not line.startswith("\t"):
                break
        result_lines.append(line)
    return "\n".join(result_lines)


def run_test_case(
    prompt: str, completion: str, test: str, entry_point: str, timeout: int = 10
) -> bool:
    """Run a single HumanEval test case in a subprocess."""
    # Build the full program: prompt (with signature) + completion + test
    program = prompt + completion + "\n\n" + test + f"\n\ncheck({entry_point})\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(program)
        f.flush()
        try:
            result = subprocess.run(
                ["python", f.name],
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
            problems_list = get_human_eval_plus()
            # evalplus returns a dict keyed by task_id
            problems = problems_list
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
        prompt = problem["prompt"]
        test = problem["test"]
        entry_point = problem["entry_point"]

        # Format as instruction for instruct model
        instruction = (
            f"Complete the following Python function. Return ONLY the function body, "
            f"no explanation.\n\n{prompt}"
        )
        chat_prompt = (
            f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n"
            f"{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        )

        completion = generate_completion(model, tokenizer, chat_prompt, max_new_tokens, temperature)
        completion = extract_function_body(completion, entry_point)

        success = run_test_case(prompt, completion, test, entry_point, timeout)

        per_problem.append({
            "task_id": task_id,
            "passed": success,
            "completion_preview": completion[:200],
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
