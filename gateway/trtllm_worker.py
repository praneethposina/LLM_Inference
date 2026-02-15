"""
TensorRT-LLM Worker - Proxies requests to NVIDIA's TensorRT-LLM backend.

TensorRT-LLM is typically served via NVIDIA's Triton Inference Server with
the TRT-LLM backend. The tensorrt_llm Docker image exposes an
OpenAI-compatible API at /v1/chat/completions.

Key differences from vLLM/TGI:
  - Requires pre-built TRT-LLM engines (model compilation step)
  - Supports FP8 quantization natively on Hopper+ GPUs
  - CUDA Graphs reduce kernel launch overhead → better TTFB
  - Inflight batching (similar to vLLM's continuous batching)
"""
import os
import json
import httpx
from typing import AsyncGenerator


class TRTLLMWorker:
    """
    Worker that proxies requests to TensorRT-LLM's OpenAI-compatible API.
    
    TRT-LLM (via Triton or the OpenAI frontend) exposes:
        GET  /health                 - Health check
        GET  /v1/models              - List models
        POST /v1/chat/completions    - Chat completions (OpenAI-compatible)
    """
    
    def __init__(self, base_url: str = None, timeout: float = 120.0):
        """
        Initialize the TRT-LLM worker.
        
        Args:
            base_url: TRT-LLM server URL (default: from TRTLLM_URL env var)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("TRTLLM_URL", "http://trt:8000")
        self.timeout = timeout
        self.model = None
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0)
        )
    
    async def _get_model_name(self) -> str:
        """Discover the model name from TRT-LLM."""
        if self.model:
            return self.model
        
        try:
            response = await self._client.get("/v1/models")
            response.raise_for_status()
            models = response.json()
            if models.get("data"):
                self.model = models["data"][0]["id"]
                return self.model
        except Exception:
            pass
        
        return "unknown"
    
    async def generate(self, prompt: str, max_tokens: int = 100) -> str:
        """Generate a non-streaming response via TRT-LLM."""
        model = await self._get_model_name()
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            response = await self._client.post(
                "/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"TRT-LLM request failed: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise RuntimeError(f"TRT-LLM connection failed: {e}")
    
    async def generate_stream(self, prompt: str, max_tokens: int = 100) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from TRT-LLM.
        
        Uses the same SSE format as vLLM/TGI:
            data: {"choices": [{"delta": {"content": "Hello"}}]}
            data: [DONE]
        """
        model = await self._get_model_name()
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": True
        }
        
        try:
            async with self._client.stream(
                "POST",
                "/v1/chat/completions",
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    if line.startswith("data: "):
                        data = line[6:]
                        
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"TRT-LLM streaming failed: {e.response.status_code}")
        except httpx.RequestError as e:
            raise RuntimeError(f"TRT-LLM connection failed: {e}")
    
    async def health_check(self) -> bool:
        """Check if TRT-LLM is healthy."""
        try:
            response = await self._client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
