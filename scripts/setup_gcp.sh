#!/bin/bash
# GCP VM setup for CodeTune
# Run this on a fresh Deep Learning VM with GPU

set -euo pipefail

echo "=== CodeTune GCP Setup ==="

# Verify GPU
echo "Checking GPU..."
nvidia-smi || { echo "ERROR: No GPU found"; exit 1; }

# Update pip
pip install --upgrade pip

# Clone repo (if not already cloned)
if [ ! -d "codetune" ]; then
    echo "Clone the repo first: git clone <your-repo-url> codetune"
    echo "Then cd codetune && bash scripts/setup_gcp.sh"
fi

# Install dependencies
echo "Installing core dependencies..."
pip install -e ".[all]"

# Install llama.cpp (for GGUF serving)
echo "Installing llama-cpp-python..."
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

# Login to HuggingFace
echo ""
echo "=== HuggingFace Login ==="
echo "You need a HuggingFace token with access to meta-llama/Llama-3.1-8B-Instruct"
echo "Get one at: https://huggingface.co/settings/tokens"
echo ""
huggingface-cli login

# Verify model access
echo "Verifying model access..."
python -c "from transformers import AutoTokenizer; t = AutoTokenizer.from_pretrained('meta-llama/Llama-3.1-8B-Instruct'); print('Model access OK')"

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. python data/prepare_dataset.py"
echo "  2. python -m train.finetune"
echo "  3. python -m train.merge"
echo "  4. python -m eval.runner --model outputs/codetune-8b --suites all --output results/eval/codetune.json"
echo "  Or run everything: bash scripts/run_all.sh"
