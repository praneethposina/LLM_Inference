# Connecting Lightning.ai Backend to Your Local Machine

## Architecture Overview

```
┌─────────────────────────────────────┐      ┌──────────────────────────────────┐
│          YOUR MAC (Local)           │      │       LIGHTNING.AI (Remote)      │
│                                     │      │                                  │
│  Browser → localhost:3000           │      │  Gateway      → :8000            │
│     │                               │      │     │                            │
│  Next.js ──→ localhost:8080 ────────┼──SSH─┼──→ :8000 ──→ vLLM → GPU (A100)   │
│  (frontend)  (tunnel)               │      │                                  │
│                                     │      │  Prometheus   → :9292            │
│  curl ─────→ localhost:8080 ────────┼──SSH─┼──→ :8000                         │
│                                     │      │  Grafana      → :3030            │
└─────────────────────────────────────┘      └──────────────────────────────────┘
```

**Key idea:** The backend (Gateway + vLLM + GPU) runs on Lightning.ai. You use SSH tunnels to make it feel like it's running locally.

---

## Step 1: Start Backend on Lightning.ai

### 1a. SSH into Lightning.ai

```bash
ssh s_01ke5v1ghk5yz3c74668bdx3b6@ssh.lightning.ai
```

### 1b. Sync Code

```bash
cd ~/LLM_Inference
git pull
```

### 1c. Start Docker Compose

```bash
cd ~/LLM_Inference/ops/compose
docker compose up -d
```

### 1d. Verify Everything is Running

```bash
# Check container status
docker compose ps

# Watch vLLM startup (takes 1-3 min for model loading)
docker compose logs -f vllm

# Wait until you see:
# "Uvicorn running on http://0.0.0.0:8000"
# or health checks returning 200 OK
```

### 1e. Quick Test (on Lightning.ai)

```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy"}

curl http://localhost:8000/v1/models
# Should return the loaded model name
```

---

## Step 2: Create SSH Tunnel (on Your Mac)

Open a **new terminal** on your Mac:

```bash
ssh -L 8080:localhost:8000 s_01ke5v1ghk5yz3c74668bdx3b6@ssh.lightning.ai
```

**What this does:**
- `-L 8080:localhost:8000` = Forward your Mac's port 8080 → Lightning.ai's port 8000
- Now `localhost:8080` on your Mac reaches the Gateway on Lightning.ai

**Keep this terminal open!** The tunnel dies if you close it.

### Verify the Tunnel

```bash
# In a separate terminal on your Mac:
curl http://localhost:8080/health
# Should return: {"status": "healthy"}
```

### Optional: Multiple Tunnels

If you want access to Prometheus or Grafana locally too:

```bash
# All-in-one tunnel (Gateway + Prometheus + Grafana)
ssh -L 8080:localhost:8000 \
    -L 9292:localhost:9292 \
    -L 3030:localhost:3030 \
    s_01ke5v1ghk5yz3c74668bdx3b6@ssh.lightning.ai
```

Then:
- `localhost:8080` → Gateway API
- `localhost:9292` → Prometheus
- `localhost:3030` → Grafana (login: admin / llminference)

---

## Step 3: Start Frontend (on Your Mac)

Open **another terminal** on your Mac:

```bash
cd /Users/praneethposina/Documents/LLM_Inference/web
npm install   # Only needed first time
NEXT_PUBLIC_GATEWAY_URL=http://localhost:8080 npm run dev
```

**Important:** The `NEXT_PUBLIC_GATEWAY_URL` tells the Playground to send API requests to `localhost:8080` (your SSH tunnel), not `localhost:8000` (which doesn't exist locally).

### Open the Playground

Visit: **http://localhost:3000**

Type a message → it goes through:
```
Browser (3000) → Next.js → localhost:8080 → SSH tunnel → Gateway (8000) → vLLM → GPU → response streams back
```

---

## Step 4: Interact with the Backend

### Option A: Use the Playground UI

Visit http://localhost:3000 and chat!

### Option B: Use curl

```bash
# Health check
curl http://localhost:8080/health

# List models
curl http://localhost:8080/v1/models

# Chat completion (non-streaming)
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -d '{
    "model": "mistral",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50,
    "stream": false
  }'

# Chat completion (streaming)
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -d '{
    "model": "mistral",
    "messages": [{"role": "user", "content": "Explain SSH tunnels in 3 sentences"}],
    "max_tokens": 100,
    "stream": true
  }'
```

### Option C: Use Python

```python
import httpx

response = httpx.post(
    "http://localhost:8080/v1/chat/completions",
    headers={"Authorization": "Bearer sk-dev-default-key-12345"},
    json={
        "model": "mistral",
        "messages": [{"role": "user", "content": "Hello!"}],
        "max_tokens": 50
    }
)
print(response.json()["choices"][0]["message"]["content"])
```

### Option D: Use OpenAI Python SDK

```bash
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="sk-dev-default-key-12345"
)

response = client.chat.completions.create(
    model="mistral",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=50
)
print(response.choices[0].message.content)
```

---

## Step 5: Run Benchmarks

### On Lightning.ai (Direct, Faster)

```bash
cd ~/LLM_Inference/bench
pip install httpx
mkdir -p results

# Sequential baseline
python benchmark.py --concurrency 1 --suite short --output results/c1.csv

# Concurrent (batching test)
python benchmark.py --concurrency 10 --suite short --output results/c10.csv
```

### From Your Mac (Through Tunnel, Adds ~20ms Latency)

```bash
cd /Users/praneethposina/Documents/LLM_Inference/bench
pip install httpx

python benchmark.py --url http://localhost:8080 --suite short
```

> **Note:** Run benchmarks from Lightning.ai for accurate numbers. The SSH tunnel adds network latency that skews results.

---

## Troubleshooting

### "Connection refused" on SSH tunnel

**Cause:** Gateway isn't running on Lightning.ai yet.

```bash
# On Lightning.ai:
cd ~/LLM_Inference/ops/compose
docker compose ps        # Check what's running
docker compose up -d     # Start everything
docker compose logs -f   # Watch logs
```

### "Failed to fetch" in Playground

**Cause:** SSH tunnel is down or GATEWAY_URL is wrong.

```bash
# Check tunnel is alive:
curl http://localhost:8080/health

# If dead, restart:
ssh -L 8080:localhost:8000 s_01ke5v1ghk5yz3c74668bdx3b6@ssh.lightning.ai

# Restart frontend with correct URL:
NEXT_PUBLIC_GATEWAY_URL=http://localhost:8080 npm run dev
```

### vLLM takes forever to start

First time downloading the model (~14GB). Check progress:

```bash
docker compose logs -f vllm
```

Subsequent starts are faster (model is cached in Docker volume).

### CORS errors in browser

The Gateway allows `localhost:3000` and `localhost:3001`. If your frontend runs on a different port, update the CORS config in `gateway/main.py`.

---

## Quick Reference

### Terminals You Need (3 total)

| Terminal | What | Command |
|----------|------|---------|
| 1 | SSH tunnel | `ssh -L 8080:localhost:8000 s_01...@ssh.lightning.ai` |
| 2 | Frontend | `cd web && NEXT_PUBLIC_GATEWAY_URL=http://localhost:8080 npm run dev` |
| 3 | General use | curl, benchmarks, etc. |

### URLs

| What | URL |
|------|-----|
| Playground | http://localhost:3000 |
| Gateway API | http://localhost:8080 |
| Prometheus | http://localhost:9292 (needs tunnel) |
| Grafana | http://localhost:3030 (needs tunnel) |

### API Key

Default dev key: `sk-dev-default-key-12345`

Configured in `gateway/api_keys.json`.
