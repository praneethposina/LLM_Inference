#!/usr/bin/env python3
"""
Benchmark Runner for LLM Inference Gateway

This script runs benchmark suites against the gateway and measures:
- TTFB (Time to First Byte)
- Total latency
- Tokens per second
- p50/p95/p99 percentiles

Usage:
    python benchmark.py --url http://localhost:8000 --suite short
    python benchmark.py --url http://localhost:8000 --suite all --output results.csv
    
    # Concurrency testing (for batching experiments)
    python benchmark.py --concurrency 1   # Sequential (no batching benefit)
    python benchmark.py --concurrency 10  # Parallel (batching enabled)
"""
import argparse
import asyncio
import json
import time
import statistics
import csv
from pathlib import Path
from typing import Optional
import httpx


class BenchmarkResult:
    """Store results for a single request."""
    def __init__(self):
        self.prompt: str = ""
        self.ttfb: float = 0.0
        self.total_latency: float = 0.0
        self.tokens: int = 0
        self.status: str = "pending"
        self.error: Optional[str] = None


async def run_benchmark_request(
    client: httpx.AsyncClient,
    url: str,
    prompt: str,
    max_tokens: int,
    api_key: str,
    stream: bool = True
) -> BenchmarkResult:
    """Run a single benchmark request."""
    result = BenchmarkResult()
    result.prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
    
    payload = {
        "model": "mistral",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": stream
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    start_time = time.perf_counter()
    first_token_time = None
    token_count = 0
    
    try:
        if stream:
            async with client.stream(
                "POST",
                f"{url}/v1/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    
                    # Record TTFB on first token
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                        result.ttfb = first_token_time - start_time
                    
                    try:
                        chunk = json.loads(data)
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            token_count += 1
                    except json.JSONDecodeError:
                        continue
        else:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            first_token_time = time.perf_counter()
            result.ttfb = first_token_time - start_time
            token_count = data.get("usage", {}).get("completion_tokens", 0)
        
        end_time = time.perf_counter()
        result.total_latency = end_time - start_time
        result.tokens = token_count
        result.status = "success"
        
    except Exception as e:
        result.status = "error"
        result.error = str(e)
        result.total_latency = time.perf_counter() - start_time
    
    return result


async def run_suite(
    url: str,
    suite_path: Path,
    api_key: str,
    concurrency: int = 1
) -> list[BenchmarkResult]:
    """
    Run all prompts in a benchmark suite.
    
    Args:
        concurrency: Number of parallel requests.
            - 1 = sequential (no batching benefit)
            - 10+ = parallel (vLLM batches these together)
    """
    with open(suite_path) as f:
        suite = json.load(f)
    
    prompts = suite["prompts"]
    max_tokens = suite.get("max_tokens", 100)
    
    print(f"\n📊 Running suite: {suite['name']}")
    print(f"   Prompts: {len(prompts)}, Max tokens: {max_tokens}, Concurrency: {concurrency}")
    
    results = []
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Use semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrency)
        
        async def run_with_semaphore(prompt: str) -> BenchmarkResult:
            async with semaphore:
                return await run_benchmark_request(
                    client, url, prompt, max_tokens, api_key, stream=True
                )
        
        if concurrency == 1:
            # Sequential mode: one at a time (for baseline)
            for i, prompt in enumerate(prompts):
                print(f"   [{i+1}/{len(prompts)}] Running (sequential)...", end="\r")
                result = await run_benchmark_request(
                    client, url, prompt, max_tokens, api_key, stream=True
                )
                results.append(result)
        else:
            # Concurrent mode: run in parallel (to trigger batching)
            print(f"   Running {len(prompts)} requests with concurrency={concurrency}...")
            tasks = [run_with_semaphore(prompt) for prompt in prompts]
            results = await asyncio.gather(*tasks)
    
    print(f"   ✅ Completed {len(results)} requests")
    return list(results)


def calculate_stats(results: list[BenchmarkResult]) -> dict:
    """Calculate statistics from benchmark results."""
    successful = [r for r in results if r.status == "success"]
    
    if not successful:
        return {"error": "No successful requests"}
    
    ttfbs = [r.ttfb for r in successful]
    latencies = [r.total_latency for r in successful]
    tokens = [r.tokens for r in successful]
    
    # Calculate tokens per second
    tokens_per_sec = [
        r.tokens / r.total_latency if r.total_latency > 0 else 0 
        for r in successful
    ]
    
    def percentile(data, p):
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * p / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]
    
    return {
        "count": len(successful),
        "errors": len(results) - len(successful),
        "ttfb_p50": round(percentile(ttfbs, 50) * 1000, 2),  # ms
        "ttfb_p95": round(percentile(ttfbs, 95) * 1000, 2),
        "ttfb_p99": round(percentile(ttfbs, 99) * 1000, 2),
        "latency_p50": round(percentile(latencies, 50) * 1000, 2),
        "latency_p95": round(percentile(latencies, 95) * 1000, 2),
        "latency_p99": round(percentile(latencies, 99) * 1000, 2),
        "tokens_avg": round(statistics.mean(tokens), 1),
        "tokens_per_sec_avg": round(statistics.mean(tokens_per_sec), 1),
        "tokens_per_sec_p50": round(percentile(tokens_per_sec, 50), 1),
    }


def print_stats(suite_name: str, stats: dict):
    """Print statistics in a formatted table."""
    print(f"\n{'='*60}")
    print(f" {suite_name.upper()} RESULTS")
    print(f"{'='*60}")
    
    if "error" in stats:
        print(f" ❌ {stats['error']}")
        return
    
    print(f" Requests: {stats['count']} successful, {stats['errors']} errors")
    print()
    print(f" {'Metric':<20} {'p50':<12} {'p95':<12} {'p99':<12}")
    print(f" {'-'*20} {'-'*12} {'-'*12} {'-'*12}")
    print(f" {'TTFB (ms)':<20} {stats['ttfb_p50']:<12} {stats['ttfb_p95']:<12} {stats['ttfb_p99']:<12}")
    print(f" {'Latency (ms)':<20} {stats['latency_p50']:<12} {stats['latency_p95']:<12} {stats['latency_p99']:<12}")
    print()
    print(f" Avg tokens: {stats['tokens_avg']}")
    print(f" Tokens/sec: {stats['tokens_per_sec_avg']} (avg), {stats['tokens_per_sec_p50']} (p50)")


def save_csv(all_results: dict, output_path: str):
    """Save results to CSV file."""
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "suite", "count", "errors",
            "ttfb_p50_ms", "ttfb_p95_ms", "ttfb_p99_ms",
            "latency_p50_ms", "latency_p95_ms", "latency_p99_ms",
            "tokens_avg", "tokens_per_sec_avg", "tokens_per_sec_p50"
        ])
        
        for suite_name, stats in all_results.items():
            if "error" not in stats:
                writer.writerow([
                    suite_name, stats["count"], stats["errors"],
                    stats["ttfb_p50"], stats["ttfb_p95"], stats["ttfb_p99"],
                    stats["latency_p50"], stats["latency_p95"], stats["latency_p99"],
                    stats["tokens_avg"], stats["tokens_per_sec_avg"], stats["tokens_per_sec_p50"]
                ])
    
    print(f"\n📁 Results saved to: {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="LLM Inference Benchmark")
    parser.add_argument("--url", default="http://localhost:8000", help="Gateway URL")
    parser.add_argument("--suite", default="all", choices=["short", "medium", "long", "stress", "all"])
    parser.add_argument("--api-key", default="sk-dev-default-key-12345", help="API key")
    parser.add_argument("--output", help="Output CSV file path")
    parser.add_argument("--concurrency", type=int, default=1, 
                        help="Number of parallel requests (1=sequential, 10+=batched)")
    
    args = parser.parse_args()
    
    prompts_dir = Path(__file__).parent / "prompts"
    
    if args.suite == "all":
        suites = ["short", "medium", "long", "stress"]
    else:
        suites = [args.suite]
    
    print(f"🚀 LLM Inference Benchmark")
    print(f"   URL: {args.url}")
    print(f"   Suites: {', '.join(suites)}")
    print(f"   Concurrency: {args.concurrency}")
    
    all_results = {}
    
    for suite_name in suites:
        suite_path = prompts_dir / f"{suite_name}.json"
        if not suite_path.exists():
            print(f"⚠️  Suite not found: {suite_path}")
            continue
        
        results = await run_suite(args.url, suite_path, args.api_key, args.concurrency)
        stats = calculate_stats(results)
        all_results[suite_name] = stats
        print_stats(suite_name, stats)
    
    if args.output:
        save_csv(all_results, args.output)
    
    print("\n✅ Benchmark complete!")


if __name__ == "__main__":
    asyncio.run(main())
