# LLM Inference Service - From Engines to Scratch

A comprehensive LLM inference service built from the top down, starting with packaged engines and descending to core inference techniques implemented from scratch.

## Project Structure

```
/web            # Next.js playground, console, docs
/gateway        # OpenAI-compatible API, auth, rate limits, feature routing
/router         # Admission control, scheduling (Tier 2)
/engines        # vLLM, TGI, TRT-LLM backends (Tier 1)
/worker-core    # From-scratch inference implementation (Tier 3)
/bench          # Benchmark harness, prompt suites, concurrency testing
/ops            # Docker Compose, Prometheus, Grafana dashboards
/docs           # Trade-offs, reports, decision guides
```

## Milestones

### Tier 1 — Product & Engines
- [x] M1: Service shell (Website, Playground, OpenAI-compatible API)
- [x] M2: First engine path (vLLM + Prometheus + Grafana + benchmarking)
- [x] M3: Feature toggles (batching, quantization, TGI, TRT-LLM, tensor parallel) ← **Current**
- [ ] M4: Alternative backend comparisons & reports

### Tier 2 — Middle Layer
- [ ] M5: Router/scheduler with admission control
- [ ] M6: Memory-aware routing and batching
- [ ] M7: Speculative decoding orchestration

### Tier 3 — From Scratch
- [ ] M8: Minimal inference loop
- [ ] M9: Continuous batching from scratch
- [ ] M10: Paged KV cache
- [ ] M11: Quantization
- [ ] M12: Speculative decoding core
- [ ] M13: Triton/CUDA kernels
- [ ] M14: Multi-GPU (optional)

## Architecture — Port Map

| Service | Port | Profile | Engine |
|---------|------|---------|--------|
| Gateway | `8000` | default | — |
| vLLM | `8001` | default | vLLM |
| vLLM Quant (AWQ) | `8002` | `--profile quant` | vLLM |
| TGI (1 GPU) | `8003` | `--profile tgi` | HuggingFace TGI |
| TGI-TP (2 GPU) | `8004` | `--profile tgi-tp` | HuggingFace TGI |
| TRT-LLM | `8005` | `--profile trt` | TensorRT-LLM |
| Prometheus | `9292` | default | — |
| Grafana | `3030` | default | — |

## Quick Start

### Full Stack (Docker Compose on Lightning.ai)

```bash
cd ops/compose
docker compose up -d                    # vLLM + Gateway + Prometheus + Grafana
docker compose --profile tgi up -d      # + TGI backend
docker compose --profile tgi-tp up -d   # + TGI 2-GPU tensor parallel
docker compose --profile quant up -d    # + AWQ quantized vLLM
```

### Local Dev (no GPU)

```bash
# Terminal 1: Gateway with echo worker
cd gateway && pip install -r requirements.txt && uvicorn main:app --reload

# Terminal 2: Web playground
cd web && npm install && npm run dev
```

### Benchmarking

```bash
cd bench && pip install httpx
python benchmark.py --concurrency 1 --suite short --output baseline.csv
python benchmark.py --concurrency 10 --suite short --output batched.csv
```

Then visit http://localhost:3000 for the playground, http://localhost:3030 for Grafana.

## M3 Feature Toggles

Toggle backends via request headers:
- `X-Backend: vllm | vllm-quant | tgi | tgi-tp | trt`
- `X-Quant: none | awq | int8 | fp8`

### Experiments
| Technique | What to Compare | KPIs |
|-----------|----------------|------|
| Continuous Batching | `--concurrency 1` vs `10` | tokens/s, p95 |
| Paged KV | `--suite stress`, rising concurrency | VRAM/token, OOMs |
| Quantization | FP16 (port 8001) vs AWQ (port 8002) | VRAM, tokens/s |
| Tensor Parallel | TGI 1-GPU vs TGI-TP 2-GPU | p95, memory |
| FP8 + Graphs | TRT-LLM short prompts | TTFB, p95 |
