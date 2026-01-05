"""
Worker Factory - Creates the appropriate worker based on configuration.

This implements the Factory Pattern:
  - Environment variable WORKER_TYPE determines which worker to create
  - All workers implement the same interface (generate, generate_stream)
  - Easy to add new workers (TensorRT-LLM, etc.) in the future
"""
import os
from typing import Union

from worker import EchoWorker
from vllm_worker import VLLMWorker


# Type alias for any worker
Worker = Union[EchoWorker, VLLMWorker]


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


# Available worker types for documentation
WORKER_TYPES = {
    "echo": "CPU-based echo worker for testing (no GPU required)",
    "vllm": "vLLM backend for real LLM inference (requires GPU)"
}
