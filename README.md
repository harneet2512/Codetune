# CodeTune

Fine-tune, evaluate, and serve a coding LLM — end to end.

## What This Is

A complete AI model lifecycle pipeline: take Llama 3.1 8B Instruct, fine-tune it on coding data with QLoRA, evaluate across four dimensions (functional correctness, structural verification, code quality), serve at three quantization levels across three inference frameworks, and benchmark everything.

This project demonstrates the workflow that production AI platforms (like Fireworks AI) productize: dataset curation → fine-tuning → multi-signal evaluation → quantized serving → inference benchmarking.

## Results at a Glance

### Evaluation: Base vs Fine-tuned

| Metric | Llama 3.1 8B | CodeTune 8B | Delta |
|--------|-------------|-------------|-------|
| HumanEval pass@1 | — | — | — |
| MBPP-sanitized pass@1 | — | — | — |
| Structural pass rate (GT) | — | — | — |
| Custom: type hints | — | — | — |
| Custom: docstrings | — | — | — |
| Custom: error handling | — | — | — |

*Results populated after training run.*

### Serving Benchmark: 3×3 Matrix

| Framework | FP16 | INT8 (GPTQ) | INT4 (AWQ) |
|-----------|------|-------------|------------|
| vLLM | — | — | — |
| SGLang | — | — | — |
| llama.cpp | — | — | — |

*Throughput in tokens/sec. Results populated after benchmark run.*

## The Pipeline

```
data/prepare_dataset.py     →  Download + filter CodeAlpaca-20k
train/finetune.py           →  QLoRA fine-tuning (SFTTrainer)
train/merge.py              →  Merge LoRA adapter into base model
eval/runner.py              →  Run all 4 eval suites
eval/compare.py             →  Generate base vs fine-tuned comparison
serve/quantize.py           →  GPTQ INT8, AWQ INT4, GGUF
serve/deploy_vllm.py        →  Launch vLLM server
serve/deploy_sglang.py      →  Launch SGLang server
serve/deploy_llamacpp.py    →  Launch llama.cpp server
bench/benchmark.py          →  Async benchmark runner
bench/analyze.py            →  Generate comparison tables
```

### Evaluation Signals

1. **HumanEval** — Functional correctness (164 problems, pass@1)
2. **MBPP** — Broader code generation (427 problems, pass@1)
3. **Structural verification** — Import correctness, symbol accuracy, hallucination detection via [GroundTruth](https://github.com/YOUR_USERNAME/groundtruth) integration
4. **Custom quality evals** — Type hints, docstrings, error handling, Pythonic style (20 test cases, AST-based checks)

The structural eval is the unique signal: code can pass functional tests but still have hallucinated imports, wrong module paths, or invented symbols. GroundTruth catches these.

## Quick Start

### Prerequisites

- Python 3.10+
- GPU with 16GB+ VRAM (T4 for training, A100 recommended for serving)
- HuggingFace account with access to [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)

### Setup

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/codetune.git
cd codetune

# Install
pip install -e ".[all]"

# Login to HuggingFace
huggingface-cli login
```

### Run the Full Pipeline

```bash
bash scripts/run_all.sh
```

Or run each phase individually:

```bash
# 1. Prepare data
python data/prepare_dataset.py

# 2. Fine-tune
python -m train.finetune --config configs/train_config.yaml

# 3. Merge adapter
python -m train.merge

# 4. Evaluate base model
python -m eval.runner --model meta-llama/Llama-3.1-8B-Instruct --suites all --output results/eval/base.json

# 5. Evaluate fine-tuned model
python -m eval.runner --model outputs/codetune-8b --suites all --output results/eval/codetune.json

# 6. Compare
python -m eval.compare results/eval/base.json results/eval/codetune.json --output results/eval/comparison.md

# 7. Quantize
python -m serve.quantize --model outputs/codetune-8b --method gptq --bits 8 --output outputs/codetune-8b-gptq-int8
python -m serve.quantize --model outputs/codetune-8b --method awq --output outputs/codetune-8b-awq-int4

# 8. Serve (in separate terminals)
python -m serve.deploy_vllm --model outputs/codetune-8b --port 8001
python -m serve.deploy_vllm --model outputs/codetune-8b-gptq-int8 --port 8011

# 9. Benchmark
python -m bench.benchmark --config configs/bench_config.yaml --output results/bench
python -m bench.analyze --input results/bench/all_results.json --output results/bench/comparison.md
```

## Architecture

```
CodeAlpaca-20k  ──→  Filter + Format  ──→  QLoRA Training  ──→  Merged Model
                     (Python-only,          (Llama 3.1 8B,      (CodeTune 8B)
                      3-100 LOC,            16-bit LoRA,            │
                      chat template)        3 epochs)               │
                                                                    ▼
                                                              ┌─────────────┐
                                                              │  Evaluation  │
                                                              │  4 suites    │
                                                              └──────┬──────┘
                                                                     │
                                            ┌────────────────────────┼────────────────────────┐
                                            ▼                        ▼                        ▼
                                      FP16 (16GB)            INT8 GPTQ (8GB)          INT4 AWQ (4GB)
                                            │                        │                        │
                                    ┌───────┼───────┐       ┌───────┼───────┐       ┌───────┼───────┐
                                    ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼
                                  vLLM   SGLang  llama   vLLM   SGLang  llama   vLLM   SGLang  llama
                                    │       │      .cpp     │       │      .cpp     │       │      .cpp
                                    └───────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┘
                                                                    │
                                                              ┌─────▼─────┐
                                                              │ Benchmark │
                                                              │ 9 configs │
                                                              │ 3 batch   │
                                                              │ sizes     │
                                                              └───────────┘
```

## GroundTruth Integration

The structural eval suite uses [GroundTruth](https://github.com/YOUR_USERNAME/groundtruth) as an optional dependency for deeper structural validation. GroundTruth is an MCP server that gives AI coding agents codebase intelligence via LSP + SQLite.

When available, it checks generated code for:
- Hallucinated imports (modules that don't exist)
- Wrong module paths (symbol exists but imported from wrong location)
- Missing symbols (referenced names that don't resolve)
- Signature mismatches (wrong argument count or types)

Without GroundTruth installed, the structural suite falls back to AST-based import and symbol checking.

## Configuration

All configuration is in YAML files under `configs/`:

- `train_config.yaml` — QLoRA hyperparameters, model config, training settings
- `eval_config.yaml` — Eval suite selection, generation parameters
- `bench_config.yaml` — Endpoint URLs, benchmark parameters, cost calculation

## Cost

Running on GCP with credits:

| Phase | GPU | Hours | Cost |
|-------|-----|-------|------|
| Training (QLoRA) | T4 | ~8 hrs | ~$3 |
| Evaluation | T4 | ~4 hrs | ~$1.50 |
| Serving + Benchmark | A100 | ~10 hrs | ~$37 |
| **Total** | | **~22 hrs** | **~$42** |

## License

MIT
