"""
DataGod Base Scraper Module (Phase 1.3 - Hardened)

Provides a reliable, fault-tolerant base class for all scrapers with:
- Exponential backoff retry logic
- Source freshness tracking
- Hash-based change detection for deduplication
- Isolated failure handling (one scraper failure doesn't cascade)
- Comprehensive logging and metrics
"""

import requests
import time
import logging
import hashlib
import json
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from functools import wraps
import random

logger = logging.getLogger(__name__)


@dataclass
class ScraperMetrics:
    """Tracks scraper performance and health metrics."""
    requests_made: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retries_total: int = 0
    records_found: int = 0
    records_new: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    last_successful_scrape: Optional[datetime] = None
    content_hashes: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'requests_made': self.requests_made,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'retries_total': self.retries_total,
            'records_found': self.records_found,
            'records_new': self.records_new,
            'records_updated': self.records_updated,
            'records_unchanged': self.records_unchanged,
            'duration_seconds': (self.end_time - self.start_time).total_seconds() if self.end_time else None,
            'success_rate': self.successful_requests / max(self.requests_made, 1) * 100,
            'last_successful_scrape': self.last_successful_scrape.isoformat() if self.last_successful_scrape else None,
        }


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)
    retryable_exceptions: tuple = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ChunkedEncodingError,
    )


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class RetryableError(ScraperError):
    """Error that should trigger a retry."""
    pass


class NonRetryableError(ScraperError):
    """Error that should NOT trigger a retry."""
    pass


class BaseScraper(ABC):
    """
    Hardened base class for all scrapers.
    
    Features:
    - Exponential backoff retry logic with jitter
    - Source freshness tracking
    - Hash-based change detection for deduplication
    - Isolated failure handling
    - Comprehensive metrics and logging
    """
    
    def __init__(
        self, 
        base_url: str, 
        delay: float = 1.0, 
        timeout: int = 30,
        retry_config: Optional[RetryConfig] = None,
        source_id: Optional[str] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.delay = delay
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.source_id = source_id or self._generate_source_id()
        
        # Session setup
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DataGod-Scraper/2.0 (Hardened)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Metrics tracking
        self.metrics = ScraperMetrics()
        
        # Content hash cache for deduplication
        self._content_hashes: Dict[str, str] = {}
        
        # Circuit breaker state
        self._consecutive_failures = 0
        self._circuit_open_until: Optional[datetime] = None
        self._max_consecutive_failures = 5
    
    def _generate_source_id(self) -> str:
        """Generate a unique source ID based on base URL."""
        return hashlib.md5(self.base_url.encode()).hexdigest()[:12]
    
    # =========================================================================
    # RETRY LOGIC WITH EXPONENTIAL BACKOFF
    # =========================================================================
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay before next retry with exponential backoff and optional jitter."""
        delay = self.retry_config.initial_delay * (self.retry_config.exponential_base ** attempt)
        delay = min(delay, self.retry_config.max_delay)
        
        if self.retry_config.jitter:
            # Add ±25% jitter to prevent thundering herd
            jitter_factor = 0.75 + (random.random() * 0.5)
            delay *= jitter_factor
        
        return delay
    
    def _should_retry(self, exception: Exception, status_code: Optional[int]) -> bool:
        """Determine if a request should be retried."""
        # Check circuit breaker
        if self._circuit_open_until and datetime.utcnow() < self._circuit_open_until:
            logger.warning(f"Circuit breaker open until {self._circuit_open_until}")
            return False
        
        # Check for retryable exceptions
        if isinstance(exception, self.retry_config.retryable_exceptions):
            return True
        
        # Check for retryable status codes
        if status_code in self.retry_config.retryable_status_codes:
            return True
        
        return False
    
    def _with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with retry logic."""
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                # Reset failure counter on success
                self._consecutive_failures = 0
                self.metrics.successful_requests += 1
                self.metrics.last_successful_scrape = datetime.utcnow()
                
                return result
                
            except Exception as e:
                last_exception = e
                status_code = getattr(getattr(e, 'response', None), 'status_code', None)
                
                if attempt < self.retry_config.max_retries and self._should_retry(e, status_code):
                    delay = self._calculate_retry_delay(attempt)
                    self.metrics.retries_total += 1
                    
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.retry_config.max_retries + 1}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    # No more retries or non-retryable error
                    self.metrics.failed_requests += 1
                    self._consecutive_failures += 1
                    
                    # Trip circuit breaker if too many consecutive failures
                    if self._consecutive_failures >= self._max_consecutive_failures:
                        self._circuit_open_until = datetime.utcnow() + timedelta(minutes=5)
                        logger.error(
                            f"Circuit breaker tripped after {self._consecutive_failures} "
                            f"consecutive failures. Open until {self._circuit_open_until}"
                        )
                    
                    raise
        
        raise last_exception
    
    # =========================================================================
    # HASH-BASED CHANGE DETECTION
    # =========================================================================
    
    def compute_content_hash(self, content: Any) -> str:
        """Compute SHA-256 hash of content for change detection."""
        if isinstance(content, dict):
            # Normalize dict for consistent hashing
            content_str = json.dumps(content, sort_keys=True, default=str)
        elif isinstance(content, (list, tuple)):
            content_str = json.dumps(list(content), sort_keys=True, default=str)
        elif isinstance(content, bytes):
            return hashlib.sha256(content).hexdigest()
        else:
            content_str = str(content)
        
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def has_content_changed(self, key: str, content: Any) -> bool:
        """Check if content has changed since last scrape."""
        new_hash = self.compute_content_hash(content)
        old_hash = self._content_hashes.get(key)
        
        if old_hash is None:
            # First time seeing this content
            self._content_hashes[key] = new_hash
            return True
        
        if new_hash != old_hash:
            # Content has changed
            self._content_hashes[key] = new_hash
            return True
        
        # Content unchanged
        return False
    
    def get_record_hash(self, record: Dict[str, Any], key_fields: Optional[List[str]] = None) -> str:
        """
        Generate a unique hash for a record based on key fields.
        Used for deduplication across scrapes.
        """
        if key_fields:
            # Use only specified fields for hash
            key_data = {k: record.get(k) for k in key_fields if k in record}
        else:
            # Use all fields
            key_data = record
        
        return self.compute_content_hash(key_data)
    
    # =========================================================================
    # FRESHNESS TRACKING
    # =========================================================================
    
    def get_freshness_status(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Get freshness status of this source."""
        last_scrape = self.metrics.last_successful_scrape
        
        if not last_scrape:
            return {
                'status': 'never_scraped',
                'last_scrape': None,
                'age_hours': None,
                'is_stale': True
            }
        
        age = datetime.utcnow() - last_scrape
        age_hours = age.total_seconds() / 3600
        is_stale = age_hours > max_age_hours
        
        return {
            'status': 'stale' if is_stale else 'fresh',
            'last_scrape': last_scrape.isoformat(),
            'age_hours': round(age_hours, 2),
            'is_stale': is_stale
        }
    
    # =========================================================================
    # REQUEST METHODS
    # =========================================================================
    
    @abstractmethod
    def scrape(self, **kwargs) -> List[Dict[str, Any]]:
        """Main scraping method - must be implemented by subclasses."""
        pass
    
    def _make_request(
        self, 
        url: str, 
        method: str = 'GET', 
        retry: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling and optional retry."""
        self.metrics.requests_made += 1
        
        def do_request():
            time.sleep(self.delay)  # Respect rate limiting
            
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=self.timeout, **kwargs)
            elif method.upper() == 'POST':
                response = self.session.post(url, timeout=self.timeout, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            logger.info(f"Scraped {url} - Status: {response.status_code}")
            
            # Determine content type and parse accordingly
            content_type = response.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                data = response.json()
            else:
                data = response.text
            
            return {
                'success': True,
                'data': data,
                'status_code': response.status_code,
                'content_hash': self.compute_content_hash(data),
                'collected_at': datetime.utcnow().isoformat(),
                'url': url
            }
        
        try:
            if retry:
                return self._with_retry(do_request)
            else:
                result = do_request()
                self.metrics.successful_requests += 1
                return result
                
        except Exception as e:
            logger.error(f"Scraping request failed for {url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'status_code': getattr(getattr(e, 'response', None), 'status_code', None),
                'url': url,
                'collected_at': datetime.utcnow().isoformat()
            }
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract links from HTML content."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/'):
                href = f"{base_url}{href}"
            elif not href.startswith('http'):
                href = f"{base_url}/{href}"
            links.append(href)
        
        return links
    
    def _parse_json_data(self, data: Any) -> Dict[str, Any]:
        """Parse and validate JSON data."""
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON data")
                return {}
        return data
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate scraped data."""
        if not data:
            return False
        
        required_fields = ['source', 'scraped_at', 'data']
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        return True
    
    def save_data(self, data: List[Dict[str, Any]], filename: str) -> bool:
        """Save scraped data to file."""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Data saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to save data to {filename}: {str(e)}")
            return False
    
    def finalize(self) -> Dict[str, Any]:
        """Finalize scraping run and return metrics."""
        self.metrics.end_time = datetime.utcnow()
        return self.metrics.to_dict()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.session.close()
        self.finalize()
        return False  # Don't suppress exceptions
