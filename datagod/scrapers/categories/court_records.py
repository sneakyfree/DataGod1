"""
Court Records Scraper Module

Provides unified access to court records across jurisdictions:
- Case search (civil, criminal, family, probate)
- Party search (plaintiff, defendant, petitioner)
- Judgment and lien search
- Court document retrieval

Supports:
- CourtListener / RECAP API (free federal court data)
- State court portals
- PACER (federal courts)
- County clerk sites

CourtListener API Documentation: https://www.courtlistener.com/api/rest-info/
"""

import asyncio
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlencode

import aiohttp

logger = logging.getLogger(__name__)


class CaseType(Enum):
    """Types of court cases"""

    CIVIL = "civil"
    CRIMINAL = "criminal"
    FAMILY = "family"
    PROBATE = "probate"
    BANKRUPTCY = "bankruptcy"
    SMALL_CLAIMS = "small_claims"
    TAX = "tax"
    TRAFFIC = "traffic"
    JUVENILE = "juvenile"
    APPELLATE = "appellate"
    UNKNOWN = "unknown"


class CaseStatus(Enum):
    """Case status values"""

    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    DISMISSED = "dismissed"
    SETTLED = "settled"
    APPEALED = "appealed"
    ON_HOLD = "on_hold"
    UNKNOWN = "unknown"


class PartyType(Enum):
    """Types of case parties"""

    PLAINTIFF = "plaintiff"
    DEFENDANT = "defendant"
    PETITIONER = "petitioner"
    RESPONDENT = "respondent"
    APPELLANT = "appellant"
    APPELLEE = "appellee"
    CREDITOR = "creditor"
    DEBTOR = "debtor"
    WITNESS = "witness"
    ATTORNEY = "attorney"
    JUDGE = "judge"
    OTHER = "other"


class CourtLevel(Enum):
    """Court levels"""

    FEDERAL_DISTRICT = "federal_district"
    FEDERAL_APPELLATE = "federal_appellate"
    FEDERAL_BANKRUPTCY = "federal_bankruptcy"
    SUPREME_COURT = "supreme_court"
    STATE_SUPREME = "state_supreme"
    STATE_APPELLATE = "state_appellate"
    STATE_TRIAL = "state_trial"
    COUNTY = "county"
    MUNICIPAL = "municipal"


@dataclass
class CaseParty:
    """Represents a party in a court case"""

    name: str
    party_type: PartyType
    party_id: Optional[str] = None
    address: Optional[str] = None
    attorney_name: Optional[str] = None
    attorney_firm: Optional[str] = None
    is_business: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "party_type": self.party_type.value,
            "party_id": self.party_id,
            "address": self.address,
            "attorney_name": self.attorney_name,
            "attorney_firm": self.attorney_firm,
            "is_business": self.is_business,
        }


@dataclass
class CourtCase:
    """Represents a court case record"""

    case_number: str
    case_type: CaseType
    court_name: str
    filing_date: Optional[date] = None
    case_title: Optional[str] = None
    status: CaseStatus = CaseStatus.UNKNOWN
    judge_name: Optional[str] = None
    parties: List[CaseParty] = field(default_factory=list)
    jurisdiction: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    disposition: Optional[str] = None
    disposition_date: Optional[date] = None
    amount_claimed: Optional[float] = None
    amount_awarded: Optional[float] = None
    docket_id: Optional[str] = None
    court_id: Optional[str] = None
    pacer_case_id: Optional[str] = None
    nature_of_suit: Optional[str] = None
    cause: Optional[str] = None
    jury_demand: Optional[str] = None
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_number": self.case_number,
            "case_type": self.case_type.value,
            "court_name": self.court_name,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "case_title": self.case_title,
            "status": self.status.value,
            "judge_name": self.judge_name,
            "parties": [p.to_dict() for p in self.parties],
            "jurisdiction": self.jurisdiction,
            "county": self.county,
            "state": self.state,
            "disposition": self.disposition,
            "disposition_date": (
                self.disposition_date.isoformat() if self.disposition_date else None
            ),
            "amount_claimed": self.amount_claimed,
            "amount_awarded": self.amount_awarded,
            "docket_id": self.docket_id,
            "court_id": self.court_id,
            "pacer_case_id": self.pacer_case_id,
            "nature_of_suit": self.nature_of_suit,
            "cause": self.cause,
            "jury_demand": self.jury_demand,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at.isoformat(),
        }

    @property
    def plaintiffs(self) -> List[CaseParty]:
        """Get all plaintiffs/petitioners"""
        return [
            p
            for p in self.parties
            if p.party_type in (PartyType.PLAINTIFF, PartyType.PETITIONER)
        ]

    @property
    def defendants(self) -> List[CaseParty]:
        """Get all defendants/respondents"""
        return [
            p
            for p in self.parties
            if p.party_type in (PartyType.DEFENDANT, PartyType.RESPONDENT)
        ]


@dataclass
class DocketEntry:
    """Represents a docket entry in a case"""

    entry_number: int
    date_filed: Optional[date] = None
    description: str = ""
    document_number: Optional[int] = None
    page_count: Optional[int] = None
    attachment_count: int = 0
    recap_document_id: Optional[str] = None
    pacer_doc_id: Optional[str] = None
    is_available: bool = False
    source_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_number": self.entry_number,
            "date_filed": self.date_filed.isoformat() if self.date_filed else None,
            "description": self.description,
            "document_number": self.document_number,
            "page_count": self.page_count,
            "attachment_count": self.attachment_count,
            "recap_document_id": self.recap_document_id,
            "pacer_doc_id": self.pacer_doc_id,
            "is_available": self.is_available,
            "source_url": self.source_url,
        }


@dataclass
class Opinion:
    """Represents a court opinion"""

    opinion_id: str
    case_name: str
    court_name: str
    date_filed: Optional[date] = None
    date_argued: Optional[date] = None
    docket_number: Optional[str] = None
    citation: Optional[str] = None
    status: Optional[str] = None
    author: Optional[str] = None
    opinion_type: Optional[str] = None
    text_excerpt: Optional[str] = None
    download_url: Optional[str] = None
    cluster_id: Optional[str] = None
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opinion_id": self.opinion_id,
            "case_name": self.case_name,
            "court_name": self.court_name,
            "date_filed": self.date_filed.isoformat() if self.date_filed else None,
            "date_argued": self.date_argued.isoformat() if self.date_argued else None,
            "docket_number": self.docket_number,
            "citation": self.citation,
            "status": self.status,
            "author": self.author,
            "opinion_type": self.opinion_type,
            "text_excerpt": self.text_excerpt,
            "download_url": self.download_url,
            "cluster_id": self.cluster_id,
            "source_url": self.source_url,
        }


@dataclass
class CaseSearch:
    """Search parameters for court cases"""

    case_number: Optional[str] = None
    party_name: Optional[str] = None
    case_type: Optional[CaseType] = None
    court_name: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[CaseStatus] = None
    include_closed: bool = True


@dataclass
class PartySearch:
    """Search parameters for party-based searches"""

    name: str
    party_type: Optional[PartyType] = None
    state: Optional[str] = None
    county: Optional[str] = None
    case_type: Optional[CaseType] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    exact_match: bool = False


# Federal court identifiers
FEDERAL_COURTS = {
    # District Courts
    "cacd": {
        "name": "Central District of California",
        "state": "CA",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "caed": {
        "name": "Eastern District of California",
        "state": "CA",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "cand": {
        "name": "Northern District of California",
        "state": "CA",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "casd": {
        "name": "Southern District of California",
        "state": "CA",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "txed": {
        "name": "Eastern District of Texas",
        "state": "TX",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "txnd": {
        "name": "Northern District of Texas",
        "state": "TX",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "txsd": {
        "name": "Southern District of Texas",
        "state": "TX",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "txwd": {
        "name": "Western District of Texas",
        "state": "TX",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "nysd": {
        "name": "Southern District of New York",
        "state": "NY",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "nyed": {
        "name": "Eastern District of New York",
        "state": "NY",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "nynd": {
        "name": "Northern District of New York",
        "state": "NY",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "nywd": {
        "name": "Western District of New York",
        "state": "NY",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "flsd": {
        "name": "Southern District of Florida",
        "state": "FL",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "flmd": {
        "name": "Middle District of Florida",
        "state": "FL",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "flnd": {
        "name": "Northern District of Florida",
        "state": "FL",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "ilnd": {
        "name": "Northern District of Illinois",
        "state": "IL",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "ilcd": {
        "name": "Central District of Illinois",
        "state": "IL",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "ilsd": {
        "name": "Southern District of Illinois",
        "state": "IL",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "dcd": {
        "name": "District of Columbia",
        "state": "DC",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    "ded": {
        "name": "District of Delaware",
        "state": "DE",
        "level": CourtLevel.FEDERAL_DISTRICT,
    },
    # Appellate Courts
    "ca1": {
        "name": "First Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "ca2": {
        "name": "Second Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "ca3": {
        "name": "Third Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "ca4": {
        "name": "Fourth Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "ca5": {
        "name": "Fifth Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "ca6": {
        "name": "Sixth Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "ca7": {
        "name": "Seventh Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "ca8": {
        "name": "Eighth Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "ca9": {
        "name": "Ninth Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "ca10": {
        "name": "Tenth Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "ca11": {
        "name": "Eleventh Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "cadc": {
        "name": "DC Circuit Court of Appeals",
        "state": "DC",
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    "cafc": {
        "name": "Federal Circuit Court of Appeals",
        "state": None,
        "level": CourtLevel.FEDERAL_APPELLATE,
    },
    # Supreme Court
    "scotus": {
        "name": "Supreme Court of the United States",
        "state": None,
        "level": CourtLevel.SUPREME_COURT,
    },
}

# CourtListener API configuration
COURTLISTENER_CONFIG = {
    "base_url": "https://www.courtlistener.com/api/rest/v4",
    "search_url": "https://www.courtlistener.com/api/rest/v4/search/",
    "docket_url": "https://www.courtlistener.com/api/rest/v4/dockets/",
    "opinion_url": "https://www.courtlistener.com/api/rest/v4/opinions/",
    "cluster_url": "https://www.courtlistener.com/api/rest/v4/clusters/",
    "court_url": "https://www.courtlistener.com/api/rest/v4/courts/",
    "party_url": "https://www.courtlistener.com/api/rest/v4/parties/",
    "attorney_url": "https://www.courtlistener.com/api/rest/v4/attorneys/",
    "auth_required": True,
    "auth_env_var": "COURTLISTENER_API_KEY",
    "rate_limit": 5000,  # Per hour with auth
    "documentation": "https://www.courtlistener.com/api/rest-info/",
}


class CourtListenerAPI:
    """
    CourtListener / RECAP API integration for federal court records.

    CourtListener provides FREE access to millions of federal court documents
    through the RECAP archive. The API provides access to:

    - Federal court dockets (district, appellate, bankruptcy)
    - Court opinions and orders
    - Party and attorney information
    - Document search
    - RECAP archive of PACER documents

    Rate Limits:
    - Without API key: 100 requests/hour
    - With API key: 5000 requests/hour

    API Key: Get free at https://www.courtlistener.com/sign-in/
    """

    CATEGORY = "court_records"
    DISPLAY_NAME = "Federal Court Records (CourtListener/RECAP)"
    BASE_URL = "https://www.courtlistener.com/api/rest/v4"

    def __init__(self, api_key: str = None):
        """
        Initialize the CourtListener API client.

        Args:
            api_key: CourtListener API key (optional but recommended)
        """
        self.api_key = api_key or os.environ.get("COURTLISTENER_API_KEY")
        self.config = COURTLISTENER_CONFIG
        self._last_request_time = 0
        # Rate limit: with key ~1.4 req/sec, without ~1 per 36 sec
        self._min_request_interval = 0.75 if self.api_key else 36.0
        logger.info(
            f"CourtListenerAPI initialized (API key: {'present' if self.api_key else 'not set'})"
        )

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    async def _make_request(
        self,
        url: str,
        params: Dict[str, Any] = None,
        session: aiohttp.ClientSession = None,
    ) -> Dict[str, Any]:
        """
        Make an async HTTP request to CourtListener API.

        Args:
            url: API endpoint URL
            params: Query parameters
            session: Optional aiohttp session

        Returns:
            JSON response as dictionary
        """
        await self._rate_limit()

        headers = {
            "Accept": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Token {self.api_key}"

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    logger.error("CourtListener API authentication failed")
                    return {}
                elif response.status == 429:
                    logger.warning("CourtListener rate limit hit, waiting...")
                    await asyncio.sleep(60)
                    return await self._make_request(
                        url, params, session if not close_session else None
                    )
                elif response.status == 404:
                    logger.warning(f"Resource not found: {url}")
                    return {}
                else:
                    error_text = await response.text()
                    logger.error(
                        f"CourtListener API error {response.status}: {error_text}"
                    )
                    return {}
        except asyncio.TimeoutError:
            logger.error(f"Timeout requesting: {url}")
            return {}
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {e}")
            return {}
        finally:
            if close_session:
                await session.close()

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date from API response."""
        if not date_str:
            return None
        try:
            # CourtListener uses ISO format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            return None

    def _classify_case_type(self, nature_of_suit: str, cause: str = None) -> CaseType:
        """Classify case type from nature of suit code."""
        if not nature_of_suit:
            return CaseType.UNKNOWN

        nos_lower = nature_of_suit.lower()

        # Criminal
        if "criminal" in nos_lower or nos_lower.startswith("cr"):
            return CaseType.CRIMINAL

        # Bankruptcy
        if "bankruptcy" in nos_lower or "bankr" in nos_lower:
            return CaseType.BANKRUPTCY

        # Civil categories
        if any(
            kw in nos_lower
            for kw in ["contract", "insurance", "negotiable", "recovery"]
        ):
            return CaseType.CIVIL

        if any(
            kw in nos_lower
            for kw in ["tort", "personal injury", "product liability", "malpractice"]
        ):
            return CaseType.CIVIL

        if any(kw in nos_lower for kw in ["labor", "employment", "erisa", "flsa"]):
            return CaseType.CIVIL

        if any(kw in nos_lower for kw in ["property", "real property", "foreclosure"]):
            return CaseType.CIVIL

        if any(kw in nos_lower for kw in ["civil rights", "voting", "housing"]):
            return CaseType.CIVIL

        if any(kw in nos_lower for kw in ["tax", "irs"]):
            return CaseType.TAX

        if "appeal" in nos_lower:
            return CaseType.APPELLATE

        return CaseType.CIVIL  # Default for federal courts

    async def search_dockets(
        self,
        query: str = "",
        court: str = "",
        case_name: str = "",
        docket_number: str = "",
        date_filed_after: date = None,
        date_filed_before: date = None,
        nature_of_suit: str = "",
        limit: int = 20,
    ) -> List[CourtCase]:
        """
        Search federal court dockets.

        Args:
            query: Full-text search query
            court: Court ID (e.g., 'cacd', 'nysd')
            case_name: Case name search
            docket_number: Docket number search
            date_filed_after: Filter by filing date
            date_filed_before: Filter by filing date
            nature_of_suit: Nature of suit filter
            limit: Maximum results to return

        Returns:
            List of CourtCase objects
        """
        logger.info(f"Searching dockets: query='{query}', court='{court}'")

        params = {
            "type": "r",  # RECAP type for dockets
        }

        if query:
            params["q"] = query
        if court:
            params["court"] = court
        if case_name:
            params["case_name"] = case_name
        if docket_number:
            params["docket_number"] = docket_number
        if date_filed_after:
            params["date_filed__gte"] = date_filed_after.isoformat()
        if date_filed_before:
            params["date_filed__lte"] = date_filed_before.isoformat()
        if nature_of_suit:
            params["nature_of_suit"] = nature_of_suit

        url = f"{self.BASE_URL}/search/"
        data = await self._make_request(url, params)

        cases = []
        results = data.get("results", [])[:limit]

        for item in results:
            court_id = item.get("court_id", "")
            court_info = FEDERAL_COURTS.get(court_id, {})

            case = CourtCase(
                case_number=item.get("docket_number", ""),
                case_type=self._classify_case_type(item.get("nature_of_suit", "")),
                court_name=court_info.get("name", item.get("court", "")),
                filing_date=self._parse_date(item.get("date_filed")),
                case_title=item.get("case_name", ""),
                status=CaseStatus.UNKNOWN,
                judge_name=item.get("assigned_to_str"),
                jurisdiction="Federal",
                state=court_info.get("state"),
                docket_id=str(item.get("docket_id", "")),
                court_id=court_id,
                pacer_case_id=item.get("pacer_case_id"),
                nature_of_suit=item.get("nature_of_suit"),
                cause=item.get("cause"),
                source_url=f"https://www.courtlistener.com/docket/{item.get('docket_id')}/",
                raw_data=item,
            )
            cases.append(case)

        logger.info(f"Found {len(cases)} dockets")
        return cases

    async def get_docket(self, docket_id: str) -> Optional[CourtCase]:
        """
        Get detailed docket information by ID.

        Args:
            docket_id: CourtListener docket ID

        Returns:
            CourtCase with full details or None
        """
        logger.info(f"Getting docket {docket_id}")

        url = f"{self.BASE_URL}/dockets/{docket_id}/"
        data = await self._make_request(url)

        if not data:
            return None

        court_id = data.get("court_id", "")
        court_info = FEDERAL_COURTS.get(court_id, {})

        # Get parties
        parties = []
        for party_data in data.get("parties", []):
            party_type = self._parse_party_type(
                party_data.get("party_type", {}).get("name", "")
            )
            party = CaseParty(
                name=party_data.get("name", ""),
                party_type=party_type,
                party_id=str(party_data.get("id", "")),
            )

            # Get attorney if available
            attorneys = party_data.get("attorneys", [])
            if attorneys:
                atty = attorneys[0]
                party.attorney_name = atty.get("name")
                party.attorney_firm = atty.get("firm")

            parties.append(party)

        case = CourtCase(
            case_number=data.get("docket_number", ""),
            case_type=self._classify_case_type(
                data.get("nature_of_suit", ""), data.get("cause")
            ),
            court_name=court_info.get(
                "name", data.get("court", {}).get("full_name", "")
            ),
            filing_date=self._parse_date(data.get("date_filed")),
            case_title=data.get("case_name", ""),
            status=(
                CaseStatus.CLOSED if data.get("date_terminated") else CaseStatus.OPEN
            ),
            judge_name=data.get("assigned_to_str"),
            parties=parties,
            jurisdiction="Federal",
            state=court_info.get("state"),
            docket_id=str(data.get("id", "")),
            court_id=court_id,
            pacer_case_id=data.get("pacer_case_id"),
            nature_of_suit=data.get("nature_of_suit"),
            cause=data.get("cause"),
            jury_demand=data.get("jury_demand"),
            disposition=data.get("date_terminated"),
            source_url=f"https://www.courtlistener.com/docket/{docket_id}/",
            raw_data=data,
        )

        return case

    async def get_docket_entries(
        self, docket_id: str, limit: int = 100
    ) -> List[DocketEntry]:
        """
        Get docket entries for a case.

        Args:
            docket_id: CourtListener docket ID
            limit: Maximum entries to return

        Returns:
            List of DocketEntry objects
        """
        logger.info(f"Getting docket entries for {docket_id}")

        url = f"{self.BASE_URL}/docket-entries/"
        params = {
            "docket": docket_id,
            "page_size": min(limit, 100),
        }

        data = await self._make_request(url, params)
        entries = []

        for item in data.get("results", []):
            entry = DocketEntry(
                entry_number=item.get("entry_number", 0),
                date_filed=self._parse_date(item.get("date_filed")),
                description=item.get("description", ""),
                document_number=item.get("document_number"),
                page_count=item.get("page_count"),
                attachment_count=len(item.get("recap_documents", [])),
                is_available=bool(item.get("recap_documents")),
                source_url=f"https://www.courtlistener.com/docket/{docket_id}/?page=1#entry-{item.get('entry_number', 0)}",
            )
            entries.append(entry)

        logger.info(f"Found {len(entries)} docket entries")
        return entries

    async def search_opinions(
        self,
        query: str = "",
        court: str = "",
        case_name: str = "",
        judge: str = "",
        date_filed_after: date = None,
        date_filed_before: date = None,
        cited_gt: int = None,
        limit: int = 20,
    ) -> List[Opinion]:
        """
        Search court opinions.

        Args:
            query: Full-text search query
            court: Court ID
            case_name: Case name search
            judge: Judge name
            date_filed_after: Filter by filing date
            date_filed_before: Filter by filing date
            cited_gt: Minimum citation count
            limit: Maximum results

        Returns:
            List of Opinion objects
        """
        logger.info(f"Searching opinions: query='{query}'")

        params = {
            "type": "o",  # Opinion type
        }

        if query:
            params["q"] = query
        if court:
            params["court"] = court
        if case_name:
            params["case_name"] = case_name
        if judge:
            params["judge"] = judge
        if date_filed_after:
            params["date_filed__gte"] = date_filed_after.isoformat()
        if date_filed_before:
            params["date_filed__lte"] = date_filed_before.isoformat()
        if cited_gt:
            params["cited_gt"] = cited_gt

        url = f"{self.BASE_URL}/search/"
        data = await self._make_request(url, params)

        opinions = []
        results = data.get("results", [])[:limit]

        for item in results:
            court_id = item.get("court_id", "")
            court_info = FEDERAL_COURTS.get(court_id, {})

            opinion = Opinion(
                opinion_id=str(item.get("id", "")),
                case_name=item.get("case_name", ""),
                court_name=court_info.get("name", item.get("court", "")),
                date_filed=self._parse_date(item.get("date_filed")),
                date_argued=self._parse_date(item.get("date_argued")),
                docket_number=item.get("docket_number"),
                citation=(
                    item.get("citation", [None])[0] if item.get("citation") else None
                ),
                status=item.get("status"),
                author=item.get("author"),
                opinion_type=item.get("type"),
                text_excerpt=(
                    item.get("snippet", "")[:500] if item.get("snippet") else None
                ),
                cluster_id=str(item.get("cluster_id", "")),
                download_url=item.get("download_url"),
                source_url=f"https://www.courtlistener.com/opinion/{item.get('cluster_id')}/",
                raw_data=item,
            )
            opinions.append(opinion)

        logger.info(f"Found {len(opinions)} opinions")
        return opinions

    async def get_opinion(self, opinion_id: str) -> Optional[Opinion]:
        """
        Get detailed opinion by ID.

        Args:
            opinion_id: CourtListener opinion ID

        Returns:
            Opinion with full details or None
        """
        logger.info(f"Getting opinion {opinion_id}")

        url = f"{self.BASE_URL}/opinions/{opinion_id}/"
        data = await self._make_request(url)

        if not data:
            return None

        # Get cluster info for case details
        cluster_url = data.get("cluster")
        cluster_data = {}
        if cluster_url:
            cluster_data = await self._make_request(cluster_url)

        court_id = cluster_data.get("court_id", "")
        court_info = FEDERAL_COURTS.get(court_id, {})

        opinion = Opinion(
            opinion_id=str(data.get("id", "")),
            case_name=cluster_data.get("case_name", ""),
            court_name=court_info.get("name", ""),
            date_filed=self._parse_date(cluster_data.get("date_filed")),
            date_argued=self._parse_date(cluster_data.get("date_argued")),
            docket_number=cluster_data.get("docket", {}).get("docket_number"),
            citation=(
                cluster_data.get("citation", [None])[0]
                if cluster_data.get("citation")
                else None
            ),
            author=data.get("author_str"),
            opinion_type=data.get("type"),
            text_excerpt=(
                data.get("plain_text", "")[:1000] if data.get("plain_text") else None
            ),
            cluster_id=str(cluster_data.get("id", "")),
            download_url=data.get("download_url"),
            source_url=f"https://www.courtlistener.com/opinion/{data.get('id')}/",
            raw_data={**data, "cluster": cluster_data},
        )

        return opinion

    async def search_by_party(
        self,
        party_name: str,
        party_type: PartyType = None,
        court: str = "",
        date_filed_after: date = None,
        date_filed_before: date = None,
        limit: int = 20,
    ) -> List[CourtCase]:
        """
        Search cases by party name.

        Args:
            party_name: Party name to search
            party_type: Type of party
            court: Court filter
            date_filed_after: Filter by date
            date_filed_before: Filter by date
            limit: Maximum results

        Returns:
            List of CourtCase objects
        """
        logger.info(f"Searching by party: {party_name}")

        # Search using party name in case name field
        params = {
            "type": "r",
            "q": f'"{party_name}"',
        }

        if court:
            params["court"] = court
        if date_filed_after:
            params["date_filed__gte"] = date_filed_after.isoformat()
        if date_filed_before:
            params["date_filed__lte"] = date_filed_before.isoformat()

        url = f"{self.BASE_URL}/search/"
        data = await self._make_request(url, params)

        cases = []
        results = data.get("results", [])[:limit]

        for item in results:
            court_id = item.get("court_id", "")
            court_info = FEDERAL_COURTS.get(court_id, {})

            case = CourtCase(
                case_number=item.get("docket_number", ""),
                case_type=self._classify_case_type(item.get("nature_of_suit", "")),
                court_name=court_info.get("name", item.get("court", "")),
                filing_date=self._parse_date(item.get("date_filed")),
                case_title=item.get("case_name", ""),
                status=CaseStatus.UNKNOWN,
                judge_name=item.get("assigned_to_str"),
                jurisdiction="Federal",
                state=court_info.get("state"),
                docket_id=str(item.get("docket_id", "")),
                court_id=court_id,
                source_url=f"https://www.courtlistener.com/docket/{item.get('docket_id')}/",
                raw_data=item,
            )
            cases.append(case)

        logger.info(f"Found {len(cases)} cases for party {party_name}")
        return cases

    async def get_courts(self) -> List[Dict[str, Any]]:
        """
        Get list of all courts in CourtListener.

        Returns:
            List of court information dictionaries
        """
        logger.info("Getting court list")

        url = f"{self.BASE_URL}/courts/"
        params = {"page_size": 200}

        all_courts = []
        while url:
            data = await self._make_request(
                url, params if "page" not in str(url) else None
            )
            all_courts.extend(data.get("results", []))
            url = data.get("next")
            if url and len(all_courts) >= 500:  # Safety limit
                break

        logger.info(f"Retrieved {len(all_courts)} courts")
        return all_courts

    async def search_attorneys(
        self, name: str, firm: str = "", limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for attorneys.

        Args:
            name: Attorney name
            firm: Law firm name
            limit: Maximum results

        Returns:
            List of attorney information
        """
        logger.info(f"Searching attorneys: {name}")

        url = f"{self.BASE_URL}/attorneys/"
        params = {
            "name__icontains": name,
        }

        data = await self._make_request(url, params)
        attorneys = data.get("results", [])[:limit]

        logger.info(f"Found {len(attorneys)} attorneys")
        return attorneys

    def _parse_party_type(self, party_type_name: str) -> PartyType:
        """Parse party type from CourtListener format."""
        name_lower = party_type_name.lower()

        if "plaintiff" in name_lower:
            return PartyType.PLAINTIFF
        elif "defendant" in name_lower:
            return PartyType.DEFENDANT
        elif "petitioner" in name_lower:
            return PartyType.PETITIONER
        elif "respondent" in name_lower:
            return PartyType.RESPONDENT
        elif "appellant" in name_lower:
            return PartyType.APPELLANT
        elif "appellee" in name_lower:
            return PartyType.APPELLEE
        elif "creditor" in name_lower:
            return PartyType.CREDITOR
        elif "debtor" in name_lower:
            return PartyType.DEBTOR

        return PartyType.OTHER

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        return {
            "category": self.CATEGORY,
            "display_name": self.DISPLAY_NAME,
            "federal_courts": len(FEDERAL_COURTS),
            "court_levels": ["District", "Appellate", "Bankruptcy", "Supreme Court"],
            "data_types": ["Dockets", "Opinions", "Parties", "Attorneys", "Documents"],
            "auth_required": "Optional (increases rate limit)",
            "rate_limit": "5000/hour with key, 100/hour without",
            "api_key_present": bool(self.api_key),
        }


class CourtRecordsScraper(ABC):
    """
    Abstract base class for court records scrapers.

    Provides unified interface for accessing court records across
    different court systems and jurisdictions.
    """

    # Case type keywords for classification
    CIVIL_KEYWORDS = [
        "civil",
        "contract",
        "tort",
        "personal injury",
        "negligence",
        "breach",
    ]
    CRIMINAL_KEYWORDS = [
        "criminal",
        "felony",
        "misdemeanor",
        "dui",
        "dwi",
        "theft",
        "assault",
    ]
    FAMILY_KEYWORDS = [
        "family",
        "divorce",
        "custody",
        "child support",
        "adoption",
        "paternity",
    ]
    PROBATE_KEYWORDS = [
        "probate",
        "estate",
        "will",
        "trust",
        "guardianship",
        "conservatorship",
    ]

    def __init__(self, jurisdiction: str, config: Dict[str, Any] = None):
        """
        Initialize the court records scraper.

        Args:
            jurisdiction: Court jurisdiction identifier
            config: Optional configuration dictionary
        """
        self.jurisdiction = jurisdiction
        self.config = config or {}
        self._session = None

        logger.info(f"Initialized CourtRecordsScraper for {jurisdiction}")

    @abstractmethod
    def search_cases(self, search: CaseSearch) -> List[CourtCase]:
        """
        Search for court cases matching criteria.

        Args:
            search: CaseSearch parameters

        Returns:
            List of matching CourtCase objects
        """
        pass

    @abstractmethod
    def search_by_party(self, search: PartySearch) -> List[CourtCase]:
        """
        Search for cases by party name.

        Args:
            search: PartySearch parameters

        Returns:
            List of CourtCase objects involving the party
        """
        pass

    @abstractmethod
    def get_case_details(self, case_number: str) -> Optional[CourtCase]:
        """
        Get detailed information for a specific case.

        Args:
            case_number: Case number/identifier

        Returns:
            CourtCase with full details or None if not found
        """
        pass

    def classify_case_type(self, text: str) -> CaseType:
        """
        Classify case type based on text content.

        Args:
            text: Case title, description, or type string

        Returns:
            Classified CaseType
        """
        text_lower = text.lower()

        if any(kw in text_lower for kw in self.CRIMINAL_KEYWORDS):
            return CaseType.CRIMINAL
        elif any(kw in text_lower for kw in self.FAMILY_KEYWORDS):
            return CaseType.FAMILY
        elif any(kw in text_lower for kw in self.PROBATE_KEYWORDS):
            return CaseType.PROBATE
        elif any(kw in text_lower for kw in self.CIVIL_KEYWORDS):
            return CaseType.CIVIL
        elif "bankruptcy" in text_lower:
            return CaseType.BANKRUPTCY
        elif "small claim" in text_lower:
            return CaseType.SMALL_CLAIMS
        elif "tax" in text_lower:
            return CaseType.TAX
        elif "traffic" in text_lower:
            return CaseType.TRAFFIC
        elif "juvenile" in text_lower:
            return CaseType.JUVENILE
        elif "appeal" in text_lower:
            return CaseType.APPELLATE

        return CaseType.UNKNOWN

    def parse_case_status(self, status_text: str) -> CaseStatus:
        """
        Parse case status from text.

        Args:
            status_text: Status string

        Returns:
            Parsed CaseStatus
        """
        status_lower = status_text.lower().strip()

        if any(s in status_lower for s in ["open", "active", "pending trial"]):
            return CaseStatus.OPEN
        elif any(s in status_lower for s in ["closed", "disposed", "final"]):
            return CaseStatus.CLOSED
        elif any(s in status_lower for s in ["pending", "awaiting"]):
            return CaseStatus.PENDING
        elif "dismiss" in status_lower:
            return CaseStatus.DISMISSED
        elif "settle" in status_lower:
            return CaseStatus.SETTLED
        elif "appeal" in status_lower:
            return CaseStatus.APPEALED
        elif any(s in status_lower for s in ["hold", "stayed", "abated"]):
            return CaseStatus.ON_HOLD

        return CaseStatus.UNKNOWN

    def parse_party_type(self, party_text: str) -> PartyType:
        """
        Parse party type from text.

        Args:
            party_text: Party type string

        Returns:
            Parsed PartyType
        """
        party_lower = party_text.lower().strip()

        if "plaintiff" in party_lower:
            return PartyType.PLAINTIFF
        elif "defendant" in party_lower:
            return PartyType.DEFENDANT
        elif "petitioner" in party_lower:
            return PartyType.PETITIONER
        elif "respondent" in party_lower:
            return PartyType.RESPONDENT
        elif "appellant" in party_lower:
            return PartyType.APPELLANT
        elif "appellee" in party_lower:
            return PartyType.APPELLEE
        elif "creditor" in party_lower:
            return PartyType.CREDITOR
        elif "debtor" in party_lower:
            return PartyType.DEBTOR
        elif "attorney" in party_lower or "counsel" in party_lower:
            return PartyType.ATTORNEY
        elif "judge" in party_lower:
            return PartyType.JUDGE
        elif "witness" in party_lower:
            return PartyType.WITNESS

        return PartyType.OTHER

    def normalize_case_number(self, case_number: str) -> str:
        """
        Normalize case number format.

        Args:
            case_number: Raw case number string

        Returns:
            Normalized case number
        """
        # Remove extra whitespace
        normalized = " ".join(case_number.split())

        # Standardize common separators
        normalized = normalized.replace(" - ", "-").replace(" / ", "/")

        return normalized.upper()

    def parse_amount(self, amount_str: str) -> Optional[float]:
        """
        Parse monetary amount from string.

        Args:
            amount_str: Amount string (e.g., "$1,234.56")

        Returns:
            Float amount or None if parsing fails
        """
        if not amount_str:
            return None

        try:
            # Remove currency symbols, commas, and whitespace
            cleaned = re.sub(r"[\$,\s]", "", amount_str)
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date from various formats.

        Args:
            date_str: Date string

        Returns:
            Parsed date or None
        """
        if not date_str:
            return None

        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y%m%d",
            "%d-%b-%Y",
            "%B %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get scraper statistics."""
        return {
            "jurisdiction": self.jurisdiction,
            "scraper_class": self.__class__.__name__,
        }


class StateCourtScraper(CourtRecordsScraper):
    """
    Generic state court scraper that can be configured for different states.
    """

    def __init__(self, state_code: str, config: Dict[str, Any] = None):
        """
        Initialize state court scraper.

        Args:
            state_code: Two-letter state code
            config: State-specific configuration
        """
        super().__init__(jurisdiction=state_code, config=config)
        self.state_code = state_code.upper()
        self.base_url = config.get("base_url", "") if config else ""
        self.court_api = config.get("court_api", "") if config else ""

    def search_cases(self, search: CaseSearch) -> List[CourtCase]:
        """Search for court cases in this state."""
        # Implementation would vary by state
        logger.info(f"Searching cases in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return []

    def search_by_party(self, search: PartySearch) -> List[CourtCase]:
        """Search for cases by party name."""
        logger.info(f"Searching by party '{search.name}' in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return []

    def get_case_details(self, case_number: str) -> Optional[CourtCase]:
        """Get detailed case information."""
        logger.info(f"Getting case details for {case_number} in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return None


# Synchronous wrapper functions
def get_courtlistener_api(api_key: str = None) -> CourtListenerAPI:
    """Get CourtListener API instance."""
    return CourtListenerAPI(api_key=api_key)


def search_federal_cases(
    query: str = "", court: str = "", party_name: str = "", limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search federal court cases (synchronous wrapper).

    Args:
        query: Search query
        court: Court ID filter
        party_name: Party name search
        limit: Maximum results

    Returns:
        List of case dictionaries
    """
    api = get_courtlistener_api()
    loop = asyncio.get_event_loop()

    if party_name:
        cases = loop.run_until_complete(
            api.search_by_party(party_name, court=court, limit=limit)
        )
    else:
        cases = loop.run_until_complete(
            api.search_dockets(query=query, court=court, limit=limit)
        )

    return [c.to_dict() for c in cases]


def search_opinions(
    query: str, court: str = "", limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search court opinions (synchronous wrapper).

    Args:
        query: Search query
        court: Court filter
        limit: Maximum results

    Returns:
        List of opinion dictionaries
    """
    api = get_courtlistener_api()
    loop = asyncio.get_event_loop()
    opinions = loop.run_until_complete(
        api.search_opinions(query=query, court=court, limit=limit)
    )
    return [o.to_dict() for o in opinions]


def search_court_records(
    party_name: str,
    states: List[str] = None,
    case_types: List[CaseType] = None,
    date_from: date = None,
    date_to: date = None,
) -> List[CourtCase]:
    """
    Convenience function to search court records across multiple jurisdictions.

    Args:
        party_name: Name to search for
        states: List of state codes to search (None = all available)
        case_types: Types of cases to include
        date_from: Start date filter
        date_to: End date filter

    Returns:
        List of matching CourtCase objects
    """
    results = []

    # Search federal courts via CourtListener
    api = get_courtlistener_api()
    loop = asyncio.get_event_loop()

    federal_cases = loop.run_until_complete(
        api.search_by_party(
            party_name, date_filed_after=date_from, date_filed_before=date_to, limit=50
        )
    )
    results.extend(federal_cases)

    logger.info(f"Found {len(results)} court records for '{party_name}'")

    return results


def get_available_courts() -> Dict[str, Dict[str, Any]]:
    """Get all available federal courts."""
    return FEDERAL_COURTS.copy()
