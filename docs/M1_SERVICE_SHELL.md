# M1: Service Shell - Website, Playground, and OpenAI-compatible API

## Goal
Build a service shell that looks and feels like a Groq/Together-style service before touching GPUs. This establishes the API surface and UX constraints that drive server design.

## What Was Built

### 1. Web Frontend (Next.js/React)
- **Playground**: Interactive chat interface with streaming output display
- **Console**: API key management and usage statistics page
- Modern, dark-themed UI with real-time streaming support

### 2. Gateway Service (FastAPI)
- **OpenAI-compatible API**: `/v1/chat/completions` endpoint
- **SSE Streaming**: Server-Sent Events for real-time token streaming
- **Authentication**: API key verification via Bearer tokens
- **Rate Limiting**: Simple per-IP rate limiting (30 requests/minute)
- **Request/Response Logging**: JSONL logs with latency tracking

### 3. Echo Worker (CPU-based)
- Simulates LLM inference by echoing input with variation
- Supports both streaming and non-streaming modes
- Configurable token delays to simulate realistic behavior

## Architecture

```
┌─────────────┐
│   Browser   │
│  (Next.js)  │
└──────┬──────┘
       │ HTTP/SSE
       ▼
┌─────────────┐
│   Gateway   │
│  (FastAPI)  │
│  - Auth     │
│  - Rate Lim │
│  - Logging  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Echo Worker │
│   (CPU)     │
└─────────────┘
```

## API Endpoints

### `GET /health`
Health check endpoint.

### `GET /v1/models`
List available models.

### `POST /v1/chat/completions`
OpenAI-compatible chat completions endpoint.

**Request:**
```json
{
  "model": "echo-model",
  "messages": [{"role": "user", "content": "Hello!"}],
  "max_tokens": 100,
  "stream": true
}
```

**Response (streaming):**
```
data: {"id": "...", "choices": [{"delta": {"content": "Echo:"}}]}
data: {"id": "...", "choices": [{"delta": {"content": "Hello "}}]}
...
data: [DONE]
```

## Testing

### Using curl

**Non-streaming:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -d '{
    "model": "echo-model",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

**Streaming:**
```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-dev-default-key-12345" \
  -d '{
    "model": "echo-model",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

### Using the test script
```bash
chmod +x test_api.sh
./test_api.sh
```

## Exit Criteria Status

- ✅ **Playground streams from CPU echo worker**: Implemented with SSE streaming
- ✅ **curl works**: Tested with OpenAI-compatible API format
- ✅ **Requests/latencies logged**: JSONL logging with request/response tracking

## Why This Exists

This milestone establishes the **user-facing interface** and **API contract** that all subsequent work will build upon. By starting with a working service shell, we:

1. **Understand the UX constraints**: What users expect (streaming, low latency, etc.)
2. **Define the API surface**: OpenAI-compatible format that works with existing tooling
3. **Establish observability**: Logging and metrics infrastructure for measuring improvements

## What Can Go Wrong

### Trade-offs
- **Simple rate limiting**: Current implementation is per-IP, not per-API-key. For production, rate limits should be key-based.
- **File-based key storage**: API keys stored in JSON file. Production needs a proper database.
- **No persistent metrics**: Usage stats are computed on-demand. Production needs time-series storage.

### Failure Modes
- **CORS issues**: If frontend and gateway are on different origins, CORS must be configured
- **Rate limit false positives**: Shared IP addresses (e.g., behind NAT) can trigger rate limits incorrectly
- **Log file growth**: JSONL logs will grow unbounded without rotation

## Next Steps (M2)

The next milestone will replace the echo worker with a real LLM backend (vLLM or TGI) to establish baseline performance metrics.

## Files Created

- `/web`: Next.js frontend application
- `/gateway`: FastAPI gateway service
  - `main.py`: API endpoints and routing
  - `worker.py`: Echo worker implementation
  - `auth.py`: API key management
  - `logger.py`: Request/response logging
- `/docs/M1_SERVICE_SHELL.md`: This document

