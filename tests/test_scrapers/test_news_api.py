"""
Tests for datagod/scrapers/categories/news_api.py

Comprehensive tests for the news API module including enums,
dataclasses, scrapers, and convenience functions.
"""

from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest


class TestNewsCategoryEnum:
    """Tests for NewsCategory enum"""

    def test_news_category_exists(self):
        """Test that NewsCategory enum exists"""
        from datagod.scrapers.categories.news_api import NewsCategory

        assert NewsCategory is not None

    def test_business_category(self):
        """Test BUSINESS category"""
        from datagod.scrapers.categories.news_api import NewsCategory

        assert NewsCategory.BUSINESS.value == "business"

    def test_technology_category(self):
        """Test TECHNOLOGY category"""
        from datagod.scrapers.categories.news_api import NewsCategory

        assert NewsCategory.TECHNOLOGY.value == "technology"

    def test_real_estate_category(self):
        """Test REAL_ESTATE category"""
        from datagod.scrapers.categories.news_api import NewsCategory

        assert NewsCategory.REAL_ESTATE.value == "real_estate"

    def test_legal_category(self):
        """Test LEGAL category"""
        from datagod.scrapers.categories.news_api import NewsCategory

        assert NewsCategory.LEGAL.value == "legal"

    def test_all_categories_defined(self):
        """Test all expected categories are defined"""
        from datagod.scrapers.categories.news_api import NewsCategory

        expected = [
            "BUSINESS",
            "TECHNOLOGY",
            "POLITICS",
            "REAL_ESTATE",
            "LEGAL",
            "FINANCE",
            "LOCAL",
            "CRIME",
            "GOVERNMENT",
            "GENERAL",
            "UNKNOWN",
        ]
        for cat in expected:
            assert hasattr(NewsCategory, cat)


class TestNewsSentimentEnum:
    """Tests for NewsSentiment enum"""

    def test_news_sentiment_exists(self):
        """Test that NewsSentiment enum exists"""
        from datagod.scrapers.categories.news_api import NewsSentiment

        assert NewsSentiment is not None

    def test_all_sentiments_defined(self):
        """Test all expected sentiments are defined"""
        from datagod.scrapers.categories.news_api import NewsSentiment

        expected = ["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED", "UNKNOWN"]
        for sent in expected:
            assert hasattr(NewsSentiment, sent)


class TestNewsSourceTypeEnum:
    """Tests for NewsSourceType enum"""

    def test_news_source_type_exists(self):
        """Test that NewsSourceType enum exists"""
        from datagod.scrapers.categories.news_api import NewsSourceType

        assert NewsSourceType is not None

    def test_major_outlet(self):
        """Test MAJOR_OUTLET type"""
        from datagod.scrapers.categories.news_api import NewsSourceType

        assert NewsSourceType.MAJOR_OUTLET.value == "major_outlet"

    def test_all_source_types_defined(self):
        """Test all expected source types are defined"""
        from datagod.scrapers.categories.news_api import NewsSourceType

        expected = [
            "MAJOR_OUTLET",
            "LOCAL_NEWS",
            "WIRE_SERVICE",
            "PRESS_RELEASE",
            "BLOG",
            "TRADE_PUBLICATION",
            "GOVERNMENT",
            "UNKNOWN",
        ]
        for st in expected:
            assert hasattr(NewsSourceType, st)


class TestNewsSource:
    """Tests for NewsSource dataclass"""

    def test_news_source_exists(self):
        """Test that NewsSource dataclass exists"""
        from datagod.scrapers.categories.news_api import NewsSource

        assert NewsSource is not None

    def test_create_news_source(self):
        """Test creating a NewsSource"""
        from datagod.scrapers.categories.news_api import NewsSource, NewsSourceType

        source = NewsSource(source_id="test123", name="Test News")
        assert source.source_id == "test123"
        assert source.name == "Test News"

    def test_news_source_defaults(self):
        """Test NewsSource default values"""
        from datagod.scrapers.categories.news_api import NewsSource, NewsSourceType

        source = NewsSource(source_id="test", name="Test")
        assert source.source_type == NewsSourceType.UNKNOWN
        assert source.language == "en"
        assert source.categories == []

    def test_news_source_to_dict(self):
        """Test NewsSource to_dict method"""
        from datagod.scrapers.categories.news_api import (
            NewsCategory,
            NewsSource,
            NewsSourceType,
        )

        source = NewsSource(
            source_id="test123",
            name="Test News",
            source_type=NewsSourceType.MAJOR_OUTLET,
            url="https://example.com",
            categories=[NewsCategory.BUSINESS],
        )
        result = source.to_dict()
        assert result["source_id"] == "test123"
        assert result["name"] == "Test News"
        assert result["source_type"] == "major_outlet"
        assert "business" in result["categories"]


class TestNewsArticle:
    """Tests for NewsArticle dataclass"""

    def test_news_article_exists(self):
        """Test that NewsArticle dataclass exists"""
        from datagod.scrapers.categories.news_api import NewsArticle

        assert NewsArticle is not None

    def test_create_news_article(self):
        """Test creating a NewsArticle"""
        from datagod.scrapers.categories.news_api import NewsArticle, NewsSource

        source = NewsSource(source_id="src", name="Source")
        article = NewsArticle(
            article_id="art123",
            title="Test Article",
            source=source,
            published_at=datetime.now(),
        )
        assert article.article_id == "art123"
        assert article.title == "Test Article"

    def test_news_article_to_dict(self):
        """Test NewsArticle to_dict method"""
        from datagod.scrapers.categories.news_api import NewsArticle, NewsSource

        source = NewsSource(source_id="src", name="Source")
        article = NewsArticle(
            article_id="art123",
            title="Test Article",
            source=source,
            published_at=datetime.now(),
        )
        result = article.to_dict()
        assert result["article_id"] == "art123"
        assert result["title"] == "Test Article"
        assert "source" in result


class TestPressRelease:
    """Tests for PressRelease dataclass"""

    def test_press_release_exists(self):
        """Test that PressRelease dataclass exists"""
        from datagod.scrapers.categories.news_api import PressRelease

        assert PressRelease is not None

    def test_create_press_release(self):
        """Test creating a PressRelease"""
        from datagod.scrapers.categories.news_api import PressRelease

        release = PressRelease(
            release_id="rel123",
            headline="Test Headline",
            source_company="Test Corp",
            published_at=datetime.now(),
        )
        assert release.release_id == "rel123"
        assert release.headline == "Test Headline"
        assert release.source_company == "Test Corp"

    def test_press_release_to_dict(self):
        """Test PressRelease to_dict method"""
        from datagod.scrapers.categories.news_api import PressRelease

        release = PressRelease(
            release_id="rel123",
            headline="Test Headline",
            source_company="Test Corp",
            published_at=datetime.now(),
        )
        result = release.to_dict()
        assert result["release_id"] == "rel123"
        assert result["headline"] == "Test Headline"


class TestNewsSearch:
    """Tests for NewsSearch dataclass"""

    def test_news_search_exists(self):
        """Test that NewsSearch dataclass exists"""
        from datagod.scrapers.categories.news_api import NewsSearch

        assert NewsSearch is not None

    def test_create_news_search(self):
        """Test creating a NewsSearch"""
        from datagod.scrapers.categories.news_api import NewsSearch

        search = NewsSearch(keywords="test query")
        assert search.keywords == "test query"

    def test_news_search_defaults(self):
        """Test NewsSearch default values"""
        from datagod.scrapers.categories.news_api import NewsSearch

        search = NewsSearch()
        assert search.language == "en"
        assert search.page_size == 20
        assert search.page == 1
        assert search.sort_by == "publishedAt"


class TestEntityNewsSearch:
    """Tests for EntityNewsSearch dataclass"""

    def test_entity_news_search_exists(self):
        """Test that EntityNewsSearch dataclass exists"""
        from datagod.scrapers.categories.news_api import EntityNewsSearch

        assert EntityNewsSearch is not None

    def test_create_entity_news_search(self):
        """Test creating an EntityNewsSearch"""
        from datagod.scrapers.categories.news_api import EntityNewsSearch

        search = EntityNewsSearch(entity_name="John Doe", entity_type="person")
        assert search.entity_name == "John Doe"
        assert search.entity_type == "person"


class TestNewsAPIScraper:
    """Tests for NewsAPIScraper abstract class"""

    def test_news_api_scraper_exists(self):
        """Test that NewsAPIScraper class exists"""
        from datagod.scrapers.categories.news_api import NewsAPIScraper

        assert NewsAPIScraper is not None

    def test_news_api_scraper_is_abstract(self):
        """Test that NewsAPIScraper is abstract"""
        from abc import ABC

        from datagod.scrapers.categories.news_api import NewsAPIScraper

        assert issubclass(NewsAPIScraper, ABC)

    def test_news_api_scraper_base_url(self):
        """Test NewsAPIScraper BASE_URL"""
        from datagod.scrapers.categories.news_api import NewsAPIScraper

        assert NewsAPIScraper.BASE_URL == "https://newsapi.org/v2"

    def test_classify_category_business(self):
        """Test classify_category for business text"""
        from datagod.scrapers.categories.news_api import NewsAPIScraper, NewsCategory

        class ConcreteScraper(NewsAPIScraper):
            def search_articles(self, search):
                return []

            def get_top_headlines(
                self, country="us", category=None, sources=None, keywords=None
            ):
                return []

            def get_sources(self, category=None, country=None, language="en"):
                return []

        scraper = ConcreteScraper(api_key="test")
        result = scraper.classify_category("The company reported strong earnings")
        assert result == NewsCategory.BUSINESS

    def test_classify_category_real_estate(self):
        """Test classify_category for real estate text"""
        from datagod.scrapers.categories.news_api import NewsAPIScraper, NewsCategory

        class ConcreteScraper(NewsAPIScraper):
            def search_articles(self, search):
                return []

            def get_top_headlines(
                self, country="us", category=None, sources=None, keywords=None
            ):
                return []

            def get_sources(self, category=None, country=None, language="en"):
                return []

        scraper = ConcreteScraper(api_key="test")
        result = scraper.classify_category("New housing development announced")
        assert result == NewsCategory.REAL_ESTATE

    def test_classify_category_unknown(self):
        """Test classify_category returns GENERAL for unknown text"""
        from datagod.scrapers.categories.news_api import NewsAPIScraper, NewsCategory

        class ConcreteScraper(NewsAPIScraper):
            def search_articles(self, search):
                return []

            def get_top_headlines(
                self, country="us", category=None, sources=None, keywords=None
            ):
                return []

            def get_sources(self, category=None, country=None, language="en"):
                return []

        scraper = ConcreteScraper(api_key="test")
        result = scraper.classify_category("Random unrelated text here")
        assert result == NewsCategory.GENERAL


class TestGoogleNewsScraper:
    """Tests for GoogleNewsScraper abstract class"""

    def test_google_news_scraper_exists(self):
        """Test that GoogleNewsScraper class exists"""
        from datagod.scrapers.categories.news_api import GoogleNewsScraper

        assert GoogleNewsScraper is not None

    def test_google_news_scraper_is_abstract(self):
        """Test that GoogleNewsScraper is abstract"""
        from abc import ABC

        from datagod.scrapers.categories.news_api import GoogleNewsScraper

        assert issubclass(GoogleNewsScraper, ABC)

    def test_google_news_scraper_base_url(self):
        """Test GoogleNewsScraper RSS_BASE_URL"""
        from datagod.scrapers.categories.news_api import GoogleNewsScraper

        assert GoogleNewsScraper.RSS_BASE_URL == "https://news.google.com/rss"


class TestLocalNewsAggregator:
    """Tests for LocalNewsAggregator abstract class"""

    def test_local_news_aggregator_exists(self):
        """Test that LocalNewsAggregator class exists"""
        from datagod.scrapers.categories.news_api import LocalNewsAggregator

        assert LocalNewsAggregator is not None

    def test_local_news_aggregator_is_abstract(self):
        """Test that LocalNewsAggregator is abstract"""
        from abc import ABC

        from datagod.scrapers.categories.news_api import LocalNewsAggregator

        assert issubclass(LocalNewsAggregator, ABC)

    def test_state_sources_defined(self):
        """Test STATE_SOURCES is defined"""
        from datagod.scrapers.categories.news_api import LocalNewsAggregator

        assert hasattr(LocalNewsAggregator, "STATE_SOURCES")
        assert "CA" in LocalNewsAggregator.STATE_SOURCES
        assert "TX" in LocalNewsAggregator.STATE_SOURCES

    def test_get_source_state(self):
        """Test get_source_state method"""
        from datagod.scrapers.categories.news_api import LocalNewsAggregator

        class ConcreteAggregator(LocalNewsAggregator):
            def search_local_news(
                self, keywords, state, city=None, date_from=None, date_to=None
            ):
                return []

            def get_state_sources(self, state):
                return []

            def get_city_news(self, city, state):
                return []

        aggregator = ConcreteAggregator()
        result = aggregator.get_source_state("https://www.latimes.com/article")
        assert result == "CA"

    def test_get_source_state_unknown(self):
        """Test get_source_state returns None for unknown source"""
        from datagod.scrapers.categories.news_api import LocalNewsAggregator

        class ConcreteAggregator(LocalNewsAggregator):
            def search_local_news(
                self, keywords, state, city=None, date_from=None, date_to=None
            ):
                return []

            def get_state_sources(self, state):
                return []

            def get_city_news(self, city, state):
                return []

        aggregator = ConcreteAggregator()
        result = aggregator.get_source_state("https://unknown-news.com/article")
        assert result is None


class TestPressReleaseAggregator:
    """Tests for PressReleaseAggregator abstract class"""

    def test_press_release_aggregator_exists(self):
        """Test that PressReleaseAggregator class exists"""
        from datagod.scrapers.categories.news_api import PressReleaseAggregator

        assert PressReleaseAggregator is not None

    def test_press_release_aggregator_is_abstract(self):
        """Test that PressReleaseAggregator is abstract"""
        from abc import ABC

        from datagod.scrapers.categories.news_api import PressReleaseAggregator

        assert issubclass(PressReleaseAggregator, ABC)

    def test_wire_services_defined(self):
        """Test WIRE_SERVICES is defined"""
        from datagod.scrapers.categories.news_api import PressReleaseAggregator

        assert hasattr(PressReleaseAggregator, "WIRE_SERVICES")
        assert "prnewswire.com" in PressReleaseAggregator.WIRE_SERVICES


class TestEntityNewsFinder:
    """Tests for EntityNewsFinder class"""

    def test_entity_news_finder_exists(self):
        """Test that EntityNewsFinder class exists"""
        from datagod.scrapers.categories.news_api import EntityNewsFinder

        assert EntityNewsFinder is not None

    def test_create_entity_news_finder(self):
        """Test creating an EntityNewsFinder"""
        from datagod.scrapers.categories.news_api import EntityNewsFinder

        finder = EntityNewsFinder()
        assert finder is not None

    def test_create_entity_news_finder_with_api_key(self):
        """Test creating an EntityNewsFinder with API key"""
        from datagod.scrapers.categories.news_api import EntityNewsFinder

        finder = EntityNewsFinder(newsapi_key="test123")
        assert finder.newsapi_key == "test123"

    def test_search_person_news_returns_list(self):
        """Test search_person_news returns a list"""
        from datagod.scrapers.categories.news_api import EntityNewsFinder

        finder = EntityNewsFinder()
        result = finder.search_person_news("John Doe")
        assert isinstance(result, list)

    def test_search_company_news_returns_list(self):
        """Test search_company_news returns a list"""
        from datagod.scrapers.categories.news_api import EntityNewsFinder

        finder = EntityNewsFinder()
        result = finder.search_company_news("Test Corp")
        assert isinstance(result, list)

    def test_search_property_news_returns_list(self):
        """Test search_property_news returns a list"""
        from datagod.scrapers.categories.news_api import EntityNewsFinder

        finder = EntityNewsFinder()
        result = finder.search_property_news("123 Main St")
        assert isinstance(result, list)


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_search_news_exists(self):
        """Test that search_news function exists"""
        from datagod.scrapers.categories.news_api import search_news

        assert callable(search_news)

    def test_search_news_returns_list(self):
        """Test search_news returns a list"""
        from datagod.scrapers.categories.news_api import search_news

        result = search_news("test query")
        assert isinstance(result, list)

    def test_search_entity_news_exists(self):
        """Test that search_entity_news function exists"""
        from datagod.scrapers.categories.news_api import search_entity_news

        assert callable(search_entity_news)

    def test_search_entity_news_returns_list(self):
        """Test search_entity_news returns a list"""
        from datagod.scrapers.categories.news_api import search_entity_news

        result = search_entity_news("John Doe")
        assert isinstance(result, list)

    def test_get_local_headlines_exists(self):
        """Test that get_local_headlines function exists"""
        from datagod.scrapers.categories.news_api import get_local_headlines

        assert callable(get_local_headlines)

    def test_get_local_headlines_returns_list(self):
        """Test get_local_headlines returns a list"""
        from datagod.scrapers.categories.news_api import get_local_headlines

        result = get_local_headlines("CA")
        assert isinstance(result, list)
