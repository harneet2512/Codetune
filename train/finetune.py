"""QLoRA fine-tuning of Llama 3.1 8B on coding data using SFTTrainer."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import torch
import yaml
from datasets import load_dataset
from peft import LoraConfig, TaskType, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def create_bnb_config(config: dict) -> BitsAndBytesConfig:
    compute_dtype = getattr(torch, config.get("bnb_4bit_compute_dtype", "bfloat16"))
    return BitsAndBytesConfig(
        load_in_4bit=config.get("load_in_4bit", True),
        bnb_4bit_quant_type=config.get("bnb_4bit_quant_type", "nf4"),
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=config.get("bnb_4bit_use_double_quant", True),
    )


def create_lora_config(config: dict) -> LoraConfig:
    return LoraConfig(
        r=config.get("lora_r", 16),
        lora_alpha=config.get("lora_alpha", 32),
        lora_dropout=config.get("lora_dropout", 0.05),
        target_modules=config.get("lora_target_modules", ["q_proj", "k_proj", "v_proj", "o_proj"]),
        bias=config.get("bias", "none"),
        task_type=TaskType.CAUSAL_LM,
    )


def print_trainable_params(model: AutoModelForCausalLM) -> None:
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    pct = 100 * trainable / total
    logger.info(f"Trainable params: {trainable:,} / {total:,} ({pct:.2f}%)")


def finetune(config_path: str = "configs/train_config.yaml") -> None:
    config = load_config(config_path)
    base_model = config["base_model"]
    output_dir = config.get("output_dir", "outputs/checkpoints")

    logger.info(f"Loading model: {base_model}")

    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # Model with 4-bit quantization
    bnb_config = create_bnb_config(config)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model)

    # LoRA
    lora_config = create_lora_config(config)
    print_trainable_params(model)

    # Dataset
    dataset_path = config.get("dataset_path", "data/processed")
    train_path = str(Path(dataset_path) / config.get("train_file", "train.jsonl"))
    eval_path = str(Path(dataset_path) / config.get("eval_file", "eval.jsonl"))

    train_ds = load_dataset("json", data_files=train_path, split="train")
    eval_ds = load_dataset("json", data_files=eval_path, split="train")
    logger.info(f"Train: {len(train_ds)} examples, Eval: {len(eval_ds)} examples")

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=config.get("num_train_epochs", 3),
        per_device_train_batch_size=config.get("per_device_train_batch_size", 4),
        per_device_eval_batch_size=config.get("per_device_train_batch_size", 4),
        gradient_accumulation_steps=config.get("gradient_accumulation_steps", 4),
        learning_rate=config.get("learning_rate", 2e-4),
        lr_scheduler_type=config.get("lr_scheduler_type", "cosine"),
        warmup_ratio=config.get("warmup_ratio", 0.05),
        fp16=config.get("fp16", False),
        bf16=config.get("bf16", True),
        gradient_checkpointing=config.get("gradient_checkpointing", True),
        optim=config.get("optim", "paged_adamw_32bit"),
        logging_steps=config.get("logging_steps", 10),
        save_strategy=config.get("save_strategy", "epoch"),
        eval_strategy=config.get("eval_strategy", "epoch"),
        report_to=config.get("report_to", "none"),
        seed=config.get("seed", 42),
        remove_unused_columns=False,
    )

    # SFTTrainer handles chat template formatting
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=lora_config,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=config.get("max_seq_length", 2048),
    )

    logger.info("Starting training...")
    trainer.train()

    # Save final adapter
    final_adapter_path = str(Path(output_dir) / "final_adapter")
    trainer.save_model(final_adapter_path)
    tokenizer.save_pretrained(final_adapter_path)
    logger.info(f"Adapter saved to {final_adapter_path}")

    # Log final metrics
    metrics = trainer.evaluate()
    logger.info(f"Final eval metrics: {metrics}")


def main() -> None:
    parser = argparse.ArgumentParser(description="QLoRA fine-tuning for CodeTune")
    parser.add_argument(
        "--config", default="configs/train_config.yaml", help="Training config path"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    finetune(args.config)


if __name__ == "__main__":
    main()
