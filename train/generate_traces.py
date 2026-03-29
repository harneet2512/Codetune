"""Generate agentic traces for all model variants for evaluation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from tooltune.contracts import TaskRecord
from tooltune.io import dump_json, load_json
from tooltune.paths import CONFIGS_DIR, TASKS_DIR
from tools.registry import ToolRegistry
from train.agentic_loop import ModelTextGenerator, generate_agentic_completion

logger = logging.getLogger(__name__)


def load_tasks() -> list[TaskRecord]:
    tasks = []
    for tier_file in sorted(TASKS_DIR.glob("tier*.json")):
        for item in load_json(tier_file):
            tasks.append(TaskRecord(**item))
    return tasks


def load_model(model_path: str):
    """Load model + tokenizer. Handles both base models and LoRA adapters."""
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    # Check if this is a LoRA adapter directory (has adapter_config.json)
    adapter_config = Path(model_path) / "adapter_config.json"
    if adapter_config.exists():
        adapter_meta = load_json(adapter_config)
        base_model_name = adapter_meta.get("base_model_name_or_path", "Qwen/Qwen2.5-7B-Instruct")
        logger.info("Loading base model %s with adapter from %s", base_model_name, model_path)
        model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        model = PeftModel.from_pretrained(model, model_path)
    else:
        logger.info("Loading model from %s", model_path)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )

    model.eval()
    return model, tokenizer


def generate_traces_for_variant(
    model_path: str,
    variant_key: str,
    tasks: list[TaskRecord],
    output_dir: Path,
    max_steps: int = 5,
    temperature: float = 0.0,
) -> None:
    logger.info("Generating traces for variant '%s' (%d tasks)", variant_key, len(tasks))
    model, tokenizer = load_model(model_path)
    generator = ModelTextGenerator(model, tokenizer)
    registry = ToolRegistry()

    traces = []
    for i, task in enumerate(tasks):
        logger.info("[%s] Task %d/%d: %s", variant_key, i + 1, len(tasks), task.id)
        trace = generate_agentic_completion(
            generator=generator,
            task=task,
            registry=registry,
            max_steps=max_steps,
            temperature=temperature,
        )
        traces.append(trace.to_dict())

    output_path = output_dir / f"{variant_key}.json"
    dump_json(output_path, traces)
    logger.info("Saved %d traces to %s", len(traces), output_path)

    # Free GPU memory
    del model, tokenizer, generator
    torch.cuda.empty_cache()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate eval traces for ToolTune variants")
    parser.add_argument("--output-dir", default="results/traces")
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--max-tasks", type=int, default=0, help="Limit tasks per variant (0=all)")
    parser.add_argument("--variants", nargs="*", help="Specific variants to generate (default: all)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    variants_data = load_json(CONFIGS_DIR / "variants.json")
    variants = variants_data["variants"] if isinstance(variants_data, dict) else variants_data
    tasks = load_tasks()
    if args.max_tasks > 0:
        # Sample evenly across tiers
        import random
        random.seed(42)
        random.shuffle(tasks)
        tasks = tasks[: args.max_tasks]
    logger.info("Loaded %d tasks for evaluation", len(tasks))

    for variant in variants:
        key = variant["key"]
        if args.variants and key not in args.variants:
            continue
        model_path = variant["model_path"]
        if not Path(model_path).exists() and not model_path.startswith("Qwen/"):
            logger.warning("Skipping variant '%s': model path '%s' not found", key, model_path)
            continue
        generate_traces_for_variant(model_path, key, tasks, output_dir, max_steps=args.max_steps)


if __name__ == "__main__":
    main()
