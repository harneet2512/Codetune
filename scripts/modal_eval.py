"""Chunked parallel evaluation on Modal.

The local RTX 2060 llama-server crashes mid-run (CUDA illegal instruction), so
long evals run on Modal T4s instead. Each container loads the model once and
runs an interleaved slice of the task set; per-chunk traces land in the
`restraint-eval` volume, then get merged and scored locally with
scripts/merge_eval_chunks.py.

Usage:
    modal run scripts/modal_eval.py --suite v1 --model v2 --n 200 --chunks 4
    modal run scripts/modal_eval.py --suite v3 --model v2 --n 120 --chunks 4
    modal run scripts/modal_eval.py --suite v1 --model baseline --n 200 --chunks 4
    modal run scripts/modal_eval.py --suite v1 --model v2-bf16 --n 50 --chunks 1

Then pull results:
    modal volume get restraint-eval traces/ results/traces_modal/ --force
"""

import modal

app = modal.App("restraint-7b-eval")
vol = modal.Volume.from_name("restraint-eval", create_if_missing=True)
runs_vol = modal.Volume.from_name("restraint-runs", create_if_missing=True)

STOPS = ["<|im_end|>", "\nUser:", "</answer>", "</tool_call>", "<observation>"]

MODELS = {
    "v2": {"kind": "gguf", "repo": "aravindpersona/restraint-7b",
           "file": "restraint-7b-v2-q4km.gguf", "gpu": "T4"},
    "baseline": {"kind": "gguf", "repo": "aravindpersona/restraint-7b",
                 "file": "baseline/restraint-7b-sft-baseline-q4km.gguf", "gpu": "T4"},
    "v2-bf16": {"kind": "safetensors", "repo": "aravindpersona/restraint-7b",
                "file": None, "gpu": "A10G"},
    "r15b": {"kind": "adapter", "base": "Qwen/Qwen2.5-1.5B-Instruct",
             "adapter": "/vol/models/r15b-adapter", "gpu": "T4"},
    # v3 candidate: stage1-merged + corrective adapter trained on the FIXED
    # generator (value-bound args, real code_executor shapes)
    "v3": {"kind": "safetensors-path", "path": "/runs/restraint-7b-v3-merged",
           "gpu": "A10G"},
}

CODE_MOUNTS = [
    ("tooltune", "/root/tooltune"),
    ("tools", "/root/tools"),
    ("tooltune_data", "/root/tooltune_data"),
    ("tasks", "/root/tasks"),
]


def _mount_code(img):
    for local, remote in CODE_MOUNTS:
        img = img.add_local_dir(local, remote_path=remote, copy=True)
    for f in ("__init__.py", "agentic_loop.py", "reward.py"):
        img = img.add_local_file(f"train/{f}", remote_path=f"/root/train/{f}", copy=True)
    img = img.add_local_file("scripts/eval_release.py",
                             remote_path="/root/scripts/eval_release.py", copy=True)
    img = img.add_local_file("results/traces_release/restraint-7b-v2-fixed.json",
                             remote_path="/root/ref_trace.json", copy=True)
    img = img.add_local_file("results/v1_fail_ids.json",
                             remote_path="/root/v1_fail_ids.json", copy=True)
    return img


def _dl_gguf(repo, filename):
    from huggingface_hub import hf_hub_download
    hf_hub_download(repo, filename, local_dir="/root/model")


gguf_base = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-runtime-ubuntu22.04", add_python="3.11")
    .apt_install("libgomp1")
    .pip_install(
        "llama-cpp-python==0.3.16",
        extra_index_url="https://abetlen.github.io/llama-cpp-python/whl/cu124",
    )
    .pip_install("huggingface_hub", "requests")
)
gguf_v2 = _mount_code(gguf_base.run_function(
    _dl_gguf, args=(MODELS["v2"]["repo"], MODELS["v2"]["file"])))
gguf_baseline = _mount_code(gguf_base.run_function(
    _dl_gguf, args=(MODELS["baseline"]["repo"], MODELS["baseline"]["file"])))
bf16_image = _mount_code(
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch", "transformers==4.49.0", "accelerate", "safetensors",
                 "huggingface_hub", "peft", "requests")
)


def _select_tasks(suite, n, seed):
    """Same selection logic as eval_release.py: sorted glob -> seed shuffle ->
    take n. Identical seed across models = paired task sets."""
    import random
    import sys
    from pathlib import Path
    sys.path.insert(0, "/root")
    from tooltune.contracts import TaskRecord
    from tooltune.io import load_json

    if suite == "adv":
        glob = "adv_*.json"
    elif suite == "v3":
        glob = "v3_tier*.json"
    else:
        glob = "tier*.json"  # v1, v1-live, paired50, v1-fail all use v1 tasks
    all_tasks = []
    for f in sorted(Path("/root/tasks").glob(glob)):
        for item in load_json(f):
            all_tasks.append(TaskRecord(**item))
    if suite == "v1-fail":
        import json
        want = set(json.loads(Path("/root/v1_fail_ids.json").read_text()))
        return [t for t in all_tasks if t.id in want][:n]
    if suite == "paired50":
        # identical task IDs as the committed 50-task release eval
        import json
        ref = json.loads(Path("/root/ref_trace.json").read_text())
        want = {t["task"]["id"] for t in ref}
        return [t for t in all_tasks if t.id in want][:n]
    random.seed(seed)
    random.shuffle(all_tasks)
    return all_tasks[:n]


def _run_chunk(chunk_id, n_chunks, suite, n, seed, generate, name):
    """Interleaved slice tasks[chunk_id::n_chunks]. Writes the chunk trace file
    after EVERY task (mkdir'd under /vol) so a late crash loses at most one
    task, and a rerun resumes the chunk from its existing file."""
    import json
    import sys
    from pathlib import Path
    sys.path.insert(0, "/root")
    sys.path.insert(0, "/root/scripts")
    from eval_release import ConnectorAdapter
    from tools.registry import ToolRegistry
    from train.agentic_loop import generate_agentic_completion

    tasks = _select_tasks(suite, n, seed)[chunk_id::n_chunks]
    if suite == "v3":
        registry = ConnectorAdapter()
    elif suite == "v1-live":
        from tools.live_registry import LiveToolRegistry
        registry = LiveToolRegistry()
    else:
        registry = ToolRegistry()

    Path("/vol/traces").mkdir(parents=True, exist_ok=True)
    path = Path(f"/vol/traces/{name}-chunk{chunk_id}.json")
    traces, done = [], set()
    if path.exists():
        traces = json.loads(path.read_text())
        done = {t["task"]["id"] for t in traces}
        print(f"[chunk {chunk_id}] resuming: {len(done)} traces", flush=True)
    for i, task in enumerate(tasks):
        if task.id in done:
            continue
        print(f"[chunk {chunk_id} {i+1}/{len(tasks)}] {task.id}", flush=True)
        trace = generate_agentic_completion(
            generator=generate, task=task, registry=registry,
            max_steps=5, temperature=0.0)
        traces.append(trace.to_dict())
        path.write_text(json.dumps(traces))
        if i % 10 == 9:
            vol.commit()
    return traces


class _CppGen:
    """LlamaCppGenerator equivalent over llama-cpp-python (same stop list)."""

    def __init__(self, model_path, cap=None):
        from llama_cpp import Llama
        self.llm = Llama(model_path, n_gpu_layers=-1, n_ctx=4096, verbose=False)
        self.cap = cap  # override the loop's 256 default (truncation study)
        self.tokens_predicted = 0
        self.tokens_evaluated = 0

    def generate(self, prompt, max_new_tokens=256, temperature=0.0):
        out = self.llm(prompt, max_tokens=self.cap or max_new_tokens,
                       temperature=temperature, stop=STOPS)
        text = out["choices"][0]["text"]
        usage = out.get("usage") or {}
        self.tokens_predicted += usage.get("completion_tokens", 0)
        self.tokens_evaluated += usage.get("prompt_tokens", 0)
        if "<answer>" in text and "</answer>" not in text:
            text += "</answer>"
        if "<tool_call>" in text and "</tool_call>" not in text:
            text += "</tool_call>"
        return text


class _HfGen:
    """Full-precision generator: safetensors repo, or base+LoRA adapter
    (cross-scale ablation). Same stop list."""

    def __init__(self, model_key):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        spec = MODELS[model_key]
        if spec["kind"] == "adapter":
            from peft import PeftModel
            vol.reload()
            # tokenizer from base repo — adapter dir's tokenizer_config was
            # written by a newer transformers and won't parse on 4.49
            self.tok = AutoTokenizer.from_pretrained(spec["base"])
            base = AutoModelForCausalLM.from_pretrained(
                spec["base"], torch_dtype=torch.bfloat16, device_map="auto")
            self.model = PeftModel.from_pretrained(base, spec["adapter"])
        elif spec["kind"] == "safetensors-path":
            runs_vol.reload()
            self.tok = AutoTokenizer.from_pretrained(spec["path"])
            self.model = AutoModelForCausalLM.from_pretrained(
                spec["path"], torch_dtype=torch.bfloat16, device_map="auto")
        else:
            self.tok = AutoTokenizer.from_pretrained(spec["repo"])
            self.model = AutoModelForCausalLM.from_pretrained(
                spec["repo"], torch_dtype=torch.bfloat16, device_map="auto")
        self.tokens_predicted = 0
        self.tokens_evaluated = 0

    def generate(self, prompt, max_new_tokens=256, temperature=0.0):
        import torch
        inputs = self.tok(prompt, return_tensors="pt").to(self.model.device)
        self.tokens_evaluated += inputs["input_ids"].shape[1]
        with torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=max_new_tokens, do_sample=False,
                stop_strings=STOPS, tokenizer=self.tok,
                pad_token_id=self.tok.eos_token_id)
        new = out[0][inputs["input_ids"].shape[1]:]
        self.tokens_predicted += new.shape[0]
        text = self.tok.decode(new, skip_special_tokens=False)
        if "<answer>" in text and "</answer>" not in text:
            text += "</answer>"
        if "<tool_call>" in text and "</tool_call>" not in text:
            text += "</tool_call>"
        return text


def _persist(name, chunk_id, traces, gen):
    import json
    from pathlib import Path
    Path("/vol/traces").mkdir(parents=True, exist_ok=True)
    vol.reload()
    base = f"/vol/traces/{name}-chunk{chunk_id}"
    with open(base + ".json", "w") as f:
        json.dump(traces, f)
    with open(base + ".meta.json", "w") as f:
        json.dump({"tokens_predicted": gen.tokens_predicted,
                   "tokens_evaluated": gen.tokens_evaluated}, f)
    vol.commit()
    print(f"chunk {chunk_id}: {len(traces)} traces -> {base}.json", flush=True)


@app.function(gpu="T4", image=gguf_v2, volumes={"/vol": vol}, timeout=7200)
def eval_gguf_v2(chunk_id, n_chunks, suite, model_key, n, seed, max_tokens=0):
    import sys
    sys.path.insert(0, "/root")
    gen = _CppGen("/root/model/" + MODELS[model_key]["file"], cap=max_tokens or None)
    name = f"{suite}-{model_key}" + (f"-mt{max_tokens}" if max_tokens else "")
    traces = _run_chunk(chunk_id, n_chunks, suite, n, seed, gen, name)
    _persist(name, chunk_id, traces, gen)


@app.function(gpu="T4", image=gguf_baseline, volumes={"/vol": vol}, timeout=7200)
def eval_gguf_baseline(chunk_id, n_chunks, suite, model_key, n, seed, max_tokens=0):
    import sys
    sys.path.insert(0, "/root")
    gen = _CppGen("/root/model/" + MODELS[model_key]["file"], cap=max_tokens or None)
    name = f"{suite}-{model_key}" + (f"-mt{max_tokens}" if max_tokens else "")
    traces = _run_chunk(chunk_id, n_chunks, suite, n, seed, gen, name)
    _persist(name, chunk_id, traces, gen)


@app.function(gpu="A10G", image=bf16_image, volumes={"/vol": vol}, timeout=7200)
def eval_bf16_chunk(chunk_id, n_chunks, suite, model_key, n, seed, max_tokens=0):
    import sys
    sys.path.insert(0, "/root")
    gen = _HfGen(model_key)
    name = f"{suite}-{model_key}" + (f"-mt{max_tokens}" if max_tokens else "")
    traces = _run_chunk(chunk_id, n_chunks, suite, n, seed, gen, name)
    _persist(name, chunk_id, traces, gen)


@app.function(gpu="T4", image=bf16_image, volumes={"/vol": vol}, timeout=7200)
def eval_r15b(chunk_id, n_chunks, suite, model_key, n, seed, max_tokens=0):
    import sys
    sys.path.insert(0, "/root")
    gen = _HfGen(model_key)
    name = f"{suite}-{model_key}" + (f"-mt{max_tokens}" if max_tokens else "")
    traces = _run_chunk(chunk_id, n_chunks, suite, n, seed, gen, name)
    _persist(name, chunk_id, traces, gen)


@app.function(gpu="A10G", image=bf16_image,
              volumes={"/vol": vol, "/runs": runs_vol}, timeout=7200)
def eval_v3(chunk_id, n_chunks, suite, model_key, n, seed, max_tokens=0):
    import sys
    sys.path.insert(0, "/root")
    gen = _HfGen(model_key)
    name = f"{suite}-{model_key}" + (f"-mt{max_tokens}" if max_tokens else "")
    traces = _run_chunk(chunk_id, n_chunks, suite, n, seed, gen, name)
    _persist(name, chunk_id, traces, gen)


@app.local_entrypoint()
def main(suite="v1", model="v2", n=50, chunks=1, seed=42, max_tokens=0):
    n, chunks, seed, max_tokens = int(n), int(chunks), int(seed), int(max_tokens)
    fn = {"v2": eval_gguf_v2, "baseline": eval_gguf_baseline,
          "v2-bf16": eval_bf16_chunk, "r15b": eval_r15b, "v3": eval_v3}[model]
    calls = [fn.spawn(i, chunks, suite, model, n, seed, max_tokens)
             for i in range(chunks)]
    for c in calls:
        c.get()
    print(f"done: {suite}/{model} n={n} across {chunks} chunks")
