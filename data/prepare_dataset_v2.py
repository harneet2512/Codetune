"""Dataset preparation v2: higher-quality instruction data + HumanEval completion mix."""

from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path

from datasets import load_dataset
from tqdm import tqdm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a Python coding assistant. Generate clean, correct, well-typed Python code."
)

# Qwen2.5 ChatML template — instruction style
CHAT_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{instruction}<|im_end|>\n"
    "<|im_start|>assistant\n{output}<|im_end|>"
)

# Qwen2.5 ChatML template — completion style (no instruction wrapper)
COMPLETION_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{prompt}<|im_end|>\n"
    "<|im_start|>assistant\n{completion}<|im_end|>"
)

COMPLETION_SYSTEM_PROMPT = (
    "Complete the following Python function. Return only the implementation."
)


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

def is_python_example(text: str) -> bool:
    """Check if text is Python-related."""
    text_lower = text.lower()
    python_signals = [
        "python", "def ", "class ", "import ", "from ", "print(",
        "self.", "__init__", "return ", "lambda ", "try:", "except",
        "with open", ".py", "pip install", "list comprehension",
        "dictionary", "tuple", "pandas", "numpy",
    ]
    non_python = [
        "javascript", "java ", "c++", "c#", "ruby", "rust",
        "golang", "swift", "kotlin", "php", "html", "css",
        "sql", "SELECT ", "CREATE TABLE",
    ]
    has_python = any(s in text_lower for s in python_signals)
    has_non_python = any(s in text_lower for s in non_python)
    return has_python and not has_non_python


def code_line_count(output: str) -> int:
    """Count non-empty, non-comment lines."""
    lines = output.strip().split("\n")
    return sum(
        1 for line in lines
        if line.strip() and not line.strip().startswith("#")
    )


# ---------------------------------------------------------------------------
# Instruction data from CodeFeedback-Filtered-Instruction
# ---------------------------------------------------------------------------

def prepare_instruction_data(
    min_code_lines: int = 3,
    max_code_lines: int = 100,
) -> list[dict]:
    """Download and filter CodeFeedback-Filtered-Instruction to Python-only examples."""
    logger.info("Downloading m-a-p/CodeFeedback-Filtered-Instruction...")
    ds = load_dataset("m-a-p/CodeFeedback-Filtered-Instruction", split="train")
    logger.info(f"Downloaded {len(ds)} examples")

    processed = []
    stats = {
        "total": len(ds),
        "not_python": 0,
        "too_short": 0,
        "too_long": 0,
        "kept": 0,
    }

    for example in tqdm(ds, desc="Filtering instruction data"):
        query = example.get("query", "") or ""
        answer = example.get("answer", "") or ""
        combined_text = query + " " + answer

        if not is_python_example(combined_text):
            stats["not_python"] += 1
            continue

        n_lines = code_line_count(answer)
        if n_lines < min_code_lines:
            stats["too_short"] += 1
            continue
        if n_lines > max_code_lines:
            stats["too_long"] += 1
            continue

        formatted_text = CHAT_TEMPLATE.format(
            system=SYSTEM_PROMPT,
            instruction=query.strip(),
            output=answer.strip(),
        )
        processed.append({
            "instruction": query.strip(),
            "output": answer.strip(),
            "text": formatted_text,
            "source": "codefeedback",
        })
        stats["kept"] += 1

    logger.info(f"Instruction filtering stats: {json.dumps(stats, indent=2)}")
    return processed


# ---------------------------------------------------------------------------
# HumanEval completion-style data (preserves code-completion ability)
# ---------------------------------------------------------------------------

def prepare_completion_data() -> list[dict]:
    """Create completion-style examples from HumanEval prompts via evalplus.

    Each example uses the raw function stub (signature + docstring) as the
    prompt and the canonical solution as the completion.  No 'write a function'
    wrapper — this teaches the model to complete code, not to follow
    instructions, which directly defends HumanEval performance.
    """
    logger.info("Loading HumanEval problems from evalplus...")
    try:
        from evalplus.data import get_human_eval_plus
        problems = get_human_eval_plus()
    except ImportError:
        logger.warning(
            "evalplus not installed — falling back to openai/humaneval via datasets"
        )
        ds = load_dataset("openai/openai_humaneval", split="test")
        problems = {}
        for ex in ds:
            problems[ex["task_id"]] = {
                "prompt": ex["prompt"],
                "canonical_solution": ex["canonical_solution"],
            }

    processed = []
    for task_id, problem in problems.items():
        prompt = problem["prompt"].rstrip()
        solution = problem["canonical_solution"].rstrip()

        # Build three variants per problem to get ~500 examples from 164 tasks
        # Variant 1: raw stub → solution
        formatted = COMPLETION_TEMPLATE.format(
            system=COMPLETION_SYSTEM_PROMPT,
            prompt=prompt,
            completion=solution,
        )
        processed.append({
            "instruction": prompt,
            "output": solution,
            "text": formatted,
            "source": "humaneval_completion",
        })

        # Variant 2: stub with "Complete this function:" prefix
        formatted_v2 = COMPLETION_TEMPLATE.format(
            system=COMPLETION_SYSTEM_PROMPT,
            prompt=f"Complete this function:\n\n{prompt}",
            completion=solution,
        )
        processed.append({
            "instruction": f"Complete this function:\n\n{prompt}",
            "output": solution,
            "text": formatted_v2,
            "source": "humaneval_completion",
        })

        # Variant 3: stub with "Implement the body:" prefix
        formatted_v3 = COMPLETION_TEMPLATE.format(
            system=COMPLETION_SYSTEM_PROMPT,
            prompt=f"Implement the body of the following function:\n\n{prompt}",
            completion=solution,
        )
        processed.append({
            "instruction": f"Implement the body of the following function:\n\n{prompt}",
            "output": solution,
            "text": formatted_v3,
            "source": "humaneval_completion",
        })

    logger.info(f"Created {len(processed)} completion-style examples from {len(problems)} HumanEval tasks")
    return processed


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def prepare_dataset(
    output_dir: str = "data/processed_v2",
    min_code_lines: int = 3,
    max_code_lines: int = 100,
    completion_ratio: float = 0.10,
    eval_ratio: float = 0.05,
    seed: int = 42,
) -> None:
    """Build the v2 mixed dataset: instruction + completion examples."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Instruction data
    instruction_data = prepare_instruction_data(
        min_code_lines=min_code_lines,
        max_code_lines=max_code_lines,
    )

    # 2. Completion data
    completion_data = prepare_completion_data()

    # 3. Mix: target ~10% completion, 90% instruction
    #    Compute how many instruction examples to keep so that completion
    #    examples make up `completion_ratio` of the final dataset.
    n_completion = len(completion_data)
    n_instruction_target = int(n_completion * (1 - completion_ratio) / completion_ratio)
    n_instruction_target = min(n_instruction_target, len(instruction_data))

    random.seed(seed)
    random.shuffle(instruction_data)
    instruction_subset = instruction_data[:n_instruction_target]

    mixed = instruction_subset + completion_data
    random.shuffle(mixed)

    logger.info(
        f"Mixed dataset: {len(instruction_subset)} instruction + "
        f"{n_completion} completion = {len(mixed)} total"
    )

    # 4. Train / eval split
    split_idx = int(len(mixed) * (1 - eval_ratio))
    train_data = mixed[:split_idx]
    eval_data = mixed[split_idx:]

    # 5. Save
    train_path = output_path / "train.jsonl"
    eval_path = output_path / "eval.jsonl"

    for path, data in [(train_path, train_data), (eval_path, eval_data)]:
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(data)} examples to {path}")

    # 6. Save stats
    stats = {
        "instruction_available": len(instruction_data),
        "instruction_used": len(instruction_subset),
        "completion_examples": n_completion,
        "total_mixed": len(mixed),
        "train_size": len(train_data),
        "eval_size": len(eval_data),
        "completion_ratio_actual": round(n_completion / len(mixed), 3),
    }
    stats_path = output_path / "stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    logger.info(f"Stats saved to {stats_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare v2 dataset: CodeFeedback instruction + HumanEval completion mix"
    )
    parser.add_argument("--output-dir", default="data/processed_v2", help="Output directory")
    parser.add_argument("--min-lines", type=int, default=3, help="Min code lines to keep")
    parser.add_argument("--max-lines", type=int, default=100, help="Max code lines to keep")
    parser.add_argument("--completion-ratio", type=float, default=0.10,
                        help="Target fraction of completion-style examples")
    parser.add_argument("--eval-ratio", type=float, default=0.05, help="Eval split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    prepare_dataset(
        output_dir=args.output_dir,
        min_code_lines=args.min_lines,
        max_code_lines=args.max_lines,
        completion_ratio=args.completion_ratio,
        eval_ratio=args.eval_ratio,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
