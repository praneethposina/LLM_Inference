# Benchmark Suite

Tools for measuring LLM inference performance.

## Quick Start

```bash
# Run all benchmark suites
python benchmark.py --url http://localhost:8000

# Run specific suite
python benchmark.py --url http://localhost:8000 --suite short

# Save results to CSV
python benchmark.py --url http://localhost:8000 --output results.csv

# Concurrency testing (M3 batching experiment)
python benchmark.py --concurrency 1   # Sequential (no batching)
python benchmark.py --concurrency 10  # Parallel (vLLM batches these)
```

## Prompt Suites

| Suite | Prompts | Tokens | Purpose |
|-------|---------|--------|---------|
| `short` | 10 | 50 | TTFB and overhead testing |
| `medium` | 10 | 200 | Typical use case |
| `long` | 5 | 500 | Stress testing, long context |
| `stress` | 5 | 1000 | Paged KV cache stress (extra-long prompts) |

## Metrics Collected

- **TTFB (Time to First Byte)**: Time until first token streams
- **Latency**: Total request time (prefill + decode)
- **Tokens/second**: Generation throughput
- **Percentiles**: p50, p95, p99 for each metric

## Example Output

```
📊 Running suite: short
   Prompts: 10, Max tokens: 50
   ✅ Completed 10 requests

============================================================
 SHORT RESULTS
============================================================
 Requests: 10 successful, 0 errors

 Metric               p50          p95          p99         
 -------------------- ------------ ------------ ------------
 TTFB (ms)            150          200          250         
 Latency (ms)         500          700          900         

 Avg tokens: 35.2
 Tokens/sec: 70.4 (avg), 65.0 (p50)
```

## CSV Output Format

| Column | Description |
|--------|-------------|
| suite | Benchmark suite name |
| count | Successful requests |
| errors | Failed requests |
| ttfb_p50_ms | TTFB 50th percentile |
| latency_p50_ms | Latency 50th percentile |
| tokens_per_sec_avg | Average tokens/second |
