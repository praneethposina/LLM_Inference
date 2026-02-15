"""
Worker Factory - Creates the appropriate worker based on configuration.

This implements the Factory Pattern:
  - Environment variable WORKER_TYPE determines which worker to create
  - All workers implement the same interface (generate, generate_stream)
  - Easy to add new workers (TensorRT-LLM, etc.) in the future
  
M3 Addition:
  - create_worker_for_backend() creates worker based on X-Backend header
"""
import os
from typing import Union, Optional

from worker import EchoWorker
from vllm_worker import VLLMWorker
from tgi_worker import TGIWorker
from trtllm_worker import TRTLLMWorker


# Type alias for any worker
Worker = Union[EchoWorker, VLLMWorker, TGIWorker, TRTLLMWorker]

# Worker cache (avoid recreating workers for same backend)
_worker_cache: dict[str, Worker] = {}


def create_worker() -> Worker:
    """
    Factory function to create a worker based on WORKER_TYPE env var.
    
    Environment Variables:
        WORKER_TYPE: 'echo' or 'vllm' (default: 'echo')
        VLLM_URL: URL for vLLM server (default: 'http://localhost:8001')
    
    Returns:
        Worker instance (EchoWorker or VLLMWorker)
    """
    worker_type = os.getenv("WORKER_TYPE", "echo").lower()
    
    if worker_type == "vllm":
        vllm_url = os.getenv("VLLM_URL", "http://localhost:8001")
        print(f"[Gateway] Using VLLMWorker at {vllm_url}")
        return VLLMWorker(base_url=vllm_url)
    
    elif worker_type == "echo":
        print("[Gateway] Using EchoWorker (CPU-based simulation)")
        return EchoWorker()
    
    else:
        print(f"[Gateway] Unknown WORKER_TYPE '{worker_type}', falling back to EchoWorker")
        return EchoWorker()


def create_worker_for_backend(backend: str, backend_url: str) -> Worker:
    """
    Create a worker for a specific backend.
    
    Used for dynamic backend selection via X-Backend header.
    Workers are cached to avoid re-creation overhead.
    
    Args:
        backend: Backend type (vllm, vllm-quant, tgi, tgi-tp, trt)
        backend_url: Full URL of the backend (e.g., http://tgi:8000)
    
    Returns:
        Worker instance connected to the specified backend
    """
    global _worker_cache
    
    if backend_url in _worker_cache:
        return _worker_cache[backend_url]
    
    # Create appropriate worker type
    if backend.startswith("tgi"):
        worker = TGIWorker(base_url=backend_url)
    elif backend.startswith("trt"):
        worker = TRTLLMWorker(base_url=backend_url)
    else:
        worker = VLLMWorker(base_url=backend_url)
    
    _worker_cache[backend_url] = worker
    print(f"[Gateway] Created {type(worker).__name__} for backend: {backend} at {backend_url}")
    
    return worker


# Available worker types for documentation
WORKER_TYPES = {
    "echo": "CPU-based echo worker for testing (no GPU required)",
    "vllm": "vLLM backend for real LLM inference (requires GPU)",
    "vllm-quant": "vLLM with AWQ quantization (lower memory)",
    "tgi": "HuggingFace TGI backend",
    "trt": "TensorRT-LLM backend (NVIDIA optimized)",
}

