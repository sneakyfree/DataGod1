"""
Transportation Records Scraper - CDL holders, vehicle registrations, driving records.

Free Public Sources:
- FMCSA: Motor carrier safety data (already integrated)
- NHTSA: Vehicle safety, recalls, complaints
- State DMV lookup databases
- CDL verification services
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp


class VehicleType(Enum):
    """Vehicle types."""

    PASSENGER = "passenger"
    TRUCK = "truck"
    MOTORCYCLE = "motorcycle"
    TRAILER = "trailer"
    BUS = "bus"
    RV = "rv"
    OTHER = "other"


class RecallStatus(Enum):
    """Vehicle recall status."""

    OPEN = "open"
    CLOSED = "closed"
    INCOMPLETE = "incomplete"


class CDLClass(Enum):
    """Commercial driver's license classes."""

    CLASS_A = "A"  # Combination vehicles 26,001+ lbs
    CLASS_B = "B"  # Single vehicles 26,001+ lbs
    CLASS_C = "C"  # Vehicles for 16+ passengers or hazmat


class CDLEndorsement(Enum):
    """CDL endorsement types."""

    H = "H"  # Hazardous Materials
    N = "N"  # Tank Vehicle
    P = "P"  # Passenger
    S = "S"  # School Bus
    T = "T"  # Double/Triple Trailers
    X = "X"  # Tank + Hazmat


@dataclass
class VehicleRecall:
    """NHTSA vehicle recall record."""

    recall_id: str
    campaign_number: str
    manufacturer: str
    subject: Optional[str] = None
    component: Optional[str] = None
    summary: Optional[str] = None
    consequence: Optional[str] = None
    remedy: Optional[str] = None
    notes: Optional[str] = None
    recall_date: Optional[datetime] = None
    report_received_date: Optional[datetime] = None
    potentially_affected: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    model_year: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VehicleComplaint:
    """NHTSA vehicle complaint record."""

    complaint_id: str
    manufacturer: str
    make: str
    model: str
    model_year: Optional[str] = None
    component: Optional[str] = None
    summary: Optional[str] = None
    crash: Optional[bool] = None
    fire: Optional[bool] = None
    injuries: int = 0
    deaths: int = 0
    date_added: Optional[datetime] = None
    date_of_incident: Optional[datetime] = None
    vin: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VehicleSafetyRating:
    """NHTSA vehicle safety rating."""

    vehicle_id: str
    make: str
    model: str
    model_year: str
    overall_rating: Optional[int] = None  # 1-5 stars
    frontal_crash_rating: Optional[int] = None
    side_crash_rating: Optional[int] = None
    rollover_rating: Optional[int] = None
    frontal_crash_driver: Optional[int] = None
    frontal_crash_passenger: Optional[int] = None
    side_crash_driver: Optional[int] = None
    side_crash_passenger: Optional[int] = None
    side_pole_rating: Optional[int] = None
    complaints_count: int = 0
    recalls_count: int = 0
    investigation_count: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VINDecodeResult:
    """VIN decode result."""

    vin: str
    make: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    model_year: Optional[str] = None
    body_class: Optional[str] = None
    vehicle_type: Optional[str] = None
    drive_type: Optional[str] = None
    fuel_type: Optional[str] = None
    engine_cylinders: Optional[int] = None
    engine_displacement: Optional[float] = None
    engine_hp: Optional[float] = None
    transmission: Optional[str] = None
    doors: Optional[int] = None
    plant_city: Optional[str] = None
    plant_state: Optional[str] = None
    plant_country: Optional[str] = None
    series: Optional[str] = None
    trim: Optional[str] = None
    gvwr: Optional[str] = None  # Gross Vehicle Weight Rating
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CDLHolder:
    """Commercial driver's license holder record."""

    license_number: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    state: Optional[str] = None
    license_class: Optional[str] = None
    endorsements: List[str] = field(default_factory=list)
    restrictions: List[str] = field(default_factory=list)
    status: Optional[str] = None
    expiration_date: Optional[datetime] = None
    issue_date: Optional[datetime] = None
    medical_cert_status: Optional[str] = None
    medical_cert_expiration: Optional[datetime] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


# State DMV lookup URLs
STATE_DMV_URLS = {
    "AL": {
        "main": "https://www.alea.gov/dps/driver-license/driver-license-division",
        "title_search": None,
    },
    "AK": {"main": "https://doa.alaska.gov/dmv/", "title_search": None},
    "AZ": {
        "main": "https://azdot.gov/mvd",
        "service_arizona": "https://servicearizona.com/",
    },
    "AR": {
        "main": "https://www.dfa.arkansas.gov/driver-services/",
        "title_search": None,
    },
    "CA": {
        "main": "https://www.dmv.ca.gov/",
        "vehicle_search": "https://www.dmv.ca.gov/portal/vehicle-industry-services/",
    },
    "CO": {"main": "https://dmv.colorado.gov/", "title_search": None},
    "CT": {"main": "https://portal.ct.gov/DMV", "title_search": None},
    "DE": {"main": "https://www.dmv.de.gov/", "title_search": None},
    "DC": {"main": "https://dmv.dc.gov/", "title_search": None},
    "FL": {
        "main": "https://www.flhsmv.gov/",
        "driver_check": "https://services.flhsmv.gov/DLCheck/",
    },
    "GA": {"main": "https://dds.georgia.gov/", "title_search": None},
    "HI": {
        "main": "https://hidot.hawaii.gov/highways/library/motor-vehicle/",
        "title_search": None,
    },
    "ID": {"main": "https://itd.idaho.gov/dmv/", "title_search": None},
    "IL": {"main": "https://www.ilsos.gov/departments/drivers/", "title_search": None},
    "IN": {"main": "https://www.in.gov/bmv/", "title_search": None},
    "IA": {"main": "https://iowadot.gov/mvd/", "title_search": None},
    "KS": {"main": "https://www.ksrevenue.gov/dovindex.html", "title_search": None},
    "KY": {"main": "https://drive.ky.gov/", "title_search": None},
    "LA": {"main": "https://expresslane.org/", "title_search": None},
    "ME": {"main": "https://www.maine.gov/sos/bmv/", "title_search": None},
    "MD": {"main": "https://mva.maryland.gov/", "title_search": None},
    "MA": {
        "main": "https://www.mass.gov/orgs/registry-of-motor-vehicles",
        "title_search": None,
    },
    "MI": {"main": "https://www.michigan.gov/sos/", "title_search": None},
    "MN": {"main": "https://dps.mn.gov/divisions/dvs/", "title_search": None},
    "MS": {"main": "https://www.dps.state.ms.us/", "title_search": None},
    "MO": {"main": "https://dor.mo.gov/motor-vehicle/", "title_search": None},
    "MT": {"main": "https://dojmt.gov/driving/", "title_search": None},
    "NE": {"main": "https://dmv.nebraska.gov/", "title_search": None},
    "NV": {"main": "https://dmv.nv.gov/", "title_search": None},
    "NH": {"main": "https://www.nh.gov/safety/divisions/dmv/", "title_search": None},
    "NJ": {"main": "https://www.nj.gov/mvc/", "title_search": None},
    "NM": {"main": "https://www.mvd.newmexico.gov/", "title_search": None},
    "NY": {"main": "https://dmv.ny.gov/", "title_search": None},
    "NC": {"main": "https://www.ncdot.gov/dmv/", "title_search": None},
    "ND": {
        "main": "https://www.dot.nd.gov/divisions/driverslicense/",
        "title_search": None,
    },
    "OH": {
        "main": "https://bmv.ohio.gov/",
        "title_search": "https://bmv.ohio.gov/links/bmv-title.aspx",
    },
    "OK": {"main": "https://oklahoma.gov/dps.html", "title_search": None},
    "OR": {"main": "https://www.oregon.gov/odot/dmv/", "title_search": None},
    "PA": {"main": "https://www.dmv.pa.gov/", "title_search": None},
    "RI": {"main": "https://dmv.ri.gov/", "title_search": None},
    "SC": {"main": "https://www.scdmvonline.com/", "title_search": None},
    "SD": {"main": "https://dps.sd.gov/driver-licensing/", "title_search": None},
    "TN": {
        "main": "https://www.tn.gov/safety/driver-services.html",
        "title_search": None,
    },
    "TX": {
        "main": "https://www.txdmv.gov/",
        "title_check": "https://www.txdmv.gov/motorists/buying-or-selling-a-vehicle/title-check",
    },
    "UT": {"main": "https://dmv.utah.gov/", "title_search": None},
    "VT": {"main": "https://dmv.vermont.gov/", "title_search": None},
    "VA": {"main": "https://www.dmv.virginia.gov/", "title_search": None},
    "WA": {"main": "https://www.dol.wa.gov/", "title_search": None},
    "WV": {"main": "https://transportation.wv.gov/DMV/", "title_search": None},
    "WI": {
        "main": "https://wisconsindot.gov/Pages/dmv/default.aspx",
        "title_search": None,
    },
    "WY": {
        "main": "https://www.dot.state.wy.us/home/driver_license_records.html",
        "title_search": None,
    },
}

# CDL verification resources
CDL_VERIFICATION_RESOURCES = {
    "cdlis": "https://www.aamva.org/technology/systems/CDLIS-driver-history",
    "fmcsa_portal": "https://ai.fmcsa.dot.gov/SMS/",
    "medical_cert": "https://www.fmcsa.dot.gov/registration/commercial-drivers-license/national-registry",
}


class TransportationRecordsScraper:
    """
    Scraper for transportation and vehicle records from NHTSA and state DMVs.

    Free Public APIs:
    - NHTSA Vehicle API: VIN decoding, recalls, complaints, safety ratings
    - State DMV databases (varies by state)
    - FMCSA data (see fmcsa_api.py)
    """

    # NHTSA API endpoints
    NHTSA_API_BASE = "https://api.nhtsa.gov"
    NHTSA_RECALLS = f"{NHTSA_API_BASE}/recalls/recallsByVehicle"
    NHTSA_COMPLAINTS = f"{NHTSA_API_BASE}/complaints/complaintsByVehicle"
    NHTSA_RATINGS = f"{NHTSA_API_BASE}/SafetyRatings"
    NHTSA_VIN_DECODE = "https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the transportation records scraper."""
        self.session = session
        self._owns_session = session is None

    async def __aenter__(self):
        if self._owns_session:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_session and self.session:
            await self.session.close()

    async def _ensure_session(self):
        """Ensure we have an active session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            self._owns_session = True

    # ==================== VIN Decoding ====================

    async def decode_vin(
        self, vin: str, model_year: Optional[int] = None
    ) -> Optional[VINDecodeResult]:
        """
        Decode a VIN using NHTSA vPIC API.

        Free API - no registration required.
        """
        await self._ensure_session()

        try:
            url = f"{self.NHTSA_VIN_DECODE}/{vin}"
            params = {"format": "json"}
            if model_year:
                params["modelyear"] = model_year

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    results = data.get("Results", [])
                    if results:
                        item = results[0]

                        # Parse engine displacement
                        displacement = None
                        if item.get("DisplacementL"):
                            try:
                                displacement = float(item["DisplacementL"])
                            except (ValueError, TypeError):
                                pass

                        # Parse horsepower
                        hp = None
                        if item.get("EngineHP"):
                            try:
                                hp = float(item["EngineHP"])
                            except (ValueError, TypeError):
                                pass

                        return VINDecodeResult(
                            vin=vin,
                            make=item.get("Make"),
                            manufacturer=item.get("Manufacturer"),
                            model=item.get("Model"),
                            model_year=item.get("ModelYear"),
                            body_class=item.get("BodyClass"),
                            vehicle_type=item.get("VehicleType"),
                            drive_type=item.get("DriveType"),
                            fuel_type=item.get("FuelTypePrimary"),
                            engine_cylinders=(
                                int(item.get("EngineCylinders", 0) or 0)
                                if item.get("EngineCylinders")
                                else None
                            ),
                            engine_displacement=displacement,
                            engine_hp=hp,
                            transmission=item.get("TransmissionStyle"),
                            doors=(
                                int(item.get("Doors", 0) or 0)
                                if item.get("Doors")
                                else None
                            ),
                            plant_city=item.get("PlantCity"),
                            plant_state=item.get("PlantState"),
                            plant_country=item.get("PlantCountry"),
                            series=item.get("Series"),
                            trim=item.get("Trim"),
                            gvwr=item.get("GVWR"),
                            raw_data=item,
                        )

        except aiohttp.ClientError:
            pass

        return None

    # ==================== Vehicle Recalls ====================

    async def search_recalls(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        model_year: Optional[int] = None,
        campaign_number: Optional[str] = None,
        limit: int = 100,
    ) -> List[VehicleRecall]:
        """
        Search vehicle recalls using NHTSA API.

        Free API - no registration required.
        """
        await self._ensure_session()

        results = []

        try:
            # Build URL based on parameters
            if campaign_number:
                url = f"{self.NHTSA_API_BASE}/recalls/campaignNumber?campaignNumber={campaign_number}"
            elif make and model and model_year:
                url = f"{self.NHTSA_RECALLS}?make={make}&model={model}&modelYear={model_year}"
            elif make and model_year:
                url = f"{self.NHTSA_API_BASE}/recalls/recallsByMakeYear?make={make}&modelYear={model_year}"
            elif make:
                url = f"{self.NHTSA_API_BASE}/recalls/recallsByMake?make={make}"
            else:
                return results

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("results", [])[:limit]:
                        try:
                            recall = VehicleRecall(
                                recall_id=str(item.get("NHTSACampaignNumber", "")),
                                campaign_number=item.get("NHTSACampaignNumber", ""),
                                manufacturer=item.get("Manufacturer", ""),
                                make=item.get("Make"),
                                model=item.get("Model"),
                                model_year=item.get("ModelYear"),
                                subject=item.get("Subject"),
                                component=item.get("Component"),
                                summary=item.get("Summary"),
                                consequence=item.get("Consequence"),
                                remedy=item.get("Remedy"),
                                notes=item.get("Notes"),
                                potentially_affected=(
                                    int(
                                        item.get("PotentialNumberofUnitsAffected", 0)
                                        or 0
                                    )
                                    if item.get("PotentialNumberofUnitsAffected")
                                    else None
                                ),
                                raw_data=item,
                            )

                            # Parse recall date
                            if item.get("ReportReceivedDate"):
                                try:
                                    recall.recall_date = datetime.strptime(
                                        item["ReportReceivedDate"][:10], "%d/%m/%Y"
                                    )
                                except (ValueError, TypeError):
                                    try:
                                        recall.recall_date = datetime.strptime(
                                            item["ReportReceivedDate"][:10], "%Y-%m-%d"
                                        )
                                    except (ValueError, TypeError):
                                        pass

                            results.append(recall)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    async def get_recalls_by_vin(self, vin: str) -> List[VehicleRecall]:
        """Get recalls for a specific VIN."""
        # First decode VIN to get make/model/year
        decoded = await self.decode_vin(vin)
        if decoded and decoded.make and decoded.model and decoded.model_year:
            return await self.search_recalls(
                make=decoded.make,
                model=decoded.model,
                model_year=int(decoded.model_year),
            )
        return []

    # ==================== Vehicle Complaints ====================

    async def search_complaints(
        self, make: str, model: str, model_year: Optional[int] = None, limit: int = 100
    ) -> List[VehicleComplaint]:
        """
        Search vehicle complaints using NHTSA API.

        Free API - no registration required.
        """
        await self._ensure_session()

        results = []

        try:
            if model_year:
                url = f"{self.NHTSA_COMPLAINTS}?make={make}&model={model}&modelYear={model_year}"
            else:
                url = f"{self.NHTSA_COMPLAINTS}?make={make}&model={model}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("results", [])[:limit]:
                        try:
                            complaint = VehicleComplaint(
                                complaint_id=str(item.get("odiNumber", "")),
                                manufacturer=item.get("manufacturer", ""),
                                make=item.get("make", ""),
                                model=item.get("model", ""),
                                model_year=item.get("modelYear"),
                                component=item.get("components"),
                                summary=item.get("summary"),
                                crash=item.get("crash") == "Y",
                                fire=item.get("fire") == "Y",
                                injuries=int(item.get("numberOfInjuries", 0) or 0),
                                deaths=int(item.get("numberOfDeaths", 0) or 0),
                                vin=item.get("vin"),
                                raw_data=item,
                            )

                            # Parse dates
                            if item.get("dateComplaintFiled"):
                                try:
                                    complaint.date_added = datetime.strptime(
                                        item["dateComplaintFiled"][:10], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            if item.get("dateOfIncident"):
                                try:
                                    complaint.date_of_incident = datetime.strptime(
                                        item["dateOfIncident"][:10], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            results.append(complaint)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    # ==================== Safety Ratings ====================

    async def get_safety_ratings(
        self, make: str, model: str, model_year: int
    ) -> Optional[VehicleSafetyRating]:
        """
        Get vehicle safety ratings from NHTSA 5-Star Safety Ratings program.

        Free API - no registration required.
        """
        await self._ensure_session()

        try:
            # First get vehicle ID
            url = (
                f"{self.NHTSA_RATINGS}/modelyear/{model_year}/make/{make}/model/{model}"
            )
            params = {"format": "json"}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    results = data.get("Results", [])
                    if results:
                        # Get first result (most relevant)
                        item = results[0]
                        vehicle_id = item.get("VehicleId")

                        # Get detailed ratings
                        if vehicle_id:
                            detail_url = f"{self.NHTSA_RATINGS}/VehicleId/{vehicle_id}"
                            async with self.session.get(
                                detail_url, params=params
                            ) as detail_response:
                                if detail_response.status == 200:
                                    detail_data = await detail_response.json()
                                    detail_results = detail_data.get("Results", [])
                                    if detail_results:
                                        detail = detail_results[0]

                                        return VehicleSafetyRating(
                                            vehicle_id=str(vehicle_id),
                                            make=make,
                                            model=model,
                                            model_year=str(model_year),
                                            overall_rating=(
                                                int(detail.get("OverallRating", 0) or 0)
                                                if detail.get("OverallRating")
                                                and detail.get("OverallRating")
                                                != "Not Rated"
                                                else None
                                            ),
                                            frontal_crash_rating=(
                                                int(
                                                    detail.get(
                                                        "OverallFrontCrashRating", 0
                                                    )
                                                    or 0
                                                )
                                                if detail.get("OverallFrontCrashRating")
                                                and detail.get(
                                                    "OverallFrontCrashRating"
                                                )
                                                != "Not Rated"
                                                else None
                                            ),
                                            side_crash_rating=(
                                                int(
                                                    detail.get(
                                                        "OverallSideCrashRating", 0
                                                    )
                                                    or 0
                                                )
                                                if detail.get("OverallSideCrashRating")
                                                and detail.get("OverallSideCrashRating")
                                                != "Not Rated"
                                                else None
                                            ),
                                            rollover_rating=(
                                                int(
                                                    detail.get("RolloverRating", 0) or 0
                                                )
                                                if detail.get("RolloverRating")
                                                and detail.get("RolloverRating")
                                                != "Not Rated"
                                                else None
                                            ),
                                            complaints_count=int(
                                                detail.get("ComplaintsCount", 0) or 0
                                            ),
                                            recalls_count=int(
                                                detail.get("RecallsCount", 0) or 0
                                            ),
                                            investigation_count=int(
                                                detail.get("InvestigationCount", 0) or 0
                                            ),
                                            raw_data=detail,
                                        )

        except aiohttp.ClientError:
            pass

        return None

    # ==================== State DMV Methods ====================

    def get_state_dmv_urls(self, state: str) -> Optional[Dict[str, str]]:
        """Get DMV URLs for a state."""
        return STATE_DMV_URLS.get(state.upper())

    def get_all_dmv_urls(self) -> Dict[str, Dict[str, str]]:
        """Get all state DMV URLs."""
        return STATE_DMV_URLS.copy()

    def get_cdl_verification_resources(self) -> Dict[str, str]:
        """Get CDL verification resources."""
        return CDL_VERIFICATION_RESOURCES.copy()

    # ==================== Helper Methods ====================

    def get_nhtsa_resources(self) -> Dict[str, str]:
        """Get useful NHTSA resources."""
        return {
            "vehicle_api": "https://vpic.nhtsa.dot.gov/api/",
            "recalls_search": "https://www.nhtsa.gov/recalls",
            "complaints_search": "https://www.nhtsa.gov/vehicle-safety-issues",
            "safety_ratings": "https://www.nhtsa.gov/ratings",
            "investigations": "https://www.nhtsa.gov/vehicle-safety-issues",
        }

    def get_vehicle_history_resources(self) -> Dict[str, str]:
        """Get vehicle history resources (some paid)."""
        return {
            "nmvtis": "https://www.vehiclehistory.gov/",  # National Motor Vehicle Title Information System
            "carfax": "https://www.carfax.com/",  # Paid
            "autocheck": "https://www.autocheck.com/",  # Paid
            "nicb_vincheck": "https://www.nicb.org/vincheck",  # Free - theft/salvage check
        }


# Synchronous wrapper functions
def decode_vin_sync(
    vin: str, model_year: Optional[int] = None
) -> Optional[VINDecodeResult]:
    """Synchronous wrapper for VIN decoding."""

    async def _decode():
        async with TransportationRecordsScraper() as scraper:
            return await scraper.decode_vin(vin, model_year)

    return asyncio.run(_decode())


def search_recalls_sync(
    make: Optional[str] = None,
    model: Optional[str] = None,
    model_year: Optional[int] = None,
    **kwargs,
) -> List[VehicleRecall]:
    """Synchronous wrapper for recall search."""

    async def _search():
        async with TransportationRecordsScraper() as scraper:
            return await scraper.search_recalls(
                make=make, model=model, model_year=model_year, **kwargs
            )

    return asyncio.run(_search())


def search_complaints_sync(
    make: str, model: str, model_year: Optional[int] = None, **kwargs
) -> List[VehicleComplaint]:
    """Synchronous wrapper for complaint search."""

    async def _search():
        async with TransportationRecordsScraper() as scraper:
            return await scraper.search_complaints(
                make=make, model=model, model_year=model_year, **kwargs
            )

    return asyncio.run(_search())


def get_safety_ratings_sync(
    make: str, model: str, model_year: int
) -> Optional[VehicleSafetyRating]:
    """Synchronous wrapper for safety ratings."""

    async def _get():
        async with TransportationRecordsScraper() as scraper:
            return await scraper.get_safety_ratings(make, model, model_year)

    return asyncio.run(_get())


# Export all
__all__ = [
    "TransportationRecordsScraper",
    "VehicleRecall",
    "VehicleComplaint",
    "VehicleSafetyRating",
    "VINDecodeResult",
    "CDLHolder",
    "VehicleType",
    "RecallStatus",
    "CDLClass",
    "CDLEndorsement",
    "STATE_DMV_URLS",
    "CDL_VERIFICATION_RESOURCES",
    "decode_vin_sync",
    "search_recalls_sync",
    "search_complaints_sync",
    "get_safety_ratings_sync",
]
