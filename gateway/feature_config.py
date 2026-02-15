"""
Feature Configuration - Parse and validate feature toggle headers.

Headers supported:
- X-Backend: vllm | vllm-quant | tgi | trt (selects which engine to use)
- X-Quant: none | awq | int8 | fp8 (quantization mode - backend dependent)

Usage:
    from feature_config import FeatureConfig

    config = FeatureConfig.from_headers(request.headers)
    worker = get_worker_for_backend(config.backend)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FeatureConfig:
    """Feature toggle configuration parsed from request headers."""
    
    backend: str = "vllm"  # Which engine to route to
    quant: str = "none"    # Quantization mode (info only, backend determines actual quant)
    
    # Backend URL mapping (container hostnames)
    BACKEND_URLS = {
        "vllm": "http://vllm:8000",
        "vllm-quant": "http://vllm-quant:8000",
        "tgi": "http://tgi:8000",
        "tgi-tp": "http://tgi-tp:8000",
        "trt": "http://trt:8000",
    }
    
    VALID_BACKENDS = {"vllm", "vllm-quant", "tgi", "tgi-tp", "trt"}
    VALID_QUANTS = {"none", "awq", "int8", "fp8"}
    
    @classmethod
    def from_headers(cls, headers: dict) -> "FeatureConfig":
        """Parse feature config from request headers."""
        backend = headers.get("x-backend", "vllm").lower()
        quant = headers.get("x-quant", "none").lower()
        
        # Validate backend
        if backend not in cls.VALID_BACKENDS:
            backend = "vllm"  # Fallback to default
        
        # Validate quant
        if quant not in cls.VALID_QUANTS:
            quant = "none"
        
        return cls(backend=backend, quant=quant)
    
    @property
    def backend_url(self) -> str:
        """Get the URL for the selected backend."""
        return self.BACKEND_URLS.get(self.backend, self.BACKEND_URLS["vllm"])
    
    def to_dict(self) -> dict:
        """Return config as dict (for logging/metrics)."""
        return {
            "backend": self.backend,
            "quant": self.quant,
            "backend_url": self.backend_url,
        }
