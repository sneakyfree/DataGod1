"""
Caching Utilities for DataGod

Provides caching strategies for API responses, database queries,
and scraper results to improve performance.

Features:
- In-memory LRU cache
- Redis cache (optional)
- TTL-based expiration
- Cache warming
- Cache invalidation
"""

import logging
import time
import json
import hashlib
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, TypeVar, Union
from dataclasses import dataclass, field
from collections import OrderedDict
from threading import Lock
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry:
    """A single cache entry with metadata"""
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    hits: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def access(self):
        """Record an access to this entry"""
        self.hits += 1
        self.last_accessed = datetime.now()


class LRUCache:
    """
    Thread-safe LRU (Least Recently Used) cache.

    Features:
    - O(1) get and put operations
    - TTL-based expiration
    - Size-limited with automatic eviction
    - Thread-safe operations
    """

    def __init__(self, max_size: int = 1000, default_ttl_seconds: int = 300):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            default_ttl_seconds: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
        }

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None

            entry = self._cache[key]

            if entry.is_expired:
                del self._cache[key]
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access()
            self._stats['hits'] += 1

            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int = None):
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Optional TTL override
        """
        with self._lock:
            # Remove old entry if exists
            if key in self._cache:
                del self._cache[key]

            # Evict LRU entries if at capacity
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats['evictions'] += 1

            # Calculate expiration
            ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self.default_ttl
            expires_at = datetime.now() + ttl if ttl else None

            # Add new entry
            self._cache[key] = CacheEntry(
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at,
            )

    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats['expirations'] += 1

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0

            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': round(hit_rate * 100, 2),
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations'],
            }

    def keys(self) -> List[str]:
        """Get all cache keys"""
        with self._lock:
            return list(self._cache.keys())

    def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        return self.get(key) is not None

    def __len__(self) -> int:
        """Get number of cache entries"""
        with self._lock:
            return len(self._cache)


def make_cache_key(*args, **kwargs) -> str:
    """
    Create a cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        SHA256 hash of arguments
    """
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]


def cached(ttl_seconds: int = 300, cache: LRUCache = None, key_prefix: str = ""):
    """
    Decorator to cache function results.

    Args:
        ttl_seconds: Cache TTL in seconds
        cache: Optional cache instance (uses default if not provided)
        key_prefix: Optional prefix for cache keys

    Example:
        @cached(ttl_seconds=60)
        def expensive_function(arg1, arg2):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        _cache = cache or get_default_cache()

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Build cache key
            func_key = f"{key_prefix}{func.__name__}"
            args_key = make_cache_key(*args, **kwargs)
            cache_key = f"{func_key}:{args_key}"

            # Check cache
            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl_seconds)
            logger.debug(f"Cache miss for {func.__name__}, result cached")

            return result

        # Add cache management methods to wrapper
        wrapper.cache = _cache
        wrapper.invalidate = lambda *args, **kwargs: _cache.delete(
            f"{key_prefix}{func.__name__}:{make_cache_key(*args, **kwargs)}"
        )

        return wrapper
    return decorator


def async_cached(ttl_seconds: int = 300, cache: LRUCache = None, key_prefix: str = ""):
    """
    Decorator to cache async function results.

    Args:
        ttl_seconds: Cache TTL in seconds
        cache: Optional cache instance
        key_prefix: Optional prefix for cache keys
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        _cache = cache or get_default_cache()

        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            func_key = f"{key_prefix}{func.__name__}"
            args_key = make_cache_key(*args, **kwargs)
            cache_key = f"{func_key}:{args_key}"

            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            _cache.set(cache_key, result, ttl_seconds)

            return result

        wrapper.cache = _cache
        wrapper.invalidate = lambda *args, **kwargs: _cache.delete(
            f"{key_prefix}{func.__name__}:{make_cache_key(*args, **kwargs)}"
        )

        return wrapper
    return decorator


class CacheWarmer:
    """
    Pre-populates cache with commonly accessed data.

    Features:
    - Background warming
    - Priority-based warming
    - Progress tracking
    """

    def __init__(self, cache: LRUCache = None):
        self.cache = cache if cache is not None else get_default_cache()
        self._warming_tasks: List[Dict[str, Any]] = []
        self._is_warming = False

    def register(self, key: str, loader: Callable[[], Any],
                 ttl_seconds: int = 300, priority: int = 0):
        """
        Register a cache warming task.

        Args:
            key: Cache key
            loader: Function to load the data
            ttl_seconds: Cache TTL
            priority: Higher priority tasks run first
        """
        self._warming_tasks.append({
            'key': key,
            'loader': loader,
            'ttl_seconds': ttl_seconds,
            'priority': priority,
        })
        self._warming_tasks.sort(key=lambda x: -x['priority'])

    def warm(self) -> Dict[str, Any]:
        """
        Execute all warming tasks.

        Returns:
            Summary of warming results
        """
        self._is_warming = True
        results = {
            'total': len(self._warming_tasks),
            'success': 0,
            'failed': 0,
            'errors': [],
        }

        for task in self._warming_tasks:
            try:
                value = task['loader']()
                self.cache.set(task['key'], value, task['ttl_seconds'])
                results['success'] += 1
                logger.debug(f"Warmed cache key: {task['key']}")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'key': task['key'],
                    'error': str(e),
                })
                logger.error(f"Failed to warm cache key {task['key']}: {e}")

        self._is_warming = False
        logger.info(f"Cache warming complete: {results['success']}/{results['total']} successful")

        return results

    async def warm_async(self) -> Dict[str, Any]:
        """Execute warming tasks asynchronously"""
        self._is_warming = True
        results = {
            'total': len(self._warming_tasks),
            'success': 0,
            'failed': 0,
            'errors': [],
        }

        async def warm_task(task):
            try:
                if asyncio.iscoroutinefunction(task['loader']):
                    value = await task['loader']()
                else:
                    value = task['loader']()
                self.cache.set(task['key'], value, task['ttl_seconds'])
                return True, None
            except Exception as e:
                return False, {'key': task['key'], 'error': str(e)}

        tasks = [warm_task(task) for task in self._warming_tasks]
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for success, error in task_results:
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                if error:
                    results['errors'].append(error)

        self._is_warming = False
        return results


class CacheInvalidator:
    """
    Manages cache invalidation patterns.

    Features:
    - Pattern-based invalidation
    - Tag-based invalidation
    - Cascade invalidation
    """

    def __init__(self, cache: LRUCache = None):
        self.cache = cache if cache is not None else get_default_cache()
        self._tag_registry: Dict[str, List[str]] = {}  # tag -> [keys]

    def tag(self, key: str, tags: List[str]):
        """
        Associate tags with a cache key.

        Args:
            key: Cache key
            tags: List of tags
        """
        for tag in tags:
            if tag not in self._tag_registry:
                self._tag_registry[tag] = []
            if key not in self._tag_registry[tag]:
                self._tag_registry[tag].append(key)

    def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all keys with a given tag.

        Args:
            tag: Tag to invalidate

        Returns:
            Number of keys invalidated
        """
        keys = self._tag_registry.get(tag, [])
        count = 0

        for key in keys:
            if self.cache.delete(key):
                count += 1

        if tag in self._tag_registry:
            del self._tag_registry[tag]

        logger.info(f"Invalidated {count} keys with tag '{tag}'")
        return count

    def invalidate_by_pattern(self, pattern: str) -> int:
        """
        Invalidate keys matching a pattern.

        Args:
            pattern: Pattern to match (supports * wildcard)

        Returns:
            Number of keys invalidated
        """
        import fnmatch

        all_keys = self.cache.keys()
        matching_keys = fnmatch.filter(all_keys, pattern)
        count = 0

        for key in matching_keys:
            if self.cache.delete(key):
                count += 1

        logger.info(f"Invalidated {count} keys matching pattern '{pattern}'")
        return count


# Default cache instance
_default_cache: Optional[LRUCache] = None
_default_lock = Lock()


def get_default_cache() -> LRUCache:
    """Get the default cache instance"""
    global _default_cache
    with _default_lock:
        if _default_cache is None:
            _default_cache = LRUCache(max_size=10000, default_ttl_seconds=300)
        return _default_cache


def configure_default_cache(max_size: int = 10000, default_ttl_seconds: int = 300):
    """Configure the default cache instance"""
    global _default_cache
    with _default_lock:
        _default_cache = LRUCache(max_size=max_size, default_ttl_seconds=default_ttl_seconds)


# Convenience functions
def cache_get(key: str) -> Optional[Any]:
    """Get value from default cache"""
    return get_default_cache().get(key)


def cache_set(key: str, value: Any, ttl_seconds: int = None):
    """Set value in default cache"""
    get_default_cache().set(key, value, ttl_seconds)


def cache_delete(key: str) -> bool:
    """Delete key from default cache"""
    return get_default_cache().delete(key)


def cache_clear():
    """Clear default cache"""
    get_default_cache().clear()


def cache_stats() -> Dict[str, Any]:
    """Get default cache statistics"""
    return get_default_cache().get_stats()
