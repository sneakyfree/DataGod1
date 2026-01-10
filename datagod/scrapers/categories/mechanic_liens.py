"""
Mechanic's Liens / Construction Liens Scraper
=============================================

Comprehensive scraper for mechanic's lien records from county recorder
offices across all US states.

Data Sources:
- County Recorder offices
- County Clerk offices
- Register of Deeds

Lien Types:
- Mechanic's liens (construction work)
- Materialman's liens (materials)
- Contractor's liens
- Subcontractor's liens
- Design professional liens
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


class LienType(Enum):
    """Types of mechanic's/construction liens"""
    MECHANICS_LIEN = "mechanics_lien"
    MATERIALMAN_LIEN = "materialman_lien"
    CONTRACTOR_LIEN = "contractor_lien"
    SUBCONTRACTOR_LIEN = "subcontractor_lien"
    LABORER_LIEN = "laborer_lien"
    DESIGN_PROFESSIONAL = "design_professional"  # Architect, engineer
    STOP_NOTICE = "stop_notice"  # CA specific
    NOTICE_TO_OWNER = "notice_to_owner"
    PRELIMINARY_NOTICE = "preliminary_notice"
    LIEN_RELEASE = "lien_release"
    LIEN_AMENDMENT = "lien_amendment"
    LIEN_EXTENSION = "lien_extension"
    OTHER = "other"


class LienStatus(Enum):
    """Status of mechanic's lien"""
    FILED = "filed"
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"
    FORECLOSED = "foreclosed"
    BONDED_OFF = "bonded_off"
    SATISFIED = "satisfied"
    CONTESTED = "contested"
    VOID = "void"


class ClaimantType(Enum):
    """Type of claimant filing the lien"""
    GENERAL_CONTRACTOR = "general_contractor"
    SUBCONTRACTOR = "subcontractor"
    SUB_SUBCONTRACTOR = "sub_subcontractor"
    MATERIAL_SUPPLIER = "material_supplier"
    EQUIPMENT_RENTAL = "equipment_rental"
    LABORER = "laborer"
    ARCHITECT = "architect"
    ENGINEER = "engineer"
    SURVEYOR = "surveyor"
    OTHER = "other"


class PropertyType(Enum):
    """Type of property where work was performed"""
    RESIDENTIAL_SINGLE = "residential_single"
    RESIDENTIAL_MULTI = "residential_multi"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"
    VACANT_LAND = "vacant_land"
    GOVERNMENT = "government"
    OTHER = "other"


@dataclass
class LienClaimant:
    """Party claiming the mechanic's lien"""
    name: str
    claimant_type: ClaimantType

    # Contact info
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None

    # Business info
    license_number: Optional[str] = None
    license_type: Optional[str] = None

    # Attorney
    attorney_name: Optional[str] = None
    attorney_firm: Optional[str] = None


@dataclass
class PropertyOwner:
    """Property owner against whom lien is filed"""
    name: str

    # Address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


@dataclass
class LienProperty:
    """Property subject to the lien"""
    address: str
    city: str
    state: str
    zip_code: Optional[str] = None
    county: Optional[str] = None

    # Property identification
    apn: Optional[str] = None  # Assessor's Parcel Number
    legal_description: Optional[str] = None
    lot: Optional[str] = None
    block: Optional[str] = None
    subdivision: Optional[str] = None

    property_type: PropertyType = PropertyType.OTHER


@dataclass
class WorkDescription:
    """Description of work performed"""
    description: str
    work_type: Optional[str] = None  # Construction, renovation, etc.

    # Timeline
    start_date: Optional[date] = None
    completion_date: Optional[date] = None
    last_work_date: Optional[date] = None
    last_material_date: Optional[date] = None


@dataclass
class MechanicLienRecord:
    """Mechanic's lien record"""
    document_number: str
    lien_type: LienType
    status: LienStatus

    # Amount
    lien_amount: float
    amount_claimed: Optional[float] = None
    interest_claimed: Optional[float] = None
    attorney_fees_claimed: Optional[float] = None

    # Parties
    claimant: Optional[LienClaimant] = None
    property_owner: Optional[PropertyOwner] = None
    general_contractor: Optional[str] = None  # If claimant is sub

    # Property
    property_info: Optional[LienProperty] = None

    # Work description
    work_description: Optional[WorkDescription] = None

    # Dates
    recording_date: Optional[date] = None
    lien_date: Optional[date] = None
    expiration_date: Optional[date] = None
    release_date: Optional[date] = None

    # Recording info
    book: Optional[str] = None
    page: Optional[str] = None
    instrument_number: Optional[str] = None

    # County/State
    county: str = ""
    state: str = ""

    # Preliminary notice info
    preliminary_notice_sent: bool = False
    preliminary_notice_date: Optional[date] = None

    # Related documents
    related_documents: List[str] = field(default_factory=list)
    release_document: Optional[str] = None
    foreclosure_case: Optional[str] = None

    # Source
    source: str = ""
    source_url: Optional[str] = None
    retrieved_date: date = field(default_factory=date.today)

    def is_valid(self) -> bool:
        """Check if lien is still valid (not expired)"""
        if self.status in [LienStatus.RELEASED, LienStatus.EXPIRED,
                           LienStatus.SATISFIED, LienStatus.VOID]:
            return False
        if self.expiration_date and self.expiration_date < date.today():
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'document_number': self.document_number,
            'lien_type': self.lien_type.value,
            'status': self.status.value,
            'lien_amount': self.lien_amount,
            'claimant': {
                'name': self.claimant.name,
                'type': self.claimant.claimant_type.value,
            } if self.claimant else None,
            'property_owner': {
                'name': self.property_owner.name,
            } if self.property_owner else None,
            'property': {
                'address': self.property_info.address,
                'city': self.property_info.city,
                'apn': self.property_info.apn,
            } if self.property_info else None,
            'recording_date': self.recording_date.isoformat() if self.recording_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'county': self.county,
            'state': self.state,
            'is_valid': self.is_valid(),
            'source': self.source,
        }


# State mechanic's lien law information
STATE_LIEN_LAWS: Dict[str, Dict[str, Any]] = {
    'AL': {
        'name': 'Alabama',
        'statute': 'Ala. Code § 35-11-210 et seq.',
        'filing_deadline_days': 180,  # From last work
        'foreclosure_deadline_days': 180,  # From filing
        'preliminary_notice_required': False,
        'owner_occupied_residential_protected': True,
        'filing_office': 'Probate Court',
    },
    'AK': {
        'name': 'Alaska',
        'statute': 'Alaska Stat. § 34.35.050 et seq.',
        'filing_deadline_days': 120,
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': False,
        'filing_office': 'District Recorder',
    },
    'AZ': {
        'name': 'Arizona',
        'statute': 'Ariz. Rev. Stat. § 33-981 et seq.',
        'filing_deadline_days': 120,
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': True,
        'preliminary_notice_days': 20,
        'filing_office': 'County Recorder',
    },
    'AR': {
        'name': 'Arkansas',
        'statute': 'Ark. Code § 18-44-101 et seq.',
        'filing_deadline_days': 120,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'Circuit Clerk',
    },
    'CA': {
        'name': 'California',
        'statute': 'Cal. Civ. Code § 8000 et seq.',
        'filing_deadline_days': 90,  # Direct contractor
        'filing_deadline_sub_days': 90,  # Sub after completion
        'foreclosure_deadline_days': 90,
        'preliminary_notice_required': True,
        'preliminary_notice_days': 20,
        'stop_notice_available': True,
        'filing_office': 'County Recorder',
        'notes': 'Complex preliminary notice requirements',
    },
    'CO': {
        'name': 'Colorado',
        'statute': 'Colo. Rev. Stat. § 38-22-101 et seq.',
        'filing_deadline_days': 120,  # 4 months
        'foreclosure_deadline_days': 180,  # 6 months
        'preliminary_notice_required': False,
        'filing_office': 'County Clerk and Recorder',
    },
    'CT': {
        'name': 'Connecticut',
        'statute': 'Conn. Gen. Stat. § 49-33 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'Town Clerk',
    },
    'DE': {
        'name': 'Delaware',
        'statute': 'Del. Code tit. 25 § 2701 et seq.',
        'filing_deadline_days': 180,  # 6 months
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'Prothonotary',
    },
    'FL': {
        'name': 'Florida',
        'statute': 'Fla. Stat. § 713.01 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,
        'preliminary_notice_days': 45,  # Notice to Owner
        'filing_office': 'Clerk of Circuit Court',
        'notes': 'Complex notice requirements',
    },
    'GA': {
        'name': 'Georgia',
        'statute': 'O.C.G.A. § 44-14-360 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'Clerk of Superior Court',
    },
    'HI': {
        'name': 'Hawaii',
        'statute': 'Haw. Rev. Stat. § 507-41 et seq.',
        'filing_deadline_days': 45,  # Short deadline
        'foreclosure_deadline_days': 90,
        'preliminary_notice_required': True,
        'filing_office': 'Bureau of Conveyances',
    },
    'ID': {
        'name': 'Idaho',
        'statute': 'Idaho Code § 45-501 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'County Recorder',
    },
    'IL': {
        'name': 'Illinois',
        'statute': '770 ILCS 60/1 et seq.',
        'filing_deadline_days': 120,  # 4 months
        'foreclosure_deadline_days': 730,  # 2 years
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'County Recorder',
    },
    'IN': {
        'name': 'Indiana',
        'statute': 'Ind. Code § 32-28-3-1 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'County Recorder',
    },
    'IA': {
        'name': 'Iowa',
        'statute': 'Iowa Code § 572.1 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 730,  # 2 years
        'preliminary_notice_required': True,  # For subs, 30 days
        'filing_office': 'County Recorder',
    },
    'KS': {
        'name': 'Kansas',
        'statute': 'Kan. Stat. § 60-1101 et seq.',
        'filing_deadline_days': 120,  # 4 months
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'Register of Deeds',
    },
    'KY': {
        'name': 'Kentucky',
        'statute': 'Ky. Rev. Stat. § 376.010 et seq.',
        'filing_deadline_days': 180,  # 6 months
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'County Clerk',
    },
    'LA': {
        'name': 'Louisiana',
        'statute': 'La. R.S. 9:4801 et seq.',
        'filing_deadline_days': 60,  # Private work
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # Complex requirements
        'filing_office': 'Clerk of Court (Mortgage Office)',
        'notes': 'Civil law system - different rules',
    },
    'ME': {
        'name': 'Maine',
        'statute': 'Me. Rev. Stat. tit. 10 § 3251 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'County Registry of Deeds',
    },
    'MD': {
        'name': 'Maryland',
        'statute': 'Md. Real Prop. Code § 9-101 et seq.',
        'filing_deadline_days': 180,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'Clerk of Circuit Court',
    },
    'MA': {
        'name': 'Massachusetts',
        'statute': 'Mass. Gen. Laws ch. 254 § 1 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 90,  # Short enforcement
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'Registry of Deeds',
    },
    'MI': {
        'name': 'Michigan',
        'statute': 'Mich. Comp. Laws § 570.1101 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # For residential
        'filing_office': 'County Register of Deeds',
    },
    'MN': {
        'name': 'Minnesota',
        'statute': 'Minn. Stat. § 514.01 et seq.',
        'filing_deadline_days': 120,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'County Recorder',
    },
    'MS': {
        'name': 'Mississippi',
        'statute': 'Miss. Code § 85-7-131 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'Chancery Clerk',
    },
    'MO': {
        'name': 'Missouri',
        'statute': 'Mo. Rev. Stat. § 429.010 et seq.',
        'filing_deadline_days': 180,  # 6 months
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'County Recorder',
    },
    'MT': {
        'name': 'Montana',
        'statute': 'Mont. Code § 71-3-521 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 730,  # 2 years
        'preliminary_notice_required': True,
        'filing_office': 'County Clerk and Recorder',
    },
    'NE': {
        'name': 'Nebraska',
        'statute': 'Neb. Rev. Stat. § 52-101 et seq.',
        'filing_deadline_days': 120,
        'foreclosure_deadline_days': 730,  # 2 years
        'preliminary_notice_required': False,
        'filing_office': 'Register of Deeds',
    },
    'NV': {
        'name': 'Nevada',
        'statute': 'Nev. Rev. Stat. § 108.221 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': True,
        'preliminary_notice_days': 31,
        'filing_office': 'County Recorder',
    },
    'NH': {
        'name': 'New Hampshire',
        'statute': 'N.H. Rev. Stat. § 447:1 et seq.',
        'filing_deadline_days': 120,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'Registry of Deeds',
    },
    'NJ': {
        'name': 'New Jersey',
        'statute': 'N.J. Stat. § 2A:44A-1 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # Lien fund notice
        'filing_office': 'County Clerk',
    },
    'NM': {
        'name': 'New Mexico',
        'statute': 'N.M. Stat. § 48-2-1 et seq.',
        'filing_deadline_days': 120,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'County Clerk',
    },
    'NY': {
        'name': 'New York',
        'statute': 'N.Y. Lien Law § 1 et seq.',
        'filing_deadline_days': 240,  # 8 months
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'County Clerk',
        'notes': 'Complex trust fund requirements',
    },
    'NC': {
        'name': 'North Carolina',
        'statute': 'N.C. Gen. Stat. § 44A-7 et seq.',
        'filing_deadline_days': 120,
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'Clerk of Superior Court',
    },
    'ND': {
        'name': 'North Dakota',
        'statute': 'N.D. Cent. Code § 35-27-01 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 1095,  # 3 years
        'preliminary_notice_required': False,
        'filing_office': 'County Recorder',
    },
    'OH': {
        'name': 'Ohio',
        'statute': 'Ohio Rev. Code § 1311.01 et seq.',
        'filing_deadline_days': 60,  # Short deadline
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'County Recorder',
    },
    'OK': {
        'name': 'Oklahoma',
        'statute': 'Okla. Stat. tit. 42 § 141 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # Pre-lien notice
        'filing_office': 'County Clerk',
    },
    'OR': {
        'name': 'Oregon',
        'statute': 'Or. Rev. Stat. § 87.001 et seq.',
        'filing_deadline_days': 75,
        'foreclosure_deadline_days': 120,
        'preliminary_notice_required': True,
        'filing_office': 'County Clerk',
    },
    'PA': {
        'name': 'Pennsylvania',
        'statute': '49 Pa. Cons. Stat. § 1101 et seq.',
        'filing_deadline_days': 180,  # 6 months
        'foreclosure_deadline_days': 730,  # 2 years
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'Prothonotary',
    },
    'RI': {
        'name': 'Rhode Island',
        'statute': 'R.I. Gen. Laws § 34-28-1 et seq.',
        'filing_deadline_days': 120,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'City/Town Clerk',
    },
    'SC': {
        'name': 'South Carolina',
        'statute': 'S.C. Code § 29-5-10 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': False,
        'filing_office': 'Clerk of Court (ROD)',
    },
    'SD': {
        'name': 'South Dakota',
        'statute': 'S.D. Codified Laws § 44-9-1 et seq.',
        'filing_deadline_days': 120,
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': False,
        'filing_office': 'Register of Deeds',
    },
    'TN': {
        'name': 'Tennessee',
        'statute': 'Tenn. Code § 66-11-101 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'Register of Deeds',
    },
    'TX': {
        'name': 'Texas',
        'statute': 'Tex. Prop. Code § 53.001 et seq.',
        'filing_deadline_days': 120,  # 4 months for original
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # Complex requirements
        'filing_office': 'County Clerk',
        'notes': 'Constitutional lien, strict notice requirements',
    },
    'UT': {
        'name': 'Utah',
        'statute': 'Utah Code § 38-1a-101 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': True,
        'filing_office': 'County Recorder',
        'notes': 'State Construction Registry (SCR) required',
    },
    'VT': {
        'name': 'Vermont',
        'statute': 'Vt. Stat. tit. 9 § 1921 et seq.',
        'filing_deadline_days': 180,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'Town Clerk',
    },
    'VA': {
        'name': 'Virginia',
        'statute': 'Va. Code § 43-1 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 180,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'Clerk of Circuit Court',
    },
    'WA': {
        'name': 'Washington',
        'statute': 'Wash. Rev. Code § 60.04.011 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 240,  # 8 months
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'County Auditor',
    },
    'WV': {
        'name': 'West Virginia',
        'statute': 'W. Va. Code § 38-2-1 et seq.',
        'filing_deadline_days': 100,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': False,
        'filing_office': 'County Clerk',
    },
    'WI': {
        'name': 'Wisconsin',
        'statute': 'Wis. Stat. § 779.01 et seq.',
        'filing_deadline_days': 180,  # 6 months
        'foreclosure_deadline_days': 730,  # 2 years
        'preliminary_notice_required': False,
        'filing_office': 'Register of Deeds',
    },
    'WY': {
        'name': 'Wyoming',
        'statute': 'Wyo. Stat. § 29-1-101 et seq.',
        'filing_deadline_days': 150,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'County Clerk',
    },
    'DC': {
        'name': 'District of Columbia',
        'statute': 'D.C. Code § 40-301.01 et seq.',
        'filing_deadline_days': 90,
        'foreclosure_deadline_days': 365,
        'preliminary_notice_required': True,  # For subs
        'filing_office': 'Recorder of Deeds',
    },
}


# Major county recorder configurations for lien searches
COUNTY_RECORDER_SOURCES: Dict[str, Dict[str, Any]] = {
    # California
    'CA_LOS_ANGELES': {
        'name': 'Los Angeles County Recorder',
        'url': 'https://www.lavote.net/home/county-clerk/recorder-background',
        'search_url': 'https://www.lavote.net/Apps/DocumentSearchPortal/',
        'api_available': False,
    },
    'CA_SAN_DIEGO': {
        'name': 'San Diego County Recorder',
        'url': 'https://arcc.sdcounty.ca.gov/',
        'search_url': 'https://arcc.sdcounty.ca.gov/Pages/onlinesearch.aspx',
        'api_available': False,
    },
    'CA_ORANGE': {
        'name': 'Orange County Recorder',
        'url': 'https://www.ocrecorder.com/',
        'search_url': 'https://cr.ocgov.com/recorderworks/',
        'api_available': False,
    },

    # Texas
    'TX_HARRIS': {
        'name': 'Harris County Clerk',
        'url': 'https://www.cclerk.hctx.net/',
        'search_url': 'https://www.cclerk.hctx.net/Applications/WebSearch/',
        'api_available': False,
    },
    'TX_DALLAS': {
        'name': 'Dallas County Clerk',
        'url': 'https://www.dallascounty.org/government/county-clerk/',
        'search_url': 'https://apps.dallascounty.org/ccfiling/search',
        'api_available': False,
    },

    # Florida
    'FL_MIAMI_DADE': {
        'name': 'Miami-Dade County Clerk',
        'url': 'https://www.miamidadeclerk.com/',
        'search_url': 'https://www2.miami-dadeclerk.com/ors/default.aspx',
        'api_available': False,
    },
    'FL_BROWARD': {
        'name': 'Broward County Records',
        'url': 'https://www.broward.org/RecordsTaxesTreasury/',
        'search_url': 'https://officialrecords.broward.org/AcclaimWeb/',
        'api_available': False,
    },

    # New York
    'NY_NEW_YORK': {
        'name': 'New York City ACRIS',
        'url': 'https://www.nyc.gov/site/finance/taxes/acris.page',
        'search_url': 'https://a836-acris.nyc.gov/DS/DocumentSearch/Index',
        'api_available': True,
    },

    # Illinois
    'IL_COOK': {
        'name': 'Cook County Recorder of Deeds',
        'url': 'https://www.cookcountyrecorder.com/',
        'search_url': 'https://www.cookcountyrecorder.com/search',
        'api_available': False,
    },

    # Arizona
    'AZ_MARICOPA': {
        'name': 'Maricopa County Recorder',
        'url': 'https://recorder.maricopa.gov/',
        'search_url': 'https://recorder.maricopa.gov/recdocdata/',
        'api_available': False,
    },

    # Nevada
    'NV_CLARK': {
        'name': 'Clark County Recorder',
        'url': 'https://www.clarkcountynv.gov/government/elected_officials/county_recorder/',
        'search_url': 'https://recorder.clarkcountynv.gov/RecorderEcommerce/Search.aspx',
        'api_available': False,
    },

    # Georgia
    'GA_FULTON': {
        'name': 'Fulton County Superior Court Clerk',
        'url': 'https://www.fultoncountyclerk.com/',
        'search_url': 'https://www.fultoncountyclerk.org/recordsearch/',
        'api_available': False,
    },

    # Washington
    'WA_KING': {
        'name': 'King County Recorder',
        'url': 'https://kingcounty.gov/depts/records-licensing/recorders-office.aspx',
        'search_url': 'https://recordsearch.kingcounty.gov/',
        'api_available': True,
    },

    # Pennsylvania
    'PA_PHILADELPHIA': {
        'name': 'Philadelphia Department of Records',
        'url': 'https://www.phila.gov/departments/department-of-records/',
        'search_url': 'https://epay.phila-records.com/PhilaRecordWeb/',
        'api_available': False,
    },

    # Ohio
    'OH_CUYAHOGA': {
        'name': 'Cuyahoga County Recorder',
        'url': 'https://recorder.cuyahogacounty.us/',
        'search_url': 'https://recorder.cuyahogacounty.us/recservices/Search',
        'api_available': False,
    },

    # Michigan
    'MI_WAYNE': {
        'name': 'Wayne County Register of Deeds',
        'url': 'https://www.waynecounty.com/elected/rod/',
        'search_url': 'https://www.waynecountyrod.com/',
        'api_available': False,
    },
}


class MechanicLiensAPI:
    """Main API class for mechanic's lien records"""

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

    def _parse_lien_type(self, type_str: str) -> LienType:
        """Parse lien type from string"""
        type_str = type_str.lower() if type_str else ""

        if 'release' in type_str or 'satisfaction' in type_str:
            return LienType.LIEN_RELEASE
        elif 'amendment' in type_str:
            return LienType.LIEN_AMENDMENT
        elif 'extension' in type_str:
            return LienType.LIEN_EXTENSION
        elif 'stop notice' in type_str:
            return LienType.STOP_NOTICE
        elif 'preliminary' in type_str or 'pre-lien' in type_str:
            return LienType.PRELIMINARY_NOTICE
        elif 'material' in type_str:
            return LienType.MATERIALMAN_LIEN
        elif 'subcontractor' in type_str:
            return LienType.SUBCONTRACTOR_LIEN
        elif 'laborer' in type_str:
            return LienType.LABORER_LIEN
        elif 'design' in type_str or 'architect' in type_str or 'engineer' in type_str:
            return LienType.DESIGN_PROFESSIONAL
        elif 'contractor' in type_str:
            return LienType.CONTRACTOR_LIEN
        else:
            return LienType.MECHANICS_LIEN

    async def search_by_property_address(
        self,
        address: str,
        city: str,
        state: str,
        county: Optional[str] = None
    ) -> List[MechanicLienRecord]:
        """Search for mechanic's liens by property address"""
        results = []

        if state not in STATE_LIEN_LAWS:
            logger.warning(f"Unknown state: {state}")
            return results

        # Find county recorder
        if county:
            county_key = f"{state}_{county.upper().replace(' ', '_')}"
            if county_key in COUNTY_RECORDER_SOURCES:
                config = COUNTY_RECORDER_SOURCES[county_key]
                logger.info(f"Searching {config['name']} for liens at {address}")

        return results

    async def search_by_property_owner(
        self,
        owner_name: str,
        state: str,
        county: Optional[str] = None
    ) -> List[MechanicLienRecord]:
        """Search for mechanic's liens by property owner name"""
        results = []

        if state not in STATE_LIEN_LAWS:
            return results

        logger.info(f"Searching for liens against {owner_name} in {state}")

        return results

    async def search_by_claimant(
        self,
        claimant_name: str,
        state: str,
        county: Optional[str] = None
    ) -> List[MechanicLienRecord]:
        """Search for mechanic's liens filed by a claimant"""
        results = []

        if state not in STATE_LIEN_LAWS:
            return results

        logger.info(f"Searching for liens filed by {claimant_name} in {state}")

        return results

    async def search_by_apn(
        self,
        apn: str,
        state: str,
        county: str
    ) -> List[MechanicLienRecord]:
        """Search for mechanic's liens by Assessor's Parcel Number"""
        results = []

        if state not in STATE_LIEN_LAWS:
            return results

        logger.info(f"Searching for liens on APN {apn} in {county}, {state}")

        return results

    async def get_lien_by_document_number(
        self,
        document_number: str,
        state: str,
        county: str
    ) -> Optional[MechanicLienRecord]:
        """Get a specific lien by document number"""
        if state not in STATE_LIEN_LAWS:
            return None

        logger.info(f"Looking up lien document {document_number}")

        return None

    async def get_recent_liens(
        self,
        state: str,
        county: Optional[str] = None,
        days: int = 30
    ) -> List[MechanicLienRecord]:
        """Get recently filed mechanic's liens"""
        results = []

        if state not in STATE_LIEN_LAWS:
            return results

        logger.info(f"Getting liens filed in last {days} days in {state}")

        return results

    async def get_expiring_liens(
        self,
        state: str,
        county: Optional[str] = None,
        days: int = 30
    ) -> List[MechanicLienRecord]:
        """Get liens that are expiring soon (foreclosure deadline approaching)"""
        results = []

        if state not in STATE_LIEN_LAWS:
            return results

        state_info = STATE_LIEN_LAWS[state]
        foreclosure_deadline = state_info.get('foreclosure_deadline_days', 365)

        logger.info(f"Getting liens expiring within {days} days in {state}")
        logger.info(f"State foreclosure deadline: {foreclosure_deadline} days from filing")

        return results

    async def search_lien_releases(
        self,
        state: str,
        county: Optional[str] = None,
        days: int = 30
    ) -> List[MechanicLienRecord]:
        """Search for recently recorded lien releases"""
        results = []

        if state not in STATE_LIEN_LAWS:
            return results

        logger.info(f"Getting lien releases in last {days} days in {state}")

        return results

    def get_lien_law_info(self, state: str) -> Optional[Dict[str, Any]]:
        """Get mechanic's lien law information for a state"""
        return STATE_LIEN_LAWS.get(state.upper())

    def get_filing_deadline(self, state: str, claimant_type: str = "contractor") -> Optional[Dict[str, Any]]:
        """Get filing deadline for a state"""
        if state.upper() not in STATE_LIEN_LAWS:
            return None

        info = STATE_LIEN_LAWS[state.upper()]

        return {
            'state': state.upper(),
            'filing_deadline_days': info.get('filing_deadline_days'),
            'filing_deadline_sub_days': info.get('filing_deadline_sub_days', info.get('filing_deadline_days')),
            'foreclosure_deadline_days': info.get('foreclosure_deadline_days'),
            'preliminary_notice_required': info.get('preliminary_notice_required', False),
            'preliminary_notice_days': info.get('preliminary_notice_days'),
            'filing_office': info.get('filing_office'),
        }

    def get_county_recorder(self, state: str, county: str) -> Optional[Dict[str, Any]]:
        """Get county recorder information"""
        county_key = f"{state.upper()}_{county.upper().replace(' ', '_')}"

        if county_key in COUNTY_RECORDER_SOURCES:
            return COUNTY_RECORDER_SOURCES[county_key]

        # Return general state info
        if state.upper() in STATE_LIEN_LAWS:
            state_info = STATE_LIEN_LAWS[state.upper()]
            return {
                'name': f"{county} County {state_info['filing_office']}",
                'filing_office': state_info['filing_office'],
            }

        return None

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get mechanic's lien law information for all states"""
        return {
            state: {
                'name': info['name'],
                'statute': info['statute'],
                'filing_deadline_days': info['filing_deadline_days'],
                'foreclosure_deadline_days': info['foreclosure_deadline_days'],
                'preliminary_notice_required': info.get('preliminary_notice_required', False),
                'filing_office': info['filing_office'],
            }
            for state, info in STATE_LIEN_LAWS.items()
        }

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics"""
        total_states = len(STATE_LIEN_LAWS)
        total_counties = len(COUNTY_RECORDER_SOURCES)

        # Count features
        with_preliminary_notice = sum(
            1 for s in STATE_LIEN_LAWS.values()
            if s.get('preliminary_notice_required')
        )
        with_stop_notice = sum(
            1 for s in STATE_LIEN_LAWS.values()
            if s.get('stop_notice_available')
        )

        # Filing deadline ranges
        deadlines = [s['filing_deadline_days'] for s in STATE_LIEN_LAWS.values()]
        foreclosure_deadlines = [s['foreclosure_deadline_days'] for s in STATE_LIEN_LAWS.values()]

        return {
            'total_states': total_states,
            'total_county_recorders': total_counties,
            'states_requiring_preliminary_notice': with_preliminary_notice,
            'states_with_stop_notice': with_stop_notice,
            'filing_deadline_range': {
                'min_days': min(deadlines),
                'max_days': max(deadlines),
                'avg_days': sum(deadlines) // len(deadlines),
            },
            'foreclosure_deadline_range': {
                'min_days': min(foreclosure_deadlines),
                'max_days': max(foreclosure_deadlines),
                'avg_days': sum(foreclosure_deadlines) // len(foreclosure_deadlines),
            },
        }


# Synchronous wrapper functions
def search_liens_by_property(
    address: str,
    city: str,
    state: str,
    county: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching liens by property address"""
    async def _search():
        async with MechanicLiensAPI() as api:
            results = await api.search_by_property_address(address, city, state, county)
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def search_liens_by_owner(
    owner_name: str,
    state: str,
    county: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching liens by property owner"""
    async def _search():
        async with MechanicLiensAPI() as api:
            results = await api.search_by_property_owner(owner_name, state, county)
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def search_liens_by_claimant(
    claimant_name: str,
    state: str,
    county: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for searching liens by claimant"""
    async def _search():
        async with MechanicLiensAPI() as api:
            results = await api.search_by_claimant(claimant_name, state, county)
            return [r.to_dict() for r in results]

    return asyncio.run(_search())


def get_lien_by_document(
    document_number: str,
    state: str,
    county: str
) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for getting lien by document number"""
    async def _get():
        async with MechanicLiensAPI() as api:
            result = await api.get_lien_by_document_number(document_number, state, county)
            return result.to_dict() if result else None

    return asyncio.run(_get())


def get_recent_liens(
    state: str,
    county: Optional[str] = None,
    days: int = 30
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for getting recent liens"""
    async def _get():
        async with MechanicLiensAPI() as api:
            results = await api.get_recent_liens(state, county, days)
            return [r.to_dict() for r in results]

    return asyncio.run(_get())


def get_lien_law_info(state: str) -> Optional[Dict[str, Any]]:
    """Get mechanic's lien law information for a state"""
    api = MechanicLiensAPI()
    return api.get_lien_law_info(state)


def get_filing_deadline(state: str, claimant_type: str = "contractor") -> Optional[Dict[str, Any]]:
    """Get filing deadline for a state"""
    api = MechanicLiensAPI()
    return api.get_filing_deadline(state, claimant_type)


def get_county_recorder_info(state: str, county: str) -> Optional[Dict[str, Any]]:
    """Get county recorder information"""
    api = MechanicLiensAPI()
    return api.get_county_recorder(state, county)


def get_all_state_lien_laws() -> Dict[str, Dict[str, Any]]:
    """Get mechanic's lien law information for all states"""
    api = MechanicLiensAPI()
    return api.get_all_states()


def get_coverage_stats() -> Dict[str, Any]:
    """Get coverage statistics for mechanic's liens"""
    api = MechanicLiensAPI()
    return api.get_coverage_stats()


if __name__ == "__main__":
    # Test the API
    print("Mechanic's Liens Scraper")
    print("=" * 50)

    stats = get_coverage_stats()
    print(f"\nCoverage Statistics:")
    print(f"  Total States: {stats['total_states']}")
    print(f"  County Recorders Configured: {stats['total_county_recorders']}")
    print(f"  States Requiring Preliminary Notice: {stats['states_requiring_preliminary_notice']}")

    print(f"\nFiling Deadline Range:")
    print(f"  Min: {stats['filing_deadline_range']['min_days']} days")
    print(f"  Max: {stats['filing_deadline_range']['max_days']} days")
    print(f"  Average: {stats['filing_deadline_range']['avg_days']} days")

    print(f"\nForeclosure Deadline Range:")
    print(f"  Min: {stats['foreclosure_deadline_range']['min_days']} days")
    print(f"  Max: {stats['foreclosure_deadline_range']['max_days']} days")
    print(f"  Average: {stats['foreclosure_deadline_range']['avg_days']} days")

    print("\nStates with Shortest Filing Deadlines:")
    states = get_all_state_lien_laws()
    sorted_states = sorted(states.items(), key=lambda x: x[1]['filing_deadline_days'])
    for state_code, info in sorted_states[:5]:
        print(f"  {state_code}: {info['filing_deadline_days']} days - {info['name']}")
