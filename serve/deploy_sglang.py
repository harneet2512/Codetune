"""Launch SGLang serving with OpenAI-compatible API."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


def launch_sglang(
    model: str,
    port: int = 8002,
    dtype: str = "auto",
) -> None:
    """Launch an SGLang server."""
    cmd = [
        sys.executable, "-m", "sglang.launch_server",
        "--model-path", model,
        "--port", str(port),
        "--dtype", dtype,
    ]

    logger.info(f"Launching SGLang: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch SGLang serving")
    parser.add_argument("--model", required=True, help="Model path")
    parser.add_argument("--port", type=int, default=8002, help="Server port")
    parser.add_argument("--dtype", default="auto", help="Data type")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    launch_sglang(args.model, args.port, args.dtype)


if __name__ == "__main__":
    main()
