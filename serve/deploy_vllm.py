"""Launch vLLM serving with OpenAI-compatible API."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


def launch_vllm(
    model: str,
    port: int = 8001,
    dtype: str = "auto",
    max_model_len: int = 4096,
    gpu_memory_utilization: float = 0.90,
    max_num_seqs: int = 64,
) -> None:
    """Launch a vLLM server."""
    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", model,
        "--port", str(port),
        "--dtype", dtype,
        "--max-model-len", str(max_model_len),
        "--gpu-memory-utilization", str(gpu_memory_utilization),
        "--max-num-seqs", str(max_num_seqs),
    ]

    logger.info(f"Launching vLLM: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch vLLM serving")
    parser.add_argument("--model", required=True, help="Model path")
    parser.add_argument("--port", type=int, default=8001, help="Server port")
    parser.add_argument("--dtype", default="auto", help="Data type")
    parser.add_argument("--max-model-len", type=int, default=4096, help="Max sequence length")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--max-num-seqs", type=int, default=64)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    launch_vllm(args.model, args.port, args.dtype, args.max_model_len,
                args.gpu_memory_utilization, args.max_num_seqs)


if __name__ == "__main__":
    main()
