"""
Prometheus Metrics for LLM Inference Gateway

This module defines the key metrics for monitoring LLM inference:
  - Request latency (histogram): How long requests take end-to-end
  - Time to First Byte (histogram): How long until first token streams
  - Tokens per second (gauge): Current throughput
  - Request count (counter): Total requests by status
  - Active requests (gauge): Currently in-flight requests

Key Learning: Why these metrics matter
  - TTFB: Measures prefill time (processing the prompt)
  - Latency: Measures total request time (prefill + decode)
  - Tokens/s: Measures throughput efficiency
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# =============================================================================
# Metric Definitions
# =============================================================================

# Request latency - how long the entire request takes
REQUEST_LATENCY = Histogram(
    'llm_request_latency_seconds',
    'Time spent processing request (prefill + decode)',
    ['model', 'status'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)

# Time to first byte - how long until first token streams
TTFB = Histogram(
    'llm_ttfb_seconds',
    'Time to first byte (prefill latency)',
    ['model'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Request counter by status
REQUEST_COUNT = Counter(
    'llm_requests_total',
    'Total number of requests',
    ['model', 'status', 'stream']
)

# Active requests gauge
ACTIVE_REQUESTS = Gauge(
    'llm_active_requests',
    'Number of currently active requests',
    ['model']
)

# Tokens generated counter
TOKENS_GENERATED = Counter(
    'llm_tokens_generated_total',
    'Total tokens generated',
    ['model']
)

# Token generation rate (for calculating tokens/s)
TOKENS_PER_REQUEST = Histogram(
    'llm_tokens_per_request',
    'Number of tokens generated per request',
    ['model'],
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2000]
)

# Prompt tokens histogram
PROMPT_TOKENS = Histogram(
    'llm_prompt_tokens',
    'Number of tokens in the prompt',
    ['model'],
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2000, 4000]
)


def get_metrics() -> Response:
    """Generate Prometheus metrics response."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# =============================================================================
# Metric Recording Helpers
# =============================================================================

class RequestMetrics:
    """Context manager for recording request metrics."""
    
    def __init__(self, model: str, stream: bool = False):
        self.model = model
        self.stream = stream
        self.start_time = None
        self.first_token_time = None
        self.tokens = 0
        self.status = "success"
    
    def start(self):
        """Call at request start."""
        import time
        self.start_time = time.time()
        ACTIVE_REQUESTS.labels(model=self.model).inc()
    
    def record_first_token(self):
        """Call when first token is generated (for streaming)."""
        import time
        if self.first_token_time is None:
            self.first_token_time = time.time()
            ttfb = self.first_token_time - self.start_time
            TTFB.labels(model=self.model).observe(ttfb)
    
    def record_token(self, count: int = 1):
        """Call for each token generated."""
        self.tokens += count
    
    def finish(self, status: str = "success"):
        """Call at request end."""
        import time
        self.status = status
        end_time = time.time()
        latency = end_time - self.start_time
        
        # Record metrics
        REQUEST_LATENCY.labels(model=self.model, status=status).observe(latency)
        REQUEST_COUNT.labels(
            model=self.model, 
            status=status, 
            stream=str(self.stream)
        ).inc()
        ACTIVE_REQUESTS.labels(model=self.model).dec()
        
        if self.tokens > 0:
            TOKENS_GENERATED.labels(model=self.model).inc(self.tokens)
            TOKENS_PER_REQUEST.labels(model=self.model).observe(self.tokens)
    
    def record_prompt_tokens(self, count: int):
        """Record prompt token count."""
        PROMPT_TOKENS.labels(model=self.model).observe(count)
