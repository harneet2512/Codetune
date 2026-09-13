"""Cross-scale ablation: same 350-example corrective recipe on Qwen2.5-1.5B.

Single-pass SFT directly on the 1.5B base — v2 used two stages (450-trace
format SFT, then this corrective pass). If restraint + tool use both emerge
from the corrected data alone at 1.5B, the finding is "the data was the fix,
and the recipe transfers across scale." If not, that's the honest negative.

Adapter lands in volume restraint-eval:/models/r15b-adapter, then:
    modal run scripts/modal_eval.py --suite v1 --model r15b --n 200 --chunks 1
"""

import modal

REPO = "D:/Codetune"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch", "transformers>=4.45", "trl==0.19.1", "peft>=0.13",
        "bitsandbytes", "datasets", "safetensors", "accelerate",
    )
    .add_local_dir(f"{REPO}/tooltune", "/repo/tooltune")
    .add_local_dir(f"{REPO}/tools", "/repo/tools")
    .add_local_dir(f"{REPO}/train", "/repo/train")
    .add_local_dir(f"{REPO}/tasks", "/repo/tasks")
    .add_local_dir(f"{REPO}/tooltune_data", "/repo/tooltune_data")
)

app = modal.App("restraint-sft-15b", image=image)
vol = modal.Volume.from_name("restraint-eval", create_if_missing=True)

N_RESTRAINT = 150
N_TOOL = 200


@app.function(gpu="L4", volumes={"/vol": vol}, timeout=3 * 3600)
def train():
    import random, sys
    from pathlib import Path
    import torch
    from safetensors import safe_open

    os_path = "/repo"
    sys.path.insert(0, os_path)
    import os
    os.chdir(os_path)

    from tooltune.io import load_json
    from tooltune.contracts import TaskRecord
    from tools.registry import ToolRegistry
    from train.agentic_loop import build_system_prompt
    from train.sft_tooltune import _make_single_tool_trace, _make_multi_step_trace

    random.seed(0)
    registry = ToolRegistry()
    THINKS = [
        "I know this from general knowledge — calling a tool would be unnecessary.",
        "This doesn't need live data or computation; I can answer directly.",
        "A tool call here adds latency without helping — I'll answer from knowledge.",
        "The available tools don't cover this; answering directly is correct.",
        "No external lookup needed — this is well-known.",
    ]

    def wrap(t, body):
        task = TaskRecord(
            id=t.get("id", "x"), tier=t.get("tier", ""), prompt=t["prompt"],
            ground_truth=t.get("ground_truth", ""),
            expected_tools=t.get("expected_tools", []),
            metadata=t.get("metadata", {}),
            error_injection_policy=t.get("error_injection_policy", {}))
        return {"text": build_system_prompt(task, registry) + body}

    rows = []
    for t in load_json("tasks/tier2_restraint.json")[:N_RESTRAINT]:
        body = (f"<think>\n{random.choice(THINKS)}\n</think>\n"
                f"<answer>\n{t['ground_truth']}\n</answer>")
        rows.append(wrap(t, body))

    tool_items = (load_json("tasks/tier1_single_tool.json")
                  + load_json("tasks/tier3_multi_step.json"))
    random.shuffle(tool_items)
    for t in tool_items[:N_TOOL]:
        et = t.get("expected_tools", [])
        trace = (_make_single_tool_trace(t["prompt"], t["ground_truth"], et[0], t)
                 if len(et) == 1 else
                 _make_multi_step_trace(t["prompt"], t["ground_truth"], et, t))
        rows.append(wrap(t, trace.split(f"User: {t['prompt']}\n", 1)[-1]))

    from datasets import Dataset
    ds = Dataset.from_list(rows).shuffle(seed=0)
    print(f"dataset: {len(ds)} examples", flush=True)

    from peft import LoraConfig, TaskType, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    BASE = "Qwen/Qwen2.5-1.5B-Instruct"
    tok = AutoTokenizer.from_pretrained(BASE)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        BASE,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True),
        device_map="auto")
    model = prepare_model_for_kbit_training(model)

    OUT = "/tmp/r15b-adapter"
    trainer = SFTTrainer(
        model=model, train_dataset=ds,
        peft_config=LoraConfig(
            r=16, lora_alpha=32, lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            bias="none", task_type=TaskType.CAUSAL_LM),
        processing_class=tok,
        args=SFTConfig(
            output_dir=OUT, num_train_epochs=2,
            per_device_train_batch_size=1, gradient_accumulation_steps=4,
            learning_rate=1e-4,
            logging_steps=5, max_length=2048, dataset_text_field="text",
            bf16=True, save_strategy="no", report_to="none"),
    )
    trainer.train()
    trainer.save_model(OUT)
    tok.save_pretrained(OUT)

    with safe_open(f"{OUT}/adapter_model.safetensors", "pt") as f:
        means = [f.get_tensor(k).abs().mean().item()
                 for k in f.keys() if k.endswith("lora_B.weight")]
    b = sum(means) / len(means)
    print(f"lora_B mean: {b:.3e}", flush=True)
    assert b > 1e-4, "Adapter looks untrained"

    import shutil
    dst = Path("/vol/models/r15b-adapter")
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(OUT, dst)
    vol.commit()
    print("saved adapter -> volume:restraint-eval/models/r15b-adapter", flush=True)
    return {"lora_b_mean": b}
