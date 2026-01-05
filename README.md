# LLM Inference Service - From Engines to Scratch

A comprehensive LLM inference service built from the top down, starting with packaged engines and descending to core inference techniques implemented from scratch.

## Project Structure

```
/web            # Next.js playground, console, docs
/gateway        # OpenAI-compatible API, auth, rate limits
/router         # Admission control, scheduling (Tier 2)
/engines        # vLLM, TGI, TRT-LLM backends (Tier 1)
/worker-core    # From-scratch inference implementation (Tier 3)
/bench          # Benchmark harness, prompt suites
/ops            # Docker compose, monitoring, dashboards
/docs           # Trade-offs, reports, decision guides
```

## Milestones

### Tier 1 — Product & Engines
- [x] M1: Service shell (Website, Playground, OpenAI-compatible API) ← **Current**
- [ ] M2: First engine path (vLLM or TGI)
- [ ] M3: Feature toggles (continuous batching, quantization, etc.)
- [ ] M4: Alternative backend (TensorRT-LLM)

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

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

**TL;DR:**
```bash
# Terminal 1: Start gateway
cd gateway && pip install -r requirements.txt && uvicorn main:app --reload

# Terminal 2: Start web
cd web && npm install && npm run dev
```

Then visit http://localhost:3000 for the playground.

## M1 Exit Criteria

- ✅ Playground streams from CPU echo worker
- ✅ curl works with OpenAI-compatible API
- ✅ Requests/latencies logged

