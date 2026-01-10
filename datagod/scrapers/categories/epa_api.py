"""
EPA (Environmental Protection Agency) API Integration

Free public APIs providing access to:
- Facility environmental compliance data (ECHO)
- Environmental permits
- Inspections and violations
- Enforcement actions
- Air quality data (AQS)
- Toxic release inventory (TRI)
- Superfund sites (NPL)

API Documentation:
- https://www.epa.gov/enviro/envirofacts-data-service-api
- https://echo.epa.gov/tools/web-services

Rate Limit: No formal limit, but reasonable use expected
"""

import asyncio
import aiohttp
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class EPADatabase(Enum):
    """EPA Envirofacts databases"""
    # Facility Registration System
    FRS = "FRS_FACILITY_SITE"
    FRS_PROGRAM = "FRS_PROGRAM_FACILITY"

    # Toxic Release Inventory
    TRI = "TRI_FACILITY"
    TRI_RELEASE = "TRI_RELEASE_QTY"

    # Air Quality System
    AQS_SITES = "AQS_SITES"
    AQS_ANNUAL = "AQS_ANNUAL_SUMMARY"

    # Superfund
    SEMS = "SEMS_SITE"

    # Safe Drinking Water
    SDWIS = "SDWIS_WATER_SYSTEM"
    SDWIS_VIOLATION = "SDWIS_VIOLATION"

    # RCRA Hazardous Waste
    RCRAInfo = "RCRAINFO"

    # Clean Water Act
    NPDES = "NPDES_FACILITY"
    NPDES_DMR = "NPDES_DMR"


class ViolationType(Enum):
    """EPA violation types"""
    CAA = "Clean Air Act"
    CWA = "Clean Water Act"
    RCRA = "Resource Conservation and Recovery Act"
    SDWA = "Safe Drinking Water Act"
    TSCA = "Toxic Substances Control Act"
    CERCLA = "Superfund"
    EPCRA = "Emergency Planning"


class ComplianceStatus(Enum):
    """EPA facility compliance status"""
    IN_COMPLIANCE = "In Compliance"
    IN_VIOLATION = "In Violation"
    SIGNIFICANT_VIOLATION = "Significant Violation"
    UNKNOWN = "Unknown"


class FacilityType(Enum):
    """EPA regulated facility types"""
    MAJOR = "Major"
    MINOR = "Minor"
    SYNTHETIC_MINOR = "Synthetic Minor"
    FEDERAL = "Federal"
    STATE = "State"
    TRIBAL = "Tribal"


@dataclass
class EPAFacility:
    """EPA-regulated facility"""
    registry_id: str
    facility_name: str
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    naics_codes: List[str] = field(default_factory=list)
    sic_codes: List[str] = field(default_factory=list)
    programs: List[str] = field(default_factory=list)
    compliance_status: Optional[ComplianceStatus] = None


@dataclass
class EPAViolation:
    """EPA compliance violation"""
    violation_id: str
    facility_id: str
    facility_name: Optional[str] = None
    program: Optional[str] = None
    violation_type: Optional[ViolationType] = None
    violation_date: Optional[date] = None
    compliance_achieved_date: Optional[date] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None


@dataclass
class EPAEnforcement:
    """EPA enforcement action"""
    enforcement_id: str
    facility_id: str
    facility_name: Optional[str] = None
    action_type: Optional[str] = None
    action_date: Optional[date] = None
    lead_agency: Optional[str] = None
    settlement_date: Optional[date] = None
    penalty_amount: Optional[float] = None
    sep_amount: Optional[float] = None  # Supplemental Environmental Projects
    compliance_action_cost: Optional[float] = None
    program: Optional[str] = None
    state: Optional[str] = None


@dataclass
class TRIRelease:
    """Toxic Release Inventory release record"""
    tri_facility_id: str
    facility_name: str
    chemical_name: str
    cas_number: Optional[str] = None
    year: int = 0
    fugitive_air: Optional[float] = None
    stack_air: Optional[float] = None
    water: Optional[float] = None
    underground_injection: Optional[float] = None
    landfill: Optional[float] = None
    total_releases: Optional[float] = None
    total_transfers: Optional[float] = None
    state: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    industry_sector: Optional[str] = None


@dataclass
class SuperfundSite:
    """Superfund/NPL site"""
    site_id: str
    site_name: str
    epa_id: Optional[str] = None
    npl_status: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    federal_facility: bool = False
    contaminants: List[str] = field(default_factory=list)
    listing_date: Optional[date] = None
    construction_completion_date: Optional[date] = None
    deletion_date: Optional[date] = None


@dataclass
class AirQualityData:
    """Air quality monitoring data"""
    site_id: str
    parameter: str
    year: int
    arithmetic_mean: Optional[float] = None
    first_max_value: Optional[float] = None
    second_max_value: Optional[float] = None
    third_max_value: Optional[float] = None
    observations: Optional[int] = None
    aqi: Optional[int] = None
    state: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class WaterSystem:
    """Public water system from SDWIS"""
    pwsid: str
    system_name: str
    primacy_agency: Optional[str] = None
    primary_source: Optional[str] = None
    population_served: Optional[int] = None
    service_connections: Optional[int] = None
    owner_type: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    activity_status: Optional[str] = None
    violations_count: int = 0


class EPAApiClient:
    """
    EPA Envirofacts and ECHO API client

    Provides access to EPA environmental compliance data including:
    - Facility registrations and programs
    - Environmental violations and inspections
    - Enforcement actions and penalties
    - Toxic Release Inventory (TRI)
    - Superfund/NPL sites
    - Air quality monitoring data
    - Safe Drinking Water systems
    """

    ENVIROFACTS_URL = "https://enviro.epa.gov/enviro/efservice"
    ECHO_URL = "https://echo.epa.gov/api"

    def __init__(self):
        """Initialize EPA API client"""
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _envirofacts_request(
        self,
        table: EPADatabase,
        filters: Optional[Dict[str, str]] = None,
        rows: int = 100,
        output_format: str = "JSON"
    ) -> List[Dict[str, Any]]:
        """
        Make request to Envirofacts API

        Args:
            table: Database table to query
            filters: Column/value filter pairs
            rows: Number of rows to return
            output_format: Output format (JSON, CSV, XML)

        Returns:
            List of results
        """
        session = await self._get_session()

        # Build URL with filters
        url_parts = [self.ENVIROFACTS_URL, table.value]

        if filters:
            for column, value in filters.items():
                url_parts.append(f"{column}/{value}")

        url_parts.append(f"rows/0:{rows}")
        url_parts.append(output_format)

        url = "/".join(url_parts)

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"EPA API error {response.status}")
                    return []
        except Exception as e:
            logger.error(f"EPA API request failed: {e}")
            return []

    async def _echo_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make request to ECHO API

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            API response
        """
        session = await self._get_session()

        url = f"{self.ECHO_URL}/{endpoint}"
        params = params or {}
        params["output"] = "JSON"

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"ECHO API error {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"ECHO API request failed: {e}")
            return {}

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse various date formats"""
        if not date_str:
            return None
        try:
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%d-%b-%Y"]:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    # Facility Searches

    async def search_facilities(
        self,
        state: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        facility_name: Optional[str] = None,
        program: Optional[str] = None,
        limit: int = 100
    ) -> List[EPAFacility]:
        """
        Search EPA-regulated facilities

        Args:
            state: Two-letter state code
            city: City name
            zip_code: ZIP code
            facility_name: Facility name (partial match)
            program: EPA program (CAA, CWA, RCRA, etc.)
            limit: Maximum results

        Returns:
            List of EPA facilities
        """
        filters = {}

        if state:
            filters["STATE_CODE"] = state.upper()

        if city:
            filters["CITY_NAME"] = city.upper()

        if zip_code:
            filters["POSTAL_CODE"] = zip_code

        if facility_name:
            filters["PRIMARY_NAME"] = facility_name.upper()

        results = await self._envirofacts_request(
            EPADatabase.FRS,
            filters=filters,
            rows=limit
        )

        facilities = []
        for row in results:
            facilities.append(EPAFacility(
                registry_id=row.get("REGISTRY_ID", ""),
                facility_name=row.get("PRIMARY_NAME", ""),
                street_address=row.get("LOCATION_ADDRESS"),
                city=row.get("CITY_NAME"),
                state=row.get("STATE_CODE"),
                zip_code=row.get("POSTAL_CODE"),
                county=row.get("COUNTY_NAME"),
                latitude=float(row["LATITUDE83"]) if row.get("LATITUDE83") else None,
                longitude=float(row["LONGITUDE83"]) if row.get("LONGITUDE83") else None,
                naics_codes=[row.get("NAICS_CODE")] if row.get("NAICS_CODE") else [],
                sic_codes=[row.get("SIC_CODE")] if row.get("SIC_CODE") else []
            ))

        return facilities

    async def search_facilities_echo(
        self,
        state: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        facility_name: Optional[str] = None,
        in_violation: Optional[bool] = None,
        program: Optional[str] = None,
        limit: int = 100
    ) -> List[EPAFacility]:
        """
        Search facilities using ECHO API (more detailed compliance info)

        Args:
            state: Two-letter state code
            city: City name
            zip_code: ZIP code
            facility_name: Facility name
            in_violation: Filter for facilities in violation
            program: EPA program filter
            limit: Maximum results

        Returns:
            List of EPA facilities with compliance status
        """
        params = {
            "p_act": "Y",  # Active facilities only
            "p_limit": limit
        }

        if state:
            params["p_st"] = state.upper()

        if city:
            params["p_city"] = city

        if zip_code:
            params["p_zip"] = zip_code

        if facility_name:
            params["p_fn"] = facility_name

        if in_violation is True:
            params["p_qnc_status"] = "N"  # Non-compliant

        if program:
            params["p_med"] = program.upper()

        response = await self._echo_request("echo_rest_services.get_facilities", params)

        facilities = []
        for row in response.get("Results", {}).get("Facilities", []):
            compliance_status = None
            if row.get("DfrUrl"):
                qnc = row.get("Qtr13Status", "")
                if "V" in qnc:
                    compliance_status = ComplianceStatus.IN_VIOLATION
                elif "S" in qnc:
                    compliance_status = ComplianceStatus.SIGNIFICANT_VIOLATION
                elif "C" in qnc:
                    compliance_status = ComplianceStatus.IN_COMPLIANCE

            facilities.append(EPAFacility(
                registry_id=row.get("RegistryId", ""),
                facility_name=row.get("FacName", ""),
                street_address=row.get("FacStreet"),
                city=row.get("FacCity"),
                state=row.get("FacState"),
                zip_code=row.get("FacZip"),
                county=row.get("FacCounty"),
                latitude=float(row["FacLat"]) if row.get("FacLat") else None,
                longitude=float(row["FacLong"]) if row.get("FacLong") else None,
                programs=[p for p in [
                    "CAA" if row.get("AirFlag") == "Y" else None,
                    "CWA" if row.get("CwaFlag") == "Y" else None,
                    "RCRA" if row.get("RcraFlag") == "Y" else None,
                    "SDWA" if row.get("SdwisFlag") == "Y" else None,
                    "TRI" if row.get("TriFlag") == "Y" else None
                ] if p],
                compliance_status=compliance_status
            ))

        return facilities

    # Violations

    async def search_violations(
        self,
        state: Optional[str] = None,
        facility_name: Optional[str] = None,
        program: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100
    ) -> List[EPAViolation]:
        """
        Search EPA violations using ECHO

        Args:
            state: Two-letter state code
            facility_name: Facility name
            program: EPA program (CAA, CWA, RCRA, SDWA)
            date_from: Start date
            date_to: End date
            limit: Maximum results

        Returns:
            List of violations
        """
        params = {
            "p_limit": limit
        }

        if state:
            params["p_st"] = state.upper()

        if facility_name:
            params["p_fn"] = facility_name

        if program:
            params["p_med"] = program.upper()

        if date_from:
            params["p_viod_start"] = date_from.strftime("%m/%d/%Y")

        if date_to:
            params["p_viod_end"] = date_to.strftime("%m/%d/%Y")

        response = await self._echo_request("echo_rest_services.get_qid", params)

        # Get violation details
        qid = response.get("Results", {}).get("QueryId")
        if not qid:
            return []

        detail_response = await self._echo_request(
            "echo_rest_services.get_download",
            {"qid": qid, "p_viol": "Y"}
        )

        violations = []
        for row in detail_response.get("Results", {}).get("Violations", []):
            violation_type = None
            program_str = row.get("Program", "")
            for vt in ViolationType:
                if vt.name in program_str.upper():
                    violation_type = vt
                    break

            violations.append(EPAViolation(
                violation_id=row.get("ViolationId", ""),
                facility_id=row.get("RegistryId", ""),
                facility_name=row.get("FacilityName"),
                program=row.get("Program"),
                violation_type=violation_type,
                violation_date=self._parse_date(row.get("ViolationDate")),
                compliance_achieved_date=self._parse_date(row.get("ComplianceAchievedDate")),
                description=row.get("ViolationDescription"),
                severity=row.get("Severity"),
                state=row.get("State"),
                city=row.get("City")
            ))

        return violations

    # Enforcement Actions

    async def search_enforcements(
        self,
        state: Optional[str] = None,
        facility_name: Optional[str] = None,
        min_penalty: Optional[float] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100
    ) -> List[EPAEnforcement]:
        """
        Search EPA enforcement actions

        Args:
            state: Two-letter state code
            facility_name: Facility name
            min_penalty: Minimum penalty amount
            date_from: Start date
            date_to: End date
            limit: Maximum results

        Returns:
            List of enforcement actions
        """
        params = {
            "p_limit": limit
        }

        if state:
            params["p_st"] = state.upper()

        if facility_name:
            params["p_fn"] = facility_name

        if min_penalty:
            params["p_penalty"] = str(min_penalty)

        if date_from:
            params["p_enfd_start"] = date_from.strftime("%m/%d/%Y")

        if date_to:
            params["p_enfd_end"] = date_to.strftime("%m/%d/%Y")

        response = await self._echo_request("echo_rest_services.get_case_report", params)

        enforcements = []
        for row in response.get("Results", {}).get("CaseReport", []):
            enforcements.append(EPAEnforcement(
                enforcement_id=row.get("CaseNumber", ""),
                facility_id=row.get("RegistryId", ""),
                facility_name=row.get("FacilityName"),
                action_type=row.get("EnforcementType"),
                action_date=self._parse_date(row.get("EnforcementDate")),
                lead_agency=row.get("LeadAgency"),
                settlement_date=self._parse_date(row.get("SettlementDate")),
                penalty_amount=float(row["PenaltyAmount"]) if row.get("PenaltyAmount") else None,
                sep_amount=float(row["SEPAmt"]) if row.get("SEPAmt") else None,
                compliance_action_cost=float(row["CompActionCost"]) if row.get("CompActionCost") else None,
                program=row.get("PrimaryLaw"),
                state=row.get("State")
            ))

        return enforcements

    # Toxic Release Inventory

    async def search_tri_releases(
        self,
        state: Optional[str] = None,
        facility_name: Optional[str] = None,
        chemical: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 100
    ) -> List[TRIRelease]:
        """
        Search Toxic Release Inventory data

        Args:
            state: Two-letter state code
            facility_name: Facility name
            chemical: Chemical name
            year: Reporting year
            limit: Maximum results

        Returns:
            List of TRI release records
        """
        filters = {}

        if state:
            filters["ST"] = state.upper()

        if facility_name:
            filters["FACILITY_NAME"] = facility_name.upper()

        if chemical:
            filters["CHEM_NAME"] = chemical.upper()

        if year:
            filters["REPORTING_YEAR"] = str(year)

        results = await self._envirofacts_request(
            EPADatabase.TRI,
            filters=filters,
            rows=limit
        )

        releases = []
        for row in results:
            releases.append(TRIRelease(
                tri_facility_id=row.get("TRI_FACILITY_ID", ""),
                facility_name=row.get("FACILITY_NAME", ""),
                chemical_name=row.get("CHEM_NAME", ""),
                cas_number=row.get("CAS_CHEM_NAME"),
                year=int(row.get("REPORTING_YEAR", 0)),
                fugitive_air=float(row["FUGITIVE_AIR"]) if row.get("FUGITIVE_AIR") else None,
                stack_air=float(row["STACK_AIR"]) if row.get("STACK_AIR") else None,
                water=float(row["WATER"]) if row.get("WATER") else None,
                underground_injection=float(row["UNINJ_I"]) if row.get("UNINJ_I") else None,
                landfill=float(row["LANDFILLS"]) if row.get("LANDFILLS") else None,
                total_releases=float(row["TOTAL_RELEASES"]) if row.get("TOTAL_RELEASES") else None,
                total_transfers=float(row["TOTAL_TRANSFERS"]) if row.get("TOTAL_TRANSFERS") else None,
                state=row.get("ST"),
                city=row.get("CITY"),
                county=row.get("COUNTY"),
                latitude=float(row["LATITUDE"]) if row.get("LATITUDE") else None,
                longitude=float(row["LONGITUDE"]) if row.get("LONGITUDE") else None,
                industry_sector=row.get("INDUSTRY_SECTOR")
            ))

        return releases

    # Superfund Sites

    async def search_superfund_sites(
        self,
        state: Optional[str] = None,
        city: Optional[str] = None,
        site_name: Optional[str] = None,
        npl_status: Optional[str] = None,
        limit: int = 100
    ) -> List[SuperfundSite]:
        """
        Search Superfund/NPL sites

        Args:
            state: Two-letter state code
            city: City name
            site_name: Site name
            npl_status: NPL status (Proposed, Final, Deleted)
            limit: Maximum results

        Returns:
            List of Superfund sites
        """
        filters = {}

        if state:
            filters["STATE_CODE"] = state.upper()

        if city:
            filters["CITY_NAME"] = city.upper()

        if site_name:
            filters["SITE_NAME"] = site_name.upper()

        if npl_status:
            filters["NPL_STATUS"] = npl_status.upper()

        results = await self._envirofacts_request(
            EPADatabase.SEMS,
            filters=filters,
            rows=limit
        )

        sites = []
        for row in results:
            sites.append(SuperfundSite(
                site_id=row.get("SEMS_ID", ""),
                site_name=row.get("SITE_NAME", ""),
                epa_id=row.get("EPA_ID"),
                npl_status=row.get("NPL_STATUS"),
                street_address=row.get("STREET_ADDRESS"),
                city=row.get("CITY_NAME"),
                state=row.get("STATE_CODE"),
                zip_code=row.get("ZIP_CODE"),
                county=row.get("COUNTY_NAME"),
                latitude=float(row["LATITUDE"]) if row.get("LATITUDE") else None,
                longitude=float(row["LONGITUDE"]) if row.get("LONGITUDE") else None,
                federal_facility=row.get("FEDERAL_FAC_FLAG") == "Y",
                listing_date=self._parse_date(row.get("NPL_LISTING_DATE")),
                construction_completion_date=self._parse_date(row.get("CC_DATE")),
                deletion_date=self._parse_date(row.get("DELETION_DATE"))
            ))

        return sites

    # Water Systems

    async def search_water_systems(
        self,
        state: Optional[str] = None,
        city: Optional[str] = None,
        system_name: Optional[str] = None,
        min_population: Optional[int] = None,
        limit: int = 100
    ) -> List[WaterSystem]:
        """
        Search public water systems (SDWIS)

        Args:
            state: Two-letter state code
            city: City name
            system_name: System name
            min_population: Minimum population served
            limit: Maximum results

        Returns:
            List of water systems
        """
        filters = {}

        if state:
            filters["PRIMACY_AGENCY_CODE"] = state.upper()

        if city:
            filters["CITIES_SERVED"] = city.upper()

        if system_name:
            filters["PWS_NAME"] = system_name.upper()

        results = await self._envirofacts_request(
            EPADatabase.SDWIS,
            filters=filters,
            rows=limit
        )

        systems = []
        for row in results:
            pop = row.get("POPULATION_SERVED_COUNT")
            if min_population and (not pop or int(pop) < min_population):
                continue

            systems.append(WaterSystem(
                pwsid=row.get("PWSID", ""),
                system_name=row.get("PWS_NAME", ""),
                primacy_agency=row.get("PRIMACY_AGENCY_CODE"),
                primary_source=row.get("PRIMARY_SOURCE_CODE"),
                population_served=int(pop) if pop else None,
                service_connections=int(row["SERVICE_CONNECTIONS_COUNT"]) if row.get("SERVICE_CONNECTIONS_COUNT") else None,
                owner_type=row.get("OWNER_TYPE_CODE"),
                state=row.get("STATE_CODE"),
                city=row.get("CITIES_SERVED"),
                zip_code=row.get("ZIP_CODE"),
                activity_status=row.get("PWS_ACTIVITY_CODE")
            ))

        return systems

    # Air Quality

    async def search_air_quality(
        self,
        state: Optional[str] = None,
        county: Optional[str] = None,
        parameter: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 100
    ) -> List[AirQualityData]:
        """
        Search air quality monitoring data

        Args:
            state: Two-letter state code
            county: County name
            parameter: Pollutant parameter (PM25, OZONE, etc.)
            year: Year of data
            limit: Maximum results

        Returns:
            List of air quality records
        """
        filters = {}

        if state:
            filters["STATE_CODE"] = state.upper()

        if county:
            filters["COUNTY_NAME"] = county.upper()

        if parameter:
            filters["PARAMETER_NAME"] = parameter.upper()

        if year:
            filters["SAMPLE_YEAR"] = str(year)

        results = await self._envirofacts_request(
            EPADatabase.AQS_ANNUAL,
            filters=filters,
            rows=limit
        )

        air_data = []
        for row in results:
            air_data.append(AirQualityData(
                site_id=row.get("AQS_SITE_ID", ""),
                parameter=row.get("PARAMETER_NAME", ""),
                year=int(row.get("SAMPLE_YEAR", 0)),
                arithmetic_mean=float(row["ARITHMETIC_MEAN"]) if row.get("ARITHMETIC_MEAN") else None,
                first_max_value=float(row["FIRST_MAX_VALUE"]) if row.get("FIRST_MAX_VALUE") else None,
                second_max_value=float(row["SECOND_MAX_VALUE"]) if row.get("SECOND_MAX_VALUE") else None,
                third_max_value=float(row["THIRD_MAX_VALUE"]) if row.get("THIRD_MAX_VALUE") else None,
                observations=int(row["OBSERVATION_COUNT"]) if row.get("OBSERVATION_COUNT") else None,
                aqi=int(row["AQI"]) if row.get("AQI") else None,
                state=row.get("STATE_CODE"),
                county=row.get("COUNTY_NAME"),
                city=row.get("CITY_NAME"),
                latitude=float(row["LATITUDE"]) if row.get("LATITUDE") else None,
                longitude=float(row["LONGITUDE"]) if row.get("LONGITUDE") else None
            ))

        return air_data


# Convenience functions for synchronous usage

def search_facilities_sync(
    state: Optional[str] = None,
    city: Optional[str] = None,
    facility_name: Optional[str] = None,
    limit: int = 100
) -> List[EPAFacility]:
    """Synchronous wrapper for facility search"""
    async def _search():
        client = EPAApiClient()
        try:
            return await client.search_facilities(
                state=state,
                city=city,
                facility_name=facility_name,
                limit=limit
            )
        finally:
            await client.close()

    return asyncio.run(_search())


def search_violations_sync(
    state: Optional[str] = None,
    facility_name: Optional[str] = None,
    limit: int = 100
) -> List[EPAViolation]:
    """Synchronous wrapper for violation search"""
    async def _search():
        client = EPAApiClient()
        try:
            return await client.search_violations(
                state=state,
                facility_name=facility_name,
                limit=limit
            )
        finally:
            await client.close()

    return asyncio.run(_search())


def search_superfund_sites_sync(
    state: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = 100
) -> List[SuperfundSite]:
    """Synchronous wrapper for Superfund site search"""
    async def _search():
        client = EPAApiClient()
        try:
            return await client.search_superfund_sites(
                state=state,
                city=city,
                limit=limit
            )
        finally:
            await client.close()

    return asyncio.run(_search())


if __name__ == "__main__":
    # Example usage
    async def main():
        client = EPAApiClient()

        try:
            # Search facilities in California
            print("Searching EPA facilities in CA...")
            facilities = await client.search_facilities(state="CA", limit=5)
            for fac in facilities:
                print(f"  {fac.facility_name} ({fac.city}, {fac.state})")

            # Search TRI releases
            print("\nSearching TRI releases in TX...")
            releases = await client.search_tri_releases(state="TX", year=2022, limit=5)
            for rel in releases:
                print(f"  {rel.facility_name}: {rel.chemical_name} - {rel.total_releases} lbs")

            # Search Superfund sites
            print("\nSearching Superfund sites in NJ...")
            sites = await client.search_superfund_sites(state="NJ", limit=5)
            for site in sites:
                print(f"  {site.site_name} ({site.city}) - {site.npl_status}")

            # Search water systems
            print("\nSearching water systems in FL...")
            systems = await client.search_water_systems(state="FL", min_population=10000, limit=5)
            for sys in systems:
                print(f"  {sys.system_name}: Pop {sys.population_served}")

        finally:
            await client.close()

    asyncio.run(main())
