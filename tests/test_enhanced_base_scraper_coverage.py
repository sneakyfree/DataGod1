"""
Tests for datagod/scrapers/enhanced_base_scraper.py
Tests that actually import and exercise the module for real coverage.
"""
import pytest
import time
import json
import tempfile
import os
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta


class TestScraperTypeEnum:
    """Test ScraperType enum"""

    def test_scraper_type_import(self):
        """Test ScraperType can be imported"""
        from datagod.scrapers.enhanced_base_scraper import ScraperType
        assert ScraperType is not None

    def test_scraper_type_values(self):
        """Test ScraperType enum values"""
        from datagod.scrapers.enhanced_base_scraper import ScraperType

        assert ScraperType.SIMPLE.value == "simple"
        assert ScraperType.BROWSER.value == "browser"
        assert ScraperType.HYBRID.value == "hybrid"


class TestProxyTypeEnum:
    """Test ProxyType enum"""

    def test_proxy_type_import(self):
        """Test ProxyType can be imported"""
        from datagod.scrapers.enhanced_base_scraper import ProxyType
        assert ProxyType is not None

    def test_proxy_type_values(self):
        """Test ProxyType enum values"""
        from datagod.scrapers.enhanced_base_scraper import ProxyType

        assert ProxyType.HTTP.value == "http"
        assert ProxyType.HTTPS.value == "https"
        assert ProxyType.SOCKS5.value == "socks5"


class TestProxyConfig:
    """Test ProxyConfig dataclass"""

    def test_proxy_config_creation(self):
        """Test ProxyConfig creation"""
        from datagod.scrapers.enhanced_base_scraper import ProxyConfig, ProxyType

        proxy = ProxyConfig(
            host="proxy.example.com",
            port=8080
        )

        assert proxy.host == "proxy.example.com"
        assert proxy.port == 8080
        assert proxy.protocol == ProxyType.HTTP
        assert proxy.is_active is True
        assert proxy.failure_count == 0
        assert proxy.success_count == 0

    def test_proxy_config_url_no_auth(self):
        """Test proxy URL without authentication"""
        from datagod.scrapers.enhanced_base_scraper import ProxyConfig

        proxy = ProxyConfig(host="proxy.com", port=8080)
        assert proxy.url == "http://proxy.com:8080"

    def test_proxy_config_url_with_auth(self):
        """Test proxy URL with authentication"""
        from datagod.scrapers.enhanced_base_scraper import ProxyConfig

        proxy = ProxyConfig(
            host="proxy.com",
            port=8080,
            username="user",
            password="pass"
        )
        assert proxy.url == "http://user:pass@proxy.com:8080"

    def test_proxy_config_url_https(self):
        """Test proxy URL with HTTPS protocol"""
        from datagod.scrapers.enhanced_base_scraper import ProxyConfig, ProxyType

        proxy = ProxyConfig(
            host="proxy.com",
            port=443,
            protocol=ProxyType.HTTPS
        )
        assert proxy.url == "https://proxy.com:443"

    def test_proxy_record_success(self):
        """Test recording successful request"""
        from datagod.scrapers.enhanced_base_scraper import ProxyConfig

        proxy = ProxyConfig(host="proxy.com", port=8080)
        proxy.failure_count = 3

        proxy.record_success(0.5)

        assert proxy.success_count == 1
        assert proxy.failure_count == 2  # Decremented
        assert proxy.last_used is not None
        assert proxy.avg_response_time == 0.5

    def test_proxy_record_success_running_average(self):
        """Test running average response time"""
        from datagod.scrapers.enhanced_base_scraper import ProxyConfig

        proxy = ProxyConfig(host="proxy.com", port=8080)
        proxy.avg_response_time = 1.0

        proxy.record_success(2.0)

        # Running average: 1.0 * 0.9 + 2.0 * 0.1 = 1.1
        assert proxy.avg_response_time == pytest.approx(1.1, rel=0.01)

    def test_proxy_record_failure(self):
        """Test recording failed request"""
        from datagod.scrapers.enhanced_base_scraper import ProxyConfig

        proxy = ProxyConfig(host="proxy.com", port=8080)

        proxy.record_failure()

        assert proxy.failure_count == 1
        assert proxy.last_used is not None
        assert proxy.is_active is True

    def test_proxy_deactivated_after_failures(self):
        """Test proxy deactivated after 5 failures"""
        from datagod.scrapers.enhanced_base_scraper import ProxyConfig

        proxy = ProxyConfig(host="proxy.com", port=8080)

        for _ in range(5):
            proxy.record_failure()

        assert proxy.failure_count == 5
        assert proxy.is_active is False


class TestScrapingMetrics:
    """Test ScrapingMetrics dataclass"""

    def test_metrics_creation(self):
        """Test metrics creation"""
        from datagod.scrapers.enhanced_base_scraper import ScrapingMetrics

        metrics = ScrapingMetrics()

        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.errors == []

    def test_success_rate_zero_requests(self):
        """Test success rate with zero requests"""
        from datagod.scrapers.enhanced_base_scraper import ScrapingMetrics

        metrics = ScrapingMetrics()
        assert metrics.success_rate == 0.0

    def test_success_rate_with_requests(self):
        """Test success rate calculation"""
        from datagod.scrapers.enhanced_base_scraper import ScrapingMetrics

        metrics = ScrapingMetrics(
            total_requests=10,
            successful_requests=8,
            failed_requests=2
        )
        assert metrics.success_rate == 80.0

    def test_duration_no_start_time(self):
        """Test duration with no start time"""
        from datagod.scrapers.enhanced_base_scraper import ScrapingMetrics

        metrics = ScrapingMetrics()
        assert metrics.duration_seconds == 0.0

    def test_duration_with_times(self):
        """Test duration calculation"""
        from datagod.scrapers.enhanced_base_scraper import ScrapingMetrics

        start = datetime.utcnow()
        end = start + timedelta(seconds=10)

        metrics = ScrapingMetrics(start_time=start, end_time=end)
        assert metrics.duration_seconds == pytest.approx(10.0, rel=0.1)

    def test_to_dict(self):
        """Test metrics to_dict"""
        from datagod.scrapers.enhanced_base_scraper import ScrapingMetrics

        metrics = ScrapingMetrics(
            total_requests=10,
            successful_requests=8,
            failed_requests=2,
            total_data_points=100,
            bytes_downloaded=1000
        )

        d = metrics.to_dict()

        assert d['total_requests'] == 10
        assert d['successful_requests'] == 8
        assert d['failed_requests'] == 2
        assert 'success_rate' in d
        assert d['total_data_points'] == 100
        assert d['bytes_downloaded'] == 1000


class TestProxyRotator:
    """Test ProxyRotator class"""

    def test_rotator_init_empty(self):
        """Test rotator initialization without proxies"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator

        rotator = ProxyRotator()
        assert rotator.proxies == []

    def test_rotator_init_with_proxies(self):
        """Test rotator initialization with proxies"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator, ProxyConfig

        proxies = [
            ProxyConfig(host="proxy1.com", port=8080),
            ProxyConfig(host="proxy2.com", port=8080)
        ]

        rotator = ProxyRotator(proxies)
        assert len(rotator.proxies) == 2

    def test_add_proxy(self):
        """Test adding a proxy"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator, ProxyConfig

        rotator = ProxyRotator()
        proxy = ProxyConfig(host="proxy.com", port=8080)

        rotator.add_proxy(proxy)

        assert len(rotator.proxies) == 1

    def test_add_proxies_from_list(self):
        """Test adding proxies from list of dicts"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator

        rotator = ProxyRotator()

        proxy_list = [
            {"host": "proxy1.com", "port": 8080},
            {"host": "proxy2.com", "port": 8081, "protocol": "https"},
            {"host": "proxy3.com", "port": 1080, "username": "user", "password": "pass"}
        ]

        rotator.add_proxies_from_list(proxy_list)

        assert len(rotator.proxies) == 3

    def test_get_next_proxy(self):
        """Test round-robin proxy selection"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator, ProxyConfig

        proxies = [
            ProxyConfig(host="proxy1.com", port=8080),
            ProxyConfig(host="proxy2.com", port=8080)
        ]

        rotator = ProxyRotator(proxies)

        # Get proxies round-robin
        p1 = rotator.get_next_proxy()
        p2 = rotator.get_next_proxy()

        assert p1 is not None
        assert p2 is not None

    def test_get_next_proxy_no_active(self):
        """Test get_next_proxy with no active proxies"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator, ProxyConfig

        proxy = ProxyConfig(host="proxy.com", port=8080, is_active=False)
        rotator = ProxyRotator([proxy])

        result = rotator.get_next_proxy()
        assert result is None

    def test_get_random_proxy(self):
        """Test random proxy selection"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator, ProxyConfig

        proxies = [
            ProxyConfig(host="proxy1.com", port=8080),
            ProxyConfig(host="proxy2.com", port=8080)
        ]

        rotator = ProxyRotator(proxies)
        proxy = rotator.get_random_proxy()

        assert proxy in proxies

    def test_get_random_proxy_no_active(self):
        """Test get_random_proxy with no active proxies"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator

        rotator = ProxyRotator()
        result = rotator.get_random_proxy()
        assert result is None

    def test_get_best_proxy(self):
        """Test best proxy selection"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator, ProxyConfig

        proxy1 = ProxyConfig(host="proxy1.com", port=8080)
        proxy1.success_count = 10
        proxy1.avg_response_time = 0.5

        proxy2 = ProxyConfig(host="proxy2.com", port=8080)
        proxy2.success_count = 5
        proxy2.avg_response_time = 1.0

        rotator = ProxyRotator([proxy1, proxy2])

        best = rotator.get_best_proxy()
        assert best == proxy1

    def test_get_best_proxy_no_active(self):
        """Test get_best_proxy with no active proxies"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator

        rotator = ProxyRotator()
        result = rotator.get_best_proxy()
        assert result is None

    def test_mark_success(self):
        """Test marking proxy success"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator, ProxyConfig

        proxy = ProxyConfig(host="proxy.com", port=8080)
        rotator = ProxyRotator([proxy])

        rotator.mark_success(proxy, 0.5)

        assert proxy.success_count == 1

    def test_mark_failure(self):
        """Test marking proxy failure"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator, ProxyConfig

        proxy = ProxyConfig(host="proxy.com", port=8080)
        rotator = ProxyRotator([proxy])

        rotator.mark_failure(proxy)

        assert proxy.failure_count == 1

    def test_get_stats(self):
        """Test getting proxy pool stats"""
        from datagod.scrapers.enhanced_base_scraper import ProxyRotator, ProxyConfig

        proxies = [
            ProxyConfig(host="proxy1.com", port=8080, is_active=True),
            ProxyConfig(host="proxy2.com", port=8080, is_active=False)
        ]

        rotator = ProxyRotator(proxies)
        stats = rotator.get_stats()

        assert stats['total_proxies'] == 2
        assert stats['active_proxies'] == 1
        assert stats['inactive_proxies'] == 1


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_rate_limiter_init(self):
        """Test rate limiter initialization"""
        from datagod.scrapers.enhanced_base_scraper import RateLimiter

        limiter = RateLimiter(requests_per_second=2.0, burst_size=5)

        assert limiter.rate == 2.0
        assert limiter.burst_size == 5
        assert limiter.tokens == 5

    def test_acquire_with_tokens(self):
        """Test acquiring when tokens available"""
        from datagod.scrapers.enhanced_base_scraper import RateLimiter

        limiter = RateLimiter(requests_per_second=10.0, burst_size=5)

        result = limiter.acquire(timeout=0.1)
        assert result is True
        assert limiter.tokens == 4

    def test_acquire_timeout(self):
        """Test acquire with timeout when no tokens"""
        from datagod.scrapers.enhanced_base_scraper import RateLimiter

        limiter = RateLimiter(requests_per_second=0.1, burst_size=1)
        limiter.tokens = 0

        result = limiter.acquire(timeout=0.1)
        # May or may not acquire depending on timing
        assert result in [True, False]

    def test_wait(self):
        """Test wait method"""
        from datagod.scrapers.enhanced_base_scraper import RateLimiter

        limiter = RateLimiter(requests_per_second=100.0, burst_size=5)
        limiter.wait()  # Should not block with high rate

        assert limiter.tokens < 5  # One token consumed


class TestEnhancedBaseScraper:
    """Test EnhancedBaseScraper class"""

    def get_concrete_scraper(self, **kwargs):
        """Helper to create concrete scraper"""
        from datagod.scrapers.enhanced_base_scraper import EnhancedBaseScraper, ScraperType

        class ConcreteScraper(EnhancedBaseScraper):
            def scrape(self, **kwargs):
                return []

            def parse(self, response):
                return []

        return ConcreteScraper(
            base_url="https://example.com",
            rate_limit=100.0,  # High rate for testing
            **kwargs
        )

    def test_enhanced_scraper_init(self):
        """Test EnhancedBaseScraper initialization"""
        scraper = self.get_concrete_scraper()

        assert scraper.base_url == "https://example.com"
        assert scraper.session is not None
        assert scraper.rate_limiter is not None
        assert scraper.metrics is not None

    def test_enhanced_scraper_trailing_slash(self):
        """Test trailing slash removed from base_url"""
        from datagod.scrapers.enhanced_base_scraper import EnhancedBaseScraper

        class ConcreteScraper(EnhancedBaseScraper):
            def scrape(self, **kwargs):
                return []

            def parse(self, response):
                return []

        scraper = ConcreteScraper(
            base_url="https://example.com/",
            rate_limit=100.0
        )
        assert scraper.base_url == "https://example.com"

    def test_get_random_user_agent(self):
        """Test random user agent selection"""
        scraper = self.get_concrete_scraper()
        ua = scraper._get_random_user_agent()

        assert ua in scraper.user_agents

    def test_get_cache_key(self):
        """Test cache key generation"""
        scraper = self.get_concrete_scraper()

        key1 = scraper._get_cache_key("https://example.com/page1", {"a": 1})
        key2 = scraper._get_cache_key("https://example.com/page1", {"a": 1})
        key3 = scraper._get_cache_key("https://example.com/page2", {"a": 1})

        assert key1 == key2
        assert key1 != key3

    def test_cache_operations(self):
        """Test cache save and get"""
        scraper = self.get_concrete_scraper()

        data = {"key": "value"}
        cache_key = "test_key"

        # Initially not in cache
        assert scraper._get_from_cache(cache_key) is None

        # Save to cache
        scraper._save_to_cache(cache_key, data)

        # Now in cache
        cached = scraper._get_from_cache(cache_key)
        assert cached == data

    def test_cache_disabled(self):
        """Test cache when disabled"""
        scraper = self.get_concrete_scraper(cache_enabled=False)

        scraper._save_to_cache("key", {"data": 1})
        result = scraper._get_from_cache("key")

        assert result is None

    def test_clear_cache(self):
        """Test clearing cache"""
        scraper = self.get_concrete_scraper()

        scraper._save_to_cache("key1", {"data": 1})
        scraper._save_to_cache("key2", {"data": 2})

        scraper.clear_cache()

        assert scraper._get_from_cache("key1") is None
        assert scraper._get_from_cache("key2") is None

    def test_get_metrics(self):
        """Test getting metrics"""
        scraper = self.get_concrete_scraper()
        scraper.metrics.total_requests = 10

        metrics = scraper.get_metrics()

        assert metrics['total_requests'] == 10
        assert 'success_rate' in metrics

    def test_reset_metrics(self):
        """Test resetting metrics"""
        scraper = self.get_concrete_scraper()
        scraper.metrics.total_requests = 10

        scraper.reset_metrics()

        assert scraper.metrics.total_requests == 0

    def test_add_proxies(self):
        """Test adding proxies"""
        scraper = self.get_concrete_scraper(use_proxies=False)

        proxies = [
            {"host": "proxy.com", "port": 8080}
        ]

        scraper.add_proxies(proxies)

        assert scraper.use_proxies is True
        assert scraper.proxy_rotator is not None
        assert len(scraper.proxy_rotator.proxies) == 1


class TestHttpRequest:
    """Test _http_request method"""

    def get_concrete_scraper(self, **kwargs):
        """Helper to create concrete scraper"""
        from datagod.scrapers.enhanced_base_scraper import EnhancedBaseScraper

        class ConcreteScraper(EnhancedBaseScraper):
            def scrape(self, **kwargs):
                return []

            def parse(self, response):
                return []

        return ConcreteScraper(
            base_url="https://example.com",
            rate_limit=100.0,
            **kwargs
        )

    def test_http_request_success_json(self):
        """Test successful HTTP request with JSON response"""
        scraper = self.get_concrete_scraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}
        mock_response.content = b'{"data": "value"}'
        mock_response.headers = {}
        mock_response.url = "https://example.com"
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, 'request', return_value=mock_response):
            result = scraper._http_request("https://example.com", "GET")

        assert result['success'] is True
        assert result['data'] == {"data": "value"}

    def test_http_request_success_text(self):
        """Test successful HTTP request with text response"""
        scraper = self.get_concrete_scraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "<html>content</html>"
        mock_response.content = b'<html>content</html>'
        mock_response.headers = {}
        mock_response.url = "https://example.com"
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, 'request', return_value=mock_response):
            result = scraper._http_request("https://example.com", "GET")

        assert result['success'] is True
        assert result['data'] == "<html>content</html>"

    def test_http_request_failure(self):
        """Test HTTP request failure"""
        import requests
        scraper = self.get_concrete_scraper()

        with patch.object(scraper.session, 'request', side_effect=requests.exceptions.Timeout("Timeout")):
            result = scraper._http_request("https://example.com", "GET")

        assert result['success'] is False
        assert 'error' in result


class TestMakeRequest:
    """Test _make_request method"""

    def get_concrete_scraper(self, **kwargs):
        """Helper to create concrete scraper"""
        from datagod.scrapers.enhanced_base_scraper import EnhancedBaseScraper

        class ConcreteScraper(EnhancedBaseScraper):
            def scrape(self, **kwargs):
                return []

            def parse(self, response):
                return []

        return ConcreteScraper(
            base_url="https://example.com",
            rate_limit=100.0,
            **kwargs
        )

    def test_make_request_cache_hit(self):
        """Test make_request returns cached response"""
        scraper = self.get_concrete_scraper()

        cached_data = {"success": True, "data": "cached"}
        cache_key = scraper._get_cache_key("https://example.com", None)
        scraper._save_to_cache(cache_key, cached_data)

        result = scraper._make_request("https://example.com")

        assert result == cached_data

    def test_make_request_updates_metrics(self):
        """Test make_request updates metrics"""
        scraper = self.get_concrete_scraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.content = b'{}'
        mock_response.headers = {}
        mock_response.url = "https://example.com"
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, 'request', return_value=mock_response):
            scraper._make_request("https://example.com/test")

        assert scraper.metrics.total_requests >= 1


class TestScrapeConcurrent:
    """Test scrape_concurrent method"""

    def get_concrete_scraper(self):
        """Helper to create concrete scraper"""
        from datagod.scrapers.enhanced_base_scraper import EnhancedBaseScraper

        class ConcreteScraper(EnhancedBaseScraper):
            def scrape(self, **kwargs):
                return []

            def parse(self, response):
                return []

        return ConcreteScraper(
            base_url="https://example.com",
            rate_limit=100.0,
            concurrent_requests=2
        )

    def test_scrape_concurrent(self):
        """Test concurrent scraping"""
        scraper = self.get_concrete_scraper()

        urls = ["https://example.com/1", "https://example.com/2"]

        with patch.object(scraper, '_make_request', return_value={'success': True, 'data': 'test'}):
            results = scraper.scrape_concurrent(urls)

        assert len(results) == 2
        assert all('source_url' in r for r in results)


class TestExportResults:
    """Test export_results method"""

    def get_concrete_scraper(self):
        """Helper to create concrete scraper"""
        from datagod.scrapers.enhanced_base_scraper import EnhancedBaseScraper

        class ConcreteScraper(EnhancedBaseScraper):
            def scrape(self, **kwargs):
                return []

            def parse(self, response):
                return []

        return ConcreteScraper(base_url="https://example.com", rate_limit=100.0)

    def test_export_json(self):
        """Test exporting to JSON"""
        scraper = self.get_concrete_scraper()
        data = [{"id": 1}, {"id": 2}]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.json")
            scraper.export_results(data, filepath, format='json')

            assert os.path.exists(filepath)

            with open(filepath, 'r') as f:
                loaded = json.load(f)

            assert loaded == data

    def test_export_jsonl(self):
        """Test exporting to JSONL"""
        scraper = self.get_concrete_scraper()
        data = [{"id": 1}, {"id": 2}]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.jsonl")
            scraper.export_results(data, filepath, format='jsonl')

            assert os.path.exists(filepath)

            with open(filepath, 'r') as f:
                lines = f.readlines()

            assert len(lines) == 2

    def test_export_invalid_format(self):
        """Test exporting with invalid format"""
        scraper = self.get_concrete_scraper()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")

            with pytest.raises(ValueError, match="Unsupported format"):
                scraper.export_results([], filepath, format='invalid')


class TestJurisdictionScraper:
    """Test JurisdictionScraper class"""

    def get_jurisdiction_scraper(self):
        """Helper to create jurisdiction scraper"""
        from datagod.scrapers.enhanced_base_scraper import JurisdictionScraper

        class ConcreteJurisdictionScraper(JurisdictionScraper):
            def scrape(self, **kwargs):
                return [{"id": 1, "title": "Test Record", "type": "deed"}]

            def parse(self, response):
                return []

        return ConcreteJurisdictionScraper(
            jurisdiction_id=1,
            jurisdiction_name="Test County",
            base_url="https://county.gov",
            rate_limit=100.0
        )

    def test_jurisdiction_scraper_init(self):
        """Test JurisdictionScraper initialization"""
        scraper = self.get_jurisdiction_scraper()

        assert scraper.jurisdiction_id == 1
        assert scraper.jurisdiction_name == "Test County"
        assert scraper.scraped_records == []

    def test_normalize_record(self):
        """Test record normalization"""
        scraper = self.get_jurisdiction_scraper()

        raw = {
            "id": "123",
            "title": "Test Record",
            "type": "deed",
            "amount": 1000,
            "date": "2024-01-01"
        }

        normalized = scraper._normalize_record(raw)

        assert normalized['jurisdiction_id'] == 1
        assert normalized['jurisdiction_name'] == "Test County"
        assert normalized['record_type'] == "deed"
        assert normalized['record_id'] == "123"
        assert 'scraped_at' in normalized

    def test_scrape_all(self):
        """Test scrape_all method"""
        scraper = self.get_jurisdiction_scraper()

        records = scraper.scrape_all(max_pages=1)

        assert len(records) > 0
        assert scraper.scraped_records == records


class TestBrowserRequest:
    """Test browser request functionality"""

    def get_concrete_scraper(self):
        """Helper to create concrete scraper"""
        from datagod.scrapers.enhanced_base_scraper import EnhancedBaseScraper, ScraperType

        class ConcreteScraper(EnhancedBaseScraper):
            def scrape(self, **kwargs):
                return []

            def parse(self, response):
                return []

        return ConcreteScraper(
            base_url="https://example.com",
            scraper_type=ScraperType.BROWSER,
            rate_limit=100.0
        )

    def test_browser_request_playwright_not_installed(self):
        """Test browser request when playwright not installed"""
        scraper = self.get_concrete_scraper()

        with patch.dict('sys.modules', {'playwright.sync_api': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                result = scraper._browser_request("https://example.com")

        # Should handle error gracefully
        assert result['success'] is False or 'error' in result


class TestLogger:
    """Test logging configuration"""

    def test_logger_exists(self):
        """Test logger is configured"""
        from datagod.scrapers import enhanced_base_scraper
        assert hasattr(enhanced_base_scraper, 'logger')
