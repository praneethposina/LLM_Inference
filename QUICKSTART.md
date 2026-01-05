# Quick Start Guide - M1

This guide will help you get the M1 service shell up and running.

## Prerequisites

- **Node.js 18+** (for the web frontend)
- **Python 3.10+** (for the gateway service)
- **curl** (for testing, optional)

## Setup

### 1. Install Gateway Dependencies

```bash
cd gateway
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Web Dependencies

```bash
cd ../web
npm install
```

## Running the Service

### Terminal 1: Start the Gateway

```bash
cd gateway
source venv/bin/activate  # If not already activated
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Terminal 2: Start the Web Frontend

```bash
cd web
npm run dev
```

You should see:
```
  ▲ Next.js 14.0.4
  - Local:        http://localhost:3000
```

## Access the Service

1. **Playground**: Open http://localhost:3000 in your browser
2. **Console**: Open http://localhost:3000/console
3. **Gateway API**: http://localhost:8000

## Testing with curl

### Test Health Endpoint

```bash
curl http://localhost:8000/health
```

### Test Chat Completion (Non-streaming)

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -d '{
    "model": "echo-model",
    "messages": [{"role": "user", "content": "Hello, world!"}],
    "max_tokens": 50,
    "stream": false
  }'
```

### Test Chat Completion (Streaming)

```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -d '{
    "model": "echo-model",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "max_tokens": 100,
    "stream": true
  }'
```

### Use the Test Script

```bash
./test_api.sh
```

## Default API Key

For development, a default API key is automatically created:
- **Key**: `sk-dev-default-key-12345`
- **Rate Limit**: 30 requests/minute

## Viewing Logs

Gateway logs are written to:
- **Console**: Standard output
- **File**: `gateway/logs/gateway.log`
- **Request Log**: `gateway/logs/requests.jsonl` (JSONL format)

To view recent requests:
```bash
tail -f gateway/logs/requests.jsonl | jq .
```

## Troubleshooting

### Port Already in Use

If port 8000 or 3000 is already in use:
- Gateway: Change port in `uvicorn main:app --port 8001`
- Web: Change port in `package.json` scripts or use `PORT=3001 npm run dev`

### CORS Errors

If you see CORS errors, ensure:
- Gateway is running on port 8000
- Web frontend is running on port 3000
- CORS origins are configured in `gateway/main.py`

### Module Not Found Errors

Ensure you're in the correct directory and have activated the virtual environment:
```bash
cd gateway
source venv/bin/activate
python -c "import fastapi; print('OK')"
```

## Next Steps

Once M1 is working, proceed to **M2: First Engine Path** to connect a real LLM backend (vLLM or TGI).

