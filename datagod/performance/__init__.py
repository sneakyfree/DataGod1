"""
Performance Utilities (Phase 5: Launch Readiness)

Provides performance optimization tools:
- Cache manager with TTL
- Async batch processor
- Query optimization helpers
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# CACHE MANAGER
# =============================================================================


@dataclass
class CacheEntry:
    """A single cache entry with TTL."""

    value: Any
    created_at: float
    ttl_seconds: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.ttl_seconds)


class CacheManager:
    """
    In-memory cache with TTL and LRU eviction.

    Features:
    - Time-based expiration (TTL)
    - LRU eviction when max size reached
    - Namespace support
    - Statistics tracking
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,  # 5 minutes
        cleanup_interval: int = 60,  # 1 minute
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval

        self._cache: Dict[str, CacheEntry] = OrderedDict()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "expirations": 0}
        self._last_cleanup = time.time()

    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Get a value from cache.

        Returns None if not found or expired.
        """
        self._maybe_cleanup()

        full_key = f"{namespace}:{key}"
        entry = self._cache.get(full_key)

        if entry is None:
            self._stats["misses"] += 1
            return None

        if entry.is_expired:
            self._cache.pop(full_key, None)
            self._stats["expirations"] += 1
            self._stats["misses"] += 1
            return None

        # Update access info and move to end (LRU)
        entry.access_count += 1
        entry.last_accessed = time.time()
        self._cache.move_to_end(full_key)

        self._stats["hits"] += 1
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default",
    ):
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds (None = default)
            namespace: Cache namespace
        """
        self._maybe_cleanup()

        # Evict if at max size
        while len(self._cache) >= self.max_size:
            self._evict_lru()

        full_key = f"{namespace}:{key}"
        self._cache[full_key] = CacheEntry(
            value=value, created_at=time.time(), ttl_seconds=ttl or self.default_ttl
        )

    def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete a key from cache."""
        full_key = f"{namespace}:{key}"
        if full_key in self._cache:
            del self._cache[full_key]
            return True
        return False

    def clear(self, namespace: Optional[str] = None):
        """Clear cache (optionally by namespace)."""
        if namespace:
            keys_to_delete = [
                k for k in self._cache.keys() if k.startswith(f"{namespace}:")
            ]
            for key in keys_to_delete:
                del self._cache[key]
        else:
            self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0

        return {
            **self._stats,
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_rate": round(hit_rate, 2),
        }

    def _evict_lru(self):
        """Evict least recently used entry."""
        if self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._stats["evictions"] += 1

    def _maybe_cleanup(self):
        """Cleanup expired entries if interval has passed."""
        now = time.time()
        if now - self._last_cleanup < self.cleanup_interval:
            return

        self._last_cleanup = now
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired]

        for key in expired_keys:
            del self._cache[key]
            self._stats["expirations"] += 1


def cached(
    cache: CacheManager,
    ttl: Optional[int] = None,
    namespace: str = "default",
    key_func: Optional[Callable] = None,
):
    """
    Decorator for caching function results.

    Args:
        cache: CacheManager instance
        ttl: Time to live in seconds
        namespace: Cache namespace
        key_func: Function to generate cache key from args
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func.__name__, args, kwargs)

            # Check cache
            result = cache.get(cache_key, namespace)
            if result is not None:
                return result

            # Execute and cache
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl, namespace)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func.__name__, args, kwargs)

            result = cache.get(cache_key, namespace)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl, namespace)
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a cache key from function name and arguments."""
    key_parts = [func_name]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_str = ":".join(key_parts)
    return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()[:16]


# =============================================================================
# ASYNC BATCH PROCESSOR
# =============================================================================


@dataclass
class BatchResult(Generic[T]):
    """Result from batch processing."""

    successful: List[T]
    failed: List[Dict[str, Any]]
    total: int
    success_count: int
    failure_count: int
    duration_seconds: float


class AsyncBatchProcessor:
    """
    Processes items in batches with concurrency control.

    Features:
    - Configurable batch size
    - Concurrency limiting
    - Progress tracking
    - Error handling with retries
    """

    def __init__(
        self,
        batch_size: int = 50,
        max_concurrent: int = 10,
        retry_attempts: int = 2,
        retry_delay: float = 1.0,
    ):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def process(
        self,
        items: List[Any],
        processor: Callable,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> BatchResult:
        """
        Process a list of items in batches.

        Args:
            items: Items to process
            processor: Async function to process each item
            on_progress: Optional callback for progress updates

        Returns:
            BatchResult with successful/failed items
        """
        start_time = time.time()
        successful = []
        failed = []
        processed = 0
        total = len(items)

        # Process in batches
        for i in range(0, total, self.batch_size):
            batch = items[i : i + self.batch_size]

            # Process batch concurrently
            tasks = [self._process_with_retry(processor, item) for item in batch]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for item, result in zip(batch, results):
                if isinstance(result, Exception):
                    failed.append({"item": item, "error": str(result)})
                else:
                    successful.append(result)

            processed += len(batch)

            if on_progress:
                on_progress(processed, total)

        duration = time.time() - start_time

        return BatchResult(
            successful=successful,
            failed=failed,
            total=total,
            success_count=len(successful),
            failure_count=len(failed),
            duration_seconds=round(duration, 2),
        )

    async def _process_with_retry(self, processor: Callable, item: Any) -> Any:
        """Process an item with retry logic."""
        async with self._semaphore:
            last_error = None

            for attempt in range(self.retry_attempts + 1):
                try:
                    if asyncio.iscoroutinefunction(processor):
                        return await processor(item)
                    else:
                        return processor(item)
                except Exception as e:
                    last_error = e
                    if attempt < self.retry_attempts:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))

            raise last_error


# =============================================================================
# QUERY OPTIMIZATION
# =============================================================================


class QueryOptimizer:
    """
    Utilities for optimizing database queries.

    Features:
    - Query analysis
    - Index suggestions
    - Pagination helpers
    """

    @staticmethod
    def paginate(
        query_result: List[Any], page: int = 1, page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Paginate a query result.

        Returns dict with items, pagination info.
        """
        total = len(query_result)
        total_pages = (total + page_size - 1) // page_size

        start = (page - 1) * page_size
        end = start + page_size
        items = query_result[start:end]

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    @staticmethod
    def build_filters(
        filters: Dict[str, Any], allowed_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Safely build query filters.

        Only includes allowed fields to prevent injection.
        """
        safe_filters = {}

        for field, value in filters.items():
            if field in allowed_fields and value is not None:
                safe_filters[field] = value

        return safe_filters

    @staticmethod
    def build_sort(
        sort_field: str,
        sort_order: str,
        allowed_fields: List[str],
        default_field: str = "id",
    ) -> tuple:
        """
        Safely build sort parameters.
        """
        if sort_field not in allowed_fields:
            sort_field = default_field

        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "asc"

        return (sort_field, sort_order.lower())

    @staticmethod
    def estimate_query_cost(filter_count: int, has_index: bool = True) -> str:
        """
        Estimate relative query cost.

        Returns: "low", "medium", or "high"
        """
        if filter_count == 0:
            return "high" if not has_index else "low"
        elif filter_count <= 2:
            return "low" if has_index else "medium"
        else:
            return "medium" if has_index else "high"


# =============================================================================
# PROFILING UTILITIES
# =============================================================================


class PerformanceProfiler:
    """
    Simple performance profiling utilities.
    """

    def __init__(self):
        self._timings: Dict[str, List[float]] = {}

    def time(self, operation: str):
        """Context manager for timing operations."""
        return _TimingContext(self, operation)

    def record(self, operation: str, duration: float):
        """Record a timing."""
        if operation not in self._timings:
            self._timings[operation] = []
        self._timings[operation].append(duration)

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get timing statistics."""
        if operation:
            timings = self._timings.get(operation, [])
            if not timings:
                return {}
            return {
                "count": len(timings),
                "total": sum(timings),
                "avg": sum(timings) / len(timings),
                "min": min(timings),
                "max": max(timings),
            }

        return {op: self.get_stats(op) for op in self._timings}

    def reset(self):
        """Reset all timings."""
        self._timings.clear()


class _TimingContext:
    """Context manager for timing."""

    def __init__(self, profiler: PerformanceProfiler, operation: str):
        self.profiler = profiler
        self.operation = operation
        self.start = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        duration = time.time() - self.start
        self.profiler.record(self.operation, duration)


# Module-level instances
cache_manager = CacheManager()
batch_processor = AsyncBatchProcessor()
query_optimizer = QueryOptimizer()
profiler = PerformanceProfiler()
