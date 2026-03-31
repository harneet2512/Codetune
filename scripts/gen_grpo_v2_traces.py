"""Generate traces for GRPO v2 model (merged SFT + GRPO adapter)."""
import json
import logging
import random
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from tooltune.contracts import TaskRecord
from tooltune.io import load_json, dump_json
from tools.registry import ToolRegistry
from train.agentic_loop import ModelTextGenerator, generate_agentic_completion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger()

# Load tasks
tasks = []
for f in sorted(Path("tasks").glob("tier*.json")):
    for item in load_json(f):
        tasks.append(TaskRecord(**item))
random.seed(42)
random.shuffle(tasks)
tasks = tasks[:50]
logger.info("Loaded %d tasks", len(tasks))

# Load model
logger.info("Loading merged SFT base + GRPO v2 adapter")
bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    "outputs/tooltune-sft-merged",
    quantization_config=bnb,
    device_map="auto",
    trust_remote_code=True,
)
model = PeftModel.from_pretrained(model, "outputs/tooltune-grpo-balanced-v2")
model.eval()

tokenizer = AutoTokenizer.from_pretrained(
    "outputs/tooltune-grpo-balanced-v2", trust_remote_code=True
)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

generator = ModelTextGenerator(model, tokenizer)
registry = ToolRegistry()

traces = []
for i, task in enumerate(tasks):
    logger.info("[grpo-v2] Task %d/50: %s", i + 1, task.id)
    trace = generate_agentic_completion(
        generator=generator, task=task, registry=registry, max_steps=5, temperature=0.0
    )
    traces.append(trace.to_dict())

Path("results/traces").mkdir(parents=True, exist_ok=True)
dump_json(Path("results/traces/grpo-balanced.json"), traces)
logger.info("Saved 50 GRPO v2 traces")
