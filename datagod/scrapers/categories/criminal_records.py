"""
Criminal Records Scraper

Free public criminal records sources:
- National Sex Offender Public Website (NSOPW)
- State sex offender registries
- State Department of Corrections inmate search
- County jail inmate rosters
- Most wanted lists (FBI, state, local)
- Warrant databases (where public)
- Court dockets (felony/misdemeanor)

Free Federal Sources:
- NSOPW (nsopw.gov) - National Sex Offender Registry
- FBI Most Wanted
- US Marshals fugitive list
- ICE detainee locator

Note: This module only accesses publicly available records.
Background checks requiring consent are not included.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class OffenderType(Enum):
    """Sex offender classification"""

    LEVEL_1 = "Level 1"  # Low risk
    LEVEL_2 = "Level 2"  # Moderate risk
    LEVEL_3 = "Level 3"  # High risk
    PREDATOR = "Predator"
    UNCLASSIFIED = "Unclassified"


class InmateStatus(Enum):
    """Inmate custody status"""

    IN_CUSTODY = "In Custody"
    RELEASED = "Released"
    PAROLE = "On Parole"
    PROBATION = "On Probation"
    ESCAPED = "Escaped"
    DECEASED = "Deceased"
    TRANSFERRED = "Transferred"


class WarrantType(Enum):
    """Warrant types"""

    ARREST = "Arrest Warrant"
    BENCH = "Bench Warrant"
    SEARCH = "Search Warrant"
    CAPIAS = "Capias"
    EXTRADITION = "Extradition"


class CrimeCategory(Enum):
    """Crime categories"""

    VIOLENT = "Violent Crime"
    PROPERTY = "Property Crime"
    DRUG = "Drug Offense"
    SEX = "Sex Offense"
    FRAUD = "Fraud"
    DUI = "DUI/DWI"
    TRAFFIC = "Traffic"
    OTHER = "Other"


@dataclass
class SexOffender:
    """Registered sex offender record"""

    registry_id: str
    name: str
    aliases: List[str] = field(default_factory=list)
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    photo_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    offender_level: Optional[OffenderType] = None
    offenses: List[str] = field(default_factory=list)
    conviction_date: Optional[date] = None
    conviction_state: Optional[str] = None
    registration_date: Optional[date] = None
    employer: Optional[str] = None
    school: Optional[str] = None
    vehicle: Optional[str] = None
    scars_marks: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class Inmate:
    """Prison/jail inmate record"""

    inmate_id: str
    name: str
    aliases: List[str] = field(default_factory=list)
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    photo_url: Optional[str] = None
    facility: Optional[str] = None
    facility_type: Optional[str] = None  # Prison, Jail, Federal
    status: Optional[InmateStatus] = None
    custody_date: Optional[date] = None
    release_date: Optional[date] = None
    projected_release: Optional[date] = None
    charges: List[str] = field(default_factory=list)
    sentence: Optional[str] = None
    case_number: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class Warrant:
    """Active warrant record"""

    warrant_number: str
    name: str
    aliases: List[str] = field(default_factory=list)
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    photo_url: Optional[str] = None
    last_known_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    warrant_type: Optional[WarrantType] = None
    charges: List[str] = field(default_factory=list)
    issuing_court: Optional[str] = None
    issuing_date: Optional[date] = None
    bond_amount: Optional[float] = None
    agency: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class MostWanted:
    """Most wanted fugitive record"""

    name: str
    aliases: List[str] = field(default_factory=list)
    photo_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    place_of_birth: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    race: Optional[str] = None
    nationality: Optional[str] = None
    scars_marks: Optional[str] = None
    charges: List[str] = field(default_factory=list)
    caution: Optional[str] = None
    reward: Optional[str] = None
    agency: Optional[str] = None  # FBI, US Marshals, State, Local
    wanted_since: Optional[date] = None
    source_url: Optional[str] = None


@dataclass
class CriminalCase:
    """Criminal court case"""

    case_number: str
    defendant_name: str
    case_status: Optional[str] = None
    filing_date: Optional[date] = None
    disposition_date: Optional[date] = None
    charges: List[str] = field(default_factory=list)
    disposition: Optional[str] = None
    sentence: Optional[str] = None
    court: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    judge: Optional[str] = None
    source_url: Optional[str] = None


class CriminalRecordsScraper:
    """
    Scraper for free public criminal records

    Sources:
    - NSOPW (National Sex Offender Public Website)
    - State DOC inmate search portals
    - County sheriff/jail websites
    - FBI/US Marshals most wanted
    - State most wanted lists
    """

    NSOPW_URL = "https://www.nsopw.gov/en/Search"

    # State DOC inmate search URLs
    STATE_DOC_URLS = {
        "AL": "https://doc.alabama.gov/InmateSearch",
        "AK": "https://www.correct.state.ak.us/doc/inmates",
        "AZ": "https://azcorrections.gov/inmate-search",
        "AR": "https://adc.arkansas.gov/inmate-search",
        "CA": "https://inmatelocator.cdcr.ca.gov/",
        "CO": "https://www.doc.state.co.us/oss",
        "CT": "https://www.ct.gov/doc/cwp/view.asp?a=1492&Q=270036",
        "DE": "https://www.doc.delaware.gov/views/offendersearch.shtml",
        "FL": "https://fdc.myflorida.com/OffenderSearch/",
        "GA": "http://www.dcor.state.ga.us/GDC/OffenderQuery/jsp/OffQryForm.jsp",
        "HI": "https://dps.hawaii.gov/about/divisions/corrections/",
        "ID": "https://www.idoc.idaho.gov/content/prisons/offender_search",
        "IL": "https://www.idoc.state.il.us/subsections/search/default.asp",
        "IN": "https://www.in.gov/idoc/2376.htm",
        "IA": "https://www.doc.state.ia.us/OffenderInfo",
        "KS": "https://www.doc.ks.gov/kasper",
        "KY": "https://corrections.ky.gov/kool/",
        "LA": "https://doc.louisiana.gov/imprisoned-person-locator/",
        "ME": "https://www.maine.gov/corrections/adult/victim-services/offender-search",
        "MD": "https://www.dpscs.state.md.us/inmate/",
        "MA": "https://www.mass.gov/service-details/inmate-search",
        "MI": "https://mdocweb.state.mi.us/OTIS2/otis2.aspx",
        "MN": "https://coms.doc.state.mn.us/",
        "MS": "https://www.mdoc.ms.gov/Inmate-Info/Pages/Inmate-Search.aspx",
        "MO": "https://doc.mo.gov/offender-search",
        "MT": "https://www.mtcorrections.org/",
        "NE": "https://dcs-inmatesearch.ne.gov/",
        "NV": "https://ofdsearch.doc.nv.gov/",
        "NH": "https://www.nh.gov/nhdoc/",
        "NJ": "https://www20.state.nj.us/DOC_Inmate/inmatesearch",
        "NM": "https://cd.nm.gov/about-us/inmate-lookup/",
        "NY": "http://nysdoccslookup.doccs.ny.gov/",
        "NC": "https://webapps.doc.state.nc.us/opi/offendersearch.do",
        "ND": "https://www.docr.nd.gov/offenderlkup/offenders.asp",
        "OH": "https://appgateway.drc.ohio.gov/OffenderSearch",
        "OK": "https://okoffender.doc.ok.gov/",
        "OR": "https://www.oregon.gov/doc/find-an-inmate/pages/default.aspx",
        "PA": "https://inmatelocator.cor.pa.gov/",
        "RI": "https://www.doc.ri.gov/adult-offender-info/",
        "SC": "https://public.doc.state.sc.us/scdc-public/",
        "SD": "https://doc.sd.gov/adult/lookup/",
        "TN": "https://apps.tn.gov/foil-app/search.jsp",
        "TX": "https://offender.tdcj.texas.gov/OffenderSearch/",
        "UT": "https://corrections.utah.gov/offender-search/",
        "VT": "https://doc.vermont.gov/",
        "VA": "https://vadoc.virginia.gov/offenders/locator/",
        "WA": "https://www.doc.wa.gov/information/inmate-search/default.aspx",
        "WV": "https://dcr.wv.gov/resources/Pages/Incarcerated-Individual-Search.aspx",
        "WI": "https://widocoffenders.wi.gov/",
        "WY": "https://corrections.wyo.gov/",
    }

    def __init__(self):
        """Initialize criminal records scraper"""
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {"User-Agent": "DataGod/1.0 (Public Records Research)"}
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse various date formats"""
        if not date_str:
            return None
        try:
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d-%b-%Y", "%B %d, %Y"]:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def get_state_doc_url(self, state: str) -> Optional[str]:
        """
        Get state DOC inmate search URL

        Args:
            state: Two-letter state code

        Returns:
            URL for state DOC search or None
        """
        return self.STATE_DOC_URLS.get(state.upper())

    def get_state_sex_offender_registry_url(self, state: str) -> str:
        """
        Get state sex offender registry URL

        Args:
            state: Two-letter state code

        Returns:
            URL for state registry (via NSOPW redirect)
        """
        return f"https://www.nsopw.gov/en/Search/Results?state={state}"

    async def search_sex_offenders_nsopw(
        self,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        limit: int = 100,
    ) -> List[SexOffender]:
        """
        Search National Sex Offender Public Website (NSOPW)

        Note: NSOPW redirects to state registries. This provides
        a unified search interface.

        Args:
            last_name: Last name
            first_name: First name
            city: City
            state: State code
            zip_code: ZIP code
            limit: Maximum results

        Returns:
            List of sex offender records
        """
        results = []

        # NSOPW requires specific state searches
        # In production, this would make requests to state registry APIs
        logger.info(f"Searching NSOPW for {last_name}, {first_name} in {state}")

        return results

    async def search_state_inmates(
        self,
        state: str,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
        inmate_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Inmate]:
        """
        Search state DOC inmate database

        Args:
            state: Two-letter state code
            last_name: Last name
            first_name: First name
            inmate_id: Inmate/offender ID number
            limit: Maximum results

        Returns:
            List of inmate records
        """
        results = []

        doc_url = self.get_state_doc_url(state)
        if not doc_url:
            logger.warning(f"No DOC URL found for state: {state}")
            return results

        logger.info(f"Searching {state} DOC for {last_name}, {first_name}")

        # In production, this would scrape state DOC websites
        # Each state has different formats

        return results

    async def search_federal_inmates(
        self,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
        register_number: Optional[str] = None,
        limit: int = 100,
    ) -> List[Inmate]:
        """
        Search Federal Bureau of Prisons inmate locator

        URL: https://www.bop.gov/inmateloc/

        Args:
            last_name: Last name
            first_name: First name
            register_number: BOP register number
            limit: Maximum results

        Returns:
            List of federal inmate records
        """
        results = []

        logger.info(f"Searching Federal BOP for {last_name}, {first_name}")

        # In production, this would query BOP inmate locator

        return results

    async def search_county_jail(
        self,
        state: str,
        county: str,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Inmate]:
        """
        Search county jail inmate roster

        Note: Not all counties publish online rosters.

        Args:
            state: State code
            county: County name
            last_name: Last name
            first_name: First name
            limit: Maximum results

        Returns:
            List of jail inmate records
        """
        results = []

        logger.info(f"Searching {county} County, {state} jail roster")

        # Would need to scrape individual county sheriff websites
        # Highly variable in format and availability

        return results

    async def search_fbi_most_wanted(
        self, category: Optional[str] = None, limit: int = 50
    ) -> List[MostWanted]:
        """
        Search FBI Most Wanted list

        Categories: ten-most-wanted, fugitives, terrorism, kidnappings,
                   missing-persons, parental-kidnappings, violent-crime

        Args:
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of most wanted records
        """
        results = []

        # FBI has a public API at api.fbi.gov
        logger.info(f"Searching FBI Most Wanted: {category or 'all'}")

        return results

    async def search_us_marshals_fugitives(self, limit: int = 50) -> List[MostWanted]:
        """
        Search US Marshals most wanted fugitives

        Args:
            limit: Maximum results

        Returns:
            List of fugitive records
        """
        results = []

        logger.info("Searching US Marshals fugitive list")

        return results

    async def search_state_most_wanted(
        self, state: str, limit: int = 50
    ) -> List[MostWanted]:
        """
        Search state most wanted list

        Args:
            state: Two-letter state code
            limit: Maximum results

        Returns:
            List of state most wanted records
        """
        results = []

        logger.info(f"Searching {state} most wanted")

        # Each state has different most wanted portals

        return results

    async def search_warrants(
        self,
        state: str,
        county: Optional[str] = None,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Warrant]:
        """
        Search active warrants

        Note: Warrant databases are not uniformly public.
        Availability varies by jurisdiction.

        Args:
            state: State code
            county: Optional county
            last_name: Last name
            first_name: First name
            limit: Maximum results

        Returns:
            List of warrant records
        """
        results = []

        logger.info(f"Searching warrants in {state}, {county or 'statewide'}")

        return results

    def get_all_state_resources(self, state: str) -> Dict[str, str]:
        """
        Get all criminal record resources for a state

        Args:
            state: Two-letter state code

        Returns:
            Dictionary of resource URLs
        """
        return {
            "doc_inmate_search": self.get_state_doc_url(state),
            "sex_offender_registry": self.get_state_sex_offender_registry_url(state),
            "nsopw_search": f"https://www.nsopw.gov/en/Search/Results?state={state}",
        }


# Convenience functions


def get_state_doc_url(state: str) -> Optional[str]:
    """Get state DOC inmate search URL"""
    scraper = CriminalRecordsScraper()
    return scraper.get_state_doc_url(state)


def get_state_resources(state: str) -> Dict[str, str]:
    """Get all criminal record resources for state"""
    scraper = CriminalRecordsScraper()
    return scraper.get_all_state_resources(state)


def search_sex_offenders_sync(
    last_name: Optional[str] = None, state: Optional[str] = None, limit: int = 100
) -> List[SexOffender]:
    """Synchronous sex offender search"""

    async def _search():
        scraper = CriminalRecordsScraper()
        try:
            return await scraper.search_sex_offenders_nsopw(
                last_name=last_name, state=state, limit=limit
            )
        finally:
            await scraper.close()

    return asyncio.run(_search())


def search_inmates_sync(
    state: str,
    last_name: Optional[str] = None,
    first_name: Optional[str] = None,
    limit: int = 100,
) -> List[Inmate]:
    """Synchronous inmate search"""

    async def _search():
        scraper = CriminalRecordsScraper()
        try:
            return await scraper.search_state_inmates(
                state=state, last_name=last_name, first_name=first_name, limit=limit
            )
        finally:
            await scraper.close()

    return asyncio.run(_search())
