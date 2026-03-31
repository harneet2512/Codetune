import os, re, subprocess, tempfile
import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import GRPOConfig, GRPOTrainer

BASE_MODEL = "outputs/codetune-7b-v4"
OUTPUT_DIR = "outputs/checkpoints_v5"
MERGED_DIR = "outputs/codetune-7b-v5"
MAX_EXAMPLES = 374

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True,
)

lora_config = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    bias="none", task_type="CAUSAL_LM",
)

grpo_config = GRPOConfig(
    output_dir=OUTPUT_DIR,
    num_generations=2,
    generation_kwargs={"max_new_tokens": 256, "do_sample": True, "temperature": 0.8},
    learning_rate=5e-6,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_train_epochs=1,
    fp16=True,
    gradient_checkpointing=False,
    beta=0.05,
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,
    report_to="none",
    logging_steps=5,
)

def extract_code(completion):
    if "```python" in completion:
        import re as _re
        m = _re.search(r"```python\n(.*?)```", completion, _re.DOTALL)
        if m:
            return m.group(1).rstrip()
    if "```" in completion:
        import re as _re
        m = _re.search(r"```\n?(.*?)```", completion, _re.DOTALL)
        if m:
            return m.group(1).rstrip()
    return completion.rstrip()

def reward_fn(completions, prompts=None, test_cases=None, **kwargs):
    rewards = []
    for completion, tests in zip(completions, test_cases):
        code = extract_code(completion)
        program = code + "\n\n" + tests
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(program)
                fname = f.name
            result = subprocess.run(["python3", fname], capture_output=True, timeout=10)
            rewards.append(1.0 if result.returncode == 0 else 0.0)
        except Exception:
            rewards.append(0.0)
        finally:
            try:
                os.unlink(fname)
            except Exception:
                pass
    return rewards

def build_dataset():
    ds = load_dataset("google-research-datasets/mbpp", "full", split="train")
    examples = []
    for item in ds:
        if len(examples) >= MAX_EXAMPLES:
            break
        tests = "\n".join(item["test_list"])
        prompt = (
            "Write a Python function to solve the following problem:\n\n"
            + item["text"]
            + "\n\nReturn only the complete Python function, no explanation."
        )
        examples.append({"prompt": prompt, "test_cases": tests})
    return examples

def main():
    print("Loading base model: " + BASE_MODEL)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=bnb_config,
        device_map="auto", trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    dataset = build_dataset()
    print("Training on {} MBPP examples".format(len(dataset)))
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        args=grpo_config,
        train_dataset=dataset,
        reward_funcs=reward_fn,
    )
    trainer.train()
    print("Merging and saving...")
    merged = trainer.model.merge_and_unload()
    merged.save_pretrained(MERGED_DIR)
    tokenizer.save_pretrained(MERGED_DIR)
    print("Saved to " + MERGED_DIR)

if __name__ == "__main__":
    main()