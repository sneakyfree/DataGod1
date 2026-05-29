"""
Inmate Records Category Scraper

Collects publicly available incarceration records including:
- Federal inmate locator (BOP)
- State department of corrections
- County jail rosters
- Parole and probation records
- Release information

Uses async/aiohttp for efficient API access where available.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import aiohttp

logger = logging.getLogger(__name__)


class CustodyStatus(Enum):
    """Inmate custody status."""

    IN_CUSTODY = "in_custody"
    RELEASED = "released"
    TRANSFERRED = "transferred"
    ESCAPED = "escaped"
    DECEASED = "deceased"
    PAROLE = "parole"
    PROBATION = "probation"
    WORK_RELEASE = "work_release"
    HOME_CONFINEMENT = "home_confinement"


class FacilityType(Enum):
    """Type of correctional facility."""

    FEDERAL_PRISON = "federal_prison"
    STATE_PRISON = "state_prison"
    COUNTY_JAIL = "county_jail"
    CITY_JAIL = "city_jail"
    DETENTION_CENTER = "detention_center"
    COMMUNITY_CORRECTIONS = "community_corrections"
    WORK_CAMP = "work_camp"
    HALFWAY_HOUSE = "halfway_house"


class SecurityLevel(Enum):
    """Facility security level."""

    MINIMUM = "minimum"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"
    ADMINISTRATIVE = "administrative"
    SUPERMAX = "supermax"


@dataclass
class InmateRecord:
    """Inmate record data structure."""

    inmate_id: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    suffix: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[int] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    custody_status: CustodyStatus = CustodyStatus.IN_CUSTODY
    facility_name: Optional[str] = None
    facility_type: Optional[FacilityType] = None
    facility_location: Optional[str] = None
    security_level: Optional[SecurityLevel] = None
    booking_date: Optional[datetime] = None
    release_date: Optional[datetime] = None
    projected_release: Optional[datetime] = None
    charges: List[str] = field(default_factory=list)
    offense_type: Optional[str] = None
    offense_description: Optional[str] = None
    sentence_length: Optional[str] = None
    sentence_start: Optional[datetime] = None
    sentence_end: Optional[datetime] = None
    bond_amount: Optional[float] = None
    bond_status: Optional[str] = None
    case_number: Optional[str] = None
    court: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    scars_marks_tattoos: List[str] = field(default_factory=list)
    mugshot_url: Optional[str] = None
    state: str = ""
    county: Optional[str] = None
    source_url: str = ""
    source_system: str = ""
    last_updated: Optional[datetime] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "inmate_id": self.inmate_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "middle_name": self.middle_name,
            "suffix": self.suffix,
            "date_of_birth": (
                self.date_of_birth.isoformat() if self.date_of_birth else None
            ),
            "age": self.age,
            "gender": self.gender,
            "race": self.race,
            "height": self.height,
            "weight": self.weight,
            "hair_color": self.hair_color,
            "eye_color": self.eye_color,
            "custody_status": self.custody_status.value,
            "facility_name": self.facility_name,
            "facility_type": self.facility_type.value if self.facility_type else None,
            "facility_location": self.facility_location,
            "security_level": (
                self.security_level.value if self.security_level else None
            ),
            "booking_date": (
                self.booking_date.isoformat() if self.booking_date else None
            ),
            "release_date": (
                self.release_date.isoformat() if self.release_date else None
            ),
            "projected_release": (
                self.projected_release.isoformat() if self.projected_release else None
            ),
            "charges": self.charges,
            "offense_type": self.offense_type,
            "offense_description": self.offense_description,
            "sentence_length": self.sentence_length,
            "sentence_start": (
                self.sentence_start.isoformat() if self.sentence_start else None
            ),
            "sentence_end": (
                self.sentence_end.isoformat() if self.sentence_end else None
            ),
            "bond_amount": self.bond_amount,
            "bond_status": self.bond_status,
            "case_number": self.case_number,
            "court": self.court,
            "aliases": self.aliases,
            "scars_marks_tattoos": self.scars_marks_tattoos,
            "mugshot_url": self.mugshot_url,
            "state": self.state,
            "county": self.county,
            "source_url": self.source_url,
            "source_system": self.source_system,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
        }


@dataclass
class FacilityInfo:
    """Correctional facility information."""

    facility_id: str
    name: str
    facility_type: FacilityType
    security_level: Optional[SecurityLevel] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: str = ""
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    capacity: Optional[int] = None
    current_population: Optional[int] = None
    warden: Optional[str] = None
    region: Optional[str] = None
    source_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "facility_id": self.facility_id,
            "name": self.name,
            "facility_type": self.facility_type.value,
            "security_level": (
                self.security_level.value if self.security_level else None
            ),
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "phone": self.phone,
            "capacity": self.capacity,
            "current_population": self.current_population,
            "warden": self.warden,
            "region": self.region,
            "source_url": self.source_url,
        }


# Federal inmate sources
FEDERAL_INMATE_SOURCES = {
    "bop": {
        "name": "Federal Bureau of Prisons",
        "url": "https://www.bop.gov/inmateloc/",
        "api_url": "https://www.bop.gov/PublicInfo/execute/inmateloc",
        "description": "Federal inmate locator - all federal prisoners",
    },
    "ice": {
        "name": "ICE Detainee Locator",
        "url": "https://locator.ice.gov/",
        "api_url": "https://locator.ice.gov/odls/search",
        "description": "Immigration detainee locator",
    },
    "usms": {
        "name": "US Marshals",
        "url": "https://www.usmarshals.gov/",
        "description": "US Marshals prisoner operations - Most Wanted",
    },
}

# State Department of Corrections sources with API capabilities
STATE_DOC_SOURCES: Dict[str, Dict[str, Any]] = {
    "AL": {
        "name": "Alabama DOC",
        "url": "http://www.doc.state.al.us/",
        "search_url": "http://www.doc.state.al.us/InmateSearch",
        "has_api": False,
    },
    "AK": {
        "name": "Alaska DOC",
        "url": "https://doc.alaska.gov/",
        "search_url": "https://www.prior.prior-msp.com/prior/#/alaska/search",
        "has_api": False,
    },
    "AZ": {
        "name": "Arizona DOC",
        "url": "https://corrections.az.gov/",
        "search_url": "https://corrections.az.gov/public-resources/inmate-datasearch",
        "api_url": "https://azcorrections.gov/api/inmates",
        "has_api": True,
    },
    "AR": {
        "name": "Arkansas DOC",
        "url": "https://adc.arkansas.gov/",
        "search_url": "https://apps.ark.org/inmate_info/index.php",
        "has_api": False,
    },
    "CA": {
        "name": "California CDCR",
        "url": "https://www.cdcr.ca.gov/",
        "search_url": "https://inmatelocator.cdcr.ca.gov/",
        "api_url": "https://inmatelocator.cdcr.ca.gov/api/search",
        "has_api": True,
    },
    "CO": {
        "name": "Colorado DOC",
        "url": "https://www.colorado.gov/cdoc",
        "search_url": "https://www.colorado.gov/pacific/cdoc/offender-search",
        "has_api": False,
    },
    "CT": {
        "name": "Connecticut DOC",
        "url": "https://portal.ct.gov/DOC",
        "search_url": "https://www.ctinmateinfo.state.ct.us/",
        "has_api": False,
    },
    "DE": {
        "name": "Delaware DOC",
        "url": "https://doc.delaware.gov/",
        "search_url": "https://doc.delaware.gov/InmateLookup.shtml",
        "has_api": False,
    },
    "FL": {
        "name": "Florida DOC",
        "url": "http://www.dc.state.fl.us/",
        "search_url": "http://www.dc.state.fl.us/offenderSearch/",
        "api_url": "http://www.dc.state.fl.us/offenderSearch/api/search.aspx",
        "has_api": True,
    },
    "GA": {
        "name": "Georgia DOC",
        "url": "http://www.dcor.state.ga.us/",
        "search_url": "http://www.dcor.state.ga.us/GDC/OffenderQuery/jsp/OffQryForm.jsp",
        "has_api": False,
    },
    "HI": {
        "name": "Hawaii PSD",
        "url": "https://dps.hawaii.gov/",
        "search_url": "https://dps.hawaii.gov/about/divisions/corrections-division/",
        "has_api": False,
    },
    "ID": {
        "name": "Idaho DOC",
        "url": "https://www.idoc.idaho.gov/",
        "search_url": "https://www.idoc.idaho.gov/content/prisons/offender_search",
        "has_api": False,
    },
    "IL": {
        "name": "Illinois DOC",
        "url": "https://www2.illinois.gov/idoc/",
        "search_url": "https://www.idoc.state.il.us/subsections/search/ISdefault.asp",
        "has_api": False,
    },
    "IN": {
        "name": "Indiana DOC",
        "url": "https://www.in.gov/idoc/",
        "search_url": "https://www.in.gov/apps/indcorrection/ofs/ofs",
        "has_api": False,
    },
    "IA": {
        "name": "Iowa DOC",
        "url": "https://doc.iowa.gov/",
        "search_url": "https://doc.iowa.gov/offender/search",
        "has_api": False,
    },
    "KS": {
        "name": "Kansas DOC",
        "url": "https://www.doc.ks.gov/",
        "search_url": "https://www.doc.ks.gov/kdoc-inmate-lookup",
        "has_api": False,
    },
    "KY": {
        "name": "Kentucky DOC",
        "url": "https://corrections.ky.gov/",
        "search_url": "https://kool.corrections.ky.gov/",
        "has_api": False,
    },
    "LA": {
        "name": "Louisiana DOC",
        "url": "https://doc.louisiana.gov/",
        "search_url": "https://doc.louisiana.gov/imprisoned-person-locator/",
        "has_api": False,
    },
    "ME": {
        "name": "Maine DOC",
        "url": "https://www.maine.gov/corrections/",
        "search_url": "https://www.maine.gov/corrections/home/adult-client-information",
        "has_api": False,
    },
    "MD": {
        "name": "Maryland DPSCS",
        "url": "https://www.dpscs.state.md.us/",
        "search_url": "https://www.dpscs.state.md.us/inmate/",
        "has_api": False,
    },
    "MA": {
        "name": "Massachusetts DOC",
        "url": "https://www.mass.gov/orgs/massachusetts-department-of-correction",
        "search_url": "https://www.mass.gov/service-details/search-the-prison-population",
        "has_api": False,
    },
    "MI": {
        "name": "Michigan DOC",
        "url": "https://www.michigan.gov/corrections",
        "search_url": "https://mdocweb.state.mi.us/OTIS2/otis2.aspx",
        "api_url": "https://mdocweb.state.mi.us/OTIS2/otis2.aspx/Search",
        "has_api": True,
    },
    "MN": {
        "name": "Minnesota DOC",
        "url": "https://mn.gov/doc/",
        "search_url": "https://coms.doc.state.mn.us/PublicViewer/",
        "has_api": False,
    },
    "MS": {
        "name": "Mississippi DOC",
        "url": "https://www.mdoc.ms.gov/",
        "search_url": "https://www.mdoc.ms.gov/Inmate-Information/Pages/Inmate-Search.aspx",
        "has_api": False,
    },
    "MO": {
        "name": "Missouri DOC",
        "url": "https://doc.mo.gov/",
        "search_url": "https://web.mo.gov/doc/offSearchWeb/",
        "has_api": False,
    },
    "MT": {
        "name": "Montana DOC",
        "url": "https://cor.mt.gov/",
        "search_url": "https://cor.mt.gov/Offenders/OffenderSearch/",
        "has_api": False,
    },
    "NE": {
        "name": "Nebraska DCS",
        "url": "https://corrections.nebraska.gov/",
        "search_url": "https://dcs-inmatesearch.ne.gov/",
        "has_api": False,
    },
    "NV": {
        "name": "Nevada DOC",
        "url": "https://doc.nv.gov/",
        "search_url": "https://ofdsearch.doc.nv.gov/",
        "has_api": False,
    },
    "NH": {
        "name": "New Hampshire DOC",
        "url": "https://www.nh.gov/nhdoc/",
        "search_url": "https://www.nh.gov/nhdoc/divisions/victim-services/offender-locator.htm",
        "has_api": False,
    },
    "NJ": {
        "name": "New Jersey DOC",
        "url": "https://www.state.nj.us/corrections/",
        "search_url": "https://www.state.nj.us/corrections/pages/offendersSearchForm.html",
        "has_api": False,
    },
    "NM": {
        "name": "New Mexico DOC",
        "url": "https://cd.nm.gov/",
        "search_url": "https://cd.nm.gov/inmate-search/",
        "has_api": False,
    },
    "NY": {
        "name": "New York DOCCS",
        "url": "https://doccs.ny.gov/",
        "search_url": "https://nysdoccslookup.doccs.ny.gov/",
        "api_url": "https://nysdoccslookup.doccs.ny.gov/api/search",
        "has_api": True,
    },
    "NC": {
        "name": "North Carolina DPS",
        "url": "https://www.ncdps.gov/",
        "search_url": "https://webapps.doc.state.nc.us/opi/offendersearch.do",
        "has_api": False,
    },
    "ND": {
        "name": "North Dakota DOCR",
        "url": "https://www.docr.nd.gov/",
        "search_url": "https://www.docr.nd.gov/offender-locator",
        "has_api": False,
    },
    "OH": {
        "name": "Ohio DRC",
        "url": "https://drc.ohio.gov/",
        "search_url": "https://appgateway.drc.ohio.gov/OffenderSearch/",
        "has_api": False,
    },
    "OK": {
        "name": "Oklahoma DOC",
        "url": "https://oklahoma.gov/doc.html",
        "search_url": "https://okoffender.doc.ok.gov/",
        "has_api": False,
    },
    "OR": {
        "name": "Oregon DOC",
        "url": "https://www.oregon.gov/doc/",
        "search_url": "https://www.oregon.gov/doc/pages/ojin-search-tips.aspx",
        "has_api": False,
    },
    "PA": {
        "name": "Pennsylvania DOC",
        "url": "https://www.cor.pa.gov/",
        "search_url": "https://inmatelocator.cor.pa.gov/",
        "has_api": False,
    },
    "RI": {
        "name": "Rhode Island DOC",
        "url": "https://doc.ri.gov/",
        "search_url": "https://doc.ri.gov/resources/search",
        "has_api": False,
    },
    "SC": {
        "name": "South Carolina DOC",
        "url": "https://www.doc.sc.gov/",
        "search_url": "https://public.doc.state.sc.us/scdc-public/",
        "has_api": False,
    },
    "SD": {
        "name": "South Dakota DOC",
        "url": "https://doc.sd.gov/",
        "search_url": "https://doc.sd.gov/adult/lookup/",
        "has_api": False,
    },
    "TN": {
        "name": "Tennessee DOC",
        "url": "https://www.tn.gov/correction.html",
        "search_url": "https://apps.tn.gov/foil/search.jsp",
        "has_api": False,
    },
    "TX": {
        "name": "Texas TDCJ",
        "url": "https://www.tdcj.texas.gov/",
        "search_url": "https://offender.tdcj.texas.gov/OffenderSearch/",
        "api_url": "https://offender.tdcj.texas.gov/OffenderSearch/api/search",
        "has_api": True,
    },
    "UT": {
        "name": "Utah DOC",
        "url": "https://corrections.utah.gov/",
        "search_url": "https://corrections.utah.gov/offender-search/",
        "has_api": False,
    },
    "VT": {
        "name": "Vermont DOC",
        "url": "https://doc.vermont.gov/",
        "search_url": "https://doc.vermont.gov/node/1876",
        "has_api": False,
    },
    "VA": {
        "name": "Virginia DOC",
        "url": "https://vadoc.virginia.gov/",
        "search_url": "https://vadoc.virginia.gov/offenders/offender-search/",
        "api_url": "https://vadoc.virginia.gov/api/offenders/search",
        "has_api": True,
    },
    "WA": {
        "name": "Washington DOC",
        "url": "https://www.doc.wa.gov/",
        "search_url": "https://www.doc.wa.gov/information/inmate-search/",
        "has_api": False,
    },
    "WV": {
        "name": "West Virginia DCR",
        "url": "https://dcr.wv.gov/",
        "search_url": "https://dcr.wv.gov/resources/Pages/Offender-Search.aspx",
        "has_api": False,
    },
    "WI": {
        "name": "Wisconsin DOC",
        "url": "https://doc.wi.gov/",
        "search_url": "https://appsdoc.wi.gov/lop/home.do",
        "has_api": False,
    },
    "WY": {
        "name": "Wyoming DOC",
        "url": "https://corrections.wyo.gov/",
        "search_url": "https://corrections.wyo.gov/inmate-family-services/inmate-search",
        "has_api": False,
    },
}

# Sex offender registry sources (public data)
SEX_OFFENDER_REGISTRIES = {
    "nsopw": {
        "name": "National Sex Offender Public Website",
        "url": "https://www.nsopw.gov/",
        "api_url": "https://www.nsopw.gov/en/api/Search",
        "description": "Free public access to sex offender data nationwide",
    },
    "family_watchdog": {
        "name": "Family Watchdog",
        "url": "https://www.familywatchdog.us/",
        "description": "Free sex offender search and alerts",
    },
}


class InmateRecordsScraper:
    """
    Scraper for publicly available inmate records.

    Features:
    - Federal BOP inmate locator
    - State DOC inmate searches
    - County jail rosters
    - Sex offender registry searches
    - Custody status tracking

    Uses async/aiohttp for efficient multi-source queries.
    """

    CATEGORY = "inmate_records"
    DISPLAY_NAME = "Inmate Records"

    # BOP API endpoint
    BOP_BASE_URL = "https://www.bop.gov"
    BOP_SEARCH_URL = "https://www.bop.gov/PublicInfo/execute/inmateloc"

    # NSOPW API endpoint
    NSOPW_BASE_URL = "https://www.nsopw.gov"
    NSOPW_API_URL = "https://www.nsopw.gov/en/api/Search"

    def __init__(self, timeout: int = 30):
        """Initialize the inmate records scraper."""
        self.federal_sources = FEDERAL_INMATE_SOURCES
        self.state_sources = STATE_DOC_SOURCES
        self.sex_offender_sources = SEX_OFFENDER_REGISTRIES
        self.records: List[InmateRecord] = []
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request = 0.0
        self._rate_limit_delay = 1.0  # 1 second between requests
        logger.info("InmateRecordsScraper initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "en-US,en;q=0.9",
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

    # ========== Federal BOP Search ==========

    async def search_federal_inmates(
        self,
        first_name: str = "",
        last_name: str = "",
        middle_name: str = "",
        age: Optional[int] = None,
        race: str = "",
        sex: str = "",
    ) -> List[InmateRecord]:
        """
        Search federal BOP inmate locator.

        The BOP provides a public inmate locator at bop.gov/inmateloc/
        covering all federal prisoners, past and present.

        Args:
            first_name: First name (partial match supported)
            last_name: Last name (required, partial match supported)
            middle_name: Middle name (optional)
            age: Age (optional)
            race: Race code (optional): A=Asian, B=Black, I=Native, W=White
            sex: Gender: M=Male, F=Female

        Returns:
            List of matching inmate records
        """
        if not last_name and not first_name:
            logger.warning("BOP search requires at least first or last name")
            return []

        logger.info(f"Searching federal inmates: {last_name}, {first_name}")

        await self._rate_limit()
        session = await self._get_session()

        # BOP uses form POST
        params = {
            "nameFirst": first_name,
            "nameLast": last_name,
            "nameMiddle": middle_name,
            "age": str(age) if age else "",
            "race": race.upper() if race else "",
            "sex": sex.upper() if sex else "",
            "output": "json",
        }

        inmates = []

        try:
            # BOP doesn't have a documented JSON API but we can try the form endpoint
            async with session.post(self.BOP_SEARCH_URL, data=params) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")

                    if "json" in content_type:
                        data = await response.json()
                        inmates = self._parse_bop_results(data)
                    else:
                        # HTML response - would need parsing
                        html = await response.text()
                        inmates = self._parse_bop_html(html, last_name, first_name)
                elif response.status == 429:
                    logger.warning("BOP rate limited, waiting...")
                    await asyncio.sleep(60)
                else:
                    logger.warning(f"BOP search returned status {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"BOP search failed: {e}")
        except Exception as e:
            logger.error(f"BOP search error: {e}")

        return inmates

    def _parse_bop_results(self, data: Dict[str, Any]) -> List[InmateRecord]:
        """Parse BOP JSON response."""
        inmates = []

        results = data.get("InmateLocator", [])
        if isinstance(results, dict):
            results = [results]

        for item in results:
            try:
                # Parse release date
                release_date = None
                rel_str = item.get("releasedDate") or item.get("projRelDate")
                if rel_str:
                    try:
                        release_date = datetime.strptime(rel_str, "%m/%d/%Y")
                    except ValueError:
                        pass

                # Determine custody status
                status = CustodyStatus.IN_CUSTODY
                if item.get("status", "").upper() == "RELEASED":
                    status = CustodyStatus.RELEASED

                inmate = InmateRecord(
                    inmate_id=item.get("register_number", item.get("regNum", "")),
                    first_name=item.get("nameFirst", item.get("firstName", "")),
                    last_name=item.get("nameLast", item.get("lastName", "")),
                    middle_name=item.get("nameMiddle", item.get("middleName")),
                    age=int(item["age"]) if item.get("age") else None,
                    race=item.get("race"),
                    gender=item.get("sex"),
                    custody_status=status,
                    facility_name=item.get("faession", item.get("facility")),
                    facility_type=FacilityType.FEDERAL_PRISON,
                    release_date=release_date,
                    projected_release=(
                        release_date if status == CustodyStatus.IN_CUSTODY else None
                    ),
                    source_url="https://www.bop.gov/inmateloc/",
                    source_system="BOP",
                    state="FEDERAL",
                    last_updated=datetime.now(),
                    raw_data=item,
                )
                inmates.append(inmate)
            except Exception as e:
                logger.warning(f"Error parsing BOP inmate: {e}")

        return inmates

    def _parse_bop_html(
        self, html: str, last_name: str, first_name: str
    ) -> List[InmateRecord]:
        """
        Parse BOP HTML response.

        Note: This is a fallback when JSON isn't available.
        The BOP website uses tables for results.
        """
        inmates = []

        # Simple regex-based extraction (would use BeautifulSoup in production)
        # Look for inmate table rows
        row_pattern = r'<tr[^>]*class="[^"]*inmate[^"]*"[^>]*>(.*?)</tr>'
        cell_pattern = r"<td[^>]*>(.*?)</td>"

        rows = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)

        for row in rows:
            cells = re.findall(cell_pattern, row, re.DOTALL)
            if len(cells) >= 4:
                # Clean HTML tags from cells
                clean_cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]

                try:
                    inmate = InmateRecord(
                        inmate_id=(
                            clean_cells[0] if clean_cells[0] else f"BOP-{len(inmates)}"
                        ),
                        last_name=clean_cells[1] if len(clean_cells) > 1 else last_name,
                        first_name=(
                            clean_cells[2] if len(clean_cells) > 2 else first_name
                        ),
                        facility_name=clean_cells[3] if len(clean_cells) > 3 else None,
                        facility_type=FacilityType.FEDERAL_PRISON,
                        custody_status=CustodyStatus.IN_CUSTODY,
                        source_url="https://www.bop.gov/inmateloc/",
                        source_system="BOP",
                        state="FEDERAL",
                        last_updated=datetime.now(),
                    )
                    inmates.append(inmate)
                except Exception as e:
                    logger.warning(f"Error parsing BOP HTML row: {e}")

        return inmates

    async def get_federal_inmate_by_id(
        self, register_number: str
    ) -> Optional[InmateRecord]:
        """
        Get federal inmate details by BOP register number.

        Args:
            register_number: BOP register number (e.g., "12345-678")

        Returns:
            Inmate record if found
        """
        logger.info(f"Looking up BOP inmate {register_number}")

        # Clean the register number
        reg_num = register_number.strip().upper()

        await self._rate_limit()
        session = await self._get_session()

        params = {
            "registrationNumber": reg_num,
            "output": "json",
        }

        try:
            async with session.post(self.BOP_SEARCH_URL, data=params) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "json" in content_type:
                        data = await response.json()
                        results = self._parse_bop_results(data)
                        return results[0] if results else None
        except Exception as e:
            logger.error(f"BOP lookup error: {e}")

        return None

    # ========== State DOC Search ==========

    async def search_state_inmates(
        self, state: str, first_name: str = "", last_name: str = "", inmate_id: str = ""
    ) -> List[InmateRecord]:
        """
        Search state DOC inmates.

        Each state has different capabilities. Some have APIs,
        others require HTML scraping.

        Args:
            state: State code (e.g., 'CA', 'TX', 'NY')
            first_name: First name
            last_name: Last name
            inmate_id: State inmate ID

        Returns:
            List of matching inmate records
        """
        state = state.upper()

        if state not in self.state_sources:
            logger.warning(f"No DOC source for state {state}")
            return []

        source = self.state_sources[state]
        logger.info(f"Searching {state} inmates: {last_name}, {first_name}")

        # Route to appropriate state handler
        if source.get("has_api"):
            return await self._search_state_api(state, first_name, last_name, inmate_id)
        else:
            return await self._search_state_scrape(
                state, first_name, last_name, inmate_id
            )

    async def _search_state_api(
        self, state: str, first_name: str, last_name: str, inmate_id: str
    ) -> List[InmateRecord]:
        """Search states with known API endpoints."""
        source = self.state_sources[state]
        api_url = source.get("api_url")

        if not api_url:
            return []

        await self._rate_limit()
        session = await self._get_session()

        inmates = []

        # Build state-specific request
        if state == "CA":
            inmates = await self._search_california(
                session, first_name, last_name, inmate_id
            )
        elif state == "TX":
            inmates = await self._search_texas(
                session, first_name, last_name, inmate_id
            )
        elif state == "FL":
            inmates = await self._search_florida(
                session, first_name, last_name, inmate_id
            )
        elif state == "NY":
            inmates = await self._search_new_york(
                session, first_name, last_name, inmate_id
            )
        elif state == "MI":
            inmates = await self._search_michigan(
                session, first_name, last_name, inmate_id
            )
        elif state == "VA":
            inmates = await self._search_virginia(
                session, first_name, last_name, inmate_id
            )
        elif state == "AZ":
            inmates = await self._search_arizona(
                session, first_name, last_name, inmate_id
            )

        return inmates

    async def _search_california(
        self,
        session: aiohttp.ClientSession,
        first_name: str,
        last_name: str,
        inmate_id: str,
    ) -> List[InmateRecord]:
        """Search California CDCR inmate locator."""
        url = "https://inmatelocator.cdcr.ca.gov/api/search"

        params = {
            "firstName": first_name,
            "lastName": last_name,
            "cdcNumber": inmate_id,
        }

        inmates = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("results", []):
                        inmate = InmateRecord(
                            inmate_id=item.get("cdcNumber", ""),
                            first_name=item.get("firstName", ""),
                            last_name=item.get("lastName", ""),
                            middle_name=item.get("middleName"),
                            facility_name=item.get("facility"),
                            facility_type=FacilityType.STATE_PRISON,
                            custody_status=(
                                CustodyStatus.IN_CUSTODY
                                if item.get("status") == "INCARCERATED"
                                else CustodyStatus.RELEASED
                            ),
                            projected_release=self._parse_date(item.get("releaseDate")),
                            source_url="https://inmatelocator.cdcr.ca.gov/",
                            source_system="CDCR",
                            state="CA",
                            last_updated=datetime.now(),
                            raw_data=item,
                        )
                        inmates.append(inmate)
        except Exception as e:
            logger.error(f"California search error: {e}")

        return inmates

    async def _search_texas(
        self,
        session: aiohttp.ClientSession,
        first_name: str,
        last_name: str,
        inmate_id: str,
    ) -> List[InmateRecord]:
        """Search Texas TDCJ offender database."""
        url = "https://offender.tdcj.texas.gov/OffenderSearch/search.action"

        params = {
            "firstName": first_name,
            "lastName": last_name,
            "tdcjNumber": inmate_id,
            "sidNumber": "",
        }

        inmates = []

        try:
            async with session.post(url, data=params) as response:
                if response.status == 200:
                    # TDCJ returns HTML, parse results
                    html = await response.text()
                    inmates = self._parse_tdcj_results(html)
        except Exception as e:
            logger.error(f"Texas search error: {e}")

        return inmates

    def _parse_tdcj_results(self, html: str) -> List[InmateRecord]:
        """Parse Texas TDCJ search results."""
        inmates = []

        # Look for result table
        row_pattern = r'<tr[^>]*class="[^"]*searchResult[^"]*"[^>]*>(.*?)</tr>'
        link_pattern = r'href="([^"]+offenderDetail[^"]+)"'

        rows = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)

        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            if len(cells) >= 5:
                clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]

                # Extract TDCJ number from link if present
                link_match = re.search(link_pattern, row)
                tdcj_num = ""
                if link_match:
                    tdcj_match = re.search(r"tdcjNumber=(\d+)", link_match.group(1))
                    if tdcj_match:
                        tdcj_num = tdcj_match.group(1)

                try:
                    inmate = InmateRecord(
                        inmate_id=tdcj_num or clean[0],
                        last_name=clean[1] if len(clean) > 1 else "",
                        first_name=clean[2] if len(clean) > 2 else "",
                        facility_name=clean[3] if len(clean) > 3 else None,
                        facility_type=FacilityType.STATE_PRISON,
                        custody_status=CustodyStatus.IN_CUSTODY,
                        source_url="https://offender.tdcj.texas.gov/",
                        source_system="TDCJ",
                        state="TX",
                        last_updated=datetime.now(),
                    )
                    inmates.append(inmate)
                except Exception as e:
                    logger.warning(f"Error parsing TDCJ row: {e}")

        return inmates

    async def _search_florida(
        self,
        session: aiohttp.ClientSession,
        first_name: str,
        last_name: str,
        inmate_id: str,
    ) -> List[InmateRecord]:
        """Search Florida DOC offender database."""
        url = "http://www.dc.state.fl.us/offenderSearch/api/search.aspx"

        params = {
            "TypeSearch": "AI",
            "firstName": first_name,
            "lastName": last_name,
            "dcNumber": inmate_id,
        }

        inmates = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("Records", []):
                        inmate = InmateRecord(
                            inmate_id=item.get("DCNumber", ""),
                            first_name=item.get("FirstName", ""),
                            last_name=item.get("LastName", ""),
                            race=item.get("Race"),
                            gender=item.get("Sex"),
                            facility_name=item.get("CurrentFacility"),
                            facility_type=FacilityType.STATE_PRISON,
                            custody_status=(
                                CustodyStatus.IN_CUSTODY
                                if item.get("Status") == "INCARCERATED"
                                else CustodyStatus.RELEASED
                            ),
                            projected_release=self._parse_date(
                                item.get("TentativeReleaseDate")
                            ),
                            source_url="http://www.dc.state.fl.us/offenderSearch/",
                            source_system="FLDOC",
                            state="FL",
                            last_updated=datetime.now(),
                            raw_data=item,
                        )
                        inmates.append(inmate)
        except Exception as e:
            logger.error(f"Florida search error: {e}")

        return inmates

    async def _search_new_york(
        self,
        session: aiohttp.ClientSession,
        first_name: str,
        last_name: str,
        inmate_id: str,
    ) -> List[InmateRecord]:
        """Search New York DOCCS inmate lookup."""
        url = "https://nysdoccslookup.doccs.ny.gov/"

        params = {
            "namfirst": first_name,
            "namlast": last_name,
            "din": inmate_id,
        }

        inmates = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    # Parse HTML response
                    html = await response.text()
                    inmates = self._parse_nydoccs_results(html)
        except Exception as e:
            logger.error(f"New York search error: {e}")

        return inmates

    def _parse_nydoccs_results(self, html: str) -> List[InmateRecord]:
        """Parse New York DOCCS search results."""
        inmates = []

        # NY DOCCS uses tables for results
        row_pattern = r'<tr[^>]*>\s*<td[^>]*>\s*<a[^>]*href="[^"]*din=(\w+)"[^>]*>([^<]+)</a>.*?</tr>'

        matches = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)

        for din, name in matches:
            # Parse name (typically "LAST, FIRST")
            parts = name.strip().split(",")
            last_name = parts[0].strip() if parts else ""
            first_name = parts[1].strip() if len(parts) > 1 else ""

            try:
                inmate = InmateRecord(
                    inmate_id=din.strip(),
                    last_name=last_name,
                    first_name=first_name,
                    facility_type=FacilityType.STATE_PRISON,
                    custody_status=CustodyStatus.IN_CUSTODY,
                    source_url="https://nysdoccslookup.doccs.ny.gov/",
                    source_system="NYDOCCS",
                    state="NY",
                    last_updated=datetime.now(),
                )
                inmates.append(inmate)
            except Exception as e:
                logger.warning(f"Error parsing NYDOCCS row: {e}")

        return inmates

    async def _search_michigan(
        self,
        session: aiohttp.ClientSession,
        first_name: str,
        last_name: str,
        inmate_id: str,
    ) -> List[InmateRecord]:
        """Search Michigan DOC OTIS system."""
        url = "https://mdocweb.state.mi.us/OTIS2/otis2.aspx"

        params = {
            "txtFirstName": first_name,
            "txtLastName": last_name,
            "txtPrisonerNumber": inmate_id,
        }

        inmates = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    # Parse OTIS results (ASP.NET form-based)
                    # Implementation would parse the DataGrid results
                    pass
        except Exception as e:
            logger.error(f"Michigan search error: {e}")

        return inmates

    async def _search_virginia(
        self,
        session: aiohttp.ClientSession,
        first_name: str,
        last_name: str,
        inmate_id: str,
    ) -> List[InmateRecord]:
        """Search Virginia DOC offender database."""
        url = "https://vadoc.virginia.gov/offenders/locator/search.aspx"

        params = {
            "firstName": first_name,
            "lastName": last_name,
            "number": inmate_id,
        }

        inmates = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    # Parse HTML response
                    html = await response.text()
                    # Implementation would parse result tables
                    pass
        except Exception as e:
            logger.error(f"Virginia search error: {e}")

        return inmates

    async def _search_arizona(
        self,
        session: aiohttp.ClientSession,
        first_name: str,
        last_name: str,
        inmate_id: str,
    ) -> List[InmateRecord]:
        """Search Arizona DOC inmate database."""
        url = "https://corrections.az.gov/public-resources/inmate-datasearch"

        params = {
            "first": first_name,
            "last": last_name,
            "adc": inmate_id,
        }

        inmates = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    # Parse response
                    pass
        except Exception as e:
            logger.error(f"Arizona search error: {e}")

        return inmates

    async def _search_state_scrape(
        self, state: str, first_name: str, last_name: str, inmate_id: str
    ) -> List[InmateRecord]:
        """Search states requiring HTML scraping."""
        source = self.state_sources[state]
        search_url = source.get("search_url")

        if not search_url:
            logger.warning(f"No search URL for {state}")
            return []

        await self._rate_limit()
        session = await self._get_session()

        inmates = []

        # Generic form POST attempt
        params = {
            "firstName": first_name,
            "first_name": first_name,
            "FirstName": first_name,
            "lastName": last_name,
            "last_name": last_name,
            "LastName": last_name,
            "inmateId": inmate_id,
            "inmate_id": inmate_id,
        }

        try:
            # Try POST first
            async with session.post(search_url, data=params) as response:
                if response.status == 200:
                    html = await response.text()
                    # Generic table parser
                    inmates = self._parse_generic_inmate_table(html, state)
        except Exception as e:
            logger.error(f"{state} search error: {e}")

        return inmates

    def _parse_generic_inmate_table(self, html: str, state: str) -> List[InmateRecord]:
        """Generic parser for inmate search result tables."""
        inmates = []

        # Look for tables with inmate-like data
        # This is a best-effort parser for various DOC website formats

        # Pattern 1: Simple table rows with inmate data
        row_pattern = r"<tr[^>]*>(.*?)</tr>"
        cell_pattern = r"<td[^>]*>(.*?)</td>"

        rows = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)

        for row in rows[1:]:  # Skip header row
            cells = re.findall(cell_pattern, row, re.DOTALL)
            if len(cells) >= 3:
                clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]

                # Try to identify name patterns (LAST, FIRST or FIRST LAST)
                name_cell = clean[0] if clean[0] else clean[1]

                if "," in name_cell:
                    parts = name_cell.split(",")
                    last_name = parts[0].strip()
                    first_name = parts[1].strip() if len(parts) > 1 else ""
                else:
                    parts = name_cell.split()
                    first_name = parts[0] if parts else ""
                    last_name = parts[-1] if len(parts) > 1 else ""

                # Look for ID pattern
                inmate_id = ""
                for cell in clean:
                    if re.match(r"^[A-Z]?\d{5,10}$", cell):
                        inmate_id = cell
                        break

                if first_name or last_name:
                    try:
                        inmate = InmateRecord(
                            inmate_id=inmate_id or f"{state}-{len(inmates)}",
                            first_name=first_name,
                            last_name=last_name,
                            facility_type=FacilityType.STATE_PRISON,
                            custody_status=CustodyStatus.IN_CUSTODY,
                            source_url=self.state_sources.get(state, {}).get(
                                "search_url", ""
                            ),
                            source_system=f"{state}DOC",
                            state=state,
                            last_updated=datetime.now(),
                        )
                        inmates.append(inmate)
                    except Exception:
                        pass

        return inmates

    # ========== Inmate by ID ==========

    async def get_inmate_by_id(
        self, inmate_id: str, state: str = "", system: str = "state"
    ) -> Optional[InmateRecord]:
        """
        Get inmate details by ID.

        Args:
            inmate_id: Inmate ID number
            state: State code (for state systems)
            system: 'federal' or 'state'

        Returns:
            Inmate record if found
        """
        logger.info(f"Getting inmate {inmate_id} from {system}")

        if system.lower() == "federal":
            return await self.get_federal_inmate_by_id(inmate_id)

        if state:
            results = await self.search_state_inmates(state=state, inmate_id=inmate_id)
            return results[0] if results else None

        return None

    # ========== County Jail Search ==========

    async def get_county_jail_roster(
        self, state: str, county: str
    ) -> List[InmateRecord]:
        """
        Get county jail roster/current inmates.

        Many counties publish daily jail rosters online.

        Args:
            state: State code
            county: County name

        Returns:
            List of current jail inmates
        """
        logger.info(f"Getting jail roster for {county}, {state}")
        inmates = []

        # County jails often use JailTracker, Inmate-Tracker, or similar systems
        # Would need county-specific implementation

        return inmates

    async def search_by_booking_date(
        self,
        state: str,
        county: str = "",
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> List[InmateRecord]:
        """
        Search inmates by booking date range.

        Args:
            state: State code
            county: County name (optional)
            start_date: Start date
            end_date: End date

        Returns:
            List of inmates booked in date range
        """
        logger.info(f"Searching bookings in {state}")

        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        inmates = []

        # Implementation would depend on state/county system capabilities
        return inmates

    async def get_recent_releases(
        self, state: str, days: int = 30
    ) -> List[InmateRecord]:
        """
        Get recently released inmates.

        Args:
            state: State code
            days: Number of days back to search

        Returns:
            List of recently released inmates
        """
        logger.info(f"Getting recent releases in {state} (last {days} days)")
        releases = []

        # Would search DOC release records
        return releases

    # ========== Sex Offender Registry ==========

    async def search_sex_offenders(
        self,
        last_name: str = "",
        first_name: str = "",
        city: str = "",
        state: str = "",
        zip_code: str = "",
        radius_miles: int = 0,
    ) -> List[InmateRecord]:
        """
        Search NSOPW (National Sex Offender Public Website).

        Free public access to registered sex offender data.

        Args:
            last_name: Last name
            first_name: First name
            city: City
            state: State code
            zip_code: ZIP code
            radius_miles: Search radius from ZIP

        Returns:
            List of matching offender records
        """
        logger.info(f"Searching sex offender registry: {last_name}, {first_name}")

        await self._rate_limit()
        session = await self._get_session()

        # NSOPW uses POST with specific format
        url = "https://www.nsopw.gov/en/Search/SearchResults"

        params = {
            "LastName": last_name,
            "FirstName": first_name,
            "City": city,
            "State": state,
            "ZipCode": zip_code,
            "Radius": str(radius_miles) if radius_miles else "",
        }

        offenders = []

        try:
            async with session.post(url, data=params) as response:
                if response.status == 200:
                    # NSOPW returns HTML
                    html = await response.text()
                    offenders = self._parse_nsopw_results(html)
        except Exception as e:
            logger.error(f"NSOPW search error: {e}")

        return offenders

    def _parse_nsopw_results(self, html: str) -> List[InmateRecord]:
        """Parse NSOPW search results."""
        offenders = []

        # Look for offender cards/results
        pattern = r'<div[^>]*class="[^"]*offender[^"]*"[^>]*>(.*?)</div>'

        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        for match in matches:
            # Extract name
            name_match = re.search(r'<[^>]*class="[^"]*name[^"]*"[^>]*>([^<]+)', match)
            if name_match:
                name = name_match.group(1).strip()
                parts = name.split(",") if "," in name else name.split()

                last_name = parts[0].strip() if parts else ""
                first_name = parts[1].strip() if len(parts) > 1 else ""

                try:
                    offender = InmateRecord(
                        inmate_id=f"NSOPW-{len(offenders)}",
                        first_name=first_name,
                        last_name=last_name,
                        custody_status=CustodyStatus.RELEASED,  # Registered offenders are typically released
                        offense_type="Sex Offense",
                        source_url="https://www.nsopw.gov/",
                        source_system="NSOPW",
                        last_updated=datetime.now(),
                    )
                    offenders.append(offender)
                except Exception:
                    pass

        return offenders

    # ========== Parole/Probation ==========

    async def get_parole_records(
        self, state: str, parolee_name: str = "", county: str = ""
    ) -> List[InmateRecord]:
        """
        Search parole records.

        Note: Parole records are often not publicly searchable.
        Some states provide limited parole lookup.

        Args:
            state: State code
            parolee_name: Parolee name search
            county: County filter

        Returns:
            List of parole records
        """
        logger.info(f"Searching parole records in {state}")
        records = []

        # Most states don't have public parole lookup
        # Would need state-specific implementation where available

        return records

    # ========== Facilities ==========

    async def get_federal_facilities(self) -> List[FacilityInfo]:
        """
        Get list of federal BOP facilities.

        Returns:
            List of federal prison facilities
        """
        logger.info("Getting federal facility list")

        await self._rate_limit()
        session = await self._get_session()

        facilities = []

        try:
            url = "https://www.bop.gov/locations/"
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    facilities = self._parse_bop_facilities(html)
        except Exception as e:
            logger.error(f"Error getting federal facilities: {e}")

        return facilities

    def _parse_bop_facilities(self, html: str) -> List[FacilityInfo]:
        """Parse BOP facility list."""
        facilities = []

        # Look for facility entries
        pattern = r'<a[^>]*href="/locations/institutions/([^"]+)"[^>]*>([^<]+)</a>'

        matches = re.findall(pattern, html, re.IGNORECASE)

        for facility_id, name in matches:
            # Determine security level from name
            security = None
            name_upper = name.upper()
            if "USP" in name_upper or "PENITENTIARY" in name_upper:
                security = SecurityLevel.HIGH
            elif "FCI" in name_upper:
                security = SecurityLevel.MEDIUM
            elif "FPC" in name_upper or "CAMP" in name_upper:
                security = SecurityLevel.MINIMUM
            elif "FDC" in name_upper or "DETENTION" in name_upper:
                security = SecurityLevel.ADMINISTRATIVE
            elif "ADX" in name_upper:
                security = SecurityLevel.SUPERMAX

            facility = FacilityInfo(
                facility_id=facility_id,
                name=name.strip(),
                facility_type=FacilityType.FEDERAL_PRISON,
                security_level=security,
                source_url=f"https://www.bop.gov/locations/institutions/{facility_id}",
            )
            facilities.append(facility)

        return facilities

    async def get_state_facilities(self, state: str) -> List[FacilityInfo]:
        """
        Get list of state DOC facilities.

        Args:
            state: State code

        Returns:
            List of state prison facilities
        """
        state = state.upper()
        logger.info(f"Getting {state} facility list")

        if state not in self.state_sources:
            return []

        facilities = []

        # Would implement state-specific facility list retrieval

        return facilities

    # ========== Utility Methods ==========

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats."""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y/%m/%d",
            "%d-%b-%Y",
            "%B %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        return None

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        states_with_api = [
            s for s, info in self.state_sources.items() if info.get("has_api")
        ]

        return {
            "category": self.CATEGORY,
            "display_name": self.DISPLAY_NAME,
            "federal_sources": len(self.federal_sources),
            "states_total": len(self.state_sources),
            "states_with_api": len(states_with_api),
            "states_api_list": states_with_api,
            "states_scrape_only": len(self.state_sources) - len(states_with_api),
            "sex_offender_sources": len(self.sex_offender_sources),
            "custody_statuses": [s.value for s in CustodyStatus],
            "facility_types": [t.value for t in FacilityType],
            "security_levels": [l.value for l in SecurityLevel],
        }


# ========== Synchronous Wrappers ==========


def get_inmate_scraper() -> InmateRecordsScraper:
    """Get inmate records scraper instance."""
    return InmateRecordsScraper()


def search_inmates(
    last_name: str, first_name: str = "", state: str = "", **kwargs
) -> List[Dict[str, Any]]:
    """
    Search for inmate records (synchronous wrapper).

    Args:
        last_name: Last name
        first_name: First name
        state: State code (empty for federal search)

    Returns:
        List of inmate records as dictionaries
    """

    async def _search():
        async with InmateRecordsScraper() as scraper:
            if state:
                records = await scraper.search_state_inmates(
                    state, first_name, last_name
                )
            else:
                records = await scraper.search_federal_inmates(first_name, last_name)
            return [r.to_dict() for r in records]

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result()
        return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def search_federal_inmates(
    last_name: str, first_name: str = "", **kwargs
) -> List[Dict[str, Any]]:
    """Search federal BOP inmates (synchronous)."""

    async def _search():
        async with InmateRecordsScraper() as scraper:
            records = await scraper.search_federal_inmates(
                first_name, last_name, **kwargs
            )
            return [r.to_dict() for r in records]

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result()
        return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def search_sex_offenders(
    last_name: str = "",
    first_name: str = "",
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> List[Dict[str, Any]]:
    """Search sex offender registry (synchronous)."""

    async def _search():
        async with InmateRecordsScraper() as scraper:
            records = await scraper.search_sex_offenders(
                last_name=last_name,
                first_name=first_name,
                city=city,
                state=state,
                zip_code=zip_code,
            )
            return [r.to_dict() for r in records]

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result()
        return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def get_available_sources() -> Dict[str, Any]:
    """Get all available inmate record sources."""
    scraper = InmateRecordsScraper()
    return {
        "federal_sources": FEDERAL_INMATE_SOURCES,
        "state_sources": {
            state: {
                "name": info["name"],
                "url": info["url"],
                "search_url": info.get("search_url"),
                "has_api": info.get("has_api", False),
            }
            for state, info in STATE_DOC_SOURCES.items()
        },
        "sex_offender_sources": SEX_OFFENDER_REGISTRIES,
        "coverage": scraper.get_coverage_stats(),
    }
