# Docker Compose Configuration

This directory contains Docker Compose configurations for the LLM inference stack.

## Services

| Service | Port | Profile | Engine | GPU |
|---------|------|---------|--------|-----|
| Gateway | `8000` | default | FastAPI | — |
| vLLM | `8001` | default | vLLM (FP16) | GPU 0 |
| vLLM Quant | `8002` | `--profile quant` | vLLM (AWQ 4-bit) | GPU 1 |
| TGI | `8003` | `--profile tgi` | HuggingFace TGI | 1 GPU |
| TGI-TP | `8004` | `--profile tgi-tp` | HuggingFace TGI (2-GPU tensor parallel) | 2 GPUs |
| TRT-LLM | `8005` | `--profile trt` | TensorRT-LLM | 1 GPU |
| Prometheus | `9292` | default | — | — |
| Grafana | `3030` | default | — | — |

## Files

| File | GPU Required | Purpose |
|------|--------------|---------|
| `docker-compose.yml` | ✅ Yes | Full stack with vLLM |
| `docker-compose.dev.yml` | ❌ No | Development with echo worker |

## Quick Start

```bash
# Start core stack (vLLM + Gateway + Prometheus + Grafana)
docker compose up -d

# View vLLM loading progress
docker compose logs -f vllm

# Stop everything
docker compose down
```

### M3 Experiment Profiles

```bash
# AWQ quantized vLLM (runs on GPU 1)
docker compose --profile quant up -d vllm-quant

# HuggingFace TGI
docker compose --profile tgi up -d tgi

# TGI with 2-GPU tensor parallel
docker compose --profile tgi-tp up -d tgi-tp

# TensorRT-LLM (requires pre-built engine)
docker compose --profile trt up -d trt
```

## Quick Start (No GPU / Development)

```bash
docker compose -f docker-compose.dev.yml up
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Your App      │     │   Playground    │
│  (curl/SDK)     │     │   (React)       │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │   Gateway   │  :8000
              │  (FastAPI)  │
              │             │
              │ • Auth      │
              │ • Logging   │
              │ • X-Backend │  ← Routes to different engines
              └──────┬──────┘
                     │ internal network
         ┌───────────┼───────────┐
         │           │           │
  ┌──────▼──────┐ ┌──▼──┐ ┌─────▼─────┐
  │    vLLM     │ │ TGI │ │  TRT-LLM  │
  │   :8001     │ │:8003│ │   :8005   │
  │   GPU 0     │ │     │ │           │
  └─────────────┘ └─────┘ └───────────┘
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL` | `mistralai/Mistral-7B-Instruct-v0.3` | HuggingFace model ID |
| `MAX_MODEL_LEN` | `8192` | Maximum context length |
| `GPU_MEMORY_UTILIZATION` | `0.90` | Fraction of VRAM to use |
| `WORKER_TYPE` | `vllm` | Worker type (`vllm`, `tgi`, or `echo`) |

## GPU Pinning

vLLM and vLLM-quant are pinned to separate GPUs to run simultaneously:

| Service | GPU | Purpose |
|---------|-----|---------|
| vLLM (FP16) | `CUDA_VISIBLE_DEVICES=0` | Baseline model |
| vLLM Quant (AWQ) | `CUDA_VISIBLE_DEVICES=1` | Quantization comparison |

## Volumes

- `huggingface_cache`: HuggingFace model cache (persists model downloads)
- `llm-gateway-logs`: Gateway request logs
- `llm-grafana-data`: Grafana dashboards and settings
- `llm-prometheus-data`: Prometheus time series data

## Troubleshooting

### vLLM not starting
```bash
nvidia-smi                  # Check GPU availability
docker compose logs vllm    # Check vLLM logs
```

### Model too large
```bash
MAX_MODEL_LEN=4096 docker compose up
# or use smaller model
MODEL=microsoft/Phi-3-mini-4k-instruct docker compose up
```

### GPU memory conflict (vllm-quant fails)
Both vLLM services try to use the same GPU. Ensure `CUDA_VISIBLE_DEVICES` pins them to separate GPUs (already configured).

### Grafana shows "No data"
1. Check Prometheus is scraping: http://localhost:9292/targets
2. Verify datasource UID matches: Grafana → Connections → Data Sources
3. Recreate Grafana if needed: `docker compose down grafana && docker volume rm llm-grafana-data && docker compose up -d grafana`
