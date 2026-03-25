#!/bin/bash
# Download Llama 3.1 8B Instruct weights
set -euo pipefail

echo "Downloading meta-llama/Llama-3.1-8B-Instruct..."
echo "This will download ~16GB to ~/.cache/huggingface/"

python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer

print('Downloading tokenizer...')
tokenizer = AutoTokenizer.from_pretrained('meta-llama/Llama-3.1-8B-Instruct')
print('Tokenizer downloaded.')

print('Downloading model weights (~16GB)...')
model = AutoModelForCausalLM.from_pretrained(
    'meta-llama/Llama-3.1-8B-Instruct',
    torch_dtype='auto',
    low_cpu_mem_usage=True,
)
print('Model downloaded successfully.')
print(f'Model size: {sum(p.numel() for p in model.parameters()) / 1e9:.1f}B parameters')
"
