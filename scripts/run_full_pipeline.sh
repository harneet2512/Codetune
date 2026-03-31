#!/bin/bash
set -e
cd /home/Lenovo/Codetune
export PYTHONPATH=/home/Lenovo/Codetune

echo "=== STEP 1: SFT (waiting for completion) ==="
# SFT already running, wait for it
while kill -0 $(cat /home/Lenovo/sft.pid 2>/dev/null) 2>/dev/null; do
    sleep 30
    tail -1 /home/Lenovo/sft.log 2>/dev/null
done
echo "=== SFT DONE ==="
ls outputs/tooltune-sft-checkpoints/final_adapter/

echo "=== STEP 2: Merge SFT into base ==="
python3 scripts/merge_sft.py 2>&1
echo "=== MERGE DONE ==="

echo "=== STEP 3: GRPO on merged model ==="
python3 -m train.grpo_tooltune \
    --base-model outputs/tooltune-sft-merged \
    --variant grpo-balanced \
    --output-dir outputs/tooltune-grpo-balanced-v2 \
    --task-files tasks/tier1_single_tool.json tasks/tier2_restraint.json tasks/tier3_multi_step.json tasks/tier4_error_recovery.json \
    2>&1
echo "=== GRPO DONE ==="

echo "=== STEP 4: Generate traces (50 tasks x 3 variants) ==="
python3 -m train.generate_traces --variants base sft grpo-balanced --max-tasks 50 2>&1
echo "=== TRACES DONE ==="

echo "=== STEP 5: Eval ==="
python3 scripts/quick_eval2.py 2>&1
echo "=== ALL DONE ==="
