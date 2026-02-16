"""
Tests for Performance utilities — coverage target for performance/__init__.py (56% → 80%+)
"""

import pytest
import asyncio
import time

from datagod.performance import (
    CacheManager,
    CacheEntry,
    AsyncBatchProcessor,
    BatchResult,
    cached,
    _generate_cache_key,
)


class TestCacheEntry:
    def test_not_expired(self):
        entry = CacheEntry(value="test", created_at=time.time(), ttl_seconds=60)
        assert entry.is_expired is False

    def test_expired(self):
        entry = CacheEntry(value="test", created_at=time.time() - 100, ttl_seconds=10)
        assert entry.is_expired is True


class TestCacheManager:
    def setup_method(self):
        self.cache = CacheManager(max_size=10, default_ttl=60)

    def test_set_and_get(self):
        self.cache.set("key1", "value1")
        assert self.cache.get("key1") == "value1"

    def test_get_missing_key(self):
        assert self.cache.get("nonexistent") is None

    def test_set_with_custom_ttl(self):
        self.cache.set("key1", "value1", ttl=1)
        assert self.cache.get("key1") == "value1"

    def test_expired_key_returns_none(self):
        # Use a very short ttl and sleep past it
        self.cache.set("key1", "value1", ttl=1)
        time.sleep(1.1)
        assert self.cache.get("key1") is None

    def test_delete(self):
        self.cache.set("key1", "value1")
        self.cache.delete("key1")
        assert self.cache.get("key1") is None

    def test_delete_missing_key(self):
        # Should not raise
        self.cache.delete("nonexistent")

    def test_clear_all(self):
        self.cache.set("k1", "v1")
        self.cache.set("k2", "v2")
        self.cache.clear()
        assert self.cache.get("k1") is None
        assert self.cache.get("k2") is None

    def test_clear_by_namespace(self):
        self.cache.set("k1", "v1", namespace="ns1")
        self.cache.set("k2", "v2", namespace="ns2")
        self.cache.clear(namespace="ns1")
        assert self.cache.get("k1", namespace="ns1") is None
        assert self.cache.get("k2", namespace="ns2") == "v2"

    def test_namespaces(self):
        self.cache.set("key", "value_a", namespace="a")
        self.cache.set("key", "value_b", namespace="b")
        assert self.cache.get("key", namespace="a") == "value_a"
        assert self.cache.get("key", namespace="b") == "value_b"

    def test_get_stats(self):
        self.cache.set("k1", "v1")
        self.cache.get("k1")
        self.cache.get("k1")
        self.cache.get("missing")
        stats = self.cache.get_stats()
        assert isinstance(stats, dict)
        assert stats["hits"] >= 2
        assert stats["misses"] >= 1

    def test_eviction_on_max_size(self):
        cache = CacheManager(max_size=3, default_ttl=60)
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
        # Oldest keys should be evicted
        stats = cache.get_stats()
        assert stats["evictions"] > 0

    def test_overwrite_existing_key(self):
        self.cache.set("key", "old")
        self.cache.set("key", "new")
        assert self.cache.get("key") == "new"


class TestCacheDecorator:
    def test_sync_cached(self):
        cache = CacheManager()

        @cached(cache, ttl=60, namespace="test")
        def expensive_func(x):
            return x * 2

        result1 = expensive_func(5)
        result2 = expensive_func(5)
        assert result1 == 10
        assert result2 == 10  # Should come from cache

    @pytest.mark.asyncio
    async def test_async_cached(self):
        cache = CacheManager()

        @cached(cache, ttl=60, namespace="test_async")
        async def expensive_async(x):
            return x * 3

        result1 = await expensive_async(4)
        result2 = await expensive_async(4)
        assert result1 == 12
        assert result2 == 12


class TestGenerateCacheKey:
    def test_generates_key(self):
        key = _generate_cache_key("my_func", (1, 2), {"a": "b"})
        assert isinstance(key, str)
        assert len(key) > 0

    def test_different_args_different_keys(self):
        k1 = _generate_cache_key("func", (1,), {})
        k2 = _generate_cache_key("func", (2,), {})
        assert k1 != k2


class TestAsyncBatchProcessor:
    def setup_method(self):
        self.processor = AsyncBatchProcessor(batch_size=3, max_concurrent=2)

    @pytest.mark.asyncio
    async def test_process_all_succeed(self):
        items = [1, 2, 3, 4, 5]

        async def doubler(item):
            return item * 2

        result = await self.processor.process(items, doubler)
        assert isinstance(result, BatchResult)
        assert result.success_count == 5
        assert result.failure_count == 0
        assert result.total == 5

    @pytest.mark.asyncio
    async def test_process_with_failures(self):
        items = [1, 2, 0, 4]

        async def divider(item):
            if item == 0:
                raise ValueError("Cannot divide by zero")
            return 10 / item

        processor = AsyncBatchProcessor(batch_size=5, retry_attempts=1, retry_delay=0.01)
        result = await processor.process(items, divider)
        assert result.failure_count >= 1

    @pytest.mark.asyncio
    async def test_process_empty_list(self):
        async def noop(item):
            return item

        result = await self.processor.process([], noop)
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_process_with_progress(self):
        progress_calls = []

        def on_progress(done, total):
            progress_calls.append((done, total))

        items = list(range(6))

        async def identity(item):
            return item

        result = await self.processor.process(items, identity, on_progress=on_progress)
        assert result.success_count == 6
        assert len(progress_calls) > 0
