"""
Request/response logging and metrics.
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Setup logging directory
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Request log file
REQUEST_LOG = LOG_DIR / "requests.jsonl"


def setup_logger(name: str = "gateway") -> logging.Logger:
    """Setup application logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(LOG_DIR / "gateway.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def log_request(
    logger: logging.Logger,
    request_id: str,
    request_data: Dict[str, Any],
    key_id: str
):
    """Log an incoming request."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "type": "request",
        "key_id": key_id,
        "model": request_data.get("model"),
        "stream": request_data.get("stream", False),
        "max_tokens": request_data.get("max_tokens"),
        "message_count": len(request_data.get("messages", []))
    }
    
    # Write to JSONL file
    with open(REQUEST_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    logger.info(f"Request {request_id} from {key_id}: model={log_entry['model']}, stream={log_entry['stream']}")


def log_response(
    logger: logging.Logger,
    request_id: str,
    latency_ms: int,
    status: str = "success"
):
    """Log a response."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "type": "response",
        "status": status,
        "latency_ms": latency_ms
    }
    
    # Write to JSONL file
    with open(REQUEST_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    logger.info(f"Response {request_id}: status={status}, latency={latency_ms}ms")


def get_usage_stats() -> Dict[str, Any]:
    """Aggregate usage statistics from log file."""
    if not REQUEST_LOG.exists():
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "avg_latency_ms": 0
        }
    
    total_requests = 0
    total_tokens = 0
    latencies = []
    
    # Read all log entries
    with open(REQUEST_LOG, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("type") == "request":
                    total_requests += 1
                    # Estimate tokens (rough estimate: ~4 chars per token)
                    # In a real implementation, we'd track actual token counts
                    # For now, we'll use a placeholder
                elif entry.get("type") == "response" and entry.get("status") == "success":
                    latency = entry.get("latency_ms", 0)
                    if latency > 0:
                        latencies.append(latency)
            except json.JSONDecodeError:
                continue
    
    # Calculate average latency
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    # For token count, we'll estimate based on requests
    # In a real implementation, we'd track this from the usage field in responses
    total_tokens = total_requests * 50  # Rough estimate
    
    return {
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "avg_latency_ms": int(avg_latency)
    }

