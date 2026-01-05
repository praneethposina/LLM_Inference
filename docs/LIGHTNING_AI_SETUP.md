# Testing on Lightning.ai Cloud GPU

This guide walks you through deploying and testing the LLM inference stack on Lightning.ai with an A100 GPU.

## Prerequisites

- Lightning.ai account with GPU credits
- This repo cloned to your local machine

---

## Step 1: Create a Lightning.ai Studio

1. Go to [lightning.ai](https://lightning.ai) and log in
2. Click **"New Studio"**
3. Select **"A100 (40GB)"** GPU
4. Give it a name (e.g., "llm-inference")
5. Click **"Create"**

---

## Step 2: Connect via SSH

### Option A: Web Terminal (Easiest)
1. In your Studio, click the **"Terminal"** tab
2. You're now in a terminal on the GPU machine

### Option B: SSH from Local (Better for file sync)
1. In your Studio, click **"Connect via SSH"**
2. Follow the instructions to add SSH config
3. Then from your local terminal:
   ```bash
   ssh <your-studio-name>
   ```

---

## Step 3: Clone Your Repo

In the Lightning.ai terminal:

```bash
# Clone your repo (or sync with git)
git clone https://github.com/YOUR_USERNAME/LLM_Inference.git
cd LLM_Inference

# Or if syncing from local, use scp:
# scp -r /Users/praneethposina/Documents/LLM_Inference <studio-ssh>:~/
```

---

## Step 4: Verify GPU & Docker

```bash
# Check GPU is available
nvidia-smi

# Check Docker is installed
docker --version
docker compose version
```

You should see your A100 40GB GPU and Docker installed.

---

## Step 5: Start the Stack

```bash
cd ops/compose

# Start with Mistral 7B (default) - this will:
# 1. Build the gateway container
# 2. Pull vLLM container
# 3. Download Mistral 7B model (~14GB, takes 2-5 min first time)
docker compose up

# Watch for "Model loaded" in vLLM logs
```

**First run takes ~5-10 minutes** (downloading model). Subsequent runs are fast.

---

## Step 6: Test the API

Open a second terminal (or new tab in Lightning.ai):

```bash
# Health check
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models

# Chat completion (non-streaming)
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [{"role": "user", "content": "What is the capital of France?"}],
    "max_tokens": 50
  }'

# Chat completion (streaming)
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [{"role": "user", "content": "Explain machine learning in 3 sentences."}],
    "max_tokens": 100,
    "stream": true
  }'
```

---

## Step 7: Try Different Models

```bash
# Stop current stack
docker compose down

# Start with Phi-3 (faster, smaller)
MODEL=microsoft/Phi-3-mini-4k-instruct docker compose up

# Or Gemma 9B (better reasoning)
MODEL=google/gemma-2-9b-it docker compose up
```

---

## Troubleshooting

### vLLM not starting
```bash
# Check logs
docker compose logs vllm

# Check GPU memory
nvidia-smi
```

### Model OOM (out of memory)
```bash
# Reduce context length
MAX_MODEL_LEN=4096 docker compose up

# Or use smaller model
MODEL=microsoft/Phi-3-mini-4k-instruct docker compose up
```

### Gateway can't connect to vLLM
```bash
# Check vLLM health
curl http://localhost:8001/health

# vLLM takes time to load - wait for "Model loaded" in logs
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `docker compose up` | Start stack (foreground) |
| `docker compose up -d` | Start in background |
| `docker compose down` | Stop stack |
| `docker compose logs -f vllm` | Watch vLLM logs |
| `docker compose logs -f gateway` | Watch gateway logs |
| `nvidia-smi` | Check GPU usage |
