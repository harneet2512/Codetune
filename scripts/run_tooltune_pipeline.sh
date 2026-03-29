#!/bin/bash
# ToolTune: End-to-end training pipeline
# Trains SFT warmup + GRPO-Balanced on Qwen2.5-7B-Instruct
# Expected runtime: ~5 hours on T4, ~$4
set -euo pipefail

BASE_MODEL="Qwen/Qwen2.5-7B-Instruct"
SFT_OUTPUT="outputs/tooltune-sft-checkpoints"
TASK_FILES=(
    "tasks/tier1_single_tool.json"
    "tasks/tier2_restraint.json"
    "tasks/tier3_multi_step.json"
    "tasks/tier4_error_recovery.json"
)

echo "============================================"
echo "  ToolTune Training Pipeline"
echo "============================================"
echo ""

# Phase 1: Generate tasks
echo "=== Phase 1: Generate 500 tasks ==="
python -m tasks.generate_tasks
echo ""

# Phase 2: SFT warmup (teaches format: think/tool_call/observation/answer tags)
echo "=== Phase 2: SFT warmup on ${BASE_MODEL} ==="
python -m train.sft_tooltune \
    --base-model "${BASE_MODEL}" \
    --output-dir "${SFT_OUTPUT}" \
    --task-files "${TASK_FILES[@]}"
echo ""

# Phase 3: GRPO-Balanced (learns WHEN/WHICH/HOW to use tools)
echo "=== Phase 3: GRPO-Balanced ==="
python -m train.grpo_tooltune \
    --base-model "${SFT_OUTPUT}/final_adapter" \
    --variant grpo-balanced \
    --task-files "${TASK_FILES[@]}"
echo ""

# Phase 4 (optional): GRPO-Exec (task completion only reward)
# Uncomment to train additional variants:
# echo "=== Phase 4: GRPO-Exec ==="
# python -m train.grpo_tooltune \
#     --base-model "${SFT_OUTPUT}/final_adapter" \
#     --variant grpo-exec \
#     --task-files "${TASK_FILES[@]}"

# Phase 5 (optional): GRPO-ToolHeavy (high tool accuracy weight)
# echo "=== Phase 5: GRPO-ToolHeavy ==="
# python -m train.grpo_tooltune \
#     --base-model "${SFT_OUTPUT}/final_adapter" \
#     --variant grpo-toolheavy \
#     --task-files "${TASK_FILES[@]}"

# Phase 6: Generate eval traces for all available variants
echo "=== Phase 6: Generate eval traces ==="
python -m train.generate_traces \
    --output-dir results/traces \
    --variants base sft grpo-balanced
echo ""

# Phase 7: Run evaluation across all variants
echo "=== Phase 7: Run evaluation ==="
for variant in base sft grpo-balanced; do
    trace_file="results/traces/${variant}.json"
    if [ -f "${trace_file}" ]; then
        echo "  Evaluating ${variant}..."
        python -m eval.run_all \
            --input "${trace_file}" \
            --output "results/eval/${variant}.json"
    else
        echo "  Skipping ${variant} (no traces found)"
    fi
done
echo ""

echo "============================================"
echo "  Pipeline complete!"
echo "  Traces:  results/traces/"
echo "  Evals:   results/eval/"
echo "============================================"
