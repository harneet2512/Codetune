# CodeTune / Restraint-7B

A post-training and agent-evaluation lab. The headline artifact is **Restraint-7B** — a Qwen2.5-7B-Instruct model trained to hold the tool/no-tool decision boundary — plus the eval infrastructure that caught four silent failures before release, falsified a wrong hypothesis, traced a failure to a data-generator bug, and proved the fix on identical task IDs.

Weights + model card: [huggingface.co/aravindpersona/restraint-7b](https://huggingface.co/aravindpersona/restraint-7b) · Engineering narrative: [TECHREPORT.md](TECHREPORT.md)

## The model vs the baseline

200-task paired eval — same task IDs, same harness, same scorer, temperature 0, real deterministic tool executor:

| Metric | SFT baseline | **Restraint-7B v3** |
|---|---|---|
| Task accuracy | 71.5% (143/200) | **92.0%** (184/200) [87.4–95.0] |
| Restraint (no-tool tasks, 0 calls) | **0%** (0/63) | **98.4%** (62/63) [91.5–99.7] |
| Total tool calls | 445 | **213** (−52%) |
| Tokens per resolved task | 2,090 | **1,163** (−44%) |
| Parse failures | 22% | **0%** |
| Tier 1 single-tool | 85/85 | **85/85** |
| Tier 4 error recovery (held-out) | 7/14 | **10/14** |

95% Wilson CIs in brackets. The baseline calls `calculator` on "What is 6 squared?" — it cannot tell *"I know this"* from *"I need a tool"*. Restraint-7B holds back, and restraint *adds* accuracy: every unnecessary call is also a failure surface.

## What the eval system caught

Four silent failures that headline metrics alone would have shipped:

1. **Dead adapter.** The first GRPO run produced an adapter with mean `lora_B` magnitude ~1e-6 — an untrained costume. A magnitude sanity check now gates every training run.
2. **Fabricated observations.** The harness was missing `</tool_call>` and `<observation>` stops — the model was writing its own tool results. Fixing the stop list moved measured accuracy 56% → 92%.
3. **Rotten ground truth.** 40/500 expected answers had drifted from environment regeneration. Repaired with a preserved diff (`results/gt_repair.json`).
4. **Contaminated baseline.** The "12% restraint" baseline was a pre-fix artifact; the true paired baseline is **0%**.

## The fix cycle (v2 → v3)

The n=200 eval left 20 canonical failures. They looked like generation-budget truncations, so we ran the falsification: all 20 re-evaluated at `max_tokens=512` → **0/20 recovered**. Trace forensics then found three layered mechanisms sharing one surface signature, two of them **inside the training-data generator itself**:

- `pop_ratio` emitted `population_X / population_Y` — symbolic variable names — as calculator args (5 tasks)
- `wiki_code` fell through to a generic branch that gave `code_executor` a `{"query": prompt}` arg — the model never saw a real `code` arg and improvised malformed JSON (5 tasks)

The generator was fixed, the model retrained (same 350-example recipe), and the identical 20 task IDs were re-evaluated: **exactly the 9 predicted data-borne failures recovered — 4/4 symbolic + 5/5 code — zero collateral change** on scorer artifacts and genuine recovery misses. Full suite re-run confirmed no regression: 90.0% → 92.0% accuracy, 88.9% → 98.4% restraint, 5% → 0% parse failures.

## The rest of the evidence

| Experiment | Result |
|---|---|
| **Adversarial restraint** (50 tool-bait prompts) | baseline captured **94%** of the time; v2 holds **56%** — real learned restraint, partially surface-form-dependent |
| **Unseen-ecosystem transfer** (17 GitHub/Drive/Gmail schemas, 120 tasks, zero-shot) | restraint **100%**, tool selection **76.8%**, judge-scored accuracy **50.8%** — argument grounding is the disclosed bottleneck |
| **Cross-scale ablation** (same 350-example recipe on Qwen2.5-1.5B) | restraint **96.8%** transfers; accuracy **37.5%** — the policy is scale-free, tool competence is capability-bound |
| **Quantization parity** (bf16 vs Q4_K_M, same 50 IDs) | 90% vs 92% — statistically indistinguishable |
| **Live APIs** (40 tasks, real Open-Meteo + Wikipedia) | restraint **100%**; misses are unit-conversion faithfulness, not tool decisions |
| **LLM judge secondary score** (`gpt-4o-mini`, committed prompt) | canonical 90% → **93%** — most residual "misses" are scorer strictness on paraphrases |

## Regression gate

`scripts/model_gate.py` — CI-ready release gate on any trace file:

```
gate: results/traces_release/v1-v3.json  (n=200)
  PASS  restraint_rate=0.984  >= 0.8
  PASS  tier1_acc=1.000       >= 0.95
  PASS  task_accuracy=0.920   >= 0.75
  PASS  parse_failure_rate=0.000  <= 0.1
GATE PASSED
```

Verified discriminating: it **rejects** the SFT baseline (3/4 failures), the 1.5B ablation (catches restraint-without-competence), and v2's adversarial traces (catches bait fragility).

## Reproduce

```bash
# Eval (any checkpoint, any suite) — Modal GPUs, resumable chunks
modal run scripts/modal_eval.py --model v2 --suite v1

# Merge chunks + score with Wilson CIs and token economics
python scripts/merge_eval_chunks.py v1-v3 --out results/traces_release/v1-v3.json

# Release gate
python scripts/model_gate.py results/traces_release/v1-v3.json
```

Raw traces for every number in this README: `results/traces_release/` (merged) and `results/traces_modal/` (raw chunks). Suites: `v1` (200), `v1-fail` (20 canonical failures), `adv` (50 bait prompts), `v3` (120 unseen-ecosystem), `paired50`, live-API variant via `tools/live_registry.py`.

## Full-stack playground

React frontend with three-column model comparison, block-based trace visualization, eval dashboard, connectors workbench with live tool testing, and a FastAPI backend with real API integrations (GitHub, Gmail, Google Drive via OAuth).

```bash
cd playground/client
npm install && npm run dev   # demo mode, no credentials needed
```

## Repo layout

```
train/                  Trace generators + SFT/GRPO training (the fixed generator lives here)
scripts/                Modal training/eval runners, merge+score, judge, release gate
tasks/                  Eval suites (v1 500, adversarial 50, unseen-ecosystem 120)
tools/                  Tool schemas + executors (deterministic mocks + live REST registry)
results/                Eval results + traces_release/ + traces_modal/ raw chunks
playground/             React client + FastAPI backend
```

## Technical details

- **Base**: Qwen/Qwen2.5-7B-Instruct (ChatML)
- **Post-training**: QLoRA SFT (450 expert ReAct traces) → corrective SFT (350 examples, r=64, lr=1e-4, 2 epochs) → data-fix v3 retrain; `lora_B` magnitude check on every adapter
- **Eval protocol**: `<think>/<tool_call>/<observation>/<answer>` raw-completion format, real executor, per-task persisted traces, canonical `is_correct` + LLM judge, Wilson CIs, tokens-per-resolved-task accounting
- **Spend to date**: ~$3 total on Modal

## Next

Incoming: **RL training for Qwen3-Coder-30B-A3B as a coding agent** — the frontier-lab recipe (verifiable rewards, GRPO, KL-gated rollouts) implemented and instrumented at small scale.
