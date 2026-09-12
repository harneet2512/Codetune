"""Memory-safe LoRA merge for release packaging.

Applies a PEFT LoRA adapter to a sharded safetensors base model,
processing one shard at a time so peak RAM stays near shard size.

Usage:
    python scripts/merge_lora_release.py \
        --base <dir with model*.safetensors + index> \
        --adapter <dir with adapter_model.safetensors + adapter_config.json> \
        --out <output dir>
"""

import argparse
import json
import re
import shutil
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import save_file


def load_adapter(adapter_dir: Path):
    cfg = json.loads((adapter_dir / "adapter_config.json").read_text())
    scaling = cfg["lora_alpha"] / cfg["r"]
    with safe_open(adapter_dir / "adapter_model.safetensors", "pt") as f:
        tensors = {k: f.get_tensor(k) for k in f.keys()}
    deltas = {}
    for k in tensors:
        if not k.endswith("lora_A.weight"):
            continue
        # base_model.model.model.layers.0.mlp.up_proj.lora_A.weight
        module = re.sub(r"^base_model\.model\.", "", k)
        module = re.sub(r"\.lora_A\.weight$", "", module)
        a = tensors[k]
        b = tensors[re.sub(r"\.lora_A\.weight$", ".lora_B.weight", k)]
        deltas[module + ".weight"] = (a, b)
    return deltas, scaling


def merge(base_dir: Path, adapter_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    deltas, scaling = load_adapter(adapter_dir)
    print(f"adapter: {len(deltas)} modules, scaling={scaling}")

    index_path = next(base_dir.glob("*.safetensors.index.json"), None)
    if index_path:
        index = json.loads(index_path.read_text())
        shard_files = sorted(set(index["weight_map"].values()))
        weight_map = index["weight_map"]
    else:
        shard_files = sorted(p.name for p in base_dir.glob("*.safetensors"))
        weight_map = None

    new_weight_map = {}
    for shard_name in shard_files:
        shard_path = base_dir / shard_name
        out_shard = {}
        with safe_open(shard_path, "pt") as f:
            keys = list(f.keys())
            for key in keys:
                w = f.get_tensor(key)
                if key in deltas:
                    a, b = deltas[key]
                    delta = (b.float() @ a.float()) * scaling
                    w = (w.float() + delta).to(w.dtype)
                    print(f"  merged {key} (+{delta.abs().mean():.5f} mean|d|)")
                out_shard[key] = w
        save_file(out_shard, out_dir / shard_name, metadata={"format": "pt"})
        for k in out_shard:
            new_weight_map[k] = shard_name
        del out_shard
        print(f"shard {shard_name}: {len(keys)} tensors -> {out_dir / shard_name}")

    # copy non-weight files
    for p in base_dir.iterdir():
        if p.suffix in (".json", ".jinja", ".txt", ".model") and "index" not in p.name:
            shutil.copy2(p, out_dir / p.name)
    # tokenizer files may live in adapter dir
    for name in ["tokenizer.json", "tokenizer_config.json", "chat_template.jinja",
                 "special_tokens_map.json", "vocab.json", "merges.txt"]:
        src = adapter_dir / name
        if src.exists():
            shutil.copy2(src, out_dir / name)

    if index_path:
        (out_dir / index_path.name).write_text(json.dumps(
            {"metadata": index.get("metadata", {}), "weight_map": new_weight_map},
            indent=2,
        ))
    print("done ->", out_dir)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, type=Path)
    ap.add_argument("--adapter", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    merge(args.base, args.adapter, args.out)
