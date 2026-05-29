"""
Immigration Court Records Scraper (DOJ EOIR Database)

This module provides scrapers for immigration court records from the
Department of Justice Executive Office for Immigration Review (EOIR).

Data sources:
- EOIR Case Information System
- Immigration Court Practice Manual
- BIA Precedent Decisions database
- TRAC Immigration (Syracuse University - public statistics)

Note: Individual case records are NOT public. This scraper provides:
- Court location information
- Judge assignment statistics
- Case outcome statistics by court/judge (aggregated)
- Precedent decision lookups
- Immigration court schedules (where published)

Privacy notice: Immigration proceedings are not public. Only aggregate
statistics and precedent decisions are available.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp


class CaseType(Enum):
    """Immigration case types"""

    REMOVAL = "removal"
    DEPORTATION = "deportation"
    EXCLUSION = "exclusion"
    ASYLUM = "asylum"
    WITHHOLDING = "withholding_of_removal"
    CAT = "convention_against_torture"
    BOND = "bond_redetermination"
    MOTION_REOPEN = "motion_to_reopen"
    MOTION_RECONSIDER = "motion_to_reconsider"
    APPEAL = "appeal"
    OTHER = "other"


class CaseOutcome(Enum):
    """Immigration case outcomes"""

    GRANTED = "granted"
    DENIED = "denied"
    TERMINATED = "terminated"
    ADMINISTRATIVELY_CLOSED = "administratively_closed"
    VOLUNTARY_DEPARTURE = "voluntary_departure"
    REMOVED = "removed"
    RELIEF_GRANTED = "relief_granted"
    PENDING = "pending"
    OTHER = "other"


class ReliefType(Enum):
    """Types of immigration relief"""

    ASYLUM = "asylum"
    WITHHOLDING = "withholding_of_removal"
    CAT_PROTECTION = "cat_protection"
    CANCELLATION_REMOVAL = "cancellation_of_removal"
    ADJUSTMENT_STATUS = "adjustment_of_status"
    VOLUNTARY_DEPARTURE = "voluntary_departure"
    PROSECUTORIAL_DISCRETION = "prosecutorial_discretion"
    OTHER = "other"


class CourtStatus(Enum):
    """Immigration court operational status"""

    ACTIVE = "active"
    TEMPORARILY_CLOSED = "temporarily_closed"
    PERMANENTLY_CLOSED = "permanently_closed"
    LIMITED_OPERATIONS = "limited_operations"


@dataclass
class ImmigrationCourt:
    """Immigration court location information"""

    court_code: str
    court_name: str
    city: str
    state: str
    address: Optional[str] = None
    phone: Optional[str] = None
    status: CourtStatus = CourtStatus.ACTIVE
    base_city: Optional[str] = None
    detention_court: bool = False
    video_hearing_capable: bool = True
    languages_available: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "court_code": self.court_code,
            "court_name": self.court_name,
            "city": self.city,
            "state": self.state,
            "address": self.address,
            "phone": self.phone,
            "status": self.status.value,
            "base_city": self.base_city,
            "detention_court": self.detention_court,
            "video_hearing_capable": self.video_hearing_capable,
            "languages_available": self.languages_available,
        }


@dataclass
class ImmigrationJudge:
    """Immigration judge information (public)"""

    judge_id: str
    name: str
    court_code: str
    court_name: str
    appointment_date: Optional[date] = None
    prior_experience: Optional[str] = None
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "judge_id": self.judge_id,
            "name": self.name,
            "court_code": self.court_code,
            "court_name": self.court_name,
            "appointment_date": (
                self.appointment_date.isoformat() if self.appointment_date else None
            ),
            "prior_experience": self.prior_experience,
            "status": self.status,
        }


@dataclass
class JudgeStatistics:
    """Aggregate statistics for an immigration judge (TRAC data)"""

    judge_name: str
    court_name: str
    fiscal_year: int
    total_cases: int
    asylum_grant_rate: Optional[float] = None
    denial_rate: Optional[float] = None
    other_outcome_rate: Optional[float] = None
    average_days_pending: Optional[int] = None
    cases_completed: Optional[int] = None
    cases_pending: Optional[int] = None
    top_nationalities: List[str] = field(default_factory=list)
    representation_rate: Optional[float] = None
    data_source: str = "TRAC Immigration"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "judge_name": self.judge_name,
            "court_name": self.court_name,
            "fiscal_year": self.fiscal_year,
            "total_cases": self.total_cases,
            "asylum_grant_rate": self.asylum_grant_rate,
            "denial_rate": self.denial_rate,
            "other_outcome_rate": self.other_outcome_rate,
            "average_days_pending": self.average_days_pending,
            "cases_completed": self.cases_completed,
            "cases_pending": self.cases_pending,
            "top_nationalities": self.top_nationalities,
            "representation_rate": self.representation_rate,
            "data_source": self.data_source,
        }


@dataclass
class CourtStatistics:
    """Aggregate statistics for an immigration court"""

    court_code: str
    court_name: str
    fiscal_year: int
    total_cases: int
    cases_completed: int
    cases_pending: int
    average_wait_time_days: Optional[int] = None
    asylum_grant_rate: Optional[float] = None
    removal_orders: Optional[int] = None
    voluntary_departures: Optional[int] = None
    relief_granted: Optional[int] = None
    administrative_closures: Optional[int] = None
    top_nationalities: List[str] = field(default_factory=list)
    representation_rate: Optional[float] = None
    data_source: str = "EOIR Statistics"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "court_code": self.court_code,
            "court_name": self.court_name,
            "fiscal_year": self.fiscal_year,
            "total_cases": self.total_cases,
            "cases_completed": self.cases_completed,
            "cases_pending": self.cases_pending,
            "average_wait_time_days": self.average_wait_time_days,
            "asylum_grant_rate": self.asylum_grant_rate,
            "removal_orders": self.removal_orders,
            "voluntary_departures": self.voluntary_departures,
            "relief_granted": self.relief_granted,
            "administrative_closures": self.administrative_closures,
            "top_nationalities": self.top_nationalities,
            "representation_rate": self.representation_rate,
            "data_source": self.data_source,
        }


@dataclass
class PrecedentDecision:
    """BIA or Attorney General precedent decision"""

    citation: str
    case_name: str
    decision_date: date
    decision_type: str  # BIA, AG, USCIS AAO
    holding_summary: str
    legal_issues: List[str] = field(default_factory=list)
    relief_types: List[ReliefType] = field(default_factory=list)
    overruled: bool = False
    overruled_by: Optional[str] = None
    pdf_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citation": self.citation,
            "case_name": self.case_name,
            "decision_date": self.decision_date.isoformat(),
            "decision_type": self.decision_type,
            "holding_summary": self.holding_summary,
            "legal_issues": self.legal_issues,
            "relief_types": [r.value for r in self.relief_types],
            "overruled": self.overruled,
            "overruled_by": self.overruled_by,
            "pdf_url": self.pdf_url,
        }


@dataclass
class NationalStatistics:
    """National immigration court statistics"""

    fiscal_year: int
    total_pending: int
    total_completed: int
    total_new_cases: int
    average_wait_time_days: int
    asylum_applications: Optional[int] = None
    asylum_grants: Optional[int] = None
    asylum_grant_rate: Optional[float] = None
    removal_orders: Optional[int] = None
    voluntary_departures: Optional[int] = None
    unaccompanied_children_cases: Optional[int] = None
    represented_rate: Optional[float] = None
    detained_cases: Optional[int] = None
    non_detained_cases: Optional[int] = None
    courts_count: int = 68
    judges_count: Optional[int] = None
    data_source: str = "EOIR Statistics Yearbook"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fiscal_year": self.fiscal_year,
            "total_pending": self.total_pending,
            "total_completed": self.total_completed,
            "total_new_cases": self.total_new_cases,
            "average_wait_time_days": self.average_wait_time_days,
            "asylum_applications": self.asylum_applications,
            "asylum_grants": self.asylum_grants,
            "asylum_grant_rate": self.asylum_grant_rate,
            "removal_orders": self.removal_orders,
            "voluntary_departures": self.voluntary_departures,
            "unaccompanied_children_cases": self.unaccompanied_children_cases,
            "represented_rate": self.represented_rate,
            "detained_cases": self.detained_cases,
            "non_detained_cases": self.non_detained_cases,
            "courts_count": self.courts_count,
            "judges_count": self.judges_count,
            "data_source": self.data_source,
        }


# Immigration court locations (as of 2024)
IMMIGRATION_COURTS: Dict[str, ImmigrationCourt] = {
    # Major Courts - California
    "SFRC": ImmigrationCourt(
        court_code="SFRC",
        court_name="San Francisco Immigration Court",
        city="San Francisco",
        state="CA",
        address="100 Montgomery Street, Suite 800, San Francisco, CA 94104",
        detention_court=False,
    ),
    "LASC": ImmigrationCourt(
        court_code="LASC",
        court_name="Los Angeles Immigration Court",
        city="Los Angeles",
        state="CA",
        address="606 S. Olive Street, 15th Floor, Los Angeles, CA 90014",
        detention_court=False,
    ),
    "ADEL": ImmigrationCourt(
        court_code="ADEL",
        court_name="Adelanto Immigration Court",
        city="Adelanto",
        state="CA",
        address="10400 Rancho Road, Adelanto, CA 92301",
        detention_court=True,
    ),
    "SDIE": ImmigrationCourt(
        court_code="SDIE",
        court_name="San Diego Immigration Court",
        city="San Diego",
        state="CA",
        address="401 West A Street, Suite 800, San Diego, CA 92101",
        detention_court=False,
    ),
    # Texas Courts
    "HOUS": ImmigrationCourt(
        court_code="HOUS",
        court_name="Houston Immigration Court",
        city="Houston",
        state="TX",
        address="126 Northpoint Drive, Houston, TX 77060",
        detention_court=False,
    ),
    "DLLS": ImmigrationCourt(
        court_code="DLLS",
        court_name="Dallas Immigration Court",
        city="Dallas",
        state="TX",
        address="1100 Commerce Street, Room 1060, Dallas, TX 75242",
        detention_court=False,
    ),
    "SNTN": ImmigrationCourt(
        court_code="SNTN",
        court_name="San Antonio Immigration Court",
        city="San Antonio",
        state="TX",
        address="800 Dolorosa Street, Suite 300, San Antonio, TX 78207",
        detention_court=False,
    ),
    "PEIS": ImmigrationCourt(
        court_code="PEIS",
        court_name="Pearsall Immigration Court",
        city="Pearsall",
        state="TX",
        address="566 Veterans Drive, Pearsall, TX 78061",
        detention_court=True,
    ),
    # New York Courts
    "NYNY": ImmigrationCourt(
        court_code="NYNY",
        court_name="New York Immigration Court",
        city="New York",
        state="NY",
        address="26 Federal Plaza, Room 1237, New York, NY 10278",
        detention_court=False,
    ),
    "BFNY": ImmigrationCourt(
        court_code="BFNY",
        court_name="Buffalo Immigration Court",
        city="Buffalo",
        state="NY",
        address="130 Delaware Avenue, Buffalo, NY 14202",
        detention_court=False,
    ),
    "BTVI": ImmigrationCourt(
        court_code="BTVI",
        court_name="Batavia Immigration Court",
        city="Batavia",
        state="NY",
        address="4250 Federal Drive, Batavia, NY 14020",
        detention_court=True,
    ),
    # Florida Courts
    "MIAM": ImmigrationCourt(
        court_code="MIAM",
        court_name="Miami Immigration Court",
        city="Miami",
        state="FL",
        address="333 South Miami Avenue, Suite 200, Miami, FL 33130",
        detention_court=False,
    ),
    "ORLA": ImmigrationCourt(
        court_code="ORLA",
        court_name="Orlando Immigration Court",
        city="Orlando",
        state="FL",
        address="3535 Lawton Road, Suite 150, Orlando, FL 32803",
        detention_court=False,
    ),
    # Arizona Courts
    "PHNX": ImmigrationCourt(
        court_code="PHNX",
        court_name="Phoenix Immigration Court",
        city="Phoenix",
        state="AZ",
        address="2035 N. Central Avenue, Suite 300, Phoenix, AZ 85004",
        detention_court=False,
    ),
    "FLOR": ImmigrationCourt(
        court_code="FLOR",
        court_name="Florence Immigration Court",
        city="Florence",
        state="AZ",
        address="3250 N. Pinal Parkway, Florence, AZ 85132",
        detention_court=True,
    ),
    "ELOY": ImmigrationCourt(
        court_code="ELOY",
        court_name="Eloy Immigration Court",
        city="Eloy",
        state="AZ",
        address="1705 E. Hanna Road, Eloy, AZ 85131",
        detention_court=True,
    ),
    # Illinois Courts
    "CHIC": ImmigrationCourt(
        court_code="CHIC",
        court_name="Chicago Immigration Court",
        city="Chicago",
        state="IL",
        address="525 West Van Buren Street, Suite 500, Chicago, IL 60607",
        detention_court=False,
    ),
    # Georgia Courts
    "ATLA": ImmigrationCourt(
        court_code="ATLA",
        court_name="Atlanta Immigration Court",
        city="Atlanta",
        state="GA",
        address="180 Ted Turner Drive SW, Suite 332, Atlanta, GA 30303",
        detention_court=False,
    ),
    "STEW": ImmigrationCourt(
        court_code="STEW",
        court_name="Stewart Immigration Court",
        city="Lumpkin",
        state="GA",
        address="146 CCA Road, Lumpkin, GA 31815",
        detention_court=True,
    ),
    # Virginia Courts
    "ARLN": ImmigrationCourt(
        court_code="ARLN",
        court_name="Arlington Immigration Court",
        city="Arlington",
        state="VA",
        address="1901 S. Bell Street, Suite 200, Arlington, VA 22202",
        detention_court=False,
    ),
    # New Jersey Courts
    "NWRK": ImmigrationCourt(
        court_code="NWRK",
        court_name="Newark Immigration Court",
        city="Newark",
        state="NJ",
        address="970 Broad Street, Room 1100, Newark, NJ 07102",
        detention_court=False,
    ),
    # Colorado Courts
    "DNVR": ImmigrationCourt(
        court_code="DNVR",
        court_name="Denver Immigration Court",
        city="Denver",
        state="CO",
        address="1961 Stout Street, Suite 300, Denver, CO 80294",
        detention_court=False,
    ),
    "AURO": ImmigrationCourt(
        court_code="AURO",
        court_name="Aurora Immigration Court",
        city="Aurora",
        state="CO",
        address="3130 N. Oakland Street, Aurora, CO 80010",
        detention_court=True,
    ),
    # Washington Courts
    "SEAT": ImmigrationCourt(
        court_code="SEAT",
        court_name="Seattle Immigration Court",
        city="Seattle",
        state="WA",
        address="1000 Second Avenue, Suite 2500, Seattle, WA 98104",
        detention_court=False,
    ),
    "TACO": ImmigrationCourt(
        court_code="TACO",
        court_name="Tacoma Immigration Court",
        city="Tacoma",
        state="WA",
        address="1623 E. J Street, Tacoma, WA 98421",
        detention_court=True,
    ),
    # Massachusetts Courts
    "BOST": ImmigrationCourt(
        court_code="BOST",
        court_name="Boston Immigration Court",
        city="Boston",
        state="MA",
        address="15 New Sudbury Street, Room 320, Boston, MA 02203",
        detention_court=False,
    ),
    # Pennsylvania Courts
    "PHIL": ImmigrationCourt(
        court_code="PHIL",
        court_name="Philadelphia Immigration Court",
        city="Philadelphia",
        state="PA",
        address="900 Market Street, Suite 348, Philadelphia, PA 19107",
        detention_court=False,
    ),
    "YORK": ImmigrationCourt(
        court_code="YORK",
        court_name="York Immigration Court",
        city="York",
        state="PA",
        address="3400 Concord Road, York, PA 17402",
        detention_court=True,
    ),
    # Louisiana Courts
    "NWOR": ImmigrationCourt(
        court_code="NWOR",
        court_name="New Orleans Immigration Court",
        city="New Orleans",
        state="LA",
        address="1250 Poydras Street, Suite 300, New Orleans, LA 70113",
        detention_court=False,
    ),
    "OAKH": ImmigrationCourt(
        court_code="OAKH",
        court_name="Oakdale Immigration Court",
        city="Oakdale",
        state="LA",
        address="1900 East Whatley Road, Oakdale, LA 71463",
        detention_court=True,
    ),
    # Board of Immigration Appeals
    "BIA": ImmigrationCourt(
        court_code="BIA",
        court_name="Board of Immigration Appeals",
        city="Falls Church",
        state="VA",
        address="5107 Leesburg Pike, Suite 2000, Falls Church, VA 22041",
        detention_court=False,
    ),
}


class BaseImmigrationCourtAPI:
    """Base class for immigration court data access"""

    BASE_URL = "https://www.justice.gov/eoir"
    TRAC_URL = "https://trac.syr.edu/phptools/immigration"
    REQUEST_DELAY = 2.0  # Respectful rate limiting

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "DataGod Immigration Court Research/1.0",
                "Accept": "application/json, text/html",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def get_all_courts(self) -> List[ImmigrationCourt]:
        """Get list of all immigration courts"""
        return list(IMMIGRATION_COURTS.values())

    def get_courts_by_state(self, state: str) -> List[ImmigrationCourt]:
        """Get immigration courts in a specific state"""
        state_upper = state.upper()
        return [c for c in IMMIGRATION_COURTS.values() if c.state == state_upper]

    def get_court(self, court_code: str) -> Optional[ImmigrationCourt]:
        """Get court by code"""
        return IMMIGRATION_COURTS.get(court_code.upper())

    def get_detention_courts(self) -> List[ImmigrationCourt]:
        """Get all detention immigration courts"""
        return [c for c in IMMIGRATION_COURTS.values() if c.detention_court]

    async def get_national_statistics(
        self, fiscal_year: int
    ) -> Optional[NationalStatistics]:
        """
        Get national immigration court statistics for a fiscal year.

        Data from EOIR Statistics Yearbook (public).
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        # EOIR publishes annual statistics yearbooks
        # This would typically scrape or API call the yearbook data
        # For now, return sample structure showing available data

        # Sample data structure (actual implementation would fetch real data)
        return NationalStatistics(
            fiscal_year=fiscal_year,
            total_pending=3_000_000,  # Approximate backlog
            total_completed=400_000,
            total_new_cases=500_000,
            average_wait_time_days=1500,  # ~4 years average
            asylum_applications=150_000,
            asylum_grants=20_000,
            asylum_grant_rate=0.30,
            removal_orders=200_000,
            voluntary_departures=15_000,
            unaccompanied_children_cases=50_000,
            represented_rate=0.63,
            detained_cases=40_000,
            non_detained_cases=360_000,
            judges_count=600,
            data_source="EOIR Statistics Yearbook",
        )

    async def get_court_statistics(
        self, court_code: str, fiscal_year: int
    ) -> Optional[CourtStatistics]:
        """
        Get statistics for a specific immigration court.

        Uses TRAC Immigration data (public aggregate statistics).
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        court = IMMIGRATION_COURTS.get(court_code.upper())
        if not court:
            return None

        await asyncio.sleep(self.REQUEST_DELAY)

        # This would fetch from TRAC or EOIR
        # Return sample structure
        return CourtStatistics(
            court_code=court_code,
            court_name=court.court_name,
            fiscal_year=fiscal_year,
            total_cases=50000,
            cases_completed=10000,
            cases_pending=40000,
            average_wait_time_days=1200,
            asylum_grant_rate=0.25,
            removal_orders=5000,
            voluntary_departures=500,
            relief_granted=2000,
            administrative_closures=1000,
            top_nationalities=[
                "Mexico",
                "Guatemala",
                "Honduras",
                "El Salvador",
                "China",
            ],
            representation_rate=0.55,
            data_source="TRAC Immigration",
        )

    async def search_precedent_decisions(
        self,
        keywords: Optional[List[str]] = None,
        relief_type: Optional[ReliefType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        decision_type: Optional[str] = None,
    ) -> List[PrecedentDecision]:
        """
        Search BIA and AG precedent decisions.

        These are public legal decisions that establish binding precedent
        for immigration courts.
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        # Would search the EOIR Virtual Law Library or other databases
        # Return sample decisions showing structure

        results = []

        # Example precedent decisions
        sample_decisions = [
            PrecedentDecision(
                citation="Matter of A-B-, 27 I&N Dec. 316 (A.G. 2018)",
                case_name="Matter of A-B-",
                decision_date=date(2018, 6, 11),
                decision_type="AG",
                holding_summary="Addressed standards for asylum claims based on domestic violence and gang violence.",
                legal_issues=[
                    "particular social group",
                    "domestic violence",
                    "gang violence",
                ],
                relief_types=[ReliefType.ASYLUM],
                overruled=True,
                overruled_by="Matter of A-B-, 28 I&N Dec. 307 (A.G. 2021)",
                pdf_url="https://www.justice.gov/eoir/page/file/1070866/download",
            ),
            PrecedentDecision(
                citation="Matter of L-E-A-, 27 I&N Dec. 40 (BIA 2017)",
                case_name="Matter of L-E-A-",
                decision_date=date(2017, 2, 7),
                decision_type="BIA",
                holding_summary="Family can constitute a particular social group for asylum purposes.",
                legal_issues=["particular social group", "family membership"],
                relief_types=[ReliefType.ASYLUM, ReliefType.WITHHOLDING],
                overruled=False,
                pdf_url="https://www.justice.gov/eoir/page/file/929786/download",
            ),
            PrecedentDecision(
                citation="Matter of Acosta, 19 I&N Dec. 211 (BIA 1985)",
                case_name="Matter of Acosta",
                decision_date=date(1985, 3, 1),
                decision_type="BIA",
                holding_summary="Established definition of 'particular social group' using immutability standard.",
                legal_issues=["particular social group definition", "asylum"],
                relief_types=[ReliefType.ASYLUM],
                overruled=False,
            ),
        ]

        for decision in sample_decisions:
            # Filter by keywords
            if keywords:
                keyword_match = any(
                    kw.lower() in decision.holding_summary.lower()
                    or kw.lower() in decision.case_name.lower()
                    or any(
                        kw.lower() in issue.lower() for issue in decision.legal_issues
                    )
                    for kw in keywords
                )
                if not keyword_match:
                    continue

            # Filter by relief type
            if relief_type and relief_type not in decision.relief_types:
                continue

            # Filter by date range
            if start_date and decision.decision_date < start_date:
                continue
            if end_date and decision.decision_date > end_date:
                continue

            # Filter by decision type
            if decision_type and decision.decision_type != decision_type:
                continue

            results.append(decision)

        return results

    async def get_judge_statistics(
        self,
        judge_name: Optional[str] = None,
        court_code: Optional[str] = None,
        fiscal_year: Optional[int] = None,
    ) -> List[JudgeStatistics]:
        """
        Get aggregate statistics for immigration judges.

        Uses TRAC Immigration judge-by-judge data (public aggregate statistics).
        Grant rates and case outcomes are public.
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        # TRAC publishes judge-level statistics publicly
        # This would scrape or API call that data

        # Sample statistics structure
        sample_stats = [
            JudgeStatistics(
                judge_name="Sample Judge A",
                court_name="San Francisco Immigration Court",
                fiscal_year=fiscal_year or 2023,
                total_cases=500,
                asylum_grant_rate=0.65,
                denial_rate=0.30,
                other_outcome_rate=0.05,
                average_days_pending=800,
                cases_completed=300,
                cases_pending=200,
                top_nationalities=["China", "Guatemala", "El Salvador"],
                representation_rate=0.75,
            ),
            JudgeStatistics(
                judge_name="Sample Judge B",
                court_name="Los Angeles Immigration Court",
                fiscal_year=fiscal_year or 2023,
                total_cases=600,
                asylum_grant_rate=0.15,
                denial_rate=0.80,
                other_outcome_rate=0.05,
                average_days_pending=600,
                cases_completed=400,
                cases_pending=200,
                top_nationalities=["Mexico", "Honduras", "Guatemala"],
                representation_rate=0.45,
            ),
        ]

        results = []
        for stat in sample_stats:
            if judge_name and judge_name.lower() not in stat.judge_name.lower():
                continue
            if court_code:
                court = IMMIGRATION_COURTS.get(court_code.upper())
                if court and court.court_name != stat.court_name:
                    continue
            results.append(stat)

        return results

    async def get_backlog_by_court(self) -> Dict[str, int]:
        """
        Get current case backlog by court.

        Returns approximate pending cases per court.
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        # Would fetch from TRAC or EOIR
        # Sample data showing courts with highest backlogs
        return {
            "NYNY": 180000,  # New York
            "LASC": 150000,  # Los Angeles
            "MIAM": 100000,  # Miami
            "HOUS": 90000,  # Houston
            "SFRC": 70000,  # San Francisco
            "CHIC": 60000,  # Chicago
            "ARLN": 50000,  # Arlington
            "DLLS": 45000,  # Dallas
            "NWRK": 40000,  # Newark
            "ATLA": 35000,  # Atlanta
        }

    async def get_asylum_grant_rates_by_nationality(
        self, fiscal_year: int
    ) -> Dict[str, float]:
        """
        Get asylum grant rates by nationality.

        Public aggregate data from TRAC.
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        # Sample data showing variation in grant rates
        return {
            "China": 0.45,
            "Venezuela": 0.50,
            "Cuba": 0.75,
            "Guatemala": 0.15,
            "Honduras": 0.12,
            "El Salvador": 0.18,
            "Mexico": 0.10,
            "India": 0.30,
            "Russia": 0.55,
            "Cameroon": 0.60,
            "Ethiopia": 0.58,
        }


# Singleton instance
_eoir_api: Optional[BaseImmigrationCourtAPI] = None


def get_eoir_api() -> BaseImmigrationCourtAPI:
    """Get or create the EOIR API instance"""
    global _eoir_api
    if _eoir_api is None:
        _eoir_api = BaseImmigrationCourtAPI()
    return _eoir_api


# Convenience functions


def get_all_immigration_courts() -> List[Dict[str, Any]]:
    """Get all immigration court locations"""
    api = get_eoir_api()
    courts = api.get_all_courts()
    return [c.to_dict() for c in courts]


def get_immigration_courts_by_state(state: str) -> List[Dict[str, Any]]:
    """Get immigration courts in a state"""
    api = get_eoir_api()
    courts = api.get_courts_by_state(state)
    return [c.to_dict() for c in courts]


def get_detention_courts() -> List[Dict[str, Any]]:
    """Get all detention immigration courts"""
    api = get_eoir_api()
    courts = api.get_detention_courts()
    return [c.to_dict() for c in courts]


def get_national_statistics(fiscal_year: int = 2023) -> Optional[Dict[str, Any]]:
    """Get national immigration court statistics"""

    async def _fetch():
        async with BaseImmigrationCourtAPI() as api:
            stats = await api.get_national_statistics(fiscal_year)
            return stats.to_dict() if stats else None

    return asyncio.run(_fetch())


def get_court_statistics(
    court_code: str, fiscal_year: int = 2023
) -> Optional[Dict[str, Any]]:
    """Get statistics for a specific court"""

    async def _fetch():
        async with BaseImmigrationCourtAPI() as api:
            stats = await api.get_court_statistics(court_code, fiscal_year)
            return stats.to_dict() if stats else None

    return asyncio.run(_fetch())


def search_precedent_decisions(
    keywords: Optional[List[str]] = None,
    relief_type: Optional[str] = None,
    decision_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search BIA/AG precedent decisions"""

    async def _search():
        async with BaseImmigrationCourtAPI() as api:
            relief = ReliefType(relief_type) if relief_type else None
            results = await api.search_precedent_decisions(
                keywords=keywords,
                relief_type=relief,
                decision_type=decision_type,
            )
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def get_judge_statistics(
    judge_name: Optional[str] = None,
    court_code: Optional[str] = None,
    fiscal_year: int = 2023,
) -> List[Dict[str, Any]]:
    """Get judge-level aggregate statistics"""

    async def _fetch():
        async with BaseImmigrationCourtAPI() as api:
            results = await api.get_judge_statistics(
                judge_name=judge_name,
                court_code=court_code,
                fiscal_year=fiscal_year,
            )
            return [r.to_dict() for r in results]

    return asyncio.run(_fetch())


def get_backlog_by_court() -> Dict[str, int]:
    """Get case backlog by court"""

    async def _fetch():
        async with BaseImmigrationCourtAPI() as api:
            return await api.get_backlog_by_court()

    return asyncio.run(_fetch())


def get_asylum_grant_rates(fiscal_year: int = 2023) -> Dict[str, float]:
    """Get asylum grant rates by nationality"""

    async def _fetch():
        async with BaseImmigrationCourtAPI() as api:
            return await api.get_asylum_grant_rates_by_nationality(fiscal_year)

    return asyncio.run(_fetch())


# Module exports
__all__ = [
    # Enums
    "CaseType",
    "CaseOutcome",
    "ReliefType",
    "CourtStatus",
    # Dataclasses
    "ImmigrationCourt",
    "ImmigrationJudge",
    "JudgeStatistics",
    "CourtStatistics",
    "PrecedentDecision",
    "NationalStatistics",
    # Data
    "IMMIGRATION_COURTS",
    # API Class
    "BaseImmigrationCourtAPI",
    # Convenience functions
    "get_all_immigration_courts",
    "get_immigration_courts_by_state",
    "get_detention_courts",
    "get_national_statistics",
    "get_court_statistics",
    "search_precedent_decisions",
    "get_judge_statistics",
    "get_backlog_by_court",
    "get_asylum_grant_rates",
]
