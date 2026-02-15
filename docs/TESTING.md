# Testing Guide

How to verify each component of the LLM Inference stack is working correctly.

---

## 1. GPU & Docker (Lightning.ai)

```bash
nvidia-smi                # Should show A100 40GB (×2)
docker --version          # Docker installed
docker compose version    # Compose v2+
```

---

## 2. Docker Compose Services

```bash
cd ~/LLM_Inference/ops/compose
docker compose up -d
docker compose ps
```

**Expected output — 4 healthy services:**

| Service | Status | Port |
|---------|--------|------|
| llm-vllm | healthy | 8001→8000 |
| llm-gateway | healthy | 8000→8000 |
| llm-prometheus | running | 9292→9090 |
| llm-grafana | running | 3030→3000 |

> **Note:** vLLM takes 1–3 min to become healthy (model loading). Gateway may show unhealthy until vLLM is ready.

### Checking Logs

```bash
docker compose logs -f vllm      # Wait for "Uvicorn running on http://0.0.0.0:8000"
docker compose logs gateway      # Check for import errors
docker compose logs prometheus   # Check scrape errors
docker compose logs grafana      # Check datasource provisioning
```

---

## 3. vLLM Engine

```bash
# Direct health check (internal port)
curl http://localhost:8001/health

# List loaded models
curl http://localhost:8001/v1/models

# Direct inference (bypasses gateway)
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistralai/Mistral-7B-Instruct-v0.3",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 20
  }'
```

**Expected:** JSON response with generated text in `choices[0].message.content`.

---

## 4. Gateway API

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# List models (proxied through gateway)
curl http://localhost:8000/v1/models

# Non-streaming chat
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -d '{
    "model": "mistral",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50,
    "stream": false
  }'

# Streaming chat
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -d '{
    "model": "mistral",
    "messages": [{"role": "user", "content": "Explain SSH tunnels in 3 sentences"}],
    "max_tokens": 100,
    "stream": true
  }'
```

**Expected (streaming):** Lines starting with `data: {...}` containing token chunks, ending with `data: [DONE]`.

### Auth Verification

```bash
# Missing key → 401
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","messages":[{"role":"user","content":"test"}]}'

# Bad key → 401
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer wrong-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","messages":[{"role":"user","content":"test"}]}'
```

---

## 5. SSH Tunnel (Local Mac → Lightning.ai)

```bash
# Open tunnel (run on your Mac, keep terminal open)
ssh -L 8080:localhost:8000 \
    -L 9292:localhost:9292 \
    -L 3030:localhost:3030 \
    s_01ke5v1ghk5yz3c74668bdx3b6@ssh.lightning.ai
```

### Verify Tunnel

```bash
# On your Mac, in a separate terminal:
curl http://localhost:8080/health
# Expected: {"status": "healthy"}

curl http://localhost:8080/v1/models
# Expected: model list from vLLM
```

**If "Connection refused":** The gateway isn't running on Lightning.ai. SSH into Lightning.ai and run `docker compose up -d`.

---

## 6. Frontend (Playground)

```bash
# On Mac:
cd /Users/praneethposina/Documents/LLM_Inference/web
NEXT_PUBLIC_GATEWAY_URL=http://localhost:8080 npm run dev
```

### Verify

1. Open http://localhost:3000
2. Type a message in the chat
3. You should see streaming tokens appear

**If "Failed to fetch":** Check that the SSH tunnel is alive (`curl http://localhost:8080/health`).

---

## 7. Gateway Metrics

```bash
curl http://localhost:8000/metrics
```

**Expected metrics (after sending requests):**

| Metric | Description |
|--------|-------------|
| `llm_requests_total` | Counter of total requests by model/status |
| `llm_request_latency_seconds` | Histogram of request latency |
| `llm_ttfb_seconds` | Histogram of time-to-first-byte |
| `llm_active_requests` | Gauge of currently active requests |
| `llm_tokens_generated_total` | Counter of tokens generated |
| `llm_tokens_per_request` | Histogram of tokens per request |
| `llm_prompt_tokens` | Histogram of prompt token counts |

---

## 8. Prometheus

### On Lightning.ai

```bash
# Check Prometheus is running
curl http://localhost:9292/-/healthy
# Expected: Prometheus Server is Healthy.

# Check scrape targets
curl -s http://localhost:9292/api/v1/targets | python3 -m json.tool
```

**Expected targets:**

| Target | Health |
|--------|--------|
| `gateway:8000` | **up** |
| `vllm:8000` | **up** |
| `localhost:9090` (prometheus self) | **up** |
| `tgi:8000` | down (expected if not running) |
| `trt:8000` | down (expected if not running) |

### Query Test

```bash
# Total requests
curl -s 'http://localhost:9292/api/v1/query?query=llm_requests_total' | python3 -m json.tool

# Average latency
curl -s 'http://localhost:9292/api/v1/query?query=llm_request_latency_seconds_sum/llm_request_latency_seconds_count' | python3 -m json.tool
```

### Via Browser (through tunnel)

Open http://localhost:9292, try these queries:
- `llm_requests_total` → total request count by model
- `llm_active_requests` → currently in-flight requests
- `rate(llm_requests_total[5m])` → request rate (needs active traffic)
- **Status → Targets** → verify gateway and vllm show as UP

---

## 9. Grafana

### Access

- **URL:** http://localhost:3030 (through tunnel)
- **Login:** username - admin, password - llminference

### Dashboard Panels

Navigate to **Dashboards → LLM Inference Dashboard**:

| Panel | Type | Shows Data When |
|-------|------|-----------------|
| Avg Latency | stat (instant) | Any requests have been made |
| Avg TTFB | stat (instant) | Any requests have been made |
| Total Requests | stat (instant) | Any requests have been made |
| Total Tokens | stat (instant) | Any requests have been made |
| Request Rate | time series | Active traffic in last 5min |
| Token Rate | time series | Active traffic in last 5min |
| Latency p50/p95 | time series | Active traffic in last 5min |
| TTFB p50/p95 | time series | Active traffic in last 5min |
| Active Requests | time series | During active requests |

### Datasource Test

1. Go to **Connections → Data Sources → Prometheus**
2. Click **Test** → should say "Data source is working"
3. If not: datasource URL should be `http://prometheus:9090`, UID should be `prometheus`

### Troubleshooting "No Data"

```bash
# On Lightning.ai — recreate Grafana with fresh volume
docker compose down grafana
docker volume rm llm-grafana-data
docker compose up -d grafana
```

---

## 10. Benchmarks

```bash
cd ~/LLM_Inference/bench
pip install httpx

# Quick test (short suite, sequential)
python benchmark.py --suite short --concurrency 1

# Batching comparison
python benchmark.py --suite short --concurrency 1 --output results/c1.csv
python benchmark.py --suite short --concurrency 10 --output results/c10.csv

# Stress test (long prompts, paged KV cache)
python benchmark.py --suite stress --concurrency 5
```

### Expected Output

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
 TTFB (ms)            ~50-150      ~100-250     ~150-300
 Latency (ms)         ~300-800     ~500-1200    ~700-1500

 Avg tokens: ~35
 Tokens/sec: ~40-80
```

### Remote Benchmarks (through tunnel, from Mac)

```bash
cd /Users/praneethposina/Documents/LLM_Inference/bench
python benchmark.py --url http://localhost:8080 --suite short
```

> ⚠️ Tunnel adds ~20ms latency. Run from Lightning.ai for accurate numbers.

---

## 11. vLLM Quantized (AWQ) — M3 Experiment

```bash
# Start quant service (uses GPU 1)
docker compose --profile quant up -d vllm-quant
docker compose logs -f vllm-quant    # Wait for healthy

# Direct test
curl http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TheBloke/Mistral-7B-Instruct-v0.2-AWQ",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'

# Benchmark comparison
python benchmark.py --url http://localhost:8002 --suite short --output results/quant.csv
```

> **Requires 2 GPUs.** vLLM (FP16) is pinned to GPU 0, vLLM-quant (AWQ) to GPU 1.

---

## Quick Smoke Test (All-in-One)

Run this on Lightning.ai to verify the full stack in ~30 seconds:

```bash
echo "=== 1. Docker Status ==="
cd ~/LLM_Inference/ops/compose && docker compose ps

echo "=== 2. Gateway Health ==="
curl -s http://localhost:8000/health

echo "=== 3. Models ==="
curl -s http://localhost:8000/v1/models | python3 -m json.tool

echo "=== 4. Chat Test ==="
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -d '{"model":"mistral","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5}' \
  | python3 -m json.tool

echo "=== 5. Metrics ==="
curl -s http://localhost:8000/metrics | grep llm_requests_total

echo "=== 6. Prometheus ==="
curl -s http://localhost:9292/-/healthy

echo "=== 7. Grafana ==="
curl -s -o /dev/null -w "%{http_code}" http://localhost:3030/login
```

**Expected:** All return valid responses, Grafana returns `200`.


testing playbook. Run these on Lightning.ai in order:

Step 1: Sync Code to Lightning.ai
bash
# On your Mac
cd /Users/praneethposina/Documents/LLM_Inference
git add -A && git commit -m "M3: feature toggles setup" && git push
# On Lightning.ai
cd ~/LLM_Inference && git pull
Step 2: Rebuild Gateway (has new workers)
bash
cd ~/LLM_Inference/ops/compose
docker compose build gateway
Step 3: Start Default Stack
bash
docker compose up -d
# Wait for vLLM to be healthy
docker compose logs -f vllm  # Watch until "Uvicorn running..."
Step 4: Run Experiments
Experiment 1: Continuous Batching
bash
cd ~/LLM_Inference/bench
pip install httpx
# Baseline: sequential (no batching)
python benchmark.py --concurrency 1 --suite short --output results/baseline_c1.csv
# Batched: 10 concurrent requests
python benchmark.py --concurrency 10 --suite short --output results/batched_c10.csv
Compare: tokens/s should be higher with concurrency=10.

Experiment 2: Paged KV Stress
bash
# Long prompts, rising concurrency
python benchmark.py --concurrency 1 --suite stress --output results/stress_c1.csv
python benchmark.py --concurrency 5 --suite stress --output results/stress_c5.csv
python benchmark.py --concurrency 10 --suite stress --output results/stress_c10.csv
# Monitor VRAM during test
nvidia-smi --query-gpu=memory.used --format=csv -l 2
Experiment 3: Quantization (needs both vLLM instances)
bash
# Start quantized vLLM
docker compose --profile quant up -d vllm-quant
docker compose logs -f vllm-quant  # Wait until healthy
# Benchmark FP16
python benchmark.py --url http://localhost:8001 --suite medium --output results/fp16.csv
# Benchmark AWQ INT4
python benchmark.py --url http://localhost:8002 --suite medium --output results/awq.csv
Compare: AWQ should use ~4x less VRAM, similar tokens/s.

Experiment 4: TGI Comparison
bash
# Start TGI
docker compose --profile tgi up -d tgi
docker compose logs -f tgi  # Wait until healthy
# Benchmark TGI
python benchmark.py --url http://localhost:8003 --suite medium --output results/tgi.csv
Compare: vLLM vs TGI tokens/s and TTFB.

Experiment 5: Tensor Parallel (2 GPU)
bash
# Start TGI with 2 GPUs
docker compose --profile tgi-tp up -d tgi-tp
docker compose logs -f tgi-tp  # Wait until healthy
# Benchmark 2-GPU
python benchmark.py --url http://localhost:8004 --suite medium --output results/tgi_tp.csv
Step 5: Create Results Directory First
bash
mkdir -p ~/LLM_Inference/bench/results
Quick Checks Between Experiments
bash
# Check VRAM usage
nvidia-smi
# Check what's running
docker compose ps
# Stop a specific profile
docker compose --profile quant stop vllm-quant
Start with Steps 1-3, then run Experiment 1 first (batching)