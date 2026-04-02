"""ToolTune v3 training on Modal — SFT + GRPO with research-backed recipe.

Usage:
    modal run train/modal_train.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Modal setup
# ---------------------------------------------------------------------------
app = modal.App("tooltune-v3-train")

# GPU image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.5.0",
        "transformers>=4.46.0,<5.0.0",
        "trl>=0.12.0,<1.0.0",
        "peft>=0.13.0",
        "bitsandbytes>=0.44.0",
        "datasets>=3.0.0",
        "accelerate>=1.0.0",
        "sentencepiece",
        "protobuf",
    )
)

# Add local code to image
image = image.add_local_dir(".", remote_path="/root/tooltune")

# Persistent volume for model outputs
vol = modal.Volume.from_name("tooltune-outputs", create_if_missing=True)


@app.function(
    image=image,
    gpu="A10G",  # 24GB VRAM
    timeout=7200,  # 2 hours max

    volumes={"/outputs": vol},
)
def train_sft():
    """Stage 1: SFT training on v3 traces."""
    import sys
    sys.path.insert(0, "/root/tooltune")
    os.chdir("/root/tooltune")

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem_in_bytes / 1e9:.1f} GB" if hasattr(torch.cuda.get_device_properties(0), 'total_mem_in_bytes') else "VRAM: check nvidia-smi")

    # Load training traces
    with open("train/v3_traces.json") as f:
        traces = json.load(f)
    print(f"Loaded {len(traces)} training traces")

    # Build dataset
    rows = []
    for tr in traces:
        rows.append({
            "text": tr["prompt"] + "\n" + tr["transcript"],
        })
    dataset = Dataset.from_list(rows)
    print(f"Dataset: {len(dataset)} examples")

    # Model
    BASE = "Qwen/Qwen2.5-7B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(BASE, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        ),
        device_map="auto",
        trust_remote_code=True,
    )

    # SFT config
    output_dir = "/outputs/sft-v3"
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            bias="none",
            task_type="CAUSAL_LM",
        ),
        args=SFTConfig(
            output_dir=output_dir,
            num_train_epochs=2,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            bf16=True,
            logging_steps=10,
            save_steps=50,
            save_total_limit=2,
            report_to="none",
        ),
    )

    print("Starting SFT training...")
    trainer.train()
    trainer.save_model(f"{output_dir}/final_adapter")
    tokenizer.save_pretrained(f"{output_dir}/final_adapter")
    print(f"SFT done — saved to {output_dir}/final_adapter")

    vol.commit()
    return {"status": "sft_done", "output": f"{output_dir}/final_adapter"}


@app.function(
    image=image,
    gpu="A10G",
    timeout=7200,

    volumes={"/outputs": vol},
)
def merge_sft():
    """Stage 2: Merge SFT adapter into base model."""
    import gc
    import sys
    sys.path.insert(0, "/root/tooltune")

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    BASE = "Qwen/Qwen2.5-7B-Instruct"
    ADAPTER = "/outputs/sft-v3/final_adapter"
    OUTPUT = "/outputs/sft-v3-merged"

    vol.reload()

    print("Loading base model to GPU...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE, dtype=torch.bfloat16, device_map="auto",
        trust_remote_code=True, low_cpu_mem_usage=True,
    )
    print("Loading SFT adapter...")
    model = PeftModel.from_pretrained(model, ADAPTER)
    print("Merging...")
    model = model.merge_and_unload()

    print("Saving merged model...")
    model.save_pretrained(OUTPUT, safe_serialization=True, max_shard_size="4GB")
    del model
    gc.collect()
    torch.cuda.empty_cache()

    tokenizer = AutoTokenizer.from_pretrained(ADAPTER, trust_remote_code=True)
    tokenizer.save_pretrained(OUTPUT)

    print(f"Merged model saved to {OUTPUT}")
    vol.commit()
    return {"status": "merge_done", "output": OUTPUT}


@app.function(
    image=image,
    gpu="A10G",
    timeout=10800,  # 3 hours for GRPO

    volumes={"/outputs": vol},
)
def train_grpo():
    """Stage 3: GRPO training with research-backed hyperparameters."""
    import sys
    sys.path.insert(0, "/root/tooltune")
    os.chdir("/root/tooltune")

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import GRPOConfig, GRPOTrainer

    vol.reload()

    BASE = "/outputs/sft-v3-merged"
    OUTPUT = "/outputs/grpo-v3"

    # Load tasks for GRPO
    tasks = []
    for tier_file in sorted(Path("tasks").glob("v3_tier*.json")):
        with open(tier_file) as f:
            tasks.extend(json.load(f))
    print(f"Loaded {len(tasks)} tasks for GRPO")

    # Build dataset with system prompts
    with open("tools/connectors/schemas.py") as f:
        pass  # We'll import properly

    from tools.connectors.schemas import CONNECTOR_TOOL_SCHEMAS

    tool_desc = json.dumps(CONNECTOR_TOOL_SCHEMAS, indent=2)
    system_prompt = (
        "You are a helpful assistant with access to the following tools:\n\n"
        f"{tool_desc}\n\n"
        "To use a tool, write a <tool_call> block with JSON. "
        "You will receive the result in an <observation> block.\n"
        "If you can answer without tools, do so directly in an <answer> block.\n"
        "Think step by step in <think> blocks before acting."
    )

    rows = []
    for task in tasks:
        prompt = f"{system_prompt}\n\nUser: {task['prompt']}"
        rows.append({
            "prompt": prompt,
            "ground_truth": task.get("ground_truth", ""),
            "expected_tools": json.dumps(task.get("expected_tools", [])),
        })
    dataset = Dataset.from_list(rows)

    # Model
    tokenizer = AutoTokenizer.from_pretrained(BASE, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        ),
        device_map="auto",
        trust_remote_code=True,
    )

    # Reward function — research-backed decomposed rewards
    def reward_fn(completions, prompts=None, ground_truth=None, expected_tools=None, **kwargs):
        import re
        rewards = []
        for i, completion in enumerate(completions):
            gt = ground_truth[i] if ground_truth else ""
            et_raw = expected_tools[i] if expected_tools else "[]"
            try:
                et = json.loads(et_raw) if isinstance(et_raw, str) else (et_raw or [])
            except (ValueError, TypeError):
                et = []

            # Extract components from completion
            answer_match = re.search(r"<answer>(.*?)</answer>", completion, re.DOTALL)
            tool_calls = re.findall(r"<tool_call>(.*?)</tool_call>", completion, re.DOTALL)
            thinks = re.findall(r"<think>(.*?)</think>", completion, re.DOTALL)

            predicted = answer_match.group(1).strip() if answer_match else ""

            # 1. Format reward (0.1) — valid structure
            has_answer = bool(answer_match)
            valid_json_calls = 0
            for tc in tool_calls:
                try:
                    json.loads(tc.strip())
                    valid_json_calls += 1
                except (ValueError, TypeError):
                    pass
            format_ok = has_answer and (valid_json_calls == len(tool_calls))
            format_reward = 0.1 if format_ok else 0.0

            # 2. Answer reward (1.0) — correct answer
            answer_reward = 0.0
            if predicted and gt:
                p, g = predicted.lower().strip(), gt.lower().strip()
                if p == g or g in p or p in g:
                    answer_reward = 1.0
                else:
                    try:
                        pf = float(re.sub(r"[^0-9.\-]", "", p))
                        gf = float(re.sub(r"[^0-9.\-]", "", g))
                        if abs(pf - gf) < 0.1 * max(abs(gf), 1):
                            answer_reward = 1.0
                    except (ValueError, ZeroDivisionError):
                        pass

            # 3. Tool accuracy (0.3) — right tools called
            tool_accuracy = 0.0
            if et:
                called_names = []
                for tc in tool_calls:
                    try:
                        parsed = json.loads(tc.strip())
                        called_names.append(parsed.get("name", ""))
                    except (ValueError, TypeError):
                        pass
                expected_names = [t if isinstance(t, str) else t.get("name", "") for t in et]
                if called_names and set(expected_names).issubset(set(called_names)):
                    tool_accuracy = 0.3
                elif called_names and any(n in expected_names for n in called_names):
                    tool_accuracy = 0.15

            # 4. Restraint (0.5) — no tools when none needed
            restraint_reward = 0.0
            overtool_penalty = 0.0
            if not et:  # No tools expected
                if len(tool_calls) == 0:
                    restraint_reward = 0.5
                else:
                    overtool_penalty = -0.5

            # 5. Efficiency — penalize excess calls
            if et:
                excess = max(0, len(tool_calls) - len(et) - 1)
                efficiency_penalty = -0.1 * excess
            else:
                efficiency_penalty = 0.0

            total = (format_reward + answer_reward + tool_accuracy
                     + restraint_reward + overtool_penalty + efficiency_penalty)
            rewards.append(max(total, -1.0))

        return rewards

    # GRPO config — research-backed
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        reward_funcs=reward_fn,
        peft_config=LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            bias="none",
            task_type="CAUSAL_LM",
        ),
        args=GRPOConfig(
            output_dir=OUTPUT,
            num_generations=8,           # Research: min 4, ideal 8 (was 2)
            generation_kwargs={
                "max_new_tokens": 512,   # Research: 512-1024 (was 256)
                "do_sample": True,
                "temperature": 1.0,      # Research: 1.0 for exploration (was 0.8)
            },
            learning_rate=5e-6,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,  # Research: 8 (was 4)
            max_steps=300,               # Research: 300+ (was 60)
            bf16=True,
            beta=0.0,                    # Research: 0.0, no KL (was 0.04)
            logging_steps=10,
            save_steps=100,
            report_to="none",
        ),
    )

    print("Starting GRPO training (300 steps, 8 generations)...")
    trainer.train()
    trainer.save_model(OUTPUT)
    tokenizer.save_pretrained(OUTPUT)
    print(f"GRPO done — saved to {OUTPUT}")

    vol.commit()
    return {"status": "grpo_done", "output": OUTPUT}


@app.function(
    image=image,
    gpu="A10G",
    timeout=3600,

    volumes={"/outputs": vol},
)
def generate_traces():
    """Stage 4: Generate evaluation traces for base, SFT, GRPO."""
    import sys
    sys.path.insert(0, "/root/tooltune")
    os.chdir("/root/tooltune")

    import random
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    from tooltune.contracts import TaskRecord
    from tools.connectors.mock import MockConnectorRegistry
    from tools.connectors.schemas import CONNECTOR_TOOL_SCHEMAS
    from train.agentic_loop import ModelTextGenerator, generate_agentic_completion

    vol.reload()

    # Load tasks
    tasks = []
    for tier_file in sorted(Path("tasks").glob("v3_tier*.json")):
        with open(tier_file) as f:
            for item in json.load(f):
                tasks.append(TaskRecord(**item))
    random.seed(42)
    random.shuffle(tasks)
    tasks = tasks[:50]
    print(f"Eval on {len(tasks)} tasks")

    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    registry = MockConnectorRegistry()

    results = {}
    for variant, model_path in [
        ("base", "Qwen/Qwen2.5-7B-Instruct"),
        ("sft", "/outputs/sft-v3-merged"),
        ("grpo", None),  # SFT-merged + GRPO adapter
    ]:
        print(f"\n=== Generating {variant} traces ===")
        model = AutoModelForCausalLM.from_pretrained(
            model_path if variant != "grpo" else "/outputs/sft-v3-merged",
            quantization_config=bnb, device_map="auto", trust_remote_code=True,
        )
        if variant == "grpo":
            model = PeftModel.from_pretrained(model, "/outputs/grpo-v3")
            model.eval()

        tokenizer = AutoTokenizer.from_pretrained(
            model_path if variant != "grpo" else "/outputs/grpo-v3",
            trust_remote_code=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        generator = ModelTextGenerator(model, tokenizer)
        traces = []
        for i, task in enumerate(tasks):
            print(f"  [{variant}] {i+1}/50: {task.id}")
            trace = generate_agentic_completion(
                generator=generator, task=task, registry=registry,
                max_steps=5, temperature=0.0,
            )
            traces.append(trace.to_dict())

        out_path = f"/outputs/traces/{variant}.json"
        os.makedirs("/outputs/traces", exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(traces, f, indent=2)
        print(f"  Saved {len(traces)} traces to {out_path}")
        results[variant] = len(traces)

        del model, generator
        torch.cuda.empty_cache()

    vol.commit()
    return results


@app.local_entrypoint()
def main():
    """Run the full pipeline: SFT → merge → GRPO → traces."""
    print("=== ToolTune v3 Training Pipeline ===\n")

    print("Stage 1: SFT training...")
    r1 = train_sft.remote()
    print(f"  {r1}\n")

    print("Stage 2: Merging SFT adapter...")
    r2 = merge_sft.remote()
    print(f"  {r2}\n")

    print("Stage 3: GRPO training (research-backed recipe)...")
    r3 = train_grpo.remote()
    print(f"  {r3}\n")

    print("Stage 4: Generating evaluation traces...")
    r4 = generate_traces.remote()
    print(f"  {r4}\n")

    print("=== Pipeline complete! ===")
    print("Outputs saved to Modal volume 'tooltune-outputs'")
    print("Download with: modal volume get tooltune-outputs /outputs .")
