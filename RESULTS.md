# ToolTune Training Results

## Training Run — March 29-30, 2026
- **Instance:** GCP `tooltune-train` (n1-standard-8, Tesla T4 15GB, us-central1-b)
- **Base model:** Qwen/Qwen2.5-7B-Instruct
- **Quantization:** QLoRA (4-bit NF4, r=16, lora_alpha=32)

### SFT Training
- **Duration:** 27 minutes, 113 steps, 1 epoch
- **Data:** 450 synthetic traces (tier1 + tier2 + tier3)
- **Final loss:** 0.3394
- **Token accuracy:** 93.1% → 94.7%
- **Adapter size:** 77MB

### GRPO Training (v2 — on SFT-merged base)
- **Duration:** 2h 29m, 60 steps
- **Data:** 500 tasks (all 4 tiers)
- **Config:** num_generations=2, beta=0.04, max_new_tokens=256, lr=5e-6
- **Reward:** 0.27 → 0.685 (peak)
- **Adapter size:** 77MB

### 3-Way Evaluation (50 tasks, sampled across all tiers)

| Metric | BASE (V0) | SFT (V1) | GRPO (V4) |
|--------|-----------|----------|-----------|
| **Task Accuracy** | 8.0% | 58.0% | 56.0% |
| **Tool Usage Rate** | 0.0% | 74.0% | 54.0% |
| **Correct Format** | 100% | 100% | 100% |
| **Restraint (no-tool tasks)** | 100% | 64.7% | **100%** |

### Key Behavioral Findings

1. **Base model (V0):** Completely broken at tool use. Outputs raw JSON blobs like `{"tool": "calculator", "tool_params": {...}}` instead of using the ReAct `<tool_call>` format. 8% accuracy from lucky string matches only. Never actually executes a tool through the agentic loop.

2. **SFT model (V1):** Massive improvement. Learns the ReAct format, calls tools correctly (74% tool usage), achieves 58% task accuracy. **But over-tools** — calls tools on 35% of questions that don't need them (restraint drops from 100% to 64.7%).

3. **GRPO model (V4):** Matches SFT accuracy (56% vs 58%) while restoring **100% restraint**. The composite reward function (task=1.0, tools=0.3, restraint=0.1) successfully taught the model when NOT to use tools. Tool usage drops from 74% to 54% — the model is more selective, only calling tools when genuinely needed.

### Sample Traces

**Task:** "What is 37 multiplied by 576?"
- BASE: `{"tool": "calculator", "tool_params": {"expression": "37*576"}}` (raw JSON, no execution) → MISS
- SFT: `<think>I need to calculate this.</think><tool_call>{"name":"calculator","arguments":{"expression":"37 * 576"}}</tool_call><observation>21312</observation><answer>21312</answer>` → OK
- GRPO: Same as SFT → OK

**Task:** "What is 2+2?" (restraint — should not use tools)
- BASE: Does not call tools (doesn't know how) → accidental restraint
- SFT: Calls calculator anyway → over-tooling
- GRPO: Answers "4" directly without tools → correct restraint

### Issues Encountered
1. **fp16 vs bf16:** Qwen2.5 uses bfloat16 weights; fp16 AMP grad scaler fails. Fixed by switching to bf16=True.
2. **TRL 0.29 dataset format:** SFTTrainer detects `prompt` column as conversational format and expects `completion`. Fixed by excluding prompt from dataset.
3. **Double LoRA stacking:** GRPO v1 trained adapter on top of SFT adapter. At inference, only GRPO delta applied to base model, losing SFT behavior. Fixed by merging SFT into base weights first, then training single GRPO LoRA.
4. **T4 speed:** GRPO at 768 max_new_tokens = 12 min/step = 50hrs for 250 steps. Fixed by capping max_new_tokens=256 and max_steps=60.
