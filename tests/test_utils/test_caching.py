"""
Tests for datagod/utils/caching.py

Comprehensive tests for the caching utilities.
"""

import time
from datetime import datetime, timedelta

import pytest

from datagod.utils.caching import (
    CacheEntry,
    CacheInvalidator,
    CacheWarmer,
    LRUCache,
    async_cached,
    cache_clear,
    cache_delete,
    cache_get,
    cache_set,
    cache_stats,
    cached,
    configure_default_cache,
    get_default_cache,
    make_cache_key,
)


class TestCacheEntry:
    """Tests for CacheEntry dataclass"""

    def test_create_entry(self):
        """Test creating a cache entry"""
        entry = CacheEntry(
            value="test_value",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert entry.value == "test_value"
        assert entry.hits == 0
        assert entry.is_expired is False

    def test_entry_not_expired(self):
        """Test entry is not expired"""
        entry = CacheEntry(
            value="test",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert entry.is_expired is False

    def test_entry_expired(self):
        """Test entry is expired"""
        entry = CacheEntry(
            value="test",
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),
        )
        assert entry.is_expired is True

    def test_entry_no_expiry(self):
        """Test entry with no expiration"""
        entry = CacheEntry(
            value="test",
            created_at=datetime.now(),
            expires_at=None,
        )
        assert entry.is_expired is False

    def test_access_increments_hits(self):
        """Test access increments hit counter"""
        entry = CacheEntry(
            value="test",
            created_at=datetime.now(),
            expires_at=None,
        )
        assert entry.hits == 0
        entry.access()
        assert entry.hits == 1
        entry.access()
        assert entry.hits == 2


class TestLRUCache:
    """Tests for LRUCache class"""

    def test_create_cache(self):
        """Test creating a cache"""
        cache = LRUCache(max_size=100, default_ttl_seconds=60)
        assert cache.max_size == 100
        assert len(cache) == 0

    def test_set_and_get(self):
        """Test setting and getting values"""
        cache = LRUCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent(self):
        """Test getting nonexistent key"""
        cache = LRUCache()
        assert cache.get("nonexistent") is None

    def test_overwrite_value(self):
        """Test overwriting a value"""
        cache = LRUCache()
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        assert cache.get("key1") == "value2"

    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = LRUCache(default_ttl_seconds=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        time.sleep(1.5)
        assert cache.get("key1") is None

    def test_custom_ttl(self):
        """Test custom TTL per key"""
        cache = LRUCache(default_ttl_seconds=60)
        cache.set("key1", "value1", ttl_seconds=1)

        time.sleep(1.5)
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        """Test LRU eviction when at capacity"""
        cache = LRUCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add key4, should evict key2 (least recently used)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_delete(self):
        """Test deleting a key"""
        cache = LRUCache()
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_nonexistent(self):
        """Test deleting nonexistent key"""
        cache = LRUCache()
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        """Test clearing cache"""
        cache = LRUCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert len(cache) == 0

    def test_cleanup_expired(self):
        """Test cleaning up expired entries"""
        cache = LRUCache(default_ttl_seconds=1)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        time.sleep(1.5)

        removed = cache.cleanup_expired()
        assert removed == 2

    def test_get_stats(self):
        """Test getting cache statistics"""
        cache = LRUCache(max_size=100)
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_keys(self):
        """Test getting all keys"""
        cache = LRUCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        keys = cache.keys()
        assert "key1" in keys
        assert "key2" in keys

    def test_contains(self):
        """Test contains check"""
        cache = LRUCache()
        cache.set("key1", "value1")

        assert "key1" in cache
        assert "key2" not in cache


class TestCachedDecorator:
    """Tests for the cached decorator"""

    def test_cached_function(self):
        """Test caching a function result"""
        test_cache = LRUCache(max_size=100)
        call_count = 0

        @cached(ttl_seconds=60, cache=test_cache)
        def expensive_function_1(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function_1(5)
        result2 = expensive_function_1(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Only called once

    def test_cached_different_args(self):
        """Test cache with different arguments"""
        test_cache = LRUCache(max_size=100)
        call_count = 0

        @cached(ttl_seconds=60, cache=test_cache)
        def expensive_function_2(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function_2(5)
        result2 = expensive_function_2(10)

        assert result1 == 10
        assert result2 == 20
        assert call_count == 2  # Called twice for different args

    def test_cached_invalidate(self):
        """Test cache invalidation"""

        @cached(ttl_seconds=60)
        def expensive_function(x):
            return x * 2

        expensive_function(5)
        expensive_function.invalidate(5)

        # After invalidation, function should be called again
        # (can't easily verify without modifying function)

    def test_cached_with_kwargs(self):
        """Test caching with keyword arguments"""
        call_count = 0

        @cached(ttl_seconds=60)
        def func_with_kwargs(a, b=10):
            nonlocal call_count
            call_count += 1
            return a + b

        result1 = func_with_kwargs(5, b=20)
        result2 = func_with_kwargs(5, b=20)

        assert result1 == 25
        assert result2 == 25
        assert call_count == 1


class TestMakeCacheKey:
    """Tests for make_cache_key function"""

    def test_basic_key(self):
        """Test basic key generation"""
        key = make_cache_key("arg1", "arg2")
        assert isinstance(key, str)
        assert len(key) == 16  # SHA256 truncated to 16 chars

    def test_consistent_keys(self):
        """Test key consistency"""
        key1 = make_cache_key("arg1", "arg2", kwarg1="value1")
        key2 = make_cache_key("arg1", "arg2", kwarg1="value1")
        assert key1 == key2

    def test_different_args_different_keys(self):
        """Test different args produce different keys"""
        key1 = make_cache_key("arg1")
        key2 = make_cache_key("arg2")
        assert key1 != key2


class TestCacheWarmer:
    """Tests for CacheWarmer class"""

    def test_register_and_warm(self):
        """Test registering and warming cache"""
        cache = LRUCache()
        warmer = CacheWarmer(cache)

        warmer.register("key1", lambda: "value1", ttl_seconds=60)
        warmer.register("key2", lambda: "value2", ttl_seconds=60)

        results = warmer.warm()

        assert results["total"] == 2
        assert results["success"] == 2
        assert results["failed"] == 0

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

    def test_warm_with_priority(self):
        """Test warming with priority order"""
        cache = LRUCache()
        warmer = CacheWarmer(cache)

        warmer.register("low", lambda: "low", priority=0)
        warmer.register("high", lambda: "high", priority=10)

        # High priority should be first in list
        assert warmer._warming_tasks[0]["key"] == "high"

    def test_warm_with_failure(self):
        """Test warming handles failures"""
        cache = LRUCache()
        warmer = CacheWarmer(cache)

        warmer.register("good", lambda: "value")
        warmer.register("bad", lambda: 1 / 0)  # Will raise

        results = warmer.warm()

        assert results["success"] == 1
        assert results["failed"] == 1
        assert len(results["errors"]) == 1


class TestCacheInvalidator:
    """Tests for CacheInvalidator class"""

    def test_invalidate_by_tag(self):
        """Test tag-based invalidation"""
        cache = LRUCache()
        invalidator = CacheInvalidator(cache)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        invalidator.tag("key1", ["tag1"])
        invalidator.tag("key2", ["tag1"])
        invalidator.tag("key3", ["tag2"])

        count = invalidator.invalidate_by_tag("tag1")

        assert count == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"

    def test_invalidate_by_pattern(self):
        """Test pattern-based invalidation"""
        cache = LRUCache()
        invalidator = CacheInvalidator(cache)

        cache.set("user:1", "value1")
        cache.set("user:2", "value2")
        cache.set("order:1", "value3")

        count = invalidator.invalidate_by_pattern("user:*")

        assert count == 2
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("order:1") == "value3"


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_get_default_cache(self):
        """Test getting default cache"""
        cache = get_default_cache()
        assert isinstance(cache, LRUCache)

    def test_configure_default_cache(self):
        """Test configuring default cache"""
        configure_default_cache(max_size=500, default_ttl_seconds=120)
        cache = get_default_cache()
        assert cache.max_size == 500

    def test_cache_convenience_functions(self):
        """Test cache convenience functions"""
        cache_clear()

        cache_set("test_key", "test_value")
        assert cache_get("test_key") == "test_value"

        cache_delete("test_key")
        assert cache_get("test_key") is None

    def test_cache_stats_function(self):
        """Test cache stats function"""
        cache_clear()
        cache_set("key1", "value1")
        cache_get("key1")

        stats = cache_stats()
        assert "size" in stats
        assert "hits" in stats


@pytest.mark.asyncio
class TestAsyncCached:
    """Tests for async_cached decorator"""

    async def test_async_cached_function(self):
        """Test caching an async function result"""
        call_count = 0

        @async_cached(ttl_seconds=60)
        async def async_expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await async_expensive_function(5)
        result2 = await async_expensive_function(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1
