"""
Tyler Odyssey Court System Scraper

Tyler Technologies' Odyssey is the most common court case management system
used by state and county courts across the United States. This module provides
a base class for scraping Odyssey-based court systems.

Key features:
- Common UI patterns across implementations
- Portal-based public access
- Case search by party name, case number, date range
- Docket and document access
- Some jurisdictions require registration for full access

Tyler Odyssey installations vary by state/county, so specific implementations
should extend this base class.
"""

import asyncio
import logging
import re
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup

from .base import (
    CourtSystemBase,
    CourtType,
    CourtLevel,
    CaseType,
    CaseStatus,
    PartyType,
    PartyRole,
    CourtCase,
    CaseParty,
    CaseEvent,
    CaseDocument,
    CaseCharge,
    SearchCriteria,
    SearchResult,
)

logger = logging.getLogger(__name__)


class OdysseyPortalType(Enum):
    """Types of Odyssey public access portals."""
    PORTAL = "portal"  # Odyssey Portal (newer)
    PAWS = "paws"  # Public Access Web Services
    ECLERK = "eclerk"  # eClerk
    ICMS = "icms"  # Integrated Case Management System
    EFILING = "efiling"  # eFiling portal with public search
    CUSTOM = "custom"


@dataclass
class OdysseyLocation:
    """Configuration for a specific Odyssey installation."""
    state: str
    county: str
    court_name: str
    base_url: str
    portal_type: OdysseyPortalType
    fips_code: str
    court_types: List[CourtType]
    requires_registration: bool = False
    has_criminal: bool = True
    has_civil: bool = True
    has_family: bool = True
    has_probate: bool = True
    has_traffic: bool = True


# Major Odyssey installations across the US
ODYSSEY_INSTALLATIONS: Dict[str, OdysseyLocation] = {
    # Texas - Statewide
    "tx_statewide": OdysseyLocation(
        state="TX",
        county="Statewide",
        court_name="Texas Courts",
        base_url="https://www.txcourts.gov/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="48",
        court_types=[CourtType.STATE_TRIAL, CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL],
        requires_registration=False,
    ),
    # Harris County, TX
    "tx_harris": OdysseyLocation(
        state="TX",
        county="Harris",
        court_name="Harris County District Courts",
        base_url="https://www.hcdistrictclerk.com/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="48201",
        court_types=[CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL, CourtType.COUNTY_FAMILY],
        requires_registration=True,
    ),
    # Dallas County, TX
    "tx_dallas": OdysseyLocation(
        state="TX",
        county="Dallas",
        court_name="Dallas County Courts",
        base_url="https://www.dallascounty.org/departments/districtclerk/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="48113",
        court_types=[CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL, CourtType.COUNTY_FAMILY],
        requires_registration=True,
    ),
    # Tarrant County, TX
    "tx_tarrant": OdysseyLocation(
        state="TX",
        county="Tarrant",
        court_name="Tarrant County Courts",
        base_url="https://www.tarrantcounty.com/en/district-clerk.html",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="48439",
        court_types=[CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL],
        requires_registration=False,
    ),
    # Indiana - Statewide
    "in_statewide": OdysseyLocation(
        state="IN",
        county="Statewide",
        court_name="Indiana Courts",
        base_url="https://public.courts.in.gov/mycase/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="18",
        court_types=[CourtType.STATE_TRIAL, CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL],
        requires_registration=False,
    ),
    # Minnesota - Statewide
    "mn_statewide": OdysseyLocation(
        state="MN",
        county="Statewide",
        court_name="Minnesota Courts",
        base_url="https://publicaccess.courts.state.mn.us/",
        portal_type=OdysseyPortalType.PAWS,
        fips_code="27",
        court_types=[CourtType.STATE_TRIAL, CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL],
        requires_registration=False,
    ),
    # Washington - Statewide
    "wa_statewide": OdysseyLocation(
        state="WA",
        county="Statewide",
        court_name="Washington Courts",
        base_url="https://dw.courts.wa.gov/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="53",
        court_types=[CourtType.STATE_TRIAL, CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL],
        requires_registration=False,
    ),
    # Georgia - Statewide
    "ga_statewide": OdysseyLocation(
        state="GA",
        county="Statewide",
        court_name="Georgia Courts",
        base_url="https://publicaccess.courts.state.ga.us/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="13",
        court_types=[CourtType.STATE_TRIAL, CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL],
        requires_registration=False,
    ),
    # Oregon - Statewide
    "or_statewide": OdysseyLocation(
        state="OR",
        county="Statewide",
        court_name="Oregon Courts",
        base_url="https://webportal.courts.oregon.gov/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="41",
        court_types=[CourtType.STATE_TRIAL, CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL],
        requires_registration=False,
    ),
    # Arizona - Maricopa County
    "az_maricopa": OdysseyLocation(
        state="AZ",
        county="Maricopa",
        court_name="Maricopa County Superior Court",
        base_url="https://www.superiorcourt.maricopa.gov/",
        portal_type=OdysseyPortalType.ICMS,
        fips_code="04013",
        court_types=[CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL, CourtType.COUNTY_FAMILY, CourtType.COUNTY_PROBATE],
        requires_registration=False,
    ),
    # California - Los Angeles
    "ca_losangeles": OdysseyLocation(
        state="CA",
        county="Los Angeles",
        court_name="Los Angeles Superior Court",
        base_url="https://www.lacourt.org/",
        portal_type=OdysseyPortalType.CUSTOM,
        fips_code="06037",
        court_types=[CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL, CourtType.COUNTY_FAMILY, CourtType.COUNTY_PROBATE],
        requires_registration=True,
    ),
    # Nevada - Clark County
    "nv_clark": OdysseyLocation(
        state="NV",
        county="Clark",
        court_name="Clark County Courts",
        base_url="https://www.clarkcountycourts.us/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="32003",
        court_types=[CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL, CourtType.COUNTY_FAMILY],
        requires_registration=False,
    ),
    # Colorado - Denver
    "co_denver": OdysseyLocation(
        state="CO",
        county="Denver",
        court_name="Denver County Courts",
        base_url="https://www.courts.state.co.us/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="08031",
        court_types=[CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL],
        requires_registration=False,
    ),
    # Tennessee - Statewide
    "tn_statewide": OdysseyLocation(
        state="TN",
        county="Statewide",
        court_name="Tennessee Courts",
        base_url="https://caselink.tncourts.gov/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="47",
        court_types=[CourtType.STATE_TRIAL, CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL],
        requires_registration=False,
    ),
    # Kentucky - Statewide
    "ky_statewide": OdysseyLocation(
        state="KY",
        county="Statewide",
        court_name="Kentucky Courts",
        base_url="https://kcoj.kycourts.net/",
        portal_type=OdysseyPortalType.PORTAL,
        fips_code="21",
        court_types=[CourtType.STATE_TRIAL, CourtType.COUNTY_CIVIL, CourtType.COUNTY_CRIMINAL],
        requires_registration=False,
    ),
}


class TylerOdysseyBase(CourtSystemBase):
    """
    Base class for Tyler Odyssey court system scrapers.

    Tyler Odyssey is used by numerous state and county courts. While the
    core functionality is similar, each installation has variations in:
    - URL structure
    - Field names and IDs
    - Available search options
    - Output formatting

    Subclasses should implement the abstract methods for their specific installation.
    """

    SYSTEM_VENDOR = "Tyler Technologies"
    SYSTEM_NAME = "Odyssey"

    def __init__(
        self,
        location: OdysseyLocation,
        session: Optional[aiohttp.ClientSession] = None
    ):
        """Initialize the Odyssey scraper."""
        super().__init__(session)
        self.location = location
        self.BASE_URL = location.base_url
        self.STATE = location.state
        self.COUNTY = location.county
        self.COURT_NAME = location.court_name

        # Set appropriate court type
        if location.court_types:
            self.COURT_TYPE = location.court_types[0]

        self._viewstate: Optional[str] = None
        self._eventvalidation: Optional[str] = None

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Odyssey requests."""
        headers = super()._get_headers()
        headers.update({
            "Referer": self.BASE_URL,
            "Origin": self.BASE_URL.rstrip("/"),
        })
        return headers

    async def _extract_viewstate(self, html: str) -> Dict[str, str]:
        """Extract ASP.NET ViewState and EventValidation from page."""
        soup = self._parse_html(html)

        viewstate_data = {}

        viewstate = soup.find("input", {"name": "__VIEWSTATE"})
        if viewstate:
            viewstate_data["__VIEWSTATE"] = viewstate.get("value", "")
            self._viewstate = viewstate_data["__VIEWSTATE"]

        viewstate_gen = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})
        if viewstate_gen:
            viewstate_data["__VIEWSTATEGENERATOR"] = viewstate_gen.get("value", "")

        event_validation = soup.find("input", {"name": "__EVENTVALIDATION"})
        if event_validation:
            viewstate_data["__EVENTVALIDATION"] = event_validation.get("value", "")
            self._eventvalidation = viewstate_data["__EVENTVALIDATION"]

        event_target = soup.find("input", {"name": "__EVENTTARGET"})
        if event_target:
            viewstate_data["__EVENTTARGET"] = event_target.get("value", "")

        event_argument = soup.find("input", {"name": "__EVENTARGUMENT"})
        if event_argument:
            viewstate_data["__EVENTARGUMENT"] = event_argument.get("value", "")

        return viewstate_data

    def _parse_odyssey_case_type(self, raw_type: str) -> CaseType:
        """Parse Odyssey-specific case type codes."""
        if not raw_type:
            return CaseType.UNKNOWN

        raw_type = raw_type.upper().strip()

        # Odyssey case type codes
        odyssey_types = {
            # Civil
            "CV": CaseType.CIVIL_GENERAL,
            "CIV": CaseType.CIVIL_GENERAL,
            "CIVIL": CaseType.CIVIL_GENERAL,
            "CT": CaseType.CONTRACT,
            "TT": CaseType.TORT,
            "EJ": CaseType.EVICTION,
            "EVIC": CaseType.EVICTION,
            "FD": CaseType.FORECLOSURE,
            "FOR": CaseType.FORECLOSURE,
            "SC": CaseType.SMALL_CLAIMS,
            "SM": CaseType.SMALL_CLAIMS,
            "PJ": CaseType.PERSONAL_INJURY,
            "DC": CaseType.DEBT_COLLECTION,

            # Criminal
            "CR": CaseType.CRIMINAL_FELONY,
            "CRIM": CaseType.CRIMINAL_FELONY,
            "CF": CaseType.CRIMINAL_FELONY,
            "FEL": CaseType.CRIMINAL_FELONY,
            "CM": CaseType.CRIMINAL_MISDEMEANOR,
            "MIS": CaseType.CRIMINAL_MISDEMEANOR,
            "MISD": CaseType.CRIMINAL_MISDEMEANOR,
            "DUI": CaseType.DUI_DWI,
            "DWI": CaseType.DUI_DWI,
            "TR": CaseType.TRAFFIC,
            "TRF": CaseType.TRAFFIC,
            "TRA": CaseType.TRAFFIC,

            # Family
            "DR": CaseType.DIVORCE,
            "DIV": CaseType.DIVORCE,
            "DI": CaseType.DIVORCE,
            "FM": CaseType.DIVORCE,  # Family
            "CU": CaseType.CHILD_CUSTODY,
            "CS": CaseType.CHILD_SUPPORT,
            "DV": CaseType.DOMESTIC_VIOLENCE,
            "PO": CaseType.DOMESTIC_VIOLENCE,  # Protection order
            "AD": CaseType.ADOPTION,
            "GU": CaseType.GUARDIANSHIP,
            "PA": CaseType.PATERNITY,

            # Probate
            "PB": CaseType.PROBATE_ESTATE,
            "PR": CaseType.PROBATE_ESTATE,
            "EST": CaseType.PROBATE_ESTATE,
            "ES": CaseType.PROBATE_ESTATE,
            "TU": CaseType.PROBATE_TRUST,
            "TR": CaseType.PROBATE_TRUST,
            "CO": CaseType.CONSERVATORSHIP,

            # Juvenile
            "JV": CaseType.OTHER,  # Juvenile (often restricted)
            "JC": CaseType.OTHER,  # Juvenile criminal
            "JD": CaseType.OTHER,  # Juvenile dependency

            # Other
            "MH": CaseType.OTHER,  # Mental health
            "AP": CaseType.APPEAL,
            "WR": CaseType.OTHER,  # Writ
        }

        if raw_type in odyssey_types:
            return odyssey_types[raw_type]

        # Check prefixes
        for prefix, case_type in odyssey_types.items():
            if raw_type.startswith(prefix):
                return case_type

        return self._parse_case_type(raw_type)

    def _parse_odyssey_party_role(self, raw_role: str) -> PartyRole:
        """Parse Odyssey-specific party role codes."""
        if not raw_role:
            return PartyRole.UNKNOWN

        raw_role = raw_role.upper().strip()

        role_mappings = {
            # Plaintiff-side
            "PLAINTIFF": PartyRole.PLAINTIFF,
            "PLTF": PartyRole.PLAINTIFF,
            "PETITIONER": PartyRole.PETITIONER,
            "PETR": PartyRole.PETITIONER,
            "COMPLAINANT": PartyRole.PLAINTIFF,
            "APPLICANT": PartyRole.APPLICANT,
            "MOVANT": PartyRole.PLAINTIFF,

            # Defendant-side
            "DEFENDANT": PartyRole.DEFENDANT,
            "DEF": PartyRole.DEFENDANT,
            "DFND": PartyRole.DEFENDANT,
            "RESPONDENT": PartyRole.RESPONDENT,
            "RESP": PartyRole.RESPONDENT,

            # Criminal
            "STATE": PartyRole.PROSECUTION,
            "PEOPLE": PartyRole.PROSECUTION,
            "COMMONWEALTH": PartyRole.PROSECUTION,
            "PROSECUTION": PartyRole.PROSECUTION,
            "DA": PartyRole.PROSECUTION,

            # Bankruptcy
            "DEBTOR": PartyRole.DEBTOR,
            "CREDITOR": PartyRole.CREDITOR,
            "TRUSTEE": PartyRole.TRUSTEE,

            # Family
            "MOTHER": PartyRole.PETITIONER,
            "FATHER": PartyRole.RESPONDENT,
            "CHILD": PartyRole.MINOR,
            "MINOR": PartyRole.MINOR,
            "GUARDIAN": PartyRole.GUARDIAN,
            "GAL": PartyRole.GUARDIAN_AD_LITEM,

            # Attorneys
            "ATTORNEY": PartyRole.ATTORNEY,
            "ATTY": PartyRole.ATTORNEY,
            "COUNSEL": PartyRole.ATTORNEY,

            # Third parties
            "INTERVENOR": PartyRole.INTERVENOR,
            "THIRD PARTY": PartyRole.THIRD_PARTY_DEFENDANT,
            "3RD PARTY": PartyRole.THIRD_PARTY_DEFENDANT,
            "CROSS-DEFENDANT": PartyRole.CROSS_DEFENDANT,
            "CROSS-PLAINTIFF": PartyRole.CROSS_PLAINTIFF,

            # Appeals
            "APPELLANT": PartyRole.APPELLANT,
            "APPELLEE": PartyRole.APPELLEE,
        }

        if raw_role in role_mappings:
            return role_mappings[raw_role]

        for key, role in role_mappings.items():
            if key in raw_role:
                return role

        return PartyRole.UNKNOWN

    def _extract_case_number_parts(self, case_number: str) -> Dict[str, str]:
        """Extract parts from an Odyssey case number."""
        parts = {}

        # Common Odyssey formats:
        # 2024-CV-001234  (year-type-sequence)
        # CV2024-001234   (type+year-sequence)
        # 24-2-01234-SEA  (year-district-sequence-location)
        # D-1-CV-24-001234 (court-division-type-year-sequence)

        # Pattern 1: YYYY-TT-NNNNNN
        pattern1 = re.match(r"(\d{4})-([A-Z]{2,4})-(\d+)", case_number)
        if pattern1:
            parts["year"] = pattern1.group(1)
            parts["type"] = pattern1.group(2)
            parts["sequence"] = pattern1.group(3)
            return parts

        # Pattern 2: TT-YYYY-NNNNNN or TTYYYY-NNNNNN
        pattern2 = re.match(r"([A-Z]{2,4})-?(\d{2,4})-(\d+)", case_number)
        if pattern2:
            parts["type"] = pattern2.group(1)
            year = pattern2.group(2)
            if len(year) == 2:
                year = "20" + year if int(year) < 50 else "19" + year
            parts["year"] = year
            parts["sequence"] = pattern2.group(3)
            return parts

        # Pattern 3: YY-D-NNNNNN-LOC (Washington style)
        pattern3 = re.match(r"(\d{2})-(\d)-(\d+)-([A-Z]{3})", case_number)
        if pattern3:
            year = pattern3.group(1)
            parts["year"] = "20" + year if int(year) < 50 else "19" + year
            parts["district"] = pattern3.group(2)
            parts["sequence"] = pattern3.group(3)
            parts["location"] = pattern3.group(4)
            return parts

        return parts

    def _parse_search_results_table(
        self,
        soup: BeautifulSoup,
        table_id: str = None
    ) -> List[Dict[str, str]]:
        """Parse a results table from Odyssey search results."""
        results = []

        # Find results table
        if table_id:
            table = soup.find("table", {"id": table_id})
        else:
            # Try common table IDs/classes
            table = (
                soup.find("table", {"id": "SearchResults"}) or
                soup.find("table", {"class": "results"}) or
                soup.find("table", {"class": "grid"}) or
                soup.find("table", {"id": "grdResults"}) or
                soup.find("table", {"id": "tblResults"})
            )

        if not table:
            return results

        # Get headers
        headers = []
        header_row = table.find("tr", {"class": "header"}) or table.find("thead")
        if header_row:
            for th in header_row.find_all(["th", "td"]):
                header_text = th.get_text(strip=True).lower().replace(" ", "_")
                headers.append(header_text)
        else:
            # Try first row
            first_row = table.find("tr")
            if first_row:
                for td in first_row.find_all(["th", "td"]):
                    header_text = td.get_text(strip=True).lower().replace(" ", "_")
                    headers.append(header_text)

        # Parse data rows
        tbody = table.find("tbody") or table
        for row in tbody.find_all("tr"):
            if "header" in row.get("class", []):
                continue

            cells = row.find_all("td")
            if not cells:
                continue

            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    key = headers[i]
                else:
                    key = f"col_{i}"

                # Check for links
                link = cell.find("a")
                if link:
                    row_data[f"{key}_link"] = link.get("href", "")

                row_data[key] = cell.get_text(strip=True)

            if row_data:
                results.append(row_data)

        return results

    def _build_case_from_row(self, row_data: Dict[str, str]) -> CourtCase:
        """Build a CourtCase from a search result row."""
        # Map common column names
        case_number = (
            row_data.get("case_number") or
            row_data.get("case_no") or
            row_data.get("case#") or
            row_data.get("case_id") or
            ""
        )

        case_title = (
            row_data.get("case_title") or
            row_data.get("case_name") or
            row_data.get("style") or
            row_data.get("caption") or
            ""
        )

        case_type_raw = (
            row_data.get("case_type") or
            row_data.get("type") or
            row_data.get("category") or
            ""
        )

        status_raw = (
            row_data.get("status") or
            row_data.get("case_status") or
            ""
        )

        filing_date_raw = (
            row_data.get("filing_date") or
            row_data.get("filed_date") or
            row_data.get("filed") or
            row_data.get("file_date") or
            ""
        )

        return CourtCase(
            case_number=case_number,
            court_name=self.COURT_NAME,
            court_type=self.COURT_TYPE,
            court_level=self.COURT_LEVEL,
            case_title=case_title,
            case_type=self._parse_odyssey_case_type(case_type_raw),
            case_type_raw=case_type_raw,
            status=self._parse_case_status(status_raw),
            filing_date=self._parse_date(filing_date_raw),
            state=self.STATE,
            county=self.COUNTY,
            source_url=row_data.get("case_number_link", ""),
            source_system="Tyler Odyssey",
            raw_data=row_data,
        )

    @abstractmethod
    async def _get_search_page(self) -> str:
        """Get the search page HTML and initialize session."""
        pass

    @abstractmethod
    async def _execute_search(
        self,
        search_type: str,
        search_params: Dict[str, Any]
    ) -> str:
        """Execute a search and return results HTML."""
        pass

    @abstractmethod
    async def _fetch_case_page(self, case_number: str) -> str:
        """Fetch the case detail page HTML."""
        pass

    async def search_by_party(
        self,
        party_name: str,
        party_type: str = "any",
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        case_types: Optional[List[CaseType]] = None,
        include_closed: bool = True,
        max_results: int = 100
    ) -> SearchResult:
        """Search for cases by party name."""
        import time
        start_time = time.time()

        # Initialize session by loading search page
        await self._get_search_page()

        # Build search parameters
        search_params = {
            "party_name": party_name,
            "party_type": party_type,
            "start_date": filed_start_date.strftime("%m/%d/%Y") if filed_start_date else "",
            "end_date": filed_end_date.strftime("%m/%d/%Y") if filed_end_date else "",
            "include_closed": include_closed,
        }

        # Execute search
        html = await self._execute_search("party", search_params)
        soup = self._parse_html(html)

        # Parse results
        results = self._parse_search_results_table(soup)

        cases = []
        for row_data in results[:max_results]:
            case = self._build_case_from_row(row_data)
            if case.case_number:
                cases.append(case)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            cases=cases,
            total_count=len(cases),
            page_number=1,
            page_size=max_results,
            has_more=len(results) > max_results,
            search_criteria=SearchCriteria(party_name=party_name),
            search_time_ms=search_time,
            source_system="Tyler Odyssey",
        )

    async def search_by_case_number(
        self,
        case_number: str
    ) -> Optional[CourtCase]:
        """Search for a case by case number."""
        # Initialize session
        await self._get_search_page()

        # Build search parameters
        search_params = {"case_number": case_number}

        # Execute search
        html = await self._execute_search("case_number", search_params)
        soup = self._parse_html(html)

        # Parse results
        results = self._parse_search_results_table(soup)

        if results:
            return self._build_case_from_row(results[0])

        return None

    async def get_case_detail(
        self,
        case_number: str
    ) -> Optional[CourtCase]:
        """Get detailed case information including docket."""
        html = await self._fetch_case_page(case_number)
        if not html:
            return None

        soup = self._parse_html(html)

        # Parse case header information
        case = self._parse_case_header(soup, case_number)

        # Parse parties
        case.parties = self._parse_parties(soup)

        # Parse events/docket
        case.events = self._parse_events(soup)

        # Parse documents
        case.documents = self._parse_documents(soup)

        # Parse charges (for criminal cases)
        if case.case_type in {CaseType.CRIMINAL_FELONY, CaseType.CRIMINAL_MISDEMEANOR,
                              CaseType.DUI_DWI, CaseType.TRAFFIC_CRIMINAL}:
            case.charges = self._parse_charges(soup)

        return case

    def _parse_case_header(self, soup: BeautifulSoup, case_number: str) -> CourtCase:
        """Parse the case header section."""
        # This implementation handles common Odyssey layouts
        # Subclasses should override for specific variations

        case = CourtCase(
            case_number=case_number,
            court_name=self.COURT_NAME,
            court_type=self.COURT_TYPE,
            court_level=self.COURT_LEVEL,
            state=self.STATE,
            county=self.COUNTY,
            source_system="Tyler Odyssey",
        )

        # Try common header patterns
        # Pattern 1: Definition list (dl/dt/dd)
        dl = soup.find("dl", {"class": "case-header"}) or soup.find("dl")
        if dl:
            for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)

                if "case number" in label or "case no" in label:
                    case.case_number = value
                elif "case type" in label or "category" in label:
                    case.case_type = self._parse_odyssey_case_type(value)
                    case.case_type_raw = value
                elif "status" in label:
                    case.status = self._parse_case_status(value)
                elif "filed" in label or "filing date" in label:
                    case.filing_date = self._parse_date(value)
                elif "judge" in label:
                    case.judge = value
                elif "style" in label or "caption" in label or "title" in label:
                    case.case_title = value

        # Pattern 2: Table layout
        header_table = soup.find("table", {"id": "caseHeader"}) or soup.find("table", {"class": "header"})
        if header_table:
            for row in header_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)

                    if "case" in label and "number" in label:
                        case.case_number = value
                    elif "type" in label:
                        case.case_type = self._parse_odyssey_case_type(value)
                        case.case_type_raw = value
                    elif "status" in label:
                        case.status = self._parse_case_status(value)
                    elif "filed" in label:
                        case.filing_date = self._parse_date(value)
                    elif "judge" in label:
                        case.judge = value

        return case

    def _parse_parties(self, soup: BeautifulSoup) -> List[CaseParty]:
        """Parse the parties section."""
        parties = []

        # Try common party section patterns
        party_section = (
            soup.find("div", {"id": "parties"}) or
            soup.find("section", {"id": "parties"}) or
            soup.find("table", {"id": "tblParties"})
        )

        if not party_section:
            return parties

        # Pattern 1: Table with party rows
        for row in party_section.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                name = cells[0].get_text(strip=True)
                role_raw = cells[1].get_text(strip=True) if len(cells) > 1 else ""

                if name:
                    party = CaseParty(
                        name=self._normalize_name(name),
                        role=self._parse_odyssey_party_role(role_raw),
                        raw_name=name,
                    )

                    # Check for attorney
                    if len(cells) > 2:
                        attorney_text = cells[2].get_text(strip=True)
                        if attorney_text:
                            party.attorney_name = attorney_text

                    parties.append(party)

        # Pattern 2: Definition list
        party_dl = party_section.find("dl")
        if party_dl:
            for dt, dd in zip(party_dl.find_all("dt"), party_dl.find_all("dd")):
                role_raw = dt.get_text(strip=True)
                name = dd.get_text(strip=True)

                if name:
                    parties.append(CaseParty(
                        name=self._normalize_name(name),
                        role=self._parse_odyssey_party_role(role_raw),
                        raw_name=name,
                    ))

        return parties

    def _parse_events(self, soup: BeautifulSoup) -> List[CaseEvent]:
        """Parse the docket/events section."""
        events = []

        # Try common docket section patterns
        docket_section = (
            soup.find("div", {"id": "docket"}) or
            soup.find("section", {"id": "events"}) or
            soup.find("table", {"id": "tblDocket"}) or
            soup.find("table", {"id": "grdDocket"})
        )

        if not docket_section:
            return events

        # Parse docket table
        for row in docket_section.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                date_str = cells[0].get_text(strip=True)
                description = cells[1].get_text(strip=True) if len(cells) > 1 else ""

                event_date = self._parse_date(date_str)
                if event_date and description:
                    event = CaseEvent(
                        date=event_date,
                        description=description,
                    )

                    # Check for document link
                    link = cells[1].find("a") if len(cells) > 1 else None
                    if link:
                        event.document_url = link.get("href", "")

                    # Additional columns
                    if len(cells) > 2:
                        event.filed_by = cells[2].get_text(strip=True)
                    if len(cells) > 3:
                        event.judge = cells[3].get_text(strip=True)

                    events.append(event)

        return events

    def _parse_documents(self, soup: BeautifulSoup) -> List[CaseDocument]:
        """Parse the documents section."""
        documents = []

        doc_section = (
            soup.find("div", {"id": "documents"}) or
            soup.find("table", {"id": "tblDocuments"})
        )

        if not doc_section:
            return documents

        for row in doc_section.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                doc_num = cells[0].get_text(strip=True)
                title = cells[1].get_text(strip=True) if len(cells) > 1 else ""

                if doc_num or title:
                    doc = CaseDocument(
                        document_number=doc_num,
                        title=title,
                    )

                    # Check for link
                    link = row.find("a")
                    if link:
                        doc.url = link.get("href", "")

                    # Additional columns
                    if len(cells) > 2:
                        doc.filed_date = self._parse_date(cells[2].get_text(strip=True))
                    if len(cells) > 3:
                        doc.filed_by = cells[3].get_text(strip=True)

                    documents.append(doc)

        return documents

    def _parse_charges(self, soup: BeautifulSoup) -> List[CaseCharge]:
        """Parse the charges section for criminal cases."""
        charges = []

        charge_section = (
            soup.find("div", {"id": "charges"}) or
            soup.find("table", {"id": "tblCharges"})
        )

        if not charge_section:
            return charges

        for row in charge_section.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                statute = cells[0].get_text(strip=True)
                description = cells[1].get_text(strip=True) if len(cells) > 1 else ""

                if statute or description:
                    charge = CaseCharge(
                        statute=statute,
                        description=description,
                    )

                    # Additional columns
                    if len(cells) > 2:
                        charge.charge_level = cells[2].get_text(strip=True)
                    if len(cells) > 3:
                        charge.disposition = cells[3].get_text(strip=True)
                    if len(cells) > 4:
                        charge.disposition_date = self._parse_date(cells[4].get_text(strip=True))

                    charges.append(charge)

        return charges


class IndianaMyCase(TylerOdysseyBase):
    """
    Indiana MyCase court system scraper.

    Indiana's MyCase (https://public.courts.in.gov/mycase/) is one of the
    best-designed Odyssey implementations with statewide coverage and
    free public access.
    """

    COURT_NAME = "Indiana Courts"
    COURT_TYPE = CourtType.STATE_TRIAL
    COURT_LEVEL = CourtLevel.TRIAL
    STATE = "IN"
    BASE_URL = "https://public.courts.in.gov/mycase/"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize Indiana MyCase scraper."""
        location = ODYSSEY_INSTALLATIONS["in_statewide"]
        super().__init__(location, session)

    async def _get_search_page(self) -> str:
        """Get the MyCase search page."""
        status, html = await self._fetch(f"{self.BASE_URL}Search.aspx")
        if status == 200:
            await self._extract_viewstate(html)
        return html

    async def _execute_search(
        self,
        search_type: str,
        search_params: Dict[str, Any]
    ) -> str:
        """Execute a MyCase search."""
        url = f"{self.BASE_URL}Search.aspx"

        data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
        }

        if search_type == "party":
            data.update({
                "txtPartyName": search_params.get("party_name", ""),
                "ddlPartyType": search_params.get("party_type", "Both"),
                "txtStartDate": search_params.get("start_date", ""),
                "txtEndDate": search_params.get("end_date", ""),
                "btnPartySearch": "Search",
            })
        elif search_type == "case_number":
            data.update({
                "txtCaseNumber": search_params.get("case_number", ""),
                "btnCaseSearch": "Search",
            })

        status, html = await self._fetch(url, method="POST", data=data)
        return html

    async def _fetch_case_page(self, case_number: str) -> str:
        """Fetch case detail page."""
        url = f"{self.BASE_URL}CaseDetail.aspx?CaseID={case_number}"
        status, html = await self._fetch(url)
        return html if status == 200 else ""


class MinnesotaPA(TylerOdysseyBase):
    """
    Minnesota Public Access court system scraper.

    Minnesota's court system (https://publicaccess.courts.state.mn.us/)
    provides statewide access to case records.
    """

    COURT_NAME = "Minnesota Courts"
    COURT_TYPE = CourtType.STATE_TRIAL
    COURT_LEVEL = CourtLevel.TRIAL
    STATE = "MN"
    BASE_URL = "https://publicaccess.courts.state.mn.us/"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize Minnesota PA scraper."""
        location = ODYSSEY_INSTALLATIONS["mn_statewide"]
        super().__init__(location, session)

    async def _get_search_page(self) -> str:
        """Get the search page."""
        status, html = await self._fetch(f"{self.BASE_URL}CaseSearch")
        if status == 200:
            await self._extract_viewstate(html)
        return html

    async def _execute_search(
        self,
        search_type: str,
        search_params: Dict[str, Any]
    ) -> str:
        """Execute a search."""
        url = f"{self.BASE_URL}CaseSearch"

        data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
        }

        if search_type == "party":
            data.update({
                "LastName": search_params.get("party_name", ""),
                "SearchAction": "PartySearch",
            })
        elif search_type == "case_number":
            data.update({
                "CaseNumber": search_params.get("case_number", ""),
                "SearchAction": "CaseSearch",
            })

        status, html = await self._fetch(url, method="POST", data=data)
        return html

    async def _fetch_case_page(self, case_number: str) -> str:
        """Fetch case detail page."""
        url = f"{self.BASE_URL}CaseDetail?caseId={case_number}"
        status, html = await self._fetch(url)
        return html if status == 200 else ""


class WashingtonCourts(TylerOdysseyBase):
    """
    Washington Courts public access scraper.

    Washington's court system provides statewide access through
    https://dw.courts.wa.gov/
    """

    COURT_NAME = "Washington Courts"
    COURT_TYPE = CourtType.STATE_TRIAL
    COURT_LEVEL = CourtLevel.TRIAL
    STATE = "WA"
    BASE_URL = "https://dw.courts.wa.gov/"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize Washington Courts scraper."""
        location = ODYSSEY_INSTALLATIONS["wa_statewide"]
        super().__init__(location, session)

    async def _get_search_page(self) -> str:
        """Get the search page."""
        status, html = await self._fetch(f"{self.BASE_URL}index.cfm")
        return html

    async def _execute_search(
        self,
        search_type: str,
        search_params: Dict[str, Any]
    ) -> str:
        """Execute a search."""
        if search_type == "party":
            url = f"{self.BASE_URL}index.cfm?fa=home.namesearchresults"
            params = {
                "searchType": "name",
                "lastName": search_params.get("party_name", ""),
                "courtLevel": "S",  # Superior court
            }
        else:
            url = f"{self.BASE_URL}index.cfm?fa=home.casesearchresults"
            params = {
                "searchType": "case",
                "caseNumber": search_params.get("case_number", ""),
            }

        status, html = await self._fetch(url, params=params)
        return html

    async def _fetch_case_page(self, case_number: str) -> str:
        """Fetch case detail page."""
        url = f"{self.BASE_URL}index.cfm?fa=home.casedetail&caession={case_number}"
        status, html = await self._fetch(url)
        return html if status == 200 else ""


def get_odyssey_scraper(installation_key: str) -> Optional[TylerOdysseyBase]:
    """
    Get an Odyssey scraper instance by installation key.

    Args:
        installation_key: Key from ODYSSEY_INSTALLATIONS dict

    Returns:
        Configured TylerOdysseyBase instance or None
    """
    if installation_key not in ODYSSEY_INSTALLATIONS:
        return None

    location = ODYSSEY_INSTALLATIONS[installation_key]

    # Return specific implementation if available
    if installation_key == "in_statewide":
        return IndianaMyCase()
    elif installation_key == "mn_statewide":
        return MinnesotaPA()
    elif installation_key == "wa_statewide":
        return WashingtonCourts()

    # Return generic - won't work without implementing abstract methods
    logger.warning(f"No specific implementation for {installation_key}, using generic base")
    return None


def list_available_odyssey_installations() -> List[Dict[str, Any]]:
    """
    List all available Odyssey installations.

    Returns:
        List of installation info dictionaries
    """
    installations = []
    for key, location in ODYSSEY_INSTALLATIONS.items():
        installations.append({
            "key": key,
            "state": location.state,
            "county": location.county,
            "court_name": location.court_name,
            "portal_type": location.portal_type.value,
            "requires_registration": location.requires_registration,
            "court_types": [ct.value for ct in location.court_types],
        })
    return installations


# Synchronous wrapper functions

def search_odyssey_party(
    installation_key: str,
    party_name: str,
    **kwargs
) -> SearchResult:
    """Synchronous wrapper for Odyssey party search."""
    scraper = get_odyssey_scraper(installation_key)
    if not scraper:
        raise ValueError(f"Unknown Odyssey installation: {installation_key}")

    async def _search():
        async with scraper:
            return await scraper.search_by_party(party_name, **kwargs)
    return asyncio.run(_search())


def get_odyssey_case(
    installation_key: str,
    case_number: str
) -> Optional[CourtCase]:
    """Synchronous wrapper for Odyssey case detail."""
    scraper = get_odyssey_scraper(installation_key)
    if not scraper:
        raise ValueError(f"Unknown Odyssey installation: {installation_key}")

    async def _get():
        async with scraper:
            return await scraper.get_case_detail(case_number)
    return asyncio.run(_get())
