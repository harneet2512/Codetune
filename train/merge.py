"""Merge LoRA adapter into base model and export the full merged model."""

from __future__ import annotations

import argparse
import logging

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)


def merge_adapter(
    base_model: str = "meta-llama/Llama-3.1-8B-Instruct",
    adapter_path: str = "outputs/checkpoints/final_adapter",
    output_path: str = "outputs/codetune-8b",
    dtype: str = "bfloat16",
) -> None:
    """Load base model + LoRA adapter, merge weights, and save the full model."""
    torch_dtype = getattr(torch, dtype)

    logger.info(f"Loading base model: {base_model} ({dtype})")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch_dtype,
        device_map="auto",
        trust_remote_code=True,
    )

    logger.info(f"Loading adapter from: {adapter_path}")
    model = PeftModel.from_pretrained(model, adapter_path)

    logger.info("Merging adapter into base model...")
    model = model.merge_and_unload()

    logger.info(f"Saving merged model to: {output_path}")
    model.save_pretrained(output_path, safe_serialization=True)

    tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    tokenizer.save_pretrained(output_path)

    # Verify the merged model loads and generates
    logger.info("Verifying merged model...")
    del model
    torch.cuda.empty_cache()

    model = AutoModelForCausalLM.from_pretrained(
        output_path,
        torch_dtype=torch_dtype,
        device_map="auto",
    )
    tokenizer = AutoTokenizer.from_pretrained(output_path)

    test_prompt = "Write a Python function that reverses a string."
    inputs = tokenizer(test_prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=100, temperature=0.0, do_sample=False)
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    logger.info(f"Verification output:\n{result[:200]}")
    logger.info("Merge complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge LoRA adapter into base model")
    parser.add_argument(
        "--base-model",
        default="meta-llama/Llama-3.1-8B-Instruct",
        help="Base model name or path",
    )
    parser.add_argument(
        "--adapter-path",
        default="outputs/checkpoints/final_adapter",
        help="Path to LoRA adapter",
    )
    parser.add_argument(
        "--output-path",
        default="outputs/codetune-8b",
        help="Output path for merged model",
    )
    parser.add_argument("--dtype", default="bfloat16", choices=["bfloat16", "float16"])
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    merge_adapter(args.base_model, args.adapter_path, args.output_path, args.dtype)


if __name__ == "__main__":
    main()
