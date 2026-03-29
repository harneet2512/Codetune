"""Dataset preparation: download, filter, format, and split coding instruction data."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from datasets import load_dataset
from tqdm import tqdm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a Python coding assistant. Generate clean, correct, well-typed Python code."
)

# Qwen2.5 ChatML template
CHAT_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{instruction}<|im_end|>\n"
    "<|im_start|>assistant\n{output}<|im_end|>"
)


def is_python_example(example: dict) -> bool:
    """Check if an example is Python-related based on instruction and output."""
    text = (example.get("instruction", "") + " " + example.get("output", "")).lower()
    # Positive signals
    python_signals = [
        "python", "def ", "class ", "import ", "from ", "print(",
        "self.", "__init__", "return ", "lambda ", "try:", "except",
        "with open", ".py", "pip install", "list comprehension",
        "dictionary", "tuple", "pandas", "numpy",
    ]
    # Negative signals (other languages)
    non_python = [
        "javascript", "java ", "c++", "c#", "ruby", "rust",
        "golang", "swift", "kotlin", "php", "html", "css",
        "sql", "SELECT ", "CREATE TABLE",
    ]
    has_python = any(s in text for s in python_signals)
    has_non_python = any(s in text for s in non_python)
    return has_python and not has_non_python


def code_line_count(output: str) -> int:
    """Count non-empty, non-comment lines in output."""
    lines = output.strip().split("\n")
    return sum(
        1 for line in lines
        if line.strip() and not line.strip().startswith("#")
    )


def format_example(example: dict) -> dict:
    """Format a single example into chat template format."""
    instruction = example["instruction"].strip()
    if example.get("input", "").strip():
        instruction = f"{instruction}\n\nInput: {example['input'].strip()}"

    output = example["output"].strip()

    formatted_text = CHAT_TEMPLATE.format(
        system=SYSTEM_PROMPT,
        instruction=instruction,
        output=output,
    )

    return {
        "instruction": instruction,
        "output": output,
        "text": formatted_text,
    }


def prepare_dataset(
    output_dir: str = "data/processed",
    min_code_lines: int = 3,
    max_code_lines: int = 100,
    eval_ratio: float = 0.1,
    seed: int = 42,
) -> None:
    """Download, filter, format, and split the CodeAlpaca dataset."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Download
    logger.info("Downloading CodeAlpaca-20k...")
    ds = load_dataset("sahil2801/CodeAlpaca-20k", split="train")
    logger.info(f"Downloaded {len(ds)} examples")

    # Filter and format
    processed = []
    stats = {"total": len(ds), "not_python": 0, "too_short": 0, "too_long": 0, "kept": 0}

    for example in tqdm(ds, desc="Processing"):
        if not is_python_example(example):
            stats["not_python"] += 1
            continue

        n_lines = code_line_count(example.get("output", ""))
        if n_lines < min_code_lines:
            stats["too_short"] += 1
            continue
        if n_lines > max_code_lines:
            stats["too_long"] += 1
            continue

        formatted = format_example(example)
        processed.append(formatted)
        stats["kept"] += 1

    logger.info(f"Filtering stats: {json.dumps(stats, indent=2)}")

    # Shuffle and split
    import random
    random.seed(seed)
    random.shuffle(processed)

    split_idx = int(len(processed) * (1 - eval_ratio))
    train_data = processed[:split_idx]
    eval_data = processed[split_idx:]

    # Save
    train_path = output_path / "train.jsonl"
    eval_path = output_path / "eval.jsonl"

    for path, data in [(train_path, train_data), (eval_path, eval_data)]:
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(data)} examples to {path}")

    # Save stats
    stats_path = output_path / "stats.json"
    stats["train_size"] = len(train_data)
    stats["eval_size"] = len(eval_data)
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    logger.info(f"Stats saved to {stats_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare CodeAlpaca dataset for fine-tuning")
    parser.add_argument("--output-dir", default="data/processed", help="Output directory")
    parser.add_argument("--min-lines", type=int, default=3, help="Min code lines to keep")
    parser.add_argument("--max-lines", type=int, default=100, help="Max code lines to keep")
    parser.add_argument("--eval-ratio", type=float, default=0.1, help="Eval split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    prepare_dataset(
        output_dir=args.output_dir,
        min_code_lines=args.min_lines,
        max_code_lines=args.max_lines,
        eval_ratio=args.eval_ratio,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
