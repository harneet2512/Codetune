"""
V4: GRPO with code execution feedback on MBPP.
Fast config for T4: num_gen=2, max_new_tokens=128, 150 examples, 1 epoch.
~35-40 min training, then eval.
"""
from __future__ import annotations
import logging, subprocess, tempfile, re
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import GRPOConfig, GRPOTrainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
OUTPUT_DIR = "outputs/checkpoints_v4"
MERGED_DIR = "outputs/codetune-7b-v4"
MAX_EXAMPLES = 150  # keep training fast on T4

def extract_code(text: str) -> str:
    if "```python" in text:
        m = re.search(r"```python\n(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
    if "```" in text:
        m = re.search(r"```\n?(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
    return text.strip()

def run_code_reward(completions: list[str], test_cases: list[str], **kwargs) -> list[float]:
    rewards = []
    for completion, tests in zip(completions, test_cases):
        code = extract_code(completion)
        program = code + "\n\n" + tests
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(program)
            fname = f.name
        try:
            result = subprocess.run(
                ["python3", fname], capture_output=True, timeout=10, text=True
            )
            reward = 1.0 if result.returncode == 0 else 0.0
        except Exception:
            reward = 0.0
        finally:
            Path(fname).unlink(missing_ok=True)
        rewards.append(reward)
    return rewards

def prepare_mbpp_dataset(max_examples: int = MAX_EXAMPLES):
    logger.info("Loading MBPP dataset...")
    ds = load_dataset("mbpp", split="train")
    examples = []
    for ex in ds:
        prompt = ex.get("text") or ex.get("prompt", "")
        test_list = ex.get("test_list", [])
        if not prompt or not test_list:
            continue
        instruction = (
            "Write a Python function to solve the following problem.\n"
            "Return ONLY the complete Python function, no explanation.\n\n"
            + prompt
        )
        tests = "\n".join(test_list)
        examples.append({"prompt": instruction, "test_cases": tests})
        if len(examples) >= max_examples:
            break
    logger.info(f"Prepared {len(examples)} MBPP training examples")
    return examples

logger.info(f"Loading base model: {BASE_MODEL}")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
logger.info("Model loaded")

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    bias="none",
    task_type="CAUSAL_LM",
)

grpo_config = GRPOConfig(
    output_dir=OUTPUT_DIR,
    num_generations=2,           # halved from 4 → much faster on T4
    generation_kwargs={"max_new_tokens": 128, "do_sample": True, "temperature": 0.8},
    learning_rate=5e-6,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_train_epochs=1,
    fp16=True,
    gradient_checkpointing=False,  # disabled: causes 'requires_grad' warning + slower
    save_strategy="epoch",
    logging_steps=5,
    beta=0.05,
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,
    remove_unused_columns=False,
    dataloader_num_workers=0,
    report_to="none",
)

raw_examples = prepare_mbpp_dataset(MAX_EXAMPLES)
from datasets import Dataset
train_data = Dataset.from_list(raw_examples)
logger.info(f"Training on {len(train_data)} examples for 1 epoch")

def reward_fn(completions, prompts=None, test_cases=None, **kwargs):
    if test_cases is None:
        test_cases = ["assert True"] * len(completions)
    return run_code_reward(completions, test_cases)

trainer = GRPOTrainer(
    model=model,
    args=grpo_config,
    train_dataset=train_data,
    reward_funcs=reward_fn,
    peft_config=lora_config,
    processing_class=tokenizer,
)

logger.info("Starting GRPO training...")
trainer.train()
logger.info("Training complete")
trainer.save_model(f"{OUTPUT_DIR}/final_adapter")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final_adapter")
logger.info(f"Adapter saved to {OUTPUT_DIR}/final_adapter")

logger.info("Merging adapter into base model...")
base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL, torch_dtype=torch.float16, device_map="cpu", trust_remote_code=True
)
merged = PeftModel.from_pretrained(base, f"{OUTPUT_DIR}/final_adapter")
merged = merged.merge_and_unload()
merged.save_pretrained(MERGED_DIR)
tokenizer.save_pretrained(MERGED_DIR)
logger.info(f"Merged model saved to {MERGED_DIR}")
