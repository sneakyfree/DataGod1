"""
Prometheus Metrics Middleware (Phase 6.4)

Exposes application metrics for Prometheus scraping.
"""

import logging
import time
from typing import Callable

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# =============================================================================
# METRICS DEFINITIONS
# =============================================================================

# HTTP request metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)

REQUEST_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
)

# Agent metrics
AGENT_TASKS = Counter(
    "agent_tasks_total", "Total agent tasks processed", ["agent_id", "status"]
)

AGENT_TASK_FAILURES = Counter(
    "agent_task_failures_total", "Total agent task failures", ["agent_id", "error_type"]
)

AGENT_OUTPUT_CONFIDENCE = Histogram(
    "agent_output_confidence",
    "Agent output confidence scores",
    ["agent_id"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

AGENT_EXECUTION_TIME = Histogram(
    "agent_execution_time_seconds",
    "Agent task execution time in seconds",
    ["agent_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# Rate limiting metrics
RATE_LIMIT_EXCEEDED = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit violations",
    ["endpoint", "limit_type"],
)

# Cache metrics
CACHE_OPERATIONS = Counter(
    "cache_operations_total",
    "Cache operations",
    ["operation", "result"],  # operation: get/set, result: hit/miss
)

# Scraper metrics
SCRAPER_REQUESTS = Counter(
    "scraper_requests_total", "Scraper requests", ["scraper_type", "status"]
)

SCRAPER_LATENCY = Histogram(
    "scraper_latency_seconds",
    "Scraper request latency",
    ["scraper_type"],
    buckets=[1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)


# =============================================================================
# MIDDLEWARE
# =============================================================================


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics.

    Tracks:
    - Request count by method, endpoint, status
    - Request latency histogram
    - In-progress requests gauge
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = self._normalize_endpoint(request.url.path)

        # Track in-progress
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()

        start_time = time.time()
        status_code = 500  # Default in case of unhandled exception

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            # Record metrics
            duration = time.time() - start_time

            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint, status=status_code
            ).inc()

            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for consistent metric labels."""
        # Replace dynamic path segments with placeholders
        parts = path.split("/")
        normalized = []

        for part in parts:
            if not part:
                continue
            # Replace UUIDs and numbers with placeholders
            if len(part) == 36 and "-" in part:  # UUID
                normalized.append("{id}")
            elif part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)

        return "/" + "/".join(normalized) if normalized else "/"


# =============================================================================
# METRICS ENDPOINT
# =============================================================================


async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus metrics endpoint.

    Returns all collected metrics in Prometheus format.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def record_agent_task(
    agent_id: str, status: str, confidence: float, execution_time: float
):
    """Record metrics for an agent task."""
    AGENT_TASKS.labels(agent_id=agent_id, status=status).inc()
    AGENT_OUTPUT_CONFIDENCE.labels(agent_id=agent_id).observe(confidence)
    AGENT_EXECUTION_TIME.labels(agent_id=agent_id).observe(execution_time)


def record_agent_failure(agent_id: str, error_type: str):
    """Record an agent task failure."""
    AGENT_TASK_FAILURES.labels(agent_id=agent_id, error_type=error_type).inc()


def record_rate_limit(endpoint: str, limit_type: str):
    """Record a rate limit violation."""
    RATE_LIMIT_EXCEEDED.labels(endpoint=endpoint, limit_type=limit_type).inc()


def record_cache_operation(operation: str, hit: bool):
    """Record a cache operation."""
    CACHE_OPERATIONS.labels(operation=operation, result="hit" if hit else "miss").inc()


def record_scraper_request(scraper_type: str, success: bool, latency: float):
    """Record a scraper request."""
    SCRAPER_REQUESTS.labels(
        scraper_type=scraper_type, status="success" if success else "error"
    ).inc()
    SCRAPER_LATENCY.labels(scraper_type=scraper_type).observe(latency)
