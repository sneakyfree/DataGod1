"""
Court System Base Class

Abstract base class for all court system scrapers. Defines the common interface
and shared functionality for extracting public court records.

Court systems vary significantly in:
- Access methods (web scraping, APIs, bulk data)
- Data availability (some records sealed/restricted)
- System vendors (Tyler, Thomson Reuters, custom)
- Fee structures (PACER charges per page, many state courts free)
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


class CourtType(Enum):
    """Types of courts."""

    # Federal
    FEDERAL_DISTRICT = "federal_district"
    FEDERAL_APPELLATE = "federal_appellate"
    FEDERAL_SUPREME = "federal_supreme"
    FEDERAL_BANKRUPTCY = "federal_bankruptcy"
    FEDERAL_MAGISTRATE = "federal_magistrate"

    # State
    STATE_SUPREME = "state_supreme"
    STATE_APPELLATE = "state_appellate"
    STATE_TRIAL = "state_trial"
    STATE_SUPERIOR = "state_superior"

    # County/Local
    COUNTY_CIVIL = "county_civil"
    COUNTY_CRIMINAL = "county_criminal"
    COUNTY_FAMILY = "county_family"
    COUNTY_PROBATE = "county_probate"
    COUNTY_JUVENILE = "county_juvenile"

    # Specialized
    SMALL_CLAIMS = "small_claims"
    TRAFFIC = "traffic"
    MUNICIPAL = "municipal"
    TAX_COURT = "tax_court"
    WORKERS_COMP = "workers_comp"

    # Administrative
    ADMIN_HEARING = "admin_hearing"
    PTAB = "ptab"  # Patent Trial and Appeal Board

    OTHER = "other"
    UNKNOWN = "unknown"


class CourtLevel(Enum):
    """Hierarchical level of court."""

    SUPREME = "supreme"
    APPELLATE = "appellate"
    TRIAL = "trial"
    LIMITED = "limited"  # Small claims, traffic, etc.
    ADMINISTRATIVE = "administrative"
    UNKNOWN = "unknown"


class CaseType(Enum):
    """Types of court cases."""

    # Civil
    CIVIL_GENERAL = "civil_general"
    CONTRACT = "contract"
    TORT = "tort"
    PROPERTY = "property"
    FORECLOSURE = "foreclosure"
    EVICTION = "eviction"
    LANDLORD_TENANT = "landlord_tenant"
    DEBT_COLLECTION = "debt_collection"
    PERSONAL_INJURY = "personal_injury"
    MEDICAL_MALPRACTICE = "medical_malpractice"
    PRODUCT_LIABILITY = "product_liability"
    EMPLOYMENT = "employment"
    DISCRIMINATION = "discrimination"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    ANTITRUST = "antitrust"
    SECURITIES = "securities"
    ENVIRONMENTAL = "environmental"

    # Criminal
    CRIMINAL_FELONY = "criminal_felony"
    CRIMINAL_MISDEMEANOR = "criminal_misdemeanor"
    CRIMINAL_INFRACTION = "criminal_infraction"
    DUI_DWI = "dui_dwi"
    DRUG_OFFENSE = "drug_offense"
    VIOLENT_CRIME = "violent_crime"
    PROPERTY_CRIME = "property_crime"
    WHITE_COLLAR = "white_collar"
    TRAFFIC_CRIMINAL = "traffic_criminal"

    # Family
    DIVORCE = "divorce"
    CHILD_CUSTODY = "child_custody"
    CHILD_SUPPORT = "child_support"
    ADOPTION = "adoption"
    GUARDIANSHIP = "guardianship"
    DOMESTIC_VIOLENCE = "domestic_violence"
    PATERNITY = "paternity"

    # Probate
    PROBATE_ESTATE = "probate_estate"
    PROBATE_TRUST = "probate_trust"
    CONSERVATORSHIP = "conservatorship"
    WILL_CONTEST = "will_contest"

    # Bankruptcy
    BANKRUPTCY_CH7 = "bankruptcy_ch7"
    BANKRUPTCY_CH11 = "bankruptcy_ch11"
    BANKRUPTCY_CH13 = "bankruptcy_ch13"

    # Other
    SMALL_CLAIMS = "small_claims"
    TRAFFIC = "traffic"
    TAX = "tax"
    ADMINISTRATIVE = "administrative"
    APPEAL = "appeal"

    OTHER = "other"
    UNKNOWN = "unknown"


class CaseStatus(Enum):
    """Status of a court case."""

    OPEN = "open"
    PENDING = "pending"
    ACTIVE = "active"
    STAYED = "stayed"
    SETTLED = "settled"
    DISMISSED = "dismissed"
    CLOSED = "closed"
    DISPOSED = "disposed"
    JUDGMENT_ENTERED = "judgment_entered"
    ON_APPEAL = "on_appeal"
    REOPENED = "reopened"
    TRANSFERRED = "transferred"
    CONSOLIDATED = "consolidated"
    SEALED = "sealed"
    EXPUNGED = "expunged"
    UNKNOWN = "unknown"


class PartyType(Enum):
    """Types of parties in court cases."""

    INDIVIDUAL = "individual"
    CORPORATION = "corporation"
    LLC = "llc"
    PARTNERSHIP = "partnership"
    TRUST = "trust"
    ESTATE = "estate"
    GOVERNMENT = "government"
    NONPROFIT = "nonprofit"
    UNKNOWN = "unknown"


class PartyRole(Enum):
    """Roles of parties in court cases."""

    # Civil
    PLAINTIFF = "plaintiff"
    DEFENDANT = "defendant"
    PETITIONER = "petitioner"
    RESPONDENT = "respondent"
    CROSS_PLAINTIFF = "cross_plaintiff"
    CROSS_DEFENDANT = "cross_defendant"
    THIRD_PARTY_PLAINTIFF = "third_party_plaintiff"
    THIRD_PARTY_DEFENDANT = "third_party_defendant"
    INTERVENOR = "intervenor"

    # Criminal
    PROSECUTION = "prosecution"
    ACCUSED = "accused"
    VICTIM = "victim"

    # Bankruptcy
    DEBTOR = "debtor"
    CREDITOR = "creditor"
    TRUSTEE = "trustee"

    # Family
    APPLICANT = "applicant"
    MINOR = "minor"
    GUARDIAN = "guardian"
    GUARDIAN_AD_LITEM = "guardian_ad_litem"

    # General
    APPELLANT = "appellant"
    APPELLEE = "appellee"
    WITNESS = "witness"
    ATTORNEY = "attorney"
    JUDGE = "judge"
    OTHER = "other"
    UNKNOWN = "unknown"


@dataclass
class CaseParty:
    """A party (person or entity) in a court case."""

    name: str
    role: PartyRole
    party_type: PartyType = PartyType.UNKNOWN
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    attorney_name: Optional[str] = None
    attorney_firm: Optional[str] = None
    attorney_bar_number: Optional[str] = None
    is_pro_se: bool = False  # Self-represented
    raw_name: Optional[str] = None


@dataclass
class CaseEvent:
    """An event/docket entry in a court case."""

    date: date
    description: str
    event_type: Optional[str] = None
    filed_by: Optional[str] = None
    judge: Optional[str] = None
    document_number: Optional[str] = None
    document_url: Optional[str] = None
    page_count: Optional[int] = None
    amount: Optional[float] = None  # For fee-related entries
    sequence_number: Optional[int] = None
    raw_text: Optional[str] = None


@dataclass
class CaseDocument:
    """A document filed in a court case."""

    document_number: str
    title: str
    filed_date: Optional[date] = None
    filed_by: Optional[str] = None
    document_type: Optional[str] = None
    page_count: Optional[int] = None
    url: Optional[str] = None
    is_sealed: bool = False
    is_restricted: bool = False
    description: Optional[str] = None
    attachments: List[str] = field(default_factory=list)


@dataclass
class CaseCharge:
    """A criminal charge in a court case."""

    charge_number: Optional[str] = None
    statute: Optional[str] = None
    description: str = ""
    charge_level: Optional[str] = None  # Felony, Misdemeanor, etc.
    charge_class: Optional[str] = None  # Class A, B, etc.
    offense_date: Optional[date] = None
    filing_date: Optional[date] = None
    disposition: Optional[str] = None
    disposition_date: Optional[date] = None
    sentence: Optional[str] = None
    fine_amount: Optional[float] = None
    counts: int = 1
    is_amended: bool = False
    is_dismissed: bool = False


@dataclass
class CourtCase:
    """A court case record."""

    # Core identifiers
    case_number: str
    court_name: str
    court_type: CourtType = CourtType.UNKNOWN
    court_level: CourtLevel = CourtLevel.UNKNOWN

    # Case info
    case_type: CaseType = CaseType.UNKNOWN
    case_type_raw: Optional[str] = None
    case_title: Optional[str] = None  # e.g., "Smith v. Jones"
    status: CaseStatus = CaseStatus.UNKNOWN

    # Dates
    filing_date: Optional[date] = None
    disposition_date: Optional[date] = None
    last_activity_date: Optional[date] = None

    # Parties
    parties: List[CaseParty] = field(default_factory=list)
    plaintiffs: List[str] = field(default_factory=list)
    defendants: List[str] = field(default_factory=list)

    # Docket/Events
    events: List[CaseEvent] = field(default_factory=list)
    documents: List[CaseDocument] = field(default_factory=list)

    # Criminal specific
    charges: List[CaseCharge] = field(default_factory=list)

    # Judgment/Disposition
    judgment_amount: Optional[float] = None
    judgment_type: Optional[str] = None
    disposition: Optional[str] = None

    # Judges/Officers
    judge: Optional[str] = None
    magistrate: Optional[str] = None

    # Location
    county: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    division: Optional[str] = None
    courtroom: Optional[str] = None

    # Related cases
    related_cases: List[str] = field(default_factory=list)
    consolidated_with: Optional[str] = None
    appealed_from: Optional[str] = None
    appealed_to: Optional[str] = None

    # Source
    source_url: Optional[str] = None
    source_system: Optional[str] = None

    # Metadata
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    is_sealed: bool = False
    has_restricted_docs: bool = False

    def get_plaintiffs(self) -> List[str]:
        """Get plaintiff names from parties."""
        plaintiff_roles = {
            PartyRole.PLAINTIFF,
            PartyRole.PETITIONER,
            PartyRole.APPELLANT,
            PartyRole.APPLICANT,
        }
        return [p.name for p in self.parties if p.role in plaintiff_roles]

    def get_defendants(self) -> List[str]:
        """Get defendant names from parties."""
        defendant_roles = {
            PartyRole.DEFENDANT,
            PartyRole.RESPONDENT,
            PartyRole.APPELLEE,
            PartyRole.ACCUSED,
        }
        return [p.name for p in self.parties if p.role in defendant_roles]


@dataclass
class SearchCriteria:
    """Criteria for searching court cases."""

    # Party search
    party_name: Optional[str] = None
    party_type: Optional[str] = None  # plaintiff, defendant, any

    # Case search
    case_number: Optional[str] = None
    case_types: List[CaseType] = field(default_factory=list)

    # Date range
    filed_start_date: Optional[date] = None
    filed_end_date: Optional[date] = None

    # Location
    court_name: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None

    # Status
    case_status: Optional[CaseStatus] = None
    include_closed: bool = True

    # Criminal specific
    charge_description: Optional[str] = None
    statute: Optional[str] = None

    # Attorney
    attorney_name: Optional[str] = None
    attorney_bar_number: Optional[str] = None

    # Pagination
    page_number: int = 1
    page_size: int = 25
    max_results: int = 500


@dataclass
class SearchResult:
    """Result of a court case search."""

    cases: List[CourtCase]
    total_count: int
    page_number: int
    page_size: int
    has_more: bool
    search_criteria: SearchCriteria
    search_time_ms: int = 0
    source_system: str = ""
    warnings: List[str] = field(default_factory=list)
    fees_incurred: float = 0.0  # For PACER searches


class CourtSystemBase(ABC):
    """
    Abstract base class for court system scrapers.

    Each court system implementation must override the abstract methods
    to handle the specific system's interface.
    """

    # Court information (override in subclasses)
    COURT_NAME: str = ""
    COURT_TYPE: CourtType = CourtType.UNKNOWN
    COURT_LEVEL: CourtLevel = CourtLevel.UNKNOWN
    STATE: str = ""
    COUNTY: str = ""

    # System information
    BASE_URL: str = ""
    SYSTEM_NAME: str = ""
    SYSTEM_VENDOR: str = ""  # Tyler, Thomson Reuters, etc.

    # Rate limiting
    REQUEST_DELAY: float = 1.0
    MAX_RETRIES: int = 3
    TIMEOUT: int = 30

    # Access
    REQUIRES_LOGIN: bool = False
    REQUIRES_PAYMENT: bool = False
    COST_PER_PAGE: float = 0.0  # PACER: $0.10/page

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the court system scraper."""
        self.session = session
        self._owns_session = session is None
        self._last_request_time: float = 0
        self._authenticated = False
        self._total_fees: float = 0.0

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

    def _normalize_name(self, name: str) -> str:
        """Normalize a party name."""
        if not name:
            return ""
        name = " ".join(name.split())
        # Handle common legal suffixes
        parts = []
        for part in name.split():
            if part.upper() in {
                "LLC",
                "LP",
                "LLP",
                "INC",
                "CORP",
                "CO",
                "LTD",
                "PC",
                "PA",
                "PLLC",
            }:
                parts.append(part.upper())
            elif part.upper() in {"II", "III", "IV", "JR", "SR", "ESQ"}:
                parts.append(part.upper())
            else:
                parts.append(part.title())
        return " ".join(parts)

    def _parse_case_type(self, raw_type: str) -> CaseType:
        """Parse a raw case type string to CaseType enum."""
        if not raw_type:
            return CaseType.UNKNOWN

        raw_type = raw_type.upper().strip()

        # Common mappings
        type_mappings = {
            # Civil
            "CV": CaseType.CIVIL_GENERAL,
            "CIVIL": CaseType.CIVIL_GENERAL,
            "CONTRACT": CaseType.CONTRACT,
            "TORT": CaseType.TORT,
            "PI": CaseType.PERSONAL_INJURY,
            "PERSONAL INJURY": CaseType.PERSONAL_INJURY,
            "FC": CaseType.FORECLOSURE,
            "FORECLOSURE": CaseType.FORECLOSURE,
            "EV": CaseType.EVICTION,
            "EVICTION": CaseType.EVICTION,
            "UNLAWFUL DETAINER": CaseType.EVICTION,
            "UD": CaseType.EVICTION,
            "LT": CaseType.LANDLORD_TENANT,
            "DEBT": CaseType.DEBT_COLLECTION,
            "COLLECTION": CaseType.DEBT_COLLECTION,
            # Criminal
            "CR": CaseType.CRIMINAL_FELONY,
            "CRIMINAL": CaseType.CRIMINAL_FELONY,
            "FELONY": CaseType.CRIMINAL_FELONY,
            "F": CaseType.CRIMINAL_FELONY,
            "M": CaseType.CRIMINAL_MISDEMEANOR,
            "MISD": CaseType.CRIMINAL_MISDEMEANOR,
            "MISDEMEANOR": CaseType.CRIMINAL_MISDEMEANOR,
            "DUI": CaseType.DUI_DWI,
            "DWI": CaseType.DUI_DWI,
            "TRAFFIC": CaseType.TRAFFIC,
            "TR": CaseType.TRAFFIC,
            # Family
            "DR": CaseType.DIVORCE,
            "DIVORCE": CaseType.DIVORCE,
            "DISSOLUTION": CaseType.DIVORCE,
            "CUSTODY": CaseType.CHILD_CUSTODY,
            "SUPPORT": CaseType.CHILD_SUPPORT,
            "DV": CaseType.DOMESTIC_VIOLENCE,
            "DOMESTIC": CaseType.DOMESTIC_VIOLENCE,
            # Probate
            "PB": CaseType.PROBATE_ESTATE,
            "PROBATE": CaseType.PROBATE_ESTATE,
            "ESTATE": CaseType.PROBATE_ESTATE,
            "GUARDIANSHIP": CaseType.GUARDIANSHIP,
            # Bankruptcy
            "BK": CaseType.BANKRUPTCY_CH7,
            "BANKRUPTCY": CaseType.BANKRUPTCY_CH7,
            "CH7": CaseType.BANKRUPTCY_CH7,
            "CH11": CaseType.BANKRUPTCY_CH11,
            "CH13": CaseType.BANKRUPTCY_CH13,
            # Other
            "SC": CaseType.SMALL_CLAIMS,
            "SMALL CLAIMS": CaseType.SMALL_CLAIMS,
            "APPEAL": CaseType.APPEAL,
            "AP": CaseType.APPEAL,
        }

        if raw_type in type_mappings:
            return type_mappings[raw_type]

        # Check partial matches
        for key, case_type in type_mappings.items():
            if key in raw_type:
                return case_type

        return CaseType.UNKNOWN

    def _parse_case_status(self, raw_status: str) -> CaseStatus:
        """Parse a raw case status string to CaseStatus enum."""
        if not raw_status:
            return CaseStatus.UNKNOWN

        raw_status = raw_status.upper().strip()

        status_mappings = {
            "OPEN": CaseStatus.OPEN,
            "PENDING": CaseStatus.PENDING,
            "ACTIVE": CaseStatus.ACTIVE,
            "CLOSED": CaseStatus.CLOSED,
            "DISPOSED": CaseStatus.DISPOSED,
            "DISMISSED": CaseStatus.DISMISSED,
            "SETTLED": CaseStatus.SETTLED,
            "JUDGMENT": CaseStatus.JUDGMENT_ENTERED,
            "JUDGMENT ENTERED": CaseStatus.JUDGMENT_ENTERED,
            "APPEAL": CaseStatus.ON_APPEAL,
            "ON APPEAL": CaseStatus.ON_APPEAL,
            "TRANSFERRED": CaseStatus.TRANSFERRED,
            "CONSOLIDATED": CaseStatus.CONSOLIDATED,
            "SEALED": CaseStatus.SEALED,
            "EXPUNGED": CaseStatus.EXPUNGED,
            "STAYED": CaseStatus.STAYED,
            "REOPENED": CaseStatus.REOPENED,
        }

        if raw_status in status_mappings:
            return status_mappings[raw_status]

        for key, status in status_mappings.items():
            if key in raw_status:
                return status

        return CaseStatus.UNKNOWN

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

        amount_str = amount_str.replace("$", "").replace(",", "").strip()

        try:
            return float(amount_str)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return None

    def get_total_fees(self) -> float:
        """Get total fees incurred (for paid systems like PACER)."""
        return self._total_fees

    # Abstract methods that must be implemented by each court system

    @abstractmethod
    async def search_by_party(
        self,
        party_name: str,
        party_type: str = "any",  # plaintiff, defendant, any
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        case_types: Optional[List[CaseType]] = None,
        include_closed: bool = True,
        max_results: int = 100,
    ) -> SearchResult:
        """
        Search for cases by party name.

        Args:
            party_name: Name to search
            party_type: Search plaintiff, defendant, or any
            filed_start_date: Start of filing date range
            filed_end_date: End of filing date range
            case_types: Filter by case types
            include_closed: Include closed cases
            max_results: Maximum results to return

        Returns:
            SearchResult with matching cases
        """
        pass

    @abstractmethod
    async def search_by_case_number(self, case_number: str) -> Optional[CourtCase]:
        """
        Search for a specific case by case number.

        Args:
            case_number: The case number

        Returns:
            CourtCase if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_case_detail(self, case_number: str) -> Optional[CourtCase]:
        """
        Get detailed information for a specific case including docket.

        Args:
            case_number: The case number

        Returns:
            CourtCase with full details, or None if not found
        """
        pass

    async def get_docket(self, case_number: str) -> List[CaseEvent]:
        """
        Get the docket/event list for a case.

        Default implementation calls get_case_detail and returns events.
        Override if the system provides a separate docket endpoint.

        Args:
            case_number: The case number

        Returns:
            List of CaseEvent entries
        """
        case = await self.get_case_detail(case_number)
        return case.events if case else []

    async def get_documents(self, case_number: str) -> List[CaseDocument]:
        """
        Get the document list for a case.

        Default implementation calls get_case_detail and returns documents.
        Override if the system provides a separate documents endpoint.

        Args:
            case_number: The case number

        Returns:
            List of CaseDocument entries
        """
        case = await self.get_case_detail(case_number)
        return case.documents if case else []

    async def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with the court system if required.

        Override in subclasses that require authentication.

        Args:
            username: Login username
            password: Login password

        Returns:
            True if authentication successful, False otherwise
        """
        if not self.REQUIRES_LOGIN:
            return True
        raise NotImplementedError(
            "This court requires authentication. Override authenticate() method."
        )

    def get_court_info(self) -> Dict[str, Any]:
        """Get information about this court system."""
        return {
            "court_name": self.COURT_NAME,
            "court_type": self.COURT_TYPE.value,
            "court_level": self.COURT_LEVEL.value,
            "state": self.STATE,
            "county": self.COUNTY,
            "base_url": self.BASE_URL,
            "system": self.SYSTEM_NAME,
            "vendor": self.SYSTEM_VENDOR,
            "requires_login": self.REQUIRES_LOGIN,
            "requires_payment": self.REQUIRES_PAYMENT,
            "cost_per_page": self.COST_PER_PAGE,
        }


# Synchronous wrapper functions


def search_party_sync(
    court: CourtSystemBase, party_name: str, **kwargs
) -> SearchResult:
    """Synchronous wrapper for search_by_party."""

    async def _search():
        async with court:
            return await court.search_by_party(party_name, **kwargs)

    return asyncio.run(_search())


def get_case_sync(court: CourtSystemBase, case_number: str) -> Optional[CourtCase]:
    """Synchronous wrapper for get_case_detail."""

    async def _get():
        async with court:
            return await court.get_case_detail(case_number)

    return asyncio.run(_get())
