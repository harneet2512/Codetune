# Restraint-7B — Engineering Report

*What we trained, what it does that the baseline doesn't, and the system
that proves every number.*

## The claim

We trained **Restraint-7B** (Qwen2.5-7B-Instruct + corrective SFT) to hold
the tool/no-tool decision boundary — answer from knowledge when it can,
call a tool only when needed. Head-to-head against the SFT baseline on the
same 200 task IDs, same harness, same scorer, temperature 0:

| | SFT baseline | Restraint-7B v3 |
|---|---|---|
| Restraint (no-tool questions answered directly) | **0%** — calls tools on *every* knowledge question | **98.4%** (62/63) |
| Accuracy | 71.5% | **92.0%** |
| Tool calls | 445 | **213** |
| Tokens per resolved task | 2,090 | **1,163** (−44%) |
| Parse failures | 22% | **0%** |

The baseline's failure is behavioral, not cosmetic: ask it "What is 6
squared?" and it calls `calculator` — it can't tell "I know this" from "I
need a tool," so every knowledge question pays a tool call plus a failure
surface. That is the behavior the training changed, and every number in
this report is reproducible from committed traces.

Everything below is the proof system: what broke, how it was caught, and
what I'd actually trust.

## What would have made these numbers false

The reason to read this report instead of just the card: the first versions
of these numbers were wrong in three different ways, and each was caught by
instrumentation, not luck.

### 1. The adapter that wasn't trained

The first post-training run (GRPO) produced an adapter with `lora_B` mean
≈ 1e-6 — statistically indistinguishable from init. The model was the base
model wearing a costume. **Fix:** a post-train sanity gate that asserts
`lora_B` magnitude — the corrective SFT run produced 8.5e-04, a real delta.
This check now runs on every training job; it costs one line and would have
flagged the first run instantly.

### 2. The harness that let the model grade itself

The eval generator didn't stop at `</tool_call>`. The model — trained on
full ReAct transcripts — kept going and wrote its own `<observation>` block,
then answered from it. The "calculator" returned `138525` for `835 × 165`
(the real answer: `137775`) because the tool never ran; the model just
hallucinated a plausible-looking result. The published 56% accuracy was
measuring a hallucination loop.

**Fix:** stop generation at `</tool_call>` and `<observation>`, re-emit the
closing tag for the parser, and let the real executor write the observation.
Accuracy moved 56% → 92% — the "multi-step failures" (1/9) were fabrication
artifacts, and with real tool values the model went 9/9, including a genuine
`Invalid expression` → retry → correct-answer recovery.

Same bug class exists in production agent evals everywhere: if your harness
doesn't cleanly sever generation from tool execution, you're measuring the
model's ability to predict plausible tool output, not use tools.

### 3. Ground truths that had quietly rotted

40 of 500 task ground truths didn't match the deterministic simulators —
the task data files were regenerated at some point and the GTs weren't.
Stored traces showed the model "wrong" for faithfully reporting what the
tool returned. **Fix:** re-derived all GTs from the current simulators,
wrote the diff as `results/gt_repair.json` (sidecar, originals preserved),
and gated the eval on it.

## The evaluation matrix

| Suite | n | What it measures | Result |
|---|---|---|---|
| v1 paired | 200 | trained-tool competence + restraint | 90% acc, 88.9% restraint, −42% tokens/task |
| v3 unseen ecosystem | 120 | zero-shot transfer to 17 GitHub/Drive/Gmail schemas | restraint 100%, selection 76.8%, judge-acc 50.8% |
| paired50 bf16 | 50 | quantization parity (vs Q4_K_M 92%) | 90% — within noise |
| v1-live | 40 | real Open-Meteo + Wikipedia APIs | restraint 100%, completion 100% |
| adversarial | 50 | restraint under tool-bait phrasing | v2 56% vs baseline 6% — see below |

## Failure taxonomy — where the model actually fails

Every one of the 20 canonical failures in the n=200 run, decomposed by cause:

| Cause | Count | Signature |
|---|---|---|
| Scorer strictness | 6 | semantically correct paraphrase ("government by the people") — judge-overturned |
| **Symbolic-argument binding** | 4 | `calculator` called with `population_bangkok / population_switzerland` — variable names instead of observed values → `Invalid expression` → retry loop → max_steps |
| **Malformed nested JSON** | 5 | `code_executor` call ends `final_population"})` — a `)` where `}}` belongs — unparseable |
| Error-recovery misses | 4 | tool errors not recovered (tier4) |
| Definitional miss | 1 | clean-wrong |

**The falsification experiment** (`results/traces_release/v1-fail-v2-mt512.json`):
the first-pass read blamed the 256-token generation cap — five failures ended
with raw `<think>Plan:` markup. Re-running all 20 failed task IDs at
`max_new_tokens=512` recovered **0/20**. But it revealed the layered truth,
and the root cause turned out to be *in the training-data generator itself*:

- **Symbolic args were taught, not learned.** `sft_tooltune.py`'s pop_ratio
  branch wrote `{"expression": "population_bangkok / population_switzerland"}`
  into the SFT traces — variable names as calculator args, with a fake
  observation pretending the call worked. The model reproduced the bug
  faithfully. (The neighboring `distance_cost` and `weather_convert` branches
  substituted real values — which is exactly why those patterns pass and
  pop_ratio fails deterministically.)
- **The malformed-JSON failures were a data gap too.** `wiki_code` fell
  through to the generic multi-step branch, which gives *every* tool —
  including `code_executor` — a `{"query": prompt}` arg. The model never saw
  a `code` arg in multi-step context, so at eval it improvises notebook-style
  code (`; final_population` — no `print`, and a dropped `}` that makes the
  whole `<tool_call>` block regex-invisible to the harness). Tier-1 code
  tasks pass 85/85 because their `meta.code` ships `print(...)`. Same model,
  different data.
- The 256 cap was real but cosmetic: at 512 the same calls complete and fail
  anyway — truncation was masking a parse slip which was masking a semantic
  bug. Three layers, one surface signature.

**The fix cycle — closed and measured** (`train/sft_tooltune.py`,
`results/traces_release/v1-fail-v3.json`): pop_ratio now parses the observed
populations and emits `{"expression": "11.1 / 8.9"}` with the real
calculator output as the observation; wiki_code got a dedicated branch
teaching `print(...)` + value binding. Retrained the same 350-example
corrective recipe → **v3** → re-eval on the identical 20 task IDs:

| Class | Recovered |
|---|---|
| Symbolic-arg binding (pop_ratio + recovery-22) | **4/4** — now emits `11.1 / 8.9` |
| Malformed code calls (wiki_code + recovery-16/23) | **5/5** — now emits `print(result)` |
| Scorer artifacts (tier2 paraphrases) | 0/7 — never broken |
| Genuine recovery misses | 0/4 — real remaining weakness |
| **Total** | **9/20 — 100% of the data-caused failures, 0 false positives** |

The recovered traces show the exact learned behavior:
`calculator {"expression": "11.1 / 8.9"}` → `1.25`, and
`code_executor {"code": "pop = 29.2; growth_rate = 2.5/100; ...; print(result)"}` → `42.29`.

That precision matters: the fix recovered *exactly* the failures the root-
cause analysis attributed to the two generator bugs and touched nothing
else — a validated causal model, not a vibe. It also converts "the eval
found a bug" into "the eval found a bug, traced it to a data-generator
line, and measured the fix" — the complete engineering loop, on record.

**Full-suite regression check** (`results/traces_release/v1-v3.json`, same
200 IDs, bf16): v3 isn't just the fix — it's strictly better:

| | v2 | v3 |
|---|---|---|
| Accuracy | 90.0% [85.1–93.4] | **92.0%** [87.4–95.0] |
| Restraint | 88.9% | **98.4%** (62/63) |
| tier4 recovery | 7/14 | **10/14** |
| Parse failures | 5% | **0%** — malformed-call markup eliminated |
| Tokens/correct task | 1205 | **1163** |
| Gate | PASS | **PASS** — all four |

Remaining v3 failures (16): 9 tier2 scorer-strictness paraphrases, 4
genuine tier4 recovery misses, 3 tier3 edge cases — the honest residual
after the data-borne bugs were removed.

## Zero-shot transfer: the interesting finding

The model never saw the GitHub/Drive/Gmail connector ecosystem in training.
On 120 tasks over those 17 unseen schemas:

- **Restraint: 38/38 = 100%.** The no-tool policy is not tied to the five
  training tools — it transfers perfectly. This is the headline: the
  behavior learned was a *decision boundary*, not a lookup table.
- **Tool selection: 63/82 = 76.8%.** Misses are semantically adjacent
  tools (`gmail_search` when `gmail_read_email` was needed).
- **End-task accuracy: canonical 15.8% → judge-scored 50.8%.** The real
  bottleneck is *argument grounding*: the model picks the right tool but
  guesses argument conventions (`File not found: 123456789` — a doc ID it
  invented; `No emails found` — a query param the mock didn't recognize).

That last point is the honest research finding: **the policy transfers; the
schema conventions don't.** An enterprise integrating new tools should
expect restraint to hold and argument-filling to need examples or schema-
aware prompting.

## Cross-scale ablation — which half of the recipe transfers?

Same 350-example corrective recipe, single-pass, on `Qwen2.5-1.5B-Instruct`
(lora_B verified at 1.045e-03 — a real adapter). Same 200 v1 task IDs:

| | 7B v2 | 1.5B same-recipe |
|---|---|---|
| Restraint | 88.9% [78.8–94.5] | **96.8%** [89.1–99.1] |
| Accuracy | 90.0% | 37.5% |
| tier1 tool use | 100% | 31.8% |
| tier3 multi-step | ~100% capable | 28.9% |

The recipe splits in two. The **restraint policy is scale-free** — the
corrective data installs the decision boundary even on a base too weak to
use tools well (96.8%, *better* than the 7B). But **tool execution is
capability-bound**: the 1.5B picks restraint correctly yet fumbles args and
faithfulness when it does call. The two-stage pipeline wasn't the fix — the
corrected data was — and the base model's competence is the binding
constraint on the tool half. That's the kind of result a single-scale
project can't produce.

## Adversarial restraint — where the policy breaks

Fifty prompts engineered to bait tool use ("Use the calculator to verify:
What is an adjective?", "Look this up on Wikipedia first: What is a for
loop?", "Before answering, verify it with a tool: What is 1000/10?").
Same harness, both models:

| | SFT baseline | v2 |
|---|---|---|
| Restraint under bait | 6% (3/50) | **56%** (28/50) |
| Accuracy | 40% | 76% |
| Tool calls | 167 | 25 |
| Tokens per correct task | 4,947 | 954 |

The baseline is almost fully captured by the bait (94% tool-use rate — it
calls whatever the prompt names). v2's restraint survives the bait only
56% of the time vs 89% on neutral phrasing — **the policy is partially
surface-form-dependent**: imperative tool-mentioning phrasing overrides the
learned boundary 44% of the time. When the baited call succeeds the answer
usually still lands (calculator on real arithmetic → 100); when it queries
a tool with no relevant data ("bones in the human body" → empty wiki mock)
the answer degrades to "I don't have enough information."

This is the honest ceiling of the current artifact and the concrete next
data fix: adversarially-phrased restraint examples in the training set. It
also demonstrates why a restraint claim needs an adversarial control — a
neutral-phrasing eval alone would have overclaimed.

## The regression gate

`scripts/model_gate.py` turns the eval into a CI check — restraint ≥ 0.80,
tier1 ≥ 0.95, accuracy ≥ 0.75, parse-failure rate ≤ 10%. Demonstrated:

| Trace | Gate result |
|---|---|
| `v1-v2.json` (n=200) | **PASSED** — all four gates |
| `v1-baseline.json` | **FAILED** — restraint 0.000, accuracy 0.735, parse 22% |
| `adv-v2.json` | **FAILED** — restraint 0.560 < 0.80 (catches the bait fragility) |
| `adv-baseline.json` | **FAILED** — all applicable gates |

The gate rejects the known-bad checkpoint *and* flags the adversarial
weakness on the good one — that's what a release gate is for.

## What I would not claim

- Restraint is **not robust to adversarial phrasing**: 56% under tool-bait
  prompts vs 89% neutral. The gate flags it; the fix is data, not spin.
- Real production API fluency — live eval proves the loop works end-to-end
  and restraint holds; argument grounding on unfamiliar schemas does not.
- Held-out error recovery is weak: 7/14 (n=14). Real signal, small sample.
- The 90% figure is in-distribution for tiers 1–3; tier4 + v3 + adversarial
  are the OOD evidence, and they say "policy transfers, serialization and
  grounding don't."
- The 1.5B ablation shows the recipe is not magic: restraint transfers
  (96.8%) but tool competence doesn't (37.5%) — the base model's ability is
  the binding constraint.
- This is a 7B on a controlled suite. It's a product artifact — instrumented,
  measured, honestly bounded — not a capability breakthrough.

## Reproduce

```bash
# model: huggingface.co/aravindpersona/restraint-7b (GGUF + safetensors + adapter)
# code + tasks + traces: github.com/harneet2512/Codetune

# local: any llama.cpp server with the stop tokens in §usage
python scripts/eval_release.py --url http://127.0.0.1:8085 \
    --out results/traces_release/myrun.json

# cloud: chunked Modal eval (resumable, per-task persisted)
modal run scripts/modal_eval.py --suite v1 --model v2 --n 200 --chunks 1
modal volume get restraint-eval traces/ results/traces_modal/ --force
python scripts/merge_eval_chunks.py v1-v2

# gate it
python scripts/model_gate.py results/traces_release/v1-v2.json
```

## Provenance

Every number in this report maps to a committed trace file under
`results/traces_release/`; every trace is a real model run through the real
tool executor at temperature 0. Judge outputs (`*.judge.json`) carry the
judge prompt and pinned model. The eval was run on Modal T4s; total
post-training + evaluation spend was under $3.
