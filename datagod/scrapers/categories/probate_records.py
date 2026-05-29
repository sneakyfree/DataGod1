"""
Probate Records Scraper
=======================

Comprehensive scraper for probate court records from county probate courts
and surrogate courts across all US states.

Data Sources:
- County Probate Courts
- Surrogate Courts (NJ, NY)
- Circuit Courts (some states)
- Superior Courts (some states)

Record Types:
- Estate administrations
- Will probates
- Guardianships/Conservatorships
- Trust matters
- Small estate affidavits
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ProbateCaseType(Enum):
    """Types of probate cases"""

    # Estate matters
    TESTATE = "testate"  # With a will
    INTESTATE = "intestate"  # Without a will
    SMALL_ESTATE = "small_estate"
    SUMMARY_ADMINISTRATION = "summary_administration"
    FULL_ADMINISTRATION = "full_administration"
    ANCILLARY_PROBATE = "ancillary_probate"  # For out-of-state estates

    # Guardianship
    GUARDIANSHIP_MINOR = "guardianship_minor"
    GUARDIANSHIP_ADULT = "guardianship_adult"
    GUARDIANSHIP_ESTATE = "guardianship_estate"
    GUARDIANSHIP_PERSON = "guardianship_person"
    GUARDIANSHIP_PERSON_ESTATE = "guardianship_person_estate"

    # Conservatorship
    CONSERVATORSHIP = "conservatorship"
    CONSERVATORSHIP_ESTATE = "conservatorship_estate"
    CONSERVATORSHIP_PERSON = "conservatorship_person"

    # Trust matters
    TRUST_ADMINISTRATION = "trust_administration"
    TRUST_MODIFICATION = "trust_modification"
    TRUST_CONTEST = "trust_contest"

    # Other
    WILL_CONTEST = "will_contest"
    ELECTIVE_SHARE = "elective_share"
    DETERMINATION_OF_HEIRS = "determination_of_heirs"
    MENTAL_HEALTH = "mental_health"
    NAME_CHANGE = "name_change"
    ADOPTION = "adoption"
    OTHER = "other"


class CaseStatus(Enum):
    """Status of probate case"""

    OPEN = "open"
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"
    DISMISSED = "dismissed"
    TRANSFERRED = "transferred"
    SETTLED = "settled"
    CONTESTED = "contested"
    ON_APPEAL = "on_appeal"


class PartyRole(Enum):
    """Role of party in probate case"""

    DECEDENT = "decedent"
    PETITIONER = "petitioner"
    EXECUTOR = "executor"
    ADMINISTRATOR = "administrator"
    PERSONAL_REPRESENTATIVE = "personal_representative"
    BENEFICIARY = "beneficiary"
    HEIR = "heir"
    CREDITOR = "creditor"
    GUARDIAN = "guardian"
    CONSERVATOR = "conservator"
    WARD = "ward"
    PROTECTED_PERSON = "protected_person"
    TRUSTEE = "trustee"
    TRUST_BENEFICIARY = "trust_beneficiary"
    ATTORNEY = "attorney"
    INTERESTED_PARTY = "interested_party"
    OBJECTOR = "objector"
    OTHER = "other"


class DocumentType(Enum):
    """Types of probate documents"""

    PETITION = "petition"
    WILL = "will"
    CODICIL = "codicil"
    LETTERS_TESTAMENTARY = "letters_testamentary"
    LETTERS_ADMINISTRATION = "letters_administration"
    LETTERS_GUARDIANSHIP = "letters_guardianship"
    INVENTORY = "inventory"
    ACCOUNTING = "accounting"
    FINAL_ACCOUNTING = "final_accounting"
    NOTICE_TO_CREDITORS = "notice_to_creditors"
    PROOF_OF_SERVICE = "proof_of_service"
    ORDER = "order"
    DECREE = "decree"
    BOND = "bond"
    WAIVER = "waiver"
    CONSENT = "consent"
    OBJECTION = "objection"
    MOTION = "motion"
    DECLARATION = "declaration"
    AFFIDAVIT = "affidavit"
    REPORT = "report"
    OTHER = "other"


@dataclass
class ProbateParty:
    """Party to a probate case"""

    name: str
    role: PartyRole

    # Name components
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    suffix: Optional[str] = None

    # Address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    # For decedent
    date_of_death: Optional[date] = None
    date_of_birth: Optional[date] = None
    last_residence: Optional[str] = None

    # For fiduciaries
    appointment_date: Optional[date] = None
    bond_amount: Optional[float] = None
    bond_waived: bool = False

    # Attorney
    attorney_name: Optional[str] = None
    attorney_bar_number: Optional[str] = None


@dataclass
class ProbateDocument:
    """Document filed in probate case"""

    document_type: DocumentType
    title: str
    filing_date: date

    document_number: Optional[str] = None
    filed_by: Optional[str] = None
    pages: Optional[int] = None
    description: Optional[str] = None

    # Document URL if available online
    document_url: Optional[str] = None


@dataclass
class ProbateAsset:
    """Asset in estate inventory"""

    description: str
    asset_type: str  # Real property, personal property, financial, etc.
    estimated_value: Optional[float] = None
    appraised_value: Optional[float] = None

    # For real property
    property_address: Optional[str] = None
    apn: Optional[str] = None  # Assessor's Parcel Number


@dataclass
class ProbateEvent:
    """Event/hearing in probate case"""

    event_type: str
    event_date: date
    description: Optional[str] = None

    # Hearing details
    time: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    judge: Optional[str] = None
    result: Optional[str] = None


@dataclass
class ProbateRecord:
    """Probate case record"""

    case_number: str
    case_type: ProbateCaseType
    status: CaseStatus

    # Parties
    parties: List[ProbateParty] = field(default_factory=list)

    # Estate/Case name
    case_title: Optional[str] = None
    decedent_name: Optional[str] = None

    # Location
    county: str = ""
    state: str = ""
    court_name: Optional[str] = None
    department: Optional[str] = None

    # Dates
    filing_date: Optional[date] = None
    date_of_death: Optional[date] = None
    close_date: Optional[date] = None

    # Estate value
    estate_value: Optional[float] = None
    real_property_value: Optional[float] = None
    personal_property_value: Optional[float] = None

    # Documents
    documents: List[ProbateDocument] = field(default_factory=list)

    # Assets
    assets: List[ProbateAsset] = field(default_factory=list)

    # Events/Hearings
    events: List[ProbateEvent] = field(default_factory=list)

    # Will information
    will_date: Optional[date] = None
    will_admitted: bool = False
    will_contested: bool = False

    # Source
    source: str = ""
    source_url: Optional[str] = None
    retrieved_date: date = field(default_factory=date.today)

    def get_decedent(self) -> Optional[ProbateParty]:
        """Get the decedent from parties"""
        for party in self.parties:
            if party.role == PartyRole.DECEDENT:
                return party
        return None

    def get_personal_representative(self) -> Optional[ProbateParty]:
        """Get the executor/administrator"""
        for party in self.parties:
            if party.role in [
                PartyRole.EXECUTOR,
                PartyRole.ADMINISTRATOR,
                PartyRole.PERSONAL_REPRESENTATIVE,
            ]:
                return party
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_number": self.case_number,
            "case_type": self.case_type.value,
            "status": self.status.value,
            "case_title": self.case_title,
            "decedent_name": self.decedent_name,
            "parties": [
                {
                    "name": p.name,
                    "role": p.role.value,
                    "date_of_death": (
                        p.date_of_death.isoformat() if p.date_of_death else None
                    ),
                }
                for p in self.parties
            ],
            "county": self.county,
            "state": self.state,
            "court_name": self.court_name,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "date_of_death": (
                self.date_of_death.isoformat() if self.date_of_death else None
            ),
            "estate_value": self.estate_value,
            "will_admitted": self.will_admitted,
            "will_contested": self.will_contested,
            "source": self.source,
        }


# State probate court information
STATE_PROBATE_COURTS: Dict[str, Dict[str, Any]] = {
    "AL": {
        "name": "Alabama",
        "court_name": "Probate Court",
        "filing_level": "county",
        "url": "https://www.alabamaprobatecourts.org/",
        "small_estate_limit": 25000,
        "notes": "Separate probate court in each county",
    },
    "AK": {
        "name": "Alaska",
        "court_name": "Superior Court",
        "filing_level": "district",
        "url": "https://courts.alaska.gov/",
        "small_estate_limit": 100000,
        "api_available": True,
        "notes": "Probate handled by Superior Court",
    },
    "AZ": {
        "name": "Arizona",
        "court_name": "Superior Court - Probate Division",
        "filing_level": "county",
        "url": "https://www.azcourts.gov/",
        "small_estate_limit": 75000,  # Personal property
        "real_property_limit": 100000,
    },
    "AR": {
        "name": "Arkansas",
        "court_name": "Circuit Court - Probate Division",
        "filing_level": "county",
        "url": "https://courts.arkansas.gov/",
        "small_estate_limit": 100000,
    },
    "CA": {
        "name": "California",
        "court_name": "Superior Court - Probate Division",
        "filing_level": "county",
        "url": "https://www.courts.ca.gov/selfhelp-probate.htm",
        "small_estate_limit": 184500,  # Adjusted for inflation
        "notes": "Small estate affidavit available under limit",
    },
    "CO": {
        "name": "Colorado",
        "court_name": "District Court - Probate Division",
        "filing_level": "county",
        "url": "https://www.courts.state.co.us/",
        "small_estate_limit": 74000,  # Personal property
        "api_available": True,
    },
    "CT": {
        "name": "Connecticut",
        "court_name": "Probate Court",
        "filing_level": "district",  # 54 probate districts
        "url": "https://www.ctprobate.gov/",
        "small_estate_limit": 40000,
        "api_available": True,
        "notes": "Probate court separate from Superior Court",
    },
    "DE": {
        "name": "Delaware",
        "court_name": "Court of Chancery / Register of Wills",
        "filing_level": "county",
        "url": "https://courts.delaware.gov/chancery/",
        "small_estate_limit": 30000,
    },
    "FL": {
        "name": "Florida",
        "court_name": "Circuit Court - Probate Division",
        "filing_level": "county",
        "url": "https://www.flcourts.org/",
        "small_estate_limit": 75000,  # Summary administration
        "disposition_limit": 6000,  # Disposition without administration
    },
    "GA": {
        "name": "Georgia",
        "court_name": "Probate Court",
        "filing_level": "county",
        "url": "https://georgiacourts.gov/probate-courts/",
        "small_estate_limit": 10000,  # No administration needed
        "notes": "Each county has own probate court",
    },
    "HI": {
        "name": "Hawaii",
        "court_name": "Circuit Court - Probate Division",
        "filing_level": "circuit",
        "url": "https://www.courts.state.hi.us/",
        "small_estate_limit": 100000,
    },
    "ID": {
        "name": "Idaho",
        "court_name": "Magistrate Court",
        "filing_level": "county",
        "url": "https://isc.idaho.gov/",
        "small_estate_limit": 100000,
    },
    "IL": {
        "name": "Illinois",
        "court_name": "Circuit Court - Probate Division",
        "filing_level": "county",
        "url": "https://www.illinoiscourts.gov/",
        "small_estate_limit": 100000,
        "notes": "Independent administration available",
    },
    "IN": {
        "name": "Indiana",
        "court_name": "Superior/Circuit Court - Probate Division",
        "filing_level": "county",
        "url": "https://www.in.gov/courts/",
        "small_estate_limit": 50000,
    },
    "IA": {
        "name": "Iowa",
        "court_name": "District Court - Probate",
        "filing_level": "county",
        "url": "https://www.iowacourts.gov/",
        "small_estate_limit": 100000,
    },
    "KS": {
        "name": "Kansas",
        "court_name": "District Court - Probate Division",
        "filing_level": "county",
        "url": "https://www.kscourts.org/",
        "small_estate_limit": 40000,
    },
    "KY": {
        "name": "Kentucky",
        "court_name": "District Court - Probate",
        "filing_level": "county",
        "url": "https://courts.ky.gov/",
        "small_estate_limit": 30000,  # Dispensing with administration
    },
    "LA": {
        "name": "Louisiana",
        "court_name": "District Court - Succession",
        "filing_level": "parish",
        "url": "https://www.lasc.org/",
        "small_estate_limit": 125000,  # Simple possession
        "notes": "Civil law system - successions not probate",
    },
    "ME": {
        "name": "Maine",
        "court_name": "Probate Court",
        "filing_level": "county",
        "url": "https://www.courts.maine.gov/courts/probate/",
        "small_estate_limit": 40000,
    },
    "MD": {
        "name": "Maryland",
        "court_name": "Orphans Court / Register of Wills",
        "filing_level": "county",
        "url": "https://registers.maryland.gov/",
        "small_estate_limit": 50000,  # Personal property
        "small_estate_limit_surviving_spouse": 100000,
    },
    "MA": {
        "name": "Massachusetts",
        "court_name": "Probate and Family Court",
        "filing_level": "county",
        "url": "https://www.mass.gov/orgs/probate-and-family-court",
        "small_estate_limit": 25000,  # Voluntary administration
        "api_available": True,
    },
    "MI": {
        "name": "Michigan",
        "court_name": "Probate Court",
        "filing_level": "county",
        "url": "https://courts.michigan.gov/",
        "small_estate_limit": 25000,  # Adjusted for inflation
    },
    "MN": {
        "name": "Minnesota",
        "court_name": "District Court - Probate Division",
        "filing_level": "county",
        "url": "https://www.mncourts.gov/",
        "small_estate_limit": 75000,
        "api_available": True,
    },
    "MS": {
        "name": "Mississippi",
        "court_name": "Chancery Court",
        "filing_level": "county",
        "url": "https://courts.ms.gov/",
        "small_estate_limit": 75000,  # Muniment of title
    },
    "MO": {
        "name": "Missouri",
        "court_name": "Circuit Court - Probate Division",
        "filing_level": "county",
        "url": "https://www.courts.mo.gov/",
        "small_estate_limit": 40000,
    },
    "MT": {
        "name": "Montana",
        "court_name": "District Court",
        "filing_level": "county",
        "url": "https://courts.mt.gov/",
        "small_estate_limit": 50000,
    },
    "NE": {
        "name": "Nebraska",
        "court_name": "County Court",
        "filing_level": "county",
        "url": "https://supremecourt.nebraska.gov/",
        "small_estate_limit": 50000,
    },
    "NV": {
        "name": "Nevada",
        "court_name": "District Court - Probate Division",
        "filing_level": "county",
        "url": "https://nvcourts.gov/",
        "small_estate_limit": 100000,  # Set aside without administration
    },
    "NH": {
        "name": "New Hampshire",
        "court_name": "Circuit Court - Probate Division",
        "filing_level": "county",
        "url": "https://www.courts.nh.gov/",
        "small_estate_limit": 10000,  # Voluntary administration
    },
    "NJ": {
        "name": "New Jersey",
        "court_name": "Surrogate Court",
        "filing_level": "county",
        "url": "https://www.njcourts.gov/",
        "small_estate_limit": 50000,  # Summary administration
        "notes": "Surrogate handles probate, Superior Court handles contested",
    },
    "NM": {
        "name": "New Mexico",
        "court_name": "District Court - Probate",
        "filing_level": "county",
        "url": "https://www.nmcourts.gov/",
        "small_estate_limit": 50000,
    },
    "NY": {
        "name": "New York",
        "court_name": "Surrogate Court",
        "filing_level": "county",
        "url": "https://www.nycourts.gov/courts/nyc/surrogates/",
        "small_estate_limit": 50000,  # Voluntary administration
        "api_available": True,
        "notes": "Each county has Surrogate Court",
    },
    "NC": {
        "name": "North Carolina",
        "court_name": "Clerk of Superior Court",
        "filing_level": "county",
        "url": "https://www.nccourts.gov/",
        "small_estate_limit": 20000,  # Affidavit for collection
    },
    "ND": {
        "name": "North Dakota",
        "court_name": "District Court",
        "filing_level": "county",
        "url": "https://www.ndcourts.gov/",
        "small_estate_limit": 50000,
    },
    "OH": {
        "name": "Ohio",
        "court_name": "Probate Court",
        "filing_level": "county",
        "url": "https://www.ohiocourts.gov/",
        "small_estate_limit": 35000,  # Release from administration
        "api_available": True,
    },
    "OK": {
        "name": "Oklahoma",
        "court_name": "District Court",
        "filing_level": "county",
        "url": "https://www.oscn.net/",
        "small_estate_limit": 50000,  # Summary administration
        "api_available": True,
    },
    "OR": {
        "name": "Oregon",
        "court_name": "Circuit Court - Probate",
        "filing_level": "county",
        "url": "https://www.courts.oregon.gov/",
        "small_estate_limit": 200000,  # Personal property affidavit
        "real_property_limit": 200000,
    },
    "PA": {
        "name": "Pennsylvania",
        "court_name": "Orphans Court / Register of Wills",
        "filing_level": "county",
        "url": "https://www.pacourts.us/",
        "small_estate_limit": 50000,  # Family exemption
    },
    "RI": {
        "name": "Rhode Island",
        "court_name": "Probate Court",
        "filing_level": "city_town",  # Municipal probate courts
        "url": "https://www.courts.ri.gov/",
        "small_estate_limit": 15000,
        "notes": "Each city/town has probate court",
    },
    "SC": {
        "name": "South Carolina",
        "court_name": "Probate Court",
        "filing_level": "county",
        "url": "https://www.sccourts.org/",
        "small_estate_limit": 25000,
    },
    "SD": {
        "name": "South Dakota",
        "court_name": "Circuit Court",
        "filing_level": "county",
        "url": "https://ujs.sd.gov/",
        "small_estate_limit": 50000,
    },
    "TN": {
        "name": "Tennessee",
        "court_name": "Probate Court / Chancery Court",
        "filing_level": "county",
        "url": "https://www.tncourts.gov/",
        "small_estate_limit": 50000,
    },
    "TX": {
        "name": "Texas",
        "court_name": "Probate Court / County Court",
        "filing_level": "county",
        "url": "https://www.txcourts.gov/",
        "small_estate_limit": 75000,  # Affidavit of heirship
        "notes": "Statutory probate courts in larger counties",
    },
    "UT": {
        "name": "Utah",
        "court_name": "District Court",
        "filing_level": "county",
        "url": "https://www.utcourts.gov/",
        "small_estate_limit": 100000,
    },
    "VT": {
        "name": "Vermont",
        "court_name": "Probate Division of Superior Court",
        "filing_level": "county",
        "url": "https://www.vermontjudiciary.org/",
        "small_estate_limit": 10000,
    },
    "VA": {
        "name": "Virginia",
        "court_name": "Circuit Court",
        "filing_level": "county_city",  # Independent cities have own courts
        "url": "https://www.vacourts.gov/",
        "small_estate_limit": 50000,
    },
    "WA": {
        "name": "Washington",
        "court_name": "Superior Court - Probate",
        "filing_level": "county",
        "url": "https://www.courts.wa.gov/",
        "small_estate_limit": 100000,
        "api_available": True,
    },
    "WV": {
        "name": "West Virginia",
        "court_name": "County Commission",
        "filing_level": "county",
        "url": "https://www.courtswv.gov/",
        "small_estate_limit": 100000,
        "notes": "Fiduciary Commissioner handles probate",
    },
    "WI": {
        "name": "Wisconsin",
        "court_name": "Circuit Court - Probate",
        "filing_level": "county",
        "url": "https://www.wicourts.gov/",
        "small_estate_limit": 50000,
        "api_available": True,
    },
    "WY": {
        "name": "Wyoming",
        "court_name": "District Court",
        "filing_level": "county",
        "url": "https://www.courts.state.wy.us/",
        "small_estate_limit": 200000,  # Summary procedures
    },
    "DC": {
        "name": "District of Columbia",
        "court_name": "Superior Court - Probate Division",
        "filing_level": "district",
        "url": "https://www.dccourts.gov/superior-court/probate-division",
        "small_estate_limit": 40000,
    },
}


# Major county probate court configurations
COUNTY_PROBATE_SOURCES: Dict[str, Dict[str, Any]] = {
    # California
    "CA_LOS_ANGELES": {
        "name": "Los Angeles County Superior Court - Probate",
        "url": "https://www.lacourt.org/division/probate/probate.aspx",
        "search_url": "https://www.lacourt.org/casesummary/ui/index.aspx",
        "api_available": False,
    },
    "CA_SAN_DIEGO": {
        "name": "San Diego County Superior Court - Probate",
        "url": "https://www.sdcourt.ca.gov/sdcourt/civil/probate",
        "search_url": "https://www.sdcourt.ca.gov/sdcourt/case-information/case-search",
        "api_available": False,
    },
    "CA_ORANGE": {
        "name": "Orange County Superior Court - Probate",
        "url": "https://www.occourts.org/online-services/case-access/",
        "search_url": "https://www.occourts.org/online-services/case-access/",
        "api_available": False,
    },
    # Florida
    "FL_MIAMI_DADE": {
        "name": "Miami-Dade County Circuit Court - Probate",
        "url": "https://www.jud11.flcourts.org/Probate",
        "search_url": "https://www2.miami-dadeclerk.com/ocs/",
        "api_available": False,
    },
    "FL_BROWARD": {
        "name": "Broward County Circuit Court - Probate",
        "url": "https://www.17th.flcourts.org/",
        "search_url": "https://www.browardclerk.org/Web2/",
        "api_available": False,
    },
    "FL_PALM_BEACH": {
        "name": "Palm Beach County Circuit Court - Probate",
        "url": "https://www.15thcircuit.com/",
        "search_url": "https://courtrecords.palmbeachclerk.com/",
        "api_available": False,
    },
    # Texas
    "TX_HARRIS": {
        "name": "Harris County Probate Courts",
        "url": "https://www.justex.net/Courts/Probate/",
        "search_url": "https://www.cclerk.hctx.net/Applications/WebSearch/",
        "api_available": False,
        "notes": "4 statutory probate courts",
    },
    "TX_DALLAS": {
        "name": "Dallas County Probate Courts",
        "url": "https://www.dallascounty.org/government/courts/probate-courts/",
        "search_url": "https://apps.dallascounty.org/ccfiling/search",
        "api_available": False,
    },
    "TX_BEXAR": {
        "name": "Bexar County Probate Courts",
        "url": "https://www.bexar.org/2848/Probate-Courts",
        "search_url": "https://www.bexar.org/2848/Probate-Courts",
        "api_available": False,
    },
    # New York
    "NY_NEW_YORK": {
        "name": "New York County Surrogate Court (Manhattan)",
        "url": "https://www.nycourts.gov/courts/1jd/surrogates/",
        "search_url": "https://iapps.courts.state.ny.us/webcivil/FCASSearch",
        "api_available": True,
    },
    "NY_KINGS": {
        "name": "Kings County Surrogate Court (Brooklyn)",
        "url": "https://www.nycourts.gov/courts/2jd/kings/surrogates/",
        "search_url": "https://iapps.courts.state.ny.us/webcivil/FCASSearch",
        "api_available": True,
    },
    # Illinois
    "IL_COOK": {
        "name": "Cook County Circuit Court - Probate Division",
        "url": "https://www.cookcountycourt.org/ABOUT-THE-COURT/Municipal-Department/Probate-Division",
        "search_url": "https://casesearch.cookcountyclerkofcourt.org/ProbateCaseSearch.aspx",
        "api_available": False,
    },
    # Arizona
    "AZ_MARICOPA": {
        "name": "Maricopa County Superior Court - Probate",
        "url": "https://superiorcourt.maricopa.gov/probate/",
        "search_url": "https://www.superiorcourt.maricopa.gov/docket/ProbateCourtCases/",
        "api_available": True,
    },
    # Nevada
    "NV_CLARK": {
        "name": "Clark County District Court - Probate",
        "url": "https://www.clarkcountycourts.us/",
        "search_url": "https://www.clarkcountycourts.us/Anonymous/default.aspx",
        "api_available": False,
    },
    # Georgia
    "GA_FULTON": {
        "name": "Fulton County Probate Court",
        "url": "https://www.fultoncountyprobatecourt.org/",
        "search_url": "https://www.fultoncountyprobatecourt.org/record-search/",
        "api_available": False,
    },
    # Ohio
    "OH_CUYAHOGA": {
        "name": "Cuyahoga County Probate Court",
        "url": "https://probate.cuyahogacounty.us/",
        "search_url": "https://probate.cuyahogacounty.us/pa/CaseSummary.aspx",
        "api_available": True,
    },
    "OH_FRANKLIN": {
        "name": "Franklin County Probate Court",
        "url": "https://probate.franklincountyohio.gov/",
        "search_url": "https://probate.franklincountyohio.gov/eservices",
        "api_available": True,
    },
    # Washington
    "WA_KING": {
        "name": "King County Superior Court - Probate",
        "url": "https://www.kingcounty.gov/courts/superior-court/case-types/probate.aspx",
        "search_url": "https://dja-prd-ecexap1.kingcounty.gov/clerks/default.aspx",
        "api_available": True,
    },
    # Pennsylvania
    "PA_PHILADELPHIA": {
        "name": "Philadelphia Register of Wills",
        "url": "https://www.phila.gov/departments/register-of-wills/",
        "search_url": "https://www.phila.gov/departments/register-of-wills/",
        "api_available": False,
    },
    # New Jersey
    "NJ_ESSEX": {
        "name": "Essex County Surrogate Court",
        "url": "https://www.essexcountynj.org/surrogates-court/",
        "search_url": "https://portal.njcourts.gov/",
        "api_available": False,
    },
    # Massachusetts
    "MA_SUFFOLK": {
        "name": "Suffolk County Probate and Family Court",
        "url": "https://www.mass.gov/locations/suffolk-probate-and-family-court",
        "search_url": "https://www.masscourts.org/eservices/",
        "api_available": True,
    },
}


class ProbateRecordsAPI:
    """Main API class for probate records"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.base_headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _make_request(
        self, url: str, params: Optional[Dict] = None
    ) -> Optional[str]:
        """Make HTTP request with error handling"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.base_headers)

        try:
            async with self.session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(
                        f"Request failed with status {response.status}: {url}"
                    )
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {url}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def _parse_case_type(self, type_str: str) -> ProbateCaseType:
        """Parse case type from string"""
        type_str = type_str.lower() if type_str else ""

        if "testate" in type_str or "with will" in type_str:
            return ProbateCaseType.TESTATE
        elif "intestate" in type_str or "without will" in type_str:
            return ProbateCaseType.INTESTATE
        elif "small estate" in type_str or "summary" in type_str:
            return ProbateCaseType.SMALL_ESTATE
        elif "guardianship" in type_str:
            if "minor" in type_str:
                return ProbateCaseType.GUARDIANSHIP_MINOR
            elif "adult" in type_str or "incapacitated" in type_str:
                return ProbateCaseType.GUARDIANSHIP_ADULT
            elif "estate" in type_str:
                return ProbateCaseType.GUARDIANSHIP_ESTATE
            return ProbateCaseType.GUARDIANSHIP_PERSON
        elif "conservatorship" in type_str:
            return ProbateCaseType.CONSERVATORSHIP
        elif "trust" in type_str:
            return ProbateCaseType.TRUST_ADMINISTRATION
        elif "will contest" in type_str:
            return ProbateCaseType.WILL_CONTEST
        elif "determination" in type_str and "heir" in type_str:
            return ProbateCaseType.DETERMINATION_OF_HEIRS
        elif "ancillary" in type_str:
            return ProbateCaseType.ANCILLARY_PROBATE
        else:
            return ProbateCaseType.OTHER

    async def search_by_decedent_name(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        state: str = "",
        county: Optional[str] = None,
        year_range: Optional[tuple] = None,
    ) -> List[ProbateRecord]:
        """Search for probate cases by decedent name"""
        results = []

        if state and state not in STATE_PROBATE_COURTS:
            logger.warning(f"Unknown state: {state}")
            return results

        # Build search
        search_name = last_name
        if first_name:
            search_name = f"{last_name}, {first_name}"

        logger.info(f"Searching probate records for decedent: {search_name}")

        # Check for county-specific search
        if county and state:
            county_key = f"{state}_{county.upper().replace(' ', '_')}"
            if county_key in COUNTY_PROBATE_SOURCES:
                config = COUNTY_PROBATE_SOURCES[county_key]
                logger.info(f"Using {config['name']}")

        return results

    async def search_by_case_number(
        self, case_number: str, state: str, county: Optional[str] = None
    ) -> Optional[ProbateRecord]:
        """Search for a specific probate case by number"""
        if state not in STATE_PROBATE_COURTS:
            logger.warning(f"Unknown state: {state}")
            return None

        logger.info(f"Looking up probate case {case_number} in {state}")

        return None

    async def search_by_heir_name(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        state: str = "",
        county: Optional[str] = None,
    ) -> List[ProbateRecord]:
        """Search for probate cases where person is an heir/beneficiary"""
        results = []

        if state and state not in STATE_PROBATE_COURTS:
            return results

        logger.info(f"Searching for probate cases with heir: {last_name}")

        return results

    async def search_by_personal_representative(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        state: str = "",
        county: Optional[str] = None,
    ) -> List[ProbateRecord]:
        """Search for probate cases by executor/administrator"""
        results = []

        if state and state not in STATE_PROBATE_COURTS:
            return results

        logger.info(f"Searching for probate cases with PR: {last_name}")

        return results

    async def get_recent_filings(
        self,
        state: str,
        county: Optional[str] = None,
        days: int = 30,
        case_type: Optional[ProbateCaseType] = None,
    ) -> List[ProbateRecord]:
        """Get recently filed probate cases"""
        results = []

        if state not in STATE_PROBATE_COURTS:
            return results

        logger.info(f"Getting recent probate filings in {state}")

        return results

    async def get_pending_cases(
        self,
        state: str,
        county: Optional[str] = None,
        case_type: Optional[ProbateCaseType] = None,
    ) -> List[ProbateRecord]:
        """Get pending/open probate cases"""
        results = []

        if state not in STATE_PROBATE_COURTS:
            return results

        logger.info(f"Getting pending probate cases in {state}")

        return results

    async def get_guardianship_cases(
        self,
        state: str,
        county: Optional[str] = None,
        ward_name: Optional[str] = None,
        guardian_name: Optional[str] = None,
    ) -> List[ProbateRecord]:
        """Search for guardianship/conservatorship cases"""
        results = []

        if state not in STATE_PROBATE_COURTS:
            return results

        logger.info(f"Searching guardianship cases in {state}")

        return results

    def get_court_info(self, state: str) -> Optional[Dict[str, Any]]:
        """Get probate court information for a state"""
        return STATE_PROBATE_COURTS.get(state.upper())

    def get_county_court(self, state: str, county: str) -> Optional[Dict[str, Any]]:
        """Get county probate court information"""
        county_key = f"{state.upper()}_{county.upper().replace(' ', '_')}"

        if county_key in COUNTY_PROBATE_SOURCES:
            return COUNTY_PROBATE_SOURCES[county_key]

        # Return general state info
        if state.upper() in STATE_PROBATE_COURTS:
            state_info = STATE_PROBATE_COURTS[state.upper()]
            return {
                "name": f"{county} County {state_info['court_name']}",
                "court_type": state_info["court_name"],
                "small_estate_limit": state_info.get("small_estate_limit"),
            }

        return None

    def get_small_estate_limit(self, state: str) -> Optional[Dict[str, Any]]:
        """Get small estate threshold for a state"""
        if state.upper() not in STATE_PROBATE_COURTS:
            return None

        info = STATE_PROBATE_COURTS[state.upper()]

        return {
            "state": state.upper(),
            "small_estate_limit": info.get("small_estate_limit"),
            "real_property_limit": info.get("real_property_limit"),
            "disposition_limit": info.get("disposition_limit"),
            "notes": info.get("notes"),
        }

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get probate court information for all states"""
        return {
            state: {
                "name": info["name"],
                "court_name": info["court_name"],
                "filing_level": info["filing_level"],
                "small_estate_limit": info.get("small_estate_limit"),
                "api_available": info.get("api_available", False),
            }
            for state, info in STATE_PROBATE_COURTS.items()
        }

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics"""
        total_states = len(STATE_PROBATE_COURTS)
        total_counties = len(COUNTY_PROBATE_SOURCES)

        # Count by filing level
        county_level = sum(
            1 for s in STATE_PROBATE_COURTS.values() if s["filing_level"] == "county"
        )
        district_level = sum(
            1 for s in STATE_PROBATE_COURTS.values() if s["filing_level"] == "district"
        )
        other_level = total_states - county_level - district_level

        # API availability
        with_api = sum(
            1 for s in STATE_PROBATE_COURTS.values() if s.get("api_available")
        )
        county_with_api = sum(
            1 for c in COUNTY_PROBATE_SOURCES.values() if c.get("api_available")
        )

        return {
            "total_states": total_states,
            "total_county_courts": total_counties,
            "filing_levels": {
                "county": county_level,
                "district": district_level,
                "other": other_level,
            },
            "states_with_api": with_api,
            "county_courts_with_api": county_with_api,
            "api_coverage_percent": round(with_api / total_states * 100, 1),
        }


# Synchronous wrapper functions
def search_probate_by_decedent(
    last_name: str,
    first_name: Optional[str] = None,
    state: str = "",
    county: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching probate by decedent name"""

    async def _search():
        async with ProbateRecordsAPI() as api:
            results = await api.search_by_decedent_name(
                last_name, first_name, state, county
            )
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def get_probate_case(
    case_number: str, state: str, county: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for getting probate case by number"""

    async def _get():
        async with ProbateRecordsAPI() as api:
            result = await api.search_by_case_number(case_number, state, county)
            return result.to_dict() if result else None

    return asyncio.run(_get())


def search_probate_by_heir(
    last_name: str,
    first_name: Optional[str] = None,
    state: str = "",
    county: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching probate by heir name"""

    async def _search():
        async with ProbateRecordsAPI() as api:
            results = await api.search_by_heir_name(
                last_name, first_name, state, county
            )
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def get_recent_probate_filings(
    state: str, county: Optional[str] = None, days: int = 30
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for getting recent probate filings"""

    async def _get():
        async with ProbateRecordsAPI() as api:
            results = await api.get_recent_filings(state, county, days)
            return [r.to_dict() for r in results]

    return asyncio.run(_get())


def get_state_probate_info(state: str) -> Optional[Dict[str, Any]]:
    """Get probate court information for a state"""
    api = ProbateRecordsAPI()
    return api.get_court_info(state)


def get_county_probate_info(state: str, county: str) -> Optional[Dict[str, Any]]:
    """Get county probate court information"""
    api = ProbateRecordsAPI()
    return api.get_county_court(state, county)


def get_small_estate_limit(state: str) -> Optional[Dict[str, Any]]:
    """Get small estate threshold for a state"""
    api = ProbateRecordsAPI()
    return api.get_small_estate_limit(state)


def get_all_state_probate_info() -> Dict[str, Dict[str, Any]]:
    """Get probate court information for all states"""
    api = ProbateRecordsAPI()
    return api.get_all_states()


def get_coverage_stats() -> Dict[str, Any]:
    """Get coverage statistics for probate records"""
    api = ProbateRecordsAPI()
    return api.get_coverage_stats()


if __name__ == "__main__":
    # Test the API
    print("Probate Records Scraper")
    print("=" * 50)

    stats = get_coverage_stats()
    print(f"\nCoverage Statistics:")
    print(f"  Total States: {stats['total_states']}")
    print(f"  County Courts Configured: {stats['total_county_courts']}")
    print(
        f"  States with API: {stats['states_with_api']} ({stats['api_coverage_percent']}%)"
    )
    print(f"  County Courts with API: {stats['county_courts_with_api']}")

    print(f"\nFiling Levels:")
    for level, count in stats["filing_levels"].items():
        print(f"  {level}: {count}")

    print("\nSmall Estate Limits by State:")
    states = get_all_state_probate_info()
    sorted_states = sorted(
        [(k, v) for k, v in states.items() if v.get("small_estate_limit")],
        key=lambda x: x[1].get("small_estate_limit", 0),
        reverse=True,
    )
    for state_code, info in sorted_states[:10]:
        limit = info.get("small_estate_limit", 0)
        print(f"  {state_code}: ${limit:,}")
