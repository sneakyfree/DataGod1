"""
County Criminal Courts Scraper

Handles criminal court cases at the county level, including:
- Felony cases
- Misdemeanor cases
- DUI/DWI cases
- Drug offenses
- Traffic criminal violations
- Probation violations

Criminal records are public in most states but may have restrictions on:
- Juvenile cases (typically sealed)
- Expunged records
- Certain disposition information
- Victim information

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
    CaseCharge,
    SearchCriteria,
    SearchResult,
)

logger = logging.getLogger(__name__)


class ChargeLevel(Enum):
    """Level/severity of criminal charges."""
    CAPITAL = "capital"  # Death penalty eligible
    FIRST_DEGREE_FELONY = "first_degree_felony"
    SECOND_DEGREE_FELONY = "second_degree_felony"
    THIRD_DEGREE_FELONY = "third_degree_felony"
    STATE_JAIL_FELONY = "state_jail_felony"  # Texas
    CLASS_A_MISDEMEANOR = "class_a_misdemeanor"
    CLASS_B_MISDEMEANOR = "class_b_misdemeanor"
    CLASS_C_MISDEMEANOR = "class_c_misdemeanor"
    INFRACTION = "infraction"
    VIOLATION = "violation"
    FELONY_UNSPECIFIED = "felony"
    MISDEMEANOR_UNSPECIFIED = "misdemeanor"
    UNKNOWN = "unknown"


class ChargeDisposition(Enum):
    """Disposition outcomes for criminal charges."""
    # Convictions
    GUILTY = "guilty"
    GUILTY_PLEA = "guilty_plea"
    NOLO_CONTENDERE = "nolo_contendere"  # No contest
    FOUND_GUILTY = "found_guilty"  # Trial verdict

    # Acquittals
    NOT_GUILTY = "not_guilty"
    ACQUITTED = "acquitted"

    # Dismissals
    DISMISSED = "dismissed"
    DISMISSED_WITH_PREJUDICE = "dismissed_with_prejudice"
    DISMISSED_WITHOUT_PREJUDICE = "dismissed_without_prejudice"
    NOLLE_PROSEQUI = "nolle_prosequi"  # Prosecution dropped

    # Other
    DEFERRED = "deferred"
    DEFERRED_ADJUDICATION = "deferred_adjudication"
    PRETRIAL_DIVERSION = "pretrial_diversion"
    REDUCED = "reduced"
    AMENDED = "amended"
    TRANSFERRED = "transferred"
    CONSOLIDATED = "consolidated"
    PENDING = "pending"

    UNKNOWN = "unknown"


class SentenceType(Enum):
    """Types of criminal sentences."""
    PRISON = "prison"
    JAIL = "jail"
    PROBATION = "probation"
    COMMUNITY_SUPERVISION = "community_supervision"
    DEFERRED_ADJUDICATION = "deferred_adjudication"
    FINE = "fine"
    RESTITUTION = "restitution"
    COMMUNITY_SERVICE = "community_service"
    TIME_SERVED = "time_served"
    SUSPENDED = "suspended"
    CONCURRENT = "concurrent"
    CONSECUTIVE = "consecutive"
    LIFE = "life"
    DEATH = "death"
    OTHER = "other"


@dataclass
class CriminalCharge:
    """Extended criminal charge information."""
    # Charge identification
    charge_number: int = 1
    count_number: int = 1
    statute_code: str = ""
    statute_description: str = ""

    # Charge details
    offense_description: str = ""
    offense_date: Optional[date] = None
    offense_location: Optional[str] = None
    charge_level: ChargeLevel = ChargeLevel.UNKNOWN
    charge_class: Optional[str] = None  # "Class A", "1st Degree", etc.
    is_enhanced: bool = False
    enhancement_reason: Optional[str] = None

    # Disposition
    disposition: ChargeDisposition = ChargeDisposition.PENDING
    disposition_date: Optional[date] = None

    # Plea
    plea: Optional[str] = None
    plea_date: Optional[date] = None

    # Sentence
    sentence: Optional[str] = None
    sentence_type: Optional[SentenceType] = None
    sentence_years: Optional[float] = None
    sentence_months: Optional[int] = None
    sentence_days: Optional[int] = None
    probation_years: Optional[float] = None
    fine_amount: Optional[float] = None
    restitution_amount: Optional[float] = None
    community_service_hours: Optional[int] = None

    # Status
    is_original: bool = True
    is_amended: bool = False
    amended_from: Optional[str] = None
    is_dismissed: bool = False


@dataclass
class CriminalDefendant:
    """Criminal defendant information."""
    name: str
    case_number: str

    # Demographics (often in public records)
    date_of_birth: Optional[date] = None
    age_at_offense: Optional[int] = None
    sex: Optional[str] = None
    race: Optional[str] = None

    # Identifiers
    sid: Optional[str] = None  # State ID number
    fbi_number: Optional[str] = None
    booking_number: Optional[str] = None

    # Address (if public)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    # Attorney
    attorney_name: Optional[str] = None
    attorney_type: Optional[str] = None  # Retained, Appointed, Public Defender

    # Status
    in_custody: bool = False
    bond_amount: Optional[float] = None
    bond_type: Optional[str] = None  # Cash, Surety, PR Bond


@dataclass
class CriminalCaseRecord:
    """Complete criminal case record."""
    # Case identification
    case_number: str
    court_name: str
    court_type: CourtType = CourtType.COUNTY_CRIMINAL

    # Parties
    defendant: Optional[CriminalDefendant] = None
    prosecutor_name: Optional[str] = None
    judge_name: Optional[str] = None

    # Charges
    charges: List[CriminalCharge] = field(default_factory=list)
    original_charge_count: int = 0

    # Case dates
    filing_date: Optional[date] = None
    arrest_date: Optional[date] = None
    arraignment_date: Optional[date] = None
    trial_date: Optional[date] = None
    disposition_date: Optional[date] = None
    sentencing_date: Optional[date] = None

    # Case status
    status: CaseStatus = CaseStatus.UNKNOWN
    case_type: CaseType = CaseType.CRIMINAL_FELONY

    # Docket
    events: List[CaseEvent] = field(default_factory=list)
    next_hearing: Optional[date] = None
    next_hearing_type: Optional[str] = None

    # Bond/Bail
    bond_amount: Optional[float] = None
    bond_status: Optional[str] = None

    # Location
    county: str = ""
    state: str = ""
    district: Optional[str] = None
    division: Optional[str] = None

    # Source
    source_url: Optional[str] = None
    source_system: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    def get_convicted_charges(self) -> List[CriminalCharge]:
        """Get all charges with guilty disposition."""
        guilty_dispositions = {
            ChargeDisposition.GUILTY,
            ChargeDisposition.GUILTY_PLEA,
            ChargeDisposition.NOLO_CONTENDERE,
            ChargeDisposition.FOUND_GUILTY,
        }
        return [c for c in self.charges if c.disposition in guilty_dispositions]

    def get_dismissed_charges(self) -> List[CriminalCharge]:
        """Get all dismissed charges."""
        dismissed_dispositions = {
            ChargeDisposition.DISMISSED,
            ChargeDisposition.DISMISSED_WITH_PREJUDICE,
            ChargeDisposition.DISMISSED_WITHOUT_PREJUDICE,
            ChargeDisposition.NOLLE_PROSEQUI,
        }
        return [c for c in self.charges if c.disposition in dismissed_dispositions]

    def get_most_serious_charge(self) -> Optional[CriminalCharge]:
        """Get the most serious charge based on level."""
        level_order = [
            ChargeLevel.CAPITAL,
            ChargeLevel.FIRST_DEGREE_FELONY,
            ChargeLevel.SECOND_DEGREE_FELONY,
            ChargeLevel.THIRD_DEGREE_FELONY,
            ChargeLevel.STATE_JAIL_FELONY,
            ChargeLevel.FELONY_UNSPECIFIED,
            ChargeLevel.CLASS_A_MISDEMEANOR,
            ChargeLevel.CLASS_B_MISDEMEANOR,
            ChargeLevel.CLASS_C_MISDEMEANOR,
            ChargeLevel.MISDEMEANOR_UNSPECIFIED,
            ChargeLevel.INFRACTION,
            ChargeLevel.VIOLATION,
        ]

        for level in level_order:
            for charge in self.charges:
                if charge.charge_level == level:
                    return charge

        return self.charges[0] if self.charges else None


class CountyCriminalCourtBase(CourtSystemBase):
    """
    Base class for county criminal court scrapers.

    Provides common functionality for searching and extracting criminal
    court records at the county level.
    """

    COURT_TYPE = CourtType.COUNTY_CRIMINAL
    COURT_LEVEL = CourtLevel.TRIAL

    # Criminal case type patterns
    CASE_TYPE_PATTERNS = {
        # Felonies
        r"felony": CaseType.CRIMINAL_FELONY,
        r"fel\b": CaseType.CRIMINAL_FELONY,
        r"f\d": CaseType.CRIMINAL_FELONY,  # F1, F2, etc.
        r"capital": CaseType.CRIMINAL_FELONY,
        r"murder": CaseType.CRIMINAL_FELONY,
        r"homicide": CaseType.CRIMINAL_FELONY,
        r"assault.*aggravated": CaseType.CRIMINAL_FELONY,
        r"robbery": CaseType.CRIMINAL_FELONY,
        r"burglary": CaseType.CRIMINAL_FELONY,

        # Misdemeanors
        r"misdemeanor": CaseType.CRIMINAL_MISDEMEANOR,
        r"misd\b": CaseType.CRIMINAL_MISDEMEANOR,
        r"m\d": CaseType.CRIMINAL_MISDEMEANOR,  # M1, M2, etc.
        r"class\s*[abc]\s*misd": CaseType.CRIMINAL_MISDEMEANOR,

        # DUI
        r"dui": CaseType.DUI_DWI,
        r"dwi": CaseType.DUI_DWI,
        r"driving.*under.*influence": CaseType.DUI_DWI,
        r"impaired": CaseType.DUI_DWI,
        r"intox": CaseType.DUI_DWI,

        # Drug
        r"drug": CaseType.DRUG_OFFENSE,
        r"controlled.*substance": CaseType.DRUG_OFFENSE,
        r"possession": CaseType.DRUG_OFFENSE,
        r"poss\b": CaseType.DRUG_OFFENSE,
        r"marijuana": CaseType.DRUG_OFFENSE,
        r"cocaine": CaseType.DRUG_OFFENSE,
        r"meth": CaseType.DRUG_OFFENSE,

        # Traffic Criminal
        r"traffic.*criminal": CaseType.TRAFFIC_CRIMINAL,
        r"reckless.*driv": CaseType.TRAFFIC_CRIMINAL,
        r"hit.*run": CaseType.TRAFFIC_CRIMINAL,
        r"evading": CaseType.TRAFFIC_CRIMINAL,
        r"no.*license": CaseType.TRAFFIC_CRIMINAL,
        r"suspended.*license": CaseType.TRAFFIC_CRIMINAL,

        # White Collar
        r"fraud": CaseType.WHITE_COLLAR,
        r"embezzlement": CaseType.WHITE_COLLAR,
        r"forgery": CaseType.WHITE_COLLAR,
        r"theft.*identity": CaseType.WHITE_COLLAR,

        # Violent
        r"assault": CaseType.VIOLENT_CRIME,
        r"battery": CaseType.VIOLENT_CRIME,
        r"domestic.*violence": CaseType.VIOLENT_CRIME,
    }

    # Charge level patterns
    CHARGE_LEVEL_PATTERNS = {
        r"capital": ChargeLevel.CAPITAL,
        r"1st\s*degree.*fel": ChargeLevel.FIRST_DEGREE_FELONY,
        r"first\s*degree.*fel": ChargeLevel.FIRST_DEGREE_FELONY,
        r"f1\b": ChargeLevel.FIRST_DEGREE_FELONY,
        r"2nd\s*degree.*fel": ChargeLevel.SECOND_DEGREE_FELONY,
        r"second\s*degree.*fel": ChargeLevel.SECOND_DEGREE_FELONY,
        r"f2\b": ChargeLevel.SECOND_DEGREE_FELONY,
        r"3rd\s*degree.*fel": ChargeLevel.THIRD_DEGREE_FELONY,
        r"third\s*degree.*fel": ChargeLevel.THIRD_DEGREE_FELONY,
        r"f3\b": ChargeLevel.THIRD_DEGREE_FELONY,
        r"state\s*jail": ChargeLevel.STATE_JAIL_FELONY,
        r"sj\s*fel": ChargeLevel.STATE_JAIL_FELONY,
        r"class\s*a\s*misd": ChargeLevel.CLASS_A_MISDEMEANOR,
        r"ma\b": ChargeLevel.CLASS_A_MISDEMEANOR,
        r"class\s*b\s*misd": ChargeLevel.CLASS_B_MISDEMEANOR,
        r"mb\b": ChargeLevel.CLASS_B_MISDEMEANOR,
        r"class\s*c\s*misd": ChargeLevel.CLASS_C_MISDEMEANOR,
        r"mc\b": ChargeLevel.CLASS_C_MISDEMEANOR,
        r"infraction": ChargeLevel.INFRACTION,
        r"violation": ChargeLevel.VIOLATION,
        r"felony": ChargeLevel.FELONY_UNSPECIFIED,
        r"misdemeanor": ChargeLevel.MISDEMEANOR_UNSPECIFIED,
    }

    # Disposition patterns
    DISPOSITION_PATTERNS = {
        r"guilty\s*plea": ChargeDisposition.GUILTY_PLEA,
        r"pled\s*guilty": ChargeDisposition.GUILTY_PLEA,
        r"nolo": ChargeDisposition.NOLO_CONTENDERE,
        r"no\s*contest": ChargeDisposition.NOLO_CONTENDERE,
        r"found\s*guilty": ChargeDisposition.FOUND_GUILTY,
        r"guilty": ChargeDisposition.GUILTY,
        r"convicted": ChargeDisposition.GUILTY,
        r"not\s*guilty": ChargeDisposition.NOT_GUILTY,
        r"acquit": ChargeDisposition.ACQUITTED,
        r"dismiss.*prejudice": ChargeDisposition.DISMISSED_WITH_PREJUDICE,
        r"dismiss.*without": ChargeDisposition.DISMISSED_WITHOUT_PREJUDICE,
        r"dismiss": ChargeDisposition.DISMISSED,
        r"nolle\s*pros": ChargeDisposition.NOLLE_PROSEQUI,
        r"no\s*bill": ChargeDisposition.DISMISSED,
        r"deferred\s*adjud": ChargeDisposition.DEFERRED_ADJUDICATION,
        r"deferred": ChargeDisposition.DEFERRED,
        r"pretrial\s*diversion": ChargeDisposition.PRETRIAL_DIVERSION,
        r"diversion": ChargeDisposition.PRETRIAL_DIVERSION,
        r"reduced": ChargeDisposition.REDUCED,
        r"amended": ChargeDisposition.AMENDED,
        r"transfer": ChargeDisposition.TRANSFERRED,
        r"consolidat": ChargeDisposition.CONSOLIDATED,
    }

    def _determine_criminal_case_type(self, raw_type: str) -> CaseType:
        """Determine case type from raw type string."""
        if not raw_type:
            return CaseType.CRIMINAL_FELONY  # Default for criminal courts

        raw_lower = raw_type.lower()

        for pattern, case_type in self.CASE_TYPE_PATTERNS.items():
            if re.search(pattern, raw_lower):
                return case_type

        return CaseType.CRIMINAL_FELONY

    def _determine_charge_level(self, raw_level: str) -> ChargeLevel:
        """Determine charge level from raw string."""
        if not raw_level:
            return ChargeLevel.UNKNOWN

        raw_lower = raw_level.lower()

        for pattern, level in self.CHARGE_LEVEL_PATTERNS.items():
            if re.search(pattern, raw_lower):
                return level

        return ChargeLevel.UNKNOWN

    def _determine_disposition(self, raw_disposition: str) -> ChargeDisposition:
        """Determine disposition from raw string."""
        if not raw_disposition:
            return ChargeDisposition.PENDING

        raw_lower = raw_disposition.lower()

        for pattern, disposition in self.DISPOSITION_PATTERNS.items():
            if re.search(pattern, raw_lower):
                return disposition

        return ChargeDisposition.UNKNOWN

    def _parse_criminal_charges(self, soup: BeautifulSoup) -> List[CriminalCharge]:
        """Parse charges from case detail page."""
        charges = []

        # Look for charges section
        charges_section = (
            soup.find("div", {"id": "charges"}) or
            soup.find("section", {"id": "charges"}) or
            soup.find("table", {"id": "tblCharges"}) or
            soup.find("table", {"class": "charges"})
        )

        if not charges_section:
            return charges

        # Parse charge rows
        charge_num = 1
        for row in charges_section.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            # Extract charge info
            statute = cells[0].get_text(strip=True) if cells else ""
            description = cells[1].get_text(strip=True) if len(cells) > 1 else ""

            if not (statute or description):
                continue

            charge = CriminalCharge(
                charge_number=charge_num,
                statute_code=statute,
                offense_description=description,
            )

            # Parse additional fields
            if len(cells) > 2:
                level_str = cells[2].get_text(strip=True)
                charge.charge_level = self._determine_charge_level(level_str)
                charge.charge_class = level_str

            if len(cells) > 3:
                disp_str = cells[3].get_text(strip=True)
                charge.disposition = self._determine_disposition(disp_str)

            if len(cells) > 4:
                charge.disposition_date = self._parse_date(cells[4].get_text(strip=True))

            if len(cells) > 5:
                charge.offense_date = self._parse_date(cells[5].get_text(strip=True))

            charges.append(charge)
            charge_num += 1

        return charges

    def _parse_defendant(self, soup: BeautifulSoup) -> Optional[CriminalDefendant]:
        """Parse defendant information from case detail page."""
        # Look for defendant section
        defendant_section = (
            soup.find("div", {"id": "defendant"}) or
            soup.find("section", {"id": "party-defendant"}) or
            soup.find("table", {"id": "tblDefendant"})
        )

        if not defendant_section:
            return None

        # Extract name
        name_elem = defendant_section.find("span", {"class": "defendant-name"})
        if not name_elem:
            name_elem = defendant_section.find("td", {"class": "name"})

        name = name_elem.get_text(strip=True) if name_elem else ""

        if not name:
            return None

        defendant = CriminalDefendant(name=name, case_number="")

        # Parse additional fields from table or dl
        for row in defendant_section.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)

                if "dob" in label or "birth" in label:
                    defendant.date_of_birth = self._parse_date(value)
                elif "sex" in label or "gender" in label:
                    defendant.sex = value
                elif "race" in label:
                    defendant.race = value
                elif "sid" in label:
                    defendant.sid = value
                elif "attorney" in label:
                    defendant.attorney_name = value
                elif "address" in label:
                    defendant.address = value
                elif "bond" in label:
                    defendant.bond_amount = self._parse_amount(value)

        return defendant

    async def search_by_defendant(
        self,
        defendant_name: str,
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        case_types: Optional[List[CaseType]] = None,
        include_closed: bool = True,
        max_results: int = 100
    ) -> List[CriminalCaseRecord]:
        """
        Search for criminal cases by defendant name.

        Args:
            defendant_name: Defendant name to search
            filed_start_date: Start of filing date range
            filed_end_date: End of filing date range
            case_types: Filter by case types
            include_closed: Include closed/disposed cases
            max_results: Maximum results

        Returns:
            List of CriminalCaseRecord
        """
        # Default to criminal case types
        if not case_types:
            case_types = [
                CaseType.CRIMINAL_FELONY,
                CaseType.CRIMINAL_MISDEMEANOR,
                CaseType.DUI_DWI,
                CaseType.DRUG_OFFENSE,
            ]

        # Search by party
        results = await self.search_by_party(
            party_name=defendant_name,
            party_type="defendant",
            filed_start_date=filed_start_date,
            filed_end_date=filed_end_date,
            case_types=case_types,
            include_closed=include_closed,
            max_results=max_results
        )

        # Convert to CriminalCaseRecord
        criminal_records = []
        for case in results.cases:
            record = self._case_to_criminal_record(case)
            criminal_records.append(record)

        return criminal_records

    def _case_to_criminal_record(self, case: CourtCase) -> CriminalCaseRecord:
        """Convert a CourtCase to CriminalCaseRecord."""
        # Get defendant info
        defendant = None
        if case.defendants:
            defendant = CriminalDefendant(
                name=case.defendants[0],
                case_number=case.case_number,
            )

        # Convert charges
        charges = []
        for i, charge in enumerate(case.charges, 1):
            criminal_charge = CriminalCharge(
                charge_number=i,
                statute_code=charge.statute or "",
                offense_description=charge.description,
                charge_level=self._determine_charge_level(charge.charge_level or ""),
                disposition=self._determine_disposition(charge.disposition or ""),
                disposition_date=charge.disposition_date,
                offense_date=charge.offense_date,
                fine_amount=charge.fine_amount,
            )
            charges.append(criminal_charge)

        return CriminalCaseRecord(
            case_number=case.case_number,
            court_name=case.court_name,
            court_type=case.court_type,
            defendant=defendant,
            judge_name=case.judge,
            charges=charges,
            filing_date=case.filing_date,
            disposition_date=case.disposition_date,
            status=case.status,
            case_type=case.case_type,
            events=case.events,
            county=case.county or self.COUNTY,
            state=case.state or self.STATE,
            source_url=case.source_url,
            source_system=case.source_system or "",
            raw_data=case.raw_data,
        )

    async def get_criminal_history(
        self,
        person_name: str,
        date_of_birth: Optional[date] = None,
        max_results: int = 100
    ) -> List[CriminalCaseRecord]:
        """
        Get criminal history for a person across all case types.

        Args:
            person_name: Person's name
            date_of_birth: Date of birth for verification
            max_results: Maximum results

        Returns:
            List of CriminalCaseRecord sorted by date
        """
        records = await self.search_by_defendant(
            defendant_name=person_name,
            include_closed=True,
            max_results=max_results
        )

        # If DOB provided, filter matches
        if date_of_birth:
            records = [
                r for r in records
                if r.defendant and r.defendant.date_of_birth == date_of_birth
            ]

        # Sort by filing date
        records.sort(key=lambda x: x.filing_date or date.min, reverse=True)

        return records


class CookCountyCriminal(CountyCriminalCourtBase):
    """
    Cook County, Illinois Criminal Court Scraper.

    Criminal cases in Cook County are handled by the Criminal Division
    of the Circuit Court of Cook County.

    Public access: https://casesearch.cookcountyclerkofcourt.org/
    """

    COURT_NAME = "Circuit Court of Cook County - Criminal Division"
    COUNTY = "Cook"
    STATE = "IL"
    FIPS_CODE = "17031"
    BASE_URL = "https://casesearch.cookcountyclerkofcourt.org/"

    async def search_by_party(
        self,
        party_name: str,
        party_type: str = "defendant",
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        case_types: Optional[List[CaseType]] = None,
        include_closed: bool = True,
        max_results: int = 100
    ) -> SearchResult:
        """Search Cook County criminal cases by party name."""
        import time
        start_time = time.time()

        # Execute search
        search_url = f"{self.BASE_URL}CriminalCaseSearchAPI.aspx/SearchByDefendant"

        data = {
            "defendantName": party_name,
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
            logger.error(f"Cook County criminal search failed: {e}")
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
                case_title=item.get("Defendant", ""),
                case_type=self._determine_criminal_case_type(item.get("CaseType", "")),
                case_type_raw=item.get("CaseType", ""),
                status=self._parse_case_status(item.get("Status", "")),
                filing_date=self._parse_date(item.get("FilingDate", "")),
                county=self.COUNTY,
                state=self.STATE,
                source_system="Cook County Clerk",
                raw_data=item,
            )

            # Add defendant
            if item.get("Defendant"):
                case.defendants.append(item["Defendant"])

            # Parse charges if included
            for charge_item in item.get("Charges", []):
                charge = CaseCharge(
                    statute=charge_item.get("Statute", ""),
                    description=charge_item.get("Description", ""),
                    charge_level=charge_item.get("Level", ""),
                    disposition=charge_item.get("Disposition", ""),
                )
                case.charges.append(charge)

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
        search_url = f"{self.BASE_URL}CriminalCaseSearchAPI.aspx/SearchByCaseNumber"

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

        case = CourtCase(
            case_number=case_data.get("CaseNumber", case_number),
            court_name=self.COURT_NAME,
            court_type=self.COURT_TYPE,
            court_level=self.COURT_LEVEL,
            case_title=case_data.get("Defendant", ""),
            case_type=self._determine_criminal_case_type(case_data.get("CaseType", "")),
            status=self._parse_case_status(case_data.get("Status", "")),
            filing_date=self._parse_date(case_data.get("FilingDate", "")),
            county=self.COUNTY,
            state=self.STATE,
            source_system="Cook County Clerk",
            raw_data=case_data,
        )

        return case

    async def get_case_detail(self, case_number: str) -> Optional[CourtCase]:
        """Get detailed case information."""
        return await self.search_by_case_number(case_number)


class HarrisCountyCriminal(CountyCriminalCourtBase):
    """
    Harris County, Texas Criminal Court Scraper.

    Criminal cases in Harris County are handled by multiple district courts
    and county criminal courts.

    Public access: https://www.hcdistrictclerk.com/
    """

    COURT_NAME = "Harris County Criminal Courts"
    COUNTY = "Harris"
    STATE = "TX"
    FIPS_CODE = "48201"
    BASE_URL = "https://www.hcdistrictclerk.com/"

    async def search_by_party(
        self,
        party_name: str,
        party_type: str = "defendant",
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        case_types: Optional[List[CaseType]] = None,
        include_closed: bool = True,
        max_results: int = 100
    ) -> SearchResult:
        """Search Harris County criminal cases."""
        import time
        start_time = time.time()

        search_url = f"{self.BASE_URL}Common/Public/Public_Search.aspx"

        # Get search page first
        status, html = await self._fetch(search_url)
        viewstate = await self._extract_viewstate(html)

        # Build form data
        data = {
            "__VIEWSTATE": viewstate.get("__VIEWSTATE", ""),
            "__EVENTVALIDATION": viewstate.get("__EVENTVALIDATION", ""),
            "ctl00$cphPublicSearch$txtDefendantName": party_name,
            "ctl00$cphPublicSearch$ddlSearchType": "CRIMINAL",
            "ctl00$cphPublicSearch$btnSearch": "Search",
        }

        # Execute search
        status, html = await self._fetch(search_url, method="POST", data=data)
        soup = self._parse_html(html)

        # Parse results table
        cases = []
        results_table = soup.find("table", {"id": "gvSearchResults"})

        if results_table:
            for row in results_table.find_all("tr")[1:max_results+1]:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    case = CourtCase(
                        case_number=cells[0].get_text(strip=True),
                        court_name=self.COURT_NAME,
                        court_type=self.COURT_TYPE,
                        court_level=self.COURT_LEVEL,
                        case_title=cells[1].get_text(strip=True),
                        case_type=self._determine_criminal_case_type(cells[2].get_text(strip=True)),
                        case_type_raw=cells[2].get_text(strip=True),
                        filing_date=self._parse_date(cells[3].get_text(strip=True) if len(cells) > 3 else ""),
                        county=self.COUNTY,
                        state=self.STATE,
                        source_system="Harris County District Clerk",
                    )

                    if cells[1].get_text(strip=True):
                        case.defendants.append(cells[1].get_text(strip=True))

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


class MaricopaCountyCriminal(CountyCriminalCourtBase):
    """
    Maricopa County, Arizona Criminal Court Scraper.

    Criminal cases are handled by the Maricopa County Superior Court.

    Public access: https://www.superiorcourt.maricopa.gov/
    """

    COURT_NAME = "Maricopa County Superior Court - Criminal"
    COUNTY = "Maricopa"
    STATE = "AZ"
    FIPS_CODE = "04013"
    BASE_URL = "https://www.superiorcourt.maricopa.gov/"

    async def search_by_party(
        self,
        party_name: str,
        party_type: str = "defendant",
        filed_start_date: Optional[date] = None,
        filed_end_date: Optional[date] = None,
        case_types: Optional[List[CaseType]] = None,
        include_closed: bool = True,
        max_results: int = 100
    ) -> SearchResult:
        """Search Maricopa County criminal cases."""
        import time
        start_time = time.time()

        search_url = f"{self.BASE_URL}docket/CriminalCourtCases/Search"

        params = {
            "partyName": party_name,
            "partyType": "DEF",
            "maxResults": max_results,
        }

        if filed_start_date:
            params["startDate"] = filed_start_date.strftime("%m/%d/%Y")
        if filed_end_date:
            params["endDate"] = filed_end_date.strftime("%m/%d/%Y")

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Maricopa County search failed: {e}")
            return SearchResult(
                cases=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(party_name=party_name),
                warnings=[str(e)],
            )

        cases = []
        case_list = json_response.get("cases", [])

        for item in case_list[:max_results]:
            case = CourtCase(
                case_number=item.get("caseNumber", ""),
                court_name=self.COURT_NAME,
                court_type=self.COURT_TYPE,
                court_level=self.COURT_LEVEL,
                case_title=item.get("defendant", ""),
                case_type=self._determine_criminal_case_type(item.get("caseType", "")),
                case_type_raw=item.get("caseType", ""),
                status=self._parse_case_status(item.get("status", "")),
                filing_date=self._parse_date(item.get("filingDate", "")),
                judge=item.get("judge", ""),
                county=self.COUNTY,
                state=self.STATE,
                source_system="Maricopa Superior Court",
                raw_data=item,
            )

            if item.get("defendant"):
                case.defendants.append(item["defendant"])

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
            source_system="Maricopa Superior Court",
        )

    async def search_by_case_number(self, case_number: str) -> Optional[CourtCase]:
        """Search for a specific case by case number."""
        search_url = f"{self.BASE_URL}docket/CriminalCourtCases/Case/{case_number}"

        try:
            json_response = await self._fetch_json(search_url)
        except Exception as e:
            logger.error(f"Maricopa County case search failed: {e}")
            return None

        if not json_response:
            return None

        return CourtCase(
            case_number=json_response.get("caseNumber", case_number),
            court_name=self.COURT_NAME,
            court_type=self.COURT_TYPE,
            court_level=self.COURT_LEVEL,
            case_title=json_response.get("defendant", ""),
            case_type=self._determine_criminal_case_type(json_response.get("caseType", "")),
            status=self._parse_case_status(json_response.get("status", "")),
            filing_date=self._parse_date(json_response.get("filingDate", "")),
            county=self.COUNTY,
            state=self.STATE,
            source_system="Maricopa Superior Court",
            raw_data=json_response,
        )

    async def get_case_detail(self, case_number: str) -> Optional[CourtCase]:
        """Get detailed case information."""
        return await self.search_by_case_number(case_number)


# Factory function to get appropriate criminal court scraper

def get_criminal_court_scraper(
    state: str,
    county: str
) -> Optional[CountyCriminalCourtBase]:
    """
    Get a criminal court scraper for a specific county.

    Args:
        state: State code (e.g., "IL", "TX", "AZ")
        county: County name (e.g., "Cook", "Harris", "Maricopa")

    Returns:
        Configured CountyCriminalCourtBase instance or None
    """
    state = state.upper()
    county_lower = county.lower()

    scrapers = {
        ("IL", "cook"): CookCountyCriminal,
        ("TX", "harris"): HarrisCountyCriminal,
        ("AZ", "maricopa"): MaricopaCountyCriminal,
    }

    scraper_class = scrapers.get((state, county_lower))
    if scraper_class:
        return scraper_class()

    return None


def list_supported_criminal_courts() -> List[Dict[str, str]]:
    """List all supported criminal court implementations."""
    return [
        {"state": "IL", "county": "Cook", "court": "Circuit Court of Cook County - Criminal"},
        {"state": "TX", "county": "Harris", "court": "Harris County Criminal Courts"},
        {"state": "AZ", "county": "Maricopa", "court": "Maricopa County Superior Court - Criminal"},
    ]


# Synchronous wrapper functions

def search_criminal_cases(
    state: str,
    county: str,
    defendant_name: str,
    **kwargs
) -> List[CriminalCaseRecord]:
    """Synchronous wrapper for criminal case search."""
    scraper = get_criminal_court_scraper(state, county)
    if not scraper:
        raise ValueError(f"No criminal court scraper for {county}, {state}")

    async def _search():
        async with scraper:
            return await scraper.search_by_defendant(defendant_name, **kwargs)
    return asyncio.run(_search())


def get_criminal_history(
    state: str,
    county: str,
    person_name: str,
    **kwargs
) -> List[CriminalCaseRecord]:
    """Synchronous wrapper for criminal history search."""
    scraper = get_criminal_court_scraper(state, county)
    if not scraper:
        raise ValueError(f"No criminal court scraper for {county}, {state}")

    async def _search():
        async with scraper:
            return await scraper.get_criminal_history(person_name, **kwargs)
    return asyncio.run(_search())


def get_criminal_case(
    state: str,
    county: str,
    case_number: str
) -> Optional[CourtCase]:
    """Synchronous wrapper for criminal case detail."""
    scraper = get_criminal_court_scraper(state, county)
    if not scraper:
        raise ValueError(f"No criminal court scraper for {county}, {state}")

    async def _get():
        async with scraper:
            return await scraper.get_case_detail(case_number)
    return asyncio.run(_get())
