"""GRPO retrain for ToolTune restraint — Kaggle/Colab free tier.

Run as a Kaggle notebook (Accelerator: T4 x1, ~30h/wk free) or Colab (free T4).
Self-contained: clones the repo, merges the SFT adapter into the base model
with a streaming merge (no big RAM spike), trains GRPO, verifies the adapter
actually learned, saves to /kaggle/working.

Before running:
  1. Upload the SFT adapter once (one-time, ~80MB):
       hf auth login   # or: huggingface-cli login
       hf upload <you>/tooltune-sft-adapter D:/Codetune/results/models/sft-merged
  2. Set HF_USER below.
  3. Kaggle: Add Data > your HF token as a secret named HF_TOKEN (optional if repo public).

Fixed vs the failed run:
  - learning_rate 5e-6 -> 2e-5  (LoRA needs ~4-10x full-FT rates)
  - num_generations 2 -> 4      (G=2 gives near-degenerate advantage signal)
  - max_steps 60 -> 120         (still fits a Kaggle session)
  - post-train assertion on adapter weight magnitude (catches silent no-ops)
"""

# %% cell 1 — install deps (Kaggle has most; pin TRL to what trained the original)
# !pip install -q "trl==0.19.1" "peft>=0.13" "bitsandbytes" "datasets" "safetensors" "accelerate"

# %% cell 2 — config
HF_USER = "aravindpersona"          # <-- set this
SFT_ADAPTER_REPO = f"{HF_USER}/tooltune-sft-adapter"
BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
REPO_URL = "https://github.com/harneet2512/Codetune.git"
WORK = "/kaggle/working"              # or "/content" on Colab
OUT_DIR = f"{WORK}/tooltune-grpo-restraint-v2"

# %% cell 3 — clone repo (task files + reward code)
import os, subprocess, sys
if not os.path.exists(f"{WORK}/Codetune"):
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, f"{WORK}/Codetune"], check=True)
os.chdir(f"{WORK}/Codetune")
sys.path.insert(0, os.getcwd())

# %% cell 4 — download base + SFT adapter, stream-merge into bf16 weights
import json, re
from pathlib import Path
import torch
from huggingface_hub import snapshot_download
from safetensors import safe_open
from safetensors.torch import save_file

def stream_merge(base_dir: str, adapter_dir: str, out_dir: str):
    base, adapter, out = map(Path, (base_dir, adapter_dir, out_dir))
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((adapter / "adapter_config.json").read_text())
    scaling = cfg["lora_alpha"] / cfg["r"]
    with safe_open(adapter / "adapter_model.safetensors", "pt") as f:
        ad = {k: f.get_tensor(k) for k in f.keys()}
    deltas = {}
    for k, a in ad.items():
        if k.endswith("lora_A.weight"):
            mod = re.sub(r"^base_model\.model\.", "", k)
            mod = re.sub(r"\.lora_A\.weight$", "", mod)
            b = ad[re.sub(r"\.lora_A\.weight$", ".lora_B.weight", k)]
            deltas[mod + ".weight"] = (a, b)
    index = json.loads((base / "model.safetensors.index.json").read_text())
    new_map = {}
    for shard_name in sorted(set(index["weight_map"].values())):
        out_shard = {}
        with safe_open(base / shard_name, "pt") as f:
            for key in f.keys():
                w = f.get_tensor(key)
                if key in deltas:
                    a, b = deltas[key]
                    w = (w.float() + (b.float() @ a.float()) * scaling).to(w.dtype)
                out_shard[key] = w
        save_file(out_shard, out / shard_name, metadata={"format": "pt"})
        for k in out_shard:
            new_map[k] = shard_name
        print("merged shard", shard_name)
    for p in base.iterdir():
        if p.suffix in (".json", ".model", ".txt") and "index" not in p.name:
            (out / p.name).write_bytes(p.read_bytes())
    (out / "model.safetensors.index.json").write_text(
        json.dumps({"metadata": index.get("metadata", {}), "weight_map": new_map}, indent=2)
    )

base_dir = snapshot_download(BASE_MODEL)
adapter_dir = snapshot_download(SFT_ADAPTER_REPO, token=os.environ.get("HF_TOKEN"))
SFT_MERGED = f"{WORK}/sft_merged"
if not os.path.exists(SFT_MERGED):
    stream_merge(base_dir, adapter_dir, SFT_MERGED)

# %% cell 5 — GRPO training (fixed hyperparams)
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import GRPOConfig, GRPOTrainer
from tooltune.contracts import TaskRecord
from tooltune.io import load_json
from tools.registry import ToolRegistry
from train.agentic_loop import build_system_prompt
from train.reward import reward_fn

registry = ToolRegistry()
rows = []
for f in ["tasks/tier1_single_tool.json", "tasks/tier2_restraint.json",
          "tasks/tier3_multi_step.json", "tasks/tier4_error_recovery.json"]:
    for item in load_json(f):
        task = TaskRecord(
            id=item.get("id", ""), tier=item.get("tier", ""), prompt=item["prompt"],
            ground_truth=item.get("ground_truth", ""),
            expected_tools=item.get("expected_tools", []),
            metadata=item.get("metadata", {}),
            error_injection_policy=item.get("error_injection_policy", {}),
        )
        rows.append({
            "prompt": build_system_prompt(task, registry),
            "ground_truth": task.ground_truth,
            "expected_tools": json.dumps(task.expected_tools),
        })
dataset = Dataset.from_list(rows)
print(f"{len(dataset)} tasks")

tokenizer = AutoTokenizer.from_pretrained(SFT_MERGED)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    SFT_MERGED,
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    ),
    device_map="auto",
)

trainer = GRPOTrainer(
    model=model,
    processing_class=tokenizer,
    train_dataset=dataset,
    reward_funcs=reward_fn,
    peft_config=LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        bias="none", task_type="CAUSAL_LM",
    ),
    args=GRPOConfig(
        output_dir=OUT_DIR,
        num_generations=4,
        generation_kwargs={"max_new_tokens": 256, "do_sample": True, "temperature": 0.8},
        learning_rate=2e-5,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=120,
        bf16=True,
        beta=0.04,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        logging_steps=5,
        save_steps=30,
        report_to="none",
    ),
)
trainer.train()
trainer.save_model(OUT_DIR)
tokenizer.save_pretrained(OUT_DIR)

# %% cell 6 — SANITY CHECK: did the adapter actually learn? (the failure that killed v1)
from safetensors import safe_open
with safe_open(f"{OUT_DIR}/adapter_model.safetensors", "pt") as f:
    keys = [k for k in f.keys() if k.endswith("lora_B.weight")]
    means = [f.get_tensor(k).abs().mean().item() for k in keys]
b_mean = sum(means) / len(means)
print(f"lora_B mean magnitude: {b_mean:.3e}")
assert b_mean > 1e-4, (
    f"Adapter looks untrained (B mean {b_mean:.2e}, expected >1e-4). "
    "Raise learning_rate or max_steps and rerun."
)
print("Adapter verified — real learned deltas.")

# %% cell 7 — quick behavioral probe (restraint should answer directly)
model.eval()
probe = (
    "You are a helpful assistant with access to the following tools:\n\n[]\n\n"
    "To use a tool, write a <tool_call> block with JSON.\n\n"
    "User: What is 6 squared?\n"
)
# (uses the model's own tokenizer; quick eyeball check only — real eval is local)
inputs = tokenizer(probe, return_tensors="pt").to(model.device)
with torch.no_grad():
    out = model.generate(**inputs, max_new_tokens=150, do_sample=False,
                         pad_token_id=tokenizer.pad_token_id)
print(tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True))
print(f"\nDone. Adapter + checkpoints in {OUT_DIR} — download and merge locally.")
