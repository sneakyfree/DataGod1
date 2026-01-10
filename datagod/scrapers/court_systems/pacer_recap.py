"""
PACER/RECAP Federal Court Integration

PACER (Public Access to Court Electronic Records) is the federal judiciary's
system for accessing case and docket information from federal courts.

RECAP is a free alternative that archives PACER documents and makes them
freely available through CourtListener.com's API.

This module provides:
1. CourtListener/RECAP API integration (FREE)
2. Direct PACER integration (PAID - $0.10/page)

RECAP/CourtListener API: https://www.courtlistener.com/api/
PACER: https://pacer.uscourts.gov/

Federal Court Structure:
- 94 District Courts (trial courts)
- 13 Circuit Courts of Appeals
- Supreme Court
- Bankruptcy Courts
- Specialty Courts (Court of Federal Claims, etc.)
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin

import aiohttp

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


# Federal court identifiers
FEDERAL_DISTRICTS = {
    # 1st Circuit
    "mad": {"name": "Massachusetts District Court", "circuit": "1"},
    "med": {"name": "Maine District Court", "circuit": "1"},
    "nhd": {"name": "New Hampshire District Court", "circuit": "1"},
    "prd": {"name": "Puerto Rico District Court", "circuit": "1"},
    "rid": {"name": "Rhode Island District Court", "circuit": "1"},

    # 2nd Circuit
    "ctd": {"name": "Connecticut District Court", "circuit": "2"},
    "nyed": {"name": "Eastern District of New York", "circuit": "2"},
    "nynd": {"name": "Northern District of New York", "circuit": "2"},
    "nysd": {"name": "Southern District of New York", "circuit": "2"},
    "nywd": {"name": "Western District of New York", "circuit": "2"},
    "vtd": {"name": "Vermont District Court", "circuit": "2"},

    # 3rd Circuit
    "ded": {"name": "Delaware District Court", "circuit": "3"},
    "njd": {"name": "New Jersey District Court", "circuit": "3"},
    "paed": {"name": "Eastern District of Pennsylvania", "circuit": "3"},
    "pamd": {"name": "Middle District of Pennsylvania", "circuit": "3"},
    "pawd": {"name": "Western District of Pennsylvania", "circuit": "3"},
    "vid": {"name": "Virgin Islands District Court", "circuit": "3"},

    # 4th Circuit
    "mdd": {"name": "Maryland District Court", "circuit": "4"},
    "nced": {"name": "Eastern District of North Carolina", "circuit": "4"},
    "ncmd": {"name": "Middle District of North Carolina", "circuit": "4"},
    "ncwd": {"name": "Western District of North Carolina", "circuit": "4"},
    "scd": {"name": "South Carolina District Court", "circuit": "4"},
    "vaed": {"name": "Eastern District of Virginia", "circuit": "4"},
    "vawd": {"name": "Western District of Virginia", "circuit": "4"},
    "wvnd": {"name": "Northern District of West Virginia", "circuit": "4"},
    "wvsd": {"name": "Southern District of West Virginia", "circuit": "4"},

    # 5th Circuit
    "laed": {"name": "Eastern District of Louisiana", "circuit": "5"},
    "lamd": {"name": "Middle District of Louisiana", "circuit": "5"},
    "lawd": {"name": "Western District of Louisiana", "circuit": "5"},
    "msnd": {"name": "Northern District of Mississippi", "circuit": "5"},
    "mssd": {"name": "Southern District of Mississippi", "circuit": "5"},
    "txed": {"name": "Eastern District of Texas", "circuit": "5"},
    "txnd": {"name": "Northern District of Texas", "circuit": "5"},
    "txsd": {"name": "Southern District of Texas", "circuit": "5"},
    "txwd": {"name": "Western District of Texas", "circuit": "5"},

    # 6th Circuit
    "kyed": {"name": "Eastern District of Kentucky", "circuit": "6"},
    "kywd": {"name": "Western District of Kentucky", "circuit": "6"},
    "mied": {"name": "Eastern District of Michigan", "circuit": "6"},
    "miwd": {"name": "Western District of Michigan", "circuit": "6"},
    "ohnd": {"name": "Northern District of Ohio", "circuit": "6"},
    "ohsd": {"name": "Southern District of Ohio", "circuit": "6"},
    "tned": {"name": "Eastern District of Tennessee", "circuit": "6"},
    "tnmd": {"name": "Middle District of Tennessee", "circuit": "6"},
    "tnwd": {"name": "Western District of Tennessee", "circuit": "6"},

    # 7th Circuit
    "ilcd": {"name": "Central District of Illinois", "circuit": "7"},
    "ilnd": {"name": "Northern District of Illinois", "circuit": "7"},
    "ilsd": {"name": "Southern District of Illinois", "circuit": "7"},
    "innd": {"name": "Northern District of Indiana", "circuit": "7"},
    "insd": {"name": "Southern District of Indiana", "circuit": "7"},
    "wied": {"name": "Eastern District of Wisconsin", "circuit": "7"},
    "wiwd": {"name": "Western District of Wisconsin", "circuit": "7"},

    # 8th Circuit
    "ared": {"name": "Eastern District of Arkansas", "circuit": "8"},
    "arwd": {"name": "Western District of Arkansas", "circuit": "8"},
    "iasd": {"name": "Southern District of Iowa", "circuit": "8"},
    "iand": {"name": "Northern District of Iowa", "circuit": "8"},
    "mnd": {"name": "Minnesota District Court", "circuit": "8"},
    "moed": {"name": "Eastern District of Missouri", "circuit": "8"},
    "mowd": {"name": "Western District of Missouri", "circuit": "8"},
    "ned": {"name": "Nebraska District Court", "circuit": "8"},
    "ndd": {"name": "North Dakota District Court", "circuit": "8"},
    "sdd": {"name": "South Dakota District Court", "circuit": "8"},

    # 9th Circuit
    "akd": {"name": "Alaska District Court", "circuit": "9"},
    "azd": {"name": "Arizona District Court", "circuit": "9"},
    "cacd": {"name": "Central District of California", "circuit": "9"},
    "caed": {"name": "Eastern District of California", "circuit": "9"},
    "cand": {"name": "Northern District of California", "circuit": "9"},
    "casd": {"name": "Southern District of California", "circuit": "9"},
    "gud": {"name": "Guam District Court", "circuit": "9"},
    "hid": {"name": "Hawaii District Court", "circuit": "9"},
    "idd": {"name": "Idaho District Court", "circuit": "9"},
    "mtd": {"name": "Montana District Court", "circuit": "9"},
    "nvd": {"name": "Nevada District Court", "circuit": "9"},
    "mpd": {"name": "Northern Mariana Islands District Court", "circuit": "9"},
    "ord": {"name": "Oregon District Court", "circuit": "9"},
    "waed": {"name": "Eastern District of Washington", "circuit": "9"},
    "wawd": {"name": "Western District of Washington", "circuit": "9"},

    # 10th Circuit
    "cod": {"name": "Colorado District Court", "circuit": "10"},
    "ksd": {"name": "Kansas District Court", "circuit": "10"},
    "nmd": {"name": "New Mexico District Court", "circuit": "10"},
    "oked": {"name": "Eastern District of Oklahoma", "circuit": "10"},
    "oknd": {"name": "Northern District of Oklahoma", "circuit": "10"},
    "okwd": {"name": "Western District of Oklahoma", "circuit": "10"},
    "utd": {"name": "Utah District Court", "circuit": "10"},
    "wyd": {"name": "Wyoming District Court", "circuit": "10"},

    # 11th Circuit
    "almd": {"name": "Middle District of Alabama", "circuit": "11"},
    "alnd": {"name": "Northern District of Alabama", "circuit": "11"},
    "alsd": {"name": "Southern District of Alabama", "circuit": "11"},
    "flmd": {"name": "Middle District of Florida", "circuit": "11"},
    "flnd": {"name": "Northern District of Florida", "circuit": "11"},
    "flsd": {"name": "Southern District of Florida", "circuit": "11"},
    "gamd": {"name": "Middle District of Georgia", "circuit": "11"},
    "gand": {"name": "Northern District of Georgia", "circuit": "11"},
    "gasd": {"name": "Southern District of Georgia", "circuit": "11"},

    # DC Circuit
    "dcd": {"name": "District of Columbia District Court", "circuit": "dc"},
}

# Circuit Courts of Appeals
CIRCUIT_COURTS = {
    "ca1": {"name": "First Circuit Court of Appeals", "states": ["MA", "ME", "NH", "PR", "RI"]},
    "ca2": {"name": "Second Circuit Court of Appeals", "states": ["CT", "NY", "VT"]},
    "ca3": {"name": "Third Circuit Court of Appeals", "states": ["DE", "NJ", "PA", "VI"]},
    "ca4": {"name": "Fourth Circuit Court of Appeals", "states": ["MD", "NC", "SC", "VA", "WV"]},
    "ca5": {"name": "Fifth Circuit Court of Appeals", "states": ["LA", "MS", "TX"]},
    "ca6": {"name": "Sixth Circuit Court of Appeals", "states": ["KY", "MI", "OH", "TN"]},
    "ca7": {"name": "Seventh Circuit Court of Appeals", "states": ["IL", "IN", "WI"]},
    "ca8": {"name": "Eighth Circuit Court of Appeals", "states": ["AR", "IA", "MN", "MO", "NE", "ND", "SD"]},
    "ca9": {"name": "Ninth Circuit Court of Appeals", "states": ["AK", "AZ", "CA", "GU", "HI", "ID", "MT", "NV", "MP", "OR", "WA"]},
    "ca10": {"name": "Tenth Circuit Court of Appeals", "states": ["CO", "KS", "NM", "OK", "UT", "WY"]},
    "ca11": {"name": "Eleventh Circuit Court of Appeals", "states": ["AL", "FL", "GA"]},
    "cadc": {"name": "DC Circuit Court of Appeals", "states": ["DC"]},
    "cafc": {"name": "Federal Circuit Court of Appeals", "states": []},  # Patents, trade, etc.
}


class PacerRecapAPI(CourtSystemBase):
    """
    PACER/RECAP Federal Court API Integration.

    This class primarily uses the FREE CourtListener/RECAP API to search
    federal court records. RECAP is a crowdsourced archive of PACER documents.

    For documents not in RECAP, direct PACER access can be used (requires
    PACER account and incurs fees).

    CourtListener API Documentation:
    https://www.courtlistener.com/api/rest-info/
    """

    COURT_NAME = "Federal Courts (PACER/RECAP)"
    COURT_TYPE = CourtType.FEDERAL_DISTRICT
    COURT_LEVEL = CourtLevel.TRIAL
    STATE = ""  # Federal - nationwide
    COUNTY = ""

    BASE_URL = "https://www.courtlistener.com/"
    API_URL = "https://www.courtlistener.com/api/rest/v3/"
    RECAP_URL = "https://www.courtlistener.com/api/rest/v3/recap/"
    PACER_URL = "https://pacer.uscourts.gov/"

    SYSTEM_NAME = "CourtListener/RECAP"
    SYSTEM_VENDOR = "Free Law Project"

    REQUEST_DELAY = 0.5  # CourtListener is generous
    MAX_RETRIES = 3
    TIMEOUT = 30

    REQUIRES_LOGIN = False  # CourtListener is free, PACER requires login
    REQUIRES_PAYMENT = False  # CourtListener is free
    COST_PER_PAGE = 0.0  # Free via RECAP

    # PACER costs (if using direct PACER)
    PACER_COST_PER_PAGE = 0.10

    def __init__(
        self,
        session: Optional[aiohttp.ClientSession] = None,
        courtlistener_token: Optional[str] = None,
        pacer_username: Optional[str] = None,
        pacer_password: Optional[str] = None
    ):
        """
        Initialize PACER/RECAP API.

        Args:
            session: Optional aiohttp session
            courtlistener_token: Optional API token for CourtListener
            pacer_username: Optional PACER username for direct access
            pacer_password: Optional PACER password
        """
        super().__init__(session)
        self.courtlistener_token = courtlistener_token
        self.pacer_username = pacer_username
        self.pacer_password = pacer_password
        self._pacer_session = None

    def _get_headers(self) -> Dict[str, str]:
        """Get headers including auth token if available."""
        headers = super()._get_headers()
        if self.courtlistener_token:
            headers["Authorization"] = f"Token {self.courtlistener_token}"
        return headers

    def _parse_courtlistener_case(self, data: Dict[str, Any]) -> CourtCase:
        """Parse a CourtListener API response into a CourtCase."""
        # Determine court type
        court_id = data.get("court", "")
        court_type = CourtType.FEDERAL_DISTRICT
        court_level = CourtLevel.TRIAL

        if court_id.startswith("ca"):
            court_type = CourtType.FEDERAL_APPELLATE
            court_level = CourtLevel.APPELLATE
        elif "scotus" in court_id:
            court_type = CourtType.FEDERAL_SUPREME
            court_level = CourtLevel.SUPREME
        elif "bk" in court_id or "bankr" in court_id:
            court_type = CourtType.FEDERAL_BANKRUPTCY
            court_level = CourtLevel.TRIAL

        # Get court name
        court_name = FEDERAL_DISTRICTS.get(court_id, {}).get("name", "")
        if not court_name:
            court_name = CIRCUIT_COURTS.get(court_id, {}).get("name", "")
        if not court_name:
            court_name = data.get("court_id", court_id)

        # Parse case type
        case_type_raw = data.get("nature_of_suit", "") or data.get("case_type", "")
        case_type = self._parse_federal_case_type(case_type_raw)

        # Parse parties
        parties = []
        plaintiffs = []
        defendants = []

        for party_data in data.get("parties", []):
            party = self._parse_party(party_data)
            parties.append(party)
            if party.role in {PartyRole.PLAINTIFF, PartyRole.PETITIONER, PartyRole.APPELLANT}:
                plaintiffs.append(party.name)
            elif party.role in {PartyRole.DEFENDANT, PartyRole.RESPONDENT, PartyRole.APPELLEE}:
                defendants.append(party.name)

        # Parse docket entries
        events = []
        for entry in data.get("docket_entries", []):
            events.append(self._parse_docket_entry(entry))

        return CourtCase(
            case_number=data.get("docket_number", "") or data.get("case_name", ""),
            court_name=court_name,
            court_type=court_type,
            court_level=court_level,
            case_type=case_type,
            case_type_raw=case_type_raw,
            case_title=data.get("case_name", ""),
            status=self._parse_case_status(data.get("status", "")),
            filing_date=self._parse_date(data.get("date_filed", "")),
            disposition_date=self._parse_date(data.get("date_terminated", "")),
            last_activity_date=self._parse_date(data.get("date_last_filing", "")),
            parties=parties,
            plaintiffs=plaintiffs,
            defendants=defendants,
            events=events,
            judge=data.get("assigned_to_str", ""),
            district=data.get("court", ""),
            source_url=f"https://www.courtlistener.com{data.get('absolute_url', '')}",
            source_system="CourtListener/RECAP",
            raw_data=data
        )

    def _parse_federal_case_type(self, raw_type: str) -> CaseType:
        """Parse federal court case type (Nature of Suit codes)."""
        if not raw_type:
            return CaseType.UNKNOWN

        raw_type = raw_type.upper()

        # Nature of Suit code mappings
        nos_mappings = {
            # Contract
            "110": CaseType.CONTRACT,  # Insurance
            "120": CaseType.CONTRACT,  # Marine
            "130": CaseType.CONTRACT,  # Miller Act
            "140": CaseType.CONTRACT,  # Negotiable Instrument
            "150": CaseType.CONTRACT,  # Recovery of Overpayment
            "151": CaseType.CONTRACT,  # Medicare Act
            "152": CaseType.CONTRACT,  # Recovery of Student Loans
            "153": CaseType.CONTRACT,  # Recovery of Veteran's Benefits
            "160": CaseType.CONTRACT,  # Stockholders' Suits
            "190": CaseType.CONTRACT,  # Other Contract

            # Real Property
            "210": CaseType.PROPERTY,  # Land Condemnation
            "220": CaseType.FORECLOSURE,  # Foreclosure
            "230": CaseType.PROPERTY,  # Rent Lease & Ejectment
            "240": CaseType.TORT,  # Torts to Land
            "245": CaseType.PROPERTY,  # Tort Product Liability
            "290": CaseType.PROPERTY,  # All Other Real Property

            # Personal Injury
            "310": CaseType.PERSONAL_INJURY,  # Airplane
            "315": CaseType.PERSONAL_INJURY,  # Airplane Product Liability
            "320": CaseType.PERSONAL_INJURY,  # Assault, Libel & Slander
            "330": CaseType.PERSONAL_INJURY,  # Federal Employers' Liability
            "340": CaseType.PERSONAL_INJURY,  # Marine
            "345": CaseType.PERSONAL_INJURY,  # Marine Product Liability
            "350": CaseType.PERSONAL_INJURY,  # Motor Vehicle
            "355": CaseType.PERSONAL_INJURY,  # Motor Vehicle Product Liability
            "360": CaseType.PERSONAL_INJURY,  # Other Personal Injury
            "362": CaseType.MEDICAL_MALPRACTICE,  # Personal Injury - Medical Malpractice
            "365": CaseType.PRODUCT_LIABILITY,  # Personal Injury - Product Liability
            "367": CaseType.PERSONAL_INJURY,  # Health Care/Pharmaceutical
            "368": CaseType.PERSONAL_INJURY,  # Asbestos Personal Injury
            "370": CaseType.TORT,  # Other Fraud
            "371": CaseType.TORT,  # Truth in Lending
            "380": CaseType.TORT,  # Other Personal Property Damage
            "385": CaseType.PRODUCT_LIABILITY,  # Property Damage Product Liability

            # Civil Rights
            "440": CaseType.DISCRIMINATION,  # Other Civil Rights
            "441": CaseType.DISCRIMINATION,  # Voting
            "442": CaseType.EMPLOYMENT,  # Employment
            "443": CaseType.DISCRIMINATION,  # Housing/Accommodations
            "444": CaseType.DISCRIMINATION,  # Welfare
            "445": CaseType.DISCRIMINATION,  # ADA - Employment
            "446": CaseType.DISCRIMINATION,  # ADA - Other
            "448": CaseType.DISCRIMINATION,  # Education

            # Bankruptcy
            "422": CaseType.BANKRUPTCY_CH7,
            "423": CaseType.BANKRUPTCY_CH11,

            # Securities
            "850": CaseType.SECURITIES,
            "890": CaseType.SECURITIES,

            # Intellectual Property
            "820": CaseType.INTELLECTUAL_PROPERTY,  # Copyrights
            "830": CaseType.INTELLECTUAL_PROPERTY,  # Patent
            "835": CaseType.INTELLECTUAL_PROPERTY,  # Patent - ANDA
            "840": CaseType.INTELLECTUAL_PROPERTY,  # Trademark
        }

        # Check NOS code
        for code, case_type in nos_mappings.items():
            if code in raw_type:
                return case_type

        # Text-based matching
        if "CONTRACT" in raw_type:
            return CaseType.CONTRACT
        elif "TORT" in raw_type or "PERSONAL INJURY" in raw_type:
            return CaseType.PERSONAL_INJURY
        elif "CIVIL RIGHTS" in raw_type or "DISCRIMINATION" in raw_type:
            return CaseType.DISCRIMINATION
        elif "BANKRUPTCY" in raw_type:
            return CaseType.BANKRUPTCY_CH7
        elif "CRIMINAL" in raw_type:
            return CaseType.CRIMINAL_FELONY
        elif "FORECLOSURE" in raw_type:
            return CaseType.FORECLOSURE

        return CaseType.CIVIL_GENERAL

    def _parse_party(self, party_data: Dict[str, Any]) -> CaseParty:
        """Parse party data from CourtListener."""
        role_str = party_data.get("party_type", "").upper()
        role = PartyRole.UNKNOWN

        if "PLAINTIFF" in role_str:
            role = PartyRole.PLAINTIFF
        elif "DEFENDANT" in role_str:
            role = PartyRole.DEFENDANT
        elif "PETITIONER" in role_str:
            role = PartyRole.PETITIONER
        elif "RESPONDENT" in role_str:
            role = PartyRole.RESPONDENT
        elif "APPELLANT" in role_str:
            role = PartyRole.APPELLANT
        elif "APPELLEE" in role_str:
            role = PartyRole.APPELLEE
        elif "DEBTOR" in role_str:
            role = PartyRole.DEBTOR
        elif "CREDITOR" in role_str:
            role = PartyRole.CREDITOR
        elif "TRUSTEE" in role_str:
            role = PartyRole.TRUSTEE

        # Get attorney info
        attorneys = party_data.get("attorneys", [])
        attorney_name = None
        attorney_firm = None
        if attorneys:
            attorney_name = attorneys[0].get("name", "")
            attorney_firm = attorneys[0].get("firm_name", "")

        return CaseParty(
            name=self._normalize_name(party_data.get("name", "")),
            role=role,
            party_type=PartyType.UNKNOWN,
            attorney_name=attorney_name,
            attorney_firm=attorney_firm,
            is_pro_se=party_data.get("is_pro_se", False),
            raw_name=party_data.get("name", "")
        )

    def _parse_docket_entry(self, entry: Dict[str, Any]) -> CaseEvent:
        """Parse a docket entry from CourtListener."""
        return CaseEvent(
            date=self._parse_date(entry.get("date_filed", "")) or date.today(),
            description=entry.get("description", ""),
            event_type=entry.get("entry_type", ""),
            document_number=str(entry.get("entry_number", "")),
            document_url=entry.get("filepath_local", ""),
            page_count=entry.get("page_count"),
            sequence_number=entry.get("entry_number"),
            raw_text=entry.get("description", "")
        )

    async def search_by_party(
        self,
        party_name: str,
        party_type: str = "any",
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        case_types: Optional[List[CaseType]] = None,
        include_closed: bool = True,
        max_results: int = 100,
        court: Optional[str] = None
    ) -> SearchResult:
        """
        Search federal court cases by party name using CourtListener API.

        Args:
            party_name: Name to search
            party_type: Search plaintiff, defendant, or any
            filed_start_date: Start of filing date range
            filed_end_date: End of filing date range
            case_types: Filter by case types
            include_closed: Include closed cases
            max_results: Maximum results to return
            court: Specific court ID (e.g., "cand" for N.D. Cal)

        Returns:
            SearchResult with matching cases
        """
        import time
        start_time = time.time()

        # Build API parameters
        params = {
            "type": "d",  # Docket search
            "party_name": party_name,
            "order_by": "dateFiled desc",
        }

        if court:
            params["court"] = court

        if filed_start_date:
            params["date_filed__gte"] = filed_start_date.isoformat()

        if filed_end_date:
            params["date_filed__lte"] = filed_end_date.isoformat()

        if not include_closed:
            params["date_terminated__isnull"] = "true"

        # Search endpoint
        search_url = f"{self.API_URL}dockets/"
        all_cases = []

        try:
            # Paginate through results
            page = 1
            has_more = True

            while has_more and len(all_cases) < max_results:
                params["page"] = page
                params["page_size"] = min(25, max_results - len(all_cases))

                response = await self._fetch_json(search_url, params=params)

                results = response.get("results", [])
                if not results:
                    has_more = False
                    break

                for result in results:
                    try:
                        case = self._parse_courtlistener_case(result)

                        # Filter by case type if specified
                        if case_types and case.case_type not in case_types:
                            continue

                        all_cases.append(case)

                    except Exception as e:
                        logger.warning(f"Error parsing case: {e}")
                        continue

                # Check for next page
                if response.get("next"):
                    page += 1
                else:
                    has_more = False

        except Exception as e:
            logger.error(f"Error during party search: {e}")

        elapsed_ms = int((time.time() - start_time) * 1000)

        return SearchResult(
            cases=all_cases[:max_results],
            total_count=len(all_cases),
            page_number=1,
            page_size=max_results,
            has_more=len(all_cases) > max_results,
            search_criteria=SearchCriteria(
                party_name=party_name,
                party_type=party_type,
                filed_start_date=filed_start_date,
                filed_end_date=filed_end_date,
                case_types=case_types or []
            ),
            search_time_ms=elapsed_ms,
            source_system="CourtListener/RECAP",
            fees_incurred=0.0  # Free via RECAP
        )

    async def search_by_case_number(
        self,
        case_number: str,
        court: Optional[str] = None
    ) -> Optional[CourtCase]:
        """
        Search for a specific federal case by case number.

        Args:
            case_number: The case number (e.g., "3:21-cv-00123")
            court: Optional court ID to narrow search

        Returns:
            CourtCase if found, None otherwise
        """
        params = {
            "docket_number": case_number,
        }

        if court:
            params["court"] = court

        search_url = f"{self.API_URL}dockets/"

        try:
            response = await self._fetch_json(search_url, params=params)
            results = response.get("results", [])

            if results:
                return self._parse_courtlistener_case(results[0])

            return None

        except Exception as e:
            logger.error(f"Error during case number search: {e}")
            return None

    async def get_case_detail(
        self,
        case_number: str,
        court: Optional[str] = None
    ) -> Optional[CourtCase]:
        """
        Get detailed information for a federal case including full docket.

        Args:
            case_number: The case number
            court: Optional court ID

        Returns:
            CourtCase with full details, or None if not found
        """
        # First search for the case
        case = await self.search_by_case_number(case_number, court)
        if not case:
            return None

        # Get case ID from raw data
        case_id = case.raw_data.get("id")
        if not case_id:
            return case

        # Fetch full docket entries
        docket_url = f"{self.API_URL}docket-entries/"
        params = {
            "docket": case_id,
            "order_by": "entry_number",
            "page_size": 100
        }

        try:
            events = []
            documents = []

            # Paginate through all entries
            has_more = True
            page = 1

            while has_more:
                params["page"] = page
                response = await self._fetch_json(docket_url, params=params)

                for entry in response.get("results", []):
                    event = self._parse_docket_entry(entry)
                    events.append(event)

                    # Check for documents
                    recap_documents = entry.get("recap_documents", [])
                    for doc in recap_documents:
                        documents.append(CaseDocument(
                            document_number=str(doc.get("document_number", "")),
                            title=doc.get("description", ""),
                            filed_date=self._parse_date(doc.get("date_upload", "")),
                            page_count=doc.get("page_count"),
                            url=doc.get("filepath_local", ""),
                            is_sealed=doc.get("is_sealed", False),
                            description=doc.get("description", "")
                        ))

                if response.get("next"):
                    page += 1
                else:
                    has_more = False

            case.events = events
            case.documents = documents

        except Exception as e:
            logger.warning(f"Error fetching docket entries: {e}")

        return case

    async def search_opinions(
        self,
        query: str,
        court: Optional[str] = None,
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search court opinions/orders in RECAP archive.

        Args:
            query: Search query text
            court: Specific court ID
            filed_start_date: Start of date range
            filed_end_date: End of date range
            max_results: Maximum results

        Returns:
            List of opinion results
        """
        params = {
            "type": "o",  # Opinion search
            "q": query,
            "order_by": "dateFiled desc",
        }

        if court:
            params["court"] = court

        if filed_start_date:
            params["filed_after"] = filed_start_date.isoformat()

        if filed_end_date:
            params["filed_before"] = filed_end_date.isoformat()

        search_url = f"{self.API_URL}search/"
        opinions = []

        try:
            params["page_size"] = min(25, max_results)
            response = await self._fetch_json(search_url, params=params)

            for result in response.get("results", [])[:max_results]:
                opinions.append({
                    "case_name": result.get("caseName", ""),
                    "court": result.get("court", ""),
                    "date_filed": result.get("dateFiled", ""),
                    "docket_number": result.get("docketNumber", ""),
                    "citation": result.get("citation", []),
                    "snippet": result.get("snippet", ""),
                    "url": result.get("absolute_url", ""),
                })

        except Exception as e:
            logger.error(f"Error searching opinions: {e}")

        return opinions

    async def get_bankruptcy_case(
        self,
        case_number: str,
        district: str
    ) -> Optional[CourtCase]:
        """
        Get a bankruptcy case by number.

        Args:
            case_number: Bankruptcy case number
            district: District code (e.g., "cand" for N.D. Cal)

        Returns:
            CourtCase if found, None otherwise
        """
        # Bankruptcy courts use different court IDs
        bk_court = f"{district}b"  # e.g., "candb" for N.D. Cal Bankruptcy

        return await self.get_case_detail(case_number, court=bk_court)

    def get_available_courts(self) -> Dict[str, Dict[str, str]]:
        """Get list of available federal courts."""
        courts = {}

        # Add district courts
        for code, info in FEDERAL_DISTRICTS.items():
            courts[code] = {
                "name": info["name"],
                "type": "district",
                "circuit": info["circuit"]
            }

        # Add circuit courts
        for code, info in CIRCUIT_COURTS.items():
            courts[code] = {
                "name": info["name"],
                "type": "appellate",
                "states": info["states"]
            }

        return courts


# Convenience functions for synchronous usage

def search_federal_courts(
    party_name: str,
    **kwargs
) -> SearchResult:
    """Search federal courts by party name (synchronous)."""
    async def _search():
        async with PacerRecapAPI() as api:
            return await api.search_by_party(party_name, **kwargs)
    return asyncio.run(_search())


def get_federal_case(
    case_number: str,
    court: Optional[str] = None
) -> Optional[CourtCase]:
    """Get a federal case by number (synchronous)."""
    async def _get():
        async with PacerRecapAPI() as api:
            return await api.get_case_detail(case_number, court)
    return asyncio.run(_get())


def search_federal_opinions(
    query: str,
    **kwargs
) -> List[Dict[str, Any]]:
    """Search federal court opinions (synchronous)."""
    async def _search():
        async with PacerRecapAPI() as api:
            return await api.search_opinions(query, **kwargs)
    return asyncio.run(_search())
