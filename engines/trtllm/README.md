# TensorRT-LLM Engine Setup

## Overview

TensorRT-LLM requires a **pre-compiled engine** (unlike vLLM/TGI which load HuggingFace models directly). This step converts a HuggingFace model into an optimized TRT-LLM engine.

## Build Steps (on Lightning.ai)

### 1. Pull the TRT-LLM build image

```bash
docker pull nvcr.io/nvidia/tritonserver:24.01-trtllm-python-py3
```

### 2. Convert HuggingFace model to TRT-LLM checkpoint

```bash
docker run --gpus all -it --rm \
  -v llm-hf-cache:/root/.cache/huggingface \
  -v $(pwd)/engines:/engines \
  nvcr.io/nvidia/tritonserver:24.01-trtllm-python-py3 \
  python /opt/scripts/convert_checkpoint.py \
    --model_dir /root/.cache/huggingface/hub/models--mistralai--Mistral-7B-Instruct-v0.3 \
    --output_dir /engines/mistral-7b-checkpoint \
    --dtype float16
```

### 3. Build the TRT-LLM engine

```bash
# FP16 engine (baseline)
trtllm-build \
  --checkpoint_dir /engines/mistral-7b-checkpoint \
  --output_dir /engines/mistral-7b-fp16 \
  --max_batch_size 8 \
  --max_input_len 4096 \
  --max_seq_len 8192

# FP8 engine (quantized - Hopper GPUs)
trtllm-build \
  --checkpoint_dir /engines/mistral-7b-checkpoint \
  --output_dir /engines/mistral-7b-fp8 \
  --max_batch_size 8 \
  --max_input_len 4096 \
  --max_seq_len 8192 \
  --use_fp8
```

### 4. Start with docker compose

```bash
cd ops/compose
docker compose --profile trt up trt
```

## Engine Directory Structure

```
engines/trtllm/engines/
├── mistral-7b-fp16/       # FP16 baseline engine
│   ├── config.json
│   └── rank0.engine
└── mistral-7b-fp8/        # FP8 quantized engine
    ├── config.json
    └── rank0.engine
```

## Port

TRT-LLM runs on **port 8005** (host) → 8000 (container).
