"""
State Courts Base Scraper

Base class for state-level court systems. State courts handle the vast
majority of court cases in the United States, including:

- State Supreme Courts (court of last resort)
- State Appellate/Appeals Courts (intermediate appeals)
- State Trial Courts (general jurisdiction)
- State Specialty Courts (tax, workers comp, etc.)

Each state has a unique court structure and public access system.
Common patterns include:
- Statewide unified systems (e.g., California, Texas)
- County-based systems with state oversight
- Mixed systems with multiple access points
"""

import asyncio
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

from .base import (
    CaseDocument,
    CaseEvent,
    CaseParty,
    CaseStatus,
    CaseType,
    CourtCase,
    CourtLevel,
    CourtSystemBase,
    CourtType,
    PartyRole,
    PartyType,
    SearchCriteria,
    SearchResult,
)

logger = logging.getLogger(__name__)


class StateCourtSystemType(Enum):
    """Types of state court systems."""

    UNIFIED = "unified"  # Statewide unified system
    COUNTY_BASED = "county_based"  # County-administered
    MIXED = "mixed"  # Combination
    REGIONAL = "regional"  # Regional circuits/districts


@dataclass
class StateCourtInfo:
    """Information about a state's court system."""

    state_code: str
    state_name: str
    system_type: StateCourtSystemType
    public_access_url: str
    court_structure: Dict[str, str]  # court level -> name
    has_statewide_search: bool = False
    requires_registration: bool = False
    case_management_vendor: Optional[str] = None  # Tyler, Thomson Reuters, etc.
    notes: str = ""


# State court system configurations
STATE_COURT_SYSTEMS: Dict[str, StateCourtInfo] = {
    "CA": StateCourtInfo(
        state_code="CA",
        state_name="California",
        system_type=StateCourtSystemType.COUNTY_BASED,
        public_access_url="https://www.courts.ca.gov/",
        court_structure={
            "supreme": "Supreme Court of California",
            "appellate": "Courts of Appeal",
            "trial": "Superior Courts",
        },
        has_statewide_search=False,
        requires_registration=True,
        case_management_vendor="Tyler Technologies",
        notes="58 counties with separate Superior Court systems",
    ),
    "TX": StateCourtInfo(
        state_code="TX",
        state_name="Texas",
        system_type=StateCourtSystemType.COUNTY_BASED,
        public_access_url="https://www.txcourts.gov/",
        court_structure={
            "supreme": "Supreme Court of Texas (civil)",
            "criminal_appeals": "Court of Criminal Appeals",
            "appellate": "Courts of Appeals",
            "district": "District Courts",
            "county": "County Courts",
            "justice": "Justice Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Tyler Technologies",
        notes="254 counties, dual supreme courts for civil/criminal",
    ),
    "FL": StateCourtInfo(
        state_code="FL",
        state_name="Florida",
        system_type=StateCourtSystemType.COUNTY_BASED,
        public_access_url="https://www.flcourts.org/",
        court_structure={
            "supreme": "Supreme Court of Florida",
            "appellate": "District Courts of Appeal",
            "circuit": "Circuit Courts",
            "county": "County Courts",
        },
        has_statewide_search=False,
        requires_registration=False,
        case_management_vendor="Mixed",
        notes="67 counties organized into 20 judicial circuits",
    ),
    "NY": StateCourtInfo(
        state_code="NY",
        state_name="New York",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://iapps.courts.state.ny.us/webcivil/",
        court_structure={
            "appeals": "Court of Appeals",
            "appellate": "Appellate Division",
            "supreme": "Supreme Court (trial level)",
            "county": "County Courts",
            "city": "City Courts",
            "district": "District Courts",
            "civil": "Civil Court of NYC",
            "criminal": "Criminal Court of NYC",
            "family": "Family Court",
            "surrogate": "Surrogate's Court",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Custom",
        notes="Unified court system with eCourts portal",
    ),
    "IL": StateCourtInfo(
        state_code="IL",
        state_name="Illinois",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.illinoiscourts.gov/",
        court_structure={
            "supreme": "Supreme Court of Illinois",
            "appellate": "Appellate Court",
            "circuit": "Circuit Courts",
        },
        has_statewide_search=False,
        requires_registration=False,
        case_management_vendor="Tyler Technologies",
        notes="102 counties in 24 judicial circuits",
    ),
    "PA": StateCourtInfo(
        state_code="PA",
        state_name="Pennsylvania",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://ujsportal.pacourts.us/",
        court_structure={
            "supreme": "Supreme Court of Pennsylvania",
            "superior": "Superior Court",
            "commonwealth": "Commonwealth Court",
            "common_pleas": "Courts of Common Pleas",
            "magisterial": "Magisterial District Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Custom",
        notes="Unified Judicial System Portal with statewide search",
    ),
    "OH": StateCourtInfo(
        state_code="OH",
        state_name="Ohio",
        system_type=StateCourtSystemType.COUNTY_BASED,
        public_access_url="https://www.supremecourt.ohio.gov/",
        court_structure={
            "supreme": "Supreme Court of Ohio",
            "appellate": "Courts of Appeals",
            "common_pleas": "Courts of Common Pleas",
            "municipal": "Municipal Courts",
            "county": "County Courts",
            "claims": "Court of Claims",
        },
        has_statewide_search=False,
        requires_registration=False,
        case_management_vendor="Mixed",
        notes="88 counties with separate systems",
    ),
    "GA": StateCourtInfo(
        state_code="GA",
        state_name="Georgia",
        system_type=StateCourtSystemType.COUNTY_BASED,
        public_access_url="https://www.georgiacourts.gov/",
        court_structure={
            "supreme": "Supreme Court of Georgia",
            "appeals": "Court of Appeals",
            "superior": "Superior Courts",
            "state": "State Courts",
            "juvenile": "Juvenile Courts",
            "probate": "Probate Courts",
            "magistrate": "Magistrate Courts",
            "municipal": "Municipal Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Tyler Technologies",
        notes="159 counties, statewide Odyssey rollout ongoing",
    ),
    "NC": StateCourtInfo(
        state_code="NC",
        state_name="North Carolina",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.nccourts.gov/",
        court_structure={
            "supreme": "Supreme Court of North Carolina",
            "appeals": "Court of Appeals",
            "superior": "Superior Courts",
            "district": "District Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Custom (eCourts)",
        notes="100 counties in unified system",
    ),
    "MI": StateCourtInfo(
        state_code="MI",
        state_name="Michigan",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://courts.michigan.gov/",
        court_structure={
            "supreme": "Michigan Supreme Court",
            "appeals": "Court of Appeals",
            "circuit": "Circuit Courts",
            "district": "District Courts",
            "probate": "Probate Courts",
            "claims": "Court of Claims",
        },
        has_statewide_search=False,
        requires_registration=False,
        case_management_vendor="Mixed",
        notes="83 counties in 57 circuits",
    ),
    "NJ": StateCourtInfo(
        state_code="NJ",
        state_name="New Jersey",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.njcourts.gov/",
        court_structure={
            "supreme": "Supreme Court of New Jersey",
            "appellate": "Appellate Division",
            "superior": "Superior Court",
            "tax": "Tax Court",
            "municipal": "Municipal Courts",
        },
        has_statewide_search=True,
        requires_registration=True,
        case_management_vendor="Custom (eCourts)",
        notes="21 counties, statewide eCourts system",
    ),
    "VA": StateCourtInfo(
        state_code="VA",
        state_name="Virginia",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.vacourts.gov/",
        court_structure={
            "supreme": "Supreme Court of Virginia",
            "appeals": "Court of Appeals",
            "circuit": "Circuit Courts",
            "district": "General District Courts",
            "juvenile": "Juvenile and Domestic Relations Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Custom",
        notes="Statewide case management system",
    ),
    "WA": StateCourtInfo(
        state_code="WA",
        state_name="Washington",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.courts.wa.gov/",
        court_structure={
            "supreme": "Washington Supreme Court",
            "appeals": "Court of Appeals",
            "superior": "Superior Courts",
            "district": "District Courts",
            "municipal": "Municipal Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Tyler Technologies (Odyssey)",
        notes="39 counties with statewide search",
    ),
    "AZ": StateCourtInfo(
        state_code="AZ",
        state_name="Arizona",
        system_type=StateCourtSystemType.COUNTY_BASED,
        public_access_url="https://www.azcourts.gov/",
        court_structure={
            "supreme": "Arizona Supreme Court",
            "appeals": "Court of Appeals",
            "superior": "Superior Courts",
            "justice": "Justice Courts",
            "municipal": "Municipal Courts",
        },
        has_statewide_search=False,
        requires_registration=False,
        case_management_vendor="iCMS",
        notes="15 counties with varying public access",
    ),
    "MA": StateCourtInfo(
        state_code="MA",
        state_name="Massachusetts",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.mass.gov/orgs/trial-court",
        court_structure={
            "sjc": "Supreme Judicial Court",
            "appeals": "Appeals Court",
            "superior": "Superior Court",
            "district": "District Court",
            "bmc": "Boston Municipal Court",
            "housing": "Housing Court",
            "juvenile": "Juvenile Court",
            "probate": "Probate and Family Court",
            "land": "Land Court",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Custom (MassCourts)",
        notes="Trial Court unified system",
    ),
    "TN": StateCourtInfo(
        state_code="TN",
        state_name="Tennessee",
        system_type=StateCourtSystemType.COUNTY_BASED,
        public_access_url="https://www.tncourts.gov/",
        court_structure={
            "supreme": "Tennessee Supreme Court",
            "appeals": "Court of Appeals",
            "criminal_appeals": "Court of Criminal Appeals",
            "circuit": "Circuit Courts",
            "chancery": "Chancery Courts",
            "criminal": "Criminal Courts",
            "general_sessions": "General Sessions Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Tyler Technologies",
        notes="95 counties with CaseLink statewide portal",
    ),
    "IN": StateCourtInfo(
        state_code="IN",
        state_name="Indiana",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://public.courts.in.gov/mycase/",
        court_structure={
            "supreme": "Indiana Supreme Court",
            "appeals": "Court of Appeals",
            "tax": "Tax Court",
            "circuit": "Circuit Courts",
            "superior": "Superior Courts",
            "city_town": "City and Town Courts",
            "small_claims": "Small Claims Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Tyler Technologies (Odyssey)",
        notes="MyCase portal provides excellent statewide access",
    ),
    "MO": StateCourtInfo(
        state_code="MO",
        state_name="Missouri",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.courts.mo.gov/",
        court_structure={
            "supreme": "Supreme Court of Missouri",
            "appeals": "Courts of Appeals",
            "circuit": "Circuit Courts",
            "municipal": "Municipal Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Custom (Case.net)",
        notes="Case.net provides comprehensive statewide access",
    ),
    "MD": StateCourtInfo(
        state_code="MD",
        state_name="Maryland",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.courts.state.md.us/",
        court_structure={
            "appeals": "Supreme Court of Maryland (renamed 2022)",
            "special_appeals": "Appellate Court of Maryland",
            "circuit": "Circuit Courts",
            "district": "District Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Custom (MDEC)",
        notes="Maryland Electronic Courts (MDEC) system",
    ),
    "WI": StateCourtInfo(
        state_code="WI",
        state_name="Wisconsin",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.wicourts.gov/",
        court_structure={
            "supreme": "Wisconsin Supreme Court",
            "appeals": "Court of Appeals",
            "circuit": "Circuit Courts",
            "municipal": "Municipal Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Custom (CCAP)",
        notes="WCCA provides excellent statewide access",
    ),
    "CO": StateCourtInfo(
        state_code="CO",
        state_name="Colorado",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.courts.state.co.us/",
        court_structure={
            "supreme": "Colorado Supreme Court",
            "appeals": "Colorado Court of Appeals",
            "district": "District Courts",
            "county": "County Courts",
            "water": "Water Courts",
            "municipal": "Municipal Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Custom",
        notes="22 judicial districts, statewide search available",
    ),
    "MN": StateCourtInfo(
        state_code="MN",
        state_name="Minnesota",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.mncourts.gov/",
        court_structure={
            "supreme": "Minnesota Supreme Court",
            "appeals": "Court of Appeals",
            "district": "District Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Tyler Technologies",
        notes="87 counties, Minnesota Court Information System (MNCIS)",
    ),
    "OR": StateCourtInfo(
        state_code="OR",
        state_name="Oregon",
        system_type=StateCourtSystemType.UNIFIED,
        public_access_url="https://www.courts.oregon.gov/",
        court_structure={
            "supreme": "Oregon Supreme Court",
            "appeals": "Court of Appeals",
            "circuit": "Circuit Courts",
            "tax": "Tax Court",
            "justice": "Justice Courts",
            "municipal": "Municipal Courts",
        },
        has_statewide_search=True,
        requires_registration=False,
        case_management_vendor="Tyler Technologies (Odyssey)",
        notes="36 counties, Oregon eCourt system",
    ),
}


class StateCourtBase(CourtSystemBase):
    """
    Abstract base class for state court system scrapers.

    Each state implementation should extend this class and implement
    the required abstract methods for that state's specific system.
    """

    STATE_CODE: str = ""
    STATE_NAME: str = ""

    def __init__(
        self, state_code: str, session: Optional[aiohttp.ClientSession] = None
    ):
        """Initialize the state court scraper."""
        super().__init__(session)

        self.STATE_CODE = state_code.upper()

        if self.STATE_CODE in STATE_COURT_SYSTEMS:
            info = STATE_COURT_SYSTEMS[self.STATE_CODE]
            self.STATE_NAME = info.state_name
            self.BASE_URL = info.public_access_url
            self.REQUIRES_LOGIN = info.requires_registration
            self._state_info = info
        else:
            self._state_info = None

    def get_state_court_info(self) -> Optional[StateCourtInfo]:
        """Get information about this state's court system."""
        return self._state_info

    def supports_statewide_search(self) -> bool:
        """Check if this state supports statewide case search."""
        return self._state_info.has_statewide_search if self._state_info else False

    def get_court_structure(self) -> Dict[str, str]:
        """Get the court structure for this state."""
        return self._state_info.court_structure if self._state_info else {}

    async def search_appellate_opinions(
        self,
        query: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        court_level: str = "all",  # supreme, appellate, all
        max_results: int = 100,
    ) -> SearchResult:
        """
        Search appellate court opinions.

        Many state courts publish appellate opinions in searchable databases.

        Args:
            query: Search query (party name, topic, citation)
            start_date: Start of date range
            end_date: End of date range
            court_level: supreme, appellate, or all
            max_results: Maximum results

        Returns:
            SearchResult with matching opinions
        """
        raise NotImplementedError(
            "Appellate opinion search not implemented for this state"
        )

    async def search_by_county(
        self,
        county: str,
        party_name: Optional[str] = None,
        case_number: Optional[str] = None,
        case_types: Optional[List[CaseType]] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """
        Search cases within a specific county.

        Args:
            county: County name
            party_name: Optional party name filter
            case_number: Optional case number
            case_types: Optional case type filter
            max_results: Maximum results

        Returns:
            SearchResult with matching cases
        """
        raise NotImplementedError("County search not implemented for this state")


class PennsylvaniaUJS(StateCourtBase):
    """
    Pennsylvania Unified Judicial System (UJS) Portal scraper.

    Pennsylvania has one of the best state court public access systems.
    https://ujsportal.pacourts.us/

    Provides access to:
    - Court of Common Pleas records
    - Magisterial District Court records
    - Appellate Court records
    """

    COURT_NAME = "Pennsylvania Unified Judicial System"
    COURT_TYPE = CourtType.STATE_TRIAL
    COURT_LEVEL = CourtLevel.TRIAL
    STATE = "PA"
    BASE_URL = "https://ujsportal.pacourts.us/"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize PA UJS scraper."""
        super().__init__("PA", session)

    async def search_by_party(
        self,
        party_name: str,
        party_type: str = "any",
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        case_types: Optional[List[CaseType]] = None,
        include_closed: bool = True,
        max_results: int = 100,
    ) -> SearchResult:
        """Search PA courts by party name."""
        import time

        start_time = time.time()

        search_url = f"{self.BASE_URL}DocketSheets/CP.aspx"

        # Get search page first
        status, html = await self._fetch(search_url)

        # Build search parameters
        params = {
            "searchType": "PartyName",
            "partyName": party_name,
        }

        if filed_start_date:
            params["filedDateFrom"] = filed_start_date.strftime("%m/%d/%Y")
        if filed_end_date:
            params["filedDateTo"] = filed_end_date.strftime("%m/%d/%Y")

        # Execute search
        status, html = await self._fetch(f"{search_url}/Search", params=params)
        soup = self._parse_html(html)

        # Parse results
        cases = []
        results_table = soup.find("table", {"id": "searchResults"})

        if results_table:
            for row in results_table.find_all("tr")[1 : max_results + 1]:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    case = CourtCase(
                        case_number=cells[0].get_text(strip=True),
                        court_name=cells[1].get_text(strip=True),
                        court_type=self.COURT_TYPE,
                        court_level=self.COURT_LEVEL,
                        case_title=cells[2].get_text(strip=True),
                        filing_date=self._parse_date(
                            cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        ),
                        state=self.STATE,
                        source_system="PA UJS Portal",
                    )
                    cases.append(case)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            cases=cases,
            total_count=len(cases),
            page_number=1,
            page_size=max_results,
            has_more=False,
            search_criteria=SearchCriteria(party_name=party_name),
            search_time_ms=search_time,
            source_system="PA UJS Portal",
        )

    async def search_by_case_number(self, case_number: str) -> Optional[CourtCase]:
        """Search for a specific case by docket number."""
        search_url = f"{self.BASE_URL}DocketSheets/CP.aspx"

        params = {
            "searchType": "DocketNumber",
            "docketNumber": case_number,
        }

        status, html = await self._fetch(f"{search_url}/Search", params=params)
        soup = self._parse_html(html)

        # Check if direct to case detail
        case_header = soup.find("div", {"class": "case-header"})
        if case_header:
            return self._parse_pa_case_detail(soup, case_number)

        return None

    async def get_case_detail(self, case_number: str) -> Optional[CourtCase]:
        """Get detailed case information."""
        detail_url = f"{self.BASE_URL}DocketSheets/CP.aspx/Docket/{case_number}"

        status, html = await self._fetch(detail_url)
        if status != 200:
            return None

        soup = self._parse_html(html)
        return self._parse_pa_case_detail(soup, case_number)

    def _parse_pa_case_detail(self, soup: BeautifulSoup, case_number: str) -> CourtCase:
        """Parse PA case detail page."""
        case = CourtCase(
            case_number=case_number,
            court_name=self.COURT_NAME,
            court_type=self.COURT_TYPE,
            court_level=self.COURT_LEVEL,
            state=self.STATE,
            source_system="PA UJS Portal",
        )

        # Parse header info
        header = soup.find("div", {"class": "case-header"})
        if header:
            title = header.find("h1")
            if title:
                case.case_title = title.get_text(strip=True)

        # Parse case info table
        info_table = soup.find("table", {"class": "case-info"})
        if info_table:
            for row in info_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)

                    if "filing date" in label:
                        case.filing_date = self._parse_date(value)
                    elif "status" in label:
                        case.status = self._parse_case_status(value)
                    elif "judge" in label:
                        case.judge = value
                    elif "county" in label:
                        case.county = value

        return case


class WisconsinCCAP(StateCourtBase):
    """
    Wisconsin Circuit Court Access Program (WCCA/CCAP) scraper.

    Wisconsin has one of the most accessible court record systems.
    https://wcca.wicourts.gov/

    Provides comprehensive access to:
    - All circuit court cases
    - Case parties
    - Charges and dispositions
    - Court events
    """

    COURT_NAME = "Wisconsin Circuit Courts"
    COURT_TYPE = CourtType.STATE_TRIAL
    COURT_LEVEL = CourtLevel.TRIAL
    STATE = "WI"
    BASE_URL = "https://wcca.wicourts.gov/"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize Wisconsin CCAP scraper."""
        super().__init__("WI", session)

    async def search_by_party(
        self,
        party_name: str,
        party_type: str = "any",
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        case_types: Optional[List[CaseType]] = None,
        include_closed: bool = True,
        max_results: int = 100,
    ) -> SearchResult:
        """Search Wisconsin circuit courts by party name."""
        import time

        start_time = time.time()

        # WCCA uses a simple query interface
        search_url = f"{self.BASE_URL}caseSearchResults.html"

        params = {
            "inputVO.partyName": party_name,
            "inputVO.partyNameSearchType": "contains",
        }

        if filed_start_date:
            params["inputVO.filedDateFrom"] = filed_start_date.strftime("%m/%d/%Y")
        if filed_end_date:
            params["inputVO.filedDateTo"] = filed_end_date.strftime("%m/%d/%Y")

        status, html = await self._fetch(search_url, params=params)
        soup = self._parse_html(html)

        # Parse results
        cases = []
        results_table = soup.find("table", {"class": "results"})

        if results_table:
            for row in results_table.find_all("tr")[1 : max_results + 1]:
                cells = row.find_all("td")
                if len(cells) >= 5:
                    case = CourtCase(
                        case_number=cells[0].get_text(strip=True),
                        court_name="Wisconsin Circuit Court",
                        court_type=self.COURT_TYPE,
                        court_level=self.COURT_LEVEL,
                        county=cells[1].get_text(strip=True),
                        case_type=self._parse_case_type(cells[2].get_text(strip=True)),
                        case_type_raw=cells[2].get_text(strip=True),
                        filing_date=self._parse_date(cells[3].get_text(strip=True)),
                        case_title=cells[4].get_text(strip=True),
                        state=self.STATE,
                        source_system="Wisconsin CCAP",
                    )
                    cases.append(case)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            cases=cases,
            total_count=len(cases),
            page_number=1,
            page_size=max_results,
            has_more=False,
            search_criteria=SearchCriteria(party_name=party_name),
            search_time_ms=search_time,
            source_system="Wisconsin CCAP",
        )

    async def search_by_case_number(self, case_number: str) -> Optional[CourtCase]:
        """Search for a specific case by case number."""
        search_url = f"{self.BASE_URL}caseDetail.html"

        params = {"caseNo": case_number}

        status, html = await self._fetch(search_url, params=params)
        if status != 200:
            return None

        soup = self._parse_html(html)
        return self._parse_wi_case_detail(soup, case_number)

    async def get_case_detail(self, case_number: str) -> Optional[CourtCase]:
        """Get detailed case information."""
        return await self.search_by_case_number(case_number)

    def _parse_wi_case_detail(self, soup: BeautifulSoup, case_number: str) -> CourtCase:
        """Parse Wisconsin case detail page."""
        case = CourtCase(
            case_number=case_number,
            court_name="Wisconsin Circuit Court",
            court_type=self.COURT_TYPE,
            court_level=self.COURT_LEVEL,
            state=self.STATE,
            source_system="Wisconsin CCAP",
        )

        # CCAP uses definition lists for case info
        for dl in soup.find_all("dl"):
            for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)

                if "case number" in label:
                    case.case_number = value
                elif "county" in label:
                    case.county = value
                elif "case type" in label:
                    case.case_type = self._parse_case_type(value)
                    case.case_type_raw = value
                elif "filing date" in label:
                    case.filing_date = self._parse_date(value)
                elif "status" in label:
                    case.status = self._parse_case_status(value)
                elif "judge" in label:
                    case.judge = value

        return case


class MissouriCaseNet(StateCourtBase):
    """
    Missouri Case.net scraper.

    Missouri's Case.net is another excellent state court access system.
    https://www.courts.mo.gov/casenet/

    Provides access to:
    - All Missouri state courts
    - Case parties and attorneys
    - Charges, judgments, and sentences
    - Docket entries
    """

    COURT_NAME = "Missouri Courts"
    COURT_TYPE = CourtType.STATE_TRIAL
    COURT_LEVEL = CourtLevel.TRIAL
    STATE = "MO"
    BASE_URL = "https://www.courts.mo.gov/casenet/"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize Missouri Case.net scraper."""
        super().__init__("MO", session)

    async def search_by_party(
        self,
        party_name: str,
        party_type: str = "any",
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        case_types: Optional[List[CaseType]] = None,
        include_closed: bool = True,
        max_results: int = 100,
    ) -> SearchResult:
        """Search Missouri courts by party name."""
        import time

        start_time = time.time()

        search_url = f"{self.BASE_URL}cases/searchCases.do"

        params = {
            "inputVO.lastName": party_name,
            "inputVO.courtId": "SW",  # Statewide
        }

        status, html = await self._fetch(search_url, params=params)
        soup = self._parse_html(html)

        # Parse results
        cases = []
        results_table = soup.find("table", {"id": "caseList"})

        if results_table:
            for row in results_table.find_all("tr")[1 : max_results + 1]:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    case = CourtCase(
                        case_number=cells[0].get_text(strip=True),
                        court_name=cells[1].get_text(strip=True),
                        court_type=self.COURT_TYPE,
                        court_level=self.COURT_LEVEL,
                        case_type=self._parse_case_type(cells[2].get_text(strip=True)),
                        filing_date=self._parse_date(cells[3].get_text(strip=True)),
                        state=self.STATE,
                        source_system="Missouri Case.net",
                    )
                    cases.append(case)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            cases=cases,
            total_count=len(cases),
            page_number=1,
            page_size=max_results,
            has_more=False,
            search_criteria=SearchCriteria(party_name=party_name),
            search_time_ms=search_time,
            source_system="Missouri Case.net",
        )

    async def search_by_case_number(self, case_number: str) -> Optional[CourtCase]:
        """Search for a specific case."""
        search_url = f"{self.BASE_URL}cases/searchCases.do"

        params = {"inputVO.caseNumber": case_number}

        status, html = await self._fetch(search_url, params=params)
        if status != 200:
            return None

        soup = self._parse_html(html)

        case_header = soup.find("div", {"class": "caseHeader"})
        if not case_header:
            return None

        return CourtCase(
            case_number=case_number,
            court_name=self.COURT_NAME,
            court_type=self.COURT_TYPE,
            court_level=self.COURT_LEVEL,
            state=self.STATE,
            source_system="Missouri Case.net",
        )

    async def get_case_detail(self, case_number: str) -> Optional[CourtCase]:
        """Get detailed case information."""
        return await self.search_by_case_number(case_number)


# Factory function to get state court scraper


def get_state_court_scraper(state_code: str) -> Optional[StateCourtBase]:
    """
    Get a state court scraper for a specific state.

    Args:
        state_code: Two-letter state code (e.g., "PA", "WI", "MO")

    Returns:
        Configured StateCourtBase instance or None
    """
    state_code = state_code.upper()

    scrapers = {
        "PA": PennsylvaniaUJS,
        "WI": WisconsinCCAP,
        "MO": MissouriCaseNet,
    }

    scraper_class = scrapers.get(state_code)
    if scraper_class:
        return scraper_class()

    # Return generic for unsupported states
    return StateCourtBase(state_code)


def list_state_court_systems() -> List[Dict[str, Any]]:
    """List all configured state court systems."""
    systems = []
    for code, info in STATE_COURT_SYSTEMS.items():
        systems.append(
            {
                "state_code": code,
                "state_name": info.state_name,
                "system_type": info.system_type.value,
                "has_statewide_search": info.has_statewide_search,
                "requires_registration": info.requires_registration,
                "public_access_url": info.public_access_url,
            }
        )
    return systems


# Synchronous wrapper functions


def search_state_cases(state_code: str, party_name: str, **kwargs) -> SearchResult:
    """Synchronous wrapper for state court party search."""
    scraper = get_state_court_scraper(state_code)
    if not scraper:
        raise ValueError(f"No state court scraper for {state_code}")

    async def _search():
        async with scraper:
            return await scraper.search_by_party(party_name, **kwargs)

    return asyncio.run(_search())


def get_state_case(state_code: str, case_number: str) -> Optional[CourtCase]:
    """Synchronous wrapper for state court case detail."""
    scraper = get_state_court_scraper(state_code)
    if not scraper:
        raise ValueError(f"No state court scraper for {state_code}")

    async def _get():
        async with scraper:
            return await scraper.get_case_detail(case_number)

    return asyncio.run(_get())
