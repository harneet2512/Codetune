"""Async benchmark runner: hit serving endpoints, collect latency and throughput metrics."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


async def send_request(
    session,
    url: str,
    model: str,
    prompt: str,
    max_tokens: int = 256,
    temperature: float = 0.0,
    timeout: int = 120,
) -> dict:
    """Send a single completion request and measure timing."""
    import aiohttp

    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    start = time.perf_counter()
    ttft = None
    tokens_generated = 0
    full_response = ""

    try:
        async with session.post(
            f"{url}/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            async for line in resp.content:
                decoded = line.decode("utf-8").strip()
                if not decoded or not decoded.startswith("data: "):
                    continue
                data_str = decoded[6:]
                if data_str == "[DONE]":
                    break

                if ttft is None:
                    ttft = (time.perf_counter() - start) * 1000  # ms

                try:
                    data = json.loads(data_str)
                    text = data.get("choices", [{}])[0].get("text", "")
                    full_response += text
                    tokens_generated += 1
                except json.JSONDecodeError:
                    continue

    except Exception as e:
        return {
            "error": str(e),
            "ttft_ms": None,
            "total_time_ms": (time.perf_counter() - start) * 1000,
            "tokens_generated": 0,
        }

    total_time = (time.perf_counter() - start) * 1000  # ms
    tps = (tokens_generated / (total_time / 1000)) if total_time > 0 else 0
    tpot = (total_time - (ttft or 0)) / max(tokens_generated - 1, 1) if tokens_generated > 1 else 0

    return {
        "ttft_ms": round(ttft, 2) if ttft else None,
        "total_time_ms": round(total_time, 2),
        "tokens_generated": tokens_generated,
        "tokens_per_second": round(tps, 2),
        "time_per_output_token_ms": round(tpot, 2),
    }


async def benchmark_endpoint(
    url: str,
    model: str,
    prompts: list[dict],
    batch_size: int = 1,
    max_tokens: int = 256,
    temperature: float = 0.0,
    warmup_requests: int = 5,
    num_requests: int = 50,
    timeout: int = 120,
) -> list[dict]:
    """Benchmark a single endpoint at a given batch size."""
    import aiohttp

    results = []

    async with aiohttp.ClientSession() as session:
        # Warmup
        logger.info(f"Warming up {url} ({warmup_requests} requests)...")
        warmup_prompts = prompts[:warmup_requests]
        for p in warmup_prompts:
            await send_request(session, url, model, p["prompt"], max_tokens, temperature, timeout)

        # Benchmark
        logger.info(f"Benchmarking {url} (batch_size={batch_size}, requests={num_requests})...")
        prompt_cycle = prompts * ((num_requests // len(prompts)) + 1)
        prompt_cycle = prompt_cycle[:num_requests]

        for batch_start in range(0, num_requests, batch_size):
            batch = prompt_cycle[batch_start:batch_start + batch_size]
            tasks = [
                send_request(session, url, model, p["prompt"], max_tokens, temperature, timeout)
                for p in batch
            ]
            batch_results = await asyncio.gather(*tasks)

            for p, r in zip(batch, batch_results):
                r["prompt_id"] = p.get("id", "unknown")
                r["prompt_category"] = p.get("category", "unknown")
                r["batch_size"] = batch_size
                results.append(r)

    return results


async def run_benchmarks(config_path: str, output_dir: str) -> None:
    """Run benchmarks for all configured endpoints."""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    bench_config = config.get("benchmark", {})
    prompts_file = bench_config.get("prompts_file", "bench/prompts.json")

    with open(prompts_file) as f:
        prompts = json.load(f)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    all_results: dict[str, list[dict]] = {}
    batch_sizes = bench_config.get("batch_sizes", [1, 4, 16])

    for endpoint in config.get("endpoints", []):
        name = endpoint["name"]
        url = endpoint["url"]
        model = endpoint["model"]

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Benchmarking: {name}")
        logger.info(f"{'=' * 60}")

        endpoint_results: list[dict] = []

        for bs in batch_sizes:
            try:
                results = await benchmark_endpoint(
                    url=url,
                    model=model,
                    prompts=prompts,
                    batch_size=bs,
                    max_tokens=bench_config.get("max_tokens", 256),
                    temperature=bench_config.get("temperature", 0.0),
                    warmup_requests=bench_config.get("warmup_requests", 5),
                    num_requests=bench_config.get("num_requests", 50),
                    timeout=bench_config.get("timeout_seconds", 120),
                )
                for r in results:
                    r["endpoint"] = name
                endpoint_results.extend(results)
            except Exception as e:
                logger.error(f"Failed to benchmark {name} at batch_size={bs}: {e}")

        all_results[name] = endpoint_results

        # Save per-endpoint results
        endpoint_file = output_path / f"{name}.json"
        with open(endpoint_file, "w") as f:
            json.dump(endpoint_results, f, indent=2)
        logger.info(f"Saved {len(endpoint_results)} results to {endpoint_file}")

    # Save combined results
    combined_file = output_path / "all_results.json"
    with open(combined_file, "w") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"All results saved to {combined_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark serving endpoints")
    parser.add_argument("--config", default="configs/bench_config.yaml", help="Benchmark config")
    parser.add_argument("--output", default="results/bench", help="Output directory")
    # Single endpoint mode
    parser.add_argument("--endpoint", help="Single endpoint URL to benchmark")
    parser.add_argument("--model", help="Model name for single endpoint mode")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.endpoint:
        # Single endpoint mode
        prompts_file = "bench/prompts.json"
        with open(prompts_file) as f:
            prompts = json.load(f)

        results = asyncio.run(benchmark_endpoint(
            url=args.endpoint,
            model=args.model or "model",
            prompts=prompts,
        ))

        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)
        with open(output_path / "single_endpoint.json", "w") as f:
            json.dump(results, f, indent=2)
    else:
        asyncio.run(run_benchmarks(args.config, args.output))


if __name__ == "__main__":
    main()
