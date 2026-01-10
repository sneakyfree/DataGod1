"""
Restaurant Inspections Scraper
==============================

Comprehensive scraper for restaurant and food establishment inspection records
from city/county health departments across all US states.

Data Sources:
- County/City Health Departments
- State Health Department APIs
- FDA Food Facility Registration
- Yelp Health Scores (where available)

Inspection Types:
- Routine inspections
- Follow-up inspections
- Complaint investigations
- Pre-opening inspections
- Re-inspections
- Permit renewals
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


class InspectionType(Enum):
    """Types of restaurant inspections"""
    ROUTINE = "routine"
    FOLLOW_UP = "follow_up"
    COMPLAINT = "complaint"
    PRE_OPENING = "pre_opening"
    RE_INSPECTION = "re_inspection"
    PERMIT_RENEWAL = "permit_renewal"
    CHANGE_OF_OWNERSHIP = "change_of_ownership"
    CONSULTATION = "consultation"
    FOODBORNE_ILLNESS = "foodborne_illness"
    ADMINISTRATIVE = "administrative"
    UNKNOWN = "unknown"


class InspectionResult(Enum):
    """Inspection result categories"""
    PASS = "pass"
    CONDITIONAL_PASS = "conditional_pass"
    FAIL = "fail"
    CLOSED = "closed"
    REINSPECTION_REQUIRED = "reinspection_required"
    PENDING = "pending"
    NOT_RATED = "not_rated"


class FacilityType(Enum):
    """Types of food establishments"""
    RESTAURANT = "restaurant"
    FAST_FOOD = "fast_food"
    CAFETERIA = "cafeteria"
    FOOD_TRUCK = "food_truck"
    CATERING = "catering"
    BAR_TAVERN = "bar_tavern"
    BAKERY = "bakery"
    DELI = "deli"
    GROCERY_STORE = "grocery_store"
    CONVENIENCE_STORE = "convenience_store"
    SUPERMARKET = "supermarket"
    SCHOOL_CAFETERIA = "school_cafeteria"
    HOSPITAL_CAFETERIA = "hospital_cafeteria"
    NURSING_HOME = "nursing_home"
    DAYCARE = "daycare"
    COMMISSARY = "commissary"
    MOBILE_FOOD = "mobile_food"
    TEMPORARY_EVENT = "temporary_event"
    FARMERS_MARKET = "farmers_market"
    COFFEE_SHOP = "coffee_shop"
    ICE_CREAM = "ice_cream"
    OTHER = "other"


class ViolationSeverity(Enum):
    """Severity levels for violations"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    CORRECTED_ON_SITE = "corrected_on_site"
    OBSERVATION = "observation"


class ViolationCategory(Enum):
    """Categories of health code violations"""
    FOOD_TEMPERATURE = "food_temperature"
    FOOD_SOURCE = "food_source"
    FOOD_CONTAMINATION = "food_contamination"
    EMPLOYEE_HYGIENE = "employee_hygiene"
    HANDWASHING = "handwashing"
    CROSS_CONTAMINATION = "cross_contamination"
    EQUIPMENT_SANITATION = "equipment_sanitation"
    FACILITY_MAINTENANCE = "facility_maintenance"
    PEST_CONTROL = "pest_control"
    CHEMICAL_STORAGE = "chemical_storage"
    WASTE_DISPOSAL = "waste_disposal"
    WATER_SUPPLY = "water_supply"
    SEWAGE_DISPOSAL = "sewage_disposal"
    VENTILATION = "ventilation"
    LIGHTING = "lighting"
    RESTROOM = "restroom"
    STORAGE = "storage"
    LABELING = "labeling"
    ALLERGEN = "allergen"
    PERMIT_LICENSE = "permit_license"
    OTHER = "other"


@dataclass
class Violation:
    """Individual violation from an inspection"""
    code: str
    description: str
    severity: ViolationSeverity
    category: ViolationCategory = ViolationCategory.OTHER
    points: Optional[int] = None
    corrected: bool = False
    corrected_date: Optional[date] = None
    repeat_violation: bool = False
    inspector_notes: Optional[str] = None


@dataclass
class FoodEstablishment:
    """Food establishment/restaurant details"""
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    facility_type: FacilityType

    permit_number: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Business details
    owner_name: Optional[str] = None
    dba_name: Optional[str] = None
    corporate_name: Optional[str] = None

    # Permit info
    permit_status: Optional[str] = None
    permit_issue_date: Optional[date] = None
    permit_expiration_date: Optional[date] = None

    # Risk category
    risk_category: Optional[str] = None  # High/Medium/Low
    seating_capacity: Optional[int] = None


@dataclass
class InspectionRecord:
    """Restaurant inspection record"""
    inspection_id: str
    establishment: FoodEstablishment

    inspection_date: date
    inspection_type: InspectionType
    result: InspectionResult

    # Scoring
    score: Optional[int] = None  # Numeric score (0-100 typically)
    grade: Optional[str] = None  # Letter grade (A, B, C, etc.)

    # Violations
    violations: List[Violation] = field(default_factory=list)
    critical_violations: int = 0
    major_violations: int = 0
    minor_violations: int = 0

    # Inspector info
    inspector_id: Optional[str] = None
    inspector_name: Optional[str] = None

    # Follow-up
    follow_up_required: bool = False
    follow_up_date: Optional[date] = None
    closure_ordered: bool = False

    # Metadata
    source: str = ""
    source_url: Optional[str] = None
    retrieved_date: date = field(default_factory=date.today)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'inspection_id': self.inspection_id,
            'establishment': {
                'name': self.establishment.name,
                'address': self.establishment.address,
                'city': self.establishment.city,
                'state': self.establishment.state,
                'zip_code': self.establishment.zip_code,
                'facility_type': self.establishment.facility_type.value,
                'permit_number': self.establishment.permit_number,
            },
            'inspection_date': self.inspection_date.isoformat(),
            'inspection_type': self.inspection_type.value,
            'result': self.result.value,
            'score': self.score,
            'grade': self.grade,
            'violations': [
                {
                    'code': v.code,
                    'description': v.description,
                    'severity': v.severity.value,
                    'category': v.category.value,
                    'corrected': v.corrected,
                }
                for v in self.violations
            ],
            'critical_violations': self.critical_violations,
            'major_violations': self.major_violations,
            'minor_violations': self.minor_violations,
            'follow_up_required': self.follow_up_required,
            'closure_ordered': self.closure_ordered,
            'source': self.source,
        }


# Major city/county health department configurations
JURISDICTION_INSPECTION_SOURCES: Dict[str, Dict[str, Any]] = {
    # California
    'CA_LOS_ANGELES': {
        'name': 'Los Angeles County',
        'url': 'http://publichealth.lacounty.gov/eh/food/',
        'api_url': 'https://data.lacounty.gov/resource/u2gf-a7cb.json',
        'api_available': True,
        'scoring_system': 'numeric',  # 0-100
        'grade_system': True,  # A, B, C grades
    },
    'CA_SAN_FRANCISCO': {
        'name': 'San Francisco',
        'url': 'https://www.sfdph.org/dph/EH/Food/default.asp',
        'api_url': 'https://data.sfgov.org/resource/pyih-qa8i.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': False,
    },
    'CA_SAN_DIEGO': {
        'name': 'San Diego County',
        'url': 'https://www.sandiegocounty.gov/content/sdc/deh/fhd/ffis/intro.html',
        'api_url': 'https://data.sandiegocounty.gov/resource/5zds-7jvk.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': True,
    },
    'CA_ORANGE': {
        'name': 'Orange County',
        'url': 'https://www.ocfoodinfo.com/',
        'api_url': None,
        'api_available': False,
        'scoring_system': 'numeric',
        'grade_system': False,
    },

    # Texas
    'TX_HOUSTON': {
        'name': 'City of Houston',
        'url': 'https://www.houstonhealth.org/services/restaurant-inspections',
        'api_url': 'https://data.houstontx.gov/resource/3nka-hgi3.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': False,
    },
    'TX_DALLAS': {
        'name': 'City of Dallas',
        'url': 'https://www.dallasopendata.com/Health-Human-Services/Restaurant-Inspection-Scores/dri5-wcct',
        'api_url': 'https://www.dallasopendata.com/resource/dri5-wcct.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': False,
    },
    'TX_AUSTIN': {
        'name': 'City of Austin',
        'url': 'https://www.austintexas.gov/department/food-establishment-inspection',
        'api_url': 'https://data.austintexas.gov/resource/ecmv-9xxi.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': False,
    },
    'TX_SAN_ANTONIO': {
        'name': 'City of San Antonio',
        'url': 'https://www.sanantonio.gov/Health/FoodLicensing',
        'api_url': 'https://data.sanantonio.gov/resource/k9zd-f3hj.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': False,
    },

    # New York
    'NY_NEW_YORK_CITY': {
        'name': 'New York City',
        'url': 'https://www1.nyc.gov/site/doh/services/restaurant-grades.page',
        'api_url': 'https://data.cityofnewyork.us/resource/43nn-pn8j.json',
        'api_available': True,
        'scoring_system': 'violation_points',  # Lower is better
        'grade_system': True,  # A, B, C, Grade Pending
    },

    # Florida
    'FL_MIAMI_DADE': {
        'name': 'Miami-Dade County',
        'url': 'https://www.miamidade.gov/global/economy/restaurant/home.page',
        'api_url': None,
        'api_available': False,
        'scoring_system': 'numeric',
        'grade_system': False,
    },
    'FL_BROWARD': {
        'name': 'Broward County',
        'url': 'https://www.broward.org/EnvironmentAndGrowth/EnvironmentalLicensing/Pages/RestaurantInspections.aspx',
        'api_url': None,
        'api_available': False,
        'scoring_system': 'numeric',
        'grade_system': False,
    },

    # Illinois
    'IL_CHICAGO': {
        'name': 'City of Chicago',
        'url': 'https://www.chicago.gov/city/en/depts/cdph/provdrs/inspections.html',
        'api_url': 'https://data.cityofchicago.org/resource/4ijn-s7e5.json',
        'api_available': True,
        'scoring_system': 'pass_fail',
        'grade_system': False,
    },

    # Nevada
    'NV_CLARK': {
        'name': 'Southern Nevada Health District',
        'url': 'https://www.southernnevadahealthdistrict.org/restaurants/',
        'api_url': 'https://opendata.snhd.org/resource/84zp-7n2u.json',
        'api_available': True,
        'scoring_system': 'demerits',  # Lower is better
        'grade_system': True,  # A, B, C
    },

    # Arizona
    'AZ_MARICOPA': {
        'name': 'Maricopa County',
        'url': 'https://www.maricopa.gov/734/Food-Inspection-Grades',
        'api_url': 'https://data.maricopa.gov/resource/mwnf-8h9x.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': True,
    },

    # Washington
    'WA_KING': {
        'name': 'King County',
        'url': 'https://kingcounty.gov/depts/health/environmental-health/food-safety/inspection-system.aspx',
        'api_url': 'https://data.kingcounty.gov/resource/f29f-zza5.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': False,
    },
    'WA_SEATTLE': {
        'name': 'City of Seattle',
        'url': 'https://www.seattle.gov/health/food-safety',
        'api_url': 'https://data.seattle.gov/resource/rndu-kxsi.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': False,
    },

    # Massachusetts
    'MA_BOSTON': {
        'name': 'City of Boston',
        'url': 'https://www.boston.gov/departments/inspectional-services',
        'api_url': 'https://data.boston.gov/resource/427a-3cn5.json',
        'api_available': True,
        'scoring_system': 'pass_fail',
        'grade_system': False,
    },

    # Georgia
    'GA_FULTON': {
        'name': 'Fulton County',
        'url': 'https://www.fultoncountyga.gov/services/health-services',
        'api_url': None,
        'api_available': False,
        'scoring_system': 'numeric',
        'grade_system': False,
    },

    # Colorado
    'CO_DENVER': {
        'name': 'City of Denver',
        'url': 'https://www.denvergov.org/Government/Agencies-Departments-Offices/Department-of-Public-Health-Environment',
        'api_url': 'https://data.denvergov.org/resource/4j98-qj9a.json',
        'api_available': True,
        'scoring_system': 'pass_fail',
        'grade_system': False,
    },

    # Pennsylvania
    'PA_PHILADELPHIA': {
        'name': 'City of Philadelphia',
        'url': 'https://www.phila.gov/services/food-licensing-and-inspections/',
        'api_url': 'https://phl.carto.com/api/v2/sql',
        'api_available': True,
        'scoring_system': 'pass_fail',
        'grade_system': False,
    },

    # North Carolina
    'NC_MECKLENBURG': {
        'name': 'Mecklenburg County',
        'url': 'https://www.mecknc.gov/HealthDepartment/EnvironmentalHealth/Pages/default.aspx',
        'api_url': 'https://data.charlottenc.gov/resource/eznd-gbqq.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': True,
    },

    # Tennessee
    'TN_DAVIDSON': {
        'name': 'Nashville-Davidson County',
        'url': 'https://www.nashville.gov/Health-Department/Environmental-Health.aspx',
        'api_url': 'https://data.nashville.gov/resource/9bjs-b7tq.json',
        'api_available': True,
        'scoring_system': 'numeric',
        'grade_system': False,
    },

    # Michigan
    'MI_WAYNE': {
        'name': 'Wayne County',
        'url': 'https://www.waynecounty.com/departments/hhvs/health/environmental-health.aspx',
        'api_url': None,
        'api_available': False,
        'scoring_system': 'numeric',
        'grade_system': False,
    },
    'MI_DETROIT': {
        'name': 'City of Detroit',
        'url': 'https://detroitmi.gov/departments/detroit-health-department',
        'api_url': 'https://data.detroitmi.gov/resource/hdjp-8qcs.json',
        'api_available': True,
        'scoring_system': 'pass_fail',
        'grade_system': False,
    },

    # Oregon
    'OR_MULTNOMAH': {
        'name': 'Multnomah County',
        'url': 'https://multco.us/health/inspections-702/food-establishment-inspection-results',
        'api_url': None,
        'api_available': False,
        'scoring_system': 'numeric',
        'grade_system': False,
    },
}


# State-level health department info
STATE_HEALTH_DEPARTMENTS: Dict[str, Dict[str, Any]] = {
    'AL': {
        'name': 'Alabama Department of Public Health',
        'url': 'https://www.alabamapublichealth.gov/foodsafety/',
        'inspection_search': 'https://www.alabamapublichealth.gov/foodsafety/county.html',
    },
    'AK': {
        'name': 'Alaska Division of Environmental Health',
        'url': 'https://dec.alaska.gov/eh/fss/',
        'inspection_search': 'https://dec.alaska.gov/Applications/EH/FSS/Index.aspx',
    },
    'AZ': {
        'name': 'Arizona Department of Health Services',
        'url': 'https://www.azdhs.gov/preparedness/epidemiology-disease-control/food-safety/',
        'inspection_search': None,  # County-managed
    },
    'AR': {
        'name': 'Arkansas Department of Health',
        'url': 'https://www.healthy.arkansas.gov/programs-services/topics/food-establishments',
        'inspection_search': 'https://www.healthy.arkansas.gov/programs-services/topics/inspection-results',
    },
    'CA': {
        'name': 'California Department of Public Health',
        'url': 'https://www.cdph.ca.gov/Programs/CEH/DFDCS/Pages/FDBPrograms/FoodSafetyProgram.aspx',
        'inspection_search': None,  # County-managed
    },
    'CO': {
        'name': 'Colorado Department of Public Health',
        'url': 'https://cdphe.colorado.gov/retail-food',
        'inspection_search': None,  # County-managed
    },
    'CT': {
        'name': 'Connecticut Department of Public Health',
        'url': 'https://portal.ct.gov/DPH/Environmental-Health/Food-Protection-Program/Food-Protection-Program',
        'inspection_search': 'https://portal.ct.gov/DPH/Environmental-Health/Food-Inspection',
    },
    'DE': {
        'name': 'Delaware Division of Public Health',
        'url': 'https://dhss.delaware.gov/dph/hsp/foodsafety.html',
        'inspection_search': 'https://dhss.delaware.gov/dhss/dph/hsp/files/findinspection.html',
    },
    'FL': {
        'name': 'Florida Department of Business and Professional Regulation',
        'url': 'https://www.myfloridalicense.com/dbpr/hr/',
        'inspection_search': 'https://www.myfloridalicense.com/wl11.asp?mode=0&SID=',
    },
    'GA': {
        'name': 'Georgia Department of Public Health',
        'url': 'https://dph.georgia.gov/environmental-health/food-service',
        'inspection_search': 'https://ga.healthinspections.us/',
    },
    'HI': {
        'name': 'Hawaii Department of Health',
        'url': 'https://health.hawaii.gov/san/food/',
        'inspection_search': 'https://health.hawaii.gov/san/inspection/',
    },
    'ID': {
        'name': 'Idaho Division of Public Health',
        'url': 'https://healthandwelfare.idaho.gov/health-wellness/food-safety',
        'inspection_search': None,  # District-managed
    },
    'IL': {
        'name': 'Illinois Department of Public Health',
        'url': 'https://dph.illinois.gov/topics-services/food-safety.html',
        'inspection_search': None,  # County-managed
    },
    'IN': {
        'name': 'Indiana State Department of Health',
        'url': 'https://www.in.gov/isdh/23286.htm',
        'inspection_search': 'https://www.in.gov/isdh/27440.htm',
    },
    'IA': {
        'name': 'Iowa Department of Inspections and Appeals',
        'url': 'https://dia.iowa.gov/food-and-consumer-safety',
        'inspection_search': 'https://dia.iowa.gov/food-database',
    },
    'KS': {
        'name': 'Kansas Department of Agriculture',
        'url': 'https://agriculture.ks.gov/divisions-programs/food-safety-lodging',
        'inspection_search': 'https://www.kansas-food-safety.com/',
    },
    'KY': {
        'name': 'Kentucky Cabinet for Health and Family Services',
        'url': 'https://chfs.ky.gov/agencies/dph/dehp/fsb/Pages/default.aspx',
        'inspection_search': 'https://eatsafe.ky.gov/',
    },
    'LA': {
        'name': 'Louisiana Department of Health',
        'url': 'https://ldh.la.gov/page/965',
        'inspection_search': 'https://ldh.la.gov/page/retail-food-inspections',
    },
    'ME': {
        'name': 'Maine Center for Disease Control',
        'url': 'https://www.maine.gov/dhhs/mecdc/environmental-health/el/inspection.shtml',
        'inspection_search': 'https://www11.maine.gov/dhhs/mecdc/environmental-health/el/inspect/index.shtml',
    },
    'MD': {
        'name': 'Maryland Department of Health',
        'url': 'https://health.maryland.gov/ohcq/fs/Pages/Home.aspx',
        'inspection_search': None,  # County-managed
    },
    'MA': {
        'name': 'Massachusetts Department of Public Health',
        'url': 'https://www.mass.gov/food-protection-program',
        'inspection_search': None,  # Local health departments
    },
    'MI': {
        'name': 'Michigan Department of Agriculture',
        'url': 'https://www.michigan.gov/mdard/food-dairy/food-safety',
        'inspection_search': None,  # County-managed
    },
    'MN': {
        'name': 'Minnesota Department of Health',
        'url': 'https://www.health.state.mn.us/communities/environment/food/',
        'inspection_search': 'https://www.health.state.mn.us/communities/environment/food/license/index.html',
    },
    'MS': {
        'name': 'Mississippi State Department of Health',
        'url': 'https://msdh.ms.gov/page/45,0,341.html',
        'inspection_search': 'https://msdh.ms.gov/msdhsite/_static/30,0,82.html',
    },
    'MO': {
        'name': 'Missouri Department of Health and Senior Services',
        'url': 'https://health.mo.gov/safety/foodsafety/',
        'inspection_search': 'https://health.mo.gov/safety/foodsafety/licensee.php',
    },
    'MT': {
        'name': 'Montana Department of Public Health',
        'url': 'https://dphhs.mt.gov/publichealth/fcss/',
        'inspection_search': 'https://dphhs.mt.gov/publichealth/fcss/retailfood',
    },
    'NE': {
        'name': 'Nebraska Department of Agriculture',
        'url': 'https://nda.nebraska.gov/dairies/food/',
        'inspection_search': 'https://nda.nebraska.gov/dairies/food/inspections.html',
    },
    'NV': {
        'name': 'Nevada Division of Public and Behavioral Health',
        'url': 'https://dpbh.nv.gov/Reg/Food/',
        'inspection_search': None,  # Health district managed
    },
    'NH': {
        'name': 'New Hampshire Department of Health and Human Services',
        'url': 'https://www.dhhs.nh.gov/dphs/fp/',
        'inspection_search': 'https://www4.des.state.nh.us/DESOneStop/Food.aspx',
    },
    'NJ': {
        'name': 'New Jersey Department of Health',
        'url': 'https://www.nj.gov/health/ceohs/food-drug/',
        'inspection_search': None,  # Local health departments
    },
    'NM': {
        'name': 'New Mexico Environment Department',
        'url': 'https://www.env.nm.gov/food/',
        'inspection_search': 'https://ei.env.nm.gov/food/inspectionresults.html',
    },
    'NY': {
        'name': 'New York State Department of Health',
        'url': 'https://www.health.ny.gov/environmental/indoors/food_safety/',
        'inspection_search': None,  # County-managed outside NYC
    },
    'NC': {
        'name': 'North Carolina Department of Health',
        'url': 'https://ehs.ncpublichealth.com/',
        'inspection_search': 'https://ehs.ncpublichealth.com/inspections/',
    },
    'ND': {
        'name': 'North Dakota Department of Health',
        'url': 'https://www.health.nd.gov/food',
        'inspection_search': 'https://ndfoodinspections.gov/',
    },
    'OH': {
        'name': 'Ohio Department of Health',
        'url': 'https://odh.ohio.gov/know-our-programs/food-safety-program/food-safety',
        'inspection_search': None,  # Local health departments
    },
    'OK': {
        'name': 'Oklahoma State Department of Health',
        'url': 'https://oklahoma.gov/health/protective-health/consumer-health-service.html',
        'inspection_search': 'https://oklahoma.gov/health/protective-health/consumer-health-service/food-safety.html',
    },
    'OR': {
        'name': 'Oregon Health Authority',
        'url': 'https://www.oregon.gov/oha/ph/healthyenvironments/foodsafety/',
        'inspection_search': 'https://healthspace.com/Clients/Oregon/Oregon/Web.nsf/',
    },
    'PA': {
        'name': 'Pennsylvania Department of Agriculture',
        'url': 'https://www.agriculture.pa.gov/consumer_protection/FoodSafety/',
        'inspection_search': 'https://www.pafoodsafety.pa.gov/',
    },
    'RI': {
        'name': 'Rhode Island Department of Health',
        'url': 'https://health.ri.gov/programs/detail.php?pgm_id=121',
        'inspection_search': 'https://health.ri.gov/data/inspections/',
    },
    'SC': {
        'name': 'South Carolina DHEC',
        'url': 'https://scdhec.gov/food-safety',
        'inspection_search': 'https://scdhec.gov/food-safety/retail-food-establishment-inspection-scores',
    },
    'SD': {
        'name': 'South Dakota Department of Health',
        'url': 'https://doh.sd.gov/diseases/foodborne/',
        'inspection_search': 'https://doh.sd.gov/food-lodging/',
    },
    'TN': {
        'name': 'Tennessee Department of Health',
        'url': 'https://www.tn.gov/health/health-program-areas/eh/eh-program-areas/food-and-general-sanitation.html',
        'inspection_search': 'https://apps.health.tn.gov/EHInspections/',
    },
    'TX': {
        'name': 'Texas Department of State Health Services',
        'url': 'https://www.dshs.texas.gov/foodestablishments/',
        'inspection_search': None,  # Local health departments
    },
    'UT': {
        'name': 'Utah Department of Agriculture and Food',
        'url': 'https://ag.utah.gov/farmers/food-safety-consumers/',
        'inspection_search': 'https://inspections.utah.gov/',
    },
    'VT': {
        'name': 'Vermont Department of Health',
        'url': 'https://www.healthvermont.gov/environment/food-lodging',
        'inspection_search': 'https://apps.health.vermont.gov/EH/FoodLodging/search/',
    },
    'VA': {
        'name': 'Virginia Department of Health',
        'url': 'https://www.vdh.virginia.gov/environmental-health/food-safety/',
        'inspection_search': 'https://inspections.myhealthdepartment.com/virginia',
    },
    'WA': {
        'name': 'Washington State Department of Health',
        'url': 'https://doh.wa.gov/community-and-environment/food/food-worker-and-industry',
        'inspection_search': None,  # Local health departments
    },
    'WV': {
        'name': 'West Virginia Department of Health and Human Resources',
        'url': 'https://dhhr.wv.gov/HealthCheck/',
        'inspection_search': 'https://dhhr.wv.gov/HealthCheck/services/foodsafety/Pages/default.aspx',
    },
    'WI': {
        'name': 'Wisconsin Department of Agriculture',
        'url': 'https://datcp.wi.gov/Pages/Programs_Services/FoodSafety.aspx',
        'inspection_search': 'https://datcp.wi.gov/Pages/Programs_Services/RestaurantInspections.aspx',
    },
    'WY': {
        'name': 'Wyoming Department of Agriculture',
        'url': 'https://agriculture.wy.gov/divisions/chs/food-safety',
        'inspection_search': 'https://agriculture.wy.gov/divisions/chs/food-safety/inspection-reports',
    },
    'DC': {
        'name': 'DC Health',
        'url': 'https://dchealth.dc.gov/service/food-safety-and-hygiene',
        'inspection_search': 'https://dc.healthinspections.us/',
    },
}


class RestaurantInspectionsAPI:
    """Main API class for restaurant inspection records"""

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

    def _parse_inspection_type(self, type_str: str) -> InspectionType:
        """Parse inspection type from string"""
        type_str = type_str.lower() if type_str else ""

        if 'routine' in type_str or 'regular' in type_str:
            return InspectionType.ROUTINE
        elif 'follow' in type_str or 'reinspect' in type_str:
            return InspectionType.FOLLOW_UP
        elif 'complaint' in type_str:
            return InspectionType.COMPLAINT
        elif 'pre-open' in type_str or 'preopening' in type_str:
            return InspectionType.PRE_OPENING
        elif 'ownership' in type_str or 'change' in type_str:
            return InspectionType.CHANGE_OF_OWNERSHIP
        elif 'consult' in type_str:
            return InspectionType.CONSULTATION
        elif 'illness' in type_str or 'outbreak' in type_str:
            return InspectionType.FOODBORNE_ILLNESS
        elif 'admin' in type_str:
            return InspectionType.ADMINISTRATIVE
        else:
            return InspectionType.UNKNOWN

    def _parse_result(self, result_str: str, score: Optional[int] = None) -> InspectionResult:
        """Parse inspection result from string"""
        result_str = result_str.lower() if result_str else ""

        if 'pass' in result_str and 'conditional' not in result_str:
            return InspectionResult.PASS
        elif 'conditional' in result_str:
            return InspectionResult.CONDITIONAL_PASS
        elif 'fail' in result_str or 'close' in result_str:
            return InspectionResult.FAIL
        elif 'reinspect' in result_str:
            return InspectionResult.REINSPECTION_REQUIRED
        elif 'pending' in result_str:
            return InspectionResult.PENDING
        elif score is not None:
            # Determine from score
            if score >= 90:
                return InspectionResult.PASS
            elif score >= 70:
                return InspectionResult.CONDITIONAL_PASS
            else:
                return InspectionResult.FAIL
        else:
            return InspectionResult.NOT_RATED

    def _parse_facility_type(self, type_str: str) -> FacilityType:
        """Parse facility type from string"""
        type_str = type_str.lower() if type_str else ""

        if 'fast food' in type_str or 'quick service' in type_str:
            return FacilityType.FAST_FOOD
        elif 'food truck' in type_str or 'mobile' in type_str:
            return FacilityType.MOBILE_FOOD
        elif 'cafeteria' in type_str:
            if 'school' in type_str:
                return FacilityType.SCHOOL_CAFETERIA
            elif 'hospital' in type_str:
                return FacilityType.HOSPITAL_CAFETERIA
            return FacilityType.CAFETERIA
        elif 'bar' in type_str or 'tavern' in type_str:
            return FacilityType.BAR_TAVERN
        elif 'bakery' in type_str:
            return FacilityType.BAKERY
        elif 'deli' in type_str:
            return FacilityType.DELI
        elif 'grocery' in type_str:
            return FacilityType.GROCERY_STORE
        elif 'convenience' in type_str:
            return FacilityType.CONVENIENCE_STORE
        elif 'supermarket' in type_str:
            return FacilityType.SUPERMARKET
        elif 'catering' in type_str:
            return FacilityType.CATERING
        elif 'daycare' in type_str or 'child care' in type_str:
            return FacilityType.DAYCARE
        elif 'nursing' in type_str:
            return FacilityType.NURSING_HOME
        elif 'coffee' in type_str:
            return FacilityType.COFFEE_SHOP
        elif 'ice cream' in type_str:
            return FacilityType.ICE_CREAM
        elif 'temporary' in type_str or 'event' in type_str:
            return FacilityType.TEMPORARY_EVENT
        elif 'farmer' in type_str or 'market' in type_str:
            return FacilityType.FARMERS_MARKET
        elif 'commissary' in type_str:
            return FacilityType.COMMISSARY
        else:
            return FacilityType.RESTAURANT

    def _parse_violation_severity(self, severity_str: str) -> ViolationSeverity:
        """Parse violation severity from string"""
        severity_str = severity_str.lower() if severity_str else ""

        if 'critical' in severity_str or 'priority' in severity_str:
            return ViolationSeverity.CRITICAL
        elif 'major' in severity_str:
            return ViolationSeverity.MAJOR
        elif 'minor' in severity_str or 'core' in severity_str:
            return ViolationSeverity.MINOR
        elif 'corrected' in severity_str:
            return ViolationSeverity.CORRECTED_ON_SITE
        else:
            return ViolationSeverity.OBSERVATION

    async def search_by_restaurant_name(
        self,
        name: str,
        jurisdiction: str,
        limit: int = 50
    ) -> List[InspectionRecord]:
        """Search inspections by restaurant name"""
        results = []

        if jurisdiction not in JURISDICTION_INSPECTION_SOURCES:
            logger.warning(f"Unknown jurisdiction: {jurisdiction}")
            return results

        config = JURISDICTION_INSPECTION_SOURCES[jurisdiction]

        if config.get('api_available') and config.get('api_url'):
            # Use Open Data API
            params = {
                '$where': f"upper(dba_name) like '%{name.upper()}%' OR upper(facility_name) like '%{name.upper()}%'",
                '$limit': limit,
                '$order': 'inspection_date DESC',
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list):
                for record in data:
                    inspection = self._parse_open_data_record(record, jurisdiction)
                    if inspection:
                        results.append(inspection)

        return results

    async def search_by_address(
        self,
        address: str,
        city: str,
        state: str,
        limit: int = 50
    ) -> List[InspectionRecord]:
        """Search inspections by address"""
        results = []

        # Find matching jurisdiction
        jurisdiction = self._find_jurisdiction(city, state)
        if not jurisdiction:
            logger.warning(f"No jurisdiction found for {city}, {state}")
            return results

        config = JURISDICTION_INSPECTION_SOURCES.get(jurisdiction)
        if not config:
            return results

        if config.get('api_available') and config.get('api_url'):
            # Use Open Data API
            params = {
                '$where': f"upper(address) like '%{address.upper()}%'",
                '$limit': limit,
                '$order': 'inspection_date DESC',
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list):
                for record in data:
                    inspection = self._parse_open_data_record(record, jurisdiction)
                    if inspection:
                        results.append(inspection)

        return results

    async def get_recent_inspections(
        self,
        jurisdiction: str,
        days: int = 30,
        limit: int = 100
    ) -> List[InspectionRecord]:
        """Get recent inspections for a jurisdiction"""
        results = []

        if jurisdiction not in JURISDICTION_INSPECTION_SOURCES:
            logger.warning(f"Unknown jurisdiction: {jurisdiction}")
            return results

        config = JURISDICTION_INSPECTION_SOURCES[jurisdiction]

        if config.get('api_available') and config.get('api_url'):
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            params = {
                '$where': f"inspection_date >= '{start_date.strftime('%Y-%m-%d')}'",
                '$limit': limit,
                '$order': 'inspection_date DESC',
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list):
                for record in data:
                    inspection = self._parse_open_data_record(record, jurisdiction)
                    if inspection:
                        results.append(inspection)

        return results

    async def get_failed_inspections(
        self,
        jurisdiction: str,
        days: int = 90,
        limit: int = 100
    ) -> List[InspectionRecord]:
        """Get failed/low-score inspections"""
        results = []

        if jurisdiction not in JURISDICTION_INSPECTION_SOURCES:
            return results

        config = JURISDICTION_INSPECTION_SOURCES[jurisdiction]

        if config.get('api_available') and config.get('api_url'):
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Build query based on scoring system
            scoring_system = config.get('scoring_system', 'numeric')

            if scoring_system == 'numeric':
                where_clause = f"inspection_date >= '{start_date.strftime('%Y-%m-%d')}' AND score < 70"
            elif scoring_system == 'violation_points':
                where_clause = f"inspection_date >= '{start_date.strftime('%Y-%m-%d')}' AND score > 28"
            elif scoring_system == 'pass_fail':
                where_clause = f"inspection_date >= '{start_date.strftime('%Y-%m-%d')}' AND upper(results) like '%FAIL%'"
            else:
                where_clause = f"inspection_date >= '{start_date.strftime('%Y-%m-%d')}'"

            params = {
                '$where': where_clause,
                '$limit': limit,
                '$order': 'inspection_date DESC',
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list):
                for record in data:
                    inspection = self._parse_open_data_record(record, jurisdiction)
                    if inspection and inspection.result in [InspectionResult.FAIL, InspectionResult.CONDITIONAL_PASS]:
                        results.append(inspection)

        return results

    async def get_critical_violations(
        self,
        jurisdiction: str,
        days: int = 90,
        limit: int = 100
    ) -> List[InspectionRecord]:
        """Get inspections with critical violations"""
        results = []

        if jurisdiction not in JURISDICTION_INSPECTION_SOURCES:
            return results

        config = JURISDICTION_INSPECTION_SOURCES[jurisdiction]

        if config.get('api_available') and config.get('api_url'):
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            params = {
                '$where': f"inspection_date >= '{start_date.strftime('%Y-%m-%d')}' AND critical_violations > 0",
                '$limit': limit,
                '$order': 'critical_violations DESC, inspection_date DESC',
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list):
                for record in data:
                    inspection = self._parse_open_data_record(record, jurisdiction)
                    if inspection and inspection.critical_violations > 0:
                        results.append(inspection)

        return results

    async def get_inspection_by_id(
        self,
        inspection_id: str,
        jurisdiction: str
    ) -> Optional[InspectionRecord]:
        """Get specific inspection by ID"""
        if jurisdiction not in JURISDICTION_INSPECTION_SOURCES:
            return None

        config = JURISDICTION_INSPECTION_SOURCES[jurisdiction]

        if config.get('api_available') and config.get('api_url'):
            params = {
                '$where': f"inspection_id = '{inspection_id}'",
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list) and len(data) > 0:
                return self._parse_open_data_record(data[0], jurisdiction)

        return None

    async def get_establishment_history(
        self,
        permit_number: str,
        jurisdiction: str,
        limit: int = 20
    ) -> List[InspectionRecord]:
        """Get inspection history for a specific establishment"""
        results = []

        if jurisdiction not in JURISDICTION_INSPECTION_SOURCES:
            return results

        config = JURISDICTION_INSPECTION_SOURCES[jurisdiction]

        if config.get('api_available') and config.get('api_url'):
            params = {
                '$where': f"permit_number = '{permit_number}' OR license_number = '{permit_number}'",
                '$limit': limit,
                '$order': 'inspection_date DESC',
            }

            data = await self._make_request(config['api_url'], params)
            if data and isinstance(data, list):
                for record in data:
                    inspection = self._parse_open_data_record(record, jurisdiction)
                    if inspection:
                        results.append(inspection)

        return results

    def _find_jurisdiction(self, city: str, state: str) -> Optional[str]:
        """Find jurisdiction key from city and state"""
        city_upper = city.upper()
        state_upper = state.upper()

        # Direct mappings
        city_jurisdiction_map = {
            ('LOS ANGELES', 'CA'): 'CA_LOS_ANGELES',
            ('SAN FRANCISCO', 'CA'): 'CA_SAN_FRANCISCO',
            ('SAN DIEGO', 'CA'): 'CA_SAN_DIEGO',
            ('HOUSTON', 'TX'): 'TX_HOUSTON',
            ('DALLAS', 'TX'): 'TX_DALLAS',
            ('AUSTIN', 'TX'): 'TX_AUSTIN',
            ('SAN ANTONIO', 'TX'): 'TX_SAN_ANTONIO',
            ('NEW YORK', 'NY'): 'NY_NEW_YORK_CITY',
            ('MIAMI', 'FL'): 'FL_MIAMI_DADE',
            ('CHICAGO', 'IL'): 'IL_CHICAGO',
            ('LAS VEGAS', 'NV'): 'NV_CLARK',
            ('PHOENIX', 'AZ'): 'AZ_MARICOPA',
            ('SEATTLE', 'WA'): 'WA_SEATTLE',
            ('BOSTON', 'MA'): 'MA_BOSTON',
            ('DENVER', 'CO'): 'CO_DENVER',
            ('PHILADELPHIA', 'PA'): 'PA_PHILADELPHIA',
            ('CHARLOTTE', 'NC'): 'NC_MECKLENBURG',
            ('NASHVILLE', 'TN'): 'TN_DAVIDSON',
            ('DETROIT', 'MI'): 'MI_DETROIT',
        }

        return city_jurisdiction_map.get((city_upper, state_upper))

    def _parse_open_data_record(self, record: Dict, jurisdiction: str) -> Optional[InspectionRecord]:
        """Parse Open Data API record into InspectionRecord"""
        try:
            # Field mapping varies by jurisdiction
            establishment = FoodEstablishment(
                name=record.get('dba_name') or record.get('facility_name') or record.get('name', 'Unknown'),
                address=record.get('address') or record.get('street_address', ''),
                city=record.get('city', ''),
                state=record.get('state', jurisdiction.split('_')[0]),
                zip_code=record.get('zip') or record.get('zip_code') or record.get('postal_code', ''),
                facility_type=self._parse_facility_type(record.get('facility_type', '')),
                permit_number=record.get('permit_number') or record.get('license_number'),
                latitude=float(record['latitude']) if record.get('latitude') else None,
                longitude=float(record['longitude']) if record.get('longitude') else None,
            )

            # Parse inspection date
            date_str = record.get('inspection_date') or record.get('activity_date', '')
            if date_str:
                if 'T' in date_str:
                    inspection_date = datetime.fromisoformat(date_str.replace('Z', '')).date()
                else:
                    inspection_date = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
            else:
                inspection_date = date.today()

            # Parse score
            score = None
            if record.get('score') is not None:
                try:
                    score = int(float(record['score']))
                except (ValueError, TypeError):
                    pass

            # Parse grade
            grade = record.get('grade') or record.get('letter_grade')

            # Parse violations
            violations = []
            critical_count = 0
            major_count = 0
            minor_count = 0

            # Some APIs include violation data in the same record
            if record.get('violation_description'):
                violation = Violation(
                    code=record.get('violation_code', 'N/A'),
                    description=record.get('violation_description', ''),
                    severity=self._parse_violation_severity(record.get('risk_category', '')),
                )
                violations.append(violation)

                if violation.severity == ViolationSeverity.CRITICAL:
                    critical_count += 1
                elif violation.severity == ViolationSeverity.MAJOR:
                    major_count += 1
                else:
                    minor_count += 1

            # Some APIs have violation counts
            if record.get('critical_violations') is not None:
                try:
                    critical_count = int(record['critical_violations'])
                except (ValueError, TypeError):
                    pass

            return InspectionRecord(
                inspection_id=str(record.get('inspection_id') or record.get('serial_number') or record.get('id', '')),
                establishment=establishment,
                inspection_date=inspection_date,
                inspection_type=self._parse_inspection_type(record.get('inspection_type', '')),
                result=self._parse_result(record.get('results') or record.get('grade_description', ''), score),
                score=score,
                grade=grade,
                violations=violations,
                critical_violations=critical_count,
                major_violations=major_count,
                minor_violations=minor_count,
                follow_up_required='follow' in (record.get('results', '') or '').lower(),
                source=JURISDICTION_INSPECTION_SOURCES.get(jurisdiction, {}).get('name', jurisdiction),
                source_url=JURISDICTION_INSPECTION_SOURCES.get(jurisdiction, {}).get('url'),
            )
        except Exception as e:
            logger.error(f"Error parsing record: {e}")
            return None

    # NYC-specific methods (grade-based system)
    async def search_nyc_by_grade(
        self,
        grade: str,
        limit: int = 100
    ) -> List[InspectionRecord]:
        """Search NYC restaurants by grade (A, B, C, etc.)"""
        results = []

        config = JURISDICTION_INSPECTION_SOURCES['NY_NEW_YORK_CITY']

        params = {
            '$where': f"grade = '{grade.upper()}'",
            '$limit': limit,
            '$order': 'inspection_date DESC',
        }

        data = await self._make_request(config['api_url'], params)
        if data and isinstance(data, list):
            for record in data:
                inspection = self._parse_open_data_record(record, 'NY_NEW_YORK_CITY')
                if inspection:
                    results.append(inspection)

        return results

    async def get_nyc_grade_pending(self, limit: int = 100) -> List[InspectionRecord]:
        """Get NYC restaurants with Grade Pending status"""
        return await self.search_nyc_by_grade('P', limit)

    # LA County-specific methods
    async def search_la_county_by_zip(
        self,
        zip_code: str,
        limit: int = 100
    ) -> List[InspectionRecord]:
        """Search LA County inspections by ZIP code"""
        results = []

        config = JURISDICTION_INSPECTION_SOURCES['CA_LOS_ANGELES']

        params = {
            '$where': f"pe_description like '%{zip_code}%' OR facility_zip = '{zip_code}'",
            '$limit': limit,
            '$order': 'activity_date DESC',
        }

        data = await self._make_request(config['api_url'], params)
        if data and isinstance(data, list):
            for record in data:
                inspection = self._parse_open_data_record(record, 'CA_LOS_ANGELES')
                if inspection:
                    results.append(inspection)

        return results

    # Chicago-specific methods
    async def search_chicago_inspections(
        self,
        name: Optional[str] = None,
        address: Optional[str] = None,
        risk: Optional[str] = None,
        limit: int = 100
    ) -> List[InspectionRecord]:
        """Search Chicago food inspections"""
        results = []

        config = JURISDICTION_INSPECTION_SOURCES['IL_CHICAGO']

        where_clauses = []
        if name:
            where_clauses.append(f"upper(dba_name) like '%{name.upper()}%'")
        if address:
            where_clauses.append(f"upper(address) like '%{address.upper()}%'")
        if risk:
            where_clauses.append(f"upper(risk) like '%{risk.upper()}%'")

        where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'

        params = {
            '$where': where_clause,
            '$limit': limit,
            '$order': 'inspection_date DESC',
        }

        data = await self._make_request(config['api_url'], params)
        if data and isinstance(data, list):
            for record in data:
                inspection = self._parse_open_data_record(record, 'IL_CHICAGO')
                if inspection:
                    results.append(inspection)

        return results

    def get_available_jurisdictions(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available jurisdictions with API support"""
        return {
            k: {
                'name': v['name'],
                'api_available': v.get('api_available', False),
                'scoring_system': v.get('scoring_system', 'unknown'),
                'grade_system': v.get('grade_system', False),
            }
            for k, v in JURISDICTION_INSPECTION_SOURCES.items()
        }

    def get_state_health_department(self, state: str) -> Optional[Dict[str, Any]]:
        """Get state health department info"""
        return STATE_HEALTH_DEPARTMENTS.get(state.upper())

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics"""
        total_jurisdictions = len(JURISDICTION_INSPECTION_SOURCES)
        api_available = sum(1 for j in JURISDICTION_INSPECTION_SOURCES.values() if j.get('api_available'))

        states_covered = len(STATE_HEALTH_DEPARTMENTS)

        return {
            'total_local_jurisdictions': total_jurisdictions,
            'jurisdictions_with_api': api_available,
            'jurisdictions_web_only': total_jurisdictions - api_available,
            'api_coverage_percent': round(api_available / total_jurisdictions * 100, 1),
            'states_with_info': states_covered,
            'scoring_systems': {
                'numeric': sum(1 for j in JURISDICTION_INSPECTION_SOURCES.values() if j.get('scoring_system') == 'numeric'),
                'pass_fail': sum(1 for j in JURISDICTION_INSPECTION_SOURCES.values() if j.get('scoring_system') == 'pass_fail'),
                'violation_points': sum(1 for j in JURISDICTION_INSPECTION_SOURCES.values() if j.get('scoring_system') == 'violation_points'),
                'demerits': sum(1 for j in JURISDICTION_INSPECTION_SOURCES.values() if j.get('scoring_system') == 'demerits'),
            },
            'jurisdictions_with_grades': sum(1 for j in JURISDICTION_INSPECTION_SOURCES.values() if j.get('grade_system')),
        }


# Import timedelta for date calculations
from datetime import timedelta


# Synchronous wrapper functions
def search_inspections_by_restaurant(
    name: str,
    jurisdiction: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching inspections by restaurant name"""
    async def _search():
        async with RestaurantInspectionsAPI() as api:
            results = await api.search_by_restaurant_name(name, jurisdiction, limit)
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def search_inspections_by_address(
    address: str,
    city: str,
    state: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching inspections by address"""
    async def _search():
        async with RestaurantInspectionsAPI() as api:
            results = await api.search_by_address(address, city, state, limit)
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def get_recent_inspections(
    jurisdiction: str,
    days: int = 30,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for getting recent inspections"""
    async def _get():
        async with RestaurantInspectionsAPI() as api:
            results = await api.get_recent_inspections(jurisdiction, days, limit)
            return [r.to_dict() for r in results]

    return asyncio.run(_get())


def get_failed_inspections(
    jurisdiction: str,
    days: int = 90,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for getting failed inspections"""
    async def _get():
        async with RestaurantInspectionsAPI() as api:
            results = await api.get_failed_inspections(jurisdiction, days, limit)
            return [r.to_dict() for r in results]

    return asyncio.run(_get())


def get_critical_violations(
    jurisdiction: str,
    days: int = 90,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for getting inspections with critical violations"""
    async def _get():
        async with RestaurantInspectionsAPI() as api:
            results = await api.get_critical_violations(jurisdiction, days, limit)
            return [r.to_dict() for r in results]

    return asyncio.run(_get())


def get_establishment_history(
    permit_number: str,
    jurisdiction: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for getting establishment inspection history"""
    async def _get():
        async with RestaurantInspectionsAPI() as api:
            results = await api.get_establishment_history(permit_number, jurisdiction, limit)
            return [r.to_dict() for r in results]

    return asyncio.run(_get())


def get_available_jurisdictions() -> Dict[str, Dict[str, Any]]:
    """Get list of available jurisdictions"""
    api = RestaurantInspectionsAPI()
    return api.get_available_jurisdictions()


def get_state_health_info(state: str) -> Optional[Dict[str, Any]]:
    """Get state health department information"""
    api = RestaurantInspectionsAPI()
    return api.get_state_health_department(state)


def get_coverage_stats() -> Dict[str, Any]:
    """Get coverage statistics for restaurant inspections"""
    api = RestaurantInspectionsAPI()
    return api.get_coverage_stats()


if __name__ == "__main__":
    # Test the API
    print("Restaurant Inspections Scraper")
    print("=" * 50)

    stats = get_coverage_stats()
    print(f"\nCoverage Statistics:")
    print(f"  Local Jurisdictions: {stats['total_local_jurisdictions']}")
    print(f"  With API Access: {stats['jurisdictions_with_api']} ({stats['api_coverage_percent']}%)")
    print(f"  States with Info: {stats['states_with_info']}")
    print(f"  Jurisdictions with Grades: {stats['jurisdictions_with_grades']}")

    print(f"\nScoring Systems:")
    for system, count in stats['scoring_systems'].items():
        print(f"  {system}: {count}")

    print("\nAvailable Jurisdictions with API:")
    jurisdictions = get_available_jurisdictions()
    for key, info in jurisdictions.items():
        if info['api_available']:
            print(f"  {key}: {info['name']} ({info['scoring_system']})")
