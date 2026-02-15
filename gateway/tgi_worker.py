"""
TGI Worker - Proxies requests to HuggingFace Text Generation Inference.

TGI also exposes an OpenAI-compatible API at /v1/chat/completions,
so this is largely the same as VLLMWorker. The key differences:
  - TGI uses different internal batching (dynamic batching vs vLLM's continuous batching)
  - TGI has built-in tensor parallel support
  - TGI health endpoint is at / (returns 200) instead of /health

We keep a separate class for clarity and future TGI-specific features.
"""
import os
import json
import httpx
from typing import AsyncGenerator


class TGIWorker:
    """
    Worker that proxies requests to HuggingFace TGI's OpenAI-compatible API.
    
    TGI exposes these endpoints:
        GET  /health                 - Health check
        GET  /v1/models              - List models
        POST /v1/chat/completions    - Chat completions (OpenAI-compatible)
        POST /generate               - TGI native generate (not used here)
        POST /generate_stream         - TGI native streaming (not used here)
    """
    
    def __init__(self, base_url: str = None, timeout: float = 120.0):
        """
        Initialize the TGI worker.
        
        Args:
            base_url: TGI server URL (default: from TGI_URL env var)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("TGI_URL", "http://tgi:8000")
        self.timeout = timeout
        self.model = None
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0)
        )
    
    async def _get_model_name(self) -> str:
        """Discover the model name from TGI."""
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
        """Generate a non-streaming response via TGI."""
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
            raise RuntimeError(f"TGI request failed: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise RuntimeError(f"TGI connection failed: {e}")
    
    async def generate_stream(self, prompt: str, max_tokens: int = 100) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from TGI.
        
        TGI's OpenAI-compatible endpoint uses the same SSE format as vLLM:
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
            raise RuntimeError(f"TGI streaming failed: {e.response.status_code}")
        except httpx.RequestError as e:
            raise RuntimeError(f"TGI connection failed: {e}")
    
    async def health_check(self) -> bool:
        """Check if TGI is healthy."""
        try:
            response = await self._client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
