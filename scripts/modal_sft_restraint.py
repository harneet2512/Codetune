"""Corrective restraint SFT on Modal — runs on your Modal credits.

One-time:  modal token new   (opens browser, click approve)
Then:      python -m modal run scripts/modal_sft_restraint.py
After:     python -m modal volume get restraint-runs restraint-sft D:/release/restraint-sft-adapter

Everything is baked into the image — no HF auth needed:
  - repo code + task data mounted from this checkout
  - SFT adapter baked in from results/models/sft-merged (~80MB)
  - base weights downloaded inside the container (Qwen public, no token)

Fixes two root causes found in v1:
  1. All 150 restraint demos shared one canned think line -> model learned
     the template, not the decision boundary.
  2. SFT data had NO system prompt; inference prepends tool definitions ->
     restraint was never learned in a context that lists tools.
"""

import modal

REPO = "D:/Codetune"  # Windows path — Modal handles local dir mounts fine

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
    .add_local_dir(f"{REPO}/results/models/sft-merged", "/adapter")
)

app = modal.App("restraint-sft", image=image)
vol = modal.Volume.from_name("restraint-runs", create_if_missing=True)

N_RESTRAINT = 150
N_TOOL = 200


@app.function(gpu="L4", volumes={"/out": vol}, timeout=3 * 3600)
def train():
    import json, os, random, re, sys
    from pathlib import Path
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    os.chdir("/repo")
    sys.path.insert(0, "/repo")

    # ---- merge SFT adapter into base (streaming, low RAM) ----
    from huggingface_hub import snapshot_download

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
            print("merged", shard, flush=True)
        for p in base.iterdir():
            if p.suffix in (".json", ".model", ".txt") and "index" not in p.name:
                (out / p.name).write_bytes(p.read_bytes())
        (out / "model.safetensors.index.json").write_text(
            json.dumps({"metadata": index.get("metadata", {}), "weight_map": new_map}))

    SFT_MERGED = "/tmp/sft_merged"
    if not Path(SFT_MERGED).exists():
        stream_merge(snapshot_download("Qwen/Qwen2.5-7B-Instruct"), "/adapter", SFT_MERGED)

    # ---- corrective dataset ----
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

    # ---- train ----
    from peft import LoraConfig, TaskType, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    tok = AutoTokenizer.from_pretrained(SFT_MERGED)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        SFT_MERGED,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True),
        device_map="auto")
    model = prepare_model_for_kbit_training(model)

    OUT = "/tmp/restraint-sft"
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

    # ---- sanity: adapter must be non-trivial ----
    with safe_open(f"{OUT}/adapter_model.safetensors", "pt") as f:
        means = [f.get_tensor(k).abs().mean().item()
                 for k in f.keys() if k.endswith("lora_B.weight")]
    b = sum(means) / len(means)
    print(f"lora_B mean: {b:.3e}", flush=True)
    assert b > 1e-4, "Adapter looks untrained"

    # ---- persist adapter to the volume FIRST (survives any later crash) ----
    import shutil
    dst = Path("/out/restraint-sft-v3")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(OUT, dst)
    vol.commit()
    print("saved adapter -> volume:restraint-runs/restraint-sft-v3", flush=True)

    # ---- also merge into the stage-1 weights -> evaluable v3 model ----
    V3_MERGED = "/tmp/v3_merged"
    if not Path(V3_MERGED).exists():
        stream_merge(SFT_MERGED, OUT, V3_MERGED)
        mdst = Path("/out/restraint-7b-v3-merged")
        if mdst.exists():
            shutil.rmtree(mdst)
        shutil.copytree(V3_MERGED, mdst)
        vol.commit()
        print("saved merged -> volume:restraint-runs/restraint-7b-v3-merged", flush=True)

    # ---- quick behavioral probe (non-fatal: real eval happens locally) ----
    try:
        from train.agentic_loop import generate_agentic_completion, ModelTextGenerator
        model.config.torch_dtype = torch.bfloat16
        gen = ModelTextGenerator(model, tok)
        for q in ["What is 6 squared?", "What is the weather in Tokyo right now?"]:
            task = TaskRecord(id="probe", tier="", prompt=q, ground_truth="",
                              expected_tools=[], metadata={}, error_injection_policy={})
            tr = generate_agentic_completion(gen, task, registry, max_steps=3)
            print(f"PROBE {q!r} -> {len(tr.tool_calls)} tool calls | answer: {tr.final_answer[:80]!r}", flush=True)
    except Exception as e:
        print(f"probe failed (non-fatal, adapter already saved): {e}", flush=True)

    return {"lora_b_mean": b}
