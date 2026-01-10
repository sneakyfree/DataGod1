"""
Childcare Licenses Scraper
==========================

Comprehensive scraper for childcare facility license records from state
licensing agencies. This data helps parents verify childcare providers
and is valuable for due diligence research.

Data Sources:
- State Department of Health and Human Services
- State licensing boards
- Child Care Resource and Referral agencies

Public Information:
- Facility name and address
- License number and type
- Capacity (children by age group)
- License status and expiration
- Inspection history
- Violations and corrective actions
- Owner/operator information

Note: Some states also report complaints and serious incidents.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
import json
import re
import logging

logger = logging.getLogger(__name__)


class FacilityType(Enum):
    """Types of childcare facilities"""
    # Center-based
    CHILD_CARE_CENTER = "child_care_center"
    PRESCHOOL = "preschool"
    NURSERY_SCHOOL = "nursery_school"
    HEAD_START = "head_start"
    BEFORE_AFTER_SCHOOL = "before_after_school"
    SUMMER_CAMP = "summer_camp"
    DROP_IN_CENTER = "drop_in_center"

    # Home-based
    FAMILY_CHILD_CARE = "family_child_care"
    GROUP_HOME = "group_home"
    LARGE_FAMILY_HOME = "large_family_home"
    SMALL_FAMILY_HOME = "small_family_home"
    REGISTERED_HOME = "registered_home"

    # Specialized
    INFANT_CENTER = "infant_center"
    SPECIAL_NEEDS = "special_needs"
    NIGHT_CARE = "night_care"
    SICK_CHILD_CARE = "sick_child_care"
    MONTESSORI = "montessori"
    RELIGIOUS_EXEMPT = "religious_exempt"

    OTHER = "other"


class LicenseStatus(Enum):
    """License status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROVISIONAL = "provisional"
    PROBATIONARY = "probationary"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING = "pending"
    CLOSED = "closed"
    EXEMPT = "exempt"


class LicenseType(Enum):
    """Types of licenses"""
    FULL_LICENSE = "full_license"
    PROVISIONAL = "provisional"
    TEMPORARY = "temporary"
    EMERGENCY = "emergency"
    PROBATIONARY = "probationary"
    REGISTRATION = "registration"
    CERTIFICATION = "certification"
    EXEMPT = "exempt"


class InspectionType(Enum):
    """Types of inspections"""
    INITIAL = "initial"
    ANNUAL = "annual"
    RENEWAL = "renewal"
    COMPLAINT = "complaint"
    FOLLOW_UP = "follow_up"
    UNANNOUNCED = "unannounced"
    MONITORING = "monitoring"


class ViolationType(Enum):
    """Types of violations"""
    CRITICAL = "critical"
    SERIOUS = "serious"
    NON_CRITICAL = "non_critical"
    TECHNICAL = "technical"
    ADMINISTRATIVE = "administrative"


@dataclass
class Inspection:
    """Inspection record"""
    inspection_date: date
    inspection_type: InspectionType = InspectionType.ANNUAL
    result: Optional[str] = None
    inspector_name: Optional[str] = None
    violations_found: int = 0
    corrected_on_site: int = 0
    report_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Violation:
    """Violation record"""
    violation_date: date
    violation_type: ViolationType = ViolationType.NON_CRITICAL
    code: Optional[str] = None
    description: str = ""
    corrective_action: Optional[str] = None
    correction_date: Optional[date] = None
    corrected: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Capacity:
    """Facility capacity by age group"""
    total_capacity: int = 0
    infants: int = 0  # 0-12 months
    toddlers: int = 0  # 12-24 months
    twos: int = 0  # 24-36 months
    preschool: int = 0  # 3-5 years
    school_age: int = 0  # 5+ years


@dataclass
class ChildcareFacility:
    """Childcare facility license record"""
    # Facility identification
    facility_name: str
    license_number: Optional[str] = None
    facility_type: FacilityType = FacilityType.CHILD_CARE_CENTER

    # Address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

    # Operator information
    operator_name: Optional[str] = None
    owner_name: Optional[str] = None
    director_name: Optional[str] = None

    # License details
    license_type: LicenseType = LicenseType.FULL_LICENSE
    license_status: LicenseStatus = LicenseStatus.ACTIVE
    issue_date: Optional[date] = None
    expiration_date: Optional[date] = None
    first_licensed: Optional[date] = None

    # Capacity
    capacity: Optional[Capacity] = None
    licensed_capacity: int = 0
    current_enrollment: Optional[int] = None

    # Hours of operation
    hours_of_operation: Optional[str] = None
    days_of_operation: Optional[str] = None

    # Inspection history
    inspections: List[Inspection] = field(default_factory=list)
    last_inspection_date: Optional[date] = None
    inspection_score: Optional[float] = None

    # Violations
    violations: List[Violation] = field(default_factory=list)
    total_violations: int = 0
    open_violations: int = 0

    # Additional info
    accepts_subsidies: Optional[bool] = None
    quality_rating: Optional[str] = None  # QRIS rating if available
    accreditation: Optional[str] = None
    languages: List[str] = field(default_factory=list)
    transportation: Optional[bool] = None
    meals_provided: Optional[bool] = None

    # Source tracking
    source_state: Optional[str] = None
    source_url: Optional[str] = None
    source_system: Optional[str] = None
    retrieved_at: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchCriteria:
    """Search criteria for childcare facilities"""
    facility_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    facility_type: Optional[FacilityType] = None
    license_status: Optional[LicenseStatus] = None
    min_capacity: Optional[int] = None
    accepts_subsidies: Optional[bool] = None


@dataclass
class SearchResult:
    """Search result container"""
    facilities: List[ChildcareFacility] = field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 100
    has_more: bool = False
    search_criteria: Optional[SearchCriteria] = None
    search_time_ms: int = 0
    source_system: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class BaseChildcareAPI:
    """Base class for state childcare licensing APIs"""

    STATE_CODE: str = ""
    STATE_NAME: str = ""
    BASE_URL: str = ""
    API_URL: str = ""
    SYSTEM_NAME: str = ""

    REQUEST_DELAY: float = 1.0

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; DataGod/1.0; Public Records Research)"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _fetch_json(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Fetch JSON data from URL"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")

        await asyncio.sleep(self.REQUEST_DELAY)

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def _fetch_html(self, url: str, params: Optional[Dict] = None) -> str:
        """Fetch HTML content from URL"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")

        await asyncio.sleep(self.REQUEST_DELAY)

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.text()

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string"""
        if not date_str:
            return None
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _classify_facility_type(self, type_str: str) -> FacilityType:
        """Classify facility type from string"""
        if not type_str:
            return FacilityType.OTHER

        type_lower = type_str.lower()

        if "family" in type_lower and "child" in type_lower:
            if "large" in type_lower:
                return FacilityType.LARGE_FAMILY_HOME
            elif "small" in type_lower:
                return FacilityType.SMALL_FAMILY_HOME
            elif "group" in type_lower:
                return FacilityType.GROUP_HOME
            return FacilityType.FAMILY_CHILD_CARE
        elif "group" in type_lower and "home" in type_lower:
            return FacilityType.GROUP_HOME
        elif "preschool" in type_lower:
            return FacilityType.PRESCHOOL
        elif "head start" in type_lower:
            return FacilityType.HEAD_START
        elif "before" in type_lower or "after" in type_lower or "school age" in type_lower:
            return FacilityType.BEFORE_AFTER_SCHOOL
        elif "summer" in type_lower or "camp" in type_lower:
            return FacilityType.SUMMER_CAMP
        elif "infant" in type_lower:
            return FacilityType.INFANT_CENTER
        elif "montessori" in type_lower:
            return FacilityType.MONTESSORI
        elif "center" in type_lower or "day care" in type_lower or "daycare" in type_lower:
            return FacilityType.CHILD_CARE_CENTER

        return FacilityType.OTHER

    def _parse_license_status(self, status_str: str) -> LicenseStatus:
        """Parse license status"""
        if not status_str:
            return LicenseStatus.ACTIVE

        status_lower = status_str.lower()

        if "active" in status_lower or "licensed" in status_lower:
            return LicenseStatus.ACTIVE
        elif "provisional" in status_lower:
            return LicenseStatus.PROVISIONAL
        elif "probation" in status_lower:
            return LicenseStatus.PROBATIONARY
        elif "suspend" in status_lower:
            return LicenseStatus.SUSPENDED
        elif "revok" in status_lower:
            return LicenseStatus.REVOKED
        elif "expir" in status_lower:
            return LicenseStatus.EXPIRED
        elif "pending" in status_lower:
            return LicenseStatus.PENDING
        elif "closed" in status_lower or "inactive" in status_lower:
            return LicenseStatus.CLOSED
        elif "exempt" in status_lower:
            return LicenseStatus.EXEMPT

        return LicenseStatus.ACTIVE

    async def search_facilities(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        county: Optional[str] = None,
        facility_type: Optional[FacilityType] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search for childcare facilities - override in subclass"""
        raise NotImplementedError

    async def get_facility_detail(
        self,
        license_number: str
    ) -> Optional[ChildcareFacility]:
        """Get detailed facility information - override in subclass"""
        raise NotImplementedError

    async def get_inspection_history(
        self,
        license_number: str
    ) -> List[Inspection]:
        """Get inspection history for a facility"""
        raise NotImplementedError


class CaliforniaChildcareAPI(BaseChildcareAPI):
    """California Community Care Licensing Division API"""

    STATE_CODE = "CA"
    STATE_NAME = "California"
    BASE_URL = "https://www.ccld.dss.ca.gov"
    API_URL = "https://www.ccld.dss.ca.gov/carefacilitysearch"
    SYSTEM_NAME = "California CCLD"

    async def search_facilities(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        county: Optional[str] = None,
        facility_type: Optional[FacilityType] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search California childcare facilities"""
        import time
        start_time = time.time()

        params = {
            "facilityType": "CHILDCARE",
            "pageSize": min(max_results, 100)
        }

        if name:
            params["facilityName"] = name
        if city:
            params["city"] = city
        if zip_code:
            params["zip"] = zip_code
        if county:
            params["county"] = county

        try:
            data = await self._fetch_json(f"{self.API_URL}/api/search", params=params)
        except Exception as e:
            logger.error(f"California childcare search failed: {e}")
            return SearchResult(
                facilities=[],
                total_count=0,
                warnings=[str(e)],
            )

        facilities = []
        for item in data.get("facilities", [])[:max_results]:
            facility = ChildcareFacility(
                facility_name=item.get("facilityName", ""),
                license_number=item.get("facilityNumber"),
                facility_type=self._classify_facility_type(item.get("facilityType", "")),
                address=item.get("address"),
                city=item.get("city"),
                state="CA",
                zip_code=item.get("zip"),
                county=item.get("county"),
                phone=item.get("phone"),
                license_status=self._parse_license_status(item.get("status", "")),
                licensed_capacity=item.get("capacity", 0),
                issue_date=self._parse_date(item.get("licenseDate", "")),
                source_state="CA",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            facilities.append(facility)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            facilities=facilities,
            total_count=data.get("totalCount", len(facilities)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                facility_name=name,
                city=city,
                zip_code=zip_code,
                county=county,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class TexasChildcareAPI(BaseChildcareAPI):
    """Texas HHS Childcare Licensing API"""

    STATE_CODE = "TX"
    STATE_NAME = "Texas"
    BASE_URL = "https://www.hhs.texas.gov"
    API_URL = "https://www.dfps.state.tx.us/child_care/Search_Texas_Child_Care"
    SYSTEM_NAME = "Texas DFPS Child Care Licensing"

    async def search_facilities(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        county: Optional[str] = None,
        facility_type: Optional[FacilityType] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search Texas childcare facilities"""
        import time
        start_time = time.time()

        params = {"pageSize": min(max_results, 100)}

        if name:
            params["operationName"] = name
        if city:
            params["city"] = city
        if zip_code:
            params["zipCode"] = zip_code
        if county:
            params["county"] = county

        try:
            data = await self._fetch_json(f"{self.API_URL}/api/search", params=params)
        except Exception as e:
            logger.error(f"Texas childcare search failed: {e}")
            return SearchResult(
                facilities=[],
                total_count=0,
                warnings=[str(e)],
            )

        facilities = []
        for item in data.get("operations", [])[:max_results]:
            facility = ChildcareFacility(
                facility_name=item.get("operationName", ""),
                license_number=item.get("operationNumber"),
                facility_type=self._classify_facility_type(item.get("operationType", "")),
                address=item.get("address"),
                city=item.get("city"),
                state="TX",
                zip_code=item.get("zip"),
                county=item.get("county"),
                phone=item.get("phone"),
                license_status=self._parse_license_status(item.get("status", "")),
                licensed_capacity=item.get("capacity", 0),
                accepts_subsidies=item.get("acceptsSubsidy"),
                source_state="TX",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            facilities.append(facility)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            facilities=facilities,
            total_count=data.get("totalCount", len(facilities)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                facility_name=name,
                city=city,
                zip_code=zip_code,
                county=county,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class FloridaChildcareAPI(BaseChildcareAPI):
    """Florida Department of Children and Families Childcare API"""

    STATE_CODE = "FL"
    STATE_NAME = "Florida"
    BASE_URL = "https://cares.myflfamilies.com"
    API_URL = "https://cares.myflfamilies.com/PublicSearch"
    SYSTEM_NAME = "Florida DCF Child Care"

    async def search_facilities(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        county: Optional[str] = None,
        facility_type: Optional[FacilityType] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search Florida childcare facilities"""
        import time
        start_time = time.time()

        params = {"searchType": "ChildCare"}

        if name:
            params["providerName"] = name
        if city:
            params["city"] = city
        if zip_code:
            params["zipCode"] = zip_code
        if county:
            params["county"] = county

        try:
            data = await self._fetch_json(f"{self.API_URL}/Search", params=params)
        except Exception as e:
            logger.error(f"Florida childcare search failed: {e}")
            return SearchResult(
                facilities=[],
                total_count=0,
                warnings=[str(e)],
            )

        facilities = []
        for item in data.get("providers", [])[:max_results]:
            facility = ChildcareFacility(
                facility_name=item.get("providerName", ""),
                license_number=item.get("licenseNumber"),
                facility_type=self._classify_facility_type(item.get("programType", "")),
                address=item.get("address"),
                city=item.get("city"),
                state="FL",
                zip_code=item.get("zip"),
                county=item.get("county"),
                phone=item.get("phone"),
                license_status=self._parse_license_status(item.get("status", "")),
                licensed_capacity=item.get("capacity", 0),
                quality_rating=item.get("goldSealStatus"),
                accepts_subsidies=item.get("acceptsSchoolReadiness"),
                source_state="FL",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            facilities.append(facility)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            facilities=facilities,
            total_count=data.get("totalCount", len(facilities)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                facility_name=name,
                city=city,
                zip_code=zip_code,
                county=county,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class NewYorkChildcareAPI(BaseChildcareAPI):
    """New York OCFS Childcare API"""

    STATE_CODE = "NY"
    STATE_NAME = "New York"
    BASE_URL = "https://ocfs.ny.gov"
    API_URL = "https://ocfs.ny.gov/programs/childcare/search"
    SYSTEM_NAME = "New York OCFS"

    async def search_facilities(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        county: Optional[str] = None,
        facility_type: Optional[FacilityType] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search New York childcare facilities"""
        import time
        start_time = time.time()

        params = {"pageSize": min(max_results, 100)}

        if name:
            params["facilityName"] = name
        if city:
            params["city"] = city
        if zip_code:
            params["zip"] = zip_code
        if county:
            params["county"] = county

        try:
            data = await self._fetch_json(f"{self.API_URL}/api/facilities", params=params)
        except Exception as e:
            logger.error(f"New York childcare search failed: {e}")
            return SearchResult(
                facilities=[],
                total_count=0,
                warnings=[str(e)],
            )

        facilities = []
        for item in data.get("facilities", [])[:max_results]:
            facility = ChildcareFacility(
                facility_name=item.get("name", ""),
                license_number=item.get("facilityId"),
                facility_type=self._classify_facility_type(item.get("type", "")),
                address=item.get("address"),
                city=item.get("city"),
                state="NY",
                zip_code=item.get("zip"),
                county=item.get("county"),
                phone=item.get("phone"),
                license_status=self._parse_license_status(item.get("status", "")),
                licensed_capacity=item.get("capacity", 0),
                quality_rating=item.get("qrisRating"),
                source_state="NY",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            facilities.append(facility)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            facilities=facilities,
            total_count=data.get("totalCount", len(facilities)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                facility_name=name,
                city=city,
                zip_code=zip_code,
                county=county,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


# State childcare API registry
STATE_CHILDCARE_APIS: Dict[str, type] = {
    "CA": CaliforniaChildcareAPI,
    "TX": TexasChildcareAPI,
    "FL": FloridaChildcareAPI,
    "NY": NewYorkChildcareAPI,
}


def get_childcare_api(state: str) -> Optional[BaseChildcareAPI]:
    """Get childcare API for a state"""
    api_class = STATE_CHILDCARE_APIS.get(state.upper())
    if api_class:
        return api_class()
    return None


# Convenience functions

def search_childcare_facilities(
    state: str,
    name: Optional[str] = None,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    county: Optional[str] = None,
    max_results: int = 100
) -> SearchResult:
    """Search childcare facilities in a state"""
    async def _search():
        api = get_childcare_api(state)
        if not api:
            return SearchResult(
                facilities=[],
                total_count=0,
                warnings=[f"No childcare API available for state: {state}"],
            )
        async with api:
            return await api.search_facilities(
                name=name,
                city=city,
                zip_code=zip_code,
                county=county,
                max_results=max_results
            )
    return asyncio.run(_search())


def search_childcare_by_zip(
    state: str,
    zip_code: str,
    max_results: int = 100
) -> SearchResult:
    """Search childcare facilities by ZIP code"""
    return search_childcare_facilities(
        state=state,
        zip_code=zip_code,
        max_results=max_results
    )


def search_all_states_childcare(
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    max_results_per_state: int = 50
) -> List[SearchResult]:
    """Search childcare facilities across all available states"""
    async def _search_all():
        results = []
        for state_code, api_class in STATE_CHILDCARE_APIS.items():
            try:
                async with api_class() as api:
                    result = await api.search_facilities(
                        city=city,
                        zip_code=zip_code,
                        max_results=max_results_per_state
                    )
                    results.append(result)
            except Exception as e:
                logger.error(f"Error searching {state_code}: {e}")
                results.append(SearchResult(
                    facilities=[],
                    total_count=0,
                    warnings=[f"{state_code}: {str(e)}"],
                ))
        return results
    return asyncio.run(_search_all())
