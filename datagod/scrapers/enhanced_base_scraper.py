"""
Enhanced Base Scraper with JavaScript Rendering, Proxy Rotation, and Advanced Features
Implements Task 4.3 of the Master Plan
"""

import asyncio
import hashlib
import json
import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from queue import Queue
from typing import Any, Callable, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ScraperType(Enum):
    """Types of scrapers"""

    SIMPLE = "simple"  # Basic HTTP requests
    BROWSER = "browser"  # Playwright browser rendering
    HYBRID = "hybrid"  # Uses both based on content


class ProxyType(Enum):
    """Types of proxy protocols"""

    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


@dataclass
class ProxyConfig:
    """Configuration for a single proxy"""

    host: str
    port: int
    protocol: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    is_active: bool = True
    failure_count: int = 0
    success_count: int = 0
    last_used: Optional[datetime] = None
    avg_response_time: float = 0.0

    @property
    def url(self) -> str:
        """Get proxy URL"""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.protocol.value}://{auth}{self.host}:{self.port}"

    def record_success(self, response_time: float):
        """Record successful request"""
        self.success_count += 1
        self.failure_count = max(0, self.failure_count - 1)
        self.last_used = datetime.utcnow()
        # Running average of response time
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time * 0.9) + (
                response_time * 0.1
            )

    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_used = datetime.utcnow()
        if self.failure_count >= 5:
            self.is_active = False


@dataclass
class ScrapingMetrics:
    """Metrics for scraping operations"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_data_points: int = 0
    bytes_downloaded: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests * 100

    @property
    def duration_seconds(self) -> float:
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": f"{self.success_rate:.2f}%",
            "total_data_points": self.total_data_points,
            "bytes_downloaded": self.bytes_downloaded,
            "duration_seconds": self.duration_seconds,
            "requests_per_second": self.total_requests / max(1, self.duration_seconds),
            "error_count": len(self.errors),
        }


class ProxyRotator:
    """Manages proxy rotation with health checking"""

    def __init__(self, proxies: List[ProxyConfig] = None):
        self.proxies: List[ProxyConfig] = proxies or []
        self._lock = threading.Lock()
        self._current_index = 0

    def add_proxy(self, proxy: ProxyConfig):
        """Add a proxy to the pool"""
        with self._lock:
            self.proxies.append(proxy)

    def add_proxies_from_list(self, proxy_list: List[Dict[str, Any]]):
        """Add multiple proxies from a list of dictionaries"""
        for p in proxy_list:
            proxy = ProxyConfig(
                host=p["host"],
                port=p["port"],
                protocol=ProxyType(p.get("protocol", "http")),
                username=p.get("username"),
                password=p.get("password"),
                country=p.get("country"),
            )
            self.add_proxy(proxy)

    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next active proxy (round-robin)"""
        with self._lock:
            active_proxies = [p for p in self.proxies if p.is_active]
            if not active_proxies:
                return None

            self._current_index = (self._current_index + 1) % len(active_proxies)
            return active_proxies[self._current_index]

    def get_random_proxy(self) -> Optional[ProxyConfig]:
        """Get a random active proxy"""
        with self._lock:
            active_proxies = [p for p in self.proxies if p.is_active]
            if not active_proxies:
                return None
            return random.choice(active_proxies)

    def get_best_proxy(self) -> Optional[ProxyConfig]:
        """Get the best performing proxy"""
        with self._lock:
            active_proxies = [p for p in self.proxies if p.is_active]
            if not active_proxies:
                return None

            # Score based on success rate and response time
            def score(p: ProxyConfig) -> float:
                success_rate = p.success_count / max(
                    1, p.success_count + p.failure_count
                )
                response_score = 1 / max(0.1, p.avg_response_time)
                return success_rate * 0.7 + response_score * 0.3

            return max(active_proxies, key=score)

    def mark_success(self, proxy: ProxyConfig, response_time: float):
        """Mark a proxy request as successful"""
        proxy.record_success(response_time)

    def mark_failure(self, proxy: ProxyConfig):
        """Mark a proxy request as failed"""
        proxy.record_failure()

    def get_stats(self) -> Dict[str, Any]:
        """Get proxy pool statistics"""
        with self._lock:
            active = [p for p in self.proxies if p.is_active]
            inactive = [p for p in self.proxies if not p.is_active]

            return {
                "total_proxies": len(self.proxies),
                "active_proxies": len(active),
                "inactive_proxies": len(inactive),
                "avg_success_rate": (
                    sum(
                        p.success_count / max(1, p.success_count + p.failure_count)
                        for p in active
                    )
                    / max(1, len(active))
                    * 100
                    if active
                    else 0
                ),
            }


class RateLimiter:
    """Rate limiter with token bucket algorithm"""

    def __init__(self, requests_per_second: float = 1.0, burst_size: int = 5):
        self.rate = requests_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = None) -> bool:
        """Acquire a token, blocking if necessary"""
        start_time = time.time()

        while True:
            with self._lock:
                now = time.time()
                # Add tokens based on time passed
                time_passed = now - self.last_update
                self.tokens = min(
                    self.burst_size, self.tokens + time_passed * self.rate
                )
                self.last_update = now

                if self.tokens >= 1:
                    self.tokens -= 1
                    return True

            # Check timeout
            if timeout is not None and (time.time() - start_time) >= timeout:
                return False

            # Wait before retrying
            time.sleep(0.1)

    def wait(self):
        """Wait until a token is available"""
        self.acquire(timeout=None)


class EnhancedBaseScraper(ABC):
    """
    Enhanced base scraper with:
    - JavaScript rendering via Playwright
    - Proxy rotation
    - Rate limiting
    - Retry logic with exponential backoff
    - Request/response caching
    - Concurrent scraping
    - Comprehensive metrics
    """

    def __init__(
        self,
        base_url: str,
        scraper_type: ScraperType = ScraperType.SIMPLE,
        rate_limit: float = 1.0,
        timeout: int = 30,
        max_retries: int = 3,
        use_proxies: bool = False,
        cache_enabled: bool = True,
        cache_ttl: int = 3600,
        concurrent_requests: int = 1,
        user_agents: List[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.scraper_type = scraper_type
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_proxies = use_proxies
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.concurrent_requests = concurrent_requests

        # Rate limiting
        self.rate_limiter = RateLimiter(
            rate_limit, burst_size=max(5, int(rate_limit * 2))
        )

        # Proxy rotation
        self.proxy_rotator = ProxyRotator() if use_proxies else None

        # Session setup with retry
        self.session = self._create_session()

        # User agent rotation
        self.user_agents = user_agents or [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

        # Cache
        self._cache: Dict[str, Dict[str, Any]] = {}

        # Metrics
        self.metrics = ScrapingMetrics()

        # Browser instance (lazy loaded)
        self._browser = None
        self._browser_context = None

        # Initialize Scraper Logger
        from datagod.scrapers.logger import ScraperLogger

        self.scraper_logger = ScraperLogger()
        self.current_run_id = 0
        self._run_start_time = None

        logger.info(f"Initialized {self.__class__.__name__} for {base_url}")

    def _create_session(self) -> requests.Session:
        """Create a session with retry configuration"""
        session = requests.Session()

        # Retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=[
                "HEAD",
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS",
                "TRACE",
            ],
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy, pool_connections=10, pool_maxsize=20
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(self.user_agents)

    def _get_cache_key(self, url: str, params: Dict = None) -> str:
        """Generate cache key for a request"""
        key_data = f"{url}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if not expired"""
        if not self.cache_enabled:
            return None

        cached = self._cache.get(cache_key)
        if cached:
            if datetime.utcnow() < cached["expires_at"]:
                logger.debug(f"Cache hit for {cache_key}")
                return cached["data"]
            else:
                del self._cache[cache_key]
        return None

    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]):
        """Save response to cache"""
        if self.cache_enabled:
            self._cache[cache_key] = {
                "data": data,
                "expires_at": datetime.utcnow() + timedelta(seconds=self.cache_ttl),
            }

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Dict = None,
        data: Dict = None,
        headers: Dict = None,
        use_browser: bool = False,
        wait_for_selector: str = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with all enhancements

        Args:
            url: URL to request
            method: HTTP method
            params: Query parameters
            data: POST data
            headers: Additional headers
            use_browser: Force browser rendering
            wait_for_selector: CSS selector to wait for (browser mode)

        Returns:
            Response dictionary with success, data, and metadata
        """
        # Check cache first
        cache_key = self._get_cache_key(url, params)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Rate limiting
        self.rate_limiter.wait()

        # Update metrics
        self.metrics.total_requests += 1
        if not self.metrics.start_time:
            self.metrics.start_time = datetime.utcnow()

        # Determine if we need browser
        should_use_browser = use_browser or (self.scraper_type == ScraperType.BROWSER)

        start_time = time.time()

        try:
            if should_use_browser:
                result = self._browser_request(url, wait_for_selector)
            else:
                result = self._http_request(url, method, params, data, headers)

            response_time = time.time() - start_time

            if result["success"]:
                self.metrics.successful_requests += 1
                if "content_length" in result:
                    self.metrics.bytes_downloaded += result["content_length"]

                # Update proxy stats
                if self.use_proxies and "proxy" in result:
                    self.proxy_rotator.mark_success(result["proxy"], response_time)

                # Cache successful response
                self._save_to_cache(cache_key, result)
            else:
                self.metrics.failed_requests += 1
                self.metrics.errors.append(
                    {
                        "url": url,
                        "error": result.get("error"),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

                # Update proxy stats
                if self.use_proxies and "proxy" in result:
                    self.proxy_rotator.mark_failure(result["proxy"])

            return result

        except Exception as e:
            self.metrics.failed_requests += 1
            self.metrics.errors.append(
                {
                    "url": url,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            logger.error(f"Request failed for {url}: {e}")
            return {"success": False, "error": str(e)}

    def _http_request(
        self,
        url: str,
        method: str,
        params: Dict = None,
        data: Dict = None,
        headers: Dict = None,
    ) -> Dict[str, Any]:
        """Make standard HTTP request"""
        request_headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }
        if headers:
            request_headers.update(headers)

        # Get proxy if enabled
        proxies = None
        proxy_config = None
        if self.use_proxies and self.proxy_rotator:
            proxy_config = self.proxy_rotator.get_next_proxy()
            if proxy_config:
                proxies = {"http": proxy_config.url, "https": proxy_config.url}

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                headers=request_headers,
                proxies=proxies,
                timeout=self.timeout,
                allow_redirects=True,
            )

            response.raise_for_status()

            # Try to parse JSON
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text

            return {
                "success": True,
                "data": response_data,
                "status_code": response.status_code,
                "content_length": len(response.content),
                "headers": dict(response.headers),
                "url": response.url,
                "proxy": proxy_config,
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": (
                    getattr(e.response, "status_code", None)
                    if hasattr(e, "response")
                    else None
                ),
                "proxy": proxy_config,
            }

    def _browser_request(
        self, url: str, wait_for_selector: str = None
    ) -> Dict[str, Any]:
        """Make request using Playwright browser"""
        try:
            # Lazy import playwright
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            )
            return {"success": False, "error": "Playwright not installed"}

        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ],
                )

                # Create context with random user agent
                context = browser.new_context(
                    user_agent=self._get_random_user_agent(),
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )

                # Set proxy if enabled
                if self.use_proxies and self.proxy_rotator:
                    proxy_config = self.proxy_rotator.get_next_proxy()
                    if proxy_config:
                        context = browser.new_context(
                            proxy={"server": proxy_config.url},
                            user_agent=self._get_random_user_agent(),
                        )

                page = context.new_page()

                # Navigate to URL
                response = page.goto(
                    url, wait_until="networkidle", timeout=self.timeout * 1000
                )

                # Wait for specific selector if provided
                if wait_for_selector:
                    page.wait_for_selector(wait_for_selector, timeout=10000)

                # Get page content
                content = page.content()

                browser.close()

                return {
                    "success": True,
                    "data": content,
                    "status_code": response.status if response else 200,
                    "content_length": len(content),
                    "url": page.url,
                    "rendered": True,
                }

        except Exception as e:
            logger.error(f"Browser request failed: {e}")
            return {"success": False, "error": str(e)}

    async def _async_browser_request(
        self, url: str, wait_for_selector: str = None
    ) -> Dict[str, Any]:
        """Async browser request for concurrent scraping"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {"success": False, "error": "Playwright not installed"}

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self._get_random_user_agent()
                )
                page = await context.new_page()

                response = await page.goto(
                    url, wait_until="networkidle", timeout=self.timeout * 1000
                )

                if wait_for_selector:
                    await page.wait_for_selector(wait_for_selector, timeout=10000)

                content = await page.content()
                await browser.close()

                return {
                    "success": True,
                    "data": content,
                    "status_code": response.status if response else 200,
                    "content_length": len(content),
                    "url": page.url,
                    "rendered": True,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def scrape_concurrent(
        self, urls: List[str], max_workers: int = None
    ) -> List[Dict[str, Any]]:
        """Scrape multiple URLs concurrently"""
        max_workers = max_workers or self.concurrent_requests
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self._make_request, url): url for url in urls
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    result["source_url"] = url
                    results.append(result)
                except Exception as e:
                    results.append(
                        {"success": False, "error": str(e), "source_url": url}
                    )

        return results

    def add_proxies(self, proxies: List[Dict[str, Any]]):
        """Add proxies to the rotator"""
        if not self.proxy_rotator:
            self.proxy_rotator = ProxyRotator()
            self.use_proxies = True

        self.proxy_rotator.add_proxies_from_list(proxies)

    @abstractmethod
    def scrape(self, **kwargs) -> List[Dict[str, Any]]:
        """Main scraping method - must be implemented by subclasses"""
        pass

    @abstractmethod
    def parse(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse response data - must be implemented by subclasses"""
        pass

    def get_metrics(self) -> Dict[str, Any]:
        """Get scraping metrics"""
        self.metrics.end_time = datetime.utcnow()
        metrics = self.metrics.to_dict()

        if self.use_proxies and self.proxy_rotator:
            metrics["proxy_stats"] = self.proxy_rotator.get_stats()

        return metrics

    def reset_metrics(self):
        """Reset scraping metrics"""
        self.metrics = ScrapingMetrics()

    def clear_cache(self):
        """Clear the response cache"""
        self._cache.clear()

    def start_run(self, jurisdiction_id: int = None):
        """Start a new scraper run logging session"""
        self._run_start_time = datetime.utcnow()
        # Use provided ID or fall back to instance attribute if it exists
        jid = jurisdiction_id
        if jid is None and hasattr(self, "jurisdiction_id"):
            jid = self.jurisdiction_id

        self.current_run_id = self.scraper_logger.log_run_start(
            scraper_name=self.__class__.__name__, jurisdiction_id=jid
        )
        return self.current_run_id

    def end_run(
        self, status: str = "success", items_scraped: int = 0, error_message: str = None
    ):
        """End the current scraper run logging session"""
        if self.current_run_id:
            self.scraper_logger.log_run_end(
                run_id=self.current_run_id,
                status=status,
                items_scraped=items_scraped,
                error_message=error_message,
            )
            self.current_run_id = 0
            self._run_start_time = None

    def export_results(
        self, data: List[Dict[str, Any]], filepath: str, format: str = "json"
    ):
        """Export scraping results to file"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        elif format == "jsonl":
            with open(path, "w") as f:
                for item in data:
                    f.write(json.dumps(item, default=str) + "\n")
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Exported {len(data)} records to {filepath}")


class JurisdictionScraper(EnhancedBaseScraper):
    """
    Base class for jurisdiction-specific scrapers
    Provides common functionality for scraping public records jurisdictions
    """

    def __init__(
        self, jurisdiction_id: int, jurisdiction_name: str, base_url: str, **kwargs
    ):
        super().__init__(base_url, **kwargs)
        self.jurisdiction_id = jurisdiction_id
        self.jurisdiction_name = jurisdiction_name

        # Data storage
        self.scraped_records: List[Dict[str, Any]] = []

    def _normalize_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a raw record to standard format"""
        return {
            "jurisdiction_id": self.jurisdiction_id,
            "jurisdiction_name": self.jurisdiction_name,
            "source_url": self.base_url,
            "scraped_at": datetime.utcnow().isoformat(),
            "raw_data": raw_record,
            # Override these in subclasses
            "record_type": raw_record.get("type", "unknown"),
            "record_id": raw_record.get("id"),
            "title": raw_record.get("title", ""),
            "date": raw_record.get("date"),
            "amount": raw_record.get("amount"),
            "parties": raw_record.get("parties", []),
            "description": raw_record.get("description", ""),
        }

    def scrape_all(
        self, start_page: int = 1, max_pages: int = None
    ) -> List[Dict[str, Any]]:
        """Scrape all pages of records"""
        all_records = []
        page = start_page

        while True:
            if max_pages and page > (start_page + max_pages - 1):
                break

            logger.info(f"Scraping page {page} for {self.jurisdiction_name}")

            records = self.scrape(page=page)

            if not records:
                break

            all_records.extend(records)
            page += 1

            # Respect rate limiting between pages
            time.sleep(1)

        self.scraped_records = all_records
        return all_records

    def save_to_database(self, db_manager) -> int:
        """Save scraped records to database"""
        saved_count = 0

        for record in self.scraped_records:
            try:
                db_manager.create_record(
                    jurisdiction_id=record["jurisdiction_id"],
                    title=record["title"],
                    data=record,
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save record: {e}")

        logger.info(f"Saved {saved_count} records to database")
        return saved_count
