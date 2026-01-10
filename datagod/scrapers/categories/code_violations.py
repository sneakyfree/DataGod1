"""
Code Violations / Code Enforcement Scraper
==========================================

Comprehensive scraper for municipal code violation records from
city/county code enforcement departments across all US states.

Data Sources:
- City Code Enforcement departments
- County Code Compliance offices
- Municipal courts
- Building departments

Violation Types:
- Building code violations
- Zoning violations
- Property maintenance violations
- Fire code violations
- Health and safety violations
- Environmental violations
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


class ViolationType(Enum):
    """Types of code violations"""
    # Building
    BUILDING_CODE = "building_code"
    UNPERMITTED_CONSTRUCTION = "unpermitted_construction"
    STRUCTURAL = "structural"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    MECHANICAL = "mechanical"

    # Zoning
    ZONING = "zoning"
    ILLEGAL_USE = "illegal_use"
    SETBACK = "setback"
    LOT_COVERAGE = "lot_coverage"
    PARKING = "parking"
    SIGNAGE = "signage"
    ILLEGAL_ADU = "illegal_adu"  # Accessory dwelling unit
    HOME_OCCUPATION = "home_occupation"

    # Property Maintenance
    PROPERTY_MAINTENANCE = "property_maintenance"
    OVERGROWN_VEGETATION = "overgrown_vegetation"
    DEBRIS_JUNK = "debris_junk"
    ABANDONED_VEHICLE = "abandoned_vehicle"
    GRAFFITI = "graffiti"
    TRASH_GARBAGE = "trash_garbage"
    INOPERABLE_VEHICLE = "inoperable_vehicle"

    # Housing
    HOUSING_CODE = "housing_code"
    SUBSTANDARD_HOUSING = "substandard_housing"
    OVERCROWDING = "overcrowding"
    HABITABILITY = "habitability"
    UNSAFE_CONDITIONS = "unsafe_conditions"

    # Fire Safety
    FIRE_CODE = "fire_code"
    FIRE_HAZARD = "fire_hazard"
    BLOCKED_EGRESS = "blocked_egress"
    SMOKE_DETECTOR = "smoke_detector"
    FIRE_EXTINGUISHER = "fire_extinguisher"

    # Environmental / Health
    ENVIRONMENTAL = "environmental"
    STORMWATER = "stormwater"
    EROSION = "erosion"
    HAZARDOUS_MATERIALS = "hazardous_materials"
    NOISE = "noise"
    ODOR = "odor"
    PEST_INFESTATION = "pest_infestation"
    SWIMMING_POOL = "swimming_pool"

    # Business
    BUSINESS_LICENSE = "business_license"
    OPERATING_WITHOUT_PERMIT = "operating_without_permit"
    SHORT_TERM_RENTAL = "short_term_rental"

    # Other
    NUISANCE = "nuisance"
    BLIGHT = "blight"
    OTHER = "other"


class ViolationStatus(Enum):
    """Status of code violation"""
    OPEN = "open"
    PENDING_INSPECTION = "pending_inspection"
    IN_COMPLIANCE = "in_compliance"
    CLOSED = "closed"
    ABATED = "abated"
    REFERRED_TO_COURT = "referred_to_court"
    HEARING_SCHEDULED = "hearing_scheduled"
    FINE_ISSUED = "fine_issued"
    LIEN_FILED = "lien_filed"
    ABATEMENT_IN_PROGRESS = "abatement_in_progress"
    APPEAL_FILED = "appeal_filed"
    DISMISSED = "dismissed"
    VOID = "void"


class PriorityLevel(Enum):
    """Priority/severity level of violation"""
    CRITICAL = "critical"  # Immediate hazard
    HIGH = "high"  # Significant hazard
    MEDIUM = "medium"  # Standard violation
    LOW = "low"  # Minor violation
    INFORMATIONAL = "informational"


class ComplaintSource(Enum):
    """Source of the violation complaint"""
    CITIZEN_COMPLAINT = "citizen_complaint"
    PROACTIVE_INSPECTION = "proactive_inspection"
    ANONYMOUS_COMPLAINT = "anonymous_complaint"
    REFERRED = "referred"  # From another department
    SELF_REPORTED = "self_reported"
    DRIVE_BY = "drive_by"
    PERMIT_INSPECTION = "permit_inspection"
    OTHER = "other"


@dataclass
class ViolationProperty:
    """Property where violation occurred"""
    address: str
    city: str
    state: str
    zip_code: Optional[str] = None
    county: Optional[str] = None

    # Property identification
    apn: Optional[str] = None  # Assessor's Parcel Number
    parcel_id: Optional[str] = None
    lot: Optional[str] = None
    block: Optional[str] = None

    # Property details
    property_type: Optional[str] = None  # Residential, Commercial, etc.
    zoning: Optional[str] = None

    # Coordinates
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class PropertyOwner:
    """Property owner of violation property"""
    name: str

    # Contact info
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    # If business
    company_name: Optional[str] = None


@dataclass
class ViolationInspection:
    """Inspection related to a violation"""
    inspection_date: date
    inspector_name: Optional[str] = None
    inspector_id: Optional[str] = None

    inspection_type: Optional[str] = None  # Initial, follow-up, reinspection
    result: Optional[str] = None  # Pass, fail, partial compliance
    notes: Optional[str] = None

    next_inspection_date: Optional[date] = None


@dataclass
class ViolationFine:
    """Fine or penalty associated with violation"""
    amount: float
    issue_date: date

    fine_type: Optional[str] = None  # Administrative, civil, etc.
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    paid_amount: Optional[float] = None

    is_paid: bool = False
    daily_penalty: Optional[float] = None  # Daily accruing fine


@dataclass
class ViolationHearing:
    """Administrative hearing for violation"""
    hearing_date: date
    hearing_time: Optional[str] = None
    location: Optional[str] = None

    hearing_type: Optional[str] = None  # Administrative, appeal, etc.
    hearing_officer: Optional[str] = None
    result: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class CodeViolationRecord:
    """Code violation record"""
    case_number: str
    violation_type: ViolationType
    status: ViolationStatus

    # Description
    description: str
    code_section: Optional[str] = None  # Municipal code section violated
    violation_code: Optional[str] = None

    # Priority
    priority: PriorityLevel = PriorityLevel.MEDIUM

    # Property
    property_info: Optional[ViolationProperty] = None
    property_owner: Optional[PropertyOwner] = None

    # Dates
    complaint_date: Optional[date] = None
    open_date: Optional[date] = None
    compliance_date: Optional[date] = None
    close_date: Optional[date] = None

    # Deadline
    compliance_deadline: Optional[date] = None
    days_open: Optional[int] = None

    # Source
    complaint_source: ComplaintSource = ComplaintSource.CITIZEN_COMPLAINT
    complainant_name: Optional[str] = None  # Usually redacted

    # Inspections
    inspections: List[ViolationInspection] = field(default_factory=list)
    inspection_count: int = 0

    # Fines and penalties
    fines: List[ViolationFine] = field(default_factory=list)
    total_fines: float = 0.0
    lien_amount: Optional[float] = None
    lien_filed: bool = False

    # Hearings
    hearings: List[ViolationHearing] = field(default_factory=list)

    # Related
    related_cases: List[str] = field(default_factory=list)
    related_permits: List[str] = field(default_factory=list)

    # Enforcement actions
    citation_issued: bool = False
    citation_number: Optional[str] = None
    abatement_ordered: bool = False
    abatement_completed: bool = False

    # Source info
    source: str = ""
    source_url: Optional[str] = None
    retrieved_date: date = field(default_factory=date.today)

    def is_active(self) -> bool:
        """Check if violation is still active"""
        return self.status in [
            ViolationStatus.OPEN,
            ViolationStatus.PENDING_INSPECTION,
            ViolationStatus.REFERRED_TO_COURT,
            ViolationStatus.HEARING_SCHEDULED,
            ViolationStatus.FINE_ISSUED,
            ViolationStatus.ABATEMENT_IN_PROGRESS,
            ViolationStatus.APPEAL_FILED,
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'case_number': self.case_number,
            'violation_type': self.violation_type.value,
            'status': self.status.value,
            'description': self.description,
            'code_section': self.code_section,
            'priority': self.priority.value,
            'property': {
                'address': self.property_info.address,
                'city': self.property_info.city,
                'apn': self.property_info.apn,
            } if self.property_info else None,
            'property_owner': {
                'name': self.property_owner.name,
            } if self.property_owner else None,
            'complaint_date': self.complaint_date.isoformat() if self.complaint_date else None,
            'compliance_deadline': self.compliance_deadline.isoformat() if self.compliance_deadline else None,
            'inspection_count': self.inspection_count,
            'total_fines': self.total_fines,
            'lien_filed': self.lien_filed,
            'citation_issued': self.citation_issued,
            'is_active': self.is_active(),
            'source': self.source,
        }


# Major city code enforcement configurations
CITY_CODE_ENFORCEMENT: Dict[str, Dict[str, Any]] = {
    # California
    'CA_LOS_ANGELES': {
        'name': 'Los Angeles Code Enforcement',
        'department': 'Department of Building and Safety',
        'url': 'https://www.ladbs.org/',
        'search_url': 'https://www.ladbsservices2.lacity.org/OnlineServices/CESearch',
        'api_url': 'https://data.lacity.org/resource/dvkr-q27u.json',
        'api_available': True,
        'code_name': 'Los Angeles Municipal Code',
    },
    'CA_SAN_FRANCISCO': {
        'name': 'San Francisco Code Enforcement',
        'department': 'Department of Building Inspection',
        'url': 'https://sfdbi.org/',
        'search_url': 'https://dbiweb02.sfgov.org/dbipts/default.aspx',
        'api_url': 'https://data.sfgov.org/resource/nbtm-fbw5.json',
        'api_available': True,
    },
    'CA_SAN_DIEGO': {
        'name': 'San Diego Code Enforcement',
        'department': 'Development Services',
        'url': 'https://www.sandiego.gov/development-services/codes',
        'search_url': 'https://www.sandiego.gov/development-services/codes/enforcement',
        'api_available': False,
    },
    'CA_SAN_JOSE': {
        'name': 'San Jose Code Enforcement',
        'department': 'Code Enforcement Division',
        'url': 'https://www.sanjoseca.gov/your-government/departments/planning-building-code-enforcement',
        'search_url': None,
        'api_available': False,
    },

    # Texas
    'TX_HOUSTON': {
        'name': 'Houston Code Enforcement',
        'department': 'Administration and Regulatory Affairs',
        'url': 'https://www.houstontx.gov/ara/',
        'search_url': 'https://www.houstontx.gov/ara/ncd/',
        'api_url': 'https://data.houstontx.gov/resource/mqhp-bsud.json',
        'api_available': True,
    },
    'TX_SAN_ANTONIO': {
        'name': 'San Antonio Code Compliance',
        'department': 'Development Services',
        'url': 'https://www.sanantonio.gov/DSD/Code-Compliance',
        'search_url': 'https://www.sanantonio.gov/DSD/Code-Compliance/Report-a-Violation',
        'api_available': False,
    },
    'TX_DALLAS': {
        'name': 'Dallas Code Compliance',
        'department': 'Code Compliance Services',
        'url': 'https://dallascityhall.com/departments/codecompliance/',
        'search_url': 'https://dallascityhall.com/departments/codecompliance/Pages/complaint-search.aspx',
        'api_url': 'https://www.dallasopendata.com/resource/9dqi-f8ib.json',
        'api_available': True,
    },
    'TX_AUSTIN': {
        'name': 'Austin Code',
        'department': 'Austin Code Department',
        'url': 'https://www.austintexas.gov/department/austin-code',
        'search_url': 'https://abc.austintexas.gov/web/permit/public-search-other',
        'api_url': 'https://data.austintexas.gov/resource/iytv-7dci.json',
        'api_available': True,
    },

    # Florida
    'FL_MIAMI': {
        'name': 'Miami Code Enforcement',
        'department': 'Department of Code Enforcement',
        'url': 'https://www.miamigov.com/Government/Departments-Organizations/Code-Enforcement',
        'search_url': None,
        'api_available': False,
    },
    'FL_JACKSONVILLE': {
        'name': 'Jacksonville Code Enforcement',
        'department': 'Municipal Code Compliance Division',
        'url': 'https://www.coj.net/departments/regulatory-compliance',
        'search_url': 'https://apps.coj.net/RCMS_Reports/',
        'api_available': False,
    },
    'FL_TAMPA': {
        'name': 'Tampa Code Enforcement',
        'department': 'Code Enforcement',
        'url': 'https://www.tampa.gov/code-enforcement',
        'search_url': None,
        'api_available': False,
    },

    # New York
    'NY_NEW_YORK_CITY': {
        'name': 'NYC Code Enforcement',
        'department': 'Department of Buildings (DOB) / HPD',
        'url': 'https://www1.nyc.gov/site/buildings/index.page',
        'search_url': 'https://a810-bisweb.nyc.gov/bisweb/bispi00.jsp',
        'api_url': 'https://data.cityofnewyork.us/resource/3h2n-5cm9.json',
        'api_available': True,
        'notes': 'DOB for building, HPD for housing',
    },
    'NY_BUFFALO': {
        'name': 'Buffalo Code Enforcement',
        'department': 'Division of Citizen Services',
        'url': 'https://www.buffalony.gov/468/Code-Enforcement',
        'search_url': None,
        'api_available': False,
    },

    # Illinois
    'IL_CHICAGO': {
        'name': 'Chicago Code Enforcement',
        'department': 'Department of Buildings',
        'url': 'https://www.chicago.gov/city/en/depts/bldgs.html',
        'search_url': 'https://webapps1.chicago.gov/buildingviolations/',
        'api_url': 'https://data.cityofchicago.org/resource/22u3-xenr.json',
        'api_available': True,
    },

    # Arizona
    'AZ_PHOENIX': {
        'name': 'Phoenix Code Enforcement',
        'department': 'Planning and Development',
        'url': 'https://www.phoenix.gov/pdd/code-enforcement',
        'search_url': 'https://www.phoenix.gov/pdd/code-enforcement',
        'api_available': False,
    },
    'AZ_TUCSON': {
        'name': 'Tucson Code Enforcement',
        'department': 'Planning and Development Services',
        'url': 'https://www.tucsonaz.gov/pdsd/code-enforcement',
        'search_url': None,
        'api_available': False,
    },

    # Nevada
    'NV_LAS_VEGAS': {
        'name': 'Las Vegas Code Enforcement',
        'department': 'Code Enforcement',
        'url': 'https://www.lasvegasnevada.gov/Government/Departments/Code-Enforcement',
        'search_url': 'https://www.lasvegasnevada.gov/Government/Departments/Code-Enforcement/Code-Enforcement-Search',
        'api_available': False,
    },

    # Georgia
    'GA_ATLANTA': {
        'name': 'Atlanta Code Enforcement',
        'department': 'Office of Buildings',
        'url': 'https://www.atlantaga.gov/government/departments/city-planning/office-of-buildings',
        'search_url': None,
        'api_available': False,
    },

    # Washington
    'WA_SEATTLE': {
        'name': 'Seattle Code Enforcement',
        'department': 'Seattle Department of Construction & Inspections',
        'url': 'https://www.seattle.gov/sdci/codes/code-compliance',
        'search_url': 'https://web6.seattle.gov/dpd/edms/',
        'api_url': 'https://data.seattle.gov/resource/ez4a-iug7.json',
        'api_available': True,
    },

    # Colorado
    'CO_DENVER': {
        'name': 'Denver Code Enforcement',
        'department': 'Community Planning and Development',
        'url': 'https://www.denvergov.org/Government/Agencies-Departments-Offices/Community-Planning-and-Development/Code-Enforcement',
        'search_url': 'https://www.denvergov.org/Government/Agencies-Departments-Offices/Community-Planning-and-Development/Code-Enforcement/Complaint-Search',
        'api_url': 'https://data.denvergov.org/resource/abch-bpts.json',
        'api_available': True,
    },

    # Massachusetts
    'MA_BOSTON': {
        'name': 'Boston Code Enforcement',
        'department': 'Inspectional Services Department',
        'url': 'https://www.boston.gov/departments/inspectional-services',
        'search_url': 'https://data.boston.gov/dataset/code-enforcement-building-and-property-violations',
        'api_url': 'https://data.boston.gov/resource/w39n-pvs8.json',
        'api_available': True,
    },

    # Pennsylvania
    'PA_PHILADELPHIA': {
        'name': 'Philadelphia L&I',
        'department': 'Department of Licenses and Inspections',
        'url': 'https://www.phila.gov/departments/department-of-licenses-and-inspections/',
        'search_url': 'https://li.phila.gov/',
        'api_url': 'https://phl.carto.com/api/v2/sql',
        'api_available': True,
    },

    # Michigan
    'MI_DETROIT': {
        'name': 'Detroit BSEED',
        'department': 'Buildings, Safety Engineering, and Environmental Department',
        'url': 'https://detroitmi.gov/departments/buildings-safety-engineering-and-environmental-department',
        'search_url': 'https://data.detroitmi.gov/datasets/blight-violations',
        'api_url': 'https://data.detroitmi.gov/resource/s7jj-7xqf.json',
        'api_available': True,
    },

    # Ohio
    'OH_CLEVELAND': {
        'name': 'Cleveland Code Enforcement',
        'department': 'Building and Housing',
        'url': 'https://www.clevelandohio.gov/building-housing',
        'search_url': None,
        'api_available': False,
    },
    'OH_COLUMBUS': {
        'name': 'Columbus Code Enforcement',
        'department': 'Department of Building and Zoning Services',
        'url': 'https://www.columbus.gov/bzs/',
        'search_url': 'https://etrakit.columbus.gov/etrakit/',
        'api_available': False,
    },

    # North Carolina
    'NC_CHARLOTTE': {
        'name': 'Charlotte Code Enforcement',
        'department': 'Code Enforcement',
        'url': 'https://charlottenc.gov/Code/Pages/default.aspx',
        'search_url': 'https://charlottenc.gov/Code/Pages/caseSearch.aspx',
        'api_url': 'https://data.charlottenc.gov/resource/4jdq-yfqs.json',
        'api_available': True,
    },

    # Tennessee
    'TN_NASHVILLE': {
        'name': 'Nashville Codes Administration',
        'department': 'Codes Administration',
        'url': 'https://www.nashville.gov/departments/codes',
        'search_url': 'https://www.nashville.gov/departments/codes/code-enforcement',
        'api_url': 'https://data.nashville.gov/resource/xz9s-nyhn.json',
        'api_available': True,
    },

    # Oregon
    'OR_PORTLAND': {
        'name': 'Portland Code Enforcement',
        'department': 'Bureau of Development Services',
        'url': 'https://www.portlandoregon.gov/bds/',
        'search_url': 'https://www.portlandmaps.com/',
        'api_available': False,
    },

    # Minnesota
    'MN_MINNEAPOLIS': {
        'name': 'Minneapolis Regulatory Services',
        'department': 'Regulatory Services',
        'url': 'https://www.minneapolismn.gov/government/departments/regulatory-services/',
        'search_url': None,
        'api_available': False,
    },

    # Louisiana
    'LA_NEW_ORLEANS': {
        'name': 'New Orleans Code Enforcement',
        'department': 'Code Enforcement & Hearings Bureau',
        'url': 'https://nola.gov/safety-and-permits/code-enforcement/',
        'search_url': 'https://blightstat.nola.gov/',
        'api_url': 'https://data.nola.gov/resource/htnw-whx3.json',
        'api_available': True,
    },
}


class CodeViolationsAPI:
    """Main API class for code violation records"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html',
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.base_headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request with error handling"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.base_headers)

        try:
            async with self.session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'json' in content_type:
                        return await response.json()
                    else:
                        text = await response.text()
                        return {'html': text}
                else:
                    logger.warning(f"Request failed with status {response.status}: {url}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {url}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def _parse_violation_type(self, type_str: str) -> ViolationType:
        """Parse violation type from string"""
        type_str = type_str.lower() if type_str else ""

        # Building related
        if 'unpermitted' in type_str or 'without permit' in type_str:
            return ViolationType.UNPERMITTED_CONSTRUCTION
        elif 'electrical' in type_str:
            return ViolationType.ELECTRICAL
        elif 'plumbing' in type_str:
            return ViolationType.PLUMBING
        elif 'mechanical' in type_str or 'hvac' in type_str:
            return ViolationType.MECHANICAL
        elif 'structural' in type_str:
            return ViolationType.STRUCTURAL
        elif 'building' in type_str:
            return ViolationType.BUILDING_CODE

        # Zoning related
        elif 'zoning' in type_str:
            return ViolationType.ZONING
        elif 'illegal use' in type_str or 'prohibited use' in type_str:
            return ViolationType.ILLEGAL_USE
        elif 'setback' in type_str:
            return ViolationType.SETBACK
        elif 'parking' in type_str:
            return ViolationType.PARKING
        elif 'sign' in type_str:
            return ViolationType.SIGNAGE
        elif 'adu' in type_str or 'accessory' in type_str:
            return ViolationType.ILLEGAL_ADU

        # Property maintenance
        elif 'vegetation' in type_str or 'overgrown' in type_str or 'weeds' in type_str:
            return ViolationType.OVERGROWN_VEGETATION
        elif 'debris' in type_str or 'junk' in type_str:
            return ViolationType.DEBRIS_JUNK
        elif 'abandoned vehicle' in type_str:
            return ViolationType.ABANDONED_VEHICLE
        elif 'graffiti' in type_str:
            return ViolationType.GRAFFITI
        elif 'trash' in type_str or 'garbage' in type_str:
            return ViolationType.TRASH_GARBAGE
        elif 'inoperable' in type_str:
            return ViolationType.INOPERABLE_VEHICLE
        elif 'maintenance' in type_str or 'property' in type_str:
            return ViolationType.PROPERTY_MAINTENANCE

        # Housing
        elif 'housing' in type_str:
            return ViolationType.HOUSING_CODE
        elif 'substandard' in type_str:
            return ViolationType.SUBSTANDARD_HOUSING
        elif 'habitability' in type_str:
            return ViolationType.HABITABILITY
        elif 'unsafe' in type_str:
            return ViolationType.UNSAFE_CONDITIONS

        # Fire safety
        elif 'fire' in type_str:
            return ViolationType.FIRE_CODE
        elif 'smoke detector' in type_str or 'alarm' in type_str:
            return ViolationType.SMOKE_DETECTOR
        elif 'egress' in type_str or 'exit' in type_str:
            return ViolationType.BLOCKED_EGRESS

        # Environmental
        elif 'stormwater' in type_str:
            return ViolationType.STORMWATER
        elif 'erosion' in type_str:
            return ViolationType.EROSION
        elif 'hazardous' in type_str:
            return ViolationType.HAZARDOUS_MATERIALS
        elif 'noise' in type_str:
            return ViolationType.NOISE
        elif 'pool' in type_str or 'swimming' in type_str:
            return ViolationType.SWIMMING_POOL
        elif 'pest' in type_str or 'rodent' in type_str:
            return ViolationType.PEST_INFESTATION

        # Business
        elif 'license' in type_str and 'business' in type_str:
            return ViolationType.BUSINESS_LICENSE
        elif 'short term' in type_str or 'airbnb' in type_str:
            return ViolationType.SHORT_TERM_RENTAL

        # General
        elif 'nuisance' in type_str:
            return ViolationType.NUISANCE
        elif 'blight' in type_str:
            return ViolationType.BLIGHT

        return ViolationType.OTHER

    def _parse_status(self, status_str: str) -> ViolationStatus:
        """Parse violation status from string"""
        status_str = status_str.lower() if status_str else ""

        if 'open' in status_str:
            return ViolationStatus.OPEN
        elif 'pending' in status_str and 'inspection' in status_str:
            return ViolationStatus.PENDING_INSPECTION
        elif 'compliance' in status_str or 'complied' in status_str:
            return ViolationStatus.IN_COMPLIANCE
        elif 'closed' in status_str:
            return ViolationStatus.CLOSED
        elif 'abated' in status_str:
            return ViolationStatus.ABATED
        elif 'court' in status_str or 'referred' in status_str:
            return ViolationStatus.REFERRED_TO_COURT
        elif 'hearing' in status_str:
            return ViolationStatus.HEARING_SCHEDULED
        elif 'fine' in status_str:
            return ViolationStatus.FINE_ISSUED
        elif 'lien' in status_str:
            return ViolationStatus.LIEN_FILED
        elif 'appeal' in status_str:
            return ViolationStatus.APPEAL_FILED
        elif 'dismissed' in status_str or 'void' in status_str:
            return ViolationStatus.DISMISSED

        return ViolationStatus.OPEN

    async def search_by_address(
        self,
        address: str,
        city: str,
        state: str
    ) -> List[CodeViolationRecord]:
        """Search for code violations by property address"""
        results = []

        # Find matching city
        city_key = self._find_city_key(city, state)
        if not city_key:
            logger.warning(f"No configuration for {city}, {state}")
            return results

        config = CITY_CODE_ENFORCEMENT[city_key]

        if config.get('api_available') and config.get('api_url'):
            # Use Open Data API
            params = {
                '$where': f"upper(address) like '%{address.upper()}%'",
                '$limit': 100,
                '$order': 'violation_date DESC',
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list):
                for record in data:
                    violation = self._parse_open_data_record(record, city_key)
                    if violation:
                        results.append(violation)

        return results

    async def search_by_owner(
        self,
        owner_name: str,
        city: str,
        state: str
    ) -> List[CodeViolationRecord]:
        """Search for code violations by property owner"""
        results = []

        city_key = self._find_city_key(city, state)
        if not city_key:
            return results

        logger.info(f"Searching violations for owner {owner_name} in {city}")

        return results

    async def search_by_case_number(
        self,
        case_number: str,
        city: str,
        state: str
    ) -> Optional[CodeViolationRecord]:
        """Search for a specific violation by case number"""
        city_key = self._find_city_key(city, state)
        if not city_key:
            return None

        config = CITY_CODE_ENFORCEMENT[city_key]

        if config.get('api_available') and config.get('api_url'):
            params = {
                '$where': f"case_number = '{case_number}' OR violation_id = '{case_number}'",
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list) and len(data) > 0:
                return self._parse_open_data_record(data[0], city_key)

        return None

    async def get_open_violations(
        self,
        city: str,
        state: str,
        violation_type: Optional[ViolationType] = None
    ) -> List[CodeViolationRecord]:
        """Get all open violations for a city"""
        results = []

        city_key = self._find_city_key(city, state)
        if not city_key:
            return results

        config = CITY_CODE_ENFORCEMENT[city_key]

        if config.get('api_available') and config.get('api_url'):
            where_clause = "status = 'OPEN' OR status = 'Open'"
            if violation_type:
                where_clause += f" AND violation_type like '%{violation_type.value}%'"

            params = {
                '$where': where_clause,
                '$limit': 500,
                '$order': 'violation_date DESC',
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list):
                for record in data:
                    violation = self._parse_open_data_record(record, city_key)
                    if violation:
                        results.append(violation)

        return results

    async def get_recent_violations(
        self,
        city: str,
        state: str,
        days: int = 30
    ) -> List[CodeViolationRecord]:
        """Get recently opened violations"""
        results = []

        city_key = self._find_city_key(city, state)
        if not city_key:
            return results

        config = CITY_CODE_ENFORCEMENT[city_key]

        if config.get('api_available') and config.get('api_url'):
            from datetime import timedelta
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            params = {
                '$where': f"violation_date >= '{start_date}'",
                '$limit': 500,
                '$order': 'violation_date DESC',
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list):
                for record in data:
                    violation = self._parse_open_data_record(record, city_key)
                    if violation:
                        results.append(violation)

        return results

    async def get_violations_with_fines(
        self,
        city: str,
        state: str
    ) -> List[CodeViolationRecord]:
        """Get violations with outstanding fines"""
        results = []

        city_key = self._find_city_key(city, state)
        if not city_key:
            return results

        config = CITY_CODE_ENFORCEMENT[city_key]

        if config.get('api_available') and config.get('api_url'):
            params = {
                '$where': "fine_amount > 0",
                '$limit': 500,
                '$order': 'fine_amount DESC',
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list):
                for record in data:
                    violation = self._parse_open_data_record(record, city_key)
                    if violation and violation.total_fines > 0:
                        results.append(violation)

        return results

    def _find_city_key(self, city: str, state: str) -> Optional[str]:
        """Find the city configuration key"""
        city_upper = city.upper().replace(' ', '_')
        state_upper = state.upper()

        # Direct match
        key = f"{state_upper}_{city_upper}"
        if key in CITY_CODE_ENFORCEMENT:
            return key

        # Try common variations
        city_map = {
            ('NEW YORK', 'NY'): 'NY_NEW_YORK_CITY',
            ('NYC', 'NY'): 'NY_NEW_YORK_CITY',
            ('LA', 'CA'): 'CA_LOS_ANGELES',
        }

        return city_map.get((city.upper(), state_upper))

    def _parse_open_data_record(self, record: Dict, city_key: str) -> Optional[CodeViolationRecord]:
        """Parse Open Data API record into CodeViolationRecord"""
        try:
            property_info = ViolationProperty(
                address=record.get('address') or record.get('location') or '',
                city=record.get('city', city_key.split('_')[-1]),
                state=city_key.split('_')[0],
                zip_code=record.get('zip') or record.get('zip_code'),
            )

            # Parse date
            date_str = record.get('violation_date') or record.get('date_opened', '')
            if date_str:
                if 'T' in date_str:
                    complaint_date = datetime.fromisoformat(date_str.replace('Z', '')).date()
                else:
                    complaint_date = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
            else:
                complaint_date = None

            # Parse fines
            total_fines = 0.0
            if record.get('fine_amount'):
                try:
                    total_fines = float(record['fine_amount'])
                except (ValueError, TypeError):
                    pass

            return CodeViolationRecord(
                case_number=str(record.get('case_number') or record.get('violation_id') or record.get('id', '')),
                violation_type=self._parse_violation_type(record.get('violation_type', '')),
                status=self._parse_status(record.get('status', '')),
                description=record.get('description') or record.get('violation_description', ''),
                code_section=record.get('code_section') or record.get('violation_code'),
                property_info=property_info,
                complaint_date=complaint_date,
                total_fines=total_fines,
                source=CITY_CODE_ENFORCEMENT.get(city_key, {}).get('name', city_key),
                source_url=CITY_CODE_ENFORCEMENT.get(city_key, {}).get('url'),
            )
        except Exception as e:
            logger.error(f"Error parsing record: {e}")
            return None

    def get_city_info(self, city: str, state: str) -> Optional[Dict[str, Any]]:
        """Get code enforcement information for a city"""
        city_key = self._find_city_key(city, state)
        if city_key:
            return CITY_CODE_ENFORCEMENT.get(city_key)
        return None

    def get_available_cities(self) -> Dict[str, Dict[str, Any]]:
        """Get all configured cities"""
        return {
            k: {
                'name': v['name'],
                'department': v.get('department'),
                'api_available': v.get('api_available', False),
                'url': v.get('url'),
            }
            for k, v in CITY_CODE_ENFORCEMENT.items()
        }

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics"""
        total_cities = len(CITY_CODE_ENFORCEMENT)
        with_api = sum(1 for c in CITY_CODE_ENFORCEMENT.values() if c.get('api_available'))

        # Count by state
        states = {}
        for key in CITY_CODE_ENFORCEMENT.keys():
            state = key.split('_')[0]
            states[state] = states.get(state, 0) + 1

        return {
            'total_cities': total_cities,
            'cities_with_api': with_api,
            'api_coverage_percent': round(with_api / total_cities * 100, 1),
            'states_covered': len(states),
            'cities_by_state': states,
        }


# Synchronous wrapper functions
def search_violations_by_address(
    address: str,
    city: str,
    state: str
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching violations by address"""
    async def _search():
        async with CodeViolationsAPI() as api:
            results = await api.search_by_address(address, city, state)
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def search_violations_by_owner(
    owner_name: str,
    city: str,
    state: str
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching violations by owner"""
    async def _search():
        async with CodeViolationsAPI() as api:
            results = await api.search_by_owner(owner_name, city, state)
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def get_violation_by_case(
    case_number: str,
    city: str,
    state: str
) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for getting violation by case number"""
    async def _get():
        async with CodeViolationsAPI() as api:
            result = await api.search_by_case_number(case_number, city, state)
            return result.to_dict() if result else None

    return asyncio.run(_get())


def get_open_violations(
    city: str,
    state: str,
    violation_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for getting open violations"""
    async def _get():
        async with CodeViolationsAPI() as api:
            vtype = ViolationType(violation_type) if violation_type else None
            results = await api.get_open_violations(city, state, vtype)
            return [r.to_dict() for r in results]

    return asyncio.run(_get())


def get_recent_violations(
    city: str,
    state: str,
    days: int = 30
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for getting recent violations"""
    async def _get():
        async with CodeViolationsAPI() as api:
            results = await api.get_recent_violations(city, state, days)
            return [r.to_dict() for r in results]

    return asyncio.run(_get())


def get_city_code_enforcement_info(city: str, state: str) -> Optional[Dict[str, Any]]:
    """Get code enforcement information for a city"""
    api = CodeViolationsAPI()
    return api.get_city_info(city, state)


def get_available_cities() -> Dict[str, Dict[str, Any]]:
    """Get all configured cities"""
    api = CodeViolationsAPI()
    return api.get_available_cities()


def get_coverage_stats() -> Dict[str, Any]:
    """Get coverage statistics for code violations"""
    api = CodeViolationsAPI()
    return api.get_coverage_stats()


if __name__ == "__main__":
    # Test the API
    print("Code Violations / Code Enforcement Scraper")
    print("=" * 50)

    stats = get_coverage_stats()
    print(f"\nCoverage Statistics:")
    print(f"  Total Cities: {stats['total_cities']}")
    print(f"  Cities with API: {stats['cities_with_api']} ({stats['api_coverage_percent']}%)")
    print(f"  States Covered: {stats['states_covered']}")

    print(f"\nCities by State:")
    for state, count in sorted(stats['cities_by_state'].items()):
        print(f"  {state}: {count}")

    print("\nCities with API Access:")
    cities = get_available_cities()
    for key, info in cities.items():
        if info.get('api_available'):
            print(f"  {key}: {info['name']}")
