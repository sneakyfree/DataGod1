"""
Base County Scraper - Abstract base class for county-level scrapers.

Provides common functionality for scraping county recorder offices,
courts, assessors, and other county-level public records.
"""

import asyncio
import aiohttp
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum


class RecordType(Enum):
    """Types of recorded documents."""
    DEED = "deed"
    MORTGAGE = "mortgage"
    DEED_OF_TRUST = "deed_of_trust"
    LIEN = "lien"
    JUDGMENT = "judgment"
    UCC = "ucc"
    RELEASE = "release"
    ASSIGNMENT = "assignment"
    SATISFACTION = "satisfaction"
    LIS_PENDENS = "lis_pendens"
    MECHANICS_LIEN = "mechanics_lien"
    TAX_LIEN = "tax_lien"
    MARRIAGE = "marriage"
    DEATH = "death"
    MILITARY_DISCHARGE = "military_discharge"
    POWER_OF_ATTORNEY = "power_of_attorney"
    OTHER = "other"


class CaseType(Enum):
    """Types of court cases."""
    CIVIL = "civil"
    CRIMINAL = "criminal"
    FAMILY = "family"
    PROBATE = "probate"
    TRAFFIC = "traffic"
    SMALL_CLAIMS = "small_claims"
    EVICTION = "eviction"
    FORECLOSURE = "foreclosure"
    BANKRUPTCY = "bankruptcy"
    JUVENILE = "juvenile"
    OTHER = "other"


class CaseStatus(Enum):
    """Court case status."""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    DISMISSED = "dismissed"
    JUDGMENT = "judgment"
    APPEAL = "appeal"
    SETTLED = "settled"


@dataclass
class CountyConfig:
    """Configuration for a county scraper."""
    state: str
    county_name: str
    fips_code: str
    seat: str
    population: int = 0
    recorder_url: Optional[str] = None
    assessor_url: Optional[str] = None
    clerk_url: Optional[str] = None
    courts_url: Optional[str] = None
    treasurer_url: Optional[str] = None
    sheriff_url: Optional[str] = None
    gis_url: Optional[str] = None
    requires_session: bool = False
    rate_limit_seconds: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "county_name": self.county_name,
            "fips_code": self.fips_code,
            "seat": self.seat,
            "population": self.population,
            "recorder_url": self.recorder_url,
            "assessor_url": self.assessor_url,
            "clerk_url": self.clerk_url,
            "courts_url": self.courts_url,
            "treasurer_url": self.treasurer_url,
            "sheriff_url": self.sheriff_url,
            "gis_url": self.gis_url,
        }


@dataclass
class PropertyRecord:
    """Property/parcel record from county assessor."""
    parcel_id: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None
    property_class: Optional[str] = None
    land_use: Optional[str] = None
    assessed_value: float = 0.0
    land_value: float = 0.0
    improvement_value: float = 0.0
    market_value: float = 0.0
    tax_year: Optional[int] = None
    acres: float = 0.0
    square_feet: int = 0
    year_built: Optional[int] = None
    bedrooms: int = 0
    bathrooms: float = 0.0
    building_sqft: int = 0
    legal_description: Optional[str] = None
    subdivision: Optional[str] = None
    school_district: Optional[str] = None
    township: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    county: Optional[str] = None
    fips_code: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parcel_id": self.parcel_id,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "owner_name": self.owner_name,
            "owner_address": self.owner_address,
            "property_class": self.property_class,
            "land_use": self.land_use,
            "assessed_value": self.assessed_value,
            "land_value": self.land_value,
            "improvement_value": self.improvement_value,
            "market_value": self.market_value,
            "tax_year": self.tax_year,
            "acres": self.acres,
            "square_feet": self.square_feet,
            "year_built": self.year_built,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "building_sqft": self.building_sqft,
            "legal_description": self.legal_description,
            "subdivision": self.subdivision,
            "school_district": self.school_district,
            "township": self.township,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "county": self.county,
            "fips_code": self.fips_code,
        }


@dataclass
class DeedRecord:
    """Deed/document record from county recorder."""
    document_number: str
    record_type: str
    grantor: Optional[str] = None
    grantee: Optional[str] = None
    recording_date: Optional[datetime] = None
    document_date: Optional[datetime] = None
    book: Optional[str] = None
    page: Optional[str] = None
    consideration: float = 0.0
    parcel_id: Optional[str] = None
    legal_description: Optional[str] = None
    property_address: Optional[str] = None
    instrument_type: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    fips_code: Optional[str] = None
    document_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_number": self.document_number,
            "record_type": self.record_type,
            "grantor": self.grantor,
            "grantee": self.grantee,
            "recording_date": self.recording_date.isoformat() if self.recording_date else None,
            "document_date": self.document_date.isoformat() if self.document_date else None,
            "book": self.book,
            "page": self.page,
            "consideration": self.consideration,
            "parcel_id": self.parcel_id,
            "legal_description": self.legal_description,
            "property_address": self.property_address,
            "instrument_type": self.instrument_type,
            "county": self.county,
            "state": self.state,
            "fips_code": self.fips_code,
            "document_url": self.document_url,
        }


@dataclass
class MortgageRecord:
    """Mortgage/deed of trust record."""
    document_number: str
    borrower: Optional[str] = None
    lender: Optional[str] = None
    loan_amount: float = 0.0
    recording_date: Optional[datetime] = None
    document_date: Optional[datetime] = None
    maturity_date: Optional[datetime] = None
    interest_rate: Optional[float] = None
    loan_type: Optional[str] = None
    parcel_id: Optional[str] = None
    property_address: Optional[str] = None
    book: Optional[str] = None
    page: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    fips_code: Optional[str] = None
    mers_min: Optional[str] = None  # MERS identification number
    is_refinance: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_number": self.document_number,
            "borrower": self.borrower,
            "lender": self.lender,
            "loan_amount": self.loan_amount,
            "recording_date": self.recording_date.isoformat() if self.recording_date else None,
            "document_date": self.document_date.isoformat() if self.document_date else None,
            "maturity_date": self.maturity_date.isoformat() if self.maturity_date else None,
            "interest_rate": self.interest_rate,
            "loan_type": self.loan_type,
            "parcel_id": self.parcel_id,
            "property_address": self.property_address,
            "book": self.book,
            "page": self.page,
            "county": self.county,
            "state": self.state,
            "fips_code": self.fips_code,
            "mers_min": self.mers_min,
            "is_refinance": self.is_refinance,
        }


@dataclass
class TaxRecord:
    """Property tax record from county treasurer."""
    parcel_id: str
    tax_year: int
    owner_name: Optional[str] = None
    property_address: Optional[str] = None
    assessed_value: float = 0.0
    taxable_value: float = 0.0
    tax_amount: float = 0.0
    amount_paid: float = 0.0
    amount_due: float = 0.0
    due_date: Optional[datetime] = None
    status: Optional[str] = None  # paid, delinquent, etc.
    tax_rate: Optional[float] = None
    exemptions: List[str] = field(default_factory=list)
    special_assessments: float = 0.0
    county: Optional[str] = None
    state: Optional[str] = None
    fips_code: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parcel_id": self.parcel_id,
            "tax_year": self.tax_year,
            "owner_name": self.owner_name,
            "property_address": self.property_address,
            "assessed_value": self.assessed_value,
            "taxable_value": self.taxable_value,
            "tax_amount": self.tax_amount,
            "amount_paid": self.amount_paid,
            "amount_due": self.amount_due,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "tax_rate": self.tax_rate,
            "exemptions": self.exemptions,
            "special_assessments": self.special_assessments,
            "county": self.county,
            "state": self.state,
            "fips_code": self.fips_code,
        }


@dataclass
class CourtCase:
    """Court case record."""
    case_number: str
    case_type: str
    court: Optional[str] = None
    filing_date: Optional[datetime] = None
    status: Optional[str] = None
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    parties: List[Dict[str, str]] = field(default_factory=list)
    judge: Optional[str] = None
    disposition: Optional[str] = None
    disposition_date: Optional[datetime] = None
    amount_claimed: float = 0.0
    judgment_amount: float = 0.0
    attorney_plaintiff: Optional[str] = None
    attorney_defendant: Optional[str] = None
    case_title: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    fips_code: Optional[str] = None
    case_url: Optional[str] = None
    docket_entries: List[Dict[str, Any]] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_number": self.case_number,
            "case_type": self.case_type,
            "court": self.court,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "status": self.status,
            "plaintiff": self.plaintiff,
            "defendant": self.defendant,
            "parties": self.parties,
            "judge": self.judge,
            "disposition": self.disposition,
            "disposition_date": self.disposition_date.isoformat() if self.disposition_date else None,
            "amount_claimed": self.amount_claimed,
            "judgment_amount": self.judgment_amount,
            "attorney_plaintiff": self.attorney_plaintiff,
            "attorney_defendant": self.attorney_defendant,
            "case_title": self.case_title,
            "county": self.county,
            "state": self.state,
            "fips_code": self.fips_code,
            "case_url": self.case_url,
            "docket_entries": self.docket_entries,
        }


@dataclass
class LienRecord:
    """Lien record (tax lien, mechanic's lien, judgment lien, etc.)."""
    document_number: str
    lien_type: str
    creditor: Optional[str] = None
    debtor: Optional[str] = None
    amount: float = 0.0
    recording_date: Optional[datetime] = None
    release_date: Optional[datetime] = None
    status: Optional[str] = None  # active, released, etc.
    parcel_id: Optional[str] = None
    property_address: Optional[str] = None
    case_number: Optional[str] = None
    book: Optional[str] = None
    page: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    fips_code: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_number": self.document_number,
            "lien_type": self.lien_type,
            "creditor": self.creditor,
            "debtor": self.debtor,
            "amount": self.amount,
            "recording_date": self.recording_date.isoformat() if self.recording_date else None,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "status": self.status,
            "parcel_id": self.parcel_id,
            "property_address": self.property_address,
            "case_number": self.case_number,
            "book": self.book,
            "page": self.page,
            "county": self.county,
            "state": self.state,
            "fips_code": self.fips_code,
        }


class BaseCountyScraper(ABC):
    """
    Abstract base class for county-level scrapers.

    Subclasses must implement the search methods for their specific county's
    online systems. Each county may have different web interfaces, APIs,
    and data formats.
    """

    def __init__(
        self,
        config: CountyConfig,
        session: Optional[aiohttp.ClientSession] = None
    ):
        """
        Initialize the county scraper.

        Args:
            config: County configuration with URLs and settings
            session: Optional aiohttp session to reuse
        """
        self.config = config
        self.session = session
        self._owns_session = session is None
        self.rate_limit = config.rate_limit_seconds
        self._last_request_time = 0.0

    async def __aenter__(self):
        if self._owns_session:
            self.session = aiohttp.ClientSession(
                headers=self._get_default_headers()
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_session and self.session:
            await self.session.close()

    async def _ensure_session(self):
        """Ensure we have an active session."""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers=self._get_default_headers()
            )
            self._owns_session = True

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers for requests."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    async def _rate_limit_wait(self):
        """Wait if needed to respect rate limits."""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self._last_request_time = time.time()

    async def _get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Make a GET request with rate limiting.

        Returns HTML content or None on error.
        """
        await self._ensure_session()
        await self._rate_limit_wait()

        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
        except aiohttp.ClientError:
            pass

        return None

    async def _post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Make a POST request with rate limiting.

        Returns HTML content or None on error.
        """
        await self._ensure_session()
        await self._rate_limit_wait()

        try:
            async with self.session.post(
                url,
                data=data,
                json=json_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.text()
        except aiohttp.ClientError:
            pass

        return None

    async def _get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a GET request and return JSON response."""
        await self._ensure_session()
        await self._rate_limit_wait()

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
        except aiohttp.ClientError:
            pass

        return None

    def _parse_date(self, date_str: Optional[str], formats: List[str] = None) -> Optional[datetime]:
        """Parse a date string using common formats."""
        if not date_str:
            return None

        formats = formats or [
            "%m/%d/%Y",
            "%Y-%m-%d",
            "%m-%d-%Y",
            "%d-%b-%Y",
            "%b %d, %Y",
            "%B %d, %Y",
            "%Y%m%d",
        ]

        date_str = date_str.strip()

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def _parse_currency(self, value_str: Optional[str]) -> float:
        """Parse a currency string to float."""
        if not value_str:
            return 0.0

        # Remove currency symbols, commas, and whitespace
        cleaned = re.sub(r'[$,\s]', '', str(value_str))

        # Handle parentheses for negative numbers
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _clean_name(self, name: Optional[str]) -> Optional[str]:
        """Clean and normalize a name string."""
        if not name:
            return None

        # Remove extra whitespace
        name = ' '.join(name.split())

        # Title case if all uppercase
        if name.isupper():
            name = name.title()

        return name.strip() or None

    # ==================== Abstract Methods ====================
    # Subclasses must implement these for their specific county

    @abstractmethod
    async def search_property_by_address(
        self,
        address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None
    ) -> List[PropertyRecord]:
        """Search property records by address."""
        pass

    @abstractmethod
    async def search_property_by_owner(
        self,
        owner_name: str
    ) -> List[PropertyRecord]:
        """Search property records by owner name."""
        pass

    @abstractmethod
    async def search_property_by_parcel(
        self,
        parcel_id: str
    ) -> Optional[PropertyRecord]:
        """Get property record by parcel/PIN number."""
        pass

    @abstractmethod
    async def search_deeds_by_name(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        as_grantor: bool = True,
        as_grantee: bool = True
    ) -> List[DeedRecord]:
        """Search recorded documents by name."""
        pass

    @abstractmethod
    async def search_deeds_by_parcel(
        self,
        parcel_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[DeedRecord]:
        """Search recorded documents by parcel ID."""
        pass

    @abstractmethod
    async def search_court_cases_by_name(
        self,
        name: str,
        case_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CourtCase]:
        """Search court cases by party name."""
        pass

    @abstractmethod
    async def search_court_cases_by_number(
        self,
        case_number: str
    ) -> Optional[CourtCase]:
        """Get court case by case number."""
        pass

    # ==================== Optional Methods ====================
    # Subclasses can override these if the county provides this data

    async def get_tax_info(self, parcel_id: str) -> Optional[TaxRecord]:
        """Get tax information for a parcel."""
        return None

    async def search_liens_by_name(
        self,
        name: str,
        lien_type: Optional[str] = None
    ) -> List[LienRecord]:
        """Search liens by debtor/creditor name."""
        return []

    async def search_liens_by_parcel(
        self,
        parcel_id: str
    ) -> List[LienRecord]:
        """Search liens by parcel ID."""
        return []

    async def search_foreclosures(
        self,
        address: Optional[str] = None,
        owner: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CourtCase]:
        """Search foreclosure cases."""
        return []

    async def search_evictions(
        self,
        address: Optional[str] = None,
        tenant: Optional[str] = None,
        landlord: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CourtCase]:
        """Search eviction cases."""
        return []

    # ==================== Convenience Methods ====================

    async def get_full_property_profile(
        self,
        parcel_id: str
    ) -> Dict[str, Any]:
        """
        Get a complete property profile including ownership,
        tax info, recorded documents, and any liens.
        """
        property_record = await self.search_property_by_parcel(parcel_id)
        deeds = await self.search_deeds_by_parcel(parcel_id)
        tax_info = await self.get_tax_info(parcel_id)
        liens = await self.search_liens_by_parcel(parcel_id)

        return {
            "property": property_record.to_dict() if property_record else None,
            "deeds": [d.to_dict() for d in deeds],
            "tax_info": tax_info.to_dict() if tax_info else None,
            "liens": [l.to_dict() for l in liens],
            "county": self.config.county_name,
            "state": self.config.state,
            "fips_code": self.config.fips_code,
        }

    async def get_person_records(
        self,
        name: str,
        include_property: bool = True,
        include_deeds: bool = True,
        include_court: bool = True
    ) -> Dict[str, Any]:
        """
        Get all available records for a person across
        property, deeds, and court systems.
        """
        results = {
            "name": name,
            "county": self.config.county_name,
            "state": self.config.state,
            "fips_code": self.config.fips_code,
        }

        if include_property:
            properties = await self.search_property_by_owner(name)
            results["properties"] = [p.to_dict() for p in properties]

        if include_deeds:
            deeds = await self.search_deeds_by_name(name)
            results["deeds"] = [d.to_dict() for d in deeds]

        if include_court:
            cases = await self.search_court_cases_by_name(name)
            results["court_cases"] = [c.to_dict() for c in cases]

        return results


# Export all
__all__ = [
    "BaseCountyScraper",
    "CountyConfig",
    "PropertyRecord",
    "DeedRecord",
    "MortgageRecord",
    "TaxRecord",
    "CourtCase",
    "LienRecord",
    "RecordType",
    "CaseType",
    "CaseStatus",
]
