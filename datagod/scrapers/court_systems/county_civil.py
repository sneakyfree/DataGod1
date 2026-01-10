"""
County Civil Courts Scraper

Handles civil court cases at the county level, including:
- General civil litigation
- Landlord/tenant disputes (evictions, unlawful detainer)
- Foreclosures
- Small claims
- Contract disputes
- Personal injury
- Collections/debt
- Property disputes

Most county civil courts use one of several case management systems:
- Tyler Odyssey (most common)
- Thomson Reuters C-Track
- Journal Technologies eCourt
- Custom systems

This module provides both a generic base class and specific implementations
for high-population counties.
"""

import asyncio
import logging
import re
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
    SearchCriteria,
    SearchResult,
)

logger = logging.getLogger(__name__)


class CivilCaseSubtype(Enum):
    """Subtypes of civil cases commonly found in county courts."""
    # Contract
    BREACH_OF_CONTRACT = "breach_of_contract"
    COLLECTIONS = "collections"
    CREDIT_CARD_DEBT = "credit_card_debt"
    MEDICAL_DEBT = "medical_debt"

    # Real Property
    FORECLOSURE = "foreclosure"
    QUIET_TITLE = "quiet_title"
    PARTITION = "partition"
    BOUNDARY_DISPUTE = "boundary_dispute"
    EASEMENT = "easement"

    # Landlord/Tenant
    EVICTION = "eviction"
    UNLAWFUL_DETAINER = "unlawful_detainer"
    NONPAYMENT = "nonpayment"
    LEASE_VIOLATION = "lease_violation"
    HOLDOVER = "holdover"

    # Tort
    PERSONAL_INJURY = "personal_injury"
    NEGLIGENCE = "negligence"
    PREMISES_LIABILITY = "premises_liability"
    AUTO_ACCIDENT = "auto_accident"
    DEFAMATION = "defamation"

    # Small Claims
    SMALL_CLAIMS = "small_claims"

    # Other
    INJUNCTION = "injunction"
    DECLARATORY_JUDGMENT = "declaratory_judgment"
    MECHANICS_LIEN = "mechanics_lien"
    OTHER = "other"


@dataclass
class CivilJudgment:
    """A judgment in a civil case."""
    judgment_date: date
    judgment_type: str  # Default, Summary, Consent, etc.
    in_favor_of: str  # Party name
    against: str  # Party name
    principal_amount: Optional[float] = None
    interest_amount: Optional[float] = None
    costs_amount: Optional[float] = None
    attorney_fees: Optional[float] = None
    total_amount: Optional[float] = None
    is_satisfied: bool = False
    satisfaction_date: Optional[date] = None
    is_vacated: bool = False
    vacated_date: Optional[date] = None
    notes: Optional[str] = None


@dataclass
class EvictionRecord:
    """Specialized record for eviction cases."""
    case_number: str
    filing_date: date
    landlord_name: str
    tenant_name: str
    property_address: str

    # Case details
    eviction_type: str = ""  # Nonpayment, Lease Violation, etc.
    amount_owed: Optional[float] = None
    rent_amount: Optional[float] = None

    # Status
    status: CaseStatus = CaseStatus.UNKNOWN
    disposition: Optional[str] = None
    disposition_date: Optional[date] = None

    # Judgment
    judgment_for: Optional[str] = None  # landlord, tenant
    judgment_amount: Optional[float] = None
    possession_awarded: bool = False
    writ_of_possession_issued: bool = False
    writ_date: Optional[date] = None

    # Metadata
    court_name: str = ""
    county: str = ""
    state: str = ""
    source_url: Optional[str] = None


@dataclass
class ForeclosureRecord:
    """Specialized record for foreclosure cases."""
    case_number: str
    filing_date: date

    # Parties
    lender_name: str
    borrower_name: str
    property_address: str

    # Loan details
    original_loan_amount: Optional[float] = None
    unpaid_principal: Optional[float] = None
    loan_date: Optional[date] = None
    default_date: Optional[date] = None

    # Property
    parcel_id: Optional[str] = None
    property_type: Optional[str] = None  # SFR, Condo, etc.

    # Status
    status: CaseStatus = CaseStatus.UNKNOWN
    foreclosure_type: str = ""  # Judicial, Non-Judicial

    # Sale info
    sale_date: Optional[date] = None
    sale_amount: Optional[float] = None
    sale_location: Optional[str] = None

    # Outcome
    disposition: Optional[str] = None
    disposition_date: Optional[date] = None

    # Metadata
    court_name: str = ""
    county: str = ""
    state: str = ""
    source_url: Optional[str] = None


@dataclass
class SmallClaimCase:
    """Specialized record for small claims cases."""
    case_number: str
    filing_date: date

    # Parties
    plaintiff_name: str
    defendant_name: str

    # Claim
    claim_amount: float
    claim_description: str = ""

    # Hearing
    hearing_date: Optional[date] = None
    hearing_time: Optional[str] = None
    courtroom: Optional[str] = None

    # Status/Outcome
    status: CaseStatus = CaseStatus.UNKNOWN
    judgment_amount: Optional[float] = None
    judgment_for: Optional[str] = None  # plaintiff, defendant
    judgment_date: Optional[date] = None

    # Metadata
    court_name: str = ""
    county: str = ""
    state: str = ""
    source_url: Optional[str] = None


class CountyCivilCourtBase(CourtSystemBase):
    """
    Base class for county civil court scrapers.

    Provides common functionality for searching and extracting civil
    court records at the county level.
    """

    COURT_TYPE = CourtType.COUNTY_CIVIL
    COURT_LEVEL = CourtLevel.TRIAL

    # Civil case type mappings
    CASE_TYPE_PATTERNS = {
        # Eviction/Landlord-Tenant
        r"evict": CaseType.EVICTION,
        r"unlawful\s*detain": CaseType.EVICTION,
        r"forcible\s*(entry|detainer)": CaseType.EVICTION,
        r"ej\b": CaseType.EVICTION,
        r"f[&/]?ed": CaseType.EVICTION,  # FED, F&ED
        r"tenant": CaseType.LANDLORD_TENANT,
        r"landlord": CaseType.LANDLORD_TENANT,
        r"lt\b": CaseType.LANDLORD_TENANT,

        # Foreclosure
        r"foreclos": CaseType.FORECLOSURE,
        r"mtg\s*fc": CaseType.FORECLOSURE,
        r"mortgage": CaseType.FORECLOSURE,

        # Contract/Debt
        r"contract": CaseType.CONTRACT,
        r"debt": CaseType.DEBT_COLLECTION,
        r"collect": CaseType.DEBT_COLLECTION,
        r"credit\s*card": CaseType.DEBT_COLLECTION,
        r"breach": CaseType.CONTRACT,

        # Tort
        r"personal\s*injury": CaseType.PERSONAL_INJURY,
        r"pi\b": CaseType.PERSONAL_INJURY,
        r"negligence": CaseType.TORT,
        r"tort": CaseType.TORT,
        r"auto\s*(accident|neg)": CaseType.PERSONAL_INJURY,
        r"malpractice": CaseType.MEDICAL_MALPRACTICE,

        # Property
        r"property": CaseType.PROPERTY,
        r"quiet\s*title": CaseType.PROPERTY,
        r"partition": CaseType.PROPERTY,
        r"eject": CaseType.PROPERTY,

        # Small Claims
        r"small\s*claim": CaseType.SMALL_CLAIMS,
        r"sc\b": CaseType.SMALL_CLAIMS,
        r"minor\s*claim": CaseType.SMALL_CLAIMS,

        # General Civil
        r"civil": CaseType.CIVIL_GENERAL,
        r"cv\b": CaseType.CIVIL_GENERAL,
        r"civ\b": CaseType.CIVIL_GENERAL,
    }

    def _determine_civil_case_type(self, raw_type: str) -> CaseType:
        """Determine case type from raw type string."""
        if not raw_type:
            return CaseType.CIVIL_GENERAL

        raw_lower = raw_type.lower()

        for pattern, case_type in self.CASE_TYPE_PATTERNS.items():
            if re.search(pattern, raw_lower):
                return case_type

        return CaseType.CIVIL_GENERAL

    def _parse_judgment(self, soup: BeautifulSoup) -> Optional[CivilJudgment]:
        """Parse judgment information from case detail page."""
        # Look for judgment section
        judgment_section = (
            soup.find("div", {"id": "judgment"}) or
            soup.find("section", {"id": "judgment"}) or
            soup.find("table", {"id": "tblJudgment"})
        )

        if not judgment_section:
            return None

        # Extract judgment data
        judgment_data = {}

        # Parse table or definition list
        if judgment_section.name == "table":
            for row in judgment_section.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    judgment_data[label] = value

        if not judgment_data:
            return None

        # Build judgment record
        judgment_date = self._parse_date(
            judgment_data.get("date") or
            judgment_data.get("judgment date") or
            ""
        )

        if not judgment_date:
            return None

        return CivilJudgment(
            judgment_date=judgment_date,
            judgment_type=judgment_data.get("type", ""),
            in_favor_of=judgment_data.get("in favor of", ""),
            against=judgment_data.get("against", ""),
            principal_amount=self._parse_amount(judgment_data.get("principal", "")),
            interest_amount=self._parse_amount(judgment_data.get("interest", "")),
            costs_amount=self._parse_amount(judgment_data.get("costs", "")),
            attorney_fees=self._parse_amount(judgment_data.get("attorney fees", "")),
            total_amount=self._parse_amount(judgment_data.get("total", "")),
        )

    async def search_evictions(
        self,
        landlord_name: Optional[str] = None,
        tenant_name: Optional[str] = None,
        property_address: Optional[str] = None,
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        max_results: int = 100
    ) -> List[EvictionRecord]:
        """
        Search for eviction cases.

        Args:
            landlord_name: Landlord/plaintiff name
            tenant_name: Tenant/defendant name
            property_address: Property address
            filed_start_date: Start of filing date range
            filed_end_date: End of filing date range
            max_results: Maximum results to return

        Returns:
            List of EvictionRecord
        """
        # Search for eviction cases
        party_name = landlord_name or tenant_name
        if not party_name:
            return []

        results = await self.search_by_party(
            party_name=party_name,
            case_types=[CaseType.EVICTION, CaseType.LANDLORD_TENANT],
            filed_start_date=filed_start_date,
            filed_end_date=filed_end_date,
            max_results=max_results
        )

        # Convert to EvictionRecord
        evictions = []
        for case in results.cases:
            if case.case_type in {CaseType.EVICTION, CaseType.LANDLORD_TENANT}:
                evictions.append(self._case_to_eviction(case))

        return evictions

    def _case_to_eviction(self, case: CourtCase) -> EvictionRecord:
        """Convert a CourtCase to EvictionRecord."""
        landlord = ""
        tenant = ""

        for party in case.parties:
            if party.role == PartyRole.PLAINTIFF:
                landlord = party.name
            elif party.role == PartyRole.DEFENDANT:
                tenant = party.name

        if not landlord:
            landlord = case.plaintiffs[0] if case.plaintiffs else ""
        if not tenant:
            tenant = case.defendants[0] if case.defendants else ""

        return EvictionRecord(
            case_number=case.case_number,
            filing_date=case.filing_date or date.today(),
            landlord_name=landlord,
            tenant_name=tenant,
            property_address="",  # Often not in case summary
            status=case.status,
            disposition=case.disposition,
            judgment_amount=case.judgment_amount,
            court_name=case.court_name,
            county=case.county or self.COUNTY,
            state=case.state or self.STATE,
            source_url=case.source_url,
        )

    async def search_foreclosures(
        self,
        lender_name: Optional[str] = None,
        borrower_name: Optional[str] = None,
        property_address: Optional[str] = None,
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        max_results: int = 100
    ) -> List[ForeclosureRecord]:
        """
        Search for foreclosure cases.

        Args:
            lender_name: Lender/bank/plaintiff name
            borrower_name: Borrower/defendant name
            property_address: Property address
            filed_start_date: Start of filing date range
            filed_end_date: End of filing date range
            max_results: Maximum results to return

        Returns:
            List of ForeclosureRecord
        """
        party_name = lender_name or borrower_name
        if not party_name:
            return []

        results = await self.search_by_party(
            party_name=party_name,
            case_types=[CaseType.FORECLOSURE],
            filed_start_date=filed_start_date,
            filed_end_date=filed_end_date,
            max_results=max_results
        )

        foreclosures = []
        for case in results.cases:
            if case.case_type == CaseType.FORECLOSURE:
                foreclosures.append(self._case_to_foreclosure(case))

        return foreclosures

    def _case_to_foreclosure(self, case: CourtCase) -> ForeclosureRecord:
        """Convert a CourtCase to ForeclosureRecord."""
        lender = ""
        borrower = ""

        for party in case.parties:
            if party.role == PartyRole.PLAINTIFF:
                lender = party.name
            elif party.role == PartyRole.DEFENDANT:
                borrower = party.name

        if not lender:
            lender = case.plaintiffs[0] if case.plaintiffs else ""
        if not borrower:
            borrower = case.defendants[0] if case.defendants else ""

        return ForeclosureRecord(
            case_number=case.case_number,
            filing_date=case.filing_date or date.today(),
            lender_name=lender,
            borrower_name=borrower,
            property_address="",
            status=case.status,
            disposition=case.disposition,
            court_name=case.court_name,
            county=case.county or self.COUNTY,
            state=case.state or self.STATE,
            source_url=case.source_url,
        )

    async def search_small_claims(
        self,
        party_name: str,
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        max_results: int = 100
    ) -> List[SmallClaimCase]:
        """
        Search for small claims cases.

        Args:
            party_name: Party name to search
            filed_start_date: Start of filing date range
            filed_end_date: End of filing date range
            max_results: Maximum results to return

        Returns:
            List of SmallClaimCase
        """
        results = await self.search_by_party(
            party_name=party_name,
            case_types=[CaseType.SMALL_CLAIMS],
            filed_start_date=filed_start_date,
            filed_end_date=filed_end_date,
            max_results=max_results
        )

        small_claims = []
        for case in results.cases:
            if case.case_type == CaseType.SMALL_CLAIMS:
                small_claims.append(self._case_to_small_claim(case))

        return small_claims

    def _case_to_small_claim(self, case: CourtCase) -> SmallClaimCase:
        """Convert a CourtCase to SmallClaimCase."""
        plaintiff = case.plaintiffs[0] if case.plaintiffs else ""
        defendant = case.defendants[0] if case.defendants else ""

        return SmallClaimCase(
            case_number=case.case_number,
            filing_date=case.filing_date or date.today(),
            plaintiff_name=plaintiff,
            defendant_name=defendant,
            claim_amount=case.judgment_amount or 0,
            status=case.status,
            judgment_amount=case.judgment_amount,
            court_name=case.court_name,
            county=case.county or self.COUNTY,
            state=case.state or self.STATE,
            source_url=case.source_url,
        )


class CookCountyCivil(CountyCivilCourtBase):
    """
    Cook County, Illinois Civil Court Scraper.

    Cook County (Chicago) is the second largest county court system in the US.
    Civil cases are heard in the Circuit Court of Cook County.

    Public access: https://casesearch.cookcountyclerkofcourt.org/
    """

    COURT_NAME = "Circuit Court of Cook County - Civil Division"
    COUNTY = "Cook"
    STATE = "IL"
    FIPS_CODE = "17031"
    BASE_URL = "https://casesearch.cookcountyclerkofcourt.org/"

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
        """Search Cook County civil cases by party name."""
        import time
        start_time = time.time()

        # Get search page to initialize session
        status, html = await self._fetch(f"{self.BASE_URL}CivilCaseSearchAPI.aspx")

        # Execute search
        search_url = f"{self.BASE_URL}CivilCaseSearchAPI.aspx/SearchByParty"

        data = {
            "partyName": party_name,
            "partyType": "A" if party_type == "any" else ("P" if party_type == "plaintiff" else "D"),
            "startDate": filed_start_date.strftime("%m/%d/%Y") if filed_start_date else "",
            "endDate": filed_end_date.strftime("%m/%d/%Y") if filed_end_date else "",
        }

        try:
            json_response = await self._fetch_json(
                search_url,
                method="POST",
                json=data,
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            logger.error(f"Cook County search failed: {e}")
            return SearchResult(
                cases=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(party_name=party_name),
                warnings=[str(e)],
            )

        # Parse results
        cases = []
        case_data = json_response.get("d", [])

        for item in case_data[:max_results]:
            case = CourtCase(
                case_number=item.get("CaseNumber", ""),
                court_name=self.COURT_NAME,
                court_type=self.COURT_TYPE,
                court_level=self.COURT_LEVEL,
                case_title=item.get("CaseTitle", ""),
                case_type=self._determine_civil_case_type(item.get("CaseType", "")),
                case_type_raw=item.get("CaseType", ""),
                status=self._parse_case_status(item.get("Status", "")),
                filing_date=self._parse_date(item.get("FilingDate", "")),
                county=self.COUNTY,
                state=self.STATE,
                source_system="Cook County Clerk",
                raw_data=item,
            )

            # Parse parties
            if item.get("Plaintiff"):
                case.plaintiffs.append(item["Plaintiff"])
            if item.get("Defendant"):
                case.defendants.append(item["Defendant"])

            cases.append(case)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            cases=cases,
            total_count=len(case_data),
            page_number=1,
            page_size=max_results,
            has_more=len(case_data) > max_results,
            search_criteria=SearchCriteria(party_name=party_name),
            search_time_ms=search_time,
            source_system="Cook County Clerk",
        )

    async def search_by_case_number(self, case_number: str) -> Optional[CourtCase]:
        """Search for a specific case by case number."""
        search_url = f"{self.BASE_URL}CivilCaseSearchAPI.aspx/SearchByCaseNumber"

        try:
            json_response = await self._fetch_json(
                search_url,
                method="POST",
                json={"caseNumber": case_number},
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            logger.error(f"Cook County case search failed: {e}")
            return None

        case_data = json_response.get("d", {})
        if not case_data:
            return None

        return CourtCase(
            case_number=case_data.get("CaseNumber", case_number),
            court_name=self.COURT_NAME,
            court_type=self.COURT_TYPE,
            court_level=self.COURT_LEVEL,
            case_title=case_data.get("CaseTitle", ""),
            case_type=self._determine_civil_case_type(case_data.get("CaseType", "")),
            status=self._parse_case_status(case_data.get("Status", "")),
            filing_date=self._parse_date(case_data.get("FilingDate", "")),
            county=self.COUNTY,
            state=self.STATE,
            source_system="Cook County Clerk",
            raw_data=case_data,
        )

    async def get_case_detail(self, case_number: str) -> Optional[CourtCase]:
        """Get detailed case information."""
        case = await self.search_by_case_number(case_number)
        if not case:
            return None

        # Get additional details
        detail_url = f"{self.BASE_URL}CivilCaseSearchAPI.aspx/GetCaseDetails"

        try:
            json_response = await self._fetch_json(
                detail_url,
                method="POST",
                json={"caseNumber": case_number},
                headers={"Content-Type": "application/json"}
            )

            detail_data = json_response.get("d", {})

            # Parse parties
            for party_data in detail_data.get("Parties", []):
                party = CaseParty(
                    name=self._normalize_name(party_data.get("Name", "")),
                    role=self._parse_party_role(party_data.get("Role", "")),
                    attorney_name=party_data.get("Attorney", ""),
                )
                case.parties.append(party)

            # Parse docket
            for event_data in detail_data.get("Docket", []):
                event = CaseEvent(
                    date=self._parse_date(event_data.get("Date", "")) or date.today(),
                    description=event_data.get("Description", ""),
                    filed_by=event_data.get("FiledBy", ""),
                )
                case.events.append(event)

        except Exception as e:
            logger.warning(f"Could not get case details: {e}")

        return case

    def _parse_party_role(self, role_str: str) -> PartyRole:
        """Parse Cook County party role."""
        if not role_str:
            return PartyRole.UNKNOWN

        role_upper = role_str.upper()

        if "PLAINTIFF" in role_upper:
            return PartyRole.PLAINTIFF
        elif "DEFENDANT" in role_upper:
            return PartyRole.DEFENDANT
        elif "PETITIONER" in role_upper:
            return PartyRole.PETITIONER
        elif "RESPONDENT" in role_upper:
            return PartyRole.RESPONDENT

        return PartyRole.UNKNOWN


class LosAngelesCivil(CountyCivilCourtBase):
    """
    Los Angeles County, California Civil Court Scraper.

    LA County is the largest county court system in the US.
    Civil cases are heard in the Los Angeles Superior Court.

    Public access requires registration: https://www.lacourt.org/
    """

    COURT_NAME = "Los Angeles Superior Court - Civil Division"
    COUNTY = "Los Angeles"
    STATE = "CA"
    FIPS_CODE = "06037"
    BASE_URL = "https://www.lacourt.org/"
    REQUIRES_LOGIN = True

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
        """Search LA County civil cases by party name."""
        import time
        start_time = time.time()

        if not self._authenticated:
            logger.warning("LA County requires login for case search")
            return SearchResult(
                cases=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(party_name=party_name),
                warnings=["LA County requires registration and login"],
            )

        # Build search URL
        search_url = f"{self.BASE_URL}civilapi/searchByName"

        params = {
            "name": party_name,
            "searchType": party_type.upper(),
        }

        if filed_start_date:
            params["startDate"] = filed_start_date.strftime("%Y-%m-%d")
        if filed_end_date:
            params["endDate"] = filed_end_date.strftime("%Y-%m-%d")

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"LA County search failed: {e}")
            return SearchResult(
                cases=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(party_name=party_name),
                warnings=[str(e)],
            )

        # Parse results
        cases = []
        case_list = json_response.get("cases", [])

        for item in case_list[:max_results]:
            case = CourtCase(
                case_number=item.get("caseNumber", ""),
                court_name=self.COURT_NAME,
                court_type=self.COURT_TYPE,
                court_level=self.COURT_LEVEL,
                case_title=item.get("caseTitle", ""),
                case_type=self._determine_civil_case_type(item.get("caseType", "")),
                case_type_raw=item.get("caseType", ""),
                status=self._parse_case_status(item.get("status", "")),
                filing_date=self._parse_date(item.get("filingDate", "")),
                county=self.COUNTY,
                state=self.STATE,
                district=item.get("district", ""),
                source_system="LA Superior Court",
                raw_data=item,
            )
            cases.append(case)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            cases=cases,
            total_count=json_response.get("totalCount", len(cases)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=SearchCriteria(party_name=party_name),
            search_time_ms=search_time,
            source_system="LA Superior Court",
        )

    async def search_by_case_number(self, case_number: str) -> Optional[CourtCase]:
        """Search for a specific case by case number."""
        if not self._authenticated:
            logger.warning("LA County requires login")
            return None

        search_url = f"{self.BASE_URL}civilapi/case/{case_number}"

        try:
            json_response = await self._fetch_json(search_url)
        except Exception as e:
            logger.error(f"LA County case search failed: {e}")
            return None

        if not json_response:
            return None

        return CourtCase(
            case_number=json_response.get("caseNumber", case_number),
            court_name=self.COURT_NAME,
            court_type=self.COURT_TYPE,
            court_level=self.COURT_LEVEL,
            case_title=json_response.get("caseTitle", ""),
            case_type=self._determine_civil_case_type(json_response.get("caseType", "")),
            status=self._parse_case_status(json_response.get("status", "")),
            filing_date=self._parse_date(json_response.get("filingDate", "")),
            county=self.COUNTY,
            state=self.STATE,
            source_system="LA Superior Court",
            raw_data=json_response,
        )

    async def get_case_detail(self, case_number: str) -> Optional[CourtCase]:
        """Get detailed case information."""
        return await self.search_by_case_number(case_number)

    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with LA County court system."""
        auth_url = f"{self.BASE_URL}auth/login"

        try:
            json_response = await self._fetch_json(
                auth_url,
                method="POST",
                json={"username": username, "password": password}
            )

            if json_response.get("success"):
                self._authenticated = True
                return True

        except Exception as e:
            logger.error(f"LA County authentication failed: {e}")

        return False


class HarrisCountyCivil(CountyCivilCourtBase):
    """
    Harris County, Texas Civil Court Scraper.

    Harris County (Houston) civil cases are heard in the District Courts.

    Public access: https://www.hcdistrictclerk.com/
    """

    COURT_NAME = "Harris County District Courts - Civil"
    COUNTY = "Harris"
    STATE = "TX"
    FIPS_CODE = "48201"
    BASE_URL = "https://www.hcdistrictclerk.com/"

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
        """Search Harris County civil cases by party name."""
        import time
        start_time = time.time()

        # Harris County uses a public portal
        search_url = f"{self.BASE_URL}Common/Public/Public_Search.aspx"

        # Get search page first
        status, html = await self._fetch(search_url)
        viewstate = await self._extract_viewstate(html)

        # Build form data
        data = {
            "__VIEWSTATE": viewstate.get("__VIEWSTATE", ""),
            "__EVENTVALIDATION": viewstate.get("__EVENTVALIDATION", ""),
            "ctl00$cphPublicSearch$txtPartyName": party_name,
            "ctl00$cphPublicSearch$ddlSearchType": "CIVIL",
            "ctl00$cphPublicSearch$btnSearch": "Search",
        }

        # Execute search
        status, html = await self._fetch(search_url, method="POST", data=data)
        soup = self._parse_html(html)

        # Parse results table
        cases = []
        results_table = soup.find("table", {"id": "gvSearchResults"})

        if results_table:
            for row in results_table.find_all("tr")[1:max_results+1]:  # Skip header
                cells = row.find_all("td")
                if len(cells) >= 4:
                    case = CourtCase(
                        case_number=cells[0].get_text(strip=True),
                        court_name=self.COURT_NAME,
                        court_type=self.COURT_TYPE,
                        court_level=self.COURT_LEVEL,
                        case_title=cells[1].get_text(strip=True),
                        case_type=self._determine_civil_case_type(cells[2].get_text(strip=True)),
                        case_type_raw=cells[2].get_text(strip=True),
                        status=self._parse_case_status(cells[3].get_text(strip=True) if len(cells) > 3 else ""),
                        filing_date=self._parse_date(cells[4].get_text(strip=True) if len(cells) > 4 else ""),
                        county=self.COUNTY,
                        state=self.STATE,
                        source_system="Harris County District Clerk",
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
            source_system="Harris County District Clerk",
        )

    async def search_by_case_number(self, case_number: str) -> Optional[CourtCase]:
        """Search for a specific case by case number."""
        search_url = f"{self.BASE_URL}Common/Public/Public_Search.aspx"

        status, html = await self._fetch(search_url)
        viewstate = await self._extract_viewstate(html)

        data = {
            "__VIEWSTATE": viewstate.get("__VIEWSTATE", ""),
            "__EVENTVALIDATION": viewstate.get("__EVENTVALIDATION", ""),
            "ctl00$cphPublicSearch$txtCaseNumber": case_number,
            "ctl00$cphPublicSearch$btnCaseSearch": "Search",
        }

        status, html = await self._fetch(search_url, method="POST", data=data)
        soup = self._parse_html(html)

        # Parse case info
        case_div = soup.find("div", {"id": "divCaseInfo"})
        if not case_div:
            return None

        return CourtCase(
            case_number=case_number,
            court_name=self.COURT_NAME,
            court_type=self.COURT_TYPE,
            court_level=self.COURT_LEVEL,
            county=self.COUNTY,
            state=self.STATE,
            source_system="Harris County District Clerk",
        )

    async def get_case_detail(self, case_number: str) -> Optional[CourtCase]:
        """Get detailed case information."""
        return await self.search_by_case_number(case_number)

    async def _extract_viewstate(self, html: str) -> Dict[str, str]:
        """Extract ASP.NET viewstate from page."""
        soup = self._parse_html(html)

        viewstate_data = {}

        viewstate = soup.find("input", {"name": "__VIEWSTATE"})
        if viewstate:
            viewstate_data["__VIEWSTATE"] = viewstate.get("value", "")

        event_validation = soup.find("input", {"name": "__EVENTVALIDATION"})
        if event_validation:
            viewstate_data["__EVENTVALIDATION"] = event_validation.get("value", "")

        return viewstate_data


# Factory function to get appropriate civil court scraper

def get_civil_court_scraper(
    state: str,
    county: str
) -> Optional[CountyCivilCourtBase]:
    """
    Get a civil court scraper for a specific county.

    Args:
        state: State code (e.g., "IL", "CA", "TX")
        county: County name (e.g., "Cook", "Los Angeles", "Harris")

    Returns:
        Configured CountyCivilCourtBase instance or None
    """
    state = state.upper()
    county_lower = county.lower()

    scrapers = {
        ("IL", "cook"): CookCountyCivil,
        ("CA", "los angeles"): LosAngelesCivil,
        ("TX", "harris"): HarrisCountyCivil,
    }

    scraper_class = scrapers.get((state, county_lower))
    if scraper_class:
        return scraper_class()

    return None


def list_supported_civil_courts() -> List[Dict[str, str]]:
    """List all supported civil court implementations."""
    return [
        {"state": "IL", "county": "Cook", "court": "Circuit Court of Cook County"},
        {"state": "CA", "county": "Los Angeles", "court": "Los Angeles Superior Court"},
        {"state": "TX", "county": "Harris", "court": "Harris County District Courts"},
    ]


# Synchronous wrapper functions

def search_civil_cases(
    state: str,
    county: str,
    party_name: str,
    **kwargs
) -> SearchResult:
    """Synchronous wrapper for civil case search."""
    scraper = get_civil_court_scraper(state, county)
    if not scraper:
        raise ValueError(f"No civil court scraper for {county}, {state}")

    async def _search():
        async with scraper:
            return await scraper.search_by_party(party_name, **kwargs)
    return asyncio.run(_search())


def search_evictions(
    state: str,
    county: str,
    **kwargs
) -> List[EvictionRecord]:
    """Synchronous wrapper for eviction search."""
    scraper = get_civil_court_scraper(state, county)
    if not scraper:
        raise ValueError(f"No civil court scraper for {county}, {state}")

    async def _search():
        async with scraper:
            return await scraper.search_evictions(**kwargs)
    return asyncio.run(_search())


def search_foreclosures(
    state: str,
    county: str,
    **kwargs
) -> List[ForeclosureRecord]:
    """Synchronous wrapper for foreclosure search."""
    scraper = get_civil_court_scraper(state, county)
    if not scraper:
        raise ValueError(f"No civil court scraper for {county}, {state}")

    async def _search():
        async with scraper:
            return await scraper.search_foreclosures(**kwargs)
    return asyncio.run(_search())
