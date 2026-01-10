"""
Application Performance Monitoring Middleware

Provides structured logging, request tracking, and metrics collection
for the DataGod API.
"""

import time
import uuid
import logging
import json
from typing import Callable, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from functools import wraps
from collections import defaultdict
import threading

# Conditional imports for FastAPI (allows testing without it)
try:
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    Request = None
    Response = None
    BaseHTTPMiddleware = object

# Configure structured logging
logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and aggregates application metrics."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Request metrics
        self.request_count = defaultdict(int)
        self.request_latency = defaultdict(list)
        self.error_count = defaultdict(int)
        self.status_codes = defaultdict(int)

        # Active connections
        self.active_connections = 0
        self.max_connections = 0

        # User metrics
        self.user_requests = defaultdict(int)

        # Start time
        self.start_time = datetime.utcnow()

        # Lock for thread safety
        self._metrics_lock = threading.Lock()

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency: float,
        user_id: Optional[str] = None
    ):
        """Record a request and its metrics."""
        with self._metrics_lock:
            key = f"{method}:{endpoint}"
            self.request_count[key] += 1
            self.request_latency[key].append(latency)
            self.status_codes[status_code] += 1

            if status_code >= 400:
                self.error_count[key] += 1

            if user_id:
                self.user_requests[user_id] += 1

            # Keep only last 1000 latency samples per endpoint
            if len(self.request_latency[key]) > 1000:
                self.request_latency[key] = self.request_latency[key][-1000:]

    def increment_connections(self):
        """Increment active connection count."""
        with self._metrics_lock:
            self.active_connections += 1
            self.max_connections = max(self.max_connections, self.active_connections)

    def decrement_connections(self):
        """Decrement active connection count."""
        with self._metrics_lock:
            self.active_connections = max(0, self.active_connections - 1)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        with self._metrics_lock:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()

            # Calculate latency statistics
            latency_stats = {}
            for endpoint, latencies in self.request_latency.items():
                if latencies:
                    sorted_latencies = sorted(latencies)
                    latency_stats[endpoint] = {
                        'count': len(latencies),
                        'avg': sum(latencies) / len(latencies),
                        'min': min(latencies),
                        'max': max(latencies),
                        'p50': sorted_latencies[len(sorted_latencies) // 2],
                        'p95': sorted_latencies[int(len(sorted_latencies) * 0.95)],
                        'p99': sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) >= 100 else sorted_latencies[-1],
                    }

            # Calculate error rate
            total_requests = sum(self.request_count.values())
            total_errors = sum(self.error_count.values())
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

            return {
                'uptime_seconds': uptime,
                'total_requests': total_requests,
                'total_errors': total_errors,
                'error_rate_percent': round(error_rate, 2),
                'active_connections': self.active_connections,
                'max_connections': self.max_connections,
                'requests_by_endpoint': dict(self.request_count),
                'errors_by_endpoint': dict(self.error_count),
                'status_codes': dict(self.status_codes),
                'latency_stats': latency_stats,
                'top_users': dict(sorted(
                    self.user_requests.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]),
            }

    def reset(self):
        """Reset all metrics."""
        with self._metrics_lock:
            self.request_count.clear()
            self.request_latency.clear()
            self.error_count.clear()
            self.status_codes.clear()
            self.user_requests.clear()
            self.active_connections = 0
            self.max_connections = 0
            self.start_time = datetime.utcnow()


# Global metrics collector instance
metrics_collector = MetricsCollector()


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request monitoring and structured logging.

    Features:
    - Request ID tracking
    - Request/response logging
    - Latency measurement
    - Metrics collection
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]

        # Record start time
        start_time = time.time()

        # Increment active connections
        metrics_collector.increment_connections()

        # Extract user ID from JWT if available
        user_id = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            try:
                import jwt
                token = auth_header.split(' ')[1]
                # Decode without verification just to get user ID for logging
                payload = jwt.decode(token, options={"verify_signature": False})
                user_id = payload.get('sub')
            except:
                pass

        # Log request
        logger.info(
            json.dumps({
                'event': 'request_started',
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'query': str(request.query_params),
                'user_id': user_id,
                'client_ip': request.client.host if request.client else None,
                'user_agent': request.headers.get('User-Agent', '')[:100],
                'timestamp': datetime.utcnow().isoformat(),
            })
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate latency
            latency = time.time() - start_time

            # Record metrics
            metrics_collector.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                latency=latency,
                user_id=user_id
            )

            # Add response headers for debugging
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Response-Time'] = f"{latency:.3f}s"

            # Log response
            log_level = 'warning' if response.status_code >= 400 else 'info'
            getattr(logger, log_level)(
                json.dumps({
                    'event': 'request_completed',
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'status_code': response.status_code,
                    'latency_ms': round(latency * 1000, 2),
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat(),
                })
            )

            return response

        except Exception as e:
            # Calculate latency
            latency = time.time() - start_time

            # Record error
            metrics_collector.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                latency=latency,
                user_id=user_id
            )

            # Log error
            logger.error(
                json.dumps({
                    'event': 'request_error',
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'latency_ms': round(latency * 1000, 2),
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat(),
                })
            )

            raise

        finally:
            # Decrement active connections
            metrics_collector.decrement_connections()


class HealthChecker:
    """
    Health check utilities for the application.
    """

    def __init__(self):
        self.checks = {}

    def register_check(self, name: str, check_func: Callable[[], bool]):
        """Register a health check function."""
        self.checks[name] = check_func

    def check_database(self) -> bool:
        """Check database connectivity."""
        try:
            from db_manager import DatabaseManager
            db = DatabaseManager()
            with db.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def check_redis(self) -> bool:
        """Check Redis connectivity (if configured)."""
        try:
            import redis
            import os
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            r = redis.from_url(redis_url)
            r.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return True  # Redis is optional, return True if not configured

    def get_liveness(self) -> Dict[str, Any]:
        """
        Liveness check - is the server running?
        Used by Kubernetes liveness probes.
        """
        return {
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat(),
        }

    def get_readiness(self) -> Dict[str, Any]:
        """
        Readiness check - is the server ready to accept traffic?
        Used by Kubernetes readiness probes.
        """
        db_healthy = self.check_database()
        redis_healthy = self.check_redis()

        all_healthy = db_healthy and redis_healthy

        return {
            'status': 'ok' if all_healthy else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {
                'database': 'ok' if db_healthy else 'failed',
                'redis': 'ok' if redis_healthy else 'failed',
            },
            'ready': all_healthy,
        }


# Global health checker instance
health_checker = HealthChecker()


def timed(func):
    """Decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(
            json.dumps({
                'event': 'function_timed',
                'function': func.__name__,
                'elapsed_ms': round(elapsed * 1000, 2),
            })
        )
        return result
    return wrapper


async def async_timed(func):
    """Async decorator to measure function execution time."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(
            json.dumps({
                'event': 'async_function_timed',
                'function': func.__name__,
                'elapsed_ms': round(elapsed * 1000, 2),
            })
        )
        return result
    return wrapper
