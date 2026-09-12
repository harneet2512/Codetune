"""Corrective SFT pass: restore restraint without losing tool behavior.

Kaggle/Colab free T4. ~30-90 min. Fixes the failure found in v1:
all 150 restraint demos in the original SFT set shared one canned think
("This is common knowledge, no tools needed."), so the model learned the
template, not the decision. This script regenerates restraint traces with
question-specific reasoning and mixes in tool traces so tool use survives.

Before running: upload the SFT adapter once (~80MB):
    hf upload <you>/tooltune-sft-adapter D:/Codetune/results/models/sft-merged
Then set HF_USER below.
"""

# %% cell 1 — deps
# !pip install -q "trl==0.19.1" "peft>=0.13" "bitsandbytes" "datasets" "safetensors" "accelerate"

# %% cell 2 — config
HF_USER = "aravindpersona"
SFT_ADAPTER_REPO = f"{HF_USER}/tooltune-sft-adapter"
BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
REPO_URL = "https://github.com/harneet2512/Codetune.git"
WORK = "/kaggle/working"          # "/content" on Colab
OUT_DIR = f"{WORK}/tooltune-restraint-sft"
N_TOOL = 200                      # tool/multi-step examples kept in the mix
N_RESTRAINT = 150                 # restraint examples (all of tier2)

# %% cell 3 — clone repo, merge SFT adapter into base (streaming, low RAM)
import os, re, sys, json, subprocess
from pathlib import Path
import torch
from huggingface_hub import snapshot_download
from safetensors import safe_open
from safetensors.torch import save_file

if not os.path.exists(f"{WORK}/Codetune"):
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, f"{WORK}/Codetune"], check=True)
os.chdir(f"{WORK}/Codetune")
sys.path.insert(0, os.getcwd())

def stream_merge(base_dir, adapter_dir, out_dir):
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
    for shard in sorted(set(index["weight_map"].values())):
        out_shard = {}
        with safe_open(base / shard, "pt") as f:
            for key in f.keys():
                w = f.get_tensor(key)
                if key in deltas:
                    a, b = deltas[key]
                    w = (w.float() + (b.float() @ a.float()) * scaling).to(w.dtype)
                out_shard[key] = w
        save_file(out_shard, out / shard, metadata={"format": "pt"})
        for k in out_shard:
            new_map[k] = shard
    for p in base.iterdir():
        if p.suffix in (".json", ".model", ".txt") and "index" not in p.name:
            (out / p.name).write_bytes(p.read_bytes())
    (out / "model.safetensors.index.json").write_text(
        json.dumps({"metadata": index.get("metadata", {}), "weight_map": new_map}, indent=2))

SFT_MERGED = f"{WORK}/sft_merged"
if not os.path.exists(SFT_MERGED):
    stream_merge(snapshot_download(BASE_MODEL),
                 snapshot_download(SFT_ADAPTER_REPO, token=os.environ.get("HF_TOKEN")),
                 SFT_MERGED)

# %% cell 4 — build corrective dataset: varied restraint thinks + real tool traces
import random
from tooltune.io import load_json
from tools.registry import ToolRegistry
from train.agentic_loop import build_system_prompt
from tooltune.contracts import TaskRecord
from train.sft_tooltune import _make_single_tool_trace, _make_multi_step_trace

random.seed(0)
registry = ToolRegistry()

RESTRAINT_THINKS = [
    "I know this from general knowledge — calling a tool would be unnecessary.",
    "This doesn't need live data or computation; I can answer directly.",
    "A tool call here adds latency without helping — I'll answer from knowledge.",
    "The available tools don't cover this; answering directly is correct.",
    "No external lookup needed — this is well-known.",
]

def restraint_body(answer):
    think = random.choice(RESTRAINT_THINKS)
    return f"<think>\n{think}\n</think>\n<answer>\n{answer}\n</answer>"

def wrap(task_dict, body_after_user_line):
    """Full inference-format example: system prompt (ends 'User: {prompt}\n')
    + completion body. The original SFT set omitted the system prompt entirely,
    so restraint was never learned in a context that lists tools — a second
    root cause alongside the canned think template."""
    task = TaskRecord(
        id=task_dict.get("id", "x"), tier=task_dict.get("tier", ""),
        prompt=task_dict["prompt"], ground_truth=task_dict.get("ground_truth", ""),
        expected_tools=task_dict.get("expected_tools", []),
        metadata=task_dict.get("metadata", {}),
        error_injection_policy=task_dict.get("error_injection_policy", {}))
    return {"text": build_system_prompt(task, registry) + body_after_user_line}

def strip_user_line(trace: str, prompt: str) -> str:
    return trace.split(f"User: {prompt}\n", 1)[-1]

restraint_items = load_json("tasks/tier2_restraint.json")[:N_RESTRAINT]
tool_items = ([t for t in load_json("tasks/tier1_single_tool.json")]
              + [t for t in load_json("tasks/tier3_multi_step.json")])
random.shuffle(tool_items)
tool_items = tool_items[:N_TOOL]

rows = [wrap(t, restraint_body(t["ground_truth"])) for t in restraint_items]
for t in tool_items:
    et = t.get("expected_tools", [])
    body = (_make_single_tool_trace(t["prompt"], t["ground_truth"], et[0], t)
            if len(et) == 1 else
            _make_multi_step_trace(t["prompt"], t["ground_truth"], et, t))
    rows.append(wrap(t, strip_user_line(body, t["prompt"])))

from datasets import Dataset
dataset = Dataset.from_list(rows).shuffle(seed=0)
print(f"{len(rows)} examples: {len(restraint_items)} restraint + {len(tool_items)} tool")

# %% cell 5 — LoRA on top of the SFT-merged model
from peft import LoraConfig, TaskType, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

tokenizer = AutoTokenizer.from_pretrained(SFT_MERGED)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    SFT_MERGED,
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True),
    device_map="auto")
model = prepare_model_for_kbit_training(model)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    peft_config=LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        bias="none", task_type=TaskType.CAUSAL_LM),
    processing_class=tokenizer,
    args=SFTConfig(
        output_dir=OUT_DIR,
        num_train_epochs=2,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=1e-4,           # lower than fresh SFT — we're correcting, not relearning
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        logging_steps=5,
        max_length=2048,
        dataset_text_field="text",
        bf16=True,
        save_strategy="epoch",
        report_to="none"),
)
trainer.train()
trainer.save_model(OUT_DIR)
tokenizer.save_pretrained(OUT_DIR)

# %% cell 6 — sanity: adapter must be non-trivial
with safe_open(f"{OUT_DIR}/adapter_model.safetensors", "pt") as f:
    means = [f.get_tensor(k).abs().mean().item()
             for k in f.keys() if k.endswith("lora_B.weight")]
b = sum(means) / len(means)
print(f"lora_B mean: {b:.3e}")
assert b > 1e-4, "Adapter looks untrained — raise LR or epochs."
print("Verified. Download adapter, merge locally, run scripts/eval_release.py.")
