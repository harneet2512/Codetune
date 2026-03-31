#!/bin/bash
# Run base model eval on all suites (except MBPP which has schema issues)
cd /home/baliharneet7_gmail_com/codetune
export PYTHONPATH=/home/baliharneet7_gmail_com/codetune
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
LOG=/home/baliharneet7_gmail_com/codetune/base_eval_final.log

echo "=== BASE EVAL START $(date) ===" > $LOG

python3 -m eval.runner \
    --model Qwen/Qwen2.5-Coder-7B-Instruct \
    --suites humaneval,structural,custom \
    --config configs/eval_config.yaml \
    --output results/eval/base.json >> $LOG 2>&1

echo "=== BASE EVAL COMPLETE $(date) ===" >> $LOG
