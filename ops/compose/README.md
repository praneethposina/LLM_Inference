# Docker Compose Configuration

This directory contains Docker Compose configurations for the LLM inference stack.

## Files

| File | GPU Required | Purpose |
|------|--------------|---------|
| `docker-compose.yml` | ✅ Yes | Full stack with vLLM |
| `docker-compose.dev.yml` | ❌ No | Development with echo worker |

## Quick Start (GPU)

```bash
# Start with Mistral 7B (default)
docker compose up

# Start with a different model
MODEL=google/gemma-2-9b-it docker compose up

# Start in background
docker compose up -d

# View vLLM loading progress
docker compose logs -f vllm

# Stop everything
docker compose down
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
              │ • Routing   │
              └──────┬──────┘
                     │ internal network
              ┌──────▼──────┐
              │    vLLM     │  :8001
              │             │
              │ • Batching  │
              │ • PagedKV   │
              │ • GPU       │
              └─────────────┘
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL` | `mistralai/Mistral-7B-Instruct-v0.3` | HuggingFace model ID |
| `MAX_MODEL_LEN` | `8192` | Maximum context length |
| `GPU_MEMORY_UTILIZATION` | `0.90` | Fraction of VRAM to use |
| `WORKER_TYPE` | `vllm` | Worker type (`vllm` or `echo`) |

## Volumes

- `llm-hf-cache`: HuggingFace model cache (persists model downloads)
- `llm-gateway-logs`: Gateway request logs

## Troubleshooting

### vLLM not starting
```bash
# Check GPU availability
nvidia-smi

# Check vLLM logs
docker compose logs vllm
```

### Model too large
Reduce context length or switch to smaller model:
```bash
MAX_MODEL_LEN=4096 docker compose up
# or
MODEL=microsoft/Phi-3-mini-4k-instruct docker compose up
```
