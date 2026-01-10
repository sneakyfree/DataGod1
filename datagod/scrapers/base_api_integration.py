"""
Base API Integration Framework
This module provides the foundation for integrating with public records APIs
"""

import logging
import time
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib
import hmac
import base64

logger = logging.getLogger(__name__)

class RateLimitExceeded(Exception):
    """Raised when API rate limit is exceeded"""
    pass

class APIAuthenticationError(Exception):
    """Raised when API authentication fails"""
    pass

class APIDataError(Exception):
    """Raised when API returns invalid or unexpected data"""
    pass

class APIIntegrationMetrics:
    """Tracks metrics for API integration performance"""

    def __init__(self):
        self.requests_total = 0
        self.requests_successful = 0
        self.requests_failed = 0
        self.rate_limit_hits = 0
        self.average_response_time = 0.0
        self.total_response_time = 0.0
        self.last_request_time = None
        self.errors_by_type = {}

    def record_request(self, success: bool, response_time: float, error_type: str = None):
        """Record a request and its outcome"""
        self.requests_total += 1
        self.last_request_time = datetime.now()

        if success:
            self.requests_successful += 1
        else:
            self.requests_failed += 1
            if error_type:
                self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1

        # Update average response time
        self.total_response_time += response_time
        self.average_response_time = self.total_response_time / self.requests_total

    def record_rate_limit_hit(self):
        """Record a rate limit hit"""
        self.rate_limit_hits += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            "requests_total": self.requests_total,
            "requests_successful": self.requests_successful,
            "requests_failed": self.requests_failed,
            "success_rate": (self.requests_successful / self.requests_total * 100) if self.requests_total > 0 else 0,
            "rate_limit_hits": self.rate_limit_hits,
            "average_response_time": round(self.average_response_time, 3),
            "errors_by_type": self.errors_by_type,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None
        }

class BaseAPIIntegration(ABC):
    """Base class for API integrations with public records systems"""

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        self.jurisdiction_id = jurisdiction_id
        self.config = config
        self.metrics = APIIntegrationMetrics()

        # Rate limiting
        self.requests_per_minute = config.get('requests_per_minute', 60)
        self.requests_per_hour = config.get('requests_per_hour', 1000)
        self.request_timestamps = []

        # Authentication
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.access_token = None
        self.token_expires_at = None

        # Request configuration
        self.base_url = config.get('base_url', '')
        self.timeout = config.get('timeout', 30)
        self.retry_attempts = config.get('retry_attempts', 3)
        self.retry_backoff = config.get('retry_backoff', 1.0)

        # Initialize HTTP session with retry strategy
        self.session = self._create_session()

        logger.info(f"Initialized {self.__class__.__name__} for jurisdiction {jurisdiction_id}")

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.retry_attempts,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=self.retry_backoff,
            raise_on_status=False
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = datetime.now()

        # Clean old timestamps (older than 1 hour)
        cutoff_time = now - timedelta(hours=1)
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > cutoff_time]

        # Check hourly limit
        if len(self.request_timestamps) >= self.requests_per_hour:
            return False

        # Check per-minute limit (last 60 requests)
        recent_requests = [ts for ts in self.request_timestamps if ts > now - timedelta(minutes=1)]
        if len(recent_requests) >= self.requests_per_minute:
            return False

        return True

    def _record_request_timestamp(self):
        """Record a request timestamp for rate limiting"""
        self.request_timestamps.append(datetime.now())

        # Keep only last 1000 timestamps to prevent memory issues
        if len(self.request_timestamps) > 1000:
            self.request_timestamps = self.request_timestamps[-1000:]

    def _wait_for_rate_limit_reset(self):
        """Wait until rate limit resets"""
        if not self.request_timestamps:
            return

        now = datetime.now()

        # Check minute limit
        recent_minute = [ts for ts in self.request_timestamps if ts > now - timedelta(minutes=1)]
        if len(recent_minute) >= self.requests_per_minute:
            oldest_recent = min(recent_minute)
            wait_time = 60 - (now - oldest_recent).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
                return

        # Check hour limit
        if len(self.request_timestamps) >= self.requests_per_hour:
            oldest_hour = min(self.request_timestamps)
            wait_time = 3600 - (now - oldest_hour).total_seconds()
            if wait_time > 0:
                logger.info(f"Hourly rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the API"""
        pass

    @abstractmethod
    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """Search for records using API"""
        pass

    @abstractmethod
    def get_record_details(self, record_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific record"""
        pass

    @abstractmethod
    def map_api_data_to_standard_format(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map API-specific data format to standard DataGod format"""
        pass

    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an HTTP request with rate limiting and error handling"""
        # Check rate limits
        if not self._check_rate_limit():
            self._wait_for_rate_limit_reset()

        if not self._check_rate_limit():
            self.metrics.record_rate_limit_hit()
            raise RateLimitExceeded("Rate limit exceeded, even after waiting")

        # Ensure authentication
        if not self._ensure_authenticated():
            raise APIAuthenticationError("Failed to authenticate with API")

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        request_start = time.time()

        try:
            # Add authentication headers if needed
            headers = kwargs.get('headers', {})
            headers.update(self._get_auth_headers(method, endpoint, kwargs.get('data', {})))
            kwargs['headers'] = headers

            # Set timeout
            kwargs.setdefault('timeout', self.timeout)

            response = self.session.request(method, url, **kwargs)
            request_time = time.time() - request_start

            # Handle rate limiting
            if response.status_code == 429:
                self.metrics.record_rate_limit_hit()
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited, retrying after {retry_after} seconds")
                time.sleep(retry_after)
                return self.make_request(method, endpoint, **kwargs)

            # Handle authentication errors
            if response.status_code == 401:
                logger.warning("Authentication failed, re-authenticating")
                self.access_token = None
                if not self.authenticate():
                    raise APIAuthenticationError("Re-authentication failed")
                # Retry the request
                return self.make_request(method, endpoint, **kwargs)

            # Record successful request
            self._record_request_timestamp()
            self.metrics.record_request(response.status_code < 400, request_time)

            return response

        except requests.RequestException as e:
            request_time = time.time() - request_start
            self.metrics.record_request(False, request_time, "request_exception")
            logger.error(f"Request failed: {e}")
            raise

    def _ensure_authenticated(self) -> bool:
        """Ensure we have valid authentication"""
        if self.access_token and self.token_expires_at:
            # Check if token is still valid (with 5-minute buffer)
            if datetime.now() < self.token_expires_at - timedelta(minutes=5):
                return True

        # Need to authenticate
        return self.authenticate()

    def _get_auth_headers(self, method: str, endpoint: str, data: Any) -> Dict[str, str]:
        """Get authentication headers for request"""
        headers = {}

        if self.api_key:
            headers['X-API-Key'] = self.api_key

        if self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"

        return headers

    def validate_response(self, response: requests.Response) -> Dict[str, Any]:
        """Validate API response and extract data"""
        if response.status_code >= 400:
            error_msg = f"API request failed: {response.status_code} - {response.text}"
            self.metrics.record_request(False, 0, f"http_{response.status_code}")
            raise APIDataError(error_msg)

        try:
            return response.json()
        except json.JSONDecodeError:
            self.metrics.record_request(False, 0, "invalid_json")
            raise APIDataError(f"Invalid JSON response: {response.text}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get integration metrics"""
        metrics = self.metrics.get_metrics()
        metrics.update({
            "jurisdiction_id": self.jurisdiction_id,
            "api_name": self.__class__.__name__,
            "config": {k: v for k, v in self.config.items() if not k.endswith('_secret') and not k.endswith('_key')}
        })
        return metrics

class APIKeyAuthentication:
    """Mixin for API key authentication"""

    def authenticate(self) -> bool:
        """Authenticate using API key"""
        if not self.api_key:
            logger.error("API key not provided")
            return False

        # For API key authentication, we just validate the key format
        # Actual validation happens on first request
        logger.info("API key authentication configured")
        return True

class OAuth2Authentication:
    """Mixin for OAuth2 authentication"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_url = self.config.get('token_url')
        self.client_id = self.config.get('client_id')
        self.client_secret = self.config.get('client_secret')
        self.scope = self.config.get('scope', '')

    def authenticate(self) -> bool:
        """Authenticate using OAuth2"""
        if not all([self.token_url, self.client_id, self.client_secret]):
            logger.error("OAuth2 credentials not provided")
            return False

        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': self.scope
            }

            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            logger.info("OAuth2 authentication successful")
            return True

        except Exception as e:
            logger.error(f"OAuth2 authentication failed: {e}")
            return False

class HMACAuthentication:
    """Mixin for HMAC authentication"""

    def _get_auth_headers(self, method: str, endpoint: str, data: Any) -> Dict[str, str]:
        """Get HMAC authentication headers"""
        headers = super()._get_auth_headers(method, endpoint, data)

        if self.api_key and self.api_secret:
            timestamp = str(int(time.time()))
            message = f"{method.upper()}{endpoint}{timestamp}"

            if isinstance(data, dict):
                message += json.dumps(data, sort_keys=True)

            signature = hmac.new(
                self.api_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            headers.update({
                'X-API-Key': self.api_key,
                'X-Timestamp': timestamp,
                'X-Signature': signature
            })

        return headers
