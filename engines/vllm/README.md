# vLLM Engine

This directory contains the vLLM inference engine configuration.

## Supported Models

| Model | Params | VRAM | Best For |
|-------|--------|------|----------|
| **Mistral 7B** (default) | 7B | 14GB | General use, coding |
| Phi-3 Mini | 3.8B | 8GB | Fast testing, development |
| Gemma 2 9B | 9B | 18GB | Complex reasoning |

## What is vLLM?

vLLM is a high-throughput LLM serving engine that implements:

- **Continuous Batching**: Dynamically adds/removes requests from the batch without waiting for all to finish
- **PagedAttention**: Memory-efficient KV cache that eliminates fragmentation (like virtual memory for GPU)
- **CUDA Graphs**: Pre-compiled GPU kernels that reduce launch overhead

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image with vLLM server |
| `models.yaml` | Model configurations and recommendations |

## Quick Start

```bash
# Build the image
docker build -t vllm-engine .

# Run with default model (Phi-3-mini for testing)
docker run --gpus all -p 8001:8000 vllm-engine

# Run with a specific model
docker run --gpus all -p 8001:8000 \
  -e MODEL="meta-llama/Llama-2-7b-chat-hf" \
  -e MAX_MODEL_LEN=4096 \
  vllm-engine
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL` | Phi-3-mini-4k-instruct | HuggingFace model ID |
| `MAX_MODEL_LEN` | 4096 | Maximum context length |
| `TENSOR_PARALLEL_SIZE` | 1 | GPUs for tensor parallelism |
| `GPU_MEMORY_UTILIZATION` | 0.90 | Fraction of VRAM to use |

## Why These Defaults?

- **Phi-3-mini**: Small (3.8B params), fast to load, great for testing infrastructure
- **MAX_MODEL_LEN=4096**: Balances memory vs capability
- **GPU_MEMORY_UTILIZATION=0.90**: Leaves headroom for KV cache growth
