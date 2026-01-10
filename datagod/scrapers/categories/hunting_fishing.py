"""
Hunting and Fishing Licenses Scraper
=====================================

Comprehensive scraper for hunting and fishing license records
from state Department of Natural Resources (DNR) and wildlife agencies.

Data Sources:
- State DNR/Fish & Wildlife agencies
- State licensing portals
- Game and Parks commissions

License Types:
- Fishing licenses (resident/non-resident)
- Hunting licenses (small game, big game, waterfowl)
- Combination licenses
- Lifetime licenses
- Special permits (tags, stamps)
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


class LicenseType(Enum):
    """Types of hunting/fishing licenses"""
    # Fishing
    FISHING_RESIDENT = "fishing_resident"
    FISHING_NON_RESIDENT = "fishing_non_resident"
    FISHING_SENIOR = "fishing_senior"
    FISHING_YOUTH = "fishing_youth"
    FISHING_DISABLED = "fishing_disabled"
    FISHING_VETERAN = "fishing_veteran"
    FISHING_LIFETIME = "fishing_lifetime"
    FISHING_ONE_DAY = "fishing_one_day"
    FISHING_THREE_DAY = "fishing_three_day"
    FISHING_SEVEN_DAY = "fishing_seven_day"
    SALTWATER_FISHING = "saltwater_fishing"
    FRESHWATER_FISHING = "freshwater_fishing"
    TROUT_STAMP = "trout_stamp"

    # Hunting
    HUNTING_RESIDENT = "hunting_resident"
    HUNTING_NON_RESIDENT = "hunting_non_resident"
    HUNTING_SENIOR = "hunting_senior"
    HUNTING_YOUTH = "hunting_youth"
    HUNTING_APPRENTICE = "hunting_apprentice"
    HUNTING_LIFETIME = "hunting_lifetime"
    SMALL_GAME = "small_game"
    BIG_GAME = "big_game"
    DEER = "deer"
    ELK = "elk"
    TURKEY = "turkey"
    BEAR = "bear"
    MOOSE = "moose"
    ANTELOPE = "antelope"
    WATERFOWL = "waterfowl"
    MIGRATORY_BIRD = "migratory_bird"
    UPLAND_GAME = "upland_game"
    FUR_BEARER = "fur_bearer"

    # Combination
    SPORTSMAN = "sportsman"  # Combo hunting + fishing
    SUPER_COMBO = "super_combo"

    # Permits and stamps
    HABITAT_STAMP = "habitat_stamp"
    DUCK_STAMP = "duck_stamp"
    PHEASANT_STAMP = "pheasant_stamp"
    ARCHERY_PERMIT = "archery_permit"
    MUZZLELOADER_PERMIT = "muzzleloader_permit"
    ANTLERLESS_PERMIT = "antlerless_permit"

    # Special
    COMMERCIAL_FISHING = "commercial_fishing"
    GUIDE_LICENSE = "guide_license"
    TAXIDERMIST = "taxidermist"
    FUR_DEALER = "fur_dealer"

    OTHER = "other"


class LicenseStatus(Enum):
    """License status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CANCELLED = "cancelled"


class ResidencyStatus(Enum):
    """Residency status for licensing"""
    RESIDENT = "resident"
    NON_RESIDENT = "non_resident"
    MILITARY = "military"
    LIFETIME = "lifetime"


class HarveyReportStatus(Enum):
    """Harvest reporting status (required in many states)"""
    REPORTED = "reported"
    NOT_REPORTED = "not_reported"
    NOT_REQUIRED = "not_required"
    OVERDUE = "overdue"


@dataclass
class LicenseHolder:
    """License holder information"""
    first_name: str
    last_name: str
    middle_name: Optional[str] = None

    # Address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None

    # Identification
    date_of_birth: Optional[date] = None
    customer_id: Optional[str] = None

    # Contact (rarely public)
    phone: Optional[str] = None
    email: Optional[str] = None

    # Residency
    residency_status: ResidencyStatus = ResidencyStatus.RESIDENT


@dataclass
class HarvestRecord:
    """Record of harvested game"""
    species: str
    harvest_date: date
    location: Optional[str] = None
    county: Optional[str] = None
    zone: Optional[str] = None
    tag_number: Optional[str] = None
    confirmation_number: Optional[str] = None
    sex: Optional[str] = None  # Male/Female
    points: Optional[int] = None  # Antler points for deer/elk
    weight: Optional[float] = None


@dataclass
class LicenseRecord:
    """Hunting or fishing license record"""
    license_number: str
    license_type: LicenseType
    holder: LicenseHolder

    # Validity
    issue_date: date
    effective_date: date
    expiration_date: date
    status: LicenseStatus

    # Details
    license_year: str  # e.g., "2024-2025"
    residency: ResidencyStatus = ResidencyStatus.RESIDENT
    fee_paid: Optional[float] = None

    # Tags and permits included
    tags: List[str] = field(default_factory=list)
    stamps: List[str] = field(default_factory=list)
    permits: List[str] = field(default_factory=list)

    # Harvest reporting
    harvest_reports: List[HarvestRecord] = field(default_factory=list)
    harvest_report_status: HarveyReportStatus = HarveyReportStatus.NOT_REQUIRED

    # Violations (if any linked to license)
    violations: List[str] = field(default_factory=list)

    # Source
    state: str = ""
    source: str = ""
    source_url: Optional[str] = None
    retrieved_date: date = field(default_factory=date.today)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'license_number': self.license_number,
            'license_type': self.license_type.value,
            'holder': {
                'first_name': self.holder.first_name,
                'last_name': self.holder.last_name,
                'city': self.holder.city,
                'state': self.holder.state,
                'county': self.holder.county,
                'residency_status': self.holder.residency_status.value,
            },
            'issue_date': self.issue_date.isoformat(),
            'effective_date': self.effective_date.isoformat(),
            'expiration_date': self.expiration_date.isoformat(),
            'status': self.status.value,
            'license_year': self.license_year,
            'tags': self.tags,
            'stamps': self.stamps,
            'permits': self.permits,
            'harvest_reports': [
                {
                    'species': h.species,
                    'harvest_date': h.harvest_date.isoformat(),
                    'location': h.location,
                    'county': h.county,
                }
                for h in self.harvest_reports
            ],
            'state': self.state,
            'source': self.source,
        }


# State DNR/Wildlife Agency configurations
STATE_WILDLIFE_AGENCIES: Dict[str, Dict[str, Any]] = {
    'AL': {
        'name': 'Alabama Department of Conservation and Natural Resources',
        'abbreviation': 'ADCNR',
        'url': 'https://www.outdooralabama.com/',
        'license_search': 'https://www.outdooralabama.com/hunting/license-information',
        'api_available': False,
        'license_year': 'Sept 1 - Aug 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'AK': {
        'name': 'Alaska Department of Fish and Game',
        'abbreviation': 'ADF&G',
        'url': 'https://www.adfg.alaska.gov/',
        'license_search': 'https://www.adfg.alaska.gov/Store/',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'notes': 'Hunt/trap registration required for most species',
    },
    'AZ': {
        'name': 'Arizona Game and Fish Department',
        'abbreviation': 'AZGFD',
        'url': 'https://www.azgfd.com/',
        'license_search': 'https://www.azgfd.com/License/',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,  # Has tag draw system
    },
    'AR': {
        'name': 'Arkansas Game and Fish Commission',
        'abbreviation': 'AGFC',
        'url': 'https://www.agfc.com/',
        'license_search': 'https://www.agfc.com/en/licenses/',
        'api_available': False,
        'license_year': 'June 15 - June 14',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'CA': {
        'name': 'California Department of Fish and Wildlife',
        'abbreviation': 'CDFW',
        'url': 'https://www.wildlife.ca.gov/',
        'license_search': 'https://www.wildlife.ca.gov/Licensing',
        'api_url': None,
        'api_available': False,
        'license_year': 'July 1 - June 30',
        'electronic_license': True,
        'harvest_reporting': True,
        'report_card_required': True,
    },
    'CO': {
        'name': 'Colorado Parks and Wildlife',
        'abbreviation': 'CPW',
        'url': 'https://cpw.state.co.us/',
        'license_search': 'https://cpw.state.co.us/buyapply/Pages/Hunting.aspx',
        'api_available': False,
        'license_year': 'April 1 - March 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,
    },
    'CT': {
        'name': 'Connecticut DEEP',
        'abbreviation': 'CT DEEP',
        'url': 'https://portal.ct.gov/DEEP',
        'license_search': 'https://portal.ct.gov/DEEP/Hunting/Licenses-and-Permits',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'DE': {
        'name': 'Delaware Division of Fish and Wildlife',
        'abbreviation': 'DFW',
        'url': 'https://dnrec.alpha.delaware.gov/fish-wildlife/',
        'license_search': 'https://dnrec.alpha.delaware.gov/fish-wildlife/licenses/',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'FL': {
        'name': 'Florida Fish and Wildlife Conservation Commission',
        'abbreviation': 'FWC',
        'url': 'https://myfwc.com/',
        'license_search': 'https://myfwc.com/license/',
        'api_url': 'https://myfwc.com/api/license/',  # Hypothetical
        'api_available': False,
        'license_year': 'July 1 - June 30',
        'electronic_license': True,
        'harvest_reporting': True,
        'gold_sportsman': True,  # Special combo license
    },
    'GA': {
        'name': 'Georgia Department of Natural Resources',
        'abbreviation': 'GA DNR',
        'url': 'https://gadnr.org/',
        'license_search': 'https://gadnrle.org/hunting-fishing-licenses',
        'api_available': False,
        'license_year': 'July 1 - June 30',
        'electronic_license': True,
        'harvest_reporting': True,
        'game_check': True,  # Harvest reporting system
    },
    'HI': {
        'name': 'Hawaii Division of Forestry and Wildlife',
        'abbreviation': 'DOFAW',
        'url': 'https://dlnr.hawaii.gov/dofaw/',
        'license_search': 'https://dlnr.hawaii.gov/dofaw/hunting/',
        'api_available': False,
        'license_year': 'July 1 - June 30',
        'electronic_license': False,
        'notes': 'Hunting only on designated areas',
    },
    'ID': {
        'name': 'Idaho Fish and Game',
        'abbreviation': 'IDFG',
        'url': 'https://idfg.idaho.gov/',
        'license_search': 'https://idfg.idaho.gov/licenses',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,
    },
    'IL': {
        'name': 'Illinois Department of Natural Resources',
        'abbreviation': 'IDNR',
        'url': 'https://www2.illinois.gov/dnr/',
        'license_search': 'https://www2.illinois.gov/dnr/hunting/Pages/Licenses.aspx',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'IN': {
        'name': 'Indiana DNR Fish and Wildlife',
        'abbreviation': 'IN DNR',
        'url': 'https://www.in.gov/dnr/fish-and-wildlife/',
        'license_search': 'https://www.in.gov/dnr/fish-and-wildlife/licenses-and-permits/',
        'api_available': False,
        'license_year': 'April 1 - March 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'IA': {
        'name': 'Iowa Department of Natural Resources',
        'abbreviation': 'IA DNR',
        'url': 'https://www.iowadnr.gov/',
        'license_search': 'https://www.iowadnr.gov/Hunting/Licenses-Laws',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'KS': {
        'name': 'Kansas Department of Wildlife and Parks',
        'abbreviation': 'KDWP',
        'url': 'https://ksoutdoors.com/',
        'license_search': 'https://ksoutdoors.com/License-Permits',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'KY': {
        'name': 'Kentucky Department of Fish and Wildlife Resources',
        'abbreviation': 'KDFWR',
        'url': 'https://fw.ky.gov/',
        'license_search': 'https://fw.ky.gov/Licenses/Pages/default.aspx',
        'api_available': False,
        'license_year': 'March 1 - Feb 28/29',
        'electronic_license': True,
        'harvest_reporting': True,
        'telecheck': True,  # Phone/online harvest reporting
    },
    'LA': {
        'name': 'Louisiana Department of Wildlife and Fisheries',
        'abbreviation': 'LDWF',
        'url': 'https://www.wlf.louisiana.gov/',
        'license_search': 'https://www.wlf.louisiana.gov/page/licenses-and-permits',
        'api_available': False,
        'license_year': 'June 1 - May 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'ME': {
        'name': 'Maine Department of Inland Fisheries and Wildlife',
        'abbreviation': 'MDIFW',
        'url': 'https://www.maine.gov/ifw/',
        'license_search': 'https://www.maine.gov/ifw/hunting-trapping/licenses-permits/',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'MD': {
        'name': 'Maryland Department of Natural Resources',
        'abbreviation': 'MD DNR',
        'url': 'https://dnr.maryland.gov/',
        'license_search': 'https://dnr.maryland.gov/wildlife/Pages/hunt_trap/Licenses.aspx',
        'api_available': False,
        'license_year': 'July 1 - June 30',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'MA': {
        'name': 'Massachusetts Division of Fisheries and Wildlife',
        'abbreviation': 'MassWildlife',
        'url': 'https://www.mass.gov/orgs/division-of-fisheries-and-wildlife',
        'license_search': 'https://www.mass.gov/how-to/buy-a-hunting-or-fishing-license',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'MI': {
        'name': 'Michigan Department of Natural Resources',
        'abbreviation': 'MI DNR',
        'url': 'https://www.michigan.gov/dnr/',
        'license_search': 'https://www.michigan.gov/dnr/buy-and-apply/hunting',
        'api_available': False,
        'license_year': 'April 1 - March 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'MN': {
        'name': 'Minnesota Department of Natural Resources',
        'abbreviation': 'MN DNR',
        'url': 'https://www.dnr.state.mn.us/',
        'license_search': 'https://www.dnr.state.mn.us/licenses/index.html',
        'api_available': False,
        'license_year': 'March 1 - Feb 28/29',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'MS': {
        'name': 'Mississippi Department of Wildlife, Fisheries, and Parks',
        'abbreviation': 'MDWFP',
        'url': 'https://www.mdwfp.com/',
        'license_search': 'https://www.mdwfp.com/license/',
        'api_available': False,
        'license_year': 'July 1 - June 30',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'MO': {
        'name': 'Missouri Department of Conservation',
        'abbreviation': 'MDC',
        'url': 'https://mdc.mo.gov/',
        'license_search': 'https://mdc.mo.gov/hunting-trapping/permits',
        'api_available': False,
        'license_year': 'Feb 28 - Feb 28',
        'electronic_license': True,
        'harvest_reporting': True,
        'telecheck': True,
    },
    'MT': {
        'name': 'Montana Fish, Wildlife and Parks',
        'abbreviation': 'MT FWP',
        'url': 'https://fwp.mt.gov/',
        'license_search': 'https://fwp.mt.gov/buyandapply/licenses',
        'api_available': False,
        'license_year': 'March 1 - Feb 28/29',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,
    },
    'NE': {
        'name': 'Nebraska Game and Parks Commission',
        'abbreviation': 'NGPC',
        'url': 'https://outdoornebraska.gov/',
        'license_search': 'https://outdoornebraska.gov/hunting/permits-and-fees/',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'NV': {
        'name': 'Nevada Department of Wildlife',
        'abbreviation': 'NDOW',
        'url': 'https://www.ndow.org/',
        'license_search': 'https://www.ndow.org/licenses/',
        'api_available': False,
        'license_year': 'March 1 - Feb 28/29',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,
    },
    'NH': {
        'name': 'New Hampshire Fish and Game Department',
        'abbreviation': 'NH F&G',
        'url': 'https://www.wildlife.nh.gov/',
        'license_search': 'https://www.wildlife.nh.gov/hunting-trapping/hunting-licenses',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'NJ': {
        'name': 'New Jersey Division of Fish and Wildlife',
        'abbreviation': 'NJ DFW',
        'url': 'https://www.nj.gov/dep/fgw/',
        'license_search': 'https://www.nj.gov/dep/fgw/licenses.htm',
        'api_available': False,
        'license_year': 'April 1 - March 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'NM': {
        'name': 'New Mexico Department of Game and Fish',
        'abbreviation': 'NMDGF',
        'url': 'https://www.wildlife.state.nm.us/',
        'license_search': 'https://www.wildlife.state.nm.us/hunting/licenses/',
        'api_available': False,
        'license_year': 'April 1 - March 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,
    },
    'NY': {
        'name': 'New York State DEC',
        'abbreviation': 'NYS DEC',
        'url': 'https://www.dec.ny.gov/',
        'license_search': 'https://www.dec.ny.gov/permits/6091.html',
        'api_available': False,
        'license_year': 'Oct 1 - Sept 30',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'NC': {
        'name': 'North Carolina Wildlife Resources Commission',
        'abbreviation': 'NCWRC',
        'url': 'https://www.ncwildlife.org/',
        'license_search': 'https://www.ncwildlife.org/Licensing/Hunting-Fishing-Trapping-Licenses',
        'api_available': False,
        'license_year': 'July 1 - June 30',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'ND': {
        'name': 'North Dakota Game and Fish Department',
        'abbreviation': 'NDGF',
        'url': 'https://gf.nd.gov/',
        'license_search': 'https://gf.nd.gov/licensing',
        'api_available': False,
        'license_year': 'April 1 - March 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'OH': {
        'name': 'Ohio Department of Natural Resources Division of Wildlife',
        'abbreviation': 'ODNR',
        'url': 'https://ohiodnr.gov/wps/portal/gov/odnr/buy-and-apply/hunting-fishing-boating',
        'license_search': 'https://ohiodnr.gov/wps/portal/gov/odnr/buy-and-apply/hunting-fishing-boating/hunting-resources/licenses-permits',
        'api_available': False,
        'license_year': 'March 1 - Feb 28/29',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'OK': {
        'name': 'Oklahoma Department of Wildlife Conservation',
        'abbreviation': 'ODWC',
        'url': 'https://www.wildlifedepartment.com/',
        'license_search': 'https://www.wildlifedepartment.com/hunting/licenses',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'OR': {
        'name': 'Oregon Department of Fish and Wildlife',
        'abbreviation': 'ODFW',
        'url': 'https://www.dfw.state.or.us/',
        'license_search': 'https://myodfw.com/hunting',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,
    },
    'PA': {
        'name': 'Pennsylvania Game Commission',
        'abbreviation': 'PGC',
        'url': 'https://www.pgc.pa.gov/',
        'license_search': 'https://www.pgc.pa.gov/HuntTrap/Law/Pages/Licenses.aspx',
        'api_available': False,
        'license_year': 'July 1 - June 30',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'RI': {
        'name': 'Rhode Island DEM Division of Fish and Wildlife',
        'abbreviation': 'RI DFW',
        'url': 'https://dem.ri.gov/natural-resources-bureau/fish-wildlife',
        'license_search': 'https://dem.ri.gov/natural-resources-bureau/fish-wildlife/licenses-permits',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'SC': {
        'name': 'South Carolina Department of Natural Resources',
        'abbreviation': 'SCDNR',
        'url': 'https://www.dnr.sc.gov/',
        'license_search': 'https://www.dnr.sc.gov/licenses.html',
        'api_available': False,
        'license_year': 'July 1 - June 30',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'SD': {
        'name': 'South Dakota Game, Fish and Parks',
        'abbreviation': 'SDGFP',
        'url': 'https://gfp.sd.gov/',
        'license_search': 'https://gfp.sd.gov/licenses/',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,
    },
    'TN': {
        'name': 'Tennessee Wildlife Resources Agency',
        'abbreviation': 'TWRA',
        'url': 'https://www.tn.gov/twra.html',
        'license_search': 'https://www.tn.gov/twra/license-sales.html',
        'api_available': False,
        'license_year': 'Feb 28 - Feb 28',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'TX': {
        'name': 'Texas Parks and Wildlife Department',
        'abbreviation': 'TPWD',
        'url': 'https://tpwd.texas.gov/',
        'license_search': 'https://tpwd.texas.gov/regulations/outdoor-annual/licenses/',
        'api_url': 'https://tpwd.texas.gov/data/',  # Has some open data
        'api_available': False,
        'license_year': 'Sept 1 - Aug 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'super_combo': True,  # Super Combo license
    },
    'UT': {
        'name': 'Utah Division of Wildlife Resources',
        'abbreviation': 'UDWR',
        'url': 'https://wildlife.utah.gov/',
        'license_search': 'https://wildlife.utah.gov/licenses-background.html',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,
    },
    'VT': {
        'name': 'Vermont Fish and Wildlife Department',
        'abbreviation': 'VT F&W',
        'url': 'https://vtfishandwildlife.com/',
        'license_search': 'https://vtfishandwildlife.com/licenses-and-lotteries',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'VA': {
        'name': 'Virginia Department of Wildlife Resources',
        'abbreviation': 'DWR',
        'url': 'https://dwr.virginia.gov/',
        'license_search': 'https://dwr.virginia.gov/licenses/',
        'api_available': False,
        'license_year': 'July 1 - June 30',
        'electronic_license': True,
        'harvest_reporting': True,
    },
    'WA': {
        'name': 'Washington Department of Fish and Wildlife',
        'abbreviation': 'WDFW',
        'url': 'https://wdfw.wa.gov/',
        'license_search': 'https://wdfw.wa.gov/licenses',
        'api_available': False,
        'license_year': 'April 1 - March 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,
    },
    'WV': {
        'name': 'West Virginia Division of Natural Resources',
        'abbreviation': 'WV DNR',
        'url': 'https://wvdnr.gov/',
        'license_search': 'https://wvdnr.gov/hunting/licenses/',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'game_check': True,
    },
    'WI': {
        'name': 'Wisconsin Department of Natural Resources',
        'abbreviation': 'WI DNR',
        'url': 'https://dnr.wisconsin.gov/',
        'license_search': 'https://dnr.wisconsin.gov/topic/hunt/licenses',
        'api_available': False,
        'license_year': 'April 1 - March 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'game_registration': True,  # GameReg system
    },
    'WY': {
        'name': 'Wyoming Game and Fish Department',
        'abbreviation': 'WGFD',
        'url': 'https://wgfd.wyo.gov/',
        'license_search': 'https://wgfd.wyo.gov/Apply-or-Buy',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'harvest_reporting': True,
        'draw_system': True,
    },
    'DC': {
        'name': 'DC Fisheries and Wildlife Division',
        'abbreviation': 'DC FWD',
        'url': 'https://doee.dc.gov/service/fishing-regulations',
        'license_search': 'https://doee.dc.gov/service/fishing-regulations',
        'api_available': False,
        'license_year': 'Jan 1 - Dec 31',
        'electronic_license': True,
        'notes': 'Fishing only - no hunting in DC',
    },
}


# Federal duck stamp program
FEDERAL_DUCK_STAMP = {
    'name': 'Federal Duck Stamp Program',
    'agency': 'U.S. Fish and Wildlife Service',
    'url': 'https://www.fws.gov/program/federal-duck-stamp',
    'purchase_url': 'https://www.fws.gov/program/federal-duck-stamp/buy-duck-stamp',
    'required_for': 'Migratory waterfowl hunting (16+ years old)',
    'price': 25.00,
    'valid': 'July 1 - June 30',
}


class HuntingFishingAPI:
    """Main API class for hunting and fishing license records"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.base_headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[str]:
        """Make HTTP request with error handling"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.base_headers)

        try:
            async with self.session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"Request failed with status {response.status}: {url}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {url}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def _parse_license_type(self, type_str: str) -> LicenseType:
        """Parse license type from string"""
        type_str = type_str.lower() if type_str else ""

        # Fishing types
        if 'saltwater' in type_str:
            return LicenseType.SALTWATER_FISHING
        elif 'freshwater' in type_str:
            return LicenseType.FRESHWATER_FISHING
        elif 'trout' in type_str and 'stamp' in type_str:
            return LicenseType.TROUT_STAMP
        elif 'fishing' in type_str:
            if 'non-resident' in type_str or 'nonresident' in type_str:
                return LicenseType.FISHING_NON_RESIDENT
            elif 'senior' in type_str:
                return LicenseType.FISHING_SENIOR
            elif 'youth' in type_str or 'junior' in type_str:
                return LicenseType.FISHING_YOUTH
            elif 'lifetime' in type_str:
                return LicenseType.FISHING_LIFETIME
            elif 'one day' in type_str or '1-day' in type_str:
                return LicenseType.FISHING_ONE_DAY
            elif 'three day' in type_str or '3-day' in type_str:
                return LicenseType.FISHING_THREE_DAY
            elif 'seven day' in type_str or '7-day' in type_str:
                return LicenseType.FISHING_SEVEN_DAY
            else:
                return LicenseType.FISHING_RESIDENT

        # Hunting types
        elif 'deer' in type_str:
            return LicenseType.DEER
        elif 'elk' in type_str:
            return LicenseType.ELK
        elif 'turkey' in type_str:
            return LicenseType.TURKEY
        elif 'bear' in type_str:
            return LicenseType.BEAR
        elif 'moose' in type_str:
            return LicenseType.MOOSE
        elif 'antelope' in type_str or 'pronghorn' in type_str:
            return LicenseType.ANTELOPE
        elif 'waterfowl' in type_str or 'duck' in type_str or 'goose' in type_str:
            return LicenseType.WATERFOWL
        elif 'migratory' in type_str:
            return LicenseType.MIGRATORY_BIRD
        elif 'upland' in type_str or 'pheasant' in type_str or 'quail' in type_str:
            return LicenseType.UPLAND_GAME
        elif 'small game' in type_str:
            return LicenseType.SMALL_GAME
        elif 'big game' in type_str:
            return LicenseType.BIG_GAME
        elif 'fur' in type_str and 'bearer' in type_str:
            return LicenseType.FUR_BEARER
        elif 'hunting' in type_str:
            if 'non-resident' in type_str or 'nonresident' in type_str:
                return LicenseType.HUNTING_NON_RESIDENT
            elif 'senior' in type_str:
                return LicenseType.HUNTING_SENIOR
            elif 'youth' in type_str or 'junior' in type_str:
                return LicenseType.HUNTING_YOUTH
            elif 'apprentice' in type_str:
                return LicenseType.HUNTING_APPRENTICE
            elif 'lifetime' in type_str:
                return LicenseType.HUNTING_LIFETIME
            else:
                return LicenseType.HUNTING_RESIDENT

        # Combination
        elif 'sportsman' in type_str or 'combo' in type_str:
            if 'super' in type_str:
                return LicenseType.SUPER_COMBO
            return LicenseType.SPORTSMAN

        # Stamps and permits
        elif 'duck stamp' in type_str:
            return LicenseType.DUCK_STAMP
        elif 'habitat' in type_str:
            return LicenseType.HABITAT_STAMP
        elif 'archery' in type_str:
            return LicenseType.ARCHERY_PERMIT
        elif 'muzzleloader' in type_str:
            return LicenseType.MUZZLELOADER_PERMIT

        # Commercial
        elif 'commercial' in type_str:
            return LicenseType.COMMERCIAL_FISHING
        elif 'guide' in type_str:
            return LicenseType.GUIDE_LICENSE
        elif 'taxiderm' in type_str:
            return LicenseType.TAXIDERMIST

        return LicenseType.OTHER

    async def search_by_name(
        self,
        last_name: str,
        first_name: str,
        state: str,
        license_year: Optional[str] = None
    ) -> List[LicenseRecord]:
        """
        Search for hunting/fishing licenses by name.

        Note: Most states do NOT make license holder information publicly searchable.
        This method is primarily for states with public license databases (rare).
        """
        results = []

        if state not in STATE_WILDLIFE_AGENCIES:
            logger.warning(f"Unknown state: {state}")
            return results

        config = STATE_WILDLIFE_AGENCIES[state]

        # Most states don't provide public API access to license holder data
        # This would need to be implemented per-state where available
        logger.info(f"License search for {state} - checking {config['name']}")

        # Note: Implementation would vary by state
        # Some states may offer public harvest data but not license holder data

        return results

    async def search_by_license_number(
        self,
        license_number: str,
        state: str
    ) -> Optional[LicenseRecord]:
        """Search for a specific license by number"""
        if state not in STATE_WILDLIFE_AGENCIES:
            logger.warning(f"Unknown state: {state}")
            return None

        config = STATE_WILDLIFE_AGENCIES[state]

        # Most states require login to verify license numbers
        logger.info(f"License lookup for {state} - {license_number}")

        return None

    async def get_harvest_data(
        self,
        state: str,
        species: str,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate harvest data for a state/species.

        Many states publish aggregate harvest statistics publicly.
        """
        if state not in STATE_WILDLIFE_AGENCIES:
            return {'error': f'Unknown state: {state}'}

        config = STATE_WILDLIFE_AGENCIES[state]
        current_year = year or datetime.now().year

        # Return aggregate harvest info structure
        return {
            'state': state,
            'species': species,
            'year': current_year,
            'agency': config['name'],
            'harvest_reporting_required': config.get('harvest_reporting', False),
            'data_url': config.get('url'),
            'notes': 'Aggregate harvest statistics typically available in annual reports',
        }

    async def get_license_types(self, state: str) -> List[Dict[str, Any]]:
        """Get available license types for a state"""
        if state not in STATE_WILDLIFE_AGENCIES:
            return []

        config = STATE_WILDLIFE_AGENCIES[state]

        # Common license types available in most states
        license_types = [
            {
                'type': 'fishing_resident',
                'name': 'Resident Fishing License',
                'description': 'Basic fishing license for state residents',
            },
            {
                'type': 'fishing_non_resident',
                'name': 'Non-Resident Fishing License',
                'description': 'Fishing license for non-residents',
            },
            {
                'type': 'hunting_resident',
                'name': 'Resident Hunting License',
                'description': 'Basic hunting license for state residents',
            },
            {
                'type': 'hunting_non_resident',
                'name': 'Non-Resident Hunting License',
                'description': 'Hunting license for non-residents',
            },
        ]

        # Add combo if available
        if config.get('super_combo') or config.get('gold_sportsman'):
            license_types.append({
                'type': 'super_combo',
                'name': 'Super Combo / Sportsman License',
                'description': 'Combined hunting and fishing with stamps',
            })

        # Add draw info if applicable
        if config.get('draw_system'):
            license_types.append({
                'type': 'draw_tags',
                'name': 'Draw/Lottery Tags',
                'description': 'Limited entry tags awarded through lottery system',
            })

        return license_types

    async def get_license_requirements(
        self,
        state: str,
        license_type: str
    ) -> Dict[str, Any]:
        """Get requirements for a specific license type"""
        if state not in STATE_WILDLIFE_AGENCIES:
            return {'error': f'Unknown state: {state}'}

        config = STATE_WILDLIFE_AGENCIES[state]

        return {
            'state': state,
            'agency': config['name'],
            'license_type': license_type,
            'license_year': config.get('license_year', 'Jan 1 - Dec 31'),
            'electronic_available': config.get('electronic_license', True),
            'purchase_url': config.get('license_search'),
            'requirements': {
                'residency_proof': 'Required for resident licenses',
                'hunter_education': 'Required for first-time hunters in most states',
                'identification': 'Valid ID required',
            },
        }

    async def verify_license(
        self,
        license_number: str,
        state: str,
        date_of_birth: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Verify if a license is valid.

        Note: Most states require authentication or are only available to
        law enforcement. This provides guidance on where to verify.
        """
        if state not in STATE_WILDLIFE_AGENCIES:
            return {'error': f'Unknown state: {state}', 'valid': False}

        config = STATE_WILDLIFE_AGENCIES[state]

        return {
            'license_number': license_number,
            'state': state,
            'verification_available': False,
            'agency': config['name'],
            'verification_url': config.get('license_search'),
            'notes': 'License verification typically requires login or is restricted to law enforcement',
        }

    def get_state_agency(self, state: str) -> Optional[Dict[str, Any]]:
        """Get state wildlife agency information"""
        return STATE_WILDLIFE_AGENCIES.get(state.upper())

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get all state wildlife agencies"""
        return {
            state: {
                'name': info['name'],
                'abbreviation': info['abbreviation'],
                'url': info['url'],
                'license_year': info.get('license_year', 'Unknown'),
                'electronic_license': info.get('electronic_license', False),
                'harvest_reporting': info.get('harvest_reporting', False),
                'draw_system': info.get('draw_system', False),
            }
            for state, info in STATE_WILDLIFE_AGENCIES.items()
        }

    def get_federal_duck_stamp_info(self) -> Dict[str, Any]:
        """Get federal duck stamp information"""
        return FEDERAL_DUCK_STAMP

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics"""
        total_states = len(STATE_WILDLIFE_AGENCIES)
        with_api = sum(1 for s in STATE_WILDLIFE_AGENCIES.values() if s.get('api_available'))
        with_electronic = sum(1 for s in STATE_WILDLIFE_AGENCIES.values() if s.get('electronic_license'))
        with_harvest_reporting = sum(1 for s in STATE_WILDLIFE_AGENCIES.values() if s.get('harvest_reporting'))
        with_draw = sum(1 for s in STATE_WILDLIFE_AGENCIES.values() if s.get('draw_system'))

        return {
            'total_states': total_states,
            'states_with_api': with_api,
            'states_with_electronic_license': with_electronic,
            'states_with_harvest_reporting': with_harvest_reporting,
            'states_with_draw_system': with_draw,
            'api_coverage_percent': round(with_api / total_states * 100, 1),
            'electronic_license_percent': round(with_electronic / total_states * 100, 1),
            'notes': 'Most states do not provide public API access to individual license records',
        }

    async def search_violations(
        self,
        state: str,
        last_name: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for hunting/fishing violations.

        Some states publish violation/citation records.
        """
        results = []

        if state not in STATE_WILDLIFE_AGENCIES:
            return results

        # Note: Implementation would vary by state
        # Some states publish violations through court records

        return results


# Synchronous wrapper functions
def search_licenses_by_name(
    last_name: str,
    first_name: str,
    state: str,
    license_year: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching licenses by name"""
    async def _search():
        async with HuntingFishingAPI() as api:
            results = await api.search_by_name(last_name, first_name, state, license_year)
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def get_license_by_number(
    license_number: str,
    state: str
) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for getting license by number"""
    async def _get():
        async with HuntingFishingAPI() as api:
            result = await api.search_by_license_number(license_number, state)
            return result.to_dict() if result else None

    return asyncio.run(_get())


def get_harvest_data(
    state: str,
    species: str,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """Synchronous wrapper for getting harvest data"""
    async def _get():
        async with HuntingFishingAPI() as api:
            return await api.get_harvest_data(state, species, year)

    return asyncio.run(_get())


def get_license_types(state: str) -> List[Dict[str, Any]]:
    """Synchronous wrapper for getting license types"""
    async def _get():
        async with HuntingFishingAPI() as api:
            return await api.get_license_types(state)

    return asyncio.run(_get())


def get_license_requirements(
    state: str,
    license_type: str
) -> Dict[str, Any]:
    """Synchronous wrapper for getting license requirements"""
    async def _get():
        async with HuntingFishingAPI() as api:
            return await api.get_license_requirements(state, license_type)

    return asyncio.run(_get())


def verify_license(
    license_number: str,
    state: str,
    date_of_birth: Optional[date] = None
) -> Dict[str, Any]:
    """Synchronous wrapper for verifying a license"""
    async def _verify():
        async with HuntingFishingAPI() as api:
            return await api.verify_license(license_number, state, date_of_birth)

    return asyncio.run(_verify())


def get_state_agency_info(state: str) -> Optional[Dict[str, Any]]:
    """Get state wildlife agency information"""
    api = HuntingFishingAPI()
    return api.get_state_agency(state)


def get_all_state_agencies() -> Dict[str, Dict[str, Any]]:
    """Get all state wildlife agencies"""
    api = HuntingFishingAPI()
    return api.get_all_states()


def get_federal_duck_stamp() -> Dict[str, Any]:
    """Get federal duck stamp information"""
    api = HuntingFishingAPI()
    return api.get_federal_duck_stamp_info()


def get_coverage_stats() -> Dict[str, Any]:
    """Get coverage statistics for hunting/fishing licenses"""
    api = HuntingFishingAPI()
    return api.get_coverage_stats()


if __name__ == "__main__":
    # Test the API
    print("Hunting and Fishing Licenses Scraper")
    print("=" * 50)

    stats = get_coverage_stats()
    print(f"\nCoverage Statistics:")
    print(f"  Total States: {stats['total_states']}")
    print(f"  With API Access: {stats['states_with_api']} ({stats['api_coverage_percent']}%)")
    print(f"  Electronic Licensing: {stats['states_with_electronic_license']} ({stats['electronic_license_percent']}%)")
    print(f"  Harvest Reporting: {stats['states_with_harvest_reporting']}")
    print(f"  Draw/Lottery Systems: {stats['states_with_draw_system']}")

    print(f"\nFederal Duck Stamp:")
    duck_stamp = get_federal_duck_stamp()
    print(f"  Price: ${duck_stamp['price']}")
    print(f"  Valid: {duck_stamp['valid']}")

    print("\nStates with Draw/Lottery Systems:")
    agencies = get_all_state_agencies()
    for state, info in agencies.items():
        if info.get('draw_system'):
            print(f"  {state}: {info['name']}")
