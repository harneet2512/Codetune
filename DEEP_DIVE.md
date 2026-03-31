# CodeTune Deep Dive — Interview Preparation Guide

> This document goes concept-by-concept, line-by-line through every critical
> piece of CodeTune. It explains the math intuitively, covers what can go wrong,
> and prepares you for the hardest follow-up questions.

---

# PART 1: FOUNDATIONS — What You Need To Know Before Anything Else

## 1.1 What is a Language Model, Really?

A language model is a probability distribution over sequences of tokens.

Given tokens [t1, t2, ..., tn], the model predicts:

    P(t_{n+1} | t1, t2, ..., tn)

That's it. It takes everything it's seen so far and outputs a probability for
every possible next token in its vocabulary (~150k tokens for Qwen2.5).

**Autoregressive generation** means: predict one token, append it to the input,
predict the next token, repeat. That's why LLMs generate one token at a time.

**Temperature** controls the sharpness of the probability distribution:
- temp=0: Always pick the highest-probability token (greedy/deterministic)
- temp=0.8: Slightly flatten the distribution, allow some randomness
- temp=1.0: Use raw probabilities as-is
- temp>1.0: Flatten further, more random

In your code (`grpo_v4.py:107`), `temperature=0.8` during GRPO training gives
diversity in generated completions. In eval (`eval_config.yaml:16`), `temperature=0.0`
gives deterministic reproducible results.

**Why this matters for your project:**
Everything downstream — SFT, GRPO, evaluation — is about manipulating this
probability distribution. SFT shifts the entire distribution (and can break it).
GRPO nudges it carefully toward higher-reward outputs.

---

## 1.2 Tokenization and Chat Templates

### What is a tokenizer?

A tokenizer converts text into token IDs that the model understands. Qwen2.5
uses a BPE (Byte Pair Encoding) tokenizer with ~150k vocabulary entries.

"def hello():" might become tokens: [878, 24296, 4019, 25]

Each model has its own tokenizer. Using the wrong tokenizer = feeding garbage
token IDs to the model = garbage output.

### What is ChatML?

ChatML is a specific format for structuring conversations:

```
<|im_start|>system
You are a Python coding assistant.<|im_end|>
<|im_start|>user
Write a function to reverse a string.<|im_end|>
<|im_start|>assistant
def reverse_string(s):
    return s[::-1]<|im_end|>
```

The special tokens `<|im_start|>` and `<|im_end|>` are actual tokens in Qwen's
vocabulary. The model was RLHF-trained to understand this exact format.

### In your code (prepare_dataset.py:20-24):

```python
CHAT_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{instruction}<|im_end|>\n"
    "<|im_start|>assistant\n{output}<|im_end|>"
)
```

This manually constructs ChatML. It works for SFT because you're training on
the full conversation including the assistant response.

### In eval (humaneval.py:127-129):

```python
messages = [{"role": "user", "content": instruction}]
chat_prompt = tokenizer.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True
)
```

`apply_chat_template` is the proper way — it uses the tokenizer's built-in
template, adds `<|im_start|>assistant\n` at the end (that's what
`add_generation_prompt=True` does), so the model knows to start generating
the assistant response.

### What goes wrong if you mess this up?

If you train with ChatML but eval without it (or vice versa), the model sees
a different token pattern than it learned. Common symptoms:
- Model outputs raw text instead of code
- Model outputs `<|im_end|>` in the middle of code
- Model repeats the instruction instead of answering

**Hard interview question:** *"Why did you manually construct ChatML in
prepare_dataset.py instead of using apply_chat_template?"*

> "For SFT, I needed the FULL conversation in the `text` field — system +
> user + assistant response + all special tokens. `apply_chat_template` with
> `add_generation_prompt=True` gives you the prompt UP TO the assistant turn
> (for inference). For training data, I needed the complete text including the
> assistant's answer, so I templated it manually to include the `<|im_end|>`
> after the assistant output."

---

## 1.3 Model Architecture — What is Qwen2.5-Coder-7B-Instruct?

### Parameter count breakdown (approximate):

| Component | Size | What it does |
|-----------|------|-------------|
| Embedding layer | ~450M params | Converts token IDs to 4096-dim vectors |
| 32 Transformer layers, each containing: | | |
|   - q_proj, k_proj, v_proj, o_proj (attention) | ~100M per layer | Self-attention: "what should I pay attention to?" |
|   - gate_proj, up_proj, down_proj (MLP/FFN) | ~100M per layer | Feed-forward: "what should I compute from what I attended to?" |
| LM head | ~450M params | Converts final hidden state back to token probabilities |
| **Total** | **~7.6B params** | (stored as float16 = ~15GB, or int4 = ~4GB) |

### What are q_proj, k_proj, v_proj, o_proj?

Self-attention works by computing:

    Attention(Q, K, V) = softmax(QK^T / sqrt(d)) * V

Where:
- **Q (query)** = "what am I looking for?" — computed by q_proj
- **K (key)** = "what do I contain?" — computed by k_proj
- **V (value)** = "what information do I provide?" — computed by v_proj
- **O (output)** = projects the attention output back — computed by o_proj

Each is a linear layer: `q_proj: [4096] -> [4096]` (a 4096x4096 matrix = ~16M params).

### What are gate_proj, up_proj, down_proj?

These form the MLP (feed-forward network) inside each transformer layer.
Qwen2.5 uses a "gated" MLP:

    MLP(x) = down_proj(gate_proj(x) * silu(up_proj(x)))

- `up_proj`: [4096] -> [11008] (expands)
- `gate_proj`: [4096] -> [11008] (gate signal)
- `down_proj`: [11008] -> [4096] (compresses back)
- `silu` = smooth activation function (like ReLU but differentiable everywhere)

The gate decides "how much" of the expanded representation to let through.

### Why this matters for LoRA target modules:

In `grpo_v4.py:96-99`:
```python
target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"]
```

You're putting LoRA adapters on ALL linear layers in EVERY transformer layer.
That's the most capacity you can give LoRA without full fine-tuning.

In `finetune.py` / `train_config.yaml`, only attention projections were targeted:
```python
target_modules: ["q_proj", "k_proj", "v_proj", "o_proj"]
```

**Why the difference?** SFT on 6,672 examples doesn't need MLP adaptation —
attention-only is enough and less prone to overfitting. GRPO trains differently
(reinforcing existing behaviors, not learning new distributions), so more
capacity helps without overfitting.

---

# PART 2: QUANTIZATION — How You Fit 7B Parameters in 16GB

## 2.1 The Memory Problem

Qwen2.5-Coder-7B has ~7.6 billion parameters.

- Full precision (float32): 7.6B × 4 bytes = **30.4 GB** — won't fit on T4
- Half precision (float16): 7.6B × 2 bytes = **15.2 GB** — barely fits, no room for gradients
- 4-bit (int4): 7.6B × 0.5 bytes = **3.8 GB** — fits easily, room for everything else

But you can't train in 4-bit — gradients need precision. That's where QLoRA comes in.

## 2.2 QLoRA — The Key Insight

### The BitsAndBytesConfig (grpo_v4.py:77-82):

```python
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,              # Load weights as 4-bit integers
    bnb_4bit_quant_type="nf4",      # Use NormalFloat4 quantization
    bnb_4bit_compute_dtype=torch.float16,  # Compute in fp16 during forward pass
    bnb_4bit_use_double_quant=True,  # Quantize the quantization constants too
)
```

**Line by line:**

**`load_in_4bit=True`**: Store every weight as a 4-bit integer (16 possible values
instead of ~4 billion for float32). Compression ratio: 8x.

**`bnb_4bit_quant_type="nf4"`**: NormalFloat4 is special. Neural network weights
follow a normal distribution (bell curve). NF4 places its 16 quantization levels
at the optimal points on a normal distribution — more levels near zero where
most weights cluster, fewer at the tails. This gives MUCH less quantization
error than uniform 4-bit.

Intuition: imagine you have 16 colored bins and 7.6 billion marbles that mostly
cluster near the center. Uniform binning wastes bins on the empty tails.
NF4 puts more bins in the dense center.

**`bnb_4bit_compute_dtype=torch.float16`**: The weights are STORED as 4-bit, but
during the forward pass they're DEQUANTIZED to float16 for computation. So the
actual matrix multiplications happen in float16 precision. This is crucial —
4-bit arithmetic would be too lossy.

**`bnb_4bit_use_double_quant=True`**: Each group of 64 weights shares a
quantization scale factor (a float32 number). With 7.6B weights, that's
~119M scale factors × 4 bytes = ~475MB just for scales. Double quantization
quantizes THESE scale factors to 8-bit, saving ~300MB.

### Memory budget on T4 (16GB VRAM):

| Component | Memory |
|-----------|--------|
| Model weights (4-bit) | ~3.8 GB |
| Quantization scales (double-quantized) | ~0.2 GB |
| LoRA adapters (float16/32) | ~0.2 GB |
| Optimizer states (paged AdamW) | ~0.4 GB (can page to CPU) |
| Activations + gradients | ~4-8 GB |
| KV cache during generation | ~2-4 GB |
| **Total** | **~11-17 GB** |

This is why gradient checkpointing and paged optimizer matter — they keep
you under 16GB.

## 2.3 LoRA — Low-Rank Adaptation

### The Math (Intuitive)

A full weight matrix W in a transformer layer is [4096 × 4096] = 16.7M params.
Fine-tuning all of them for 6,672 examples would massively overfit.

LoRA says: instead of updating W directly, learn a LOW-RANK update:

    W_new = W_frozen + (B × A)

Where:
- W_frozen: [4096 × 4096] — never changes, stays in 4-bit
- A: [4096 × 16] — 65,536 params (rank 16)
- B: [16 × 4096] — 65,536 params (rank 16)
- B × A: [4096 × 4096] — but only 131,072 free parameters!

So instead of learning 16.7M values, you learn 131K values. That's a 128x reduction.

The "rank" (r=16) is the bottleneck dimension. It's like saying "the change I
want to make to this weight matrix can be described by just 16 independent
directions." For small datasets (6,672 examples), this is enough.

### In your code (grpo_v4.py:95-102):

```python
lora_config = LoraConfig(
    r=16,              # Rank: bottleneck dimension
    lora_alpha=32,     # Scaling factor: actual scaling = alpha/r = 32/16 = 2.0
    lora_dropout=0.05, # 5% dropout on LoRA layers for regularization
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    bias="none",       # Don't add bias terms to LoRA layers
    task_type="CAUSAL_LM",  # Task type hint for PEFT
)
```

**`lora_alpha=32`**: The actual output is:

    W_new = W_frozen + (alpha/r) × (B × A) = W_frozen + 2.0 × (B × A)

The alpha/r ratio controls how much the LoRA update "matters" relative to the
frozen weights. alpha=32 with r=16 gives scaling=2.0 — the LoRA update is
amplified 2x. This is standard — it lets you use a normal learning rate.

**`lora_dropout=0.05`**: During training, 5% of LoRA activations are randomly
zeroed. This prevents the LoRA from overfitting to the training data. Small
value because the dataset is relatively clean.

**`bias="none"`**: LoRA adds parameters to the weight matrices. Adding bias
terms too would increase params for minimal benefit on small datasets.

### Trainable parameter count:

With all 7 target modules across 32 layers:
- Per module: (4096 × 16) + (16 × 4096) = 131,072 params
- Actually it depends on module dimensions:
  - Attention (q,k,v,o): 4 × 131K = 524K per layer
  - MLP (gate, up, down): up/gate are 4096→11008, so rank-16 adapters are
    (4096×16 + 16×11008) + (4096×16 + 16×11008) + (11008×16 + 16×4096)
    ≈ 241K + 241K + 241K = 723K per layer
  - Total per layer: ~1.25M
  - Total across 32 layers: ~40M
  - Plus some overhead: ~87M total reported

87M out of 4.35B loaded params = **2%** trainable.

**Hard interview question:** *"Why rank 16 specifically? How would you choose
this if you were starting fresh?"*

> "It depends on dataset size and task complexity. Rule of thumb: rank should
> be proportional to the log of dataset size and the complexity of the
> distributional shift. For 6,672 examples with a narrow domain shift (general
> code → Python code), rank 8-32 is the sweet spot. Sebastian Raschka ran
> hundreds of experiments and found rank 16 consistently strong for datasets
> under 50k examples. If I had 500k examples, I'd try rank 64. If I had 500
> examples, I'd try rank 4-8."

**Hard interview question:** *"What happens if rank is too high?"*

> "Overfitting. With rank 64 and 6,672 examples, the LoRA has enough capacity
> to memorize the training data. You'd see low training loss but eval loss
> increasing — the model learns to reproduce training examples verbatim
> instead of generalizing. I actually saw hints of this with my SFT V3
> where I used rank 64."

**Hard interview question:** *"What happens if rank is too low?"*

> "Underfitting. The LoRA can't capture enough of the distributional shift.
> Training loss plateaus at a higher value. The model barely changes from base.
> With rank 4, I'd expect maybe 1-2% of the improvement I got with rank 16."

---

# PART 3: SFT — Why It Failed (The Critical Lesson)

## 3.1 What SFT Actually Does

SFT = Supervised Fine-Tuning. You show the model input-output pairs and train
it to maximize the probability of the output given the input.

The loss function is **cross-entropy** on the assistant tokens:

    L = -sum(log P(t_i | t_1, ..., t_{i-1}))

For each token in the assistant's response, you compute: "how probable did the
model think this token was?" Take the log. Negate it. Sum across all tokens.
Minimize this.

### In your code (finetune.py:94-114):

```python
training_args = SFTConfig(
    ...
    dataset_text_field="text",     # <-- Train on the full ChatML conversation
    max_length=config.get("max_seq_length", 2048),
)
```

`dataset_text_field="text"` tells SFTTrainer: "the `text` field in each JSONL
row is the full training example." The trainer tokenizes it, masks the
system+user tokens (so loss is only on assistant tokens), and runs standard
causal LM training.

## 3.2 Why SFT Degraded the Model

### The catastrophic forgetting problem:

Qwen2.5-Coder-7B-Instruct was already trained in three stages:
1. **Pretraining**: Trillions of tokens of code + text → learns language/code patterns
2. **SFT**: Instruction-following examples → learns to follow instructions
3. **RLHF**: Human preference optimization → learns to be helpful, safe, high-quality

When you do SFT again on CodeAlpaca, you're overwriting stage 2 and 3.

**The distribution shift problem:**

CodeAlpaca examples look like:
```
Instruction: "Write a function to add two numbers"
Output: "def add(a, b):\n    return a + b"
```

This is MUCH simpler than what the model learned to produce during its original
training. The model learned sophisticated patterns:
- Proper error handling
- Type hints
- Edge cases
- Multi-function solutions

SFT on CodeAlpaca teaches it: "just output 3-5 lines of simple code."
The model's distribution shifts toward these simpler outputs.

### Evidence from your results:

| Version | HumanEval | What happened |
|---------|-----------|---------------|
| Base | 86.6% (142/164) | Model's original capability |
| V1 SFT | ~68% | Massive degradation |
| V2 SFT | ~70% | Still bad |
| V3 SFT (completion format, rank 64) | 74.4% | Less bad, but still -12% |

V3 was less bad because:
1. Completion format (just the code body, not instruction format) was closer
   to what HumanEval expects
2. But rank 64 meant more capacity → more overwriting of base knowledge

### The specific bugs you hit (PROGRESS.md):

> "Bugs hit: `raw.strip()` removed leading 4-space indent → `return` at
> module level → SyntaxError"

This is a concrete example of distribution shift. CodeAlpaca outputs don't
have leading indentation (they're standalone). `raw.strip()` removes all
leading whitespace. But HumanEval expects the model to continue a function
body that needs 4-space indentation. The SFT model learned "outputs don't
start with spaces" and broke the indentation.

**Hard interview question:** *"Couldn't you fix catastrophic forgetting with
a smaller learning rate or fewer epochs?"*

> "You can reduce it but not eliminate it. Lower LR = slower distribution
> shift, but any SFT will shift the distribution toward the training data.
> The fundamental issue is that cross-entropy loss treats every token
> equally — it shifts the ENTIRE output distribution, not just the parts
> you want to change. Even with 1 epoch and LR=1e-5, I'd expect some
> degradation on tasks not represented in CodeAlpaca."

**Hard interview question:** *"What about mixing in replay data from the
original training set?"*

> "That's a real solution — mix CodeAlpaca data with samples from the model's
> original training distribution to prevent forgetting. But I don't have
> Qwen's original instruction data. You can approximate it by having the
> base model generate synthetic data, but that adds complexity. GRPO was
> simpler and more principled — it doesn't shift the distribution at all,
> just reinforces the good parts."

---

# PART 4: GRPO — The Core Innovation (Deep Dive)

## 4.1 What Problem Does GRPO Solve?

You want the model to generate code that passes tests. You have a reward
function: run the code, 1.0 if it passes, 0.0 if it fails.

The challenge: you can't differentiate through code execution. You can't
compute d(reward)/d(weights). The reward is a black box.

Policy gradient methods solve this by:
1. Sample outputs from the current model
2. Score them with the reward function
3. Increase probability of high-reward outputs
4. Decrease probability of low-reward outputs

## 4.2 GRPO vs PPO vs DPO — The Landscape

### PPO (Proximal Policy Optimization):

```
PPO needs:
1. Policy model (the LLM you're training)
2. Reference model (frozen copy of the original LLM)
3. Value model / Critic (a SEPARATE model that predicts expected reward)
4. Reward model (scores outputs)

Memory: 4 models (even with sharing, ~2-3x overhead)
Complexity: Train critic alongside policy, GAE advantage estimation
```

### DPO (Direct Preference Optimization):

```
DPO needs:
1. Policy model
2. Reference model
3. Paired preference data: (prompt, chosen_response, rejected_response)

Memory: 2 models
Complexity: Simpler, but needs preference data you don't have
```

### GRPO (Group Relative Policy Optimization):

```
GRPO needs:
1. Policy model
2. Reference model (or use the policy itself)
3. A reward function (ANY function that scores outputs)

Memory: ~1.5-2x (no separate critic)
Complexity: Simplest of the three
```

GRPO's key innovation: **it uses the GROUP of generated outputs to compute
advantages**, eliminating the need for a learned critic.

## 4.3 The GRPO Algorithm (Step by Step)

For each prompt in the training batch:

### Step 1: Generate N completions

For a prompt like "Write a function to find prime numbers", generate N=2
different completions using sampling (temperature=0.8):

```
Completion A: def is_prime(n):
                 if n < 2: return False
                 for i in range(2, int(n**0.5)+1):
                     if n % i == 0: return False
                 return True

Completion B: def is_prime(n):
                 return n > 1  # wrong!
```

### Step 2: Score each completion with the reward function

Run each through `reward_fn`:
```
Reward A = 1.0 (passes tests)
Reward B = 0.0 (fails tests)
```

### Step 3: Compute group-relative advantages

Instead of using a critic to estimate "how good is this?", GRPO compares
each completion to the group:

```
Group mean = (1.0 + 0.0) / 2 = 0.5
Group std  = sqrt(((1.0-0.5)^2 + (0.0-0.5)^2) / 2) = 0.5

Advantage A = (1.0 - 0.5) / 0.5 = +1.0  (better than average)
Advantage B = (0.0 - 0.5) / 0.5 = -1.0  (worse than average)
```

This is just z-score normalization. The advantage tells you: "how much better
or worse was this completion compared to the others for the same prompt?"

### Step 4: Policy gradient update

For each token in Completion A (advantage=+1.0):
- Increase the log-probability of that token
- Scaled by the advantage (+1.0)

For each token in Completion B (advantage=-1.0):
- Decrease the log-probability of that token
- Scaled by the advantage (-1.0)

The gradient for each token is approximately:

    gradient ≈ advantage × d(log P(token))/d(weights)

### Step 5: KL penalty

Additionally, penalize the model for drifting too far from the reference:

    total_loss = -advantage × log P(token) + beta × KL(policy || reference)

KL divergence measures how different the current model's distribution is from
the reference model. beta=0.05 controls how much this penalty matters.

**Intuition:** The advantage says "go this way" and the KL penalty says
"but don't go too far." This is why GRPO preserves base capabilities —
the KL penalty prevents catastrophic forgetting.

## 4.4 Your GRPO Config, Line by Line

### V4 (grpo_v4.py:104-122):

```python
grpo_config = GRPOConfig(
    output_dir=OUTPUT_DIR,
    num_generations=2,           # Generate 2 completions per prompt
```

**`num_generations=2`**: Minimum for group comparison. With N=2, one completion
passes and one fails → clear signal. With N=1, you can't compute group
advantage. More N = better advantage estimates but more memory/time.

On T4 with 16GB: N=2 is the max. Papers use N=4-8 on A100s.

```python
    generation_kwargs={
        "max_new_tokens": 128,   # V4: short completions (speed)
        "do_sample": True,       # Must sample (not greedy) for diversity
        "temperature": 0.8,      # Enough randomness for different outputs
    },
```

**`max_new_tokens=128`**: V4 limited to 128 tokens. Most simple MBPP functions
fit in this. V5 increased to 256 for longer/harder problems.

**`do_sample=True, temperature=0.8`**: CRITICAL. If you use greedy decoding
(temp=0), both completions would be identical → advantage = 0 for all tokens
→ no learning. You NEED diversity to get different rewards.

Temperature 0.8 = enough randomness to get different solutions, not so much
that everything is garbage.

```python
    learning_rate=5e-6,          # 40x smaller than SFT (2e-4)
```

**`learning_rate=5e-6`**: RL is much more sensitive to learning rate than SFT.
Too high → model collapses (forgets everything). Too low → no learning.
5e-6 is conservative and safe.

Why 40x smaller than SFT's 2e-4? SFT has a dense, stable gradient (every
token has a ground-truth target). GRPO has a noisy gradient (estimated from
only 2 samples). Noisy gradients + high LR = instability.

```python
    per_device_train_batch_size=1,    # One prompt at a time (memory)
    gradient_accumulation_steps=4,    # Effective batch = 4 prompts
```

**Effective batch size = 1 × 4 = 4 prompts.** With 2 generations each,
that's 8 completions per gradient update. Small but sufficient for GRPO
because the advantage is computed per-prompt, not per-batch.

```python
    num_train_epochs=1,          # One pass through the data
    fp16=True,                   # Mixed precision training
    gradient_checkpointing=False,  # Disabled: causes warnings with LoRA
```

**`gradient_checkpointing=False`**: In SFT, gradient checkpointing was
critical for memory. In GRPO V4, it caused PyTorch warnings about
`requires_grad` not being set correctly on re-computed activations
(a known bug with PEFT + GRPOTrainer). Disabling it worked because
GRPO's memory footprint is different — shorter sequences (128 tokens)
and batch size 1 mean activations are smaller.

```python
    save_strategy="epoch",
    logging_steps=5,
    beta=0.05,                   # KL penalty coefficient
```

**`beta=0.05`**: The KL penalty weight. This is the single most important
hyperparameter in GRPO.

- beta=0: No KL penalty. Model can drift anywhere. Risk of catastrophic
  forgetting and reward hacking.
- beta=0.01: Very loose. Model learns fast but might forget base capabilities.
- beta=0.05: Moderate. Good balance for your use case.
- beta=0.1: Conservative. Model changes slowly.
- beta=0.5: Very conservative. Model barely changes.

The DeepSeek-R1 paper used beta=0.04. Your 0.05 is very close. This is
a well-validated range.

```python
    lr_scheduler_type="cosine",  # Cosine decay
    warmup_ratio=0.05,           # 5% warmup
    remove_unused_columns=False, # Keep test_cases column for reward fn
    dataloader_num_workers=0,    # Single-threaded (simpler)
    report_to="none",            # No W&B/MLflow logging
)
```

**`remove_unused_columns=False`**: By default, HF trainers drop columns
that aren't model inputs. But your dataset has a `test_cases` column that
the reward function needs. This flag keeps it.

## 4.5 The Reward Function Deep Dive

### grpo_v4.py:35-53:

```python
def run_code_reward(completions: list[str], test_cases: list[str], **kwargs):
    rewards = []
    for completion, tests in zip(completions, test_cases):
        code = extract_code(completion)          # Strip markdown fences
        program = code + "\n\n" + tests          # Append test assertions
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(program)
            fname = f.name
        try:
            result = subprocess.run(
                ["python3", fname],
                capture_output=True,
                timeout=10,                      # Kill after 10 seconds
                text=True
            )
            reward = 1.0 if result.returncode == 0 else 0.0
        except Exception:
            reward = 0.0                         # Timeout or crash = 0
        finally:
            Path(fname).unlink(missing_ok=True)  # Clean up temp file
        rewards.append(reward)
    return rewards
```

### What could go wrong:

1. **Security**: This runs arbitrary generated code with no sandboxing.
   The model could generate `import os; os.system("rm -rf /")`. On a
   training VM, this is acceptable risk. In production, you'd use Docker
   containers, seccomp, or nsjail.

2. **Timeout gaming**: A model could learn to generate infinite loops
   (always gets 0 reward but never crashes). The 10-second timeout prevents
   this from blocking training, but the model still "wastes" a generation.

3. **Reward hacking**: The model could learn to generate code that passes
   tests in degenerate ways (e.g., hardcoding return values). MBPP's test
   assertions make this hard because there are usually 3+ assertions with
   different inputs. But it's theoretically possible.

4. **Non-deterministic rewards**: If the generated code uses `random`,
   the reward might differ across runs. This adds noise to the advantage
   estimation. Not a problem with MBPP since the problems are deterministic.

**Hard interview question:** *"Your reward function runs untrusted generated
code. How would you make this production-safe?"*

> "Three layers of isolation:
> 1. Run code in a Docker container with no network, read-only filesystem,
>    and memory/CPU limits
> 2. Use seccomp or nsjail to restrict syscalls (no file I/O, no network,
>    no process spawning)
> 3. Use cgroups to enforce memory limits (kill if >256MB)
> On a training VM with no sensitive data, subprocess with timeout is
> acceptable. In production, I'd use something like E2B or Modal sandboxes."

**Hard interview question:** *"What if the reward is too sparse? Most
completions get 0?"*

> "That's the cold start problem. If the model can't solve any MBPP problems,
> all rewards are 0, all advantages are 0, no learning happens. This is why
> I started from Qwen2.5-Coder-7B-Instruct — it already solves ~85% of MBPP.
> So most prompts have at least one passing completion, giving useful signal.
> If I were starting from a base model (not instruct), I'd need to do SFT
> first to get it to a reasonable starting point, then switch to GRPO."

## 4.6 V4 → V5: Why Compounding Works

### V4: 150 MBPP examples → 86.6% (matched base)
### V5: 374 MBPP examples from V4 checkpoint → 87.8% (beat base)

V5 starts from V4's weights, not from the base model. This is like a student
who already knows calculus taking a harder math course — they can learn from
problems they'd have struggled with before.

### grpo_v5.py differences from V4:

```python
BASE_MODEL = "outputs/codetune-7b-v4"  # Start from V4, not Qwen base
MAX_EXAMPLES = 374                      # 2.5x more training data
# generation_kwargs: max_new_tokens=256 (vs 128 in V4)
```

**Why 374 examples?** MBPP has ~500 training problems. V4 used the first 150.
V5 uses 374 — more of the dataset, including harder problems.

**Why 256 max tokens?** V4's 128-token limit truncated some longer solutions.
V5 allows longer generations, letting the model attempt problems that need
more code.

**Why start from V4?** V4 at 86.6% already solves most easy/medium problems
consistently. Its reward signal on those is mostly 1.0 → advantage ≈ 0 →
no learning. But V5's larger dataset includes harder problems where V4 is
INCONSISTENT (sometimes 1.0, sometimes 0.0). These are exactly the problems
where GRPO can learn — the variance in rewards gives non-zero advantages.

**The result:** V5's 87.8% means it solved 2 more HumanEval problems than
base. That's 2 out of 22 that the base model failed — a 9% reduction in
failures. Not huge in absolute terms, but statistically significant and
achieved with <3 hours of training and $2 of compute.

**Hard interview question:** *"Only +1.2% improvement seems small. Was it
worth it?"*

> "Three points:
> 1. The base model is already very strong (86.6%). Improving strong models
>    is MUCH harder than improving weak ones. The Posterior-GRPO paper
>    reported +13.9% relative improvement on the same model family — our
>    +1.4% relative is in the same direction, less because we used less
>    compute and data.
> 2. The real value of CodeTune isn't +1.2% on HumanEval. It's the pipeline
>    and the learning. I can now take any model, any dataset, any reward
>    function, and run this pipeline.
> 3. Plus I showed that SFT *hurts* instruct models — that's the more
>    important finding. Knowing what NOT to do is as valuable as knowing
>    what to do."

---

# PART 5: EVALUATION — Deep Dive Into Each Suite

## 5.1 HumanEval (eval/suites/humaneval.py)

### What is HumanEval?

164 hand-written Python programming problems from OpenAI. Each has:
- A function signature + docstring (the prompt)
- A test harness (hidden from the model)
- An entry point (function name)

Example:
```python
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """Check if in given list of numbers, are any two numbers closer to
    each other than given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
```

### How your eval works (humaneval.py:85-163):

1. Load problems from `human_eval` or `evalplus` package
2. For each problem:
   a. Format the prompt as a chat instruction
   b. Generate one completion (temperature=0, greedy)
   c. Extract the code (strip markdown fences, stop at explanations)
   d. If model didn't include the function signature, prepend it
   e. Run: `code + test_harness + "check(entry_point)"` in a subprocess
   f. Record pass/fail

### The code extraction logic (humaneval.py:34-58):

```python
def extract_code(completion: str) -> str:
    # Strip markdown fences
    code = completion.strip()
    if "```python" in code:
        match = re.search(r"```python\n(.*?)```", code, re.DOTALL)
        ...
    # Stop at explanations
    lines = code.split("\n")
    result = []
    in_function = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            in_function = True
        if in_function and result and not line.startswith((" ", "\t", "def "...)):
            if stripped and not stripped.startswith(("#", "import ")):
                break   # Stop when we hit unindented non-code text
        result.append(line)
    return "\n".join(result)
```

**Why is this necessary?** Instruct models often add explanations after the
code: "This function works by..." If you include this text, Python will try
to parse it and throw SyntaxError. The extraction logic stops at the first
unindented, non-code line.

**What could go wrong:**
- Model outputs code without markdown fences but with explanation → extraction
  might include explanation text
- Model outputs multiple functions → extraction might miss the second one
- Model outputs class with methods → the "stop at unindented" heuristic
  might stop too early

These are real eval engineering problems. HumanEval pass@1 numbers are
sensitive to your extraction logic. Different extraction = different score.

### The "prepend signature" fallback (humaneval.py:135-136):

```python
if f"def {entry_point}" not in code:
    code = prompt_stub + "\n" + code
```

If the model outputs just the function body (no `def` line), prepend the
original prompt which contains the signature. This handles the case where
the model assumes you want a continuation, not a standalone function.

**Hard interview question:** *"How sensitive is your HumanEval score to the
extraction logic? Could a different extraction give you 90%?"*

> "Very sensitive. I've seen 2-5% swings depending on extraction heuristics.
> That's why I also do MBPP and structural evals — triangulating across
> multiple benchmarks reduces the impact of any one eval's quirks. For
> production eval, I'd use EvalPlus which has a more robust extraction
> pipeline and additional tests (HumanEval+ has 80x more tests per problem)."

## 5.2 MBPP (eval/suites/mbpp.py)

### Differences from HumanEval:

- 427 problems (sanitized subset) vs 164
- Problems are described in natural language (not function stubs)
- Tests are simple assert statements (not harness functions)
- Broader range: string manipulation, math, list operations, etc.

### In your code (mbpp.py:54-127):

Same pattern as HumanEval but simpler:
1. Format problem text as instruction
2. Generate completion
3. Strip markdown fences
4. Run `code + "\n".join(test_assertions)` in subprocess
5. Record pass/fail

**Why both HumanEval AND MBPP?**

HumanEval problems have strong hints (function signature + docstring with
examples). MBPP gives only a natural language description. A model might
score high on HumanEval (because the signature constrains the solution)
but low on MBPP (because it has to figure out the function name, parameters,
and return type from scratch).

## 5.3 Structural Eval (eval/suites/structural.py)

### What unique signal does this provide?

HumanEval and MBPP test: "does the code work?" But code can work while:
- Importing modules that don't exist (`from utils.helpers import magic`)
- Using API methods with wrong names (`requests.fetch()` instead of `requests.get()`)
- Missing critical imports (code works in test because the test imports it)

Structural eval catches these.

### The 20 hand-crafted problems (structural.py:21-142):

Each problem specifies:
- `prompt`: What to generate
- `expected_imports`: Which modules should be imported
- `expected_symbols`: Which specific APIs should be used

Example:
```python
{
    "id": "struct_002",
    "prompt": "Write a function that makes an HTTP GET request and returns JSON.",
    "expected_imports": ["requests"],
    "expected_symbols": ["requests.get"],
}
```

### The three checkers:

**1. check_imports (structural.py:161-173):**
```python
def check_imports(code: str, expected_imports: list[str]) -> list[str]:
    missing = []
    for imp in expected_imports:
        patterns = [f"import {imp}", f"from {imp} import", f"from {imp}."]
        if not any(p in code for p in patterns):
            missing.append(imp)
    return missing
```

Simple string matching. Checks for `import requests`, `from requests import`,
or `from requests.` patterns. Not AST-based — catches both standard and
non-standard import styles.

**2. check_symbols (structural.py:176-185):**
```python
def check_symbols(code: str, expected_symbols: list[str]) -> list[str]:
    missing = []
    for sym in expected_symbols:
        parts = sym.split(".")
        short_form = parts[-1]  # "get" from "requests.get"
        if sym not in code and short_form not in code:
            missing.append(sym)
    return missing
```

Checks for `requests.get` OR just `get` (in case of `from requests import get`).

**3. check_hallucinated_imports (structural.py:188-228):**
```python
def check_hallucinated_imports(code: str) -> list[str]:
    hallucinated = []
    tree = ast.parse(code)
    known_modules = {"os", "sys", "json", "csv", "re", ...}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_module = alias.name.split(".")[0]
                if top_module not in known_modules:
                    try:
                        importlib.import_module(top_module)
                    except ImportError:
                        hallucinated.append(alias.name)
    return hallucinated
```

This is the most sophisticated check. It:
1. Parses the code into an AST
2. Walks every node looking for Import and ImportFrom nodes
3. Checks if the top-level module is in a known set (~50 stdlib + common packages)
4. For unknown modules, tries to actually import them
5. If ImportError → it's hallucinated

**Why AST instead of regex?** Regex can't distinguish between `import os`
in a comment vs actual code. AST only sees actual import statements.

### The GroundTruth integration (structural.py:231-261):

```python
def try_gt_validation(code: str, gt_path: str | None) -> dict | None:
    if not gt_path:
        return None
    try:
        from groundtruth.core.validator import Validator
        from groundtruth.core.store import SymbolStore

        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "generated.py"
            code_file.write_text(code, encoding="utf-8")
            store = SymbolStore(Path(tmpdir) / ".gt.db")
            validator = Validator(store)
            result = validator.validate_file(str(code_file))
            return {"gt_available": True, "errors": [...], "valid": ...}
    except Exception:
        return None  # Graceful degradation if GT not installed
```

This connects your two projects. GroundTruth's `Validator` does deeper
analysis than AST — it builds a symbol database (via LSP), resolves imports,
and checks that every referenced symbol actually exists in the target module.

**Hard interview question:** *"Your structural problems are hand-crafted. How
do you know 20 problems is enough?"*

> "It's not enough for statistical significance on its own — 20 problems gives
> wide confidence intervals. But structural eval isn't measuring a single number;
> it's measuring three specific failure modes: missing imports, missing symbols,
> hallucinated imports. Each problem is designed to test a specific real-world
> API pattern (csv, requests, asyncio, etc.). The pass rate (75%) and zero
> hallucinations tell me the model generates structurally valid code. For a
> production eval suite, I'd expand to 100+ problems covering more of the
> stdlib and popular packages."

## 5.4 Custom Code Quality (eval/suites/custom.py)

### The six AST-based checkers:

**1. check_contains_type_hints (custom.py:33-50):**
```python
def check_contains_type_hints(code: str) -> bool:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            annotated = sum(1 for arg in args.args
                          if arg.annotation is not None and arg.arg != "self")
            non_self_args = sum(1 for arg in args.args if arg.arg != "self")
            if non_self_args > 0 and annotated > 0:
                return True
    return False
```

Walks the AST, finds function definitions, checks if ANY non-self argument
has a type annotation. Returns True if at least one function has at least
one typed parameter.

**2. check_has_return_type (custom.py:53-63):** Checks `node.returns is not None`.

**3. check_has_docstring (custom.py:66-80):** Checks if the first statement in
a function body is a string literal (the standard docstring pattern).

**4. check_handles_edge_cases (custom.py:83-91):** Pattern matching — looks for
`if not`, `is None`, `ValueError`, `IndexError`, etc. Not AST-based, just
string matching. This is the weakest checker (could match comments).

**5. check_no_bare_except (custom.py:94-103):** AST-based. Finds ExceptHandler
nodes where `node.type is None` (bare `except:` without specifying the
exception type). This is a real code quality issue — bare excepts swallow
all exceptions including KeyboardInterrupt.

**6. check_uses_list_comprehension (custom.py:106-115):** Checks for ListComp,
SetComp, DictComp, or GeneratorExp nodes. Pythonic code uses comprehensions
instead of manual loops with append.

### Results breakdown (from PROGRESS.md):

| Category | Score | What it means |
|----------|-------|---------------|
| Docstrings | 83% | Model usually adds docstrings when asked |
| Error handling | 78% | Model handles edge cases most of the time |
| Pythonic style | 80% | Model uses comprehensions and modern patterns |
| Type hints | ~60% | Model often skips type annotations |
| Overall | 69.8% | Room for improvement on code quality |

**Hard interview question:** *"These quality checks are proxy metrics. How do
you know they correlate with actual code quality?"*

> "They're necessary but not sufficient conditions. Having type hints doesn't
> make code good, but production Python code SHOULD have type hints. Same for
> docstrings and error handling. I treat these as a quality floor — if the
> model consistently skips type hints, that's a signal even if the code works.
> For a deeper quality eval, I'd add: cyclomatic complexity, function length,
> naming conventions, and actually run mypy/ruff on the generated code."

---

# PART 6: SERVING & BENCHMARKING — Deep Dive

## 6.1 Quantization Methods

### GPTQ (serve/quantize.py:13-43):

**How it works:**
1. Load the full-precision model
2. Feed 128 calibration examples through it
3. For each layer, solve: "what's the best way to round these float16 weights
   to INT8 (or INT4) such that the layer's output changes the least?"
4. This is an optimization problem solved layer-by-layer (sequentially)

**Key detail — calibration data (quantize.py:35-36):**
```python
calibration_ds = load_dataset("json", data_files="data/processed/train.jsonl")
calibration_data = [tokenizer(ex["text"], ...) for ex in calibration_ds.select(range(128))]
```

You use YOUR training data as calibration. The quantizer optimizes rounding
decisions based on what activations look like for code tasks. If you used
generic text as calibration, the quantized model might be worse at code.

### AWQ (serve/quantize.py:46-68):

**How it's different from GPTQ:**
AWQ observes that ~1% of weights are "salient" — they correspond to
large-magnitude activations that carry most of the information. AWQ
protects these salient weights during quantization by scaling them up
before quantizing and scaling the corresponding activations down.

Result: AWQ at INT4 often matches GPTQ at INT8 in quality, while being
half the size.

### GGUF (serve/quantize.py:71-97):

**How it's different:**
GGUF is not a quantization METHOD — it's a FILE FORMAT. The actual
quantization types (Q4_K_M, Q8_0, etc.) use different algorithms:
- Q8_0: Simple round-to-nearest 8-bit (fast, high quality)
- Q4_K_M: K-quants with mixed precision (important layers get more bits)
- Q4_0: Simple 4-bit (fast, lower quality)

The "K" in Q4_K_M means "K-quants" — a method that assigns more bits to
layers that are more sensitive to quantization. "M" means medium (vs S/L).

## 6.2 Serving Frameworks

### vLLM (serve/deploy_vllm.py):

**Key innovation: PagedAttention**

During generation, each token needs a "KV cache" — the key and value vectors
for all previous tokens. For a 7B model generating 4096 tokens:

    KV cache per request ≈ 2 × 32 layers × 32 heads × 128 dim × 4096 tokens × 2 bytes
                         ≈ 2 GB per request

With 16GB VRAM, you can only serve ~3-4 concurrent requests!

PagedAttention solves this by treating KV cache like virtual memory:
- Divide KV cache into fixed-size "pages" (blocks)
- Allocate pages on-demand (not all 4096 upfront)
- Share pages across requests with the same prefix
- Free pages as soon as a request completes

Result: 2-4x higher throughput at the same memory.

**Your config (deploy_vllm.py:22-29):**
```python
cmd = [
    "--model", model,
    "--port", str(port),
    "--dtype", dtype,
    "--max-model-len", str(max_model_len),      # 4096 context window
    "--gpu-memory-utilization", str(0.90),       # Use 90% of VRAM
    "--max-num-seqs", str(max_num_seqs),         # Up to 64 concurrent requests
]
```

`gpu-memory-utilization=0.90`: Leave 10% VRAM for other operations.
`max-num-seqs=64`: Maximum concurrent requests in the batch.

### SGLang:

**Key innovation: RadixAttention**

Stores KV caches in a radix tree (trie). If two requests share the same
prefix (e.g., same system prompt), their KV caches are shared. This is
particularly good for:
- Chat applications (shared conversation history)
- Constrained decoding (shared grammar)
- Batch eval (same instruction template)

### llama.cpp:

**Key innovation: C++ inference with no Python**

- Runs on CPU or GPU (CUDA, Metal, Vulkan)
- No Python overhead — direct C++ inference
- GGUF format allows quantization-specific optimizations
- `-ngl 99` offloads all 99 layers to GPU (if you have fewer, it offloads what fits)

## 6.3 The Benchmark Runner (bench/benchmark.py)

### Async streaming client (benchmark.py:17-85):

```python
async def send_request(session, url, model, prompt, ...):
    payload = {"model": model, "prompt": prompt, "stream": True, ...}

    start = time.perf_counter()
    ttft = None
    tokens_generated = 0

    async with session.post(f"{url}/completions", json=payload) as resp:
        async for line in resp.content:
            # Parse SSE (Server-Sent Events) stream
            decoded = line.decode("utf-8").strip()
            if not decoded.startswith("data: "): continue
            data_str = decoded[6:]
            if data_str == "[DONE]": break

            if ttft is None:
                ttft = (time.perf_counter() - start) * 1000  # First token!

            tokens_generated += 1
```

**Server-Sent Events (SSE):** vLLM/SGLang stream tokens as SSE events.
Each event is a line starting with `data: ` containing JSON. The model
generates one token, the server sends it immediately, and the client
receives it before the next token is generated.

**TTFT (Time to First Token):** Measured from request start to first
`data: ` event. This captures:
- Network latency
- Prompt tokenization
- KV cache computation (the "prefill" phase)
- First token sampling

This is the most important latency metric for user-facing applications
because it's the time the user stares at a blank screen.

**TPOT (Time Per Output Token):** After the first token, how long between
each subsequent token:
```python
tpot = (total_time - ttft) / max(tokens_generated - 1, 1)
```

This captures the "decode" phase. Each new token requires one model forward
pass. TPOT is mostly constant and represents the model's raw generation speed.

**Throughput (tokens/sec):**
```python
tps = tokens_generated / (total_time / 1000)
```

Total tokens divided by total time. This includes both prefill and decode.

### Batch testing (benchmark.py:88-130):

```python
for bs in batch_sizes:   # [1, 4, 16]
    for batch_start in range(0, num_requests, batch_size):
        batch = prompt_cycle[batch_start:batch_start + batch_size]
        tasks = [send_request(...) for p in batch]
        batch_results = await asyncio.gather(*tasks)  # Concurrent!
```

At batch_size=1: One request at a time. Measures per-request latency.
At batch_size=4: Four concurrent requests. Tests how well the framework
  handles concurrent batch scheduling.
At batch_size=16: Sixteen concurrent. Tests throughput under load.

**Why this matters:** A framework might be fast for single requests but slow
when batching (poor scheduler), or vice versa. The 3x batch comparison shows
the scaling characteristics.

### The analyze module (bench/analyze.py):

**Percentile computation:**
```python
def percentile(values, p):
    return float(np.percentile(values, p))
```

p50 = median (typical experience). p99 = worst 1% (tail latency).

For production: you care about p99 because ONE slow request can block a user
session. A system with p50=50ms but p99=5000ms is worse than one with
p50=100ms and p99=200ms.

**Cost calculation (analyze.py:47-52):**
```python
def compute_cost(throughput_tps, gpu_hourly_rate=3.67):
    seconds_per_1m_tokens = 1_000_000 / throughput_tps
    hours = seconds_per_1m_tokens / 3600
    return round(hours * gpu_hourly_rate, 2)
```

Example: 100 tokens/sec on a $3.67/hr A100:
- 1M tokens / 100 tps = 10,000 seconds = 2.78 hours
- 2.78 × $3.67 = **$10.19 per 1M tokens**

For comparison: OpenAI charges ~$15/1M output tokens for GPT-4. So if your
model is competitive quality-wise, self-hosting saves money at scale.

---

# PART 7: THE HARDEST INTERVIEW QUESTIONS

These are the questions that would stump most candidates. Having answers
ready for these will set you apart.

## On Training:

**Q: "If you had an A100 instead of T4, what would you do differently?"**

> "Four things:
> 1. num_generations=8 instead of 2 — better advantage estimates
> 2. Full bfloat16 instead of 4-bit — higher quality gradients, I might not
>    even need QLoRA
> 3. Longer training (3-5 epochs instead of 1) with more data
> 4. Bigger context (4096 tokens) for harder problems
> Expected result: 90%+ on HumanEval based on what the GRPO papers show."

**Q: "How would you scale this to a 70B model?"**

> "DeepSpeed ZeRO-3 or FSDP to shard the model across multiple GPUs.
> Still use QLoRA (now essential, not optional — 70B in fp16 = 140GB).
> 4x A100-80GB would work. The GRPO loop stays the same, just more
> memory-efficient distributed training."

**Q: "Your reward function is binary (0/1). What about partial credit?"**

> "You could do: execution reward (0/1) + style reward (0-1 from the custom
> eval checks) + structural reward (0-1 from the structural checks). Weight
> them: 0.7 × execution + 0.2 × style + 0.1 × structural. The risk is reward
> hacking — the model optimizes whatever is easiest to maximize. Binary
> execution reward is hack-proof. Composite rewards need careful tuning."

**Q: "What happens if you GRPO a model that can't solve ANY problems?"**

> "All rewards are 0.0. Group mean = 0. Group std = 0 (or epsilon). All
> advantages are 0. No gradients. No learning. This is why you need a
> warm start — the base model must already be somewhat capable. In my case,
> Qwen2.5-Coder-7B already solves ~85% of MBPP, giving plenty of signal."

**Q: "Could you use GRPO to align a model for safety? Not just code execution?"**

> "Yes, if you can define a reward function. For safety: use a classifier
> that scores responses as safe/unsafe. For helpfulness: use a preference
> model. The advantage of GRPO over DPO is you don't need paired data —
> just a scoring function. DeepSeek-R1 used GRPO for reasoning, not just
> code. The key challenge is reward quality — a noisy safety classifier
> would teach the model to be evasive rather than genuinely safe."

## On Evaluation:

**Q: "HumanEval is saturating — models are hitting 95%+. What's next?"**

> "Three directions:
> 1. EvalPlus (HumanEval+ and MBPP+) — 80x more tests per problem, catches
>    edge cases that basic HumanEval misses
> 2. SWE-bench — real GitHub issues requiring multi-file changes. Much harder
>    and more realistic than isolated function generation.
> 3. LiveCodeBench — continuously updated with new problems from competitive
>    programming contests, preventing contamination."

**Q: "How do you know your model didn't just memorize MBPP since you trained on it?"**

> "Valid concern. I trained on MBPP TRAIN split but evaluated on MBPP
> TEST split (sanitized). These are non-overlapping. Additionally, the
> HumanEval improvement (+1.2%) serves as an out-of-distribution validation —
> the model never saw HumanEval problems during GRPO, so improvement there
> indicates genuine capability gain, not memorization."

**Q: "Your eval runs each test in a subprocess. What about evaluation speed?"**

> "164 HumanEval problems × ~5 seconds each ≈ 15 minutes. For MBPP (427
> problems), ~35 minutes. This is dominated by model generation time, not
> test execution. To speed up: batch generation (generate all completions
> first, then test), or use vLLM for inference instead of raw HF generate.
> With vLLM, I could cut eval time to ~5 minutes."

## On Serving:

**Q: "A customer says vLLM is slower than their raw PyTorch inference.
What happened?"**

> "Three likely causes:
> 1. Single request, short prompt — vLLM's overhead (scheduler, PagedAttention
>    bookkeeping) dominates when there's no batching benefit. Raw PyTorch is
>    faster for batch_size=1.
> 2. They're not using continuous batching — vLLM shines when requests arrive
>    asynchronously and the scheduler can batch them. Synchronous use misses this.
> 3. Model doesn't fit optimally — if they're using tensor parallelism across
>    GPUs for a small model, the communication overhead hurts more than the
>    parallelism helps."

**Q: "How would you choose between vLLM, SGLang, and TGI for production?"**

> "Depends on the workload:
> - vLLM: Best default choice. Highest throughput for diverse, concurrent requests.
>   Good OpenAI-compatible API. Largest community.
> - SGLang: Better if you need structured generation (JSON mode, grammar
>   constraints) or have lots of shared prefixes (RadixAttention saves memory).
> - TGI: If you're in the HuggingFace ecosystem and need enterprise support.
> - llama.cpp: If you need CPU inference, edge deployment, or GGUF format.
> I'd start with vLLM and only switch if I hit a specific limitation."

## On Architecture & Design:

**Q: "If you were building this pipeline as a product (like Fireworks),
what would you change?"**

> "Five things:
> 1. Dataset validation layer — check for PII, duplicates, format errors
>    before training starts. Most customer issues are data quality.
> 2. Experiment tracking — log every run to W&B or MLflow with full
>    hyperparams and metrics. I used report_to='none' for simplicity.
> 3. Model registry — version every checkpoint with metadata (what data,
>    what config, what eval scores). I just saved to directories.
> 4. Sandboxed code execution — Docker/nsjail for the reward function.
>    Can't run customer-generated code in bare subprocess.
> 5. A/B testing framework — serve base and fine-tuned models behind a
>    router, collect user preference data for future training."

**Q: "Why didn't you use Axolotl, LLaMA-Factory, or another training framework?"**

> "I wanted to understand every line. Frameworks abstract away the decisions —
> tokenizer setup, chat template formatting, LoRA target selection, reward
> function design. For a product role, understanding these details matters
> more than using a framework. In production, I'd probably use a framework
> for SFT (fewer footguns) but keep GRPO custom (because the reward function
> is domain-specific and you want full control)."

---

# PART 8: CONCEPT CONNECTIONS MAP

Understanding how every piece connects:

```
CodeAlpaca-20k
    │
    ▼
prepare_dataset.py ─── filter Python, format ChatML, split 90/10
    │
    ▼
train.jsonl + eval.jsonl
    │
    ├──▶ finetune.py (SFT) ──▶ FAILED: -18% HumanEval
    │         │
    │         └── WHY: cross-entropy loss shifts entire distribution
    │                   away from RLHF alignment = catastrophic forgetting
    │
    ▼
Qwen2.5-Coder-7B-Instruct (base model, unchanged)
    │
    ▼
grpo_v4.py ────── 150 MBPP problems, code execution reward
    │                  reward_fn: generate → run → pass/fail → 1.0/0.0
    │                  GRPO advantage: z-score within group of 2 completions
    │                  KL penalty (beta=0.05) prevents forgetting
    │                  34 minutes on T4
    │
    ▼
codetune-7b-v4 (86.6% HumanEval = matched base)
    │
    ▼
grpo_v5.py ────── 374 MBPP problems, from V4 checkpoint
    │                  Harder problems now learnable because V4 is stronger
    │                  256 max tokens (vs 128) for longer solutions
    │                  2 hours on T4
    │
    ▼
codetune-7b-v5 (87.8% HumanEval = beat base by 1.2%)
    │
    ├──▶ eval/runner.py ────── orchestrates 4 eval suites:
    │         │
    │         ├── humaneval.py ── 164 problems, pass@1, subprocess execution
    │         ├── mbpp.py ─────── 427 problems, same approach
    │         ├── structural.py ─ 20 problems, AST-based import/symbol checking
    │         │       └── optional GroundTruth deep validation
    │         └── custom.py ───── 20 problems, code quality via AST
    │                  (type hints, docstrings, error handling, comprehensions)
    │
    ├──▶ serve/quantize.py ──── GPTQ(INT8), AWQ(INT4), GGUF
    │         │
    │         ├── deploy_vllm.py ──── PagedAttention, highest throughput
    │         ├── deploy_sglang.py ── RadixAttention, shared prefix caching
    │         └── deploy_llamacpp.py ─ C++ inference, CPU/edge deployment
    │
    └──▶ bench/benchmark.py ──── async streaming benchmark
              │                      TTFT, throughput, TPOT at batch 1/4/16
              ▼
         bench/analyze.py ──── p50/p99 latencies, cost per 1M tokens
              │                  framework × quantization comparison matrix
              ▼
         comparison.md ──── final report
```

---

# PART 9: NUMBERS TO HAVE MEMORIZED

| Fact | Number | Why it matters |
|------|--------|---------------|
| Base model params | 7.6B (loaded as 4.35B in 4-bit) | Shows you understand model scale |
| Trainable params (LoRA) | ~87M (2% of loaded) | Shows you understand parameter efficiency |
| Training data | 6,672 examples (from 20k) | Shows aggressive curation |
| GRPO V4 time | 34 minutes | Shows RL is fast |
| GRPO V5 time | 2 hours 2 minutes | Shows scaling to more data |
| Total compute cost | ~$36 on T4 | Shows cost awareness |
| T4 hourly cost | $0.75/hr | vs A100 at $3.67/hr |
| T4 VRAM | 16GB | The constraint that drove all design decisions |
| HumanEval base | 86.6% (142/164) | The target to beat |
| HumanEval V5 | 87.8% (144/164) | +2 problems = +1.2% |
| HumanEval SFT (worst) | ~68% | The failure that motivated GRPO |
| Structural pass rate | 75% (V4) | 0 hallucinated symbols |
| Custom quality | 69.8% overall | Docstrings 83%, error handling 78% |
| Eval suites | 4 | HumanEval, MBPP, Structural, Custom |
| Serving matrix | 3×3 | 3 frameworks × 3 quantization levels |
| beta (KL coefficient) | 0.05 | The most important GRPO hyperparameter |
| LoRA rank | 16 | alpha=32, so scaling = 2.0 |
| Learning rate (GRPO) | 5e-6 | 40x smaller than SFT's 2e-4 |
| num_generations | 2 | Minimum for group-relative advantage |

---

# PART 10: THE META-LESSON

If an interviewer asks "What did you learn from this project?", this is
the answer that shows depth:

> "The biggest lesson was that the training METHOD matters more than the
> training DATA for instruct-tuned models.
>
> I started with the conventional approach — SFT on a curated dataset — and
> it made the model worse. Not slightly worse. 18 points worse on HumanEval.
> That's a hard failure, and the instinct is to fix the data: better examples,
> more filtering, different formatting.
>
> But the problem wasn't the data. The problem was SFT itself. Cross-entropy
> loss on a new dataset overwrites the model's existing alignment. You're not
> adding a capability — you're replacing the distribution.
>
> GRPO solved this not by being a better training algorithm in general, but
> by being the RIGHT algorithm for the problem. It preserves base capabilities
> (KL penalty), uses a verifiable reward (code execution), and doesn't need
> paired preference data (which I didn't have).
>
> The pipeline matters too. If I'd only measured HumanEval, I might've
> concluded that GRPO just recovered what SFT lost. But the structural eval
> showed zero hallucinated symbols, and the custom eval showed 83% docstring
> quality. The model wasn't just correct — it was generating well-structured
> Python. Four eval suites gave me the full picture that one benchmark couldn't.
>
> That's what I'd bring to a post-training team: the judgment to choose the
> right training method, the discipline to evaluate rigorously, and the
> experience of watching a conventional approach fail and diagnosing why."
