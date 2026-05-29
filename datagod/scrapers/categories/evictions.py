"""
Eviction Records Scraper Module

Provides comprehensive access to eviction records across US jurisdictions:
- Unlawful Detainer filings
- Forcible Entry and Detainer (FED)
- Summary Ejectment
- Eviction judgments
- Writs of Possession/Restitution

Eviction data comes from:
- County Civil Courts
- District Courts
- Small Claims Courts
- Justice of the Peace Courts

Uses async/aiohttp for efficient multi-source queries.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class EvictionType(Enum):
    """Types of eviction cases"""

    UNLAWFUL_DETAINER = "unlawful_detainer"
    FORCIBLE_ENTRY_DETAINER = "forcible_entry_detainer"
    SUMMARY_EJECTMENT = "summary_ejectment"
    HOLDOVER = "holdover"
    NONPAYMENT = "nonpayment"
    LEASE_VIOLATION = "lease_violation"
    NUISANCE = "nuisance"
    ILLEGAL_USE = "illegal_use"
    NO_FAULT = "no_fault"
    OWNER_MOVE_IN = "owner_move_in"
    DEMOLITION = "demolition"
    COMMERCIAL = "commercial_eviction"
    UNKNOWN = "unknown"


class CaseStatus(Enum):
    """Eviction case status values"""

    FILED = "filed"
    SERVED = "served"
    HEARING_SCHEDULED = "hearing_scheduled"
    JUDGMENT_PLAINTIFF = "judgment_for_plaintiff"
    JUDGMENT_DEFENDANT = "judgment_for_defendant"
    DEFAULT_JUDGMENT = "default_judgment"
    STIPULATED = "stipulated"
    DISMISSED = "dismissed"
    DISMISSED_WITH_PREJUDICE = "dismissed_with_prejudice"
    DISMISSED_WITHOUT_PREJUDICE = "dismissed_without_prejudice"
    SETTLED = "settled"
    WRIT_ISSUED = "writ_issued"
    WRIT_EXECUTED = "writ_executed"
    APPEALED = "appealed"
    SEALED = "sealed"
    UNKNOWN = "unknown"


class PartyRole(Enum):
    """Roles of parties in eviction case"""

    PLAINTIFF = "plaintiff"  # Landlord/Property owner
    DEFENDANT = "defendant"  # Tenant
    ATTORNEY_PLAINTIFF = "attorney_plaintiff"
    ATTORNEY_DEFENDANT = "attorney_defendant"
    PROPERTY_MANAGER = "property_manager"
    UNKNOWN = "unknown"


@dataclass
class EvictionParty:
    """Party in an eviction case"""

    name: str
    role: PartyRole
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    is_business: bool = False
    attorney_name: Optional[str] = None
    attorney_bar_number: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role.value,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "phone": self.phone,
            "is_business": self.is_business,
            "attorney_name": self.attorney_name,
            "attorney_bar_number": self.attorney_bar_number,
        }


@dataclass
class EvictionEvent:
    """Event/hearing in eviction case timeline"""

    event_date: date
    event_type: str
    description: Optional[str] = None
    result: Optional[str] = None
    judge_name: Optional[str] = None
    courtroom: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_date": self.event_date.isoformat(),
            "event_type": self.event_type,
            "description": self.description,
            "result": self.result,
            "judge_name": self.judge_name,
            "courtroom": self.courtroom,
        }


@dataclass
class EvictionJudgment:
    """Judgment details for eviction case"""

    judgment_date: date
    judgment_type: str  # for_plaintiff, for_defendant, default, stipulated
    possession_granted: bool = False
    monetary_amount: Optional[float] = None
    rent_owed: Optional[float] = None
    damages: Optional[float] = None
    attorney_fees: Optional[float] = None
    court_costs: Optional[float] = None
    stay_granted: bool = False
    stay_expiration: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "judgment_date": self.judgment_date.isoformat(),
            "judgment_type": self.judgment_type,
            "possession_granted": self.possession_granted,
            "monetary_amount": self.monetary_amount,
            "rent_owed": self.rent_owed,
            "damages": self.damages,
            "attorney_fees": self.attorney_fees,
            "court_costs": self.court_costs,
            "stay_granted": self.stay_granted,
            "stay_expiration": (
                self.stay_expiration.isoformat() if self.stay_expiration else None
            ),
        }


@dataclass
class EvictionRecord:
    """Represents an eviction case record"""

    # Case identifiers
    case_number: str
    state: str
    county: str
    filing_date: date
    court_name: str

    # Property info
    property_address: Optional[str] = None
    property_city: Optional[str] = None
    property_zip: Optional[str] = None
    property_type: Optional[str] = None  # residential, commercial
    unit_number: Optional[str] = None

    # Case details
    eviction_type: EvictionType = EvictionType.UNKNOWN
    case_status: CaseStatus = CaseStatus.UNKNOWN
    cause_of_action: Optional[str] = None
    amount_claimed: Optional[float] = None
    rent_amount: Optional[float] = None

    # Parties
    parties: List[EvictionParty] = field(default_factory=list)

    # Timeline
    events: List[EvictionEvent] = field(default_factory=list)

    # Judgment
    judgment: Optional[EvictionJudgment] = None

    # Writ information
    writ_issued_date: Optional[date] = None
    writ_type: Optional[str] = None  # possession, restitution, execution
    writ_executed_date: Optional[date] = None
    lockout_date: Optional[date] = None

    # Metadata
    document_url: Optional[str] = None
    docket_url: Optional[str] = None
    source_url: str = ""
    source_system: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_number": self.case_number,
            "state": self.state,
            "county": self.county,
            "filing_date": self.filing_date.isoformat(),
            "court_name": self.court_name,
            "property_address": self.property_address,
            "property_city": self.property_city,
            "property_zip": self.property_zip,
            "property_type": self.property_type,
            "unit_number": self.unit_number,
            "eviction_type": self.eviction_type.value,
            "case_status": self.case_status.value,
            "cause_of_action": self.cause_of_action,
            "amount_claimed": self.amount_claimed,
            "rent_amount": self.rent_amount,
            "parties": [p.to_dict() for p in self.parties],
            "events": [e.to_dict() for e in self.events],
            "judgment": self.judgment.to_dict() if self.judgment else None,
            "writ_issued_date": (
                self.writ_issued_date.isoformat() if self.writ_issued_date else None
            ),
            "writ_type": self.writ_type,
            "writ_executed_date": (
                self.writ_executed_date.isoformat() if self.writ_executed_date else None
            ),
            "lockout_date": (
                self.lockout_date.isoformat() if self.lockout_date else None
            ),
            "document_url": self.document_url,
            "docket_url": self.docket_url,
            "source_url": self.source_url,
            "source_system": self.source_system,
            "fetched_at": self.fetched_at.isoformat(),
        }

    @property
    def plaintiff_name(self) -> Optional[str]:
        """Get primary plaintiff name."""
        for party in self.parties:
            if party.role == PartyRole.PLAINTIFF:
                return party.name
        return None

    @property
    def defendant_name(self) -> Optional[str]:
        """Get primary defendant name."""
        for party in self.parties:
            if party.role == PartyRole.DEFENDANT:
                return party.name
        return None


# State eviction configurations
STATE_EVICTION_CONFIGS: Dict[str, Dict[str, Any]] = {
    "CA": {
        "name": "California",
        "case_type": "Unlawful Detainer",
        "court_level": "Superior Court",
        "notice_days": {"nonpayment": 3, "lease_violation": 3, "no_fault": 60},
        "tenant_protections": True,
        "notes": "Strong tenant protections, AB 1482 rent control",
    },
    "TX": {
        "name": "Texas",
        "case_type": "Forcible Entry and Detainer",
        "court_level": "Justice of the Peace Court",
        "notice_days": {"nonpayment": 3, "lease_violation": 3},
        "tenant_protections": False,
        "notes": "Quick eviction process, JP Court jurisdiction",
    },
    "FL": {
        "name": "Florida",
        "case_type": "Eviction",
        "court_level": "County Court",
        "notice_days": {"nonpayment": 3, "lease_violation": 7},
        "tenant_protections": False,
        "notes": "Fast-track eviction process available",
    },
    "NY": {
        "name": "New York",
        "case_type": "Summary Proceeding",
        "court_level": "Housing Court / Civil Court",
        "notice_days": {"nonpayment": 14, "holdover": 30},
        "tenant_protections": True,
        "notes": "Strong tenant protections, rent stabilization",
    },
    "IL": {
        "name": "Illinois",
        "case_type": "Forcible Entry and Detainer",
        "court_level": "Circuit Court",
        "notice_days": {"nonpayment": 5, "lease_violation": 10},
        "tenant_protections": True,
        "notes": "CRLTO applies in Chicago",
    },
    "PA": {
        "name": "Pennsylvania",
        "case_type": "Landlord-Tenant Complaint",
        "court_level": "Magisterial District Court",
        "notice_days": {"nonpayment": 10, "lease_violation": 15},
        "tenant_protections": False,
        "notes": "Two-step eviction process",
    },
    "OH": {
        "name": "Ohio",
        "case_type": "Forcible Entry and Detainer",
        "court_level": "Municipal Court",
        "notice_days": {"nonpayment": 3, "lease_violation": 30},
        "tenant_protections": False,
        "notes": "Fast eviction timeline",
    },
    "GA": {
        "name": "Georgia",
        "case_type": "Dispossessory",
        "court_level": "Magistrate Court",
        "notice_days": {"nonpayment": 0, "lease_end": 60},
        "tenant_protections": False,
        "notes": "No notice required for nonpayment after demand",
    },
    "NC": {
        "name": "North Carolina",
        "case_type": "Summary Ejectment",
        "court_level": "Small Claims Court",
        "notice_days": {"nonpayment": 10, "lease_violation": 0},
        "tenant_protections": False,
        "notes": "Fast-track summary ejectment process",
    },
    "MI": {
        "name": "Michigan",
        "case_type": "Summary Proceedings",
        "court_level": "District Court",
        "notice_days": {"nonpayment": 7, "lease_violation": 30},
        "tenant_protections": False,
        "notes": "Summary proceedings in district court",
    },
    "NJ": {
        "name": "New Jersey",
        "case_type": "Summary Dispossess",
        "court_level": "Special Civil Part",
        "notice_days": {"nonpayment": 30, "lease_violation": 3},
        "tenant_protections": True,
        "notes": "Anti-eviction act protections",
    },
    "VA": {
        "name": "Virginia",
        "case_type": "Unlawful Detainer",
        "court_level": "General District Court",
        "notice_days": {"nonpayment": 5, "lease_violation": 30},
        "tenant_protections": False,
        "notes": "Pay or quit notice required",
    },
    "WA": {
        "name": "Washington",
        "case_type": "Unlawful Detainer",
        "court_level": "Superior Court",
        "notice_days": {"nonpayment": 14, "lease_violation": 10},
        "tenant_protections": True,
        "notes": "Tenant protections, just cause required in Seattle",
    },
    "AZ": {
        "name": "Arizona",
        "case_type": "Forcible Entry and Detainer",
        "court_level": "Justice Court",
        "notice_days": {"nonpayment": 5, "lease_violation": 10},
        "tenant_protections": False,
        "notes": "Fast eviction process",
    },
    "MA": {
        "name": "Massachusetts",
        "case_type": "Summary Process",
        "court_level": "Housing Court / District Court",
        "notice_days": {"nonpayment": 14, "lease_violation": 30},
        "tenant_protections": True,
        "notes": "Strong tenant protections, no-fault prohibited in some areas",
    },
    "CO": {
        "name": "Colorado",
        "case_type": "Forcible Entry and Detainer",
        "court_level": "County Court",
        "notice_days": {"nonpayment": 10, "lease_violation": 10},
        "tenant_protections": True,
        "notes": "Recent tenant protection laws",
    },
    "NV": {
        "name": "Nevada",
        "case_type": "Summary Eviction",
        "court_level": "Justice Court",
        "notice_days": {"nonpayment": 7, "lease_violation": 5},
        "tenant_protections": False,
        "notes": "Summary eviction process available",
    },
    "MD": {
        "name": "Maryland",
        "case_type": "Failure to Pay Rent / Tenant Holding Over",
        "court_level": "District Court",
        "notice_days": {"nonpayment": 10, "lease_end": 60},
        "tenant_protections": True,
        "notes": "Separate processes for rent and lease violations",
    },
}

# Add remaining states with default config
for state in [
    "AL",
    "AK",
    "AR",
    "CT",
    "DE",
    "HI",
    "ID",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NH",
    "NM",
    "ND",
    "OK",
    "OR",
    "RI",
    "SC",
    "SD",
    "TN",
    "UT",
    "VT",
    "WI",
    "WV",
    "WY",
    "DC",
]:
    if state not in STATE_EVICTION_CONFIGS:
        STATE_EVICTION_CONFIGS[state] = {
            "name": state,
            "case_type": "Eviction",
            "court_level": "District Court",
            "notice_days": {"nonpayment": 7, "lease_violation": 14},
            "tenant_protections": False,
        }


# County court search URLs
COUNTY_EVICTION_SOURCES: Dict[str, Dict[str, Any]] = {
    # California
    "CA_LOS_ANGELES": {
        "name": "Los Angeles County Superior Court",
        "url": "https://www.lacourt.org/casesummary/ui/",
        "api_available": False,
        "case_type": "UD",
    },
    "CA_SAN_DIEGO": {
        "name": "San Diego Superior Court",
        "url": "https://www.sdcourt.ca.gov/portal/page/portal/sdcourt/CivilCases",
        "api_available": False,
    },
    # Texas
    "TX_HARRIS": {
        "name": "Harris County Justice Courts",
        "url": "https://www.jp.hctx.net/evictions/",
        "api_available": True,
    },
    "TX_DALLAS": {
        "name": "Dallas County Justice Courts",
        "url": "https://justice.dallascounty.org/",
        "api_available": False,
    },
    # Florida
    "FL_MIAMI_DADE": {
        "name": "Miami-Dade County Clerk",
        "url": "https://www.miamidadeclerk.gov/ocs/",
        "api_available": True,
    },
    "FL_BROWARD": {
        "name": "Broward County Clerk",
        "url": "https://www.browardclerk.org/Web2/",
        "api_available": True,
    },
    # New York
    "NY_NEW_YORK": {
        "name": "NYC Housing Court",
        "url": "https://iapps.courts.state.ny.us/webcivil/FCASMain",
        "api_available": False,
    },
    # Illinois
    "IL_COOK": {
        "name": "Cook County Clerk of Court",
        "url": "https://casesearch.cookcountyclerkofcourt.org/",
        "api_available": True,
    },
    # Georgia
    "GA_FULTON": {
        "name": "Fulton County Magistrate Court",
        "url": "https://ody.fultoncountyga.gov/",
        "api_available": True,
    },
    # Nevada
    "NV_CLARK": {
        "name": "Las Vegas Justice Court",
        "url": "https://www.clarkcountycourts.us/ejc/",
        "api_available": True,
    },
}


class EvictionsAPI:
    """
    Unified Eviction Records API client.

    Provides access to eviction case data from county court systems.
    Handles various eviction case types across different state systems.

    Uses async/aiohttp for efficient multi-source queries.
    """

    CATEGORY = "evictions"
    DISPLAY_NAME = "Eviction Records"

    def __init__(self, timeout: int = 30):
        """
        Initialize eviction records API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request = 0.0
        self._rate_limit_delay = 1.5
        self.state_configs = STATE_EVICTION_CONFIGS
        self.county_sources = COUNTY_EVICTION_SOURCES
        logger.info("EvictionsAPI initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {
                "User-Agent": "DataGod/1.0 (Court Records Research)",
                "Accept": "text/html,application/xhtml+xml,application/json",
            }
            self._session = aiohttp.ClientSession(timeout=self.timeout, headers=headers)
        return self._session

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        import time

        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request = time.time()

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # ========== Main Search Methods ==========

    async def search_by_defendant(
        self,
        state: str,
        defendant_name: str,
        county: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50,
    ) -> List[EvictionRecord]:
        """
        Search eviction records by defendant (tenant) name.

        Args:
            state: Two-letter state code
            defendant_name: Defendant/tenant name
            county: County name (optional)
            date_from: Start date filter
            date_to: End date filter
            limit: Maximum results

        Returns:
            List of matching EvictionRecord objects
        """
        state = state.upper()
        logger.info(f"Searching evictions in {state} for defendant: {defendant_name}")

        await self._rate_limit()
        session = await self._get_session()

        if county:
            county_key = f"{state}_{county.upper().replace(' ', '_').replace('COUNTY', '').strip()}"
            if county_key in self.county_sources:
                return await self._search_county(
                    session,
                    county_key,
                    defendant_name=defendant_name,
                    date_from=date_from,
                    date_to=date_to,
                    limit=limit,
                )

        # Search major counties in state
        records = []
        state_counties = [
            k for k in self.county_sources.keys() if k.startswith(f"{state}_")
        ]

        for county_key in state_counties[:5]:
            county_records = await self._search_county(
                session,
                county_key,
                defendant_name=defendant_name,
                date_from=date_from,
                date_to=date_to,
                limit=limit // 5,
            )
            records.extend(county_records)

        return records[:limit]

    async def search_by_plaintiff(
        self,
        state: str,
        plaintiff_name: str,
        county: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50,
    ) -> List[EvictionRecord]:
        """
        Search eviction records by plaintiff (landlord) name.

        Args:
            state: Two-letter state code
            plaintiff_name: Plaintiff/landlord name
            county: County name (optional)
            date_from: Start date filter
            date_to: End date filter
            limit: Maximum results

        Returns:
            List of matching EvictionRecord objects
        """
        state = state.upper()
        logger.info(f"Searching evictions in {state} for plaintiff: {plaintiff_name}")

        await self._rate_limit()
        session = await self._get_session()

        if county:
            county_key = f"{state}_{county.upper().replace(' ', '_').replace('COUNTY', '').strip()}"
            if county_key in self.county_sources:
                return await self._search_county(
                    session,
                    county_key,
                    plaintiff_name=plaintiff_name,
                    date_from=date_from,
                    date_to=date_to,
                    limit=limit,
                )

        # Search major counties
        records = []
        state_counties = [
            k for k in self.county_sources.keys() if k.startswith(f"{state}_")
        ]

        for county_key in state_counties[:5]:
            county_records = await self._search_county(
                session,
                county_key,
                plaintiff_name=plaintiff_name,
                date_from=date_from,
                date_to=date_to,
                limit=limit // 5,
            )
            records.extend(county_records)

        return records[:limit]

    async def search_by_address(
        self, state: str, address: str, county: str = None, limit: int = 25
    ) -> List[EvictionRecord]:
        """
        Search eviction records by property address.

        Args:
            state: Two-letter state code
            address: Property address
            county: County name (optional)
            limit: Maximum results

        Returns:
            List of matching EvictionRecord objects
        """
        state = state.upper()
        logger.info(f"Searching evictions in {state} for address: {address}")

        await self._rate_limit()
        session = await self._get_session()

        if county:
            county_key = f"{state}_{county.upper().replace(' ', '_').replace('COUNTY', '').strip()}"
            if county_key in self.county_sources:
                return await self._search_county(
                    session, county_key, address=address, limit=limit
                )

        # Search major counties
        records = []
        state_counties = [
            k for k in self.county_sources.keys() if k.startswith(f"{state}_")
        ]

        for county_key in state_counties[:3]:
            county_records = await self._search_county(
                session, county_key, address=address, limit=limit // 3
            )
            records.extend(county_records)

        return records[:limit]

    async def search_by_case_number(
        self, state: str, county: str, case_number: str
    ) -> Optional[EvictionRecord]:
        """
        Get eviction case by case number.

        Args:
            state: Two-letter state code
            county: County name
            case_number: Case number

        Returns:
            EvictionRecord or None
        """
        state = state.upper()
        logger.info(f"Looking up eviction case {case_number} in {county}, {state}")

        await self._rate_limit()
        session = await self._get_session()

        county_key = (
            f"{state}_{county.upper().replace(' ', '_').replace('COUNTY', '').strip()}"
        )

        records = await self._search_county(
            session, county_key, case_number=case_number, limit=1
        )
        return records[0] if records else None

    async def search_recent_filings(
        self, state: str, county: str, days_back: int = 30, limit: int = 100
    ) -> List[EvictionRecord]:
        """
        Search recent eviction filings in a county.

        Args:
            state: Two-letter state code
            county: County name
            days_back: Number of days back to search
            limit: Maximum results

        Returns:
            List of EvictionRecord objects
        """
        state = state.upper()
        logger.info(f"Searching recent evictions in {county}, {state}")

        await self._rate_limit()
        session = await self._get_session()

        from datetime import timedelta

        date_from = date.today() - timedelta(days=days_back)

        county_key = (
            f"{state}_{county.upper().replace(' ', '_').replace('COUNTY', '').strip()}"
        )

        return await self._search_county(
            session, county_key, date_from=date_from, limit=limit
        )

    # ========== County-Specific Searches ==========

    async def _search_county(
        self,
        session: aiohttp.ClientSession,
        county_key: str,
        defendant_name: str = None,
        plaintiff_name: str = None,
        address: str = None,
        case_number: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50,
    ) -> List[EvictionRecord]:
        """Route to county-specific search implementation."""

        if county_key not in self.county_sources:
            return []

        config = self.county_sources[county_key]
        state = county_key.split("_")[0]
        county_name = (
            config.get("name", "")
            .replace(" County", "")
            .replace(" Superior Court", "")
            .replace(" Justice Courts", "")
        )

        # Route to specific implementations
        if county_key == "TX_HARRIS":
            return await self._search_harris_county(
                session,
                defendant_name,
                plaintiff_name,
                case_number,
                date_from,
                date_to,
                limit,
            )
        elif county_key == "FL_MIAMI_DADE":
            return await self._search_miami_dade(
                session,
                defendant_name,
                plaintiff_name,
                case_number,
                date_from,
                date_to,
                limit,
            )
        elif county_key == "IL_COOK":
            return await self._search_cook_county(
                session,
                defendant_name,
                plaintiff_name,
                case_number,
                date_from,
                date_to,
                limit,
            )
        elif county_key == "NV_CLARK":
            return await self._search_clark_county(
                session,
                defendant_name,
                plaintiff_name,
                case_number,
                date_from,
                date_to,
                limit,
            )
        elif county_key == "GA_FULTON":
            return await self._search_fulton_county(
                session,
                defendant_name,
                plaintiff_name,
                case_number,
                date_from,
                date_to,
                limit,
            )
        else:
            # Generic web scraper
            return await self._search_generic_court(
                session,
                county_key,
                config,
                defendant_name,
                plaintiff_name,
                address,
                case_number,
                limit,
            )

    async def _search_harris_county(
        self,
        session: aiohttp.ClientSession,
        defendant_name: str = None,
        plaintiff_name: str = None,
        case_number: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50,
    ) -> List[EvictionRecord]:
        """Search Harris County (Houston) Justice Court evictions."""
        url = "https://www.jp.hctx.net/evictions/search.asp"

        data = {}
        if defendant_name:
            data["defendant"] = defendant_name
        elif plaintiff_name:
            data["plaintiff"] = plaintiff_name
        elif case_number:
            data["casenum"] = case_number

        if date_from:
            data["startdate"] = date_from.strftime("%m/%d/%Y")
        if date_to:
            data["enddate"] = date_to.strftime("%m/%d/%Y")

        records = []

        try:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    html = await response.text()
                    records = self._parse_harris_results(html, limit)
        except Exception as e:
            logger.error(f"Harris County eviction search error: {e}")

        return records

    def _parse_harris_results(self, html: str, limit: int) -> List[EvictionRecord]:
        """Parse Harris County eviction search results."""
        records = []
        soup = BeautifulSoup(html, "html.parser")

        # Find result table
        table = soup.find("table", class_="results") or soup.find("table")
        if not table:
            return records

        rows = table.find_all("tr")[1 : limit + 1]  # Skip header

        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 5:
                try:
                    case_number = cells[0].get_text(strip=True)
                    filing_date = self._parse_date(cells[1].get_text(strip=True))
                    plaintiff = cells[2].get_text(strip=True)
                    defendant = cells[3].get_text(strip=True)
                    status = cells[4].get_text(strip=True) if len(cells) > 4 else ""

                    if filing_date:
                        record = EvictionRecord(
                            case_number=case_number,
                            state="TX",
                            county="Harris",
                            filing_date=filing_date,
                            court_name="Harris County Justice Court",
                            eviction_type=EvictionType.FORCIBLE_ENTRY_DETAINER,
                            case_status=self._parse_status(status),
                            parties=[
                                EvictionParty(name=plaintiff, role=PartyRole.PLAINTIFF),
                                EvictionParty(name=defendant, role=PartyRole.DEFENDANT),
                            ],
                            source_url="https://www.jp.hctx.net/evictions/",
                            source_system="Harris County JP Courts",
                            fetched_at=datetime.now(),
                        )
                        records.append(record)
                except Exception as e:
                    logger.warning(f"Error parsing Harris County row: {e}")

        return records

    async def _search_miami_dade(
        self,
        session: aiohttp.ClientSession,
        defendant_name: str = None,
        plaintiff_name: str = None,
        case_number: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50,
    ) -> List[EvictionRecord]:
        """Search Miami-Dade County evictions."""
        url = "https://www.miamidadeclerk.gov/ocs/Search.aspx"

        data = {
            "CaseType": "CC",  # County Civil (includes evictions)
        }
        if defendant_name:
            data["DefendantName"] = defendant_name
        elif plaintiff_name:
            data["PlaintiffName"] = plaintiff_name
        elif case_number:
            data["CaseNumber"] = case_number

        records = []

        try:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    html = await response.text()
                    records = self._parse_miami_dade_results(html, limit)
        except Exception as e:
            logger.error(f"Miami-Dade eviction search error: {e}")

        return records

    def _parse_miami_dade_results(self, html: str, limit: int) -> List[EvictionRecord]:
        """Parse Miami-Dade County eviction search results."""
        records = []
        soup = BeautifulSoup(html, "html.parser")

        rows = soup.select("table tr, .case-result")

        for row in rows[1 : limit + 1]:
            cells = row.find_all(["td", "span"])
            if len(cells) >= 4:
                try:
                    case_number = cells[0].get_text(strip=True)
                    # Filter for eviction cases (typically start with certain prefixes)
                    if not any(
                        prefix in case_number.upper() for prefix in ["CC", "EV", "SP"]
                    ):
                        continue

                    filing_date = self._parse_date(cells[1].get_text(strip=True))
                    parties_text = (
                        cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    )

                    if filing_date:
                        record = EvictionRecord(
                            case_number=case_number,
                            state="FL",
                            county="Miami-Dade",
                            filing_date=filing_date,
                            court_name="Miami-Dade County Court",
                            eviction_type=EvictionType.UNKNOWN,
                            source_url="https://www.miamidadeclerk.gov/",
                            source_system="Miami-Dade Clerk",
                            fetched_at=datetime.now(),
                        )
                        records.append(record)
                except Exception as e:
                    logger.warning(f"Error parsing Miami-Dade row: {e}")

        return records

    async def _search_cook_county(
        self,
        session: aiohttp.ClientSession,
        defendant_name: str = None,
        plaintiff_name: str = None,
        case_number: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50,
    ) -> List[EvictionRecord]:
        """Search Cook County (Chicago) evictions."""
        url = "https://casesearch.cookcountyclerkofcourt.org/CivilCaseSearchAPI.svc/SearchByCriteria"

        params = {
            "DivisionCode": "CV",  # Civil
            "CaseType": "EV",  # Eviction
        }
        if defendant_name:
            params["DefendantName"] = defendant_name
        elif plaintiff_name:
            params["PlaintiffName"] = plaintiff_name
        elif case_number:
            params["CaseNumber"] = case_number

        if date_from:
            params["FilingDateFrom"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            params["FilingDateTo"] = date_to.strftime("%Y-%m-%d")

        records = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "json" in content_type:
                        data = await response.json()
                        records = self._parse_cook_county_json(data, limit)
                    else:
                        html = await response.text()
                        records = self._parse_cook_county_html(html, limit)
        except Exception as e:
            logger.error(f"Cook County eviction search error: {e}")

        return records

    def _parse_cook_county_json(
        self, data: Dict[str, Any], limit: int
    ) -> List[EvictionRecord]:
        """Parse Cook County JSON results."""
        records = []

        cases = data.get("Cases", data.get("results", []))

        for case in cases[:limit]:
            try:
                filing_date = self._parse_date(case.get("FilingDate"))
                if not filing_date:
                    continue

                record = EvictionRecord(
                    case_number=case.get("CaseNumber", ""),
                    state="IL",
                    county="Cook",
                    filing_date=filing_date,
                    court_name="Cook County Circuit Court",
                    eviction_type=EvictionType.FORCIBLE_ENTRY_DETAINER,
                    case_status=self._parse_status(case.get("CaseStatus", "")),
                    parties=[
                        EvictionParty(
                            name=case.get("PlaintiffName", ""), role=PartyRole.PLAINTIFF
                        ),
                        EvictionParty(
                            name=case.get("DefendantName", ""), role=PartyRole.DEFENDANT
                        ),
                    ],
                    property_address=case.get("PropertyAddress"),
                    source_url="https://casesearch.cookcountyclerkofcourt.org/",
                    source_system="Cook County Clerk",
                    raw_data=case,
                    fetched_at=datetime.now(),
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Error parsing Cook County case: {e}")

        return records

    def _parse_cook_county_html(self, html: str, limit: int) -> List[EvictionRecord]:
        """Parse Cook County HTML results."""
        records = []
        soup = BeautifulSoup(html, "html.parser")

        rows = soup.select("table tr, .case-row")

        for row in rows[1 : limit + 1]:
            cells = row.find_all("td")
            if len(cells) >= 4:
                try:
                    case_number = cells[0].get_text(strip=True)
                    filing_date = self._parse_date(cells[1].get_text(strip=True))

                    if filing_date:
                        record = EvictionRecord(
                            case_number=case_number,
                            state="IL",
                            county="Cook",
                            filing_date=filing_date,
                            court_name="Cook County Circuit Court",
                            eviction_type=EvictionType.FORCIBLE_ENTRY_DETAINER,
                            source_url="https://casesearch.cookcountyclerkofcourt.org/",
                            source_system="Cook County Clerk",
                            fetched_at=datetime.now(),
                        )
                        records.append(record)
                except Exception:
                    pass

        return records

    async def _search_clark_county(
        self,
        session: aiohttp.ClientSession,
        defendant_name: str = None,
        plaintiff_name: str = None,
        case_number: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50,
    ) -> List[EvictionRecord]:
        """Search Clark County (Las Vegas) evictions."""
        url = "https://www.clarkcountycourts.us/ejc/search.php"

        data = {}
        if defendant_name:
            data["defendant"] = defendant_name
        elif plaintiff_name:
            data["plaintiff"] = plaintiff_name
        elif case_number:
            data["case_number"] = case_number

        records = []

        try:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    html = await response.text()
                    records = self._parse_clark_county_results(html, limit)
        except Exception as e:
            logger.error(f"Clark County eviction search error: {e}")

        return records

    def _parse_clark_county_results(
        self, html: str, limit: int
    ) -> List[EvictionRecord]:
        """Parse Clark County eviction search results."""
        records = []
        soup = BeautifulSoup(html, "html.parser")

        rows = soup.select("table tr, .search-result")

        for row in rows[1 : limit + 1]:
            cells = row.find_all("td")
            if len(cells) >= 3:
                try:
                    case_number = cells[0].get_text(strip=True)
                    filing_date = self._parse_date(cells[1].get_text(strip=True))

                    if filing_date:
                        record = EvictionRecord(
                            case_number=case_number,
                            state="NV",
                            county="Clark",
                            filing_date=filing_date,
                            court_name="Las Vegas Justice Court",
                            eviction_type=EvictionType.UNLAWFUL_DETAINER,
                            source_url="https://www.clarkcountycourts.us/",
                            source_system="Clark County Courts",
                            fetched_at=datetime.now(),
                        )
                        records.append(record)
                except Exception:
                    pass

        return records

    async def _search_fulton_county(
        self,
        session: aiohttp.ClientSession,
        defendant_name: str = None,
        plaintiff_name: str = None,
        case_number: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50,
    ) -> List[EvictionRecord]:
        """Search Fulton County (Atlanta) evictions."""
        url = "https://ody.fultoncountyga.gov/MagistrateCourt/search"

        params = {
            "caseType": "DISP",  # Dispossessory
        }
        if defendant_name:
            params["defendantName"] = defendant_name
        elif plaintiff_name:
            params["plaintiffName"] = plaintiff_name
        elif case_number:
            params["caseNumber"] = case_number

        records = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    records = self._parse_fulton_results(html, limit)
        except Exception as e:
            logger.error(f"Fulton County eviction search error: {e}")

        return records

    def _parse_fulton_results(self, html: str, limit: int) -> List[EvictionRecord]:
        """Parse Fulton County eviction search results."""
        records = []
        soup = BeautifulSoup(html, "html.parser")

        rows = soup.select("table tbody tr, .case-item")

        for row in rows[:limit]:
            cells = row.find_all("td")
            if len(cells) >= 4:
                try:
                    case_number = cells[0].get_text(strip=True)
                    filing_date = self._parse_date(cells[1].get_text(strip=True))
                    plaintiff = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    defendant = cells[3].get_text(strip=True) if len(cells) > 3 else ""

                    if filing_date:
                        record = EvictionRecord(
                            case_number=case_number,
                            state="GA",
                            county="Fulton",
                            filing_date=filing_date,
                            court_name="Fulton County Magistrate Court",
                            eviction_type=EvictionType.FORCIBLE_ENTRY_DETAINER,
                            parties=[
                                (
                                    EvictionParty(
                                        name=plaintiff, role=PartyRole.PLAINTIFF
                                    )
                                    if plaintiff
                                    else None
                                ),
                                (
                                    EvictionParty(
                                        name=defendant, role=PartyRole.DEFENDANT
                                    )
                                    if defendant
                                    else None
                                ),
                            ],
                            source_url="https://ody.fultoncountyga.gov/",
                            source_system="Fulton County Odyssey",
                            fetched_at=datetime.now(),
                        )
                        record.parties = [p for p in record.parties if p]
                        records.append(record)
                except Exception:
                    pass

        return records

    async def _search_generic_court(
        self,
        session: aiohttp.ClientSession,
        county_key: str,
        config: Dict[str, Any],
        defendant_name: str = None,
        plaintiff_name: str = None,
        address: str = None,
        case_number: str = None,
        limit: int = 50,
    ) -> List[EvictionRecord]:
        """Generic court search for unsupported counties."""
        url = config.get("url")
        if not url:
            return []

        records = []

        try:
            # Try common search patterns
            search_params = {}
            if defendant_name:
                search_params["defendant"] = defendant_name
            elif plaintiff_name:
                search_params["plaintiff"] = plaintiff_name
            elif case_number:
                search_params["case_number"] = case_number

            async with session.get(url, params=search_params) as response:
                if response.status == 200:
                    html = await response.text()
                    records = self._parse_generic_results(html, county_key, limit)
        except Exception as e:
            logger.warning(f"Generic court search error for {county_key}: {e}")

        return records

    def _parse_generic_results(
        self, html: str, county_key: str, limit: int
    ) -> List[EvictionRecord]:
        """Parse generic court search results."""
        records = []
        soup = BeautifulSoup(html, "html.parser")

        state = county_key.split("_")[0]
        county = (
            county_key.split("_", 1)[1].replace("_", " ").title()
            if "_" in county_key
            else ""
        )

        # Look for common table structures
        rows = soup.select("table tr, .result-row, .case-row")

        for row in rows[1 : limit + 1]:  # Skip header
            cells = row.find_all(["td", "div"])
            if len(cells) >= 2:
                try:
                    # Try to extract case number and date
                    text_content = [c.get_text(strip=True) for c in cells]

                    case_number = None
                    filing_date = None

                    for text in text_content:
                        # Look for case number patterns
                        if re.match(r"^[\dA-Z]{4,}-", text) or re.match(
                            r"^\d{2,4}[A-Z]{2}", text
                        ):
                            case_number = text
                        # Try to parse as date
                        parsed_date = self._parse_date(text)
                        if parsed_date:
                            filing_date = parsed_date

                    if case_number and filing_date:
                        record = EvictionRecord(
                            case_number=case_number,
                            state=state,
                            county=county,
                            filing_date=filing_date,
                            court_name=f"{county} County Court",
                            source_system="County Court",
                            fetched_at=datetime.now(),
                        )
                        records.append(record)
                except Exception:
                    continue

        return records

    # ========== Utility Methods ==========

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date from various formats."""
        if not date_str:
            return None

        if "T" in str(date_str):
            date_str = str(date_str).split("T")[0]

        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y%m%d",
            "%d-%b-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).strip(), fmt).date()
            except ValueError:
                continue

        return None

    def _parse_status(self, status_text: str) -> CaseStatus:
        """Parse case status from text."""
        if not status_text:
            return CaseStatus.UNKNOWN

        status_lower = status_text.lower().strip()

        if "filed" in status_lower:
            return CaseStatus.FILED
        elif "served" in status_lower:
            return CaseStatus.SERVED
        elif "hearing" in status_lower or "scheduled" in status_lower:
            return CaseStatus.HEARING_SCHEDULED
        elif "judgment" in status_lower:
            if "plaintiff" in status_lower:
                return CaseStatus.JUDGMENT_PLAINTIFF
            elif "defendant" in status_lower:
                return CaseStatus.JUDGMENT_DEFENDANT
            elif "default" in status_lower:
                return CaseStatus.DEFAULT_JUDGMENT
        elif "dismiss" in status_lower:
            if "with prejudice" in status_lower:
                return CaseStatus.DISMISSED_WITH_PREJUDICE
            elif "without prejudice" in status_lower:
                return CaseStatus.DISMISSED_WITHOUT_PREJUDICE
            return CaseStatus.DISMISSED
        elif "settled" in status_lower or "stipulat" in status_lower:
            return CaseStatus.SETTLED
        elif "writ" in status_lower:
            if "executed" in status_lower:
                return CaseStatus.WRIT_EXECUTED
            return CaseStatus.WRIT_ISSUED
        elif "appeal" in status_lower:
            return CaseStatus.APPEALED
        elif "sealed" in status_lower:
            return CaseStatus.SEALED

        return CaseStatus.UNKNOWN

    def _classify_eviction_type(self, cause_text: str) -> EvictionType:
        """Classify eviction type from cause of action."""
        if not cause_text:
            return EvictionType.UNKNOWN

        cause_lower = cause_text.lower()

        if (
            "nonpayment" in cause_lower
            or "non-payment" in cause_lower
            or "rent" in cause_lower
        ):
            return EvictionType.NONPAYMENT
        elif "holdover" in cause_lower:
            return EvictionType.HOLDOVER
        elif "lease violation" in cause_lower or "breach" in cause_lower:
            return EvictionType.LEASE_VIOLATION
        elif "nuisance" in cause_lower:
            return EvictionType.NUISANCE
        elif "illegal" in cause_lower:
            return EvictionType.ILLEGAL_USE
        elif "no fault" in cause_lower or "no-fault" in cause_lower:
            return EvictionType.NO_FAULT
        elif "owner move" in cause_lower or "omi" in cause_lower:
            return EvictionType.OWNER_MOVE_IN
        elif "demolition" in cause_lower:
            return EvictionType.DEMOLITION
        elif "commercial" in cause_lower:
            return EvictionType.COMMERCIAL
        elif "unlawful detainer" in cause_lower:
            return EvictionType.UNLAWFUL_DETAINER
        elif "forcible" in cause_lower:
            return EvictionType.FORCIBLE_ENTRY_DETAINER
        elif "summary ejectment" in cause_lower:
            return EvictionType.SUMMARY_EJECTMENT

        return EvictionType.UNKNOWN

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        states_with_protections = [
            s for s, c in self.state_configs.items() if c.get("tenant_protections")
        ]

        return {
            "category": self.CATEGORY,
            "display_name": self.DISPLAY_NAME,
            "total_states": len(self.state_configs),
            "states_with_tenant_protections": len(states_with_protections),
            "counties_with_sources": len(self.county_sources),
            "eviction_types": [t.value for t in EvictionType],
            "case_statuses": [s.value for s in CaseStatus],
        }


# ========== Synchronous Wrappers ==========


def search_evictions_by_defendant(
    defendant_name: str, state: str, county: str = None, limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search eviction records by defendant/tenant name (synchronous wrapper).

    Args:
        defendant_name: Defendant/tenant name
        state: Two-letter state code
        county: County name (optional)
        limit: Maximum results

    Returns:
        List of EvictionRecord dictionaries
    """

    async def _search():
        async with EvictionsAPI() as api:
            records = await api.search_by_defendant(
                state, defendant_name, county, limit=limit
            )
            return [r.to_dict() for r in records]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def search_evictions_by_plaintiff(
    plaintiff_name: str, state: str, county: str = None, limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search eviction records by plaintiff/landlord name (synchronous wrapper).

    Args:
        plaintiff_name: Plaintiff/landlord name
        state: Two-letter state code
        county: County name (optional)
        limit: Maximum results

    Returns:
        List of EvictionRecord dictionaries
    """

    async def _search():
        async with EvictionsAPI() as api:
            records = await api.search_by_plaintiff(
                state, plaintiff_name, county, limit=limit
            )
            return [r.to_dict() for r in records]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def search_evictions_by_address(
    address: str, state: str, county: str = None, limit: int = 25
) -> List[Dict[str, Any]]:
    """
    Search eviction records by property address (synchronous wrapper).

    Args:
        address: Property address
        state: Two-letter state code
        county: County name (optional)
        limit: Maximum results

    Returns:
        List of EvictionRecord dictionaries
    """

    async def _search():
        async with EvictionsAPI() as api:
            records = await api.search_by_address(state, address, county, limit)
            return [r.to_dict() for r in records]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def get_eviction_case(
    case_number: str, state: str, county: str
) -> Optional[Dict[str, Any]]:
    """
    Get eviction case by case number (synchronous wrapper).

    Args:
        case_number: Case number
        state: Two-letter state code
        county: County name

    Returns:
        EvictionRecord dictionary or None
    """

    async def _get():
        async with EvictionsAPI() as api:
            record = await api.search_by_case_number(state, county, case_number)
            return record.to_dict() if record else None

    try:
        return asyncio.run(_get())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())


def get_recent_evictions(
    state: str, county: str, days_back: int = 30, limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get recent eviction filings (synchronous wrapper).

    Args:
        state: Two-letter state code
        county: County name
        days_back: Number of days to search back
        limit: Maximum results

    Returns:
        List of EvictionRecord dictionaries
    """

    async def _search():
        async with EvictionsAPI() as api:
            records = await api.search_recent_filings(state, county, days_back, limit)
            return [r.to_dict() for r in records]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def get_state_eviction_info(state: str) -> Dict[str, Any]:
    """Get eviction process information for a state."""
    api = EvictionsAPI()
    config = api.state_configs.get(state.upper(), {})
    return {
        "state": state.upper(),
        "name": config.get("name", state),
        "case_type": config.get("case_type", "Eviction"),
        "court_level": config.get("court_level", "Court"),
        "notice_days": config.get("notice_days", {}),
        "tenant_protections": config.get("tenant_protections", False),
        "notes": config.get("notes", ""),
    }


def get_available_counties() -> Dict[str, List[str]]:
    """Get counties with eviction search support by state."""
    api = EvictionsAPI()
    result = {}
    for county_key in api.county_sources.keys():
        parts = county_key.split("_", 1)
        if len(parts) == 2:
            state, county = parts
            if state not in result:
                result[state] = []
            result[state].append(county.replace("_", " ").title())
    return result
