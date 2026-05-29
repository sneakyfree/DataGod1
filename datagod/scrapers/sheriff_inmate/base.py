"""
Base classes for County Sheriff and Inmate Record Scrapers

This module provides abstract base classes and common data structures for
scraping inmate and jail information from county sheriff departments.

Data categories supported:
- Inmate records (current jail population)
- Booking records (arrest intake data)
- Charges and bonds
- Visitation information
- Arrest records
- Warrant records
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class InmateStatus(Enum):
    """Current status of an inmate."""

    IN_CUSTODY = "in_custody"
    RELEASED = "released"
    TRANSFERRED = "transferred"
    BONDED_OUT = "bonded_out"
    COURT_RELEASED = "court_released"
    SENTENCED = "sentenced"
    AWAITING_TRIAL = "awaiting_trial"
    AWAITING_TRANSFER = "awaiting_transfer"
    MEDICAL_HOLD = "medical_hold"
    IMMIGRATION_HOLD = "immigration_hold"
    FEDERAL_HOLD = "federal_hold"
    UNKNOWN = "unknown"


class ChargeType(Enum):
    """Type of criminal charge."""

    FELONY = "felony"
    MISDEMEANOR = "misdemeanor"
    INFRACTION = "infraction"
    VIOLATION = "violation"
    ORDINANCE = "ordinance"
    TRAFFIC = "traffic"
    WARRANT = "warrant"
    HOLD = "hold"
    UNKNOWN = "unknown"


class ChargeSeverity(Enum):
    """Severity/class of charge."""

    # Felony classes
    CAPITAL = "capital"
    FELONY_1 = "felony_1"
    FELONY_2 = "felony_2"
    FELONY_3 = "felony_3"
    FELONY_4 = "felony_4"
    FELONY_5 = "felony_5"
    FELONY_UNCLASSIFIED = "felony_unclassified"
    # Misdemeanor classes
    MISDEMEANOR_A = "misdemeanor_a"
    MISDEMEANOR_B = "misdemeanor_b"
    MISDEMEANOR_C = "misdemeanor_c"
    MISDEMEANOR_UNCLASSIFIED = "misdemeanor_unclassified"
    # Other
    PETTY = "petty"
    SUMMARY = "summary"
    UNKNOWN = "unknown"


class BondType(Enum):
    """Type of bond/bail."""

    CASH = "cash"
    SURETY = "surety"
    PROPERTY = "property"
    PERSONAL_RECOGNIZANCE = "personal_recognizance"
    SIGNATURE = "signature"
    NO_BOND = "no_bond"
    BOND_DENIED = "bond_denied"
    BAIL_BOND = "bail_bond"
    PRETRIAL_RELEASE = "pretrial_release"
    HOLD_WITHOUT_BOND = "hold_without_bond"
    UNKNOWN = "unknown"


class ReleaseType(Enum):
    """Type of release from custody."""

    BOND = "bond"
    CASH_BAIL = "cash_bail"
    TIME_SERVED = "time_served"
    CHARGES_DROPPED = "charges_dropped"
    ACQUITTED = "acquitted"
    TRANSFER = "transfer"
    COURT_ORDERED = "court_ordered"
    PAROLE = "parole"
    PROBATION = "probation"
    SENTENCE_COMPLETED = "sentence_completed"
    DIED_IN_CUSTODY = "died_in_custody"
    ESCAPE = "escape"
    OTHER = "other"


@dataclass
class InmateCharge:
    """Individual charge against an inmate."""

    charge_description: str
    charge_code: Optional[str] = None
    charge_type: Optional[ChargeType] = None
    severity: Optional[ChargeSeverity] = None
    statute: Optional[str] = None
    offense_date: Optional[date] = None
    arrest_date: Optional[date] = None
    filing_date: Optional[date] = None
    court: Optional[str] = None
    case_number: Optional[str] = None
    disposition: Optional[str] = None
    disposition_date: Optional[date] = None
    sentence: Optional[str] = None
    counts: int = 1
    is_felony: bool = False
    is_violent: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BondInformation:
    """Bond/bail information for an inmate."""

    bond_amount: Optional[Decimal] = None
    bond_type: Optional[BondType] = None
    bond_status: Optional[str] = None
    bond_date: Optional[date] = None
    bondsman_name: Optional[str] = None
    bondsman_company: Optional[str] = None
    total_bond: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    remaining_balance: Optional[Decimal] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisitationInfo:
    """Visitation schedule and rules for an inmate."""

    visitation_allowed: bool = True
    visitation_days: List[str] = field(default_factory=list)
    visitation_hours: Optional[str] = None
    next_visit_date: Optional[date] = None
    visit_duration_minutes: Optional[int] = None
    visitor_requirements: Optional[str] = None
    video_visitation: bool = False
    video_url: Optional[str] = None
    restrictions: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BookingRecord:
    """Booking/intake record for an inmate."""

    booking_number: str
    booking_date: datetime
    booking_facility: Optional[str] = None
    arresting_agency: Optional[str] = None
    arresting_officer: Optional[str] = None
    arrest_location: Optional[str] = None
    charges_at_booking: List[InmateCharge] = field(default_factory=list)
    release_date: Optional[datetime] = None
    release_type: Optional[ReleaseType] = None
    release_reason: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InmateRecord:
    """Complete inmate record with all available information."""

    # Identifiers
    inmate_id: str
    booking_number: Optional[str] = None
    jacket_number: Optional[str] = None

    # Personal information
    first_name: str = ""
    middle_name: Optional[str] = None
    last_name: str = ""
    suffix: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    ethnicity: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    eye_color: Optional[str] = None
    hair_color: Optional[str] = None
    complexion: Optional[str] = None
    scars_marks_tattoos: Optional[str] = None

    # Custody information
    status: InmateStatus = InmateStatus.UNKNOWN
    facility: Optional[str] = None
    housing_location: Optional[str] = None
    custody_level: Optional[str] = None
    classification: Optional[str] = None

    # Booking information
    booking_date: Optional[datetime] = None
    arrest_date: Optional[date] = None
    scheduled_release: Optional[date] = None
    actual_release: Optional[datetime] = None
    release_type: Optional[ReleaseType] = None

    # Charges and bonds
    charges: List[InmateCharge] = field(default_factory=list)
    bond_info: Optional[BondInformation] = None
    total_bond_amount: Optional[Decimal] = None
    bond_eligible: bool = True

    # Booking history
    booking_history: List[BookingRecord] = field(default_factory=list)

    # Visitation
    visitation: Optional[VisitationInfo] = None

    # Mugshot
    mugshot_url: Optional[str] = None
    mugshot_date: Optional[date] = None

    # Holds
    holds: List[str] = field(default_factory=list)
    detainers: List[str] = field(default_factory=list)

    # Location/jurisdiction
    county: str = ""
    state: str = ""

    # Source information
    source_url: Optional[str] = None
    source_system: Optional[str] = None
    last_updated: Optional[datetime] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        """Get full name of inmate."""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(parts)

    @property
    def felony_count(self) -> int:
        """Count number of felony charges."""
        return sum(
            1 for c in self.charges if c.is_felony or c.charge_type == ChargeType.FELONY
        )

    @property
    def total_charges(self) -> int:
        """Count total number of charges."""
        return sum(c.counts for c in self.charges)


@dataclass
class ArrestRecord:
    """Public arrest record (may not result in incarceration)."""

    arrest_id: str
    arrest_date: date
    arrest_time: Optional[time] = None
    first_name: str = ""
    last_name: str = ""
    middle_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    arresting_agency: Optional[str] = None
    arresting_officer: Optional[str] = None
    arrest_location: Optional[str] = None
    charges: List[InmateCharge] = field(default_factory=list)
    disposition: Optional[str] = None
    released: bool = False
    release_date: Optional[date] = None
    mugshot_url: Optional[str] = None
    county: str = ""
    state: str = ""
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WarrantRecord:
    """Active warrant record."""

    warrant_number: str
    warrant_type: str = ""  # Arrest, Bench, Capias, etc.
    warrant_date: Optional[date] = None
    first_name: str = ""
    last_name: str = ""
    middle_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    charges: List[str] = field(default_factory=list)
    bond_amount: Optional[Decimal] = None
    issuing_court: Optional[str] = None
    issuing_judge: Optional[str] = None
    case_number: Optional[str] = None
    status: str = "active"
    county: str = ""
    state: str = ""
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InmateSearchCriteria:
    """Search criteria for inmate lookup."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    age_range: Optional[Tuple[int, int]] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    booking_number: Optional[str] = None
    inmate_id: Optional[str] = None
    booking_date_start: Optional[date] = None
    booking_date_end: Optional[date] = None
    facility: Optional[str] = None
    status: Optional[InmateStatus] = None
    include_released: bool = False


@dataclass
class InmateSearchResult:
    """Result from an inmate search operation."""

    inmates: List[InmateRecord]
    total_count: int = 0
    page_number: int = 1
    page_size: int = 100
    has_more: bool = False
    search_criteria: Optional[InmateSearchCriteria] = None
    warnings: List[str] = field(default_factory=list)
    search_time_ms: Optional[int] = None
    source_system: Optional[str] = None


class SheriffInmateBase(ABC):
    """
    Abstract base class for county sheriff/inmate scrapers.

    Provides common functionality for searching inmate records,
    arrest records, and warrant databases maintained by county
    sheriff departments.
    """

    # Class-level constants (override in subclasses)
    COUNTY_NAME: str = ""
    STATE: str = ""
    FIPS_CODE: str = ""
    BASE_URL: str = ""
    SYSTEM_NAME: str = ""

    # Rate limiting
    REQUEST_DELAY: float = 1.0
    MAX_RETRIES: int = 3

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_request_time: float = 0

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; DataGod/1.0; Public Records Research)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            self.session = None

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        import time

        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    async def _fetch_html(self, url: str, params: Optional[Dict] = None) -> str:
        """Fetch HTML content from a URL."""
        await self._rate_limit()

        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        for attempt in range(self.MAX_RETRIES):
            try:
                async with self.session.get(url, params=params, timeout=30) as response:
                    response.raise_for_status()
                    return await response.text()
            except aiohttp.ClientError as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2**attempt)

        return ""

    async def _fetch_json(
        self, url: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Fetch JSON content from a URL."""
        await self._rate_limit()

        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        for attempt in range(self.MAX_RETRIES):
            try:
                async with self.session.get(url, params=params, timeout=30) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2**attempt)

        return {}

    async def _post_form(self, url: str, data: Dict[str, str]) -> str:
        """Submit form data and return response."""
        await self._rate_limit()

        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        for attempt in range(self.MAX_RETRIES):
            try:
                async with self.session.post(url, data=data, timeout=30) as response:
                    response.raise_for_status()
                    return await response.text()
            except aiohttp.ClientError as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2**attempt)

        return ""

    # Utility parsing methods

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string in various formats."""
        if not date_str or date_str.strip() == "":
            return None

        date_str = date_str.strip()

        formats = [
            "%m/%d/%Y",
            "%Y-%m-%d",
            "%m-%d-%Y",
            "%d-%b-%Y",
            "%B %d, %Y",
            "%m/%d/%y",
            "%Y%m%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse a datetime string in various formats."""
        if not datetime_str or datetime_str.strip() == "":
            return None

        datetime_str = datetime_str.strip()

        formats = [
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y %I:%M %p",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%m/%d/%y %H:%M",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue

        # Try parsing just the date
        d = self._parse_date(datetime_str)
        if d:
            return datetime.combine(d, time.min)

        return None

    def _parse_decimal(self, value_str: str) -> Optional[Decimal]:
        """Parse a decimal/money value."""
        if not value_str or value_str.strip() == "":
            return None

        # Remove currency symbols and commas
        cleaned = re.sub(r"[$,\s]", "", value_str.strip())

        try:
            return Decimal(cleaned)
        except Exception:
            return None

    def _parse_int(self, value_str: str) -> Optional[int]:
        """Parse an integer value."""
        if not value_str or value_str.strip() == "":
            return None

        cleaned = re.sub(r"[^\d-]", "", value_str.strip())

        try:
            return int(cleaned)
        except ValueError:
            return None

    def _parse_charge_type(self, charge_str: str) -> ChargeType:
        """Parse charge type from description."""
        if not charge_str:
            return ChargeType.UNKNOWN

        upper = charge_str.upper()

        if "FELONY" in upper or "(F)" in upper:
            return ChargeType.FELONY
        elif "MISDEMEANOR" in upper or "(M)" in upper:
            return ChargeType.MISDEMEANOR
        elif "INFRACTION" in upper or "(I)" in upper:
            return ChargeType.INFRACTION
        elif "TRAFFIC" in upper:
            return ChargeType.TRAFFIC
        elif "WARRANT" in upper:
            return ChargeType.WARRANT
        elif "HOLD" in upper:
            return ChargeType.HOLD
        elif "ORDINANCE" in upper:
            return ChargeType.ORDINANCE

        return ChargeType.UNKNOWN

    def _parse_charge_severity(self, charge_str: str) -> ChargeSeverity:
        """Parse charge severity/class from description."""
        if not charge_str:
            return ChargeSeverity.UNKNOWN

        upper = charge_str.upper()

        # Felony classes
        if "CAPITAL" in upper:
            return ChargeSeverity.CAPITAL
        elif "FELONY 1" in upper or "1ST DEG FEL" in upper or "F1" in upper:
            return ChargeSeverity.FELONY_1
        elif "FELONY 2" in upper or "2ND DEG FEL" in upper or "F2" in upper:
            return ChargeSeverity.FELONY_2
        elif "FELONY 3" in upper or "3RD DEG FEL" in upper or "F3" in upper:
            return ChargeSeverity.FELONY_3
        elif "FELONY 4" in upper or "F4" in upper:
            return ChargeSeverity.FELONY_4
        elif "FELONY 5" in upper or "F5" in upper:
            return ChargeSeverity.FELONY_5
        elif "FELONY" in upper:
            return ChargeSeverity.FELONY_UNCLASSIFIED
        # Misdemeanor classes
        elif "MISD A" in upper or "CLASS A MISD" in upper or "MA" in upper:
            return ChargeSeverity.MISDEMEANOR_A
        elif "MISD B" in upper or "CLASS B MISD" in upper or "MB" in upper:
            return ChargeSeverity.MISDEMEANOR_B
        elif "MISD C" in upper or "CLASS C MISD" in upper or "MC" in upper:
            return ChargeSeverity.MISDEMEANOR_C
        elif "MISDEMEANOR" in upper:
            return ChargeSeverity.MISDEMEANOR_UNCLASSIFIED

        return ChargeSeverity.UNKNOWN

    def _parse_bond_type(self, bond_str: str) -> BondType:
        """Parse bond type from description."""
        if not bond_str:
            return BondType.UNKNOWN

        upper = bond_str.upper()

        if "CASH" in upper:
            return BondType.CASH
        elif "SURETY" in upper:
            return BondType.SURETY
        elif "PROPERTY" in upper:
            return BondType.PROPERTY
        elif (
            "PR" in upper
            or "PERSONAL" in upper
            or "ROR" in upper
            or "RECOGNIZANCE" in upper
        ):
            return BondType.PERSONAL_RECOGNIZANCE
        elif "SIGNATURE" in upper:
            return BondType.SIGNATURE
        elif "NO BOND" in upper or "NONE" in upper:
            return BondType.NO_BOND
        elif "DENIED" in upper:
            return BondType.BOND_DENIED
        elif "HOLD" in upper or "WITHOUT" in upper:
            return BondType.HOLD_WITHOUT_BOND
        elif "PRETRIAL" in upper:
            return BondType.PRETRIAL_RELEASE

        return BondType.BAIL_BOND

    def _parse_inmate_status(self, status_str: str) -> InmateStatus:
        """Parse inmate status from description."""
        if not status_str:
            return InmateStatus.UNKNOWN

        upper = status_str.upper()

        if "RELEASED" in upper or "DISCHARGED" in upper:
            return InmateStatus.RELEASED
        elif "BOND" in upper or "BAIL" in upper:
            return InmateStatus.BONDED_OUT
        elif "TRANSFER" in upper:
            return InmateStatus.TRANSFERRED
        elif "SENTENCED" in upper:
            return InmateStatus.SENTENCED
        elif "AWAITING" in upper and "TRIAL" in upper:
            return InmateStatus.AWAITING_TRIAL
        elif "CUSTODY" in upper or "INCARCERATED" in upper or "ACTIVE" in upper:
            return InmateStatus.IN_CUSTODY
        elif "MEDICAL" in upper:
            return InmateStatus.MEDICAL_HOLD
        elif "IMMIGRATION" in upper or "ICE" in upper:
            return InmateStatus.IMMIGRATION_HOLD
        elif "FEDERAL" in upper:
            return InmateStatus.FEDERAL_HOLD

        return InmateStatus.IN_CUSTODY

    def _is_violent_charge(self, charge_desc: str) -> bool:
        """Determine if a charge is violent."""
        if not charge_desc:
            return False

        violent_keywords = [
            "MURDER",
            "HOMICIDE",
            "MANSLAUGHTER",
            "ASSAULT",
            "BATTERY",
            "ROBBERY",
            "RAPE",
            "SEXUAL ASSAULT",
            "KIDNAP",
            "ARSON",
            "CARJACK",
            "WEAPON",
            "FIREARM",
            "SHOOTING",
            "STAB",
            "DOMESTIC VIOLENCE",
            "DV",
            "AGGRAVATED",
            "ARMED",
            "DEADLY",
            "VIOLENT",
        ]

        upper = charge_desc.upper()
        return any(kw in upper for kw in violent_keywords)

    # Abstract methods (must be implemented by subclasses)

    @abstractmethod
    async def search_inmates(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        include_released: bool = False,
        max_results: int = 100,
    ) -> InmateSearchResult:
        """Search for inmates by name and other criteria."""
        pass

    @abstractmethod
    async def get_inmate_detail(self, inmate_id: str) -> Optional[InmateRecord]:
        """Get detailed information for a specific inmate."""
        pass

    async def search_by_booking_number(
        self, booking_number: str
    ) -> Optional[InmateRecord]:
        """Search for an inmate by booking number."""
        # Default implementation - override if direct lookup available
        results = await self.search_inmates(
            last_name="", first_name="", include_released=True, max_results=1
        )
        # Try to find matching booking
        for inmate in results.inmates:
            if inmate.booking_number == booking_number:
                return await self.get_inmate_detail(inmate.inmate_id)
        return None

    async def get_current_inmates(
        self, facility: Optional[str] = None, max_results: int = 500
    ) -> InmateSearchResult:
        """Get list of current inmates (jail roster)."""
        # Default implementation returns empty - override for systems with roster
        return InmateSearchResult(
            inmates=[],
            total_count=0,
            warnings=["Jail roster not available for this jurisdiction"],
        )

    async def search_warrants(
        self, last_name: str, first_name: Optional[str] = None, max_results: int = 100
    ) -> List[WarrantRecord]:
        """Search for active warrants by name."""
        # Default returns empty - override for systems with warrant search
        return []

    async def search_arrests(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100,
    ) -> List[ArrestRecord]:
        """Search for arrest records by name and date range."""
        # Default returns empty - override for systems with arrest log
        return []
