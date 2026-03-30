"""Merge SFT LoRA adapter into base model weights."""
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = "Qwen/Qwen2.5-7B-Instruct"
ADAPTER = "outputs/tooltune-sft-checkpoints/final_adapter"
OUTPUT = "outputs/tooltune-sft-merged"

print("Loading base model...")
model = AutoModelForCausalLM.from_pretrained(
    BASE, torch_dtype=torch.bfloat16, device_map="cpu", trust_remote_code=True
)

print("Loading SFT adapter...")
model = PeftModel.from_pretrained(model, ADAPTER)

print("Merging adapter into base weights...")
model = model.merge_and_unload()

print("Saving merged model...")
model.save_pretrained(OUTPUT, safe_serialization=True)

tokenizer = AutoTokenizer.from_pretrained(ADAPTER, trust_remote_code=True)
tokenizer.save_pretrained(OUTPUT)

print(f"DONE - saved to {OUTPUT}")
