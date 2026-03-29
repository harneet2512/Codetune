"""GRPO training entrypoint for ToolTune reward variants.

Builds a dataset with full system prompts (including tool definitions),
then runs GRPO with the ToolTune reward function that scores correctness,
tool usage quality, restraint, planning, and error recovery.
"""

from __future__ import annotations

import argparse
import json
import logging

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import GRPOConfig, GRPOTrainer

from tooltune.contracts import TaskRecord
from tooltune.io import load_json
from tools.registry import ToolRegistry
from train.agentic_loop import build_system_prompt
from train.reward import reward_fn

logger = logging.getLogger(__name__)

VARIANT_CHOICES = ["grpo-exec", "grpo-toolheavy", "grpo-balanced"]

VARIANT_REWARD_OVERRIDES = {
    "grpo-exec": {"tool_bonus": False},
    "grpo-toolheavy": {"tool_bonus": True},
    "grpo-balanced": {"tool_bonus": True},
}


def _task_record_from_json(item: dict) -> TaskRecord:
    """Convert a raw JSON dict into a TaskRecord, filling defaults."""
    return TaskRecord(
        id=item.get("id", ""),
        tier=item.get("tier", ""),
        prompt=item["prompt"],
        ground_truth=item.get("ground_truth", ""),
        expected_tools=item.get("expected_tools", []),
        metadata=item.get("metadata", {}),
        error_injection_policy=item.get("error_injection_policy", {}),
    )


def build_dataset(task_files: list[str]) -> Dataset:
    """Load task JSON files and build an HF Dataset with full system prompts.

    Each row contains:
      - prompt: the full system prompt with tool definitions (used by GRPOTrainer
        as the generation input).
      - ground_truth: expected answer string (passed as kwarg to reward_fn).
      - expected_tools: list of tool names the task expects (passed as kwarg to
        reward_fn).
    """
    registry = ToolRegistry()
    raw_items: list[dict] = []
    for path in task_files:
        raw_items.extend(load_json(path))

    rows: list[dict] = []
    for item in raw_items:
        task = _task_record_from_json(item)
        prompt = build_system_prompt(task, registry)
        rows.append(
            {
                "prompt": prompt,
                "ground_truth": task.ground_truth,
                "expected_tools": json.dumps(task.expected_tools),
            }
        )

    dataset = Dataset.from_list(rows)
    logger.info(
        "Built dataset with %d rows. Columns: %s",
        len(dataset),
        dataset.column_names,
    )
    return dataset


def train(base_model: str, task_files: list[str], output_dir: str) -> None:
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        ),
        device_map="auto",
        trust_remote_code=True,
    )

    dataset = build_dataset(task_files)

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        reward_funcs=reward_fn,
        peft_config=LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ],
            bias="none",
            task_type="CAUSAL_LM",
        ),
        args=GRPOConfig(
            output_dir=output_dir,
            num_generations=2,
            generation_kwargs={
                "max_new_tokens": 768,
                "do_sample": True,
                "temperature": 0.8,
            },
            learning_rate=5e-6,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            num_train_epochs=1,
            fp16=True,
            beta=0.04,
            logging_steps=5,
            report_to="none",
        ),
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info("Model and tokenizer saved to %s", output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="ToolTune GRPO training")
    parser.add_argument(
        "--base-model",
        default="outputs/tooltune-sft-checkpoints/final_adapter",
        help="Base model or adapter path (default: SFT checkpoint)",
    )
    parser.add_argument(
        "--variant",
        choices=VARIANT_CHOICES,
        default="grpo-balanced",
        help="Reward variant (default: grpo-balanced)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: outputs/tooltune-{variant})",
    )
    parser.add_argument(
        "--task-files",
        nargs="+",
        default=[
            "tasks/tier1_single_tool.json",
            "tasks/tier2_restraint.json",
            "tasks/tier3_multi_step.json",
            "tasks/tier4_error_recovery.json",
        ],
    )
    args = parser.parse_args()

    # Derive output_dir from variant if not explicitly set.
    output_dir = args.output_dir or f"outputs/tooltune-{args.variant}"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger.info("Variant: %s  |  Output: %s", args.variant, output_dir)
    train(args.base_model, args.task_files, output_dir)


if __name__ == "__main__":
    main()
