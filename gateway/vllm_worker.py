"""
vLLM Worker - Proxies requests to vLLM's OpenAI-compatible API.

This worker matches the same interface as EchoWorker but calls a real LLM.
Key learning: vLLM exposes an OpenAI-compatible API, so we can use httpx
to make HTTP requests just like calling OpenAI's API.
"""
import os
import json
import httpx
from typing import AsyncGenerator


class VLLMWorker:
    """
    Worker that proxies requests to vLLM's OpenAI-compatible API.
    
    vLLM exposes these endpoints:
        GET  /health           - Health check
        GET  /v1/models        - List models
        POST /v1/completions   - Text completions
        POST /v1/chat/completions - Chat completions (what we use)
    """
    
    def __init__(self, base_url: str = None, timeout: float = 120.0):
        """
        Initialize the vLLM worker.
        
        Args:
            base_url: vLLM server URL (default: from VLLM_URL env var)
            timeout: Request timeout in seconds (model inference can be slow)
        """
        self.base_url = base_url or os.getenv("VLLM_URL", "http://localhost:8001")
        self.timeout = timeout
        self.model = None  # Will be discovered from vLLM
        
        # Use a persistent client for connection pooling
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0)
        )
    
    async def _get_model_name(self) -> str:
        """Discover the model name from vLLM (cached after first call)."""
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
        
        # Fallback
        return "unknown"
    
    async def generate(self, prompt: str, max_tokens: int = 100) -> str:
        """
        Generate a non-streaming response.
        
        This calls vLLM's /v1/chat/completions endpoint with stream=false.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text
        """
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
            
            # Extract the response content
            return data["choices"][0]["message"]["content"]
            
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"vLLM request failed: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise RuntimeError(f"vLLM connection failed: {e}")
    
    async def generate_stream(self, prompt: str, max_tokens: int = 100) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response token by token.
        
        This calls vLLM's /v1/chat/completions with stream=true, 
        which returns Server-Sent Events (SSE).
        
        Key learning: SSE format is:
            data: {"choices": [{"delta": {"content": "Hello"}}]}
            data: {"choices": [{"delta": {"content": " world"}}]}
            data: [DONE]
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Yields:
            Token strings as they arrive from vLLM
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
                
                # Parse SSE events
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    # SSE lines start with "data: "
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            # Extract content from delta
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"vLLM streaming failed: {e.response.status_code}")
        except httpx.RequestError as e:
            raise RuntimeError(f"vLLM connection failed: {e}")
    
    async def health_check(self) -> bool:
        """Check if vLLM is healthy and ready."""
        try:
            response = await self._client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
