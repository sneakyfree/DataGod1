"""
News API Module

Provides unified access to news sources:
- NewsAPI.org integration
- Google News RSS feeds
- Local news outlet aggregation
- Press release aggregators

Supports searching for news articles by keyword, source,
date range, and geographic location.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class NewsCategory(Enum):
    """News article categories"""
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    POLITICS = "politics"
    REAL_ESTATE = "real_estate"
    LEGAL = "legal"
    FINANCE = "finance"
    LOCAL = "local"
    CRIME = "crime"
    GOVERNMENT = "government"
    GENERAL = "general"
    UNKNOWN = "unknown"


class NewsSentiment(Enum):
    """Sentiment analysis result"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class NewsSourceType(Enum):
    """Types of news sources"""
    MAJOR_OUTLET = "major_outlet"
    LOCAL_NEWS = "local_news"
    WIRE_SERVICE = "wire_service"
    PRESS_RELEASE = "press_release"
    BLOG = "blog"
    TRADE_PUBLICATION = "trade_publication"
    GOVERNMENT = "government"
    UNKNOWN = "unknown"


@dataclass
class NewsSource:
    """Represents a news source/publisher"""
    source_id: str
    name: str
    source_type: NewsSourceType = NewsSourceType.UNKNOWN
    url: Optional[str] = None
    description: Optional[str] = None
    country: Optional[str] = None
    language: str = "en"
    categories: List[NewsCategory] = field(default_factory=list)
    state: Optional[str] = None  # For local news
    city: Optional[str] = None   # For local news

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_id': self.source_id,
            'name': self.name,
            'source_type': self.source_type.value,
            'url': self.url,
            'description': self.description,
            'country': self.country,
            'language': self.language,
            'categories': [c.value for c in self.categories],
            'state': self.state,
            'city': self.city
        }


@dataclass
class NewsArticle:
    """Represents a news article"""
    article_id: str
    title: str
    source: NewsSource
    published_at: datetime
    url: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    category: NewsCategory = NewsCategory.UNKNOWN
    sentiment: NewsSentiment = NewsSentiment.UNKNOWN
    keywords: List[str] = field(default_factory=list)
    entities_mentioned: List[str] = field(default_factory=list)
    locations_mentioned: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'article_id': self.article_id,
            'title': self.title,
            'source': self.source.to_dict(),
            'published_at': self.published_at.isoformat(),
            'url': self.url,
            'author': self.author,
            'description': self.description,
            'content': self.content,
            'image_url': self.image_url,
            'category': self.category.value,
            'sentiment': self.sentiment.value,
            'keywords': self.keywords,
            'entities_mentioned': self.entities_mentioned,
            'locations_mentioned': self.locations_mentioned,
            'fetched_at': self.fetched_at.isoformat()
        }


@dataclass
class PressRelease:
    """Represents a press release"""
    release_id: str
    headline: str
    source_company: str
    published_at: datetime
    url: Optional[str] = None
    summary: Optional[str] = None
    full_text: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    ticker_symbols: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'release_id': self.release_id,
            'headline': self.headline,
            'source_company': self.source_company,
            'published_at': self.published_at.isoformat(),
            'url': self.url,
            'summary': self.summary,
            'full_text': self.full_text,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'ticker_symbols': self.ticker_symbols,
            'topics': self.topics,
            'fetched_at': self.fetched_at.isoformat()
        }


@dataclass
class NewsSearch:
    """Search parameters for news articles"""
    keywords: Optional[str] = None
    phrase: Optional[str] = None  # Exact phrase match
    exclude_keywords: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    categories: Optional[List[NewsCategory]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    language: str = "en"
    country: Optional[str] = None
    state: Optional[str] = None  # For local news
    city: Optional[str] = None   # For local news
    sort_by: str = "publishedAt"  # publishedAt, relevancy, popularity
    page_size: int = 20
    page: int = 1


@dataclass
class EntityNewsSearch:
    """Search for news about a specific entity (person, company, property)"""
    entity_name: str
    entity_type: str  # person, company, property, address
    additional_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    state: Optional[str] = None
    include_press_releases: bool = True


class NewsAPIScraper(ABC):
    """
    Abstract base class for NewsAPI.org integration.

    NewsAPI provides access to headlines and articles from
    over 80,000 news sources worldwide.

    Free tier: 100 requests/day, 1 month old articles
    Developer tier: 250 requests/day, 1 month old articles
    Business tier: 500,000+ requests/month, all articles
    """

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        """
        Initialize NewsAPI scraper.

        Args:
            api_key: NewsAPI.org API key (required)
            config: Optional configuration dictionary
        """
        self.api_key = api_key
        self.config = config or {}
        logger.info("Initialized NewsAPIScraper")

    @abstractmethod
    def search_articles(self, search: NewsSearch) -> List[NewsArticle]:
        """
        Search for news articles.

        Args:
            search: NewsSearch parameters

        Returns:
            List of matching NewsArticle objects
        """
        pass

    @abstractmethod
    def get_top_headlines(self,
                         country: str = "us",
                         category: NewsCategory = None,
                         sources: List[str] = None,
                         keywords: str = None) -> List[NewsArticle]:
        """
        Get top headlines.

        Args:
            country: 2-letter country code
            category: News category filter
            sources: List of source IDs
            keywords: Keywords to search in headlines

        Returns:
            List of NewsArticle objects
        """
        pass

    @abstractmethod
    def get_sources(self,
                   category: NewsCategory = None,
                   country: str = None,
                   language: str = "en") -> List[NewsSource]:
        """
        Get available news sources.

        Args:
            category: Filter by category
            country: Filter by country
            language: Filter by language

        Returns:
            List of NewsSource objects
        """
        pass

    def classify_category(self, text: str) -> NewsCategory:
        """Classify article category based on text content."""
        text_lower = text.lower()

        category_keywords = {
            NewsCategory.BUSINESS: ['business', 'company', 'corporate', 'market', 'stock', 'earnings'],
            NewsCategory.TECHNOLOGY: ['tech', 'technology', 'software', 'startup', 'digital', 'ai', 'app'],
            NewsCategory.POLITICS: ['politics', 'election', 'vote', 'congress', 'senate', 'governor'],
            NewsCategory.REAL_ESTATE: ['real estate', 'property', 'housing', 'home', 'mortgage', 'foreclosure'],
            NewsCategory.LEGAL: ['lawsuit', 'court', 'legal', 'attorney', 'judge', 'verdict', 'trial'],
            NewsCategory.FINANCE: ['finance', 'bank', 'loan', 'investment', 'credit', 'debt'],
            NewsCategory.CRIME: ['crime', 'arrest', 'police', 'robbery', 'fraud', 'theft'],
            NewsCategory.GOVERNMENT: ['government', 'city council', 'mayor', 'county', 'public'],
        }

        for category, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return category

        return NewsCategory.GENERAL


class GoogleNewsScraper(ABC):
    """
    Abstract base class for Google News RSS scraping.

    Google News RSS feeds are free and don't require API keys,
    but have limited customization and may be rate-limited.
    """

    RSS_BASE_URL = "https://news.google.com/rss"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        logger.info("Initialized GoogleNewsScraper")

    @abstractmethod
    def search_news(self, query: str,
                   language: str = "en",
                   country: str = "US") -> List[NewsArticle]:
        """
        Search Google News RSS feed.

        Args:
            query: Search query
            language: Language code
            country: Country code

        Returns:
            List of NewsArticle objects
        """
        pass

    @abstractmethod
    def get_topic_headlines(self, topic: str,
                           language: str = "en",
                           country: str = "US") -> List[NewsArticle]:
        """
        Get headlines for a topic.

        Topics: WORLD, NATION, BUSINESS, TECHNOLOGY,
                ENTERTAINMENT, SPORTS, SCIENCE, HEALTH

        Args:
            topic: Topic name
            language: Language code
            country: Country code

        Returns:
            List of NewsArticle objects
        """
        pass

    @abstractmethod
    def get_location_news(self, location: str,
                         language: str = "en") -> List[NewsArticle]:
        """
        Get news for a specific location.

        Args:
            location: City, state, or region name
            language: Language code

        Returns:
            List of NewsArticle objects
        """
        pass


class LocalNewsAggregator(ABC):
    """
    Abstract base class for local news aggregation.

    Aggregates news from local newspapers, TV stations,
    and regional news outlets by state and city.
    """

    # Major local news sources by state (sample)
    STATE_SOURCES = {
        'CA': ['latimes.com', 'sfchronicle.com', 'sandiegouniontribune.com', 'mercurynews.com'],
        'TX': ['dallasnews.com', 'houstonchronicle.com', 'statesman.com', 'expressnews.com'],
        'NY': ['nytimes.com', 'newsday.com', 'nydailynews.com', 'buffalonews.com'],
        'FL': ['miamiherald.com', 'tampabay.com', 'orlandosentinel.com', 'sun-sentinel.com'],
        'IL': ['chicagotribune.com', 'suntimes.com'],
        'PA': ['inquirer.com', 'post-gazette.com'],
        'OH': ['dispatch.com', 'cleveland.com', 'cincinnati.com'],
        'GA': ['ajc.com'],
        'NC': ['charlotteobserver.com', 'newsobserver.com'],
        'MI': ['freep.com', 'detroitnews.com'],
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        logger.info("Initialized LocalNewsAggregator")

    @abstractmethod
    def search_local_news(self,
                         keywords: str,
                         state: str,
                         city: str = None,
                         date_from: date = None,
                         date_to: date = None) -> List[NewsArticle]:
        """
        Search local news sources.

        Args:
            keywords: Search keywords
            state: State code (e.g., 'CA', 'TX')
            city: Optional city filter
            date_from: Start date
            date_to: End date

        Returns:
            List of NewsArticle objects
        """
        pass

    @abstractmethod
    def get_state_sources(self, state: str) -> List[NewsSource]:
        """
        Get available news sources for a state.

        Args:
            state: State code

        Returns:
            List of NewsSource objects
        """
        pass

    @abstractmethod
    def get_city_news(self, city: str, state: str) -> List[NewsArticle]:
        """
        Get recent news for a city.

        Args:
            city: City name
            state: State code

        Returns:
            List of NewsArticle objects
        """
        pass

    def get_source_state(self, source_url: str) -> Optional[str]:
        """Determine which state a news source covers."""
        domain = urlparse(source_url).netloc.lower()
        domain = domain.replace('www.', '')

        for state, sources in self.STATE_SOURCES.items():
            if domain in sources:
                return state

        return None


class PressReleaseAggregator(ABC):
    """
    Abstract base class for press release aggregation.

    Aggregates press releases from various wire services
    and company newsrooms.
    """

    # Major press release services
    WIRE_SERVICES = [
        'prnewswire.com',
        'businesswire.com',
        'globenewswire.com',
        'accesswire.com',
    ]

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        logger.info("Initialized PressReleaseAggregator")

    @abstractmethod
    def search_releases(self,
                       keywords: str = None,
                       company_name: str = None,
                       ticker: str = None,
                       date_from: date = None,
                       date_to: date = None) -> List[PressRelease]:
        """
        Search press releases.

        Args:
            keywords: Search keywords
            company_name: Company name filter
            ticker: Stock ticker filter
            date_from: Start date
            date_to: End date

        Returns:
            List of PressRelease objects
        """
        pass

    @abstractmethod
    def get_company_releases(self, company_name: str,
                            limit: int = 20) -> List[PressRelease]:
        """
        Get press releases for a company.

        Args:
            company_name: Company name
            limit: Maximum number to return

        Returns:
            List of PressRelease objects
        """
        pass


class EntityNewsFinder:
    """
    Specialized class for finding news about specific entities.

    Combines multiple news sources to find articles mentioning
    a person, company, property, or address.
    """

    def __init__(self,
                 newsapi_key: str = None,
                 config: Dict[str, Any] = None):
        self.newsapi_key = newsapi_key
        self.config = config or {}
        logger.info("Initialized EntityNewsFinder")

    def search_person_news(self,
                          name: str,
                          state: str = None,
                          date_from: date = None,
                          date_to: date = None) -> List[NewsArticle]:
        """
        Search for news articles mentioning a person.

        Args:
            name: Person's name
            state: Optional state filter for local news
            date_from: Start date
            date_to: End date

        Returns:
            List of NewsArticle objects
        """
        search = EntityNewsSearch(
            entity_name=name,
            entity_type='person',
            date_from=date_from,
            date_to=date_to,
            state=state
        )

        logger.info(f"Searching news for person: {name}")

        # Placeholder - actual implementation would search multiple sources
        return []

    def search_company_news(self,
                           company_name: str,
                           ticker: str = None,
                           date_from: date = None,
                           date_to: date = None,
                           include_press_releases: bool = True) -> List[NewsArticle]:
        """
        Search for news articles about a company.

        Args:
            company_name: Company name
            ticker: Stock ticker symbol
            date_from: Start date
            date_to: End date
            include_press_releases: Include company press releases

        Returns:
            List of NewsArticle objects
        """
        logger.info(f"Searching news for company: {company_name}")

        # Placeholder - actual implementation would search multiple sources
        return []

    def search_property_news(self,
                            address: str,
                            city: str = None,
                            state: str = None,
                            date_from: date = None,
                            date_to: date = None) -> List[NewsArticle]:
        """
        Search for news articles mentioning a property address.

        Args:
            address: Property address
            city: City name
            state: State code
            date_from: Start date
            date_to: End date

        Returns:
            List of NewsArticle objects
        """
        logger.info(f"Searching news for property: {address}")

        # Placeholder - actual implementation would search multiple sources
        return []


# =============================================================================
# Convenience Functions
# =============================================================================

def search_news(
    keywords: str,
    sources: List[str] = None,
    date_from: date = None,
    date_to: date = None,
    state: str = None
) -> List[NewsArticle]:
    """
    Convenience function to search news across multiple sources.

    Args:
        keywords: Search keywords
        sources: List of source IDs
        date_from: Start date filter
        date_to: End date filter
        state: State code for local news

    Returns:
        List of matching NewsArticle objects
    """
    search = NewsSearch(
        keywords=keywords,
        sources=sources,
        date_from=date_from,
        date_to=date_to,
        state=state
    )

    logger.info(f"Searching news: {keywords}")

    # Placeholder - actual implementation would use news scrapers
    return []


def search_entity_news(
    entity_name: str,
    entity_type: str = "person",
    state: str = None,
    date_from: date = None,
    date_to: date = None
) -> List[NewsArticle]:
    """
    Convenience function to search news about an entity.

    Args:
        entity_name: Name of the entity
        entity_type: Type (person, company, property)
        state: State code for local news
        date_from: Start date filter
        date_to: End date filter

    Returns:
        List of matching NewsArticle objects
    """
    search = EntityNewsSearch(
        entity_name=entity_name,
        entity_type=entity_type,
        state=state,
        date_from=date_from,
        date_to=date_to
    )

    logger.info(f"Searching news for {entity_type}: {entity_name}")

    # Placeholder - actual implementation would use EntityNewsFinder
    return []


def get_local_headlines(
    state: str,
    city: str = None,
    category: NewsCategory = None
) -> List[NewsArticle]:
    """
    Convenience function to get local news headlines.

    Args:
        state: State code
        city: Optional city filter
        category: Optional category filter

    Returns:
        List of NewsArticle objects
    """
    logger.info(f"Getting local headlines for {state}" + (f", {city}" if city else ""))

    # Placeholder - actual implementation would use LocalNewsAggregator
    return []
