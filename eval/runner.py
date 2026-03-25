"""Eval orchestrator: loads model, runs requested suites, outputs structured results."""

from __future__ import annotations

import argparse
import json
import logging
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
import yaml
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)

SUITE_REGISTRY: dict[str, str] = {
    "humaneval": "eval.suites.humaneval",
    "mbpp": "eval.suites.mbpp",
    "structural": "eval.suites.structural",
    "custom": "eval.suites.custom",
}


def load_model(model_path: str, dtype: str = "bfloat16"):
    """Load a model and tokenizer for evaluation."""
    torch_dtype = getattr(torch, dtype)
    logger.info(f"Loading model: {model_path}")

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch_dtype,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    return model, tokenizer


def get_hardware_info() -> dict:
    """Collect hardware metadata."""
    info: dict = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
    }
    if torch.cuda.is_available():
        info["gpu"] = torch.cuda.get_device_name(0)
        info["gpu_memory_gb"] = round(torch.cuda.get_device_properties(0).total_mem / 1e9, 1)
        info["cuda"] = torch.version.cuda or "unknown"
    return info


def run_suite(suite_name: str, model, tokenizer, config: dict) -> dict:
    """Dynamically import and run an eval suite."""
    import importlib

    module_path = SUITE_REGISTRY[suite_name]
    module = importlib.import_module(module_path)
    suite_config = config.get("suites", {}).get(suite_name, {})
    gen_config = config.get("generation", {})

    logger.info(f"Running suite: {suite_name}")
    start = time.time()
    result = module.run(model, tokenizer, suite_config=suite_config, gen_config=gen_config)
    elapsed = time.time() - start

    result["suite"] = suite_name
    result["elapsed_seconds"] = round(elapsed, 1)
    logger.info(f"Suite {suite_name} completed in {elapsed:.1f}s")
    return result


def run_eval(
    model_path: str,
    config_path: str = "configs/eval_config.yaml",
    suites: str = "all",
    output: str | None = None,
) -> dict:
    """Run evaluation pipeline."""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Determine which suites to run
    if suites == "all":
        suite_names = [
            name for name, cfg in config.get("suites", {}).items()
            if cfg.get("enabled", True)
        ]
    else:
        suite_names = [s.strip() for s in suites.split(",")]

    # Validate suite names
    for name in suite_names:
        if name not in SUITE_REGISTRY:
            raise ValueError(f"Unknown suite: {name}. Available: {list(SUITE_REGISTRY.keys())}")

    # Load model
    model, tokenizer = load_model(model_path)

    # Run suites
    results = {
        "model": model_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hardware": get_hardware_info(),
        "suites": {},
    }

    for suite_name in suite_names:
        suite_result = run_suite(suite_name, model, tokenizer, config)
        results["suites"][suite_name] = suite_result

    # Save results
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_path}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="CodeTune evaluation runner")
    parser.add_argument("--model", required=True, help="Model name or path")
    parser.add_argument("--config", default="configs/eval_config.yaml", help="Eval config path")
    parser.add_argument(
        "--suites", default="all",
        help="Comma-separated suite names or 'all'",
    )
    parser.add_argument("--output", help="Output JSON path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = run_eval(args.model, args.config, args.suites, args.output)

    # Print summary
    print("\n" + "=" * 60)
    print(f"EVAL RESULTS: {args.model}")
    print("=" * 60)
    for suite_name, suite_result in results["suites"].items():
        metrics = suite_result.get("metrics", {})
        print(f"\n{suite_name}:")
        for k, v in metrics.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
