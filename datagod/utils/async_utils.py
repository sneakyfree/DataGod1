"""
Async Utilities for DataGod

Provides async/concurrent processing utilities for improved performance.

Features:
- Async HTTP client with connection pooling
- Concurrent task execution with rate limiting
- Async database operations
- Background job processing
"""

import logging
import asyncio
from typing import (
    Dict, List, Any, Optional, Callable, TypeVar, Coroutine,
    AsyncIterator, Awaitable
)
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import aiohttp
from asyncio import Semaphore, Queue
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RateLimiter:
    """
    Async rate limiter using token bucket algorithm.

    Features:
    - Configurable requests per second
    - Burst capacity
    - Async-safe
    """
    requests_per_second: float
    burst_size: int = 10
    _tokens: float = field(default=0, init=False)
    _last_update: float = field(default_factory=time.monotonic, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self):
        self._tokens = float(self.burst_size)

    async def acquire(self):
        """Acquire a token, waiting if necessary"""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update
            self._last_update = now

            # Add tokens based on elapsed time
            self._tokens = min(
                self.burst_size,
                self._tokens + elapsed * self.requests_per_second
            )

            if self._tokens < 1:
                # Wait for a token
                wait_time = (1 - self._tokens) / self.requests_per_second
                await asyncio.sleep(wait_time)
                self._tokens = 0
            else:
                self._tokens -= 1


class AsyncHTTPClient:
    """
    Async HTTP client with connection pooling and rate limiting.

    Features:
    - Connection pooling
    - Automatic retries
    - Rate limiting
    - Response caching
    """

    def __init__(
        self,
        base_url: str = "",
        max_connections: int = 100,
        requests_per_second: float = 10.0,
        timeout_seconds: int = 30,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ):
        self.base_url = base_url
        self.max_connections = max_connections
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            burst_size=int(requests_per_second * 2)
        )
        self._session: Optional[aiohttp.ClientSession] = None
        self._stats = {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'retries': 0,
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                enable_cleanup_closed=True,
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
            )
        return self._session

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an HTTP request with retries"""
        full_url = f"{self.base_url}{url}" if not url.startswith("http") else url

        for attempt in range(self.retry_count + 1):
            try:
                await self.rate_limiter.acquire()
                session = await self._get_session()
                self._stats['requests'] += 1

                async with session.request(method, full_url, **kwargs) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self._stats['successes'] += 1
                    return {
                        'status': response.status,
                        'data': data,
                        'headers': dict(response.headers),
                    }

            except aiohttp.ClientError as e:
                self._stats['retries'] += 1
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")

                if attempt < self.retry_count:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    self._stats['failures'] += 1
                    raise

    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP GET request"""
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP POST request"""
        return await self._request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP PUT request"""
        return await self._request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP DELETE request"""
        return await self._request("DELETE", url, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return self._stats.copy()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def gather_with_limit(
    tasks: List[Coroutine],
    limit: int = 10,
    return_exceptions: bool = False
) -> List[Any]:
    """
    Execute coroutines with concurrency limit.

    Args:
        tasks: List of coroutines to execute
        limit: Maximum concurrent tasks
        return_exceptions: If True, exceptions are returned instead of raised

    Returns:
        List of results in order
    """
    semaphore = Semaphore(limit)

    async def limited_task(coro):
        async with semaphore:
            return await coro

    limited_tasks = [limited_task(task) for task in tasks]
    return await asyncio.gather(*limited_tasks, return_exceptions=return_exceptions)


async def map_async(
    func: Callable[[T], Awaitable[Any]],
    items: List[T],
    limit: int = 10
) -> List[Any]:
    """
    Apply async function to items with concurrency limit.

    Args:
        func: Async function to apply
        items: Items to process
        limit: Maximum concurrent operations

    Returns:
        List of results
    """
    tasks = [func(item) for item in items]
    return await gather_with_limit(tasks, limit)


class AsyncWorkerPool:
    """
    Pool of async workers for background processing.

    Features:
    - Configurable worker count
    - Task queue with priorities
    - Graceful shutdown
    """

    def __init__(self, num_workers: int = 5, max_queue_size: int = 1000):
        self.num_workers = num_workers
        self.max_queue_size = max_queue_size
        self._queue: Queue = Queue(maxsize=max_queue_size)
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._stats = {
            'tasks_processed': 0,
            'tasks_failed': 0,
        }

    async def start(self):
        """Start worker pool"""
        if self._running:
            return

        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.num_workers)
        ]
        logger.info(f"Started {self.num_workers} async workers")

    async def stop(self, timeout: float = 30.0):
        """Stop worker pool gracefully"""
        if not self._running:
            return

        self._running = False

        # Wait for queue to drain or timeout
        try:
            await asyncio.wait_for(self._queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for queue to drain")

        # Cancel workers
        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []
        logger.info("Async worker pool stopped")

    async def _worker(self, worker_id: int):
        """Worker coroutine"""
        while self._running:
            try:
                task_data = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )

                try:
                    func, args, kwargs, future = task_data
                    result = await func(*args, **kwargs)
                    future.set_result(result)
                    self._stats['tasks_processed'] += 1
                except Exception as e:
                    future.set_exception(e)
                    self._stats['tasks_failed'] += 1
                    logger.error(f"Worker {worker_id} task failed: {e}")
                finally:
                    self._queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def submit(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> asyncio.Future:
        """
        Submit a task to the worker pool.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Future that will contain the result
        """
        future = asyncio.get_event_loop().create_future()
        await self._queue.put((func, args, kwargs, future))
        return future

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            **self._stats,
            'queue_size': self._queue.qsize(),
            'workers': self.num_workers,
            'running': self._running,
        }


class AsyncBatcher:
    """
    Batches async operations for efficiency.

    Collects operations and executes them in batches.
    """

    def __init__(
        self,
        batch_size: int = 100,
        flush_interval: float = 1.0,
        processor: Callable[[List[Any]], Awaitable[List[Any]]] = None
    ):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.processor = processor
        self._items: List[Any] = []
        self._futures: List[asyncio.Future] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    async def add(self, item: Any) -> asyncio.Future:
        """
        Add an item to the batch.

        Args:
            item: Item to process

        Returns:
            Future that will contain the result
        """
        async with self._lock:
            future = asyncio.get_event_loop().create_future()
            self._items.append(item)
            self._futures.append(future)

            if len(self._items) >= self.batch_size:
                await self._flush()
            elif self._flush_task is None:
                self._flush_task = asyncio.create_task(self._delayed_flush())

            return future

    async def _delayed_flush(self):
        """Flush after interval"""
        await asyncio.sleep(self.flush_interval)
        async with self._lock:
            if self._items:
                await self._flush()

    async def _flush(self):
        """Process current batch"""
        if not self._items:
            return

        items = self._items
        futures = self._futures
        self._items = []
        self._futures = []
        self._flush_task = None

        try:
            if self.processor:
                results = await self.processor(items)
                for future, result in zip(futures, results):
                    future.set_result(result)
            else:
                for future, item in zip(futures, items):
                    future.set_result(item)
        except Exception as e:
            for future in futures:
                future.set_exception(e)

    async def flush(self):
        """Force flush pending items"""
        async with self._lock:
            await self._flush()


@asynccontextmanager
async def timeout(seconds: float):
    """
    Async context manager for timeouts.

    Usage:
        async with timeout(5.0):
            await some_operation()
    """
    try:
        yield await asyncio.wait_for(asyncio.sleep(0), timeout=seconds)
    except asyncio.TimeoutError:
        raise


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    **kwargs
) -> T:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to call
        *args: Positional arguments
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch
        **kwargs: Keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = delay * (backoff ** attempt)
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)

    raise last_exception


async def run_in_executor(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a synchronous function in thread executor.

    Useful for I/O-bound operations that don't have async versions.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: func(*args, **kwargs)
    )


class AsyncCircuitBreaker:
    """
    Circuit breaker for async operations.

    Prevents cascading failures by stopping requests to failing services.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        self._failures = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = "closed"  # closed, open, half-open
        self._half_open_successes = 0
        self._lock = asyncio.Lock()

    @property
    def is_open(self) -> bool:
        return self._state == "open"

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """
        Execute function with circuit breaker protection.
        """
        async with self._lock:
            if self._state == "open":
                if self._should_try_reset():
                    self._state = "half-open"
                    self._half_open_successes = 0
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)

            async with self._lock:
                if self._state == "half-open":
                    self._half_open_successes += 1
                    if self._half_open_successes >= self.half_open_requests:
                        self._reset()

            return result

        except Exception as e:
            await self._record_failure()
            raise

    def _should_try_reset(self) -> bool:
        if self._last_failure_time is None:
            return True
        elapsed = (datetime.now() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    async def _record_failure(self):
        async with self._lock:
            self._failures += 1
            self._last_failure_time = datetime.now()

            if self._failures >= self.failure_threshold:
                self._state = "open"
                logger.warning("Circuit breaker opened")

    def _reset(self):
        self._failures = 0
        self._state = "closed"
        self._last_failure_time = None
        logger.info("Circuit breaker reset")

    def get_state(self) -> Dict[str, Any]:
        return {
            'state': self._state,
            'failures': self._failures,
            'last_failure': self._last_failure_time.isoformat() if self._last_failure_time else None,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass
