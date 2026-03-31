# CodeTune — Progress Log

> This file documents every step of the pipeline for interview preparation.
> NOT uploaded to GitHub.

---

## Day 1 — March 25, 2026

### Infrastructure Setup

**GCP Project:** `fieldpilot-485003`
**Billing:** Linked to free credits ($300 budget)
**GPU Quota:** Requested GPUS_ALL_REGIONS increase from 0 → 1 (approved instantly)
**VM:** Vertex AI Workbench instance `codetune-nb`
  - Zone: `us-west4-b` (T4s were exhausted in us-central1, us-east1, us-west1 — had to try 12+ zones)
  - Machine: `n1-highmem-8` (8 vCPUs, 52GB RAM)
  - GPU: **Tesla T4** (16GB VRAM)
  - Disk: 200GB PD-Balanced
  - Image: PyTorch 2.7 + CUDA 12.8 on Ubuntu 22.04
  - Cost: ~$0.35/hr for T4 + ~$0.40/hr for n1-highmem-8 = **~$0.75/hr total**

**Why T4 over A100?**
- A100 = $3.67/hr (10x more expensive)
- T4 has 16GB VRAM — tight but works with QLoRA + gradient checkpointing
- QLoRA reduces trainable params to <1% so 16GB is enough
- Budget-conscious: $300 credits need to last for train + eval + serve + benchmark

### Model Selection

**Chose:** `Qwen/Qwen2.5-Coder-7B-Instruct`
**Why not Llama 3.1 8B?** Llama 3.1 is gated on HuggingFace (requires Meta approval, can take hours/days). Qwen2.5-Coder is:
- Fully open (no approval gate)
- 7B params (same class as Llama 8B)
- Actually stronger on coding benchmarks (HumanEval, MBPP)
- Uses ChatML template (standard, well-supported)

**Interview talking point:** "I chose the model that let me ship fastest without sacrificing quality. Qwen2.5-Coder outperforms Llama 3.1 8B on coding tasks anyway — the gating was a business constraint, not a technical one."

### Data Pipeline

**Dataset:** CodeAlpaca-20k (`sahil2801/CodeAlpaca-20k`)
- 20,022 instruction/response pairs covering code generation
- Filtered to Python-only: 7,414 kept (37% of original)
- Filtered out: 10,423 non-Python, 2,184 too short (<3 lines), 1 too long (>100 lines)
- Train/eval split: 6,672 train / 742 eval (90/10)

**Chat template:** Qwen2.5 ChatML format:
```
<|im_start|>system
You are a Python coding assistant...<|im_end|>
<|im_start|>user
{instruction}<|im_end|>
<|im_start|>assistant
{output}<|im_end|>
```

**Interview talking point:** "Data curation is where most fine-tuning projects fail. I filtered aggressively — only Python, only 3-100 lines, deduplicated — because training on garbage produces garbage. The chat template must exactly match the model's expected format or the model learns the wrong token patterns."

### QLoRA Training Configuration

```yaml
Base model: Qwen/Qwen2.5-Coder-7B-Instruct
Quantization: 4-bit NF4 with double quantization
LoRA rank: 16 (alpha: 32, dropout: 0.05)
Target modules: q_proj, k_proj, v_proj, o_proj
Trainable params: ~87M out of 4.35B (~2%)
Effective batch size: 16 (4 per device × 4 gradient accumulation)
Learning rate: 2e-4 with cosine schedule
Epochs: 3
Max sequence length: 2048
Optimizer: paged_adamw_32bit (memory efficient)
Gradient checkpointing: enabled (saves ~40% VRAM)
```

**Why these choices?**
- **QLoRA (4-bit):** Fits 7B model in 16GB VRAM. Full fine-tuning would need 56GB+.
- **Rank 16:** Good balance. Rank 8 underfits, rank 64 overfits on small datasets.
- **All attention projections:** Not just q/v (common mistake). Targeting all 4 gives better quality for ~2x the trainable params.
- **Cosine schedule:** Better than linear decay for short training runs.
- **Gradient checkpointing:** Trades ~20% speed for ~40% VRAM savings. Critical on T4.

**Interview talking point:** "QLoRA lets you fine-tune a 7B model on consumer hardware. The key insight is that 4-bit quantization preserves model quality during training because the gradients flow through the LoRA adapters in full precision — the frozen weights are just for the forward pass."

### Training Execution

**Status:** Training in progress on GCP VM
**Expected duration:** ~4-6 hours on T4 for 3 epochs × 6,672 examples
**Expected cost:** ~$3-5

---

## Architecture Decisions

### Why This Pipeline Matters for Fireworks

Fireworks AI productizes exactly this workflow:
1. **Dataset curation** → Fireworks' fine-tuning product accepts custom datasets
2. **Fine-tuning (SFT)** → Fireworks offers SFT as a managed service
3. **Evaluation** → The role is literally "Evals & Post-Training Product"
4. **Serving at multiple quantization levels** → Fireworks' core inference product
5. **Benchmarking throughput/latency/cost** → How Fireworks sells (fastest inference)

### How GroundTruth Fits

GroundTruth provides the **structural eval signal** — one of 4 eval suites:
1. HumanEval (functional correctness)
2. MBPP (broader code generation)
3. **Structural verification via GT** (hallucination detection, import correctness)
4. Custom quality evals (type hints, docstrings, error handling)

GT is integrated as a Python library, not the star of the show. It's one eval signal among four. But it's the UNIQUE signal — nobody else measures structural correctness of generated code.

**Interview talking point:** "Functional correctness (does the code pass tests?) is necessary but not sufficient. Code can pass tests while importing from nonexistent modules, using hallucinated function names, or calling APIs with wrong signatures. GroundTruth catches these structural issues that tests miss."

---

## Key Numbers to Remember

| Metric | Value |
|--------|-------|
| Base model | Qwen2.5-Coder-7B-Instruct |
| Training data | 6,672 examples (filtered from 20K) |
| Trainable params | ~87M / 4.35B (2%) |
| Training cost | ~$3-5 on T4 |
| Total pipeline cost | ~$10-15 (well under $300 budget) |
| Eval suites | 4 (HumanEval, MBPP, Structural/GT, Custom) |
| Serving configs | 9 (3 frameworks × 3 quant levels) |
| Benchmark prompts | 50 (10 short, 20 medium, 20 long) |

---

---

## Day 2 — March 27, 2026

### Fine-tuning Journey: SFT → GRPO

#### V1 / V2 (SFT instruct format)
- Standard SFT on CodeAlpaca, instruction format
- HumanEval: ~68-70% — **-18% vs base**
- Root cause: SFT shifts model distribution away from base instruct format

#### V3 (SFT completion format, rank 64)
- Switched to body-only completion format (no `def` header in output)
- HumanEval: **74.4% (122/164)** — still -12% vs base
- Bugs hit: `raw.strip()` removed leading 4-space indent → `return` at module level → SyntaxError
- Root cause of degradation: SFT on instruction data causes catastrophic forgetting (per RLEF paper)

#### V4 (GRPO — 150 MBPP examples, from V3)
- **Method:** Group Relative Policy Optimization (TRL GRPOTrainer)
- **Reward:** Binary code execution (python3 subprocess, timeout=10s)
- **Config:** rank=16, alpha=32, LR=5e-6, 2 gen, 128 max tokens, 75 steps, 34 min
- **Result: 86.6% (142/164) — matched base exactly**
- GRPO recovered all SFT damage in one 34-min run

#### V5 (GRPO — 374 MBPP examples, from V4) ← FINAL MODEL
- **Method:** Second GRPO pass starting from V4 (already at 86.6%)
- **Config:** rank=16, alpha=32, LR=5e-6, 2 gen, 256 max tokens, 187 steps, 2h 2min
- **Result: 87.8% (144/164) — BEAT BASELINE by +1.2%**
- Model fit fully in GPU (2 shards vs V4's 4) → eval ran 8x faster (971s vs 7783s)

### Final Results Table

| Model | HumanEval pass@1 | Passed | Delta |
|---|---|---|---|
| Base Qwen2.5-Coder-7B-Instruct | 86.6% | 142/164 | — |
| V1 SFT | ~68% | ~112/164 | -18% |
| V2 SFT | ~70% | ~115/164 | -16% |
| V3 SFT (completion) | 74.4% | 122/164 | -12.2% |
| V4 GRPO (150 ex) | 86.6% | 142/164 | = base |
| **V5 GRPO (374 ex)** | **87.8%** | **144/164** | **+1.2%** |

### V4 Full Eval (all 3 suites)
- HumanEval: 86.6% (142/164)
- Structural: 75% pass rate, 0 hallucinated symbols, 2 missing imports, 3 missing symbols
- Custom (code quality): 69.8% overall — docstrings 83%, error handling 78%, Pythonic 80%

### Key Insights for Interview

**Why SFT hurts instruct models:**
Fine-tuning an already-instruction-tuned model on a new dataset shifts the token distribution. The model "forgets" its base RLHF alignment. This is the catastrophic forgetting problem documented in the RLEF paper (Gehman et al.).

**Why GRPO works:**
GRPO keeps the model close to the reference policy via KL penalty while only reinforcing behaviors that lead to passing tests. It can't forget what it already knows — it can only add new behaviors. The KL coefficient (`beta=0.05`) controls this tradeoff.

**Why compounding GRPO (V4→V5) helped:**
V4 at 86.6% was already solving most easy/medium MBPP problems. V5's second pass with 2.5x more data provided signal on the marginal problems where V4 was inconsistent. Even with low reward variance (most problems solved or not solved consistently), the larger dataset gave more signal on edge cases.

**Research backing:**
- RLEF paper: RL methods preserve base capabilities; SFT degrades them
- Posterior-GRPO: +13.9% relative on Qwen2.5-Coder-7B-Instruct using GRPO with execution reward
- Our result: +1.2% absolute over base (86.6% → 87.8%) in <3 hours total GRPO training

### GCP Infrastructure Costs (Final)
- VM: n1-highmem-8 + T4 GPU = ~$0.75/hr
- Total runtime: ~48 hours ≈ **~$36 total**
- Well within $300 free credit budget

### Files Downloaded Locally
- `results/eval/base.json` — base model full eval
- `results/eval/codetune_v3.json` — V3 SFT results
- `results/eval/codetune_v4.json` — V4 GRPO full results (all 3 suites)
- `results/eval/codetune_v5.json` — V5 GRPO HumanEval results
- `results/v4_eval.log` — V4 eval run log
- `results/v5_train.log` — V5 GRPO training log (with step metrics)
- `results/v5_eval.log` — V5 eval run log
- `train/grpo_v4.py` — V4 GRPO script
- `train/grpo_v5.py` — V5 GRPO script
