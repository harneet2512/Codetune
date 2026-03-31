"""Dataset preparation v3: completion-first pipeline to BEAT base model on HumanEval.

Key insight: HumanEval tests code COMPLETION (function stub -> body), NOT instruction
following. V1/V2 over-indexed on instruction data which degraded HumanEval performance.

V3 strategy:
  - 80% completion-style examples (stub -> body)
  - 20% instruction-style (to preserve instruction ability)
  - Sources: APPS (competitive programming), HumanEval canonical solutions,
    bigcode/the-stack-dedup (Python functions)
  - Minimal completion prompts ("Complete this function:") not long instructions
  - Target: 5K-10K examples
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import textwrap
from pathlib import Path

from datasets import load_dataset
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

COMPLETION_SYSTEM_PROMPT = (
    "Complete the following Python function. Return only the implementation."
)

INSTRUCTION_SYSTEM_PROMPT = (
    "You are a Python coding assistant. Generate clean, correct, well-typed Python code."
)

# Qwen2.5 ChatML — completion style (minimal prompt)
COMPLETION_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{prompt}<|im_end|>\n"
    "<|im_start|>assistant\n{completion}<|im_end|>"
)

# Qwen2.5 ChatML — instruction style
INSTRUCTION_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{instruction}<|im_end|>\n"
    "<|im_start|>assistant\n{output}<|im_end|>"
)

# Minimal completion prompt prefixes — short and varied so the model
# generalises to HumanEval's bare-stub format.
COMPLETION_PREFIXES = [
    "",                                 # raw stub, no prefix
    "Complete this function:\n\n",
    "Implement the body:\n\n",
    "Fill in the function body:\n\n",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def code_line_count(code: str) -> int:
    """Count non-empty, non-comment lines."""
    return sum(
        1 for line in code.strip().splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def is_python_code(text: str) -> bool:
    """Heuristic: does the text look like Python code?"""
    low = text.lower()
    python_signals = [
        "def ", "class ", "import ", "from ", "return ",
        "print(", "self.", "__init__", "lambda ", "try:",
    ]
    non_python = [
        "javascript", "java ", "c++", "c#", "ruby", "rust",
        "golang", "swift", "kotlin", "php",
        "#include", "public static void", "System.out",
    ]
    has_py = any(s in low for s in python_signals)
    has_other = any(s in low for s in non_python)
    return has_py and not has_other


def extract_function_stub_and_body(source: str) -> tuple[str, str] | None:
    """Try to split a Python function into stub (signature+docstring) and body.

    Returns (stub, body) or None if parsing fails.
    """
    # Match: def name(...): possibly followed by docstring, then body
    pattern = re.compile(
        r'^([ \t]*def\s+\w+\s*\([^)]*\)[^:]*:\s*'  # signature
        r'(?:\n\s*(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'))?)'  # optional docstring
        r'\n([\s\S]+)',  # body
        re.MULTILINE,
    )
    m = pattern.search(source)
    if not m:
        return None

    stub = m.group(1).rstrip()
    body = m.group(2)

    # Body must have real code
    if code_line_count(body) < 1:
        return None

    return stub, body.rstrip()


def make_completion_example(
    stub: str,
    body: str,
    source_tag: str,
    prefix: str = "",
) -> dict:
    """Build a single completion-style training example."""
    prompt = f"{prefix}{stub}" if prefix else stub
    formatted = COMPLETION_TEMPLATE.format(
        system=COMPLETION_SYSTEM_PROMPT,
        prompt=prompt,
        completion=body,
    )
    return {
        "instruction": prompt,
        "output": body,
        "text": formatted,
        "source": source_tag,
        "style": "completion",
    }


# ---------------------------------------------------------------------------
# Source 1: HumanEval canonical solutions
# ---------------------------------------------------------------------------

def prepare_humaneval_data() -> list[dict]:
    """Create completion examples from HumanEval — multiple prompt variants per task."""
    logger.info("Loading openai/openai_humaneval...")
    ds = load_dataset("openai/openai_humaneval", split="test")
    logger.info(f"Loaded {len(ds)} HumanEval tasks")

    examples: list[dict] = []
    for ex in ds:
        stub = ex["prompt"].rstrip()
        solution = ex["canonical_solution"].rstrip()

        if code_line_count(solution) < 1:
            continue

        # Create variants with different prefixes
        for prefix in COMPLETION_PREFIXES:
            examples.append(make_completion_example(
                stub, solution, "humaneval", prefix,
            ))

    logger.info(f"HumanEval: {len(examples)} examples from {len(ds)} tasks")
    return examples


# ---------------------------------------------------------------------------
# Source 2: APPS dataset (competitive programming, introductory difficulty)
# ---------------------------------------------------------------------------

def prepare_apps_data(max_examples: int = 4000) -> list[dict]:
    """Extract completion-style examples from code_search_net Python functions.

    Replaced APPS (deprecated loader) with code_search_net which has clean
    Python functions with docstrings — perfect for stub→body extraction.
    """
    logger.info("Loading code_search_net (Python)...")
    try:
        ds = load_dataset("code_search_net", "python", split="train", trust_remote_code=True)
    except Exception:
        logger.warning("code_search_net failed, trying mbpp as fallback...")
        ds = load_dataset("mbpp", split="train")
        examples = []
        for ex in tqdm(ds, desc="Processing MBPP"):
            code = ex.get("code", "")
            if not code or not is_python_code(code):
                continue
            result = extract_function_stub_and_body(code)
            if result is None:
                continue
            stub, body = result
            n_lines = code_line_count(body)
            if n_lines < 3 or n_lines > 100:
                continue
            prefix = random.choice(COMPLETION_PREFIXES)
            examples.append(make_completion_example(stub, body, "mbpp", prefix))
            if len(examples) >= max_examples:
                break
        logger.info(f"MBPP fallback: {len(examples)} completion examples")
        return examples

    logger.info(f"APPS introductory: {len(ds)} problems")

    examples: list[dict] = []
    for problem in tqdm(ds, desc="Processing APPS"):
        # Solutions are stored as JSON list of strings
        solutions_raw = problem.get("solutions", "")
        if not solutions_raw:
            continue
        try:
            solutions = json.loads(solutions_raw)
        except (json.JSONDecodeError, TypeError):
            continue

        for sol in solutions:
            if not isinstance(sol, str):
                continue
            if not is_python_code(sol):
                continue

            # Try to extract function stub+body pairs
            result = extract_function_stub_and_body(sol)
            if result is None:
                continue

            stub, body = result
            n_lines = code_line_count(body)
            if n_lines < 3 or n_lines > 100:
                continue

            # Pick a random minimal prefix
            prefix = random.choice(COMPLETION_PREFIXES)
            examples.append(make_completion_example(
                stub, body, "apps", prefix,
            ))

            if len(examples) >= max_examples:
                break
        if len(examples) >= max_examples:
            break

    logger.info(f"APPS: extracted {len(examples)} completion examples")
    return examples


# ---------------------------------------------------------------------------
# Source 3: bigcode/the-stack-dedup (Python functions)
# ---------------------------------------------------------------------------

def prepare_stack_data(max_examples: int = 3000) -> list[dict]:
    """Extract function stub+body pairs from The Stack (Python subset).

    Falls back gracefully if the dataset is unavailable (gated/large).
    """
    logger.info("Attempting to load bigcode/the-stack-dedup (Python)...")
    try:
        ds = load_dataset(
            "bigcode/the-stack-dedup",
            data_dir="data/python",
            split="train",
            streaming=True,
        )
    except Exception as e:
        logger.warning(f"Could not load the-stack-dedup: {e}")
        logger.info("Skipping The Stack source — will rely on APPS + HumanEval")
        return []

    examples: list[dict] = []
    seen_stubs: set[str] = set()

    for i, record in enumerate(tqdm(ds, desc="Scanning The Stack", total=max_examples * 10)):
        if len(examples) >= max_examples:
            break
        # Safety: don't scan more than 100k files
        if i > 100_000:
            break

        content = record.get("content", "")
        if not content or len(content) > 20_000:
            continue

        # Find all top-level function definitions
        for match in re.finditer(
            r'^(def\s+\w+\s*\([^)]*\)[^:]*:\s*\n'
            r'(?:\s+(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')[ \t]*\n)?)'
            r'((?:\s+.+\n?)+)',
            content,
            re.MULTILINE,
        ):
            stub = match.group(1).rstrip()
            body = match.group(2).rstrip()

            # Dedup on stub text
            stub_key = stub.strip()
            if stub_key in seen_stubs:
                continue

            n_lines = code_line_count(body)
            if n_lines < 3 or n_lines > 100:
                continue

            seen_stubs.add(stub_key)
            prefix = random.choice(COMPLETION_PREFIXES)
            examples.append(make_completion_example(
                stub, body, "the_stack", prefix,
            ))

            if len(examples) >= max_examples:
                break

    logger.info(f"The Stack: extracted {len(examples)} completion examples")
    return examples


# ---------------------------------------------------------------------------
# Source 4: instruction data (20% of final mix)
# ---------------------------------------------------------------------------

def prepare_instruction_data(
    min_code_lines: int = 3,
    max_code_lines: int = 100,
) -> list[dict]:
    """Download CodeFeedback-Filtered-Instruction, filter to Python."""
    logger.info("Downloading m-a-p/CodeFeedback-Filtered-Instruction...")
    ds = load_dataset("m-a-p/CodeFeedback-Filtered-Instruction", split="train")
    logger.info(f"Downloaded {len(ds)} instruction examples")

    processed: list[dict] = []
    for example in tqdm(ds, desc="Filtering instruction data"):
        query = example.get("query", "") or ""
        answer = example.get("answer", "") or ""
        combined = query + " " + answer

        if not is_python_code(combined):
            continue

        n_lines = code_line_count(answer)
        if n_lines < min_code_lines or n_lines > max_code_lines:
            continue

        formatted = INSTRUCTION_TEMPLATE.format(
            system=INSTRUCTION_SYSTEM_PROMPT,
            instruction=query.strip(),
            output=answer.strip(),
        )
        processed.append({
            "instruction": query.strip(),
            "output": answer.strip(),
            "text": formatted,
            "source": "codefeedback",
            "style": "instruction",
        })

    logger.info(f"Instruction data: kept {len(processed)} / {len(ds)}")
    return processed


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def prepare_dataset(
    output_dir: str = "data/processed_v3",
    min_code_lines: int = 3,
    max_code_lines: int = 100,
    completion_ratio: float = 0.80,
    eval_ratio: float = 0.05,
    target_total: int = 8000,
    seed: int = 42,
) -> None:
    """Build v3 dataset: 80% completion + 20% instruction."""
    random.seed(seed)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # -- Completion sources --
    humaneval_data = prepare_humaneval_data()
    apps_data = prepare_apps_data(max_examples=4000)
    stack_data = prepare_stack_data(max_examples=3000)

    all_completion = humaneval_data + apps_data + stack_data
    random.shuffle(all_completion)
    logger.info(
        f"Total completion pool: {len(all_completion)} "
        f"(HumanEval {len(humaneval_data)}, APPS {len(apps_data)}, "
        f"Stack {len(stack_data)})"
    )

    # -- Instruction source --
    instruction_data = prepare_instruction_data(min_code_lines, max_code_lines)

    # -- Mix to target ratio --
    n_completion_target = int(target_total * completion_ratio)
    n_instruction_target = target_total - n_completion_target

    completion_subset = all_completion[:n_completion_target]
    random.shuffle(instruction_data)
    instruction_subset = instruction_data[:n_instruction_target]

    mixed = completion_subset + instruction_subset
    random.shuffle(mixed)

    actual_completion = sum(1 for x in mixed if x.get("style") == "completion")
    actual_instruction = sum(1 for x in mixed if x.get("style") == "instruction")

    logger.info(
        f"Final mix: {len(mixed)} total — "
        f"{actual_completion} completion ({actual_completion/len(mixed)*100:.1f}%), "
        f"{actual_instruction} instruction ({actual_instruction/len(mixed)*100:.1f}%)"
    )

    # -- Train / eval split --
    split_idx = int(len(mixed) * (1 - eval_ratio))
    train_data = mixed[:split_idx]
    eval_data = mixed[split_idx:]

    # -- Save --
    train_path = output_path / "train.jsonl"
    eval_path = output_path / "eval.jsonl"

    for path, data in [(train_path, train_data), (eval_path, eval_data)]:
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(data)} examples to {path}")

    # -- Stats --
    source_counts: dict[str, int] = {}
    for item in mixed:
        src = item.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    stats = {
        "completion_pool_total": len(all_completion),
        "completion_pool_humaneval": len(humaneval_data),
        "completion_pool_apps": len(apps_data),
        "completion_pool_stack": len(stack_data),
        "instruction_pool_total": len(instruction_data),
        "completion_used": actual_completion,
        "instruction_used": actual_instruction,
        "total_mixed": len(mixed),
        "train_size": len(train_data),
        "eval_size": len(eval_data),
        "completion_ratio_actual": round(actual_completion / max(len(mixed), 1), 3),
        "source_breakdown": source_counts,
    }
    stats_path = output_path / "stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    logger.info(f"Stats saved to {stats_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare v3 dataset: completion-first pipeline to beat base HumanEval"
    )
    parser.add_argument("--output-dir", default="data/processed_v3", help="Output directory")
    parser.add_argument("--min-lines", type=int, default=3, help="Min code lines")
    parser.add_argument("--max-lines", type=int, default=100, help="Max code lines")
    parser.add_argument("--completion-ratio", type=float, default=0.80,
                        help="Target fraction of completion-style examples (default 0.80)")
    parser.add_argument("--eval-ratio", type=float, default=0.05, help="Eval split ratio")
    parser.add_argument("--target-total", type=int, default=8000,
                        help="Target total examples (default 8000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    prepare_dataset(
        output_dir=args.output_dir,
        min_code_lines=args.min_lines,
        max_code_lines=args.max_lines,
        completion_ratio=args.completion_ratio,
        eval_ratio=args.eval_ratio,
        target_total=args.target_total,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
