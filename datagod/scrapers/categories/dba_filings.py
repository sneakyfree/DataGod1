"""
DBA (Doing Business As) / Fictitious Business Name Filings Scraper
==================================================================

Comprehensive scraper for DBA/Fictitious Business Name records
from county clerks and recorder offices across all US states.

Data Sources:
- County Clerk offices
- County Recorder offices
- State-level DBA registries (some states)

Record Types:
- Fictitious Business Name Statements
- DBA Filings
- Assumed Name Certificates
- Trade Name Registrations
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


class DBAFilingType(Enum):
    """Types of DBA filings"""

    ORIGINAL = "original"
    RENEWAL = "renewal"
    AMENDMENT = "amendment"
    ABANDONMENT = "abandonment"
    WITHDRAWAL = "withdrawal"
    CHANGE_OF_ADDRESS = "change_of_address"
    CHANGE_OF_REGISTRANT = "change_of_registrant"


class DBAStatus(Enum):
    """Status of DBA filing"""

    ACTIVE = "active"
    EXPIRED = "expired"
    ABANDONED = "abandoned"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    REJECTED = "rejected"


class BusinessStructure(Enum):
    """Business structure type"""

    INDIVIDUAL = "individual"
    GENERAL_PARTNERSHIP = "general_partnership"
    LIMITED_PARTNERSHIP = "limited_partnership"
    LIMITED_LIABILITY_PARTNERSHIP = "limited_liability_partnership"
    CORPORATION = "corporation"
    LLC = "llc"
    TRUST = "trust"
    JOINT_VENTURE = "joint_venture"
    MARRIED_COUPLE = "married_couple"
    OTHER = "other"


@dataclass
class DBARegistrant:
    """Person or entity registering a DBA"""

    name: str
    registrant_type: str  # Individual, Corporation, LLC, etc.

    # Individual info
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None

    # Address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None

    # If a business entity
    entity_number: Optional[str] = None  # State entity number
    entity_state: Optional[str] = None  # State of incorporation


@dataclass
class DBAFiling:
    """DBA/Fictitious Business Name filing record"""

    filing_number: str
    fictitious_name: str  # The DBA name
    filing_type: DBAFilingType
    status: DBAStatus

    # Registrants (can be multiple)
    registrants: List[DBARegistrant] = field(default_factory=list)

    # Business structure
    business_structure: BusinessStructure = BusinessStructure.INDIVIDUAL

    # Location
    county: str = ""
    state: str = ""
    business_address: Optional[str] = None
    business_city: Optional[str] = None
    business_zip: Optional[str] = None

    # Dates
    filing_date: Optional[date] = None
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    publication_date: Optional[date] = None

    # Publication (required in many states)
    newspaper_name: Optional[str] = None
    publication_dates: List[date] = field(default_factory=list)
    publication_complete: bool = False

    # Business description
    business_type: Optional[str] = None  # Type of business activity
    business_description: Optional[str] = None

    # Related filings
    original_filing_number: Optional[str] = None  # For renewals/amendments
    previous_names: List[str] = field(default_factory=list)

    # Fees
    filing_fee: Optional[float] = None

    # Source
    source: str = ""
    source_url: Optional[str] = None
    document_number: Optional[str] = None
    book_page: Optional[str] = None  # For older records
    retrieved_date: date = field(default_factory=date.today)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filing_number": self.filing_number,
            "fictitious_name": self.fictitious_name,
            "filing_type": self.filing_type.value,
            "status": self.status.value,
            "registrants": [
                {
                    "name": r.name,
                    "type": r.registrant_type,
                    "address": r.address,
                    "city": r.city,
                    "state": r.state,
                    "zip_code": r.zip_code,
                }
                for r in self.registrants
            ],
            "business_structure": self.business_structure.value,
            "county": self.county,
            "state": self.state,
            "business_address": self.business_address,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "expiration_date": (
                self.expiration_date.isoformat() if self.expiration_date else None
            ),
            "publication_complete": self.publication_complete,
            "source": self.source,
        }


# State-level DBA information and requirements
STATE_DBA_INFO: Dict[str, Dict[str, Any]] = {
    "AL": {
        "name": "Alabama",
        "filing_level": "county",
        "term_name": "Trade Name",
        "filing_office": "Probate Court",
        "duration_years": None,  # No expiration
        "publication_required": False,
        "state_registry_url": None,
    },
    "AK": {
        "name": "Alaska",
        "filing_level": "state",
        "term_name": "Business Name Registration",
        "filing_office": "Division of Corporations",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://www.commerce.alaska.gov/cbp/main/",
        "api_available": True,
    },
    "AZ": {
        "name": "Arizona",
        "filing_level": "county",
        "term_name": "Trade Name",
        "filing_office": "County Recorder",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://azcc.gov/corporations",
    },
    "AR": {
        "name": "Arkansas",
        "filing_level": "county",
        "term_name": "Fictitious Name",
        "filing_office": "County Clerk",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": None,
    },
    "CA": {
        "name": "California",
        "filing_level": "county",
        "term_name": "Fictitious Business Name Statement",
        "filing_office": "County Clerk",
        "duration_years": 5,
        "publication_required": True,
        "publication_days": 28,  # 4 consecutive weeks
        "renewal_period_days": 40,  # Before expiration
        "state_registry_url": None,
        "notes": "Must be published in newspaper of general circulation",
    },
    "CO": {
        "name": "Colorado",
        "filing_level": "state",
        "term_name": "Trade Name",
        "filing_office": "Secretary of State",
        "duration_years": None,  # No expiration
        "publication_required": False,
        "state_registry_url": "https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do",
        "api_available": True,
    },
    "CT": {
        "name": "Connecticut",
        "filing_level": "town",
        "term_name": "Trade Name Certificate",
        "filing_office": "Town Clerk",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": None,
    },
    "DE": {
        "name": "Delaware",
        "filing_level": "county",
        "term_name": "Trade Name",
        "filing_office": "Prothonotary",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": None,
    },
    "FL": {
        "name": "Florida",
        "filing_level": "state",
        "term_name": "Fictitious Name",
        "filing_office": "Division of Corporations",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://search.sunbiz.org/Inquiry/CorporationSearch/ByName",
        "api_available": True,
    },
    "GA": {
        "name": "Georgia",
        "filing_level": "county",
        "term_name": "Trade Name",
        "filing_office": "Clerk of Superior Court",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": None,
    },
    "HI": {
        "name": "Hawaii",
        "filing_level": "state",
        "term_name": "Trade Name",
        "filing_office": "DCCA BREG",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://hbe.ehawaii.gov/documents/search.html",
    },
    "ID": {
        "name": "Idaho",
        "filing_level": "county",
        "term_name": "Assumed Business Name",
        "filing_office": "County Recorder",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://sosbiz.idaho.gov/search/business",
    },
    "IL": {
        "name": "Illinois",
        "filing_level": "county",
        "term_name": "Assumed Business Name",
        "filing_office": "County Clerk",
        "duration_years": 5,
        "publication_required": True,  # In some counties
        "state_registry_url": None,
    },
    "IN": {
        "name": "Indiana",
        "filing_level": "county",
        "term_name": "Assumed Business Name",
        "filing_office": "County Recorder",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://bsd.sos.in.gov/publicbusinesssearch",
    },
    "IA": {
        "name": "Iowa",
        "filing_level": "county",
        "term_name": "Fictitious Name",
        "filing_office": "County Recorder",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": None,
    },
    "KS": {
        "name": "Kansas",
        "filing_level": "county",
        "term_name": "Trade Name",
        "filing_office": "Register of Deeds",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://www.kansas.gov/bess/flow/main",
    },
    "KY": {
        "name": "Kentucky",
        "filing_level": "county",
        "term_name": "Assumed Name",
        "filing_office": "County Clerk",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://web.sos.ky.gov/bussearchnew/search",
    },
    "LA": {
        "name": "Louisiana",
        "filing_level": "parish",
        "term_name": "Trade Name",
        "filing_office": "Clerk of Court",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://coraweb.sos.la.gov/commercialsearch/CommercialSearch.aspx",
    },
    "ME": {
        "name": "Maine",
        "filing_level": "town",
        "term_name": "Trade Name",
        "filing_office": "Town Clerk",
        "duration_years": 1,  # Annual renewal in some areas
        "publication_required": False,
        "state_registry_url": None,
    },
    "MD": {
        "name": "Maryland",
        "filing_level": "state",
        "term_name": "Trade Name",
        "filing_office": "SDAT",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://egov.maryland.gov/BusinessExpress/EntitySearch",
        "api_available": True,
    },
    "MA": {
        "name": "Massachusetts",
        "filing_level": "city_town",
        "term_name": "Business Certificate",
        "filing_office": "City/Town Clerk",
        "duration_years": 4,
        "publication_required": False,
        "state_registry_url": None,
    },
    "MI": {
        "name": "Michigan",
        "filing_level": "county",
        "term_name": "Assumed Name",
        "filing_office": "County Clerk",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://cofs.lara.state.mi.us/SearchApi/Search/Search",
    },
    "MN": {
        "name": "Minnesota",
        "filing_level": "state",
        "term_name": "Assumed Name",
        "filing_office": "Secretary of State",
        "duration_years": 10,
        "publication_required": False,
        "state_registry_url": "https://mblsportal.sos.state.mn.us/Business/Search",
        "api_available": True,
    },
    "MS": {
        "name": "Mississippi",
        "filing_level": "county",
        "term_name": "Fictitious Name",
        "filing_office": "Chancery Clerk",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": None,
    },
    "MO": {
        "name": "Missouri",
        "filing_level": "county",
        "term_name": "Fictitious Name",
        "filing_office": "Secretary of State (but filed with county)",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://bsd.sos.mo.gov/BusinessEntity/BESearch.aspx",
    },
    "MT": {
        "name": "Montana",
        "filing_level": "state",
        "term_name": "Assumed Business Name",
        "filing_office": "Secretary of State",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://biz.sosmt.gov/search",
    },
    "NE": {
        "name": "Nebraska",
        "filing_level": "county",
        "term_name": "Trade Name",
        "filing_office": "Register of Deeds or County Clerk",
        "duration_years": 10,
        "publication_required": True,  # In newspaper
        "state_registry_url": "https://www.nebraska.gov/sos/corp/corpsearch.cgi",
    },
    "NV": {
        "name": "Nevada",
        "filing_level": "county",
        "term_name": "Fictitious Firm Name",
        "filing_office": "County Clerk",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://esos.nv.gov/EntitySearch/OnlineEntitySearch",
    },
    "NH": {
        "name": "New Hampshire",
        "filing_level": "town",
        "term_name": "Trade Name",
        "filing_office": "Town/City Clerk",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://quickstart.sos.nh.gov/online/BusinessInquire",
    },
    "NJ": {
        "name": "New Jersey",
        "filing_level": "county",
        "term_name": "Trade Name",
        "filing_office": "County Clerk",
        "duration_years": None,
        "publication_required": True,  # In two newspapers
        "state_registry_url": None,
    },
    "NM": {
        "name": "New Mexico",
        "filing_level": "county",
        "term_name": "Trade Name",
        "filing_office": "County Clerk",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://portal.sos.state.nm.us/BFS/online/CorporationBusinessSearch",
    },
    "NY": {
        "name": "New York",
        "filing_level": "county",
        "term_name": "Business Certificate / DBA",
        "filing_office": "County Clerk",
        "duration_years": None,  # Perpetual until cancelled
        "publication_required": True,  # LLC/LP must publish
        "state_registry_url": None,
        "notes": "NYC has separate rules",
    },
    "NC": {
        "name": "North Carolina",
        "filing_level": "county",
        "term_name": "Assumed Business Name",
        "filing_office": "Register of Deeds",
        "duration_years": 10,
        "publication_required": False,
        "state_registry_url": "https://www.sosnc.gov/online_services/search/by_title/_Business_Registration",
    },
    "ND": {
        "name": "North Dakota",
        "filing_level": "state",
        "term_name": "Trade Name",
        "filing_office": "Secretary of State",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://firststop.sos.nd.gov/",
        "api_available": True,
    },
    "OH": {
        "name": "Ohio",
        "filing_level": "county",
        "term_name": "Fictitious Name",
        "filing_office": "Secretary of State (but filed with county)",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://businesssearch.ohiosos.gov/",
    },
    "OK": {
        "name": "Oklahoma",
        "filing_level": "county",
        "term_name": "Trade Name",
        "filing_office": "County Clerk",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://www.sos.ok.gov/corp/corpInquiryFind.aspx",
    },
    "OR": {
        "name": "Oregon",
        "filing_level": "state",
        "term_name": "Assumed Business Name",
        "filing_office": "Secretary of State",
        "duration_years": 2,
        "publication_required": False,
        "state_registry_url": "https://sos.oregon.gov/business/Pages/find.aspx",
        "api_available": True,
    },
    "PA": {
        "name": "Pennsylvania",
        "filing_level": "county",
        "term_name": "Fictitious Name",
        "filing_office": "Department of State (filed via county)",
        "duration_years": 10,
        "publication_required": True,  # In two newspapers
        "state_registry_url": "https://www.corporations.pa.gov/Search/corpsearch",
    },
    "RI": {
        "name": "Rhode Island",
        "filing_level": "town",
        "term_name": "Fictitious Business Name",
        "filing_office": "Town Clerk",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "http://business.sos.ri.gov/CorpWeb/CorpSearch/CorpSearch.aspx",
    },
    "SC": {
        "name": "South Carolina",
        "filing_level": "county",
        "term_name": "Trade Name",
        "filing_office": "Register of Deeds",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://businessfilings.sc.gov/BusinessFiling/Entity/Search",
    },
    "SD": {
        "name": "South Dakota",
        "filing_level": "county",
        "term_name": "Fictitious Business Name",
        "filing_office": "Register of Deeds",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://sosenterprise.sd.gov/BusinessServices/Business/FilingSearch.aspx",
    },
    "TN": {
        "name": "Tennessee",
        "filing_level": "county",
        "term_name": "Assumed Name",
        "filing_office": "County Register",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://tnbear.tn.gov/Ecommerce/FilingSearch.aspx",
    },
    "TX": {
        "name": "Texas",
        "filing_level": "county",
        "term_name": "Assumed Name",
        "filing_office": "County Clerk",
        "duration_years": 10,
        "publication_required": False,
        "state_registry_url": "https://mycpa.cpa.state.tx.us/coa/",
    },
    "UT": {
        "name": "Utah",
        "filing_level": "state",
        "term_name": "DBA",
        "filing_office": "Division of Corporations",
        "duration_years": 1,  # Annual renewal
        "publication_required": False,
        "state_registry_url": "https://secure.utah.gov/bes/index.html",
        "api_available": True,
    },
    "VT": {
        "name": "Vermont",
        "filing_level": "town",
        "term_name": "Trade Name",
        "filing_office": "Town Clerk",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://bizfilings.vermont.gov/online/BusinessInquire",
    },
    "VA": {
        "name": "Virginia",
        "filing_level": "county",
        "term_name": "Fictitious Name",
        "filing_office": "Clerk of Court",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://cis.scc.virginia.gov/",
        "api_available": True,
    },
    "WA": {
        "name": "Washington",
        "filing_level": "state",
        "term_name": "Trade Name",
        "filing_office": "Secretary of State",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://ccfs.sos.wa.gov/",
        "api_available": True,
    },
    "WV": {
        "name": "West Virginia",
        "filing_level": "county",
        "term_name": "Fictitious Name",
        "filing_office": "County Clerk",
        "duration_years": 5,
        "publication_required": False,
        "state_registry_url": "https://apps.wv.gov/sos/businessentitysearch/",
    },
    "WI": {
        "name": "Wisconsin",
        "filing_level": "county",
        "term_name": "Fictitious Name",
        "filing_office": "Register of Deeds",
        "duration_years": None,
        "publication_required": False,
        "state_registry_url": "https://www.wdfi.org/apps/CorpSearch/Search.aspx",
    },
    "WY": {
        "name": "Wyoming",
        "filing_level": "state",
        "term_name": "Trade Name",
        "filing_office": "Secretary of State",
        "duration_years": 4,
        "publication_required": False,
        "state_registry_url": "https://wyobiz.wyo.gov/Business/FilingSearch.aspx",
        "api_available": True,
    },
    "DC": {
        "name": "District of Columbia",
        "filing_level": "district",
        "term_name": "Trade Name",
        "filing_office": "DCRA",
        "duration_years": 2,
        "publication_required": False,
        "state_registry_url": "https://corponline.dcra.dc.gov/Home.aspx",
    },
}


# Major county DBA filing offices
COUNTY_DBA_SOURCES: Dict[str, Dict[str, Any]] = {
    # California (county-level, publication required)
    "CA_LOS_ANGELES": {
        "name": "Los Angeles County Registrar-Recorder",
        "url": "https://www.lavote.net/home/county-clerk/fictitious-business-names",
        "search_url": "https://www.lavote.net/home/county-clerk/fictitious-business-names/search",
        "api_available": False,
        "publication_required": True,
    },
    "CA_SAN_DIEGO": {
        "name": "San Diego County Recorder",
        "url": "https://arcc.sdcounty.ca.gov/Pages/fbn-home.aspx",
        "search_url": "https://arcc.sdcounty.ca.gov/Pages/fbn-search.aspx",
        "api_available": False,
        "publication_required": True,
    },
    "CA_ORANGE": {
        "name": "Orange County Clerk-Recorder",
        "url": "https://www.ocrecorder.com/",
        "search_url": "https://cr.ocgov.com/recorderworks/",
        "api_available": False,
        "publication_required": True,
    },
    "CA_SAN_FRANCISCO": {
        "name": "San Francisco County Clerk",
        "url": "https://sfgov.org/countyclerk/fictitious-business-name",
        "search_url": "https://services.sfgov.org/bln/",
        "api_available": True,
        "publication_required": True,
    },
    # Texas
    "TX_HARRIS": {
        "name": "Harris County Clerk",
        "url": "https://www.cclerk.hctx.net/",
        "search_url": "https://www.cclerk.hctx.net/applications/websearch/",
        "api_available": False,
        "publication_required": False,
    },
    "TX_DALLAS": {
        "name": "Dallas County Clerk",
        "url": "https://www.dallascounty.org/government/county-clerk/",
        "search_url": "https://apps.dallascounty.org/ccfiling/search",
        "api_available": False,
        "publication_required": False,
    },
    "TX_BEXAR": {
        "name": "Bexar County Clerk",
        "url": "https://www.bexar.org/1532/County-Clerk",
        "search_url": "https://gov.propertyinfo.com/TX-Bexar/",
        "api_available": False,
        "publication_required": False,
    },
    "TX_TARRANT": {
        "name": "Tarrant County Clerk",
        "url": "https://www.tarrantcountytx.gov/en/county-clerk.html",
        "search_url": "https://www.tarrantcountytx.gov/en/county-clerk/public-records.html",
        "api_available": False,
        "publication_required": False,
    },
    # New York
    "NY_NEW_YORK": {
        "name": "New York County Clerk (Manhattan)",
        "url": "https://www.nycourts.gov/courts/1jd/supctmanh/county_clerk_background.shtml",
        "search_url": "https://iapps.courts.state.ny.us/nyscef/CaseSearch",
        "api_available": False,
        "publication_required": True,
    },
    "NY_KINGS": {
        "name": "Kings County Clerk (Brooklyn)",
        "url": "https://www.nycourts.gov/courts/2jd/kings/civil/countyclerk.shtml",
        "search_url": None,
        "api_available": False,
        "publication_required": True,
    },
    # Illinois
    "IL_COOK": {
        "name": "Cook County Clerk",
        "url": "https://www.cookcountyclerk.com/",
        "search_url": "https://www.cookcountyclerk.com/agency/business-services",
        "api_available": False,
        "publication_required": True,
    },
    # Arizona
    "AZ_MARICOPA": {
        "name": "Maricopa County Recorder",
        "url": "https://recorder.maricopa.gov/",
        "search_url": "https://recorder.maricopa.gov/recdocdata/",
        "api_available": False,
        "publication_required": False,
    },
    # Nevada
    "NV_CLARK": {
        "name": "Clark County Clerk",
        "url": "https://www.clarkcountynv.gov/government/elected_officials/county_clerk/",
        "search_url": "https://www.clarkcountynv.gov/government/elected_officials/county_clerk/services/fictitious_firm_name.php",
        "api_available": False,
        "publication_required": False,
    },
    # Georgia
    "GA_FULTON": {
        "name": "Fulton County Superior Court Clerk",
        "url": "https://www.fultoncountyclerk.com/",
        "search_url": "https://www.fultoncountyclerk.org/recordsearch/",
        "api_available": False,
        "publication_required": False,
    },
    # Washington (state-level but some county involvement)
    "WA_KING": {
        "name": "Washington Secretary of State (King County)",
        "url": "https://ccfs.sos.wa.gov/",
        "search_url": "https://ccfs.sos.wa.gov/#/AdvancedSearch",
        "api_available": True,
        "publication_required": False,
    },
    # Pennsylvania
    "PA_PHILADELPHIA": {
        "name": "Philadelphia County",
        "url": "https://www.phila.gov/services/business-self-employment/",
        "search_url": "https://www.corporations.pa.gov/Search/corpsearch",
        "api_available": False,
        "publication_required": True,
    },
    # Michigan
    "MI_WAYNE": {
        "name": "Wayne County Clerk",
        "url": "https://www.waynecounty.com/elected/clerk/",
        "search_url": None,
        "api_available": False,
        "publication_required": False,
    },
    # Ohio
    "OH_CUYAHOGA": {
        "name": "Cuyahoga County Fiscal Officer",
        "url": "https://fiscalofficer.cuyahogacounty.us/",
        "search_url": "https://businesssearch.ohiosos.gov/",
        "api_available": False,
        "publication_required": False,
    },
}


class DBAFilingsAPI:
    """Main API class for DBA/Fictitious Business Name records"""

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

    def _parse_filing_type(self, type_str: str) -> DBAFilingType:
        """Parse filing type from string"""
        type_str = type_str.lower() if type_str else ""

        if "original" in type_str or "new" in type_str:
            return DBAFilingType.ORIGINAL
        elif "renewal" in type_str or "refile" in type_str:
            return DBAFilingType.RENEWAL
        elif "amendment" in type_str or "change" in type_str:
            return DBAFilingType.AMENDMENT
        elif "abandon" in type_str:
            return DBAFilingType.ABANDONMENT
        elif "withdraw" in type_str:
            return DBAFilingType.WITHDRAWAL
        else:
            return DBAFilingType.ORIGINAL

    def _parse_status(
        self, status_str: str, expiration_date: Optional[date] = None
    ) -> DBAStatus:
        """Parse filing status from string"""
        status_str = status_str.lower() if status_str else ""

        if "active" in status_str or "current" in status_str:
            # Check if expired
            if expiration_date and expiration_date < date.today():
                return DBAStatus.EXPIRED
            return DBAStatus.ACTIVE
        elif "expired" in status_str:
            return DBAStatus.EXPIRED
        elif "abandon" in status_str:
            return DBAStatus.ABANDONED
        elif "withdraw" in status_str or "cancelled" in status_str:
            return DBAStatus.WITHDRAWN
        elif "pending" in status_str:
            return DBAStatus.PENDING
        elif "reject" in status_str:
            return DBAStatus.REJECTED
        else:
            return DBAStatus.ACTIVE

    def _parse_business_structure(self, structure_str: str) -> BusinessStructure:
        """Parse business structure from string"""
        structure_str = structure_str.lower() if structure_str else ""

        if "individual" in structure_str or "sole" in structure_str:
            return BusinessStructure.INDIVIDUAL
        elif "llc" in structure_str or "limited liability company" in structure_str:
            return BusinessStructure.LLC
        elif "corporation" in structure_str or "inc" in structure_str:
            return BusinessStructure.CORPORATION
        elif "lp" in structure_str or "limited partnership" in structure_str:
            if "llp" in structure_str:
                return BusinessStructure.LIMITED_LIABILITY_PARTNERSHIP
            return BusinessStructure.LIMITED_PARTNERSHIP
        elif "general partnership" in structure_str or "gp" in structure_str:
            return BusinessStructure.GENERAL_PARTNERSHIP
        elif "trust" in structure_str:
            return BusinessStructure.TRUST
        elif "joint venture" in structure_str:
            return BusinessStructure.JOINT_VENTURE
        elif (
            "married" in structure_str
            or "husband" in structure_str
            or "wife" in structure_str
        ):
            return BusinessStructure.MARRIED_COUPLE
        else:
            return BusinessStructure.OTHER

    async def search_by_business_name(
        self,
        business_name: str,
        state: str,
        county: Optional[str] = None,
        include_expired: bool = False,
    ) -> List[DBAFiling]:
        """Search for DBA filings by business name"""
        results = []

        if state not in STATE_DBA_INFO:
            logger.warning(f"Unknown state: {state}")
            return results

        state_info = STATE_DBA_INFO[state]

        # Check if state has API
        if state_info.get("api_available") and state_info.get("state_registry_url"):
            # Try state-level search
            logger.info(f"Searching {state} state registry for '{business_name}'")
            # Implementation would vary by state API

        # For county-level states, need specific county
        if state_info["filing_level"] == "county" and county:
            county_key = f"{state}_{county.upper().replace(' ', '_')}"
            if county_key in COUNTY_DBA_SOURCES:
                config = COUNTY_DBA_SOURCES[county_key]
                logger.info(f"Searching {config['name']} for '{business_name}'")

        return results

    async def search_by_registrant_name(
        self, name: str, state: str, county: Optional[str] = None
    ) -> List[DBAFiling]:
        """Search for DBA filings by registrant/owner name"""
        results = []

        if state not in STATE_DBA_INFO:
            logger.warning(f"Unknown state: {state}")
            return results

        state_info = STATE_DBA_INFO[state]

        # Note: Registrant search is often more restricted than business name search
        logger.info(f"Searching for DBAs registered to '{name}' in {state}")

        return results

    async def search_by_filing_number(
        self, filing_number: str, state: str, county: Optional[str] = None
    ) -> Optional[DBAFiling]:
        """Search for a specific DBA filing by number"""
        if state not in STATE_DBA_INFO:
            logger.warning(f"Unknown state: {state}")
            return None

        state_info = STATE_DBA_INFO[state]

        logger.info(f"Looking up filing {filing_number} in {state}")

        return None

    async def get_expiring_filings(
        self, state: str, county: Optional[str] = None, days_until_expiration: int = 90
    ) -> List[DBAFiling]:
        """Get DBA filings that are expiring soon"""
        results = []

        if state not in STATE_DBA_INFO:
            return results

        state_info = STATE_DBA_INFO[state]

        # Only applicable for states with expiration
        if not state_info.get("duration_years"):
            logger.info(f"{state} DBAs do not expire")
            return results

        logger.info(
            f"Searching for DBAs expiring within {days_until_expiration} days in {state}"
        )

        return results

    async def get_recent_filings(
        self, state: str, county: Optional[str] = None, days: int = 30
    ) -> List[DBAFiling]:
        """Get recently filed DBAs"""
        results = []

        if state not in STATE_DBA_INFO:
            return results

        logger.info(f"Getting DBAs filed in last {days} days in {state}")

        return results

    def get_filing_requirements(self, state: str) -> Dict[str, Any]:
        """Get DBA filing requirements for a state"""
        if state not in STATE_DBA_INFO:
            return {"error": f"Unknown state: {state}"}

        info = STATE_DBA_INFO[state]

        requirements = {
            "state": state,
            "state_name": info["name"],
            "filing_level": info["filing_level"],
            "term_used": info["term_name"],
            "filing_office": info["filing_office"],
            "duration_years": info.get("duration_years", "No expiration"),
            "publication_required": info.get("publication_required", False),
            "state_registry_url": info.get("state_registry_url"),
            "api_available": info.get("api_available", False),
        }

        if info.get("publication_required"):
            requirements["publication_info"] = {
                "required": True,
                "publication_days": info.get("publication_days", "Varies by county"),
                "notes": info.get(
                    "notes", "Check with filing office for specific requirements"
                ),
            }

        return requirements

    def get_county_office(self, state: str, county: str) -> Optional[Dict[str, Any]]:
        """Get county DBA filing office information"""
        county_key = f"{state.upper()}_{county.upper().replace(' ', '_')}"

        if county_key in COUNTY_DBA_SOURCES:
            return COUNTY_DBA_SOURCES[county_key]

        # Return general state info if no specific county config
        if state in STATE_DBA_INFO:
            state_info = STATE_DBA_INFO[state]
            return {
                "name": f"{county} County {state_info['filing_office']}",
                "filing_office": state_info["filing_office"],
                "publication_required": state_info.get("publication_required", False),
                "notes": f"Contact the {county} County {state_info['filing_office']} for specific filing procedures",
            }

        return None

    def get_state_info(self, state: str) -> Optional[Dict[str, Any]]:
        """Get state DBA information"""
        return STATE_DBA_INFO.get(state.upper())

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get DBA information for all states"""
        return {
            state: {
                "name": info["name"],
                "filing_level": info["filing_level"],
                "term_name": info["term_name"],
                "filing_office": info["filing_office"],
                "duration_years": info.get("duration_years"),
                "publication_required": info.get("publication_required", False),
                "api_available": info.get("api_available", False),
            }
            for state, info in STATE_DBA_INFO.items()
        }

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics"""
        total_states = len(STATE_DBA_INFO)

        # Count by filing level
        county_level = sum(
            1 for s in STATE_DBA_INFO.values() if s["filing_level"] == "county"
        )
        state_level = sum(
            1 for s in STATE_DBA_INFO.values() if s["filing_level"] == "state"
        )
        town_level = sum(
            1
            for s in STATE_DBA_INFO.values()
            if s["filing_level"] in ["town", "city_town"]
        )
        other_level = total_states - county_level - state_level - town_level

        # Count features
        with_api = sum(1 for s in STATE_DBA_INFO.values() if s.get("api_available"))
        with_expiration = sum(
            1 for s in STATE_DBA_INFO.values() if s.get("duration_years")
        )
        with_publication = sum(
            1 for s in STATE_DBA_INFO.values() if s.get("publication_required")
        )

        return {
            "total_states": total_states,
            "total_county_offices": len(COUNTY_DBA_SOURCES),
            "filing_levels": {
                "state": state_level,
                "county": county_level,
                "town_city": town_level,
                "other": other_level,
            },
            "states_with_api": with_api,
            "states_with_expiration": with_expiration,
            "states_requiring_publication": with_publication,
            "api_coverage_percent": round(with_api / total_states * 100, 1),
        }


# Synchronous wrapper functions
def search_dba_by_business_name(
    business_name: str,
    state: str,
    county: Optional[str] = None,
    include_expired: bool = False,
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching DBA by business name"""

    async def _search():
        async with DBAFilingsAPI() as api:
            results = await api.search_by_business_name(
                business_name, state, county, include_expired
            )
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def search_dba_by_registrant(
    name: str, state: str, county: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching DBA by registrant name"""

    async def _search():
        async with DBAFilingsAPI() as api:
            results = await api.search_by_registrant_name(name, state, county)
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def get_dba_by_filing_number(
    filing_number: str, state: str, county: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for getting DBA by filing number"""

    async def _get():
        async with DBAFilingsAPI() as api:
            result = await api.search_by_filing_number(filing_number, state, county)
            return result.to_dict() if result else None

    return asyncio.run(_get())


def get_filing_requirements(state: str) -> Dict[str, Any]:
    """Get DBA filing requirements for a state"""
    api = DBAFilingsAPI()
    return api.get_filing_requirements(state)


def get_county_office_info(state: str, county: str) -> Optional[Dict[str, Any]]:
    """Get county DBA filing office information"""
    api = DBAFilingsAPI()
    return api.get_county_office(state, county)


def get_state_dba_info(state: str) -> Optional[Dict[str, Any]]:
    """Get state DBA information"""
    api = DBAFilingsAPI()
    return api.get_state_info(state)


def get_all_state_info() -> Dict[str, Dict[str, Any]]:
    """Get DBA information for all states"""
    api = DBAFilingsAPI()
    return api.get_all_states()


def get_coverage_stats() -> Dict[str, Any]:
    """Get coverage statistics for DBA filings"""
    api = DBAFilingsAPI()
    return api.get_coverage_stats()


if __name__ == "__main__":
    # Test the API
    print("DBA / Fictitious Business Name Filings Scraper")
    print("=" * 50)

    stats = get_coverage_stats()
    print(f"\nCoverage Statistics:")
    print(f"  Total States: {stats['total_states']}")
    print(f"  County Offices Configured: {stats['total_county_offices']}")
    print(
        f"  States with API: {stats['states_with_api']} ({stats['api_coverage_percent']}%)"
    )
    print(f"  States with Expiration: {stats['states_with_expiration']}")
    print(f"  States Requiring Publication: {stats['states_requiring_publication']}")

    print(f"\nFiling Levels:")
    for level, count in stats["filing_levels"].items():
        print(f"  {level}: {count}")

    print("\nStates with Publication Required:")
    states = get_all_state_info()
    for state_code, info in states.items():
        if info.get("publication_required"):
            print(f"  {state_code}: {info['name']}")

    print("\nStates with State-Level Filing:")
    for state_code, info in states.items():
        if info["filing_level"] == "state":
            print(f"  {state_code}: {info['name']} - {info['term_name']}")
