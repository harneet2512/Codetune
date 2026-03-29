"""MBPP (Mostly Basic Programming Problems) evaluation suite."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

import torch
from datasets import load_dataset

logger = logging.getLogger(__name__)


def generate_completion(
    model, tokenizer, prompt: str, max_new_tokens: int = 512, temperature: float = 0.0
) -> str:
    """Generate a code completion."""
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


def run_test(code: str, test_cases: list[str], timeout: int = 10) -> bool:
    """Run generated code against MBPP test assertions."""
    program = code + "\n\n" + "\n".join(test_cases)

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
    """Run MBPP evaluation."""
    suite_config = suite_config or {}
    gen_config = gen_config or {}

    max_new_tokens = suite_config.get("max_new_tokens", gen_config.get("max_new_tokens", 512))
    temperature = suite_config.get("temperature", gen_config.get("temperature", 0.0))
    timeout = suite_config.get("timeout_seconds", 10)
    subset = suite_config.get("subset", "sanitized")

    # Load MBPP dataset
    logger.info(f"Loading MBPP dataset (subset: {subset})...")
    if subset == "sanitized":
        ds = load_dataset("mbpp", "sanitized", split="test")
    else:
        ds = load_dataset("mbpp", split="test")

    passed = 0
    total = 0
    per_problem: list[dict] = []

    for example in ds:
        task_id = example["task_id"]
        text = example.get("text") or example.get("prompt", "")  # Schema varies
        test_list = example["test_list"]

        # Format as instruction
        instruction = (
            f"Write a Python function to solve the following problem. "
            f"Return ONLY the code, no explanation.\n\n{text}"
        )
        messages = [{"role": "user", "content": instruction}]
        chat_prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        completion = generate_completion(model, tokenizer, chat_prompt, max_new_tokens, temperature)

        # Extract code (strip markdown fences if present)
        code = completion.strip()
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        success = run_test(code, test_list, timeout)

        per_problem.append({
            "task_id": task_id,
            "passed": success,
            "completion_preview": code[:200],
        })

        if success:
            passed += 1
        total += 1

        if total % 50 == 0:
            logger.info(f"MBPP progress: {total}/{len(ds)} ({passed}/{total} passed)")

    pass_at_1 = passed / total if total > 0 else 0.0

    return {
        "metrics": {
            "pass_at_1": round(pass_at_1, 4),
            "total_problems": total,
            "passed": passed,
            "failed": total - passed,
            "subset": subset,
        },
        "per_problem": per_problem,
    }
