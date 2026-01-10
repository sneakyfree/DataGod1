"""
County Recorder Base Class

Abstract base class for all county recorder scrapers. Defines the common interface
and shared functionality for extracting public records from county recorder offices.

Each county recorder office may use different systems:
- Tyler Technologies (Odyssey, Eagle, etc.)
- Granicus/Laserfiche
- AVID
- Landshark
- Custom county systems

This base class provides a unified interface regardless of the underlying system.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types of documents recorded in county recorder offices."""
    # Deeds
    WARRANTY_DEED = "warranty_deed"
    QUITCLAIM_DEED = "quitclaim_deed"
    GRANT_DEED = "grant_deed"
    BARGAIN_SALE_DEED = "bargain_sale_deed"
    SPECIAL_WARRANTY_DEED = "special_warranty_deed"
    TRUSTEES_DEED = "trustees_deed"
    SHERIFFS_DEED = "sheriffs_deed"
    TAX_DEED = "tax_deed"
    DEED_IN_LIEU = "deed_in_lieu"
    CORRECTION_DEED = "correction_deed"

    # Mortgages and Liens
    MORTGAGE = "mortgage"
    DEED_OF_TRUST = "deed_of_trust"
    MORTGAGE_RELEASE = "mortgage_release"
    MORTGAGE_ASSIGNMENT = "mortgage_assignment"
    MORTGAGE_MODIFICATION = "mortgage_modification"
    SUBORDINATION_AGREEMENT = "subordination_agreement"

    # Other Liens
    MECHANICS_LIEN = "mechanics_lien"
    MECHANICS_LIEN_RELEASE = "mechanics_lien_release"
    JUDGMENT_LIEN = "judgment_lien"
    JUDGMENT_SATISFACTION = "judgment_satisfaction"
    TAX_LIEN_FEDERAL = "tax_lien_federal"
    TAX_LIEN_STATE = "tax_lien_state"
    TAX_LIEN_RELEASE = "tax_lien_release"
    UCC_FINANCING = "ucc_financing"
    UCC_TERMINATION = "ucc_termination"
    UCC_AMENDMENT = "ucc_amendment"
    HOA_LIEN = "hoa_lien"
    CHILD_SUPPORT_LIEN = "child_support_lien"

    # Foreclosure Related
    LIS_PENDENS = "lis_pendens"
    NOTICE_OF_DEFAULT = "notice_of_default"
    NOTICE_OF_SALE = "notice_of_sale"
    TRUSTEES_DEED_UPON_SALE = "trustees_deed_upon_sale"

    # Easements and Restrictions
    EASEMENT = "easement"
    EASEMENT_RELEASE = "easement_release"
    RESTRICTIVE_COVENANT = "restrictive_covenant"
    CC_AND_RS = "cc_and_rs"

    # Vital Records
    MARRIAGE_LICENSE = "marriage_license"
    MARRIAGE_CERTIFICATE = "marriage_certificate"
    DEATH_CERTIFICATE = "death_certificate"
    BIRTH_CERTIFICATE = "birth_certificate"

    # Powers and Trusts
    POWER_OF_ATTORNEY = "power_of_attorney"
    REVOCATION_OF_POA = "revocation_of_poa"
    TRUST_CERTIFICATE = "trust_certificate"
    AFFIDAVIT_OF_TRUST = "affidavit_of_trust"

    # Military
    DD214 = "dd214"
    MILITARY_DISCHARGE = "military_discharge"

    # Maps and Plats
    PLAT_MAP = "plat_map"
    SUBDIVISION_MAP = "subdivision_map"
    PARCEL_MAP = "parcel_map"
    SURVEY = "survey"

    # Other
    AFFIDAVIT = "affidavit"
    DECLARATION = "declaration"
    AGREEMENT = "agreement"
    NOTICE = "notice"
    LEASE = "lease"
    OPTION_TO_PURCHASE = "option_to_purchase"
    MEMORANDUM = "memorandum"
    FICTITIOUS_BUSINESS_NAME = "fictitious_business_name"
    OTHER = "other"
    UNKNOWN = "unknown"


class DocumentStatus(Enum):
    """Status of a recorded document."""
    ACTIVE = "active"
    RELEASED = "released"
    SATISFIED = "satisfied"
    TERMINATED = "terminated"
    EXPIRED = "expired"
    AMENDED = "amended"
    SUPERSEDED = "superseded"
    VOID = "void"
    PENDING = "pending"
    UNKNOWN = "unknown"


class PartyRole(Enum):
    """Roles of parties in recorded documents."""
    # Deed parties
    GRANTOR = "grantor"
    GRANTEE = "grantee"

    # Mortgage parties
    MORTGAGOR = "mortgagor"
    MORTGAGEE = "mortgagee"
    TRUSTOR = "trustor"
    TRUSTEE = "trustee"
    BENEFICIARY = "beneficiary"

    # Lien parties
    LIENHOLDER = "lienholder"
    DEBTOR = "debtor"
    SECURED_PARTY = "secured_party"
    CLAIMANT = "claimant"

    # General
    BUYER = "buyer"
    SELLER = "seller"
    BORROWER = "borrower"
    LENDER = "lender"
    ASSIGNOR = "assignor"
    ASSIGNEE = "assignee"
    RELEASOR = "releasor"
    RELEASEE = "releasee"
    PRINCIPAL = "principal"
    AGENT = "agent"

    # Vital records
    SPOUSE_1 = "spouse_1"
    SPOUSE_2 = "spouse_2"
    DECEDENT = "decedent"
    INFORMANT = "informant"

    # Other
    WITNESS = "witness"
    NOTARY = "notary"
    ATTORNEY = "attorney"
    PARTY = "party"
    OTHER = "other"
    UNKNOWN = "unknown"


@dataclass
class DocumentParty:
    """A party (person or entity) involved in a recorded document."""
    name: str
    role: PartyRole
    party_type: str = "unknown"  # individual, corporation, trust, llc, etc.
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    is_individual: bool = True
    raw_name: Optional[str] = None  # Original name before normalization


@dataclass
class LegalDescription:
    """Legal description of a property."""
    full_description: str
    parcel_number: Optional[str] = None
    apn: Optional[str] = None  # Assessor's Parcel Number
    lot: Optional[str] = None
    block: Optional[str] = None
    subdivision: Optional[str] = None
    section: Optional[str] = None
    township: Optional[str] = None
    range: Optional[str] = None
    tract: Optional[str] = None
    unit: Optional[str] = None  # For condos
    book: Optional[str] = None
    page: Optional[str] = None
    property_address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None


@dataclass
class RecordedDocument:
    """A document recorded in the county recorder's office."""
    # Core identifiers
    document_number: str
    instrument_number: Optional[str] = None
    book: Optional[str] = None
    page: Optional[str] = None

    # Document info
    document_type: DocumentType = DocumentType.UNKNOWN
    document_type_raw: Optional[str] = None  # Original type string from source
    status: DocumentStatus = DocumentStatus.UNKNOWN

    # Dates
    recorded_date: Optional[date] = None
    execution_date: Optional[date] = None  # Date document was signed
    effective_date: Optional[date] = None

    # Parties
    parties: List[DocumentParty] = field(default_factory=list)
    grantors: List[str] = field(default_factory=list)  # Convenience lists
    grantees: List[str] = field(default_factory=list)

    # Property info
    legal_descriptions: List[LegalDescription] = field(default_factory=list)
    property_addresses: List[str] = field(default_factory=list)
    parcels: List[str] = field(default_factory=list)

    # Financial info
    consideration: Optional[float] = None  # Sale price or loan amount
    transfer_tax: Optional[float] = None
    documentary_stamps: Optional[float] = None

    # References
    related_documents: List[str] = field(default_factory=list)
    reference_numbers: List[str] = field(default_factory=list)
    case_number: Optional[str] = None  # For judgment liens, lis pendens

    # Source info
    county: str = ""
    state: str = ""
    fips_code: Optional[str] = None
    source_url: Optional[str] = None
    image_available: bool = False
    image_url: Optional[str] = None
    page_count: Optional[int] = None

    # Metadata
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    def get_grantors(self) -> List[str]:
        """Get all grantor names from parties."""
        grantor_roles = {PartyRole.GRANTOR, PartyRole.MORTGAGOR, PartyRole.TRUSTOR,
                        PartyRole.SELLER, PartyRole.ASSIGNOR, PartyRole.RELEASOR}
        return [p.name for p in self.parties if p.role in grantor_roles]

    def get_grantees(self) -> List[str]:
        """Get all grantee names from parties."""
        grantee_roles = {PartyRole.GRANTEE, PartyRole.MORTGAGEE, PartyRole.TRUSTEE,
                        PartyRole.BENEFICIARY, PartyRole.BUYER, PartyRole.ASSIGNEE,
                        PartyRole.RELEASEE, PartyRole.SECURED_PARTY}
        return [p.name for p in self.parties if p.role in grantee_roles]


@dataclass
class SearchCriteria:
    """Criteria for searching recorded documents."""
    # Name search
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    business_name: Optional[str] = None
    party_type: Optional[str] = None  # grantor, grantee, either

    # Date range
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Document search
    document_number: Optional[str] = None
    instrument_number: Optional[str] = None
    book: Optional[str] = None
    page: Optional[str] = None
    document_types: List[DocumentType] = field(default_factory=list)

    # Property search
    parcel_number: Optional[str] = None
    apn: Optional[str] = None
    property_address: Optional[str] = None
    subdivision: Optional[str] = None
    lot: Optional[str] = None
    block: Optional[str] = None
    section: Optional[str] = None
    township: Optional[str] = None
    range: Optional[str] = None

    # Pagination
    page_number: int = 1
    page_size: int = 50
    max_results: int = 1000


@dataclass
class SearchResult:
    """Result of a document search."""
    documents: List[RecordedDocument]
    total_count: int
    page_number: int
    page_size: int
    has_more: bool
    search_criteria: SearchCriteria
    search_time_ms: int = 0
    source_system: str = ""
    warnings: List[str] = field(default_factory=list)


class CountyRecorderBase(ABC):
    """
    Abstract base class for county recorder scrapers.

    Each county implementation must override the abstract methods to handle
    the specific system used by that county.
    """

    # County information (override in subclasses)
    COUNTY_NAME: str = ""
    STATE: str = ""
    STATE_ABBREV: str = ""
    FIPS_CODE: str = ""

    # System information
    BASE_URL: str = ""
    SYSTEM_NAME: str = ""  # e.g., "Tyler Odyssey", "AVID", "Landshark"

    # Rate limiting
    REQUEST_DELAY: float = 1.0  # Seconds between requests
    MAX_RETRIES: int = 3
    TIMEOUT: int = 30

    # Session configuration
    REQUIRES_LOGIN: bool = False
    REQUIRES_CAPTCHA: bool = False

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the county recorder scraper."""
        self.session = session
        self._owns_session = session is None
        self._last_request_time: float = 0
        self._authenticated = False

    async def __aenter__(self):
        """Async context manager entry."""
        if self._owns_session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT),
                headers=self._get_headers()
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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
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
        """
        Fetch a URL with rate limiting and retries.

        Returns:
            Tuple of (status_code, response_text)
        """
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
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

        raise RuntimeError(f"Failed to fetch {url} after {self.MAX_RETRIES} attempts")

    async def _fetch_json(self, url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Fetch a URL and parse JSON response."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit()

        async with self.session.request(method, url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()

    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content."""
        return BeautifulSoup(html, "html.parser")

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for consistent formatting."""
        if not name:
            return ""
        # Remove extra whitespace
        name = " ".join(name.split())
        # Convert to title case but preserve known acronyms
        parts = []
        for part in name.split():
            if part.upper() in {"LLC", "LP", "LLP", "INC", "CORP", "CO", "LTD", "NA", "FSB", "PC"}:
                parts.append(part.upper())
            elif part.upper() in {"II", "III", "IV", "JR", "SR"}:
                parts.append(part.upper())
            else:
                parts.append(part.title())
        return " ".join(parts)

    def _parse_document_type(self, raw_type: str) -> DocumentType:
        """Parse a raw document type string to DocumentType enum."""
        if not raw_type:
            return DocumentType.UNKNOWN

        raw_type = raw_type.upper().strip()

        # Mapping of common abbreviations and variations
        type_mappings = {
            # Deeds
            "WD": DocumentType.WARRANTY_DEED,
            "WARRANTY DEED": DocumentType.WARRANTY_DEED,
            "WARR DEED": DocumentType.WARRANTY_DEED,
            "QCD": DocumentType.QUITCLAIM_DEED,
            "QUIT CLAIM": DocumentType.QUITCLAIM_DEED,
            "QUITCLAIM": DocumentType.QUITCLAIM_DEED,
            "QUITCLAIM DEED": DocumentType.QUITCLAIM_DEED,
            "GD": DocumentType.GRANT_DEED,
            "GRANT DEED": DocumentType.GRANT_DEED,
            "TD": DocumentType.TRUSTEES_DEED,
            "TRUSTEE DEED": DocumentType.TRUSTEES_DEED,
            "TRUSTEES DEED": DocumentType.TRUSTEES_DEED,
            "SD": DocumentType.SHERIFFS_DEED,
            "SHERIFF DEED": DocumentType.SHERIFFS_DEED,
            "SHERIFFS DEED": DocumentType.SHERIFFS_DEED,
            "TAX DEED": DocumentType.TAX_DEED,
            "DEED": DocumentType.WARRANTY_DEED,  # Default deed type

            # Mortgages
            "MTG": DocumentType.MORTGAGE,
            "MORT": DocumentType.MORTGAGE,
            "MORTGAGE": DocumentType.MORTGAGE,
            "DOT": DocumentType.DEED_OF_TRUST,
            "DEED OF TRUST": DocumentType.DEED_OF_TRUST,
            "TRUST DEED": DocumentType.DEED_OF_TRUST,
            "REL": DocumentType.MORTGAGE_RELEASE,
            "RELEASE": DocumentType.MORTGAGE_RELEASE,
            "SATISFACTION": DocumentType.MORTGAGE_RELEASE,
            "SAT": DocumentType.MORTGAGE_RELEASE,
            "SATISFACTION OF MORTGAGE": DocumentType.MORTGAGE_RELEASE,
            "ASGN": DocumentType.MORTGAGE_ASSIGNMENT,
            "ASSIGNMENT": DocumentType.MORTGAGE_ASSIGNMENT,
            "ASSIGNMENT OF MORTGAGE": DocumentType.MORTGAGE_ASSIGNMENT,
            "MOD": DocumentType.MORTGAGE_MODIFICATION,
            "MODIFICATION": DocumentType.MORTGAGE_MODIFICATION,
            "LOAN MODIFICATION": DocumentType.MORTGAGE_MODIFICATION,

            # Liens
            "ML": DocumentType.MECHANICS_LIEN,
            "MECH LIEN": DocumentType.MECHANICS_LIEN,
            "MECHANICS LIEN": DocumentType.MECHANICS_LIEN,
            "MECHANIC LIEN": DocumentType.MECHANICS_LIEN,
            "CONSTRUCTION LIEN": DocumentType.MECHANICS_LIEN,
            "JL": DocumentType.JUDGMENT_LIEN,
            "JUDGMENT": DocumentType.JUDGMENT_LIEN,
            "JUDGEMENT": DocumentType.JUDGMENT_LIEN,
            "JUDGMENT LIEN": DocumentType.JUDGMENT_LIEN,
            "FTL": DocumentType.TAX_LIEN_FEDERAL,
            "FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
            "IRS LIEN": DocumentType.TAX_LIEN_FEDERAL,
            "STL": DocumentType.TAX_LIEN_STATE,
            "STATE TAX LIEN": DocumentType.TAX_LIEN_STATE,
            "TAX LIEN": DocumentType.TAX_LIEN_STATE,
            "UCC": DocumentType.UCC_FINANCING,
            "UCC1": DocumentType.UCC_FINANCING,
            "UCC-1": DocumentType.UCC_FINANCING,
            "UCC3": DocumentType.UCC_AMENDMENT,
            "UCC-3": DocumentType.UCC_AMENDMENT,
            "HOA LIEN": DocumentType.HOA_LIEN,

            # Foreclosure
            "LP": DocumentType.LIS_PENDENS,
            "LIS PENDENS": DocumentType.LIS_PENDENS,
            "NOD": DocumentType.NOTICE_OF_DEFAULT,
            "NOTICE OF DEFAULT": DocumentType.NOTICE_OF_DEFAULT,
            "NOS": DocumentType.NOTICE_OF_SALE,
            "NOTICE OF SALE": DocumentType.NOTICE_OF_SALE,
            "NOTICE OF TRUSTEE SALE": DocumentType.NOTICE_OF_SALE,
            "TDUS": DocumentType.TRUSTEES_DEED_UPON_SALE,
            "TRUSTEES DEED UPON SALE": DocumentType.TRUSTEES_DEED_UPON_SALE,

            # Easements
            "EASE": DocumentType.EASEMENT,
            "EASEMENT": DocumentType.EASEMENT,
            "CCR": DocumentType.CC_AND_RS,
            "CC&R": DocumentType.CC_AND_RS,
            "CC&RS": DocumentType.CC_AND_RS,
            "COVENANT": DocumentType.RESTRICTIVE_COVENANT,
            "RESTRICTION": DocumentType.RESTRICTIVE_COVENANT,

            # Vital
            "MAR": DocumentType.MARRIAGE_LICENSE,
            "MARRIAGE": DocumentType.MARRIAGE_LICENSE,
            "MARRIAGE LICENSE": DocumentType.MARRIAGE_LICENSE,
            "MARRIAGE CERTIFICATE": DocumentType.MARRIAGE_CERTIFICATE,
            "DEATH": DocumentType.DEATH_CERTIFICATE,
            "DEATH CERTIFICATE": DocumentType.DEATH_CERTIFICATE,

            # Powers
            "POA": DocumentType.POWER_OF_ATTORNEY,
            "POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,

            # Maps
            "PLAT": DocumentType.PLAT_MAP,
            "PLAT MAP": DocumentType.PLAT_MAP,
            "SUBDIVISION": DocumentType.SUBDIVISION_MAP,
            "SUBDIVISION MAP": DocumentType.SUBDIVISION_MAP,
            "PARCEL MAP": DocumentType.PARCEL_MAP,
            "SURVEY": DocumentType.SURVEY,

            # Other
            "AFF": DocumentType.AFFIDAVIT,
            "AFFIDAVIT": DocumentType.AFFIDAVIT,
            "FBN": DocumentType.FICTITIOUS_BUSINESS_NAME,
            "FICTITIOUS BUSINESS NAME": DocumentType.FICTITIOUS_BUSINESS_NAME,
            "DBA": DocumentType.FICTITIOUS_BUSINESS_NAME,
            "LEASE": DocumentType.LEASE,
            "OPTION": DocumentType.OPTION_TO_PURCHASE,
            "NOTICE": DocumentType.NOTICE,
            "MEMO": DocumentType.MEMORANDUM,
            "MEMORANDUM": DocumentType.MEMORANDUM,
        }

        # Check exact match first
        if raw_type in type_mappings:
            return type_mappings[raw_type]

        # Check partial matches
        for key, doc_type in type_mappings.items():
            if key in raw_type:
                return doc_type

        return DocumentType.UNKNOWN

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string to a date object."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # Common date formats
        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%y",
            "%m-%d-%y",
            "%d-%b-%Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse a monetary amount string to a float."""
        if not amount_str:
            return None

        # Remove currency symbols and commas
        amount_str = amount_str.replace("$", "").replace(",", "").strip()

        try:
            return float(amount_str)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return None

    # Abstract methods that must be implemented by each county

    @abstractmethod
    async def search_by_name(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        party_type: str = "either",  # grantor, grantee, either
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        document_types: Optional[List[DocumentType]] = None,
        max_results: int = 100
    ) -> SearchResult:
        """
        Search for documents by party name.

        Args:
            last_name: Last name or business name to search
            first_name: First name (optional, for individuals)
            party_type: Search grantor, grantee, or either
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            document_types: Filter by document types (optional)
            max_results: Maximum number of results to return

        Returns:
            SearchResult with matching documents
        """
        pass

    @abstractmethod
    async def search_by_document_number(
        self,
        document_number: str
    ) -> Optional[RecordedDocument]:
        """
        Search for a specific document by its recording number.

        Args:
            document_number: The document/instrument number

        Returns:
            RecordedDocument if found, None otherwise
        """
        pass

    @abstractmethod
    async def search_by_parcel(
        self,
        parcel_number: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        document_types: Optional[List[DocumentType]] = None,
        max_results: int = 100
    ) -> SearchResult:
        """
        Search for documents by parcel/APN number.

        Args:
            parcel_number: The parcel or APN number
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            document_types: Filter by document types (optional)
            max_results: Maximum number of results to return

        Returns:
            SearchResult with matching documents
        """
        pass

    @abstractmethod
    async def search_by_address(
        self,
        address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """
        Search for documents by property address.

        Args:
            address: Street address
            city: City name (optional)
            zip_code: ZIP code (optional)
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            max_results: Maximum number of results to return

        Returns:
            SearchResult with matching documents
        """
        pass

    @abstractmethod
    async def get_document_detail(
        self,
        document_number: str
    ) -> Optional[RecordedDocument]:
        """
        Get detailed information for a specific document.

        Args:
            document_number: The document/instrument number

        Returns:
            RecordedDocument with full details, or None if not found
        """
        pass

    async def get_recent_recordings(
        self,
        days: int = 7,
        document_types: Optional[List[DocumentType]] = None,
        max_results: int = 100
    ) -> SearchResult:
        """
        Get recent recordings within the specified number of days.

        Default implementation uses date range search.
        Override if the county provides a specific API for recent recordings.

        Args:
            days: Number of days back to search
            document_types: Filter by document types (optional)
            max_results: Maximum number of results to return

        Returns:
            SearchResult with recent documents
        """
        from datetime import timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Use a common name that will return results (implementation-specific)
        return await self.search_by_name(
            last_name="BANK",  # Generic term likely to have recordings
            start_date=start_date,
            end_date=end_date,
            document_types=document_types,
            max_results=max_results
        )

    async def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with the recorder's system if required.

        Override in subclasses that require authentication.

        Args:
            username: Login username
            password: Login password

        Returns:
            True if authentication successful, False otherwise
        """
        if not self.REQUIRES_LOGIN:
            return True
        raise NotImplementedError("This county requires authentication. Override authenticate() method.")

    def get_county_info(self) -> Dict[str, Any]:
        """Get information about this county recorder."""
        return {
            "county": self.COUNTY_NAME,
            "state": self.STATE,
            "state_abbrev": self.STATE_ABBREV,
            "fips_code": self.FIPS_CODE,
            "base_url": self.BASE_URL,
            "system": self.SYSTEM_NAME,
            "requires_login": self.REQUIRES_LOGIN,
            "requires_captcha": self.REQUIRES_CAPTCHA,
        }


# Synchronous wrapper functions for non-async consumers

def search_name_sync(
    recorder: CountyRecorderBase,
    last_name: str,
    first_name: Optional[str] = None,
    **kwargs
) -> SearchResult:
    """Synchronous wrapper for search_by_name."""
    async def _search():
        async with recorder:
            return await recorder.search_by_name(last_name, first_name, **kwargs)
    return asyncio.run(_search())


def search_document_sync(
    recorder: CountyRecorderBase,
    document_number: str
) -> Optional[RecordedDocument]:
    """Synchronous wrapper for search_by_document_number."""
    async def _search():
        async with recorder:
            return await recorder.search_by_document_number(document_number)
    return asyncio.run(_search())


def search_parcel_sync(
    recorder: CountyRecorderBase,
    parcel_number: str,
    **kwargs
) -> SearchResult:
    """Synchronous wrapper for search_by_parcel."""
    async def _search():
        async with recorder:
            return await recorder.search_by_parcel(parcel_number, **kwargs)
    return asyncio.run(_search())


def get_document_detail_sync(
    recorder: CountyRecorderBase,
    document_number: str
) -> Optional[RecordedDocument]:
    """Synchronous wrapper for get_document_detail."""
    async def _search():
        async with recorder:
            return await recorder.get_document_detail(document_number)
    return asyncio.run(_search())
