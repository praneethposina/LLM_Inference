"""
Gateway service - OpenAI-compatible API with authentication and rate limiting.
"""
import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from worker_factory import create_worker
from auth import verify_api_key, list_api_keys, create_api_key, revoke_api_key, revoke_api_key_by_id
from logger import setup_logger, log_request, log_response, get_usage_stats
from metrics import get_metrics, RequestMetrics

# Initialize FastAPI app
app = FastAPI(
    title="LLM Inference Gateway",
    description="OpenAI-compatible API for LLM inference",
    version="0.1.0"
)

# CORS middleware - allow localhost for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiting (simplified for M1 - will be enhanced in later milestones)
# Note: slowapi requires additional setup for async endpoints, so we'll implement
# a simple rate limiter in a later milestone. For now, basic auth is sufficient.

# Logger
logger = setup_logger()

# Initialize worker based on WORKER_TYPE environment variable
# - WORKER_TYPE=echo (default): CPU-based simulation, no GPU
# - WORKER_TYPE=vllm: Real LLM via vLLM backend
worker = create_worker()

# Request/Response models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "echo-model"
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = 100
    stream: bool = False

class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[dict]

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict]
    usage: dict

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics()

@app.get("/v1/models")
async def list_models():
    """List available models."""
    return {
        "object": "list",
        "data": [
            {
                "id": "echo-model",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "llm-inference"
            }
        ]
    }

@app.get("/v1/keys")
async def get_keys():
    """List all API keys."""
    keys = list_api_keys()
    return {
        "object": "list",
        "data": keys
    }

class CreateKeyRequest(BaseModel):
    key_id: str
    rate_limit: int = 30

@app.post("/v1/keys")
async def create_key(body: CreateKeyRequest):
    """Create a new API key."""
    api_key = create_api_key(body.key_id, body.rate_limit)
    return {
        "api_key": api_key,
        "key_id": body.key_id,
        "rate_limit": body.rate_limit
    }

@app.delete("/v1/keys/{key_id}")
async def delete_key(key_id: str, authorization: Optional[str] = Header(None)):
    """Revoke an API key by key_id."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    
    # Verify the authorization key is valid
    api_key = authorization.replace("Bearer ", "")
    key_info = verify_api_key(api_key)
    if not key_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Revoke the key by key_id
    success = revoke_api_key_by_id(key_id)
    if success:
        return {"status": "revoked", "key_id": key_id}
    else:
        raise HTTPException(status_code=404, detail="Key not found")

@app.get("/v1/usage")
async def get_usage():
    """Get usage statistics."""
    stats = get_usage_stats()
    return stats

@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    OpenAI-compatible chat completions endpoint with SSE streaming support.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Verify API key
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    
    api_key = authorization.replace("Bearer ", "")
    key_info = verify_api_key(api_key)
    if not key_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Log request
    log_request(logger, request_id, body.model_dump(), key_info["key_id"])
    
    # Generate response
    if body.stream:
        return StreamingResponse(
            _stream_chat_completion(request_id, body, start_time),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    else:
        # Non-streaming with metrics
        req_metrics = RequestMetrics(model=body.model, stream=False)
        req_metrics.start()
        try:
            response = await _generate_chat_completion(request_id, body, start_time, req_metrics)
            latency_ms = int((time.time() - start_time) * 1000)
            log_response(logger, request_id, latency_ms, "success")
            req_metrics.finish("success")
            return response
        except Exception as e:
            req_metrics.finish("error")
            raise

async def _generate_chat_completion(
    request_id: str,
    body: ChatCompletionRequest,
    start_time: float,
    req_metrics: RequestMetrics = None
) -> ChatCompletionResponse:
    """Generate a non-streaming chat completion."""
    # Get the last user message
    user_messages = [msg for msg in body.messages if msg.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user messages found")
    
    prompt = user_messages[-1].content
    
    # Record prompt tokens
    prompt_tokens = len(prompt.split())
    if req_metrics:
        req_metrics.record_prompt_tokens(prompt_tokens)
    
    # Generate response using worker
    full_response = await worker.generate(prompt, max_tokens=body.max_tokens or 100)
    # Count completion tokens
    completion_tokens = len(full_response.split())
    if req_metrics:
        req_metrics.record_token(completion_tokens)
    
    # Format response
    return ChatCompletionResponse(
        id=request_id,
        created=int(start_time),
        model=body.model,
        choices=[{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": full_response
            },
            "finish_reason": "stop"
        }],
        usage={
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(full_response.split()),
            "total_tokens": len(prompt.split()) + len(full_response.split())
        }
    )

async def _stream_chat_completion(
    request_id: str,
    body: ChatCompletionRequest,
    start_time: float
) -> AsyncGenerator[str, None]:
    """Generate a streaming chat completion (SSE format)."""
    # Initialize metrics for streaming
    req_metrics = RequestMetrics(model=body.model, stream=True)
    req_metrics.start()
    first_token = True
    token_count = 0
    
    # Get the last user message
    user_messages = [msg for msg in body.messages if msg.role == "user"]
    if not user_messages:
        yield f"data: {json.dumps({'error': 'No user messages found'})}\n\n"
        req_metrics.finish("error")
        return
    
    prompt = user_messages[-1].content
    req_metrics.record_prompt_tokens(len(prompt.split()))
    
    try:
        # Stream response using worker
        async for chunk in worker.generate_stream(prompt, max_tokens=body.max_tokens or 100):
            # Record TTFB on first token
            if first_token:
                req_metrics.record_first_token()
                first_token = False
            
            token_count += 1
            chunk_data = ChatCompletionChunk(
                id=request_id,
                created=int(start_time),
                model=body.model,
                choices=[{
                    "index": 0,
                    "delta": {"role": "assistant", "content": chunk},
                    "finish_reason": None
                }]
            )
            yield f"data: {chunk_data.model_dump_json()}\n\n"
            await asyncio.sleep(0.01)  # Small delay to simulate token generation
        
        # Send final chunk
        final_chunk = ChatCompletionChunk(
            id=request_id,
            created=int(start_time),
            model=body.model,
            choices=[{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        )
        yield f"data: {final_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
        
        # Log and record metrics
        latency_ms = int((time.time() - start_time) * 1000)
        log_response(logger, request_id, latency_ms, "success")
        req_metrics.record_token(token_count)
        req_metrics.finish("success")
        
    except Exception as e:
        req_metrics.finish("error")
        # Optionally re-raise or log the exception
        # yield f"data: {json.dumps({'error': str(e)})}\n\n" # If you want to send error to client
        raise # Re-raise to ensure it's logged by the server if not handled elsewhere
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
