"""
County Assessor Base Class

Abstract base class for all county assessor scrapers. Defines the common
interface and shared functionality for extracting property assessment data.

Property assessment data includes:
- Assessed values (land, improvements, total)
- Market values
- Property characteristics
- Tax information
- Ownership history
- Sales history
- Exemptions and special assessments
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PropertyType(Enum):
    """Types of properties."""

    # Residential
    SINGLE_FAMILY = "single_family"
    MULTI_FAMILY = "multi_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MOBILE_HOME = "mobile_home"
    MANUFACTURED = "manufactured"
    COOPERATIVE = "cooperative"

    # Commercial
    COMMERCIAL = "commercial"
    OFFICE = "office"
    RETAIL = "retail"
    INDUSTRIAL = "industrial"
    WAREHOUSE = "warehouse"
    HOTEL_MOTEL = "hotel_motel"
    MIXED_USE = "mixed_use"

    # Land
    VACANT_LAND = "vacant_land"
    AGRICULTURAL = "agricultural"
    FARM = "farm"
    RANCH = "ranch"
    TIMBER = "timber"

    # Special
    EXEMPT = "exempt"
    GOVERNMENT = "government"
    RELIGIOUS = "religious"
    EDUCATIONAL = "educational"
    NONPROFIT = "nonprofit"
    UTILITY = "utility"

    OTHER = "other"
    UNKNOWN = "unknown"


class PropertyClass(Enum):
    """Property classification codes (varies by jurisdiction)."""

    # Common classifications
    CLASS_1 = "class_1"  # Often residential
    CLASS_2 = "class_2"  # Often commercial
    CLASS_3 = "class_3"  # Often industrial
    CLASS_4 = "class_4"  # Often agricultural
    CLASS_5 = "class_5"

    # Residential subclasses
    RESIDENTIAL_IMPROVED = "residential_improved"
    RESIDENTIAL_VACANT = "residential_vacant"

    # Commercial subclasses
    COMMERCIAL_IMPROVED = "commercial_improved"
    COMMERCIAL_VACANT = "commercial_vacant"

    # Industrial
    INDUSTRIAL_IMPROVED = "industrial_improved"
    INDUSTRIAL_VACANT = "industrial_vacant"

    # Agricultural
    AGRICULTURAL_IMPROVED = "agricultural_improved"
    AGRICULTURAL_VACANT = "agricultural_vacant"

    # Exempt
    EXEMPT_GOVERNMENT = "exempt_government"
    EXEMPT_RELIGIOUS = "exempt_religious"
    EXEMPT_EDUCATIONAL = "exempt_educational"
    EXEMPT_CHARITABLE = "exempt_charitable"

    OTHER = "other"
    UNKNOWN = "unknown"


class ExemptionType(Enum):
    """Types of property tax exemptions."""

    HOMESTEAD = "homestead"
    SENIOR_CITIZEN = "senior_citizen"
    VETERAN = "veteran"
    DISABLED_VETERAN = "disabled_veteran"
    DISABILITY = "disability"
    WIDOW_WIDOWER = "widow_widower"
    BLIND = "blind"
    AGRICULTURAL = "agricultural"
    HISTORIC = "historic"
    SOLAR_ENERGY = "solar_energy"
    GREEN_BUILDING = "green_building"
    ECONOMIC_DEVELOPMENT = "economic_development"
    RELIGIOUS = "religious"
    CHARITABLE = "charitable"
    EDUCATIONAL = "educational"
    GOVERNMENT = "government"
    LOW_INCOME = "low_income"
    FREEZE = "freeze"  # Assessment freeze
    OTHER = "other"


@dataclass
class PropertyCharacteristics:
    """Physical characteristics of a property."""

    # Building info
    year_built: Optional[int] = None
    effective_year: Optional[int] = None  # Year of major renovation
    building_sqft: Optional[int] = None
    living_sqft: Optional[int] = None
    gross_sqft: Optional[int] = None

    # Rooms
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None  # 2.5 for 2 full, 1 half
    full_baths: Optional[int] = None
    half_baths: Optional[int] = None
    rooms_total: Optional[int] = None

    # Structure
    stories: Optional[float] = None
    units: Optional[int] = None  # For multi-family
    building_type: Optional[str] = None
    construction_type: Optional[str] = None  # Frame, Masonry, etc.
    exterior_wall: Optional[str] = None
    roof_type: Optional[str] = None
    foundation: Optional[str] = None

    # Features
    garage_type: Optional[str] = None
    garage_sqft: Optional[int] = None
    garage_spaces: Optional[int] = None
    parking_spaces: Optional[int] = None
    basement: Optional[str] = None  # Full, Partial, None
    basement_sqft: Optional[int] = None
    basement_finished_sqft: Optional[int] = None
    attic: Optional[str] = None
    fireplace_count: Optional[int] = None
    pool: bool = False
    pool_type: Optional[str] = None
    central_air: bool = False
    heating_type: Optional[str] = None
    cooling_type: Optional[str] = None

    # Land
    lot_sqft: Optional[int] = None
    lot_acres: Optional[float] = None
    lot_width: Optional[float] = None
    lot_depth: Optional[float] = None
    zoning: Optional[str] = None
    flood_zone: Optional[str] = None
    topography: Optional[str] = None

    # Condition
    condition: Optional[str] = None  # Excellent, Good, Fair, Poor
    quality: Optional[str] = None

    # Raw data
    raw_characteristics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaxAssessment:
    """Tax assessment information for a specific year."""

    tax_year: int
    assessed_value_land: Optional[Decimal] = None
    assessed_value_improvements: Optional[Decimal] = None
    assessed_value_total: Optional[Decimal] = None
    market_value_land: Optional[Decimal] = None
    market_value_improvements: Optional[Decimal] = None
    market_value_total: Optional[Decimal] = None

    # Tax amounts
    tax_amount: Optional[Decimal] = None
    tax_rate: Optional[float] = None  # Mills or percentage

    # Exemptions
    exemptions: List[ExemptionType] = field(default_factory=list)
    exemption_amount: Optional[Decimal] = None
    taxable_value: Optional[Decimal] = None

    # Special assessments
    special_assessments: Optional[Decimal] = None
    special_assessment_details: List[str] = field(default_factory=list)

    # Status
    is_delinquent: bool = False
    delinquent_amount: Optional[Decimal] = None
    delinquent_years: List[int] = field(default_factory=list)


@dataclass
class OwnershipRecord:
    """Property ownership record."""

    owner_name: str
    owner_type: Optional[str] = None  # Individual, Corporation, Trust, etc.
    mailing_address: Optional[str] = None
    mailing_city: Optional[str] = None
    mailing_state: Optional[str] = None
    mailing_zip: Optional[str] = None
    ownership_start_date: Optional[date] = None
    ownership_percentage: Optional[float] = None  # For multiple owners
    is_primary_owner: bool = True

    # Additional owners
    co_owner_name: Optional[str] = None


@dataclass
class SaleRecord:
    """Property sale/transfer record."""

    sale_date: date
    sale_price: Decimal
    buyer_name: Optional[str] = None
    seller_name: Optional[str] = None
    document_number: Optional[str] = None
    document_type: Optional[str] = None  # Warranty Deed, Quit Claim, etc.
    sale_type: Optional[str] = None  # Arms-length, Related party, etc.
    is_valid_sale: bool = True  # Arms-length transaction
    price_per_sqft: Optional[Decimal] = None


@dataclass
class PropertyAssessment:
    """Complete property assessment record."""

    # Identifiers
    parcel_id: str  # APN, PIN, Folio, etc.
    property_address: str
    city: Optional[str] = None
    state: str = ""
    zip_code: Optional[str] = None
    county: str = ""

    # Legal description
    legal_description: Optional[str] = None
    subdivision: Optional[str] = None
    lot: Optional[str] = None
    block: Optional[str] = None
    section: Optional[str] = None
    township: Optional[str] = None
    range: Optional[str] = None

    # Property type
    property_type: PropertyType = PropertyType.UNKNOWN
    property_class: PropertyClass = PropertyClass.UNKNOWN
    property_use: Optional[str] = None
    zoning: Optional[str] = None

    # Current values
    assessed_value: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    land_value: Optional[Decimal] = None
    improvement_value: Optional[Decimal] = None
    tax_year: Optional[int] = None

    # Characteristics
    characteristics: Optional[PropertyCharacteristics] = None

    # Assessment history
    assessment_history: List[TaxAssessment] = field(default_factory=list)

    # Ownership
    current_owner: Optional[OwnershipRecord] = None
    ownership_history: List[OwnershipRecord] = field(default_factory=list)

    # Sales history
    sales_history: List[SaleRecord] = field(default_factory=list)
    last_sale_date: Optional[date] = None
    last_sale_price: Optional[Decimal] = None

    # Geographic
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    census_tract: Optional[str] = None
    neighborhood: Optional[str] = None

    # Source
    source_url: Optional[str] = None
    source_system: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AssessorSearchCriteria:
    """Criteria for searching property assessments."""

    # Address search
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None

    # Parcel search
    parcel_id: Optional[str] = None

    # Owner search
    owner_name: Optional[str] = None

    # Legal description
    subdivision: Optional[str] = None
    lot: Optional[str] = None
    block: Optional[str] = None

    # Filters
    property_types: List[PropertyType] = field(default_factory=list)
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    min_sqft: Optional[int] = None
    max_sqft: Optional[int] = None
    min_year_built: Optional[int] = None
    max_year_built: Optional[int] = None

    # Pagination
    page_number: int = 1
    page_size: int = 25
    max_results: int = 500


@dataclass
class AssessorSearchResult:
    """Result of a property assessment search."""

    properties: List[PropertyAssessment]
    total_count: int
    page_number: int
    page_size: int
    has_more: bool
    search_criteria: AssessorSearchCriteria
    search_time_ms: int = 0
    source_system: str = ""
    warnings: List[str] = field(default_factory=list)


class CountyAssessorBase(ABC):
    """
    Abstract base class for county assessor scrapers.

    Each county assessor implementation must override the abstract methods
    to handle the specific county's data portal.
    """

    # County information (override in subclasses)
    COUNTY_NAME: str = ""
    STATE: str = ""
    FIPS_CODE: str = ""

    # System information
    BASE_URL: str = ""
    SYSTEM_NAME: str = ""

    # Parcel ID format (varies by county)
    PARCEL_ID_FORMAT: str = ""  # Description of format
    PARCEL_ID_PATTERN: str = ""  # Regex pattern

    # Rate limiting
    REQUEST_DELAY: float = 1.0
    MAX_RETRIES: int = 3
    TIMEOUT: int = 30

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the county assessor scraper."""
        self.session = session
        self._owns_session = session is None
        self._last_request_time: float = 0

    async def __aenter__(self):
        """Async context manager entry."""
        if self._owns_session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT),
                headers=self._get_headers(),
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._owns_session and self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        import time

        current_time = time.time()
        elapsed = current_time - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    async def _fetch(self, url: str, method: str = "GET", **kwargs) -> Tuple[int, str]:
        """Fetch a URL with rate limiting and retries."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit()

        for attempt in range(self.MAX_RETRIES):
            try:
                if method.upper() == "GET":
                    async with self.session.get(url, **kwargs) as response:
                        return response.status, await response.text()
                elif method.upper() == "POST":
                    async with self.session.post(url, **kwargs) as response:
                        return response.status, await response.text()
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

            except aiohttp.ClientError as e:
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    raise

        raise RuntimeError(f"Failed to fetch {url} after {self.MAX_RETRIES} attempts")

    async def _fetch_json(
        self, url: str, method: str = "GET", **kwargs
    ) -> Dict[str, Any]:
        """Fetch a URL and parse JSON response."""
        if not self.session:
            raise RuntimeError("Session not initialized.")

        await self._rate_limit()

        async with self.session.request(method, url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()

    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content."""
        return BeautifulSoup(html, "html.parser")

    def _normalize_parcel_id(self, parcel_id: str) -> str:
        """Normalize a parcel ID to standard format."""
        # Remove common separators and spaces
        normalized = (
            parcel_id.replace("-", "").replace(".", "").replace(" ", "").strip()
        )
        return normalized.upper()

    def _parse_property_type(self, raw_type: str) -> PropertyType:
        """Parse a raw property type string to PropertyType enum."""
        if not raw_type:
            return PropertyType.UNKNOWN

        raw_type = raw_type.upper().strip()

        type_mappings = {
            # Residential
            "SFR": PropertyType.SINGLE_FAMILY,
            "SINGLE FAMILY": PropertyType.SINGLE_FAMILY,
            "SINGLE FAM": PropertyType.SINGLE_FAMILY,
            "RESIDENTIAL": PropertyType.SINGLE_FAMILY,
            "RES": PropertyType.SINGLE_FAMILY,
            "MULTI": PropertyType.MULTI_FAMILY,
            "MULTI-FAMILY": PropertyType.MULTI_FAMILY,
            "DUPLEX": PropertyType.MULTI_FAMILY,
            "TRIPLEX": PropertyType.MULTI_FAMILY,
            "FOURPLEX": PropertyType.MULTI_FAMILY,
            "APARTMENT": PropertyType.MULTI_FAMILY,
            "CONDO": PropertyType.CONDO,
            "CONDOMINIUM": PropertyType.CONDO,
            "TOWNHOUSE": PropertyType.TOWNHOUSE,
            "TOWNHOME": PropertyType.TOWNHOUSE,
            "MOBILE": PropertyType.MOBILE_HOME,
            "MOBILE HOME": PropertyType.MOBILE_HOME,
            "MANUFACTURED": PropertyType.MANUFACTURED,
            # Commercial
            "COMMERCIAL": PropertyType.COMMERCIAL,
            "COM": PropertyType.COMMERCIAL,
            "OFFICE": PropertyType.OFFICE,
            "RETAIL": PropertyType.RETAIL,
            "INDUSTRIAL": PropertyType.INDUSTRIAL,
            "IND": PropertyType.INDUSTRIAL,
            "WAREHOUSE": PropertyType.WAREHOUSE,
            "HOTEL": PropertyType.HOTEL_MOTEL,
            "MOTEL": PropertyType.HOTEL_MOTEL,
            "MIXED": PropertyType.MIXED_USE,
            "MIXED USE": PropertyType.MIXED_USE,
            # Land
            "VACANT": PropertyType.VACANT_LAND,
            "VACANT LAND": PropertyType.VACANT_LAND,
            "LAND": PropertyType.VACANT_LAND,
            "AGRICULTURAL": PropertyType.AGRICULTURAL,
            "AG": PropertyType.AGRICULTURAL,
            "FARM": PropertyType.FARM,
            "RANCH": PropertyType.RANCH,
            "TIMBER": PropertyType.TIMBER,
            # Special
            "EXEMPT": PropertyType.EXEMPT,
            "GOVERNMENT": PropertyType.GOVERNMENT,
            "CHURCH": PropertyType.RELIGIOUS,
            "RELIGIOUS": PropertyType.RELIGIOUS,
            "SCHOOL": PropertyType.EDUCATIONAL,
            "EDUCATIONAL": PropertyType.EDUCATIONAL,
            "NONPROFIT": PropertyType.NONPROFIT,
            "UTILITY": PropertyType.UTILITY,
        }

        if raw_type in type_mappings:
            return type_mappings[raw_type]

        # Check partial matches
        for key, prop_type in type_mappings.items():
            if key in raw_type:
                return prop_type

        return PropertyType.UNKNOWN

    def _parse_decimal(self, value_str: str) -> Optional[Decimal]:
        """Parse a monetary value string to Decimal."""
        if not value_str:
            return None

        # Remove currency symbols and commas
        cleaned = value_str.replace("$", "").replace(",", "").strip()

        try:
            return Decimal(cleaned)
        except Exception:
            logger.warning(f"Could not parse decimal: {value_str}")
            return None

    def _parse_int(self, value_str: str) -> Optional[int]:
        """Parse an integer string."""
        if not value_str:
            return None

        # Remove commas
        cleaned = value_str.replace(",", "").strip()

        try:
            return int(float(cleaned))  # Handle "1234.0" format
        except Exception:
            logger.warning(f"Could not parse int: {value_str}")
            return None

    def _parse_float(self, value_str: str) -> Optional[float]:
        """Parse a float string."""
        if not value_str:
            return None

        cleaned = value_str.replace(",", "").strip()

        try:
            return float(cleaned)
        except Exception:
            logger.warning(f"Could not parse float: {value_str}")
            return None

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string to a date object."""
        if not date_str:
            return None

        date_str = date_str.strip()

        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y-%m-%d",
            "%m/%d/%y",
            "%d-%b-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y%m%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def get_assessor_info(self) -> Dict[str, Any]:
        """Get information about this assessor's office."""
        return {
            "county": self.COUNTY_NAME,
            "state": self.STATE,
            "fips_code": self.FIPS_CODE,
            "base_url": self.BASE_URL,
            "system": self.SYSTEM_NAME,
            "parcel_id_format": self.PARCEL_ID_FORMAT,
        }

    # Abstract methods that must be implemented by each assessor

    @abstractmethod
    async def search_by_address(
        self,
        street_address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        max_results: int = 100,
    ) -> AssessorSearchResult:
        """
        Search for properties by address.

        Args:
            street_address: Street address to search
            city: Optional city filter
            zip_code: Optional zip code filter
            max_results: Maximum results to return

        Returns:
            AssessorSearchResult with matching properties
        """
        pass

    @abstractmethod
    async def search_by_parcel_id(self, parcel_id: str) -> Optional[PropertyAssessment]:
        """
        Search for a property by parcel ID (APN, PIN, Folio, etc.).

        Args:
            parcel_id: The parcel identifier

        Returns:
            PropertyAssessment if found, None otherwise
        """
        pass

    @abstractmethod
    async def search_by_owner(
        self, owner_name: str, max_results: int = 100
    ) -> AssessorSearchResult:
        """
        Search for properties by owner name.

        Args:
            owner_name: Owner name to search
            max_results: Maximum results to return

        Returns:
            AssessorSearchResult with matching properties
        """
        pass

    @abstractmethod
    async def get_property_detail(self, parcel_id: str) -> Optional[PropertyAssessment]:
        """
        Get detailed property information including characteristics and history.

        Args:
            parcel_id: The parcel identifier

        Returns:
            PropertyAssessment with full details, or None if not found
        """
        pass

    async def get_assessment_history(
        self, parcel_id: str, years: int = 5
    ) -> List[TaxAssessment]:
        """
        Get assessment history for a property.

        Default implementation calls get_property_detail and returns history.
        Override if the system provides a separate history endpoint.

        Args:
            parcel_id: The parcel identifier
            years: Number of years of history

        Returns:
            List of TaxAssessment entries
        """
        property_data = await self.get_property_detail(parcel_id)
        if property_data:
            return property_data.assessment_history[:years]
        return []

    async def get_sales_history(self, parcel_id: str) -> List[SaleRecord]:
        """
        Get sales history for a property.

        Default implementation calls get_property_detail and returns sales.
        Override if the system provides a separate sales endpoint.

        Args:
            parcel_id: The parcel identifier

        Returns:
            List of SaleRecord entries
        """
        property_data = await self.get_property_detail(parcel_id)
        if property_data:
            return property_data.sales_history
        return []


# Synchronous wrapper functions


def search_by_address_sync(
    assessor: CountyAssessorBase, street_address: str, **kwargs
) -> AssessorSearchResult:
    """Synchronous wrapper for search_by_address."""

    async def _search():
        async with assessor:
            return await assessor.search_by_address(street_address, **kwargs)

    return asyncio.run(_search())


def search_by_owner_sync(
    assessor: CountyAssessorBase, owner_name: str, **kwargs
) -> AssessorSearchResult:
    """Synchronous wrapper for search_by_owner."""

    async def _search():
        async with assessor:
            return await assessor.search_by_owner(owner_name, **kwargs)

    return asyncio.run(_search())


def get_property_sync(
    assessor: CountyAssessorBase, parcel_id: str
) -> Optional[PropertyAssessment]:
    """Synchronous wrapper for get_property_detail."""

    async def _get():
        async with assessor:
            return await assessor.get_property_detail(parcel_id)

    return asyncio.run(_get())
