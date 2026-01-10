"""
FMCSA (Federal Motor Carrier Safety Administration) API Integration

Free public API providing access to:
- Motor carrier safety data (SAFER)
- Commercial driver's license (CDL) data
- Crash and inspection data
- Operating authority records
- Out-of-service violations
- Safety ratings

API Documentation: https://mobile.fmcsa.dot.gov/developer
Rate Limit: No formal limit for public queries
"""

import asyncio
import aiohttp
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CarrierOperationType(Enum):
    """Motor carrier operation types"""
    AUTHORIZED_FOR_HIRE = "A"
    EXEMPT_FOR_HIRE = "B"
    PRIVATE_PROPERTY = "C"
    PRIVATE_PASSENGERS_BUSINESS = "D"
    PRIVATE_PASSENGERS_NONBUSINESS = "E"
    MIGRANT = "F"
    US_MAIL = "G"
    FEDERAL_GOVERNMENT = "H"
    STATE_GOVERNMENT = "I"
    LOCAL_GOVERNMENT = "J"
    INDIAN_NATION = "K"


class CarrierType(Enum):
    """Type of carrier entity"""
    CARRIER = "CARRIER"
    SHIPPER = "SHIPPER"
    BROKER = "BROKER"
    FREIGHT_FORWARDER = "FREIGHT_FORWARDER"
    IEP = "IEP"  # Intermodal Equipment Provider


class SafetyRating(Enum):
    """FMCSA safety ratings"""
    SATISFACTORY = "Satisfactory"
    CONDITIONAL = "Conditional"
    UNSATISFACTORY = "Unsatisfactory"
    NOT_RATED = "Not Rated"


class OperatingStatus(Enum):
    """Carrier operating status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    OUT_OF_SERVICE = "OUT OF SERVICE"
    REVOKED = "REVOKED"


class InspectionType(Enum):
    """FMCSA inspection types"""
    DRIVER = "D"
    VEHICLE = "V"
    HAZMAT = "H"
    PASSENGER = "P"


class ViolationType(Enum):
    """FMCSA violation categories"""
    UNSAFE_DRIVING = "Unsafe Driving"
    HOS_COMPLIANCE = "HOS Compliance"
    DRIVER_FITNESS = "Driver Fitness"
    CONTROLLED_SUBSTANCES = "Controlled Substances/Alcohol"
    VEHICLE_MAINTENANCE = "Vehicle Maintenance"
    HAZMAT_COMPLIANCE = "Hazmat Compliance"
    CRASH_INDICATOR = "Crash Indicator"


@dataclass
class Carrier:
    """Motor carrier entity"""
    dot_number: str
    legal_name: str
    dba_name: Optional[str] = None
    carrier_type: Optional[CarrierType] = None
    operating_status: Optional[OperatingStatus] = None
    safety_rating: Optional[SafetyRating] = None
    safety_rating_date: Optional[date] = None
    physical_address: Optional[str] = None
    physical_city: Optional[str] = None
    physical_state: Optional[str] = None
    physical_zip: Optional[str] = None
    mailing_address: Optional[str] = None
    mailing_city: Optional[str] = None
    mailing_state: Optional[str] = None
    mailing_zip: Optional[str] = None
    phone: Optional[str] = None
    mcs150_date: Optional[date] = None  # MCS-150 form date
    mc_number: Optional[str] = None  # Motor Carrier number
    mx_number: Optional[str] = None  # Mexico number
    ff_number: Optional[str] = None  # Freight Forwarder number
    power_units: int = 0
    drivers: int = 0
    operation_classification: List[CarrierOperationType] = field(default_factory=list)
    cargo_carried: List[str] = field(default_factory=list)
    hazmat: bool = False
    passenger_carrier: bool = False
    out_of_service: bool = False
    oos_date: Optional[date] = None


@dataclass
class CarrierBasics:
    """Carrier safety BASICS scores"""
    dot_number: str
    carrier_name: str
    unsafe_driving_score: Optional[float] = None
    unsafe_driving_percentile: Optional[float] = None
    hos_compliance_score: Optional[float] = None
    hos_compliance_percentile: Optional[float] = None
    driver_fitness_score: Optional[float] = None
    driver_fitness_percentile: Optional[float] = None
    controlled_substances_score: Optional[float] = None
    controlled_substances_percentile: Optional[float] = None
    vehicle_maintenance_score: Optional[float] = None
    vehicle_maintenance_percentile: Optional[float] = None
    hazmat_compliance_score: Optional[float] = None
    hazmat_compliance_percentile: Optional[float] = None
    crash_indicator_score: Optional[float] = None
    crash_indicator_percentile: Optional[float] = None


@dataclass
class Inspection:
    """FMCSA inspection record"""
    inspection_id: str
    dot_number: str
    carrier_name: Optional[str] = None
    inspection_date: Optional[date] = None
    report_state: Optional[str] = None
    report_number: Optional[str] = None
    inspection_level: Optional[int] = None
    inspection_type: Optional[InspectionType] = None
    vehicle_unit_type: Optional[str] = None
    driver_oos: bool = False
    vehicle_oos: bool = False
    hazmat_oos: bool = False
    driver_violations: int = 0
    vehicle_violations: int = 0
    hazmat_violations: int = 0
    total_violations: int = 0


@dataclass
class Crash:
    """FMCSA crash record"""
    crash_id: str
    dot_number: str
    carrier_name: Optional[str] = None
    crash_date: Optional[date] = None
    report_state: Optional[str] = None
    report_number: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    fatalities: int = 0
    injuries: int = 0
    tow_away: bool = False
    hazmat_release: bool = False
    vehicle_type: Optional[str] = None
    road_type: Optional[str] = None
    light_condition: Optional[str] = None
    weather_condition: Optional[str] = None


@dataclass
class OperatingAuthority:
    """Motor carrier operating authority"""
    dot_number: str
    carrier_name: str
    docket_number: Optional[str] = None
    authority_type: Optional[str] = None
    authority_status: Optional[str] = None
    common_authority: bool = False
    contract_authority: bool = False
    broker_authority: bool = False
    application_pending: bool = False
    effective_date: Optional[date] = None
    insurance_required: Optional[str] = None
    insurance_on_file: Optional[str] = None
    bipdInsuranceRequired: Optional[int] = None
    bipdInsuranceOnFile: Optional[int] = None


@dataclass
class Violation:
    """FMCSA violation record"""
    violation_code: str
    violation_description: str
    violation_group: Optional[ViolationType] = None
    section: Optional[str] = None
    oos_indicator: bool = False
    severity_weight: Optional[float] = None
    unit_type: Optional[str] = None
    time_weight: Optional[float] = None


class FMCSAApiClient:
    """
    FMCSA Web Services API client

    Provides access to motor carrier safety data including:
    - Carrier registration and operating authority
    - Safety ratings and BASICS scores
    - Inspections and violations
    - Crash records
    - Out-of-service orders
    """

    # FMCSA SAFER web services
    BASE_URL = "https://mobile.fmcsa.dot.gov/qc"

    # Alternative endpoints
    SAFER_URL = "https://ai.fmcsa.dot.gov/SMS/Carrier"
    CENSUS_URL = "https://ai.fmcsa.dot.gov/SMS/Census"

    def __init__(self, webkey: Optional[str] = None):
        """
        Initialize FMCSA API client

        Args:
            webkey: Optional FMCSA webkey for authenticated access
                   Get free key at: https://mobile.fmcsa.dot.gov/developer
        """
        self.webkey = webkey
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make request to FMCSA API

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            API response as dictionary
        """
        session = await self._get_session()

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}

        if self.webkey:
            params["webKey"] = self.webkey

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'json' in content_type:
                        return await response.json()
                    else:
                        text = await response.text()
                        return {"content": text}
                else:
                    error_text = await response.text()
                    logger.error(f"FMCSA API error {response.status}: {error_text}")
                    return {"error": error_text, "status": response.status}

        except asyncio.TimeoutError:
            logger.error("FMCSA API request timed out")
            return {"error": "Request timed out", "status": 408}
        except Exception as e:
            logger.error(f"FMCSA API request failed: {e}")
            return {"error": str(e), "status": 500}

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse various date formats"""
        if not date_str:
            return None
        try:
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%d-%b-%Y", "%b %d, %Y"]:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def _parse_operating_status(self, status: Optional[str]) -> Optional[OperatingStatus]:
        """Parse operating status string"""
        if not status:
            return None
        status_upper = status.upper()
        for os in OperatingStatus:
            if os.value in status_upper:
                return os
        return None

    def _parse_safety_rating(self, rating: Optional[str]) -> Optional[SafetyRating]:
        """Parse safety rating string"""
        if not rating:
            return None
        rating_lower = rating.lower()
        for sr in SafetyRating:
            if sr.value.lower() in rating_lower:
                return sr
        return SafetyRating.NOT_RATED

    # Carrier Lookup

    async def get_carrier_by_dot(self, dot_number: str) -> Optional[Carrier]:
        """
        Get carrier details by DOT number

        Args:
            dot_number: USDOT number

        Returns:
            Carrier details or None if not found
        """
        response = await self._make_request(
            "carrier/profile",
            {"dotNumber": dot_number}
        )

        carrier_data = response.get("content", {})
        if isinstance(carrier_data, str) or not carrier_data:
            # Try alternate format
            carrier_data = response.get("carrier", {})
            if not carrier_data:
                return None

        return self._parse_carrier(carrier_data)

    async def search_carriers(
        self,
        name: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        mc_number: Optional[str] = None,
        limit: int = 100
    ) -> List[Carrier]:
        """
        Search for motor carriers

        Args:
            name: Carrier name (partial match)
            state: State code
            city: City name
            mc_number: MC number
            limit: Maximum results

        Returns:
            List of matching carriers
        """
        params = {"size": limit}

        if name:
            params["searchType"] = "NAME"
            params["searchTerm"] = name

        if state:
            params["state"] = state.upper()

        if city:
            params["city"] = city

        if mc_number:
            params["searchType"] = "MC"
            params["searchTerm"] = mc_number

        response = await self._make_request("carrier/search", params)

        carriers = []
        results = response.get("content", [])
        if isinstance(results, list):
            for result in results[:limit]:
                carrier = self._parse_carrier(result)
                if carrier:
                    carriers.append(carrier)

        return carriers

    def _parse_carrier(self, data: Dict[str, Any]) -> Optional[Carrier]:
        """Parse carrier data from API response"""
        if not data:
            return None

        # Handle nested structures
        carrier_data = data.get("carrier", data)

        dot_number = str(carrier_data.get("dotNumber", carrier_data.get("dot_number", "")))
        if not dot_number:
            return None

        # Parse operation classifications
        operations = []
        op_class = carrier_data.get("operationClassification", carrier_data.get("operation_classification", []))
        if isinstance(op_class, list):
            for op in op_class:
                code = op if isinstance(op, str) else op.get("code", "")
                for cot in CarrierOperationType:
                    if cot.value == code:
                        operations.append(cot)
                        break

        return Carrier(
            dot_number=dot_number,
            legal_name=carrier_data.get("legalName", carrier_data.get("legal_name", "")),
            dba_name=carrier_data.get("dbaName", carrier_data.get("dba_name")),
            operating_status=self._parse_operating_status(
                carrier_data.get("operatingStatus", carrier_data.get("operating_status"))
            ),
            safety_rating=self._parse_safety_rating(
                carrier_data.get("safetyRating", carrier_data.get("safety_rating"))
            ),
            safety_rating_date=self._parse_date(
                carrier_data.get("safetyRatingDate", carrier_data.get("safety_rating_date"))
            ),
            physical_address=carrier_data.get("phyStreet", carrier_data.get("physical_address")),
            physical_city=carrier_data.get("phyCity", carrier_data.get("physical_city")),
            physical_state=carrier_data.get("phyState", carrier_data.get("physical_state")),
            physical_zip=carrier_data.get("phyZipcode", carrier_data.get("physical_zip")),
            mailing_address=carrier_data.get("mailingStreet", carrier_data.get("mailing_address")),
            mailing_city=carrier_data.get("mailingCity", carrier_data.get("mailing_city")),
            mailing_state=carrier_data.get("mailingState", carrier_data.get("mailing_state")),
            mailing_zip=carrier_data.get("mailingZipcode", carrier_data.get("mailing_zip")),
            phone=carrier_data.get("telephone", carrier_data.get("phone")),
            mcs150_date=self._parse_date(
                carrier_data.get("mcs150FormDate", carrier_data.get("mcs150_date"))
            ),
            mc_number=carrier_data.get("mcNumber", carrier_data.get("mc_number")),
            mx_number=carrier_data.get("mxNumber"),
            ff_number=carrier_data.get("ffNumber"),
            power_units=int(carrier_data.get("totalPowerUnits", carrier_data.get("power_units", 0)) or 0),
            drivers=int(carrier_data.get("totalDrivers", carrier_data.get("drivers", 0)) or 0),
            operation_classification=operations,
            cargo_carried=carrier_data.get("cargoCarried", carrier_data.get("cargo_carried", [])),
            hazmat=carrier_data.get("carrierHm", carrier_data.get("hazmat")) == "Y",
            passenger_carrier=carrier_data.get("carrierPC", carrier_data.get("passenger_carrier")) == "Y",
            out_of_service=carrier_data.get("oosFlag", carrier_data.get("out_of_service")) == "Y",
            oos_date=self._parse_date(carrier_data.get("oosDate", carrier_data.get("oos_date")))
        )

    # Safety Data

    async def get_carrier_basics(self, dot_number: str) -> Optional[CarrierBasics]:
        """
        Get carrier BASICS safety scores

        Args:
            dot_number: USDOT number

        Returns:
            BASICS scores or None if not found
        """
        response = await self._make_request(
            "carrier/basics",
            {"dotNumber": dot_number}
        )

        data = response.get("content", response.get("basics", {}))
        if not data:
            return None

        return CarrierBasics(
            dot_number=dot_number,
            carrier_name=data.get("carrierName", data.get("carrier_name", "")),
            unsafe_driving_score=data.get("unsafeDrivingMeasure"),
            unsafe_driving_percentile=data.get("unsafeDrivingPercentile"),
            hos_compliance_score=data.get("hosComplianceMeasure"),
            hos_compliance_percentile=data.get("hosCompliancePercentile"),
            driver_fitness_score=data.get("driverFitnessMeasure"),
            driver_fitness_percentile=data.get("driverFitnessPercentile"),
            controlled_substances_score=data.get("controlledSubstancesMeasure"),
            controlled_substances_percentile=data.get("controlledSubstancesPercentile"),
            vehicle_maintenance_score=data.get("vehicleMaintenanceMeasure"),
            vehicle_maintenance_percentile=data.get("vehicleMaintenancePercentile"),
            hazmat_compliance_score=data.get("hazmatComplianceMeasure"),
            hazmat_compliance_percentile=data.get("hazmatCompliancePercentile"),
            crash_indicator_score=data.get("crashIndicatorMeasure"),
            crash_indicator_percentile=data.get("crashIndicatorPercentile")
        )

    # Inspections

    async def get_carrier_inspections(
        self,
        dot_number: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Inspection]:
        """
        Get inspection records for a carrier

        Args:
            dot_number: USDOT number
            start_date: Start date for search
            end_date: End date for search
            limit: Maximum results

        Returns:
            List of inspection records
        """
        params = {
            "dotNumber": dot_number,
            "size": limit
        }

        if start_date:
            params["startDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            params["endDate"] = end_date.strftime("%m/%d/%Y")

        response = await self._make_request("carrier/inspections", params)

        inspections = []
        results = response.get("content", response.get("inspections", []))
        if isinstance(results, list):
            for result in results:
                inspection = self._parse_inspection(result, dot_number)
                if inspection:
                    inspections.append(inspection)

        return inspections

    def _parse_inspection(self, data: Dict[str, Any], dot_number: str) -> Optional[Inspection]:
        """Parse inspection data from API response"""
        if not data:
            return None

        inspection_id = data.get("inspectionId", data.get("inspection_id", data.get("reportNumber", "")))

        return Inspection(
            inspection_id=str(inspection_id),
            dot_number=dot_number,
            carrier_name=data.get("carrierName", data.get("carrier_name")),
            inspection_date=self._parse_date(data.get("inspectionDate", data.get("inspection_date"))),
            report_state=data.get("reportState", data.get("state")),
            report_number=data.get("reportNumber", data.get("report_number")),
            inspection_level=int(data.get("inspectionLevel", data.get("level", 0)) or 0),
            driver_oos=data.get("driverOOS", data.get("driver_oos")) == "Y",
            vehicle_oos=data.get("vehicleOOS", data.get("vehicle_oos")) == "Y",
            hazmat_oos=data.get("hazmatOOS", data.get("hazmat_oos")) == "Y",
            driver_violations=int(data.get("driverViolations", data.get("driver_violations", 0)) or 0),
            vehicle_violations=int(data.get("vehicleViolations", data.get("vehicle_violations", 0)) or 0),
            hazmat_violations=int(data.get("hazmatViolations", data.get("hazmat_violations", 0)) or 0),
            total_violations=int(data.get("totalViolations", data.get("total_violations", 0)) or 0)
        )

    # Crashes

    async def get_carrier_crashes(
        self,
        dot_number: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Crash]:
        """
        Get crash records for a carrier

        Args:
            dot_number: USDOT number
            start_date: Start date for search
            end_date: End date for search
            limit: Maximum results

        Returns:
            List of crash records
        """
        params = {
            "dotNumber": dot_number,
            "size": limit
        }

        if start_date:
            params["startDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            params["endDate"] = end_date.strftime("%m/%d/%Y")

        response = await self._make_request("carrier/crashes", params)

        crashes = []
        results = response.get("content", response.get("crashes", []))
        if isinstance(results, list):
            for result in results:
                crash = self._parse_crash(result, dot_number)
                if crash:
                    crashes.append(crash)

        return crashes

    def _parse_crash(self, data: Dict[str, Any], dot_number: str) -> Optional[Crash]:
        """Parse crash data from API response"""
        if not data:
            return None

        crash_id = data.get("crashId", data.get("crash_id", data.get("reportNumber", "")))

        return Crash(
            crash_id=str(crash_id),
            dot_number=dot_number,
            carrier_name=data.get("carrierName", data.get("carrier_name")),
            crash_date=self._parse_date(data.get("crashDate", data.get("crash_date"))),
            report_state=data.get("reportState", data.get("state")),
            report_number=data.get("reportNumber", data.get("report_number")),
            city=data.get("city"),
            county=data.get("county"),
            fatalities=int(data.get("fatalities", 0) or 0),
            injuries=int(data.get("injuries", 0) or 0),
            tow_away=data.get("towAway", data.get("tow_away")) == "Y",
            hazmat_release=data.get("hazmatReleased", data.get("hazmat_release")) == "Y",
            vehicle_type=data.get("vehicleType", data.get("vehicle_type")),
            road_type=data.get("roadType", data.get("road_type")),
            light_condition=data.get("lightCondition", data.get("light_condition")),
            weather_condition=data.get("weatherCondition", data.get("weather_condition"))
        )

    # Operating Authority

    async def get_carrier_authority(self, dot_number: str) -> Optional[OperatingAuthority]:
        """
        Get operating authority for a carrier

        Args:
            dot_number: USDOT number

        Returns:
            Operating authority details or None
        """
        response = await self._make_request(
            "carrier/authority",
            {"dotNumber": dot_number}
        )

        data = response.get("content", response.get("authority", {}))
        if not data:
            return None

        return OperatingAuthority(
            dot_number=dot_number,
            carrier_name=data.get("carrierName", data.get("carrier_name", "")),
            docket_number=data.get("docketNumber", data.get("docket_number")),
            authority_type=data.get("authorityType", data.get("authority_type")),
            authority_status=data.get("authorityStatus", data.get("authority_status")),
            common_authority=data.get("commonAuth", data.get("common_authority")) == "A",
            contract_authority=data.get("contractAuth", data.get("contract_authority")) == "A",
            broker_authority=data.get("brokerAuth", data.get("broker_authority")) == "A",
            application_pending=data.get("applicationPending", False),
            effective_date=self._parse_date(data.get("effectiveDate", data.get("effective_date"))),
            insurance_required=data.get("insuranceRequired", data.get("insurance_required")),
            insurance_on_file=data.get("insuranceOnFile", data.get("insurance_on_file")),
            bipdInsuranceRequired=int(data.get("bipdInsuranceRequired", 0) or 0),
            bipdInsuranceOnFile=int(data.get("bipdInsuranceOnFile", 0) or 0)
        )

    # Out of Service Summary

    async def get_carrier_oos_summary(self, dot_number: str) -> Dict[str, Any]:
        """
        Get out-of-service summary for a carrier

        Args:
            dot_number: USDOT number

        Returns:
            OOS summary statistics
        """
        response = await self._make_request(
            "carrier/oos",
            {"dotNumber": dot_number}
        )

        data = response.get("content", response.get("oosSummary", {}))

        return {
            "dot_number": dot_number,
            "total_inspections": data.get("totalInspections", 0),
            "driver_inspections": data.get("driverInspections", 0),
            "driver_oos": data.get("driverOOS", 0),
            "driver_oos_rate": data.get("driverOOSRate", 0),
            "vehicle_inspections": data.get("vehicleInspections", 0),
            "vehicle_oos": data.get("vehicleOOS", 0),
            "vehicle_oos_rate": data.get("vehicleOOSRate", 0),
            "hazmat_inspections": data.get("hazmatInspections", 0),
            "hazmat_oos": data.get("hazmatOOS", 0),
            "hazmat_oos_rate": data.get("hazmatOOSRate", 0),
            "national_driver_oos_rate": data.get("nationalDriverOOSRate"),
            "national_vehicle_oos_rate": data.get("nationalVehicleOOSRate")
        }

    # Carrier List by State

    async def get_carriers_by_state(
        self,
        state: str,
        operating_status: Optional[OperatingStatus] = None,
        hazmat_only: bool = False,
        passenger_only: bool = False,
        limit: int = 100
    ) -> List[Carrier]:
        """
        Get carriers registered in a state

        Args:
            state: Two-letter state code
            operating_status: Filter by operating status
            hazmat_only: Only hazmat carriers
            passenger_only: Only passenger carriers
            limit: Maximum results

        Returns:
            List of carriers
        """
        params = {
            "state": state.upper(),
            "size": limit
        }

        if operating_status:
            params["operatingStatus"] = operating_status.value

        if hazmat_only:
            params["hazmat"] = "Y"

        if passenger_only:
            params["passenger"] = "Y"

        response = await self._make_request("carrier/byState", params)

        carriers = []
        results = response.get("content", [])
        if isinstance(results, list):
            for result in results:
                carrier = self._parse_carrier(result)
                if carrier:
                    carriers.append(carrier)

        return carriers


# Convenience functions for synchronous usage

def get_carrier_sync(dot_number: str, webkey: Optional[str] = None) -> Optional[Carrier]:
    """Synchronous wrapper for carrier lookup"""
    async def _get():
        client = FMCSAApiClient(webkey=webkey)
        try:
            return await client.get_carrier_by_dot(dot_number)
        finally:
            await client.close()

    return asyncio.run(_get())


def search_carriers_sync(
    name: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 100,
    webkey: Optional[str] = None
) -> List[Carrier]:
    """Synchronous wrapper for carrier search"""
    async def _search():
        client = FMCSAApiClient(webkey=webkey)
        try:
            return await client.search_carriers(
                name=name,
                state=state,
                limit=limit
            )
        finally:
            await client.close()

    return asyncio.run(_search())


def get_carrier_inspections_sync(
    dot_number: str,
    limit: int = 100,
    webkey: Optional[str] = None
) -> List[Inspection]:
    """Synchronous wrapper for inspection lookup"""
    async def _get():
        client = FMCSAApiClient(webkey=webkey)
        try:
            return await client.get_carrier_inspections(dot_number, limit=limit)
        finally:
            await client.close()

    return asyncio.run(_get())


if __name__ == "__main__":
    # Example usage
    async def main():
        client = FMCSAApiClient()

        try:
            # Search for carriers
            print("Searching for carriers named 'Swift'...")
            carriers = await client.search_carriers(name="Swift", limit=5)
            for carrier in carriers:
                print(f"  DOT {carrier.dot_number}: {carrier.legal_name} ({carrier.physical_state})")

            # Get carrier details (if we found any)
            if carriers:
                dot = carriers[0].dot_number
                print(f"\nGetting details for DOT {dot}...")
                carrier = await client.get_carrier_by_dot(dot)
                if carrier:
                    print(f"  Name: {carrier.legal_name}")
                    print(f"  Status: {carrier.operating_status}")
                    print(f"  Safety Rating: {carrier.safety_rating}")
                    print(f"  Drivers: {carrier.drivers}")
                    print(f"  Power Units: {carrier.power_units}")

                # Get inspections
                print(f"\nGetting inspections for DOT {dot}...")
                inspections = await client.get_carrier_inspections(dot, limit=5)
                for insp in inspections:
                    print(f"  {insp.inspection_date}: {insp.total_violations} violations")

                # Get crashes
                print(f"\nGetting crashes for DOT {dot}...")
                crashes = await client.get_carrier_crashes(dot, limit=5)
                for crash in crashes:
                    print(f"  {crash.crash_date}: {crash.fatalities} fatalities, {crash.injuries} injuries")

        finally:
            await client.close()

    asyncio.run(main())
