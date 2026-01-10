"""
Asset Records Scraper

Free public asset records sources:
- FAA Aircraft Registry (registry.faa.gov)
- USCG Vessel Documentation (uscg.mil)
- State boat/watercraft registrations
- UCC filings (collateral on assets)
- State vehicle title liens (limited)

Free Sources:
- FAA N-Number Registry - Aircraft ownership
- FAA Airmen Certification - Pilot licenses
- USCG Documentation - Documented vessels
- State DMV (limited public access)
- County UCC filings
"""

import asyncio
import aiohttp
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AircraftCategory(Enum):
    """FAA aircraft categories"""
    LAND = "Land"
    SEA = "Sea"
    AMPHIBIAN = "Amphibian"
    HELICOPTER = "Helicopter"
    GLIDER = "Glider"
    BALLOON = "Balloon"
    POWERED_LIFT = "Powered Lift"
    WEIGHT_SHIFT = "Weight-Shift-Control"
    POWERED_PARACHUTE = "Powered Parachute"


class AircraftType(Enum):
    """FAA aircraft type classifications"""
    FIXED_WING_SINGLE = "Fixed Wing Single-Engine"
    FIXED_WING_MULTI = "Fixed Wing Multi-Engine"
    ROTORCRAFT = "Rotorcraft"
    GLIDER = "Glider"
    LIGHTER_THAN_AIR = "Lighter Than Air"
    POWERED_PARACHUTE = "Powered Parachute"
    WEIGHT_SHIFT = "Weight-Shift-Control"


class RegistrationStatus(Enum):
    """FAA registration status"""
    VALID = "Valid"
    EXPIRED = "Expired"
    CANCELLED = "Cancelled"
    REVOKED = "Revoked"
    PENDING = "Pending"
    RESERVED = "Reserved"


class VesselType(Enum):
    """USCG vessel types"""
    RECREATIONAL = "Recreational"
    COMMERCIAL = "Commercial"
    FISHING = "Fishing"
    PASSENGER = "Passenger"
    FREIGHT = "Freight"
    TOWING = "Towing"
    OFFSHORE_SUPPLY = "Offshore Supply"


class VesselService(Enum):
    """USCG vessel service types"""
    COASTWISE = "Coastwise"
    FISHERY = "Fishery"
    RECREATIONAL = "Recreational"
    REGISTRY = "Registry"


@dataclass
class Aircraft:
    """FAA aircraft registration record"""
    n_number: str  # Registration number (N12345)
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    year_manufactured: Optional[int] = None
    aircraft_type: Optional[AircraftType] = None
    category: Optional[AircraftCategory] = None
    engine_type: Optional[str] = None
    engine_count: Optional[int] = None
    seats: Optional[int] = None
    max_weight: Optional[int] = None  # in lbs
    status: Optional[RegistrationStatus] = None
    registration_date: Optional[date] = None
    expiration_date: Optional[date] = None
    last_action_date: Optional[date] = None
    certificate_issue_date: Optional[date] = None
    # Owner info
    owner_name: Optional[str] = None
    owner_type: Optional[str] = None  # Individual, Corporation, etc.
    owner_address: Optional[str] = None
    owner_city: Optional[str] = None
    owner_state: Optional[str] = None
    owner_zip: Optional[str] = None
    owner_country: Optional[str] = None
    # Fractional ownership
    fractional: bool = False
    co_owners: List[str] = field(default_factory=list)


@dataclass
class Pilot:
    """FAA airmen certification record"""
    certificate_number: Optional[str] = None
    name: str = ""
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    certificate_type: Optional[str] = None  # ATP, Commercial, Private, Student
    ratings: List[str] = field(default_factory=list)
    certificate_date: Optional[date] = None
    expiration_date: Optional[date] = None
    medical_class: Optional[str] = None
    medical_date: Optional[date] = None


@dataclass
class Vessel:
    """USCG documented vessel record"""
    documentation_number: str
    vessel_name: Optional[str] = None
    hailing_port: Optional[str] = None
    hull_number: Optional[str] = None
    build_year: Optional[int] = None
    builder: Optional[str] = None
    gross_tons: Optional[float] = None
    net_tons: Optional[float] = None
    length: Optional[float] = None  # in feet
    breadth: Optional[float] = None
    depth: Optional[float] = None
    vessel_type: Optional[VesselType] = None
    service: Optional[VesselService] = None
    hull_material: Optional[str] = None
    propulsion: Optional[str] = None
    # Owner info
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None
    owner_city: Optional[str] = None
    owner_state: Optional[str] = None
    owner_country: Optional[str] = None
    managing_owner: Optional[str] = None
    # Status
    status: Optional[str] = None
    endorsements: List[str] = field(default_factory=list)


@dataclass
class StateBoatRegistration:
    """State boat registration record"""
    registration_number: str
    state: str
    vessel_name: Optional[str] = None
    hull_id: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    length: Optional[float] = None
    hull_material: Optional[str] = None
    propulsion: Optional[str] = None
    use: Optional[str] = None  # Pleasure, Commercial
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None
    owner_city: Optional[str] = None
    registration_date: Optional[date] = None
    expiration_date: Optional[date] = None


class AssetRecordsScraper:
    """
    Scraper for free public asset records

    Sources:
    - FAA Aircraft Registry
    - FAA Airmen Certification Database
    - USCG Vessel Documentation Center
    - State boat registration (varies)
    """

    FAA_REGISTRY_URL = "https://registry.faa.gov/AircraftInquiry"
    FAA_AIRMEN_URL = "https://amsrvs.registry.faa.gov/airmeninquiry"
    USCG_VESSEL_URL = "https://www.st.nmfs.noaa.gov/st1/CoastGuard/VesselByName.html"

    # State boat registration URLs
    STATE_BOAT_URLS = {
        "AL": "https://www.alea.gov/boat-registration",
        "AK": "https://dnr.alaska.gov/parks/boating/",
        "AZ": "https://www.azgfd.com/boating/",
        "CA": "https://www.dmv.ca.gov/portal/vehicle-registration/new-registration/register-a-vessel/",
        "CO": "https://cpw.state.co.us/thingstodo/Pages/BoatRegistration.aspx",
        "CT": "https://portal.ct.gov/DEEP/Boating/Boat-Registration",
        "FL": "https://www.flhsmv.gov/motor-vehicles-tags-titles/vessels/",
        "GA": "https://georgiawildlife.com/boating/registration",
        "IL": "https://www.dnr.illinois.gov/boating/Pages/BoatRegistration.aspx",
        "IN": "https://www.in.gov/bmv/vehicles-trailers-and-titles/buying-a-vehicle/boat-registration/",
        "MI": "https://www.michigan.gov/sos/vehicle/boat",
        "MN": "https://www.dnr.state.mn.us/licenses/watercraft/index.html",
        "NC": "https://www.ncwildlife.org/Boating/Registration",
        "NY": "https://parks.ny.gov/recreation/boating/registration.aspx",
        "OH": "https://odnr.gov/buy-and-apply/watercraft-registration",
        "PA": "https://www.fishandboat.com/Boat/BoatRegistration/",
        "SC": "https://www.dnr.sc.gov/boating/registration.html",
        "TX": "https://tpwd.texas.gov/fishboat/boat/owner/titles_and_registration/",
        "VA": "https://www.dgif.virginia.gov/boating/registration/",
        "WA": "https://www.dol.wa.gov/vehicles/vessel-registration.html",
        "WI": "https://dnr.wisconsin.gov/topic/Boat/registration"
    }

    def __init__(self):
        """Initialize asset records scraper"""
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "User-Agent": "DataGod/1.0 (Public Records Research)"
            }
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
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%d-%b-%Y"]:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    # FAA Aircraft Registry

    async def search_aircraft_by_n_number(
        self,
        n_number: str
    ) -> Optional[Aircraft]:
        """
        Search FAA registry by N-number

        Args:
            n_number: Aircraft N-number (e.g., "N12345")

        Returns:
            Aircraft record or None
        """
        # Remove N prefix if present
        n_number = n_number.upper().lstrip("N")

        logger.info(f"Searching FAA registry for N{n_number}")

        # In production, would query FAA registry
        # FAA provides downloadable database files at:
        # https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/releasable_aircraft_download

        return None

    async def search_aircraft_by_owner(
        self,
        owner_name: str,
        state: Optional[str] = None,
        limit: int = 100
    ) -> List[Aircraft]:
        """
        Search FAA registry by owner name

        Args:
            owner_name: Owner name (individual or organization)
            state: Optional state filter
            limit: Maximum results

        Returns:
            List of aircraft records
        """
        results = []

        logger.info(f"Searching FAA registry for owner: {owner_name}")

        # Would query FAA registry database

        return results

    async def search_aircraft_by_serial(
        self,
        serial_number: str
    ) -> Optional[Aircraft]:
        """
        Search FAA registry by serial number

        Args:
            serial_number: Manufacturer serial number

        Returns:
            Aircraft record or None
        """
        logger.info(f"Searching FAA registry for serial: {serial_number}")

        return None

    # FAA Airmen (Pilot) Database

    async def search_pilots(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        state: Optional[str] = None,
        certificate_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Pilot]:
        """
        Search FAA airmen certification database

        Args:
            last_name: Last name
            first_name: Optional first name
            state: Optional state filter
            certificate_type: Certificate type (ATP, Commercial, Private)
            limit: Maximum results

        Returns:
            List of pilot records
        """
        results = []

        logger.info(f"Searching FAA airmen database for {last_name}, {first_name}")

        # FAA provides releasable airmen database files

        return results

    # USCG Vessel Documentation

    async def search_vessels_by_name(
        self,
        vessel_name: str,
        hailing_port: Optional[str] = None,
        limit: int = 100
    ) -> List[Vessel]:
        """
        Search USCG documented vessels by name

        Args:
            vessel_name: Vessel name
            hailing_port: Optional hailing port
            limit: Maximum results

        Returns:
            List of vessel records
        """
        results = []

        logger.info(f"Searching USCG vessels for: {vessel_name}")

        # Would query USCG vessel documentation center

        return results

    async def search_vessels_by_owner(
        self,
        owner_name: str,
        state: Optional[str] = None,
        limit: int = 100
    ) -> List[Vessel]:
        """
        Search USCG documented vessels by owner

        Args:
            owner_name: Owner name
            state: Optional state filter
            limit: Maximum results

        Returns:
            List of vessel records
        """
        results = []

        logger.info(f"Searching USCG vessels for owner: {owner_name}")

        return results

    async def get_vessel_by_documentation_number(
        self,
        doc_number: str
    ) -> Optional[Vessel]:
        """
        Get vessel by USCG documentation number

        Args:
            doc_number: USCG documentation number

        Returns:
            Vessel record or None
        """
        logger.info(f"Getting USCG vessel: {doc_number}")

        return None

    # State Boat Registrations

    def get_state_boat_registration_url(self, state: str) -> Optional[str]:
        """
        Get state boat registration portal URL

        Args:
            state: Two-letter state code

        Returns:
            URL for state boat registration
        """
        return self.STATE_BOAT_URLS.get(state.upper())

    async def search_state_boats(
        self,
        state: str,
        registration_number: Optional[str] = None,
        owner_name: Optional[str] = None,
        hull_id: Optional[str] = None,
        limit: int = 100
    ) -> List[StateBoatRegistration]:
        """
        Search state boat registrations

        Note: Availability varies significantly by state.
        Many states don't provide online search.

        Args:
            state: State code
            registration_number: State registration number
            owner_name: Owner name
            hull_id: Hull identification number
            limit: Maximum results

        Returns:
            List of boat registration records
        """
        results = []

        registration_url = self.get_state_boat_registration_url(state)
        if not registration_url:
            logger.warning(f"No boat registration URL for state: {state}")
            return results

        logger.info(f"Searching {state} boat registrations")

        return results

    def get_all_asset_resources(self) -> Dict[str, str]:
        """
        Get all asset record resource URLs

        Returns:
            Dictionary of resource URLs
        """
        return {
            "faa_aircraft_registry": "https://registry.faa.gov/AircraftInquiry",
            "faa_airmen_inquiry": "https://amsrvs.registry.faa.gov/airmeninquiry",
            "faa_releasable_database": "https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/releasable_aircraft_download",
            "uscg_vessel_search": "https://www.st.nmfs.noaa.gov/st1/CoastGuard/VesselByName.html",
            "uscg_documentation_center": "https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/National-Vessel-Documentation-Center/"
        }


# Convenience functions

def get_faa_resources() -> Dict[str, str]:
    """Get FAA resource URLs"""
    return {
        "aircraft_registry": "https://registry.faa.gov/AircraftInquiry",
        "airmen_inquiry": "https://amsrvs.registry.faa.gov/airmeninquiry",
        "releasable_database": "https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/releasable_aircraft_download"
    }


def get_state_boat_url(state: str) -> Optional[str]:
    """Get state boat registration URL"""
    scraper = AssetRecordsScraper()
    return scraper.get_state_boat_registration_url(state)


def search_aircraft_sync(
    n_number: Optional[str] = None,
    owner_name: Optional[str] = None,
    limit: int = 100
) -> List[Aircraft]:
    """Synchronous aircraft search"""
    async def _search():
        scraper = AssetRecordsScraper()
        try:
            if n_number:
                result = await scraper.search_aircraft_by_n_number(n_number)
                return [result] if result else []
            elif owner_name:
                return await scraper.search_aircraft_by_owner(owner_name, limit=limit)
            return []
        finally:
            await scraper.close()

    return asyncio.run(_search())
