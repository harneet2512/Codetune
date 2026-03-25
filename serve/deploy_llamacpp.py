"""Launch llama.cpp server."""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def launch_llamacpp(
    model: str,
    port: int = 8003,
    n_gpu_layers: int = 99,
    ctx_size: int = 4096,
) -> None:
    """Launch a llama.cpp server."""
    llama_server = shutil.which("llama-server") or "llama-server"
    cmd = [
        llama_server,
        "-m", model,
        "--port", str(port),
        "-ngl", str(n_gpu_layers),
        "-c", str(ctx_size),
    ]

    logger.info(f"Launching llama.cpp: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch llama.cpp serving")
    parser.add_argument("--model", required=True, help="GGUF model path")
    parser.add_argument("--port", type=int, default=8003, help="Server port")
    parser.add_argument("--n-gpu-layers", type=int, default=99, help="GPU layers to offload")
    parser.add_argument("--ctx-size", type=int, default=4096, help="Context size")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    launch_llamacpp(args.model, args.port, args.n_gpu_layers, args.ctx_size)


if __name__ == "__main__":
    main()
