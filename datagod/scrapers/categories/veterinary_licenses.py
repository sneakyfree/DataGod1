"""
Veterinary Licenses Scraper
===========================

Comprehensive scraper for veterinary professional license records from state
veterinary medical boards. This data is useful for verifying credentials
and conducting due diligence on veterinary professionals.

Data Sources:
- State Board of Veterinary Medicine/Examiners
- State licensing verification databases
- Professional credential repositories

Public Information:
- Licensee name
- License number and type
- License status
- Issue and expiration dates
- Practice address
- Disciplinary actions (if any)
- Specialties/certifications

Licensed Professionals Covered:
- Veterinarians (DVM, VMD)
- Veterinary Technicians/Technologists
- Veterinary Assistants (where licensed)
- Veterinary Specialists
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


class LicenseType(Enum):
    """Types of veterinary licenses"""

    # Veterinarians
    VETERINARIAN = "veterinarian"
    VETERINARIAN_LIMITED = "veterinarian_limited"
    VETERINARIAN_TEMPORARY = "veterinarian_temporary"
    VETERINARIAN_FACULTY = "veterinarian_faculty"
    VETERINARIAN_SPECIALTY = "veterinarian_specialty"

    # Technicians
    VETERINARY_TECHNICIAN = "veterinary_technician"
    LICENSED_VET_TECH = "licensed_vet_tech"
    CERTIFIED_VET_TECH = "certified_vet_tech"
    REGISTERED_VET_TECH = "registered_vet_tech"

    # Other
    VETERINARY_ASSISTANT = "veterinary_assistant"
    ANIMAL_CHIROPRACTOR = "animal_chiropractor"
    ANIMAL_PHYSICAL_THERAPIST = "animal_physical_therapist"
    EQUINE_DENTIST = "equine_dentist"

    OTHER = "other"


class LicenseStatus(Enum):
    """License status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PROBATION = "probation"
    PENDING = "pending"
    RETIRED = "retired"
    DECEASED = "deceased"
    SURRENDERED = "surrendered"
    LAPSED = "lapsed"


class Specialty(Enum):
    """Veterinary specialties (AVMA recognized)"""

    # Clinical Specialties
    ANESTHESIA = "anesthesia"
    BEHAVIOR = "behavior"
    CARDIOLOGY = "cardiology"
    DENTISTRY = "dentistry"
    DERMATOLOGY = "dermatology"
    EMERGENCY_CRITICAL_CARE = "emergency_critical_care"
    INTERNAL_MEDICINE = "internal_medicine"
    NEUROLOGY = "neurology"
    NUTRITION = "nutrition"
    ONCOLOGY = "oncology"
    OPHTHALMOLOGY = "ophthalmology"
    RADIOLOGY = "radiology"
    SPORTS_MEDICINE = "sports_medicine"
    SURGERY = "surgery"
    THERIOGENOLOGY = "theriogenology"  # Reproduction

    # Species/Practice Area
    AVIAN = "avian"
    EQUINE = "equine"
    EXOTIC = "exotic"
    FELINE = "feline"
    FOOD_ANIMAL = "food_animal"
    LABORATORY_ANIMAL = "laboratory_animal"
    POULTRY = "poultry"
    SWINE = "swine"
    ZOOLOGICAL = "zoological"

    # Other
    PATHOLOGY = "pathology"
    PHARMACOLOGY = "pharmacology"
    PREVENTIVE_MEDICINE = "preventive_medicine"
    TOXICOLOGY = "toxicology"

    GENERAL_PRACTICE = "general_practice"
    OTHER = "other"


class DisciplinaryAction(Enum):
    """Types of disciplinary actions"""

    REPRIMAND = "reprimand"
    FINE = "fine"
    PROBATION = "probation"
    SUSPENSION = "suspension"
    REVOCATION = "revocation"
    SURRENDER = "surrender"
    RESTRICTION = "restriction"
    CONTINUING_EDUCATION = "continuing_education"
    WARNING = "warning"
    CONSENT_ORDER = "consent_order"
    OTHER = "other"


@dataclass
class DisciplinaryRecord:
    """Disciplinary action record"""

    action_type: DisciplinaryAction = DisciplinaryAction.OTHER
    action_date: Optional[date] = None
    effective_date: Optional[date] = None
    end_date: Optional[date] = None
    violation_description: Optional[str] = None
    order_number: Optional[str] = None
    fine_amount: Optional[float] = None
    is_active: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VeterinaryLicense:
    """Veterinary license record"""

    # Licensee information
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    suffix: Optional[str] = None
    credential: Optional[str] = None  # DVM, VMD, LVT, etc.

    # License details
    license_number: Optional[str] = None
    license_type: LicenseType = LicenseType.VETERINARIAN
    license_status: LicenseStatus = LicenseStatus.ACTIVE
    issue_date: Optional[date] = None
    expiration_date: Optional[date] = None
    original_issue_date: Optional[date] = None

    # Practice information
    practice_name: Optional[str] = None
    practice_address: Optional[str] = None
    practice_city: Optional[str] = None
    practice_state: Optional[str] = None
    practice_zip: Optional[str] = None
    practice_phone: Optional[str] = None

    # Mailing address (if different)
    mailing_address: Optional[str] = None
    mailing_city: Optional[str] = None
    mailing_state: Optional[str] = None
    mailing_zip: Optional[str] = None

    # Education and credentials
    school: Optional[str] = None
    graduation_year: Optional[int] = None
    specialties: List[Specialty] = field(default_factory=list)
    board_certifications: List[str] = field(default_factory=list)

    # DEA information (controlled substances)
    dea_number: Optional[str] = None
    dea_status: Optional[str] = None

    # Disciplinary history
    disciplinary_actions: List[DisciplinaryRecord] = field(default_factory=list)
    has_discipline: bool = False

    # Source tracking
    source_state: Optional[str] = None
    source_url: Optional[str] = None
    source_system: Optional[str] = None
    retrieved_at: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchCriteria:
    """Search criteria for veterinary licenses"""

    last_name: Optional[str] = None
    first_name: Optional[str] = None
    license_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    license_type: Optional[LicenseType] = None
    license_status: Optional[LicenseStatus] = None
    specialty: Optional[Specialty] = None


@dataclass
class SearchResult:
    """Search result container"""

    licenses: List[VeterinaryLicense] = field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 100
    has_more: bool = False
    search_criteria: Optional[SearchCriteria] = None
    search_time_ms: int = 0
    source_system: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class BaseVeterinaryBoardAPI:
    """Base class for state veterinary board APIs"""

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

    def _parse_license_status(self, status_str: str) -> LicenseStatus:
        """Parse license status"""
        if not status_str:
            return LicenseStatus.ACTIVE

        status_lower = status_str.lower()

        if "active" in status_lower or "current" in status_lower:
            return LicenseStatus.ACTIVE
        elif "inactive" in status_lower:
            return LicenseStatus.INACTIVE
        elif "expired" in status_lower or "lapsed" in status_lower:
            return LicenseStatus.EXPIRED
        elif "suspend" in status_lower:
            return LicenseStatus.SUSPENDED
        elif "revok" in status_lower:
            return LicenseStatus.REVOKED
        elif "probation" in status_lower:
            return LicenseStatus.PROBATION
        elif "retired" in status_lower:
            return LicenseStatus.RETIRED
        elif "deceased" in status_lower:
            return LicenseStatus.DECEASED
        elif "surrender" in status_lower:
            return LicenseStatus.SURRENDERED

        return LicenseStatus.ACTIVE

    def _classify_license_type(self, type_str: str) -> LicenseType:
        """Classify license type"""
        if not type_str:
            return LicenseType.VETERINARIAN

        type_lower = type_str.lower()

        if "technician" in type_lower or "tech" in type_lower:
            if "licensed" in type_lower:
                return LicenseType.LICENSED_VET_TECH
            elif "certified" in type_lower:
                return LicenseType.CERTIFIED_VET_TECH
            elif "registered" in type_lower:
                return LicenseType.REGISTERED_VET_TECH
            return LicenseType.VETERINARY_TECHNICIAN
        elif "assistant" in type_lower:
            return LicenseType.VETERINARY_ASSISTANT
        elif "faculty" in type_lower:
            return LicenseType.VETERINARIAN_FACULTY
        elif "temporary" in type_lower or "temp" in type_lower:
            return LicenseType.VETERINARIAN_TEMPORARY
        elif "limited" in type_lower:
            return LicenseType.VETERINARIAN_LIMITED
        elif "specialty" in type_lower or "specialist" in type_lower:
            return LicenseType.VETERINARIAN_SPECIALTY
        elif "veterinar" in type_lower or "dvm" in type_lower or "vmd" in type_lower:
            return LicenseType.VETERINARIAN

        return LicenseType.OTHER

    async def search_licenses(
        self,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
        license_number: Optional[str] = None,
        city: Optional[str] = None,
        license_type: Optional[LicenseType] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """Search for veterinary licenses - override in subclass"""
        raise NotImplementedError

    async def get_license_detail(
        self, license_number: str
    ) -> Optional[VeterinaryLicense]:
        """Get detailed license information - override in subclass"""
        raise NotImplementedError

    async def verify_license(self, license_number: str) -> bool:
        """Verify a license is active"""
        license_info = await self.get_license_detail(license_number)
        if license_info:
            return license_info.license_status == LicenseStatus.ACTIVE
        return False


class CaliforniaVetBoardAPI(BaseVeterinaryBoardAPI):
    """California Veterinary Medical Board API"""

    STATE_CODE = "CA"
    STATE_NAME = "California"
    BASE_URL = "https://www.vmb.ca.gov"
    API_URL = "https://search.dca.ca.gov"
    SYSTEM_NAME = "California VMB"

    async def search_licenses(
        self,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
        license_number: Optional[str] = None,
        city: Optional[str] = None,
        license_type: Optional[LicenseType] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """Search California veterinary licenses"""
        import time

        start_time = time.time()

        params = {"boardCode": "VMB", "pageSize": min(max_results, 100)}

        if last_name:
            params["lastName"] = last_name
        if first_name:
            params["firstName"] = first_name
        if license_number:
            params["licenseNumber"] = license_number
        if city:
            params["city"] = city

        try:
            data = await self._fetch_json(f"{self.API_URL}/results", params=params)
        except Exception as e:
            logger.error(f"California vet license search failed: {e}")
            return SearchResult(
                licenses=[],
                total_count=0,
                warnings=[str(e)],
            )

        licenses = []
        for item in data.get("results", [])[:max_results]:
            vet_license = VeterinaryLicense(
                first_name=item.get("firstName", ""),
                last_name=item.get("lastName", ""),
                middle_name=item.get("middleName"),
                license_number=item.get("licenseNumber"),
                license_type=self._classify_license_type(item.get("licenseType", "")),
                license_status=self._parse_license_status(item.get("status", "")),
                issue_date=self._parse_date(item.get("issueDate", "")),
                expiration_date=self._parse_date(item.get("expirationDate", "")),
                practice_city=item.get("city"),
                practice_state="CA",
                practice_zip=item.get("zip"),
                has_discipline=item.get("hasDiscipline", False),
                source_state="CA",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            licenses.append(vet_license)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            licenses=licenses,
            total_count=data.get("totalCount", len(licenses)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                last_name=last_name,
                first_name=first_name,
                license_number=license_number,
                city=city,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class TexasVetBoardAPI(BaseVeterinaryBoardAPI):
    """Texas State Board of Veterinary Medical Examiners API"""

    STATE_CODE = "TX"
    STATE_NAME = "Texas"
    BASE_URL = "https://www.veterinary.texas.gov"
    API_URL = "https://www.veterinary.texas.gov/lic_verification"
    SYSTEM_NAME = "Texas SBVME"

    async def search_licenses(
        self,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
        license_number: Optional[str] = None,
        city: Optional[str] = None,
        license_type: Optional[LicenseType] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """Search Texas veterinary licenses"""
        import time

        start_time = time.time()

        params = {"pageSize": min(max_results, 100)}

        if last_name:
            params["lastName"] = last_name
        if first_name:
            params["firstName"] = first_name
        if license_number:
            params["licenseNumber"] = license_number
        if city:
            params["city"] = city

        try:
            data = await self._fetch_json(f"{self.API_URL}/search", params=params)
        except Exception as e:
            logger.error(f"Texas vet license search failed: {e}")
            return SearchResult(
                licenses=[],
                total_count=0,
                warnings=[str(e)],
            )

        licenses = []
        for item in data.get("licensees", [])[:max_results]:
            vet_license = VeterinaryLicense(
                first_name=item.get("firstName", ""),
                last_name=item.get("lastName", ""),
                license_number=item.get("licenseNumber"),
                license_type=self._classify_license_type(item.get("licenseType", "")),
                license_status=self._parse_license_status(item.get("status", "")),
                expiration_date=self._parse_date(item.get("expirationDate", "")),
                practice_city=item.get("city"),
                practice_state="TX",
                source_state="TX",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            licenses.append(vet_license)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            licenses=licenses,
            total_count=data.get("totalCount", len(licenses)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                last_name=last_name,
                first_name=first_name,
                license_number=license_number,
                city=city,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class FloridaVetBoardAPI(BaseVeterinaryBoardAPI):
    """Florida Board of Veterinary Medicine API"""

    STATE_CODE = "FL"
    STATE_NAME = "Florida"
    BASE_URL = "https://flhealthsource.gov"
    API_URL = (
        "https://mqa-internet.doh.state.fl.us/MQASearchServices/HealthCareProviders"
    )
    SYSTEM_NAME = "Florida DOH MQA"

    async def search_licenses(
        self,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
        license_number: Optional[str] = None,
        city: Optional[str] = None,
        license_type: Optional[LicenseType] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """Search Florida veterinary licenses"""
        import time

        start_time = time.time()

        params = {"board": "Veterinary Medicine", "pageSize": min(max_results, 100)}

        if last_name:
            params["lastName"] = last_name
        if first_name:
            params["firstName"] = first_name
        if license_number:
            params["licenseNumber"] = license_number
        if city:
            params["city"] = city

        try:
            data = await self._fetch_json(f"{self.API_URL}/Search", params=params)
        except Exception as e:
            logger.error(f"Florida vet license search failed: {e}")
            return SearchResult(
                licenses=[],
                total_count=0,
                warnings=[str(e)],
            )

        licenses = []
        for item in data.get("providers", [])[:max_results]:
            vet_license = VeterinaryLicense(
                first_name=item.get("firstName", ""),
                last_name=item.get("lastName", ""),
                middle_name=item.get("middleName"),
                license_number=item.get("licenseNumber"),
                license_type=self._classify_license_type(item.get("profession", "")),
                license_status=self._parse_license_status(item.get("status", "")),
                expiration_date=self._parse_date(item.get("expirationDate", "")),
                practice_city=item.get("city"),
                practice_state="FL",
                practice_zip=item.get("zip"),
                source_state="FL",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            licenses.append(vet_license)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            licenses=licenses,
            total_count=data.get("totalCount", len(licenses)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                last_name=last_name,
                first_name=first_name,
                license_number=license_number,
                city=city,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class NewYorkVetBoardAPI(BaseVeterinaryBoardAPI):
    """New York State Education Department Veterinary License API"""

    STATE_CODE = "NY"
    STATE_NAME = "New York"
    BASE_URL = "http://www.op.nysed.gov"
    API_URL = "http://www.op.nysed.gov/opsearches.htm"
    SYSTEM_NAME = "New York SED OP"

    async def search_licenses(
        self,
        last_name: Optional[str] = None,
        first_name: Optional[str] = None,
        license_number: Optional[str] = None,
        city: Optional[str] = None,
        license_type: Optional[LicenseType] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """Search New York veterinary licenses"""
        import time

        start_time = time.time()

        params = {
            "profession": "Veterinary Medicine",
            "pageSize": min(max_results, 100),
        }

        if last_name:
            params["lastName"] = last_name
        if first_name:
            params["firstName"] = first_name
        if license_number:
            params["licenseNumber"] = license_number
        if city:
            params["city"] = city

        try:
            data = await self._fetch_json(f"{self.BASE_URL}/api/search", params=params)
        except Exception as e:
            logger.error(f"New York vet license search failed: {e}")
            return SearchResult(
                licenses=[],
                total_count=0,
                warnings=[str(e)],
            )

        licenses = []
        for item in data.get("results", [])[:max_results]:
            vet_license = VeterinaryLicense(
                first_name=item.get("firstName", ""),
                last_name=item.get("lastName", ""),
                license_number=item.get("licenseNumber"),
                license_type=self._classify_license_type(item.get("title", "")),
                license_status=self._parse_license_status(item.get("status", "")),
                issue_date=self._parse_date(item.get("dateRegistered", "")),
                practice_city=item.get("city"),
                practice_state="NY",
                source_state="NY",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            licenses.append(vet_license)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            licenses=licenses,
            total_count=data.get("totalCount", len(licenses)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                last_name=last_name,
                first_name=first_name,
                license_number=license_number,
                city=city,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


# State veterinary board API registry
STATE_VET_BOARD_APIS: Dict[str, type] = {
    "CA": CaliforniaVetBoardAPI,
    "TX": TexasVetBoardAPI,
    "FL": FloridaVetBoardAPI,
    "NY": NewYorkVetBoardAPI,
}


def get_vet_board_api(state: str) -> Optional[BaseVeterinaryBoardAPI]:
    """Get veterinary board API for a state"""
    api_class = STATE_VET_BOARD_APIS.get(state.upper())
    if api_class:
        return api_class()
    return None


# Convenience functions


def search_veterinary_licenses(
    state: str,
    last_name: Optional[str] = None,
    first_name: Optional[str] = None,
    license_number: Optional[str] = None,
    city: Optional[str] = None,
    max_results: int = 100,
) -> SearchResult:
    """Search veterinary licenses in a state"""

    async def _search():
        api = get_vet_board_api(state)
        if not api:
            return SearchResult(
                licenses=[],
                total_count=0,
                warnings=[f"No veterinary board API available for state: {state}"],
            )
        async with api:
            return await api.search_licenses(
                last_name=last_name,
                first_name=first_name,
                license_number=license_number,
                city=city,
                max_results=max_results,
            )

    return asyncio.run(_search())


def verify_veterinary_license(state: str, license_number: str) -> bool:
    """Verify a veterinary license is active"""

    async def _verify():
        api = get_vet_board_api(state)
        if not api:
            return False
        async with api:
            return await api.verify_license(license_number)

    return asyncio.run(_verify())


def search_all_states_vet_licenses(
    last_name: Optional[str] = None,
    first_name: Optional[str] = None,
    max_results_per_state: int = 50,
) -> List[SearchResult]:
    """Search veterinary licenses across all available states"""

    async def _search_all():
        results = []
        for state_code, api_class in STATE_VET_BOARD_APIS.items():
            try:
                async with api_class() as api:
                    result = await api.search_licenses(
                        last_name=last_name,
                        first_name=first_name,
                        max_results=max_results_per_state,
                    )
                    results.append(result)
            except Exception as e:
                logger.error(f"Error searching {state_code}: {e}")
                results.append(
                    SearchResult(
                        licenses=[],
                        total_count=0,
                        warnings=[f"{state_code}: {str(e)}"],
                    )
                )
        return results

    return asyncio.run(_search_all())
