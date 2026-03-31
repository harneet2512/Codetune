#!/bin/bash
# CodeTune v3 pipeline: data prep → train → merge → eval
# Goal: BEAT base model HumanEval (84.8% pass@1)
#
# Key changes from v2:
#   - 80% completion-style data (stub→body), 20% instruction
#   - LoRA rank 64 / alpha 128 (max capacity)
#   - lr 1e-4 (gentler, less forgetting)
#   - Sources: APPS + HumanEval + The Stack
#
# Run on VM: /home/baliharneet7_gmail_com/codetune
set -eo pipefail

export PYTHONPATH="/home/baliharneet7_gmail_com/codetune:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BASE_MODEL="Qwen/Qwen2.5-Coder-7B-Instruct"
MERGED_MODEL="outputs/codetune-7b-v3"

echo "============================================"
echo "  CodeTune v3 Pipeline"
echo "  Goal: Beat base HumanEval 84.8% pass@1"
echo "  Started: $(date)"
echo "============================================"

# -------------------------------------------------------
# Phase 0: Data preparation
# -------------------------------------------------------
echo ""
echo "=== Phase 0: Data Preparation (v3) ==="
python3 data/prepare_dataset_v3.py \
    --output-dir data/processed_v3 \
    --completion-ratio 0.80 \
    --target-total 8000
echo "Data preparation complete."

# -------------------------------------------------------
# Phase 1: Fine-tuning
# -------------------------------------------------------
echo ""
echo "=== Phase 1: Fine-tuning (v3) ==="
python3 -m train.finetune --config configs/train_config_v3.yaml
echo "Fine-tuning complete."

# -------------------------------------------------------
# Phase 1b: Merge adapter into base model
# -------------------------------------------------------
echo ""
echo "=== Phase 1b: Merge Adapter ==="
python3 -m train.merge \
    --base-model "$BASE_MODEL" \
    --adapter-path outputs/checkpoints_v3/final_adapter \
    --output-path "$MERGED_MODEL"
echo "Merge complete: $MERGED_MODEL"

# -------------------------------------------------------
# Phase 2: Evaluation — HumanEval (the target), structural, custom
# -------------------------------------------------------
echo ""
echo "=== Phase 2: Evaluation ==="

echo "--- Evaluating base model ---"
python3 -m eval.runner \
    --model "$BASE_MODEL" \
    --suites humaneval,structural,custom \
    --output "results/eval/base_v3_${TIMESTAMP}.json"

echo "--- Evaluating v3 fine-tuned model ---"
python3 -m eval.runner \
    --model "$MERGED_MODEL" \
    --suites humaneval,structural,custom \
    --output "results/eval/v3_${TIMESTAMP}.json"

echo "--- Generating comparison ---"
python3 -m eval.compare \
    "results/eval/base_v3_${TIMESTAMP}.json" \
    "results/eval/v3_${TIMESTAMP}.json" \
    --output "results/eval/v3_comparison_${TIMESTAMP}.md"

echo ""
echo "============================================"
echo "  v3 Pipeline Complete"
echo "  Finished: $(date)"
echo "============================================"
echo ""
echo "Results:"
echo "  Merged model:  $MERGED_MODEL"
echo "  Base eval:     results/eval/base_v3_${TIMESTAMP}.json"
echo "  v3 eval:       results/eval/v3_${TIMESTAMP}.json"
echo "  Comparison:    results/eval/v3_comparison_${TIMESTAMP}.md"
echo ""
echo "If HumanEval pass@1 > 84.8%, we beat the base model!"
