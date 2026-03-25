#!/bin/bash
# Full CodeTune pipeline: data → train → merge → eval → quantize → serve → bench
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "============================================"
echo "  CodeTune Full Pipeline"
echo "  Started: $(date)"
echo "============================================"

# Phase 0: Data preparation
echo ""
echo "=== Phase 0: Data Preparation ==="
python data/prepare_dataset.py --output-dir data/processed
echo "Data preparation complete."

# Phase 1: Fine-tuning
echo ""
echo "=== Phase 1: Fine-tuning ==="
python -m train.finetune --config configs/train_config.yaml
echo "Fine-tuning complete."

# Merge adapter
echo ""
echo "=== Phase 1b: Merge Adapter ==="
python -m train.merge \
    --base-model meta-llama/Llama-3.1-8B-Instruct \
    --adapter-path outputs/checkpoints/final_adapter \
    --output-path outputs/codetune-8b
echo "Merge complete."

# Phase 2: Evaluation
echo ""
echo "=== Phase 2: Evaluation ==="

# Eval base model
echo "Evaluating base model..."
python -m eval.runner \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --suites all \
    --output results/eval/base_${TIMESTAMP}.json

# Eval fine-tuned model
echo "Evaluating fine-tuned model..."
python -m eval.runner \
    --model outputs/codetune-8b \
    --suites all \
    --output results/eval/codetune_${TIMESTAMP}.json

# Compare
echo "Generating comparison report..."
python -m eval.compare \
    results/eval/base_${TIMESTAMP}.json \
    results/eval/codetune_${TIMESTAMP}.json \
    --output results/eval/comparison_${TIMESTAMP}.md

echo "Evaluation complete."

# Phase 3: Quantization
echo ""
echo "=== Phase 3: Quantization ==="

echo "GPTQ INT8..."
python -m serve.quantize \
    --model outputs/codetune-8b \
    --method gptq --bits 8 \
    --output outputs/codetune-8b-gptq-int8

echo "AWQ INT4..."
python -m serve.quantize \
    --model outputs/codetune-8b \
    --method awq \
    --output outputs/codetune-8b-awq-int4

echo "Quantization complete."

# Phase 4: Quality at quantization
echo ""
echo "=== Phase 4: Quality-at-Quantization Check ==="

echo "HumanEval on GPTQ INT8..."
python -m eval.runner \
    --model outputs/codetune-8b-gptq-int8 \
    --suites humaneval \
    --output results/eval/codetune_gptq_int8_${TIMESTAMP}.json

echo "HumanEval on AWQ INT4..."
python -m eval.runner \
    --model outputs/codetune-8b-awq-int4 \
    --suites humaneval \
    --output results/eval/codetune_awq_int4_${TIMESTAMP}.json

echo ""
echo "============================================"
echo "  Pipeline Complete"
echo "  Finished: $(date)"
echo "============================================"
echo ""
echo "Results:"
echo "  Eval comparison: results/eval/comparison_${TIMESTAMP}.md"
echo "  All eval results: results/eval/"
echo ""
echo "Next: Start serving endpoints and run benchmarks"
echo "  python -m serve.deploy_vllm --model outputs/codetune-8b --port 8001"
echo "  python -m bench.benchmark --config configs/bench_config.yaml"
echo "  python -m bench.analyze --input results/bench/all_results.json"
