# vLLM Engine Container
# 
# This Dockerfile creates a vLLM inference server optimized for A100 GPUs.
# vLLM provides high-throughput LLM serving with:
#   - Continuous batching (dynamically batches requests)
#   - PagedAttention (efficient KV cache memory management)
#   - CUDA graph optimization (reduces kernel launch overhead)
#
# Supported Models (all fit on A100 40GB):
#   - mistralai/Mistral-7B-Instruct-v0.3 (default, best quality/speed)
#   - microsoft/Phi-3-mini-4k-instruct (fast, good for testing)
#   - google/gemma-2-9b-it (strong reasoning, instruction tuned)
#
# Usage:
#   docker build -t vllm-engine .
#   docker run --gpus all -p 8001:8000 vllm-engine
#   docker run --gpus all -p 8001:8000 -e MODEL="google/gemma-2-9b-it" vllm-engine

FROM vllm/vllm-openai:latest

# Environment variables - Mistral 7B as default (best balance of quality/speed)
# Override at runtime: docker run -e MODEL="google/gemma-2-9b-it" ...
ENV MODEL="mistralai/Mistral-7B-Instruct-v0.3"
ENV MAX_MODEL_LEN=8192
ENV TENSOR_PARALLEL_SIZE=1
ENV GPU_MEMORY_UTILIZATION=0.90
ENV HOST="0.0.0.0"
ENV PORT=8000

# vLLM exposes an OpenAI-compatible API by default
EXPOSE 8000

# Run vLLM's OpenAI-compatible server
CMD python -m vllm.entrypoints.openai.api_server \
    --model $MODEL \
    --max-model-len $MAX_MODEL_LEN \
    --tensor-parallel-size $TENSOR_PARALLEL_SIZE \
    --gpu-memory-utilization $GPU_MEMORY_UTILIZATION \
    --host $HOST \
    --port $PORT \
    --trust-remote-code
