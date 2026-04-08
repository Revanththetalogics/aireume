"""
Prometheus metrics for ARIA observability.

This module defines custom metrics used across the application.
Import metrics from here to avoid circular imports.
"""

from prometheus_client import Histogram, Counter

# Custom metrics for LLM operations
LLM_CALL_DURATION = Histogram(
    "aria_llm_call_duration_seconds",
    "Duration of LLM calls in seconds",
    buckets=[5, 10, 20, 30, 60, 120, 180, 300]
)

LLM_FALLBACK_TOTAL = Counter(
    "aria_llm_fallback_total",
    "Total number of LLM fallbacks triggered"
)

# Custom metrics for resume parsing
RESUME_PARSE_DURATION = Histogram(
    "aria_resume_parse_duration_seconds",
    "Duration of resume parsing in seconds",
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

# Custom metrics for batch operations
BATCH_SIZE = Histogram(
    "aria_batch_size",
    "Number of resumes in batch requests",
    buckets=[1, 5, 10, 20, 30, 50]
)
