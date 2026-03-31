#!/bin/bash
# CodeTune v2 pipeline: data prep → train → merge
# Improvements over v1:
#   - CodeFeedback-Filtered-Instruction (higher quality than CodeAlpaca)
#   - HumanEval completion-style examples mixed in (10%) to prevent regression
#   - 1 epoch, LoRA rank 32
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "============================================"
echo "  CodeTune v2 Training Pipeline"
echo "  Started: $(date)"
echo "============================================"

# Phase 0: Data preparation
echo ""
echo "=== Phase 0: Data Preparation (v2) ==="
python data/prepare_dataset_v2.py --output-dir data/processed_v2
echo "Data preparation complete."

# Phase 1: Fine-tuning
echo ""
echo "=== Phase 1: Fine-tuning (v2) ==="
python -m train.finetune --config configs/train_config_v2.yaml
echo "Fine-tuning complete."

# Phase 1b: Merge adapter into base model
echo ""
echo "=== Phase 1b: Merge Adapter ==="
python -m train.merge \
    --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
    --adapter-path outputs/checkpoints_v2/final_adapter \
    --output-path outputs/codetune-qwen-7b-v2
echo "Merge complete."

echo ""
echo "============================================"
echo "  v2 Training Pipeline Complete"
echo "  Finished: $(date)"
echo "============================================"
echo ""
echo "Merged model: outputs/codetune-qwen-7b-v2"
echo ""
echo "Next steps:"
echo "  # Evaluate on HumanEval"
echo "  python -m eval.runner --model outputs/codetune-qwen-7b-v2 --suites humaneval --output results/eval/v2_${TIMESTAMP}.json"
echo ""
echo "  # Compare with base"
echo "  python -m eval.runner --model Qwen/Qwen2.5-Coder-7B-Instruct --suites humaneval --output results/eval/base_qwen_${TIMESTAMP}.json"
echo "  python -m eval.compare results/eval/base_qwen_${TIMESTAMP}.json results/eval/v2_${TIMESTAMP}.json --output results/eval/v2_comparison_${TIMESTAMP}.md"
