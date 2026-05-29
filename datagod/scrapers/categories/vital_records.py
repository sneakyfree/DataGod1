"""
Vital Records Scraper

Free public vital records sources:
- Death records (Social Security Death Index via FamilySearch)
- Marriage records (state/county vital records offices)
- Divorce records (county courts)
- Birth records (limited - mostly indices)

Note: Most vital records are restricted. This module focuses on
publicly accessible indices and summary data.

Free Sources Integrated:
- Find A Grave (findagrave.com) - death/burial records
- BillionGraves API - cemetery records with GPS coordinates
- CDC WONDER - death statistics and aggregated data
- State vital records portals - varies by state
- Obituary aggregators - newspaper obituaries

Note on FamilySearch:
FamilySearch offers free access to historical records but requires
a free account. This module provides integration guidance and
direct URLs for FamilySearch searches.
"""

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlencode

logger = logging.getLogger(__name__)

# Try to import aiohttp for async requests
try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available, async methods will be limited")


class RecordType(Enum):
    """Vital record types"""

    DEATH = "death"
    MARRIAGE = "marriage"
    DIVORCE = "divorce"
    BIRTH = "birth"
    BURIAL = "burial"
    OBITUARY = "obituary"


class RecordSource(Enum):
    """Vital record sources"""

    SSDI = "Social Security Death Index"
    FAMILYSEARCH = "FamilySearch"
    FINDAGRAVE = "Find A Grave"
    BILLIONGRAVES = "BillionGraves"
    STATE_RECORDS = "State Vital Records"
    COUNTY_RECORDS = "County Vital Records"
    CDC_WONDER = "CDC WONDER"
    NEWSPAPER = "Newspaper Obituary"
    ANCESTRY_FREE = "Ancestry Free Collections"


@dataclass
class DeathRecord:
    """Death record from public indices"""

    name: str
    death_date: Optional[date] = None
    birth_date: Optional[date] = None
    death_place: Optional[str] = None
    birth_place: Optional[str] = None
    age_at_death: Optional[int] = None
    ssn_last_four: Optional[str] = None
    state_issued: Optional[str] = None
    source: Optional[RecordSource] = None
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    burial_location: Optional[str] = None
    cemetery: Optional[str] = None
    obituary_text: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "death_date": self.death_date.isoformat() if self.death_date else None,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "death_place": self.death_place,
            "birth_place": self.birth_place,
            "age_at_death": self.age_at_death,
            "ssn_last_four": self.ssn_last_four,
            "state_issued": self.state_issued,
            "source": self.source.value if self.source else None,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "burial_location": self.burial_location,
            "cemetery": self.cemetery,
            "obituary_text": self.obituary_text,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class MarriageRecord:
    """Marriage record from public indices"""

    spouse1_name: str
    spouse2_name: str
    marriage_date: Optional[date] = None
    marriage_place: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    license_number: Optional[str] = None
    officiant: Optional[str] = None
    source: Optional[RecordSource] = None
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spouse1_name": self.spouse1_name,
            "spouse2_name": self.spouse2_name,
            "marriage_date": (
                self.marriage_date.isoformat() if self.marriage_date else None
            ),
            "marriage_place": self.marriage_place,
            "county": self.county,
            "state": self.state,
            "license_number": self.license_number,
            "officiant": self.officiant,
            "source": self.source.value if self.source else None,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class DivorceRecord:
    """Divorce record from court records"""

    party1_name: str
    party2_name: str
    filing_date: Optional[date] = None
    final_date: Optional[date] = None
    county: Optional[str] = None
    state: Optional[str] = None
    case_number: Optional[str] = None
    court: Optional[str] = None
    source: Optional[RecordSource] = None
    source_url: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "party1_name": self.party1_name,
            "party2_name": self.party2_name,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "final_date": self.final_date.isoformat() if self.final_date else None,
            "county": self.county,
            "state": self.state,
            "case_number": self.case_number,
            "court": self.court,
            "source": self.source.value if self.source else None,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class BurialRecord:
    """Cemetery/burial record"""

    name: str
    birth_date: Optional[date] = None
    death_date: Optional[date] = None
    cemetery_name: Optional[str] = None
    cemetery_location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    plot_info: Optional[str] = None
    headstone_inscription: Optional[str] = None
    photo_url: Optional[str] = None
    memorial_url: Optional[str] = None
    source: Optional[RecordSource] = None
    source_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bio_text: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "death_date": self.death_date.isoformat() if self.death_date else None,
            "cemetery_name": self.cemetery_name,
            "cemetery_location": self.cemetery_location,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "plot_info": self.plot_info,
            "headstone_inscription": self.headstone_inscription,
            "photo_url": self.photo_url,
            "memorial_url": self.memorial_url,
            "source": self.source.value if self.source else None,
            "source_id": self.source_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "bio_text": self.bio_text,
            "fetched_at": self.fetched_at.isoformat(),
        }


# =============================================================================
# State Vital Records Office Database
# =============================================================================

STATE_VITAL_RECORDS_OFFICES: Dict[str, Dict[str, Any]] = {
    "AL": {
        "name": "Alabama Center for Health Statistics",
        "address": "201 Monroe St, Montgomery, AL 36104",
        "phone": "(334) 206-5418",
        "url": "https://www.alabamapublichealth.gov/vitalrecords/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1908,
            "death": 1908,
            "marriage": 1936,
            "divorce": 1950,
        },
    },
    "AK": {
        "name": "Alaska Bureau of Vital Statistics",
        "address": "P.O. Box 110675, Juneau, AK 99811",
        "phone": "(907) 465-3391",
        "url": "https://health.alaska.gov/dph/VitalStats/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1913,
            "death": 1913,
            "marriage": 1913,
            "divorce": 1950,
        },
    },
    "AZ": {
        "name": "Arizona Office of Vital Records",
        "address": "1818 W Adams St, Phoenix, AZ 85007",
        "phone": "(602) 364-1300",
        "url": "https://azdhs.gov/vital-records/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage"],
        "years_on_file": {"birth": 1909, "death": 1909, "marriage": 1909},
    },
    "AR": {
        "name": "Arkansas Department of Health",
        "address": "4815 W Markham St, Little Rock, AR 72205",
        "phone": "(501) 661-2336",
        "url": "https://www.healthy.arkansas.gov/programs-services/topics/certificates-background-checks",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1914,
            "death": 1914,
            "marriage": 1917,
            "divorce": 1923,
        },
    },
    "CA": {
        "name": "California Department of Public Health",
        "address": "P.O. Box 997410, Sacramento, CA 95899",
        "phone": "(916) 445-2684",
        "url": "https://www.cdph.ca.gov/Programs/CHSI/Pages/Vital-Records.aspx",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1905,
            "death": 1905,
            "marriage": 1905,
            "divorce": 1962,
        },
        "notes": "Informational copies available to anyone; certified copies restricted",
    },
    "CO": {
        "name": "Colorado Vital Records",
        "address": "4300 Cherry Creek Drive S, Denver, CO 80246",
        "phone": "(303) 692-2200",
        "url": "https://cdphe.colorado.gov/vitalrecords",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1910,
            "death": 1910,
            "marriage": 1900,
            "divorce": 1900,
        },
    },
    "CT": {
        "name": "Connecticut Vital Records",
        "address": "410 Capitol Ave, Hartford, CT 06134",
        "phone": "(860) 509-7897",
        "url": "https://portal.ct.gov/DPH/Vital-Records/Vital-Records",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage"],
        "years_on_file": {"birth": 1897, "death": 1897, "marriage": 1897},
    },
    "DE": {
        "name": "Delaware Office of Vital Statistics",
        "address": "417 Federal St, Dover, DE 19901",
        "phone": "(302) 744-4549",
        "url": "https://dhss.delaware.gov/dhss/dph/ss/vitalstats.html",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage"],
        "years_on_file": {"birth": 1861, "death": 1881, "marriage": 1847},
    },
    "FL": {
        "name": "Florida Office of Vital Statistics",
        "address": "P.O. Box 210, Jacksonville, FL 32231",
        "phone": "(904) 359-6900",
        "url": "https://www.floridahealth.gov/certificates/certificates/index.html",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1917,
            "death": 1917,
            "marriage": 1927,
            "divorce": 1927,
        },
    },
    "GA": {
        "name": "Georgia Vital Records",
        "address": "2600 Skyland Drive NE, Atlanta, GA 30319",
        "phone": "(404) 679-4701",
        "url": "https://dph.georgia.gov/VitalRecords",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1919,
            "death": 1919,
            "marriage": 1952,
            "divorce": 1952,
        },
    },
    "HI": {
        "name": "Hawaii Office of Health Status Monitoring",
        "address": "P.O. Box 3378, Honolulu, HI 96801",
        "phone": "(808) 586-4533",
        "url": "https://health.hawaii.gov/vitalrecords/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1853,
            "death": 1853,
            "marriage": 1842,
            "divorce": 1951,
        },
    },
    "ID": {
        "name": "Idaho Vital Records",
        "address": "450 W State St, Boise, ID 83720",
        "phone": "(208) 334-5988",
        "url": "https://healthandwelfare.idaho.gov/services-programs/vital-records",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1911,
            "death": 1911,
            "marriage": 1947,
            "divorce": 1947,
        },
    },
    "IL": {
        "name": "Illinois Division of Vital Records",
        "address": "925 E Ridgely Ave, Springfield, IL 62702",
        "phone": "(217) 782-6553",
        "url": "https://dph.illinois.gov/topics-services/birth-death-other-records/vital-records.html",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1916,
            "death": 1916,
            "marriage": 1962,
            "divorce": 1962,
        },
    },
    "IN": {
        "name": "Indiana Vital Records",
        "address": "P.O. Box 7125, Indianapolis, IN 46206",
        "phone": "(317) 233-2700",
        "url": "https://www.in.gov/health/vital-records/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage"],
        "years_on_file": {"birth": 1907, "death": 1900, "marriage": 1958},
    },
    "IA": {
        "name": "Iowa Vital Records",
        "address": "321 E 12th St, Des Moines, IA 50319",
        "phone": "(515) 281-4944",
        "url": "https://idph.iowa.gov/health-statistics/vital-records",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1880,
            "death": 1880,
            "marriage": 1880,
            "divorce": 1906,
        },
    },
    "KS": {
        "name": "Kansas Office of Vital Statistics",
        "address": "1000 SW Jackson St, Topeka, KS 66612",
        "phone": "(785) 296-1400",
        "url": "https://www.kdheks.gov/vital/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1911,
            "death": 1911,
            "marriage": 1913,
            "divorce": 1951,
        },
    },
    "KY": {
        "name": "Kentucky Office of Vital Statistics",
        "address": "275 E Main St, Frankfort, KY 40621",
        "phone": "(502) 564-4212",
        "url": "https://chfs.ky.gov/agencies/dph/dehp/vsb/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1911,
            "death": 1911,
            "marriage": 1958,
            "divorce": 1958,
        },
    },
    "LA": {
        "name": "Louisiana Vital Records Registry",
        "address": "P.O. Box 60630, New Orleans, LA 70160",
        "phone": "(504) 593-5100",
        "url": "https://ldh.la.gov/vitalrecords",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage"],
        "years_on_file": {"birth": 1914, "death": 1914, "marriage": 1946},
        "notes": "Orleans Parish records from 1790",
    },
    "ME": {
        "name": "Maine Office of Vital Records",
        "address": "11 State House Station, Augusta, ME 04333",
        "phone": "(207) 287-3181",
        "url": "https://www.maine.gov/dhhs/mecdc/public-health-systems/data-research/vital-records/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1923,
            "death": 1923,
            "marriage": 1892,
            "divorce": 1892,
        },
    },
    "MD": {
        "name": "Maryland Division of Vital Records",
        "address": "6764 Reisterstown Rd, Baltimore, MD 21215",
        "phone": "(410) 764-3038",
        "url": "https://health.maryland.gov/vsa/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1898,
            "death": 1898,
            "marriage": 1951,
            "divorce": 1961,
        },
    },
    "MA": {
        "name": "Massachusetts Registry of Vital Records",
        "address": "150 Mount Vernon St, Boston, MA 02125",
        "phone": "(617) 740-2600",
        "url": "https://www.mass.gov/orgs/registry-of-vital-records-and-statistics",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage"],
        "years_on_file": {"birth": 1841, "death": 1841, "marriage": 1841},
    },
    "MI": {
        "name": "Michigan Vital Records",
        "address": "P.O. Box 30721, Lansing, MI 48909",
        "phone": "(517) 335-8656",
        "url": "https://www.michigan.gov/mdhhs/assistance-programs/vital-records",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1867,
            "death": 1867,
            "marriage": 1867,
            "divorce": 1897,
        },
    },
    "MN": {
        "name": "Minnesota Office of Vital Records",
        "address": "P.O. Box 64499, St. Paul, MN 55164",
        "phone": "(651) 201-5970",
        "url": "https://www.health.state.mn.us/people/vitalrecords/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1900,
            "death": 1908,
            "marriage": 1958,
            "divorce": 1970,
        },
    },
    "MS": {
        "name": "Mississippi Vital Records",
        "address": "P.O. Box 1700, Jackson, MS 39215",
        "phone": "(601) 576-7960",
        "url": "https://msdh.ms.gov/page/30,0,109.html",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1912,
            "death": 1912,
            "marriage": 1926,
            "divorce": 1926,
        },
    },
    "MO": {
        "name": "Missouri Bureau of Vital Records",
        "address": "P.O. Box 570, Jefferson City, MO 65102",
        "phone": "(573) 751-6387",
        "url": "https://health.mo.gov/data/vitalrecords/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1910,
            "death": 1910,
            "marriage": 1948,
            "divorce": 1948,
        },
    },
    "MT": {
        "name": "Montana Office of Vital Statistics",
        "address": "111 N Sanders St, Helena, MT 59620",
        "phone": "(406) 444-4228",
        "url": "https://dphhs.mt.gov/vitalrecords",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1907,
            "death": 1907,
            "marriage": 1943,
            "divorce": 1943,
        },
    },
    "NE": {
        "name": "Nebraska Vital Records",
        "address": "P.O. Box 95065, Lincoln, NE 68509",
        "phone": "(402) 471-2871",
        "url": "https://dhhs.ne.gov/Pages/Vital-Records.aspx",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1904,
            "death": 1904,
            "marriage": 1909,
            "divorce": 1909,
        },
    },
    "NV": {
        "name": "Nevada Office of Vital Records",
        "address": "4150 Technology Way, Carson City, NV 89706",
        "phone": "(775) 684-4242",
        "url": "https://dpbh.nv.gov/Programs/Vital_Records/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1911,
            "death": 1911,
            "marriage": 1968,
            "divorce": 1968,
        },
    },
    "NH": {
        "name": "New Hampshire Division of Vital Records",
        "address": "29 Hazen Dr, Concord, NH 03301",
        "phone": "(603) 271-4650",
        "url": "https://www.dhhs.nh.gov/programs-services/vital-records",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1640,
            "death": 1640,
            "marriage": 1640,
            "divorce": 1808,
        },
    },
    "NJ": {
        "name": "New Jersey Office of Vital Statistics",
        "address": "P.O. Box 370, Trenton, NJ 08625",
        "phone": "(609) 292-4087",
        "url": "https://www.nj.gov/health/vital/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1878,
            "death": 1878,
            "marriage": 1848,
            "divorce": 1948,
        },
    },
    "NM": {
        "name": "New Mexico Vital Records",
        "address": "P.O. Box 25767, Albuquerque, NM 87125",
        "phone": "(505) 827-0121",
        "url": "https://www.nmhealth.org/about/erd/bvrhs/vrb/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage"],
        "years_on_file": {"birth": 1920, "death": 1920, "marriage": 1920},
    },
    "NY": {
        "name": "New York State Vital Records",
        "address": "P.O. Box 2602, Albany, NY 12220",
        "phone": "(518) 474-3075",
        "url": "https://www.health.ny.gov/vital_records/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1881,
            "death": 1880,
            "marriage": 1880,
            "divorce": 1963,
        },
        "notes": "NYC has separate office - NYC records not included",
    },
    "NC": {
        "name": "North Carolina Vital Records",
        "address": "1903 Mail Service Center, Raleigh, NC 27699",
        "phone": "(919) 733-3526",
        "url": "https://vitalrecords.nc.gov/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1913,
            "death": 1913,
            "marriage": 1962,
            "divorce": 1958,
        },
    },
    "ND": {
        "name": "North Dakota Vital Records",
        "address": "600 E Boulevard Ave, Bismarck, ND 58505",
        "phone": "(701) 328-2360",
        "url": "https://www.health.nd.gov/vital",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1907,
            "death": 1907,
            "marriage": 1925,
            "divorce": 1949,
        },
    },
    "OH": {
        "name": "Ohio Office of Vital Statistics",
        "address": "225 Neilston St, Columbus, OH 43215",
        "phone": "(614) 466-2531",
        "url": "https://odh.ohio.gov/know-our-programs/vital-statistics/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1908,
            "death": 1908,
            "marriage": 1949,
            "divorce": 1948,
        },
    },
    "OK": {
        "name": "Oklahoma Vital Records",
        "address": "1000 NE 10th St, Oklahoma City, OK 73117",
        "phone": "(405) 271-4040",
        "url": "https://oklahoma.gov/health/services/vital-records.html",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage"],
        "years_on_file": {"birth": 1908, "death": 1908, "marriage": 1951},
    },
    "OR": {
        "name": "Oregon Vital Records",
        "address": "800 NE Oregon St, Portland, OR 97232",
        "phone": "(971) 673-1190",
        "url": "https://www.oregon.gov/oha/PH/BIRTHDEATHCERTIFICATES/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1903,
            "death": 1903,
            "marriage": 1906,
            "divorce": 1925,
        },
    },
    "PA": {
        "name": "Pennsylvania Division of Vital Records",
        "address": "P.O. Box 1528, New Castle, PA 16103",
        "phone": "(724) 656-3100",
        "url": "https://www.health.pa.gov/topics/certificates/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1906,
            "death": 1906,
            "marriage": 1906,
            "divorce": 1946,
        },
    },
    "RI": {
        "name": "Rhode Island Office of Vital Records",
        "address": "3 Capitol Hill, Providence, RI 02908",
        "phone": "(401) 222-2811",
        "url": "https://health.ri.gov/records/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage"],
        "years_on_file": {"birth": 1853, "death": 1853, "marriage": 1853},
    },
    "SC": {
        "name": "South Carolina Vital Records",
        "address": "2600 Bull St, Columbia, SC 29201",
        "phone": "(803) 898-3630",
        "url": "https://scdhec.gov/vital-records",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1915,
            "death": 1915,
            "marriage": 1950,
            "divorce": 1962,
        },
    },
    "SD": {
        "name": "South Dakota Vital Records",
        "address": "207 E Missouri Ave, Pierre, SD 57501",
        "phone": "(605) 773-4961",
        "url": "https://doh.sd.gov/records/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1905,
            "death": 1905,
            "marriage": 1905,
            "divorce": 1905,
        },
    },
    "TN": {
        "name": "Tennessee Office of Vital Records",
        "address": "710 James Robertson Parkway, Nashville, TN 37243",
        "phone": "(615) 741-1763",
        "url": "https://www.tn.gov/health/health-program-areas/vital-records.html",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1914,
            "death": 1914,
            "marriage": 1945,
            "divorce": 1945,
        },
    },
    "TX": {
        "name": "Texas Vital Statistics",
        "address": "P.O. Box 12040, Austin, TX 78711",
        "phone": "(512) 776-7111",
        "url": "https://www.dshs.texas.gov/vital-statistics",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1903,
            "death": 1903,
            "marriage": 1966,
            "divorce": 1968,
        },
    },
    "UT": {
        "name": "Utah Office of Vital Records",
        "address": "288 N 1460 W, Salt Lake City, UT 84116",
        "phone": "(801) 538-6105",
        "url": "https://vitalrecords.utah.gov/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1905,
            "death": 1905,
            "marriage": 1978,
            "divorce": 1978,
        },
    },
    "VT": {
        "name": "Vermont Vital Records",
        "address": "P.O. Box 70, Burlington, VT 05402",
        "phone": "(802) 863-7275",
        "url": "https://www.healthvermont.gov/vital-records",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1760,
            "death": 1760,
            "marriage": 1760,
            "divorce": 1968,
        },
    },
    "VA": {
        "name": "Virginia Division of Vital Records",
        "address": "P.O. Box 1000, Richmond, VA 23218",
        "phone": "(804) 662-6200",
        "url": "https://www.vdh.virginia.gov/vital-records/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1912,
            "death": 1912,
            "marriage": 1936,
            "divorce": 1918,
        },
    },
    "WA": {
        "name": "Washington Center for Health Statistics",
        "address": "P.O. Box 9709, Olympia, WA 98507",
        "phone": "(360) 236-4300",
        "url": "https://www.doh.wa.gov/LicensesPermitsandCertificates/BirthDeathMarriageandDivorce",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1907,
            "death": 1907,
            "marriage": 1968,
            "divorce": 1968,
        },
    },
    "WV": {
        "name": "West Virginia Vital Registration Office",
        "address": "350 Capitol St, Charleston, WV 25301",
        "phone": "(304) 558-2931",
        "url": "https://dhhr.wv.gov/vitalreg/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1917,
            "death": 1917,
            "marriage": 1964,
            "divorce": 1968,
        },
    },
    "WI": {
        "name": "Wisconsin Vital Records",
        "address": "1 W Wilson St, Madison, WI 53703",
        "phone": "(608) 266-1371",
        "url": "https://www.dhs.wisconsin.gov/vitalrecords/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1907,
            "death": 1907,
            "marriage": 1907,
            "divorce": 1907,
        },
    },
    "WY": {
        "name": "Wyoming Vital Statistics Services",
        "address": "2300 Capitol Ave, Cheyenne, WY 82002",
        "phone": "(307) 777-7591",
        "url": "https://health.wyo.gov/admin/vitalstatistics/",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1909,
            "death": 1909,
            "marriage": 1941,
            "divorce": 1941,
        },
    },
    "DC": {
        "name": "DC Vital Records Division",
        "address": "899 N Capitol St NE, Washington, DC 20002",
        "phone": "(202) 442-9009",
        "url": "https://dchealth.dc.gov/service/vital-records",
        "online_ordering": True,
        "records_available": ["birth", "death", "marriage", "divorce"],
        "years_on_file": {
            "birth": 1874,
            "death": 1874,
            "marriage": 1811,
            "divorce": 1956,
        },
    },
}


# =============================================================================
# Vital Records API (Main Implementation)
# =============================================================================


class VitalRecordsAPI:
    """
    API for searching vital records from free public sources.

    Integrates:
    - Find A Grave (free, no API key required for basic search)
    - BillionGraves (limited free tier)
    - CDC WONDER (aggregate death statistics)
    - State vital records office lookups
    - FamilySearch search URL generation

    All methods are async-first with synchronous wrappers.
    """

    # API endpoints
    FINDAGRAVE_SEARCH_URL = "https://www.findagrave.com/memorial/search"
    CDC_WONDER_URL = "https://wonder.cdc.gov"
    FAMILYSEARCH_SEARCH_URL = "https://www.familysearch.org/search/record/results"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Vital Records API.

        Args:
            config: Optional configuration dict
        """
        self.config = config or {}
        self._session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0
        self.last_request_time = None

        logger.info("Initialized VitalRecordsAPI")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "DataGod/1.0 (Public Records Research)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _rate_limit(self, delay: float = 2.0):
        """Apply rate limiting between requests."""
        if self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
        self.last_request_time = datetime.now()
        self.request_count += 1

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse various date formats."""
        if not date_str:
            return None
        date_str = date_str.strip()

        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%Y",
            "%b %d, %Y",
            "%d-%m-%Y",
            "%m-%d-%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Try to extract just year
        year_match = re.search(r"(\d{4})", date_str)
        if year_match:
            try:
                return date(int(year_match.group(1)), 1, 1)
            except ValueError:
                pass

        return None

    # =========================================================================
    # State Vital Records Office Lookup
    # =========================================================================

    def get_state_vital_records_office(self, state: str) -> Dict[str, Any]:
        """
        Get contact info for state vital records office.

        Args:
            state: Two-letter state code

        Returns:
            Office contact information including URL, phone, records available
        """
        state = state.upper()
        return STATE_VITAL_RECORDS_OFFICES.get(
            state,
            {
                "name": f"{state} Vital Records Office",
                "url": f"https://www.google.com/search?q={state}+vital+records+office",
                "online_ordering": False,
                "records_available": ["birth", "death", "marriage", "divorce"],
                "notes": "State not found in database - please verify contact information",
            },
        )

    def get_all_state_offices(self) -> Dict[str, Dict[str, Any]]:
        """Get all state vital records offices."""
        return STATE_VITAL_RECORDS_OFFICES.copy()

    # =========================================================================
    # Find A Grave Integration
    # =========================================================================

    async def search_find_a_grave(
        self,
        firstname: str = "",
        lastname: str = "",
        birth_year: int = None,
        death_year: int = None,
        cemetery_name: str = "",
        city: str = "",
        state: str = "",
        country: str = "US",
        limit: int = 50,
    ) -> List[BurialRecord]:
        """
        Search Find A Grave for burial/cemetery records.

        Find A Grave is a free community-maintained database of cemetery
        records with over 210 million memorials worldwide.

        Args:
            firstname: First name
            lastname: Last name (required for meaningful results)
            birth_year: Year of birth
            death_year: Year of death
            cemetery_name: Cemetery name filter
            city: City filter
            state: State/province filter
            country: Country code (default US)
            limit: Maximum results

        Returns:
            List of BurialRecord objects
        """
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp required for Find A Grave searches")
            return []

        if not lastname:
            logger.warning("Last name required for Find A Grave search")
            return []

        await self._rate_limit(3.0)  # Be respectful of Find A Grave

        # Build search parameters
        params = {
            "firstname": firstname,
            "lastname": lastname,
            "orderby": "r",  # Relevance
            "page": 1,
        }

        if birth_year:
            params["birthyear"] = birth_year
        if death_year:
            params["deathyear"] = death_year
        if state:
            params["state"] = state
        if city:
            params["city"] = city
        if cemetery_name:
            params["cemeteryName"] = cemetery_name

        results = []

        try:
            session = await self._get_session()
            search_url = f"{self.FINDAGRAVE_SEARCH_URL}?{urlencode(params)}"

            async with session.get(search_url) as response:
                if response.status != 200:
                    logger.error(f"Find A Grave search error: {response.status}")
                    return results

                html = await response.text()
                results = self._parse_findagrave_results(html, limit)

                logger.info(f"Find A Grave search returned {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"Find A Grave search error: {e}")
            return results

    def _parse_findagrave_results(self, html: str, limit: int) -> List[BurialRecord]:
        """Parse Find A Grave search results HTML."""
        records = []

        # Find memorial entries - look for memorial links and data
        # Pattern for memorial cards
        memorial_pattern = re.compile(
            r'<a[^>]*href="/memorial/(\d+)/([^"]*)"[^>]*>.*?'
            r"<h2[^>]*>([^<]+)</h2>.*?"
            r"(?:Birth:?\s*([^<]*?))?(?:Death:?\s*([^<]*?))?"
            r"(?:Cemetery:?\s*([^<]*?))?",
            re.DOTALL | re.IGNORECASE,
        )

        # Simplified pattern for basic memorial links
        simple_pattern = re.compile(
            r'href="/memorial/(\d+)/([^"]*)"[^>]*class="[^"]*memorial-item[^"]*"[^>]*>'
            r'.*?<[^>]*class="[^"]*name[^"]*"[^>]*>([^<]+)<',
            re.DOTALL | re.IGNORECASE,
        )

        # Try to find memorial entries
        matches = memorial_pattern.findall(html)
        if not matches:
            matches = simple_pattern.findall(html)

        for match in matches[:limit]:
            try:
                if len(match) >= 3:
                    memorial_id = match[0]
                    memorial_slug = match[1]
                    name = match[2].strip() if len(match) > 2 else ""

                    # Clean up name - remove HTML entities
                    name = re.sub(r"&[^;]+;", " ", name)
                    name = " ".join(name.split())

                    if not name:
                        continue

                    birth_date = None
                    death_date = None
                    cemetery = None

                    if len(match) > 3 and match[3]:
                        birth_date = self._parse_date(match[3])
                    if len(match) > 4 and match[4]:
                        death_date = self._parse_date(match[4])
                    if len(match) > 5 and match[5]:
                        cemetery = match[5].strip()

                    record = BurialRecord(
                        name=name,
                        birth_date=birth_date,
                        death_date=death_date,
                        cemetery_name=cemetery,
                        source=RecordSource.FINDAGRAVE,
                        source_id=memorial_id,
                        memorial_url=f"https://www.findagrave.com/memorial/{memorial_id}/{memorial_slug}",
                    )
                    records.append(record)

            except Exception as e:
                logger.debug(f"Error parsing Find A Grave result: {e}")
                continue

        # If no results from pattern matching, create search guidance
        if not records:
            # Check if there are any results indicated
            if "results found" in html.lower() or "memorial" in html.lower():
                logger.info(
                    "Find A Grave returned results but parsing failed - providing search URL"
                )

        return records

    async def get_findagrave_memorial(self, memorial_id: str) -> Optional[BurialRecord]:
        """
        Get detailed information for a specific Find A Grave memorial.

        Args:
            memorial_id: Find A Grave memorial ID

        Returns:
            BurialRecord with full details or None
        """
        if not AIOHTTP_AVAILABLE:
            return None

        await self._rate_limit(3.0)

        try:
            session = await self._get_session()
            url = f"https://www.findagrave.com/memorial/{memorial_id}"

            async with session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                return self._parse_findagrave_memorial(html, memorial_id, url)

        except Exception as e:
            logger.error(f"Error fetching Find A Grave memorial: {e}")
            return None

    def _parse_findagrave_memorial(
        self, html: str, memorial_id: str, url: str
    ) -> Optional[BurialRecord]:
        """Parse a Find A Grave memorial page."""
        try:
            # Extract name
            name_match = re.search(r'<h1[^>]*id="bio-name"[^>]*>([^<]+)</h1>', html)
            if not name_match:
                name_match = re.search(r"<title>([^<|]+)", html)
            name = name_match.group(1).strip() if name_match else "Unknown"

            # Extract dates
            birth_match = re.search(
                r"Birth:?\s*</dt>\s*<dd[^>]*>([^<]+)", html, re.IGNORECASE
            )
            death_match = re.search(
                r"Death:?\s*</dt>\s*<dd[^>]*>([^<]+)", html, re.IGNORECASE
            )

            birth_date = self._parse_date(birth_match.group(1)) if birth_match else None
            death_date = self._parse_date(death_match.group(1)) if death_match else None

            # Extract cemetery info
            cemetery_match = re.search(
                r"Cemetery:?\s*</dt>\s*<dd[^>]*>\s*<a[^>]*>([^<]+)</a>",
                html,
                re.IGNORECASE,
            )
            cemetery_name = cemetery_match.group(1).strip() if cemetery_match else None

            # Extract location
            location_match = re.search(
                r'<span[^>]*class="[^"]*location[^"]*"[^>]*>([^<]+)</span>', html
            )
            location = location_match.group(1).strip() if location_match else None

            # Parse location into city/state
            city = None
            state = None
            if location:
                parts = [p.strip() for p in location.split(",")]
                if len(parts) >= 2:
                    city = parts[0]
                    state = parts[-2] if len(parts) > 2 else parts[-1]

            # Extract bio/inscription
            bio_match = re.search(
                r'<div[^>]*id="bio"[^>]*>(.*?)</div>', html, re.DOTALL
            )
            bio_text = None
            if bio_match:
                bio_text = re.sub(r"<[^>]+>", "", bio_match.group(1)).strip()
                bio_text = " ".join(bio_text.split())[:1000]  # Limit length

            # Extract photo URL
            photo_match = re.search(
                r'<img[^>]*class="[^"]*memorial-photo[^"]*"[^>]*src="([^"]+)"', html
            )
            photo_url = photo_match.group(1) if photo_match else None

            # Extract GPS coordinates if available
            lat_match = re.search(r'"latitude":\s*([-\d.]+)', html)
            lng_match = re.search(r'"longitude":\s*([-\d.]+)', html)
            latitude = float(lat_match.group(1)) if lat_match else None
            longitude = float(lng_match.group(1)) if lng_match else None

            # Extract plot info
            plot_match = re.search(
                r"Plot:?\s*</dt>\s*<dd[^>]*>([^<]+)", html, re.IGNORECASE
            )
            plot_info = plot_match.group(1).strip() if plot_match else None

            return BurialRecord(
                name=name,
                birth_date=birth_date,
                death_date=death_date,
                cemetery_name=cemetery_name,
                cemetery_location=location,
                city=city,
                state=state,
                country="USA",
                plot_info=plot_info,
                photo_url=photo_url,
                memorial_url=url,
                source=RecordSource.FINDAGRAVE,
                source_id=memorial_id,
                latitude=latitude,
                longitude=longitude,
                bio_text=bio_text,
            )

        except Exception as e:
            logger.error(f"Error parsing Find A Grave memorial: {e}")
            return None

    # =========================================================================
    # FamilySearch Integration (URL Generation)
    # =========================================================================

    def get_familysearch_search_url(
        self,
        firstname: str = "",
        lastname: str = "",
        birth_year: int = None,
        death_year: int = None,
        birth_place: str = "",
        death_place: str = "",
        record_type: str = "",
    ) -> str:
        """
        Generate a FamilySearch search URL.

        FamilySearch is free but requires a free account for full access.
        This generates a direct search URL for the user.

        Args:
            firstname: First name
            lastname: Last name
            birth_year: Year of birth
            death_year: Year of death
            birth_place: Place of birth
            death_place: Place of death
            record_type: Type filter (deaths, marriages, etc.)

        Returns:
            FamilySearch search URL
        """
        params = {}

        if firstname:
            params["q.givenName"] = firstname
        if lastname:
            params["q.surname"] = lastname
        if birth_year:
            params["q.birthLikeDate.from"] = str(birth_year - 2)
            params["q.birthLikeDate.to"] = str(birth_year + 2)
        if death_year:
            params["q.deathLikeDate.from"] = str(death_year - 2)
            params["q.deathLikeDate.to"] = str(death_year + 2)
        if birth_place:
            params["q.birthLikePlace"] = birth_place
        if death_place:
            params["q.deathLikePlace"] = death_place

        # Collection filters for record types
        collection_filters = {
            "deaths": "m.defaultFacets=on&m.queryRequireDefault=on&m.facetNestCollectionInCategory=on&f.collectionId=1202535",
            "marriages": "f.collectionId=1803970",
            "ssdi": "f.collectionId=1202535",  # Social Security Death Index
        }

        base_url = self.FAMILYSEARCH_SEARCH_URL
        if params:
            base_url += "?" + urlencode(params)
            if record_type and record_type.lower() in collection_filters:
                base_url += "&" + collection_filters[record_type.lower()]

        return base_url

    # =========================================================================
    # Death Record Search (Aggregated)
    # =========================================================================

    async def search_death_records(
        self,
        lastname: str,
        firstname: str = "",
        birth_year: int = None,
        death_year: int = None,
        state: str = "",
        limit: int = 50,
    ) -> List[DeathRecord]:
        """
        Search for death records across multiple free sources.

        Sources searched:
        - Find A Grave (cemetery records)
        - Generates FamilySearch URLs for SSDI

        Args:
            lastname: Last name (required)
            firstname: First name
            birth_year: Year of birth
            death_year: Year of death
            state: State filter
            limit: Maximum results

        Returns:
            List of DeathRecord objects
        """
        results = []

        if not lastname:
            logger.warning("Last name required for death record search")
            return results

        # Search Find A Grave
        burial_records = await self.search_find_a_grave(
            firstname=firstname,
            lastname=lastname,
            birth_year=birth_year,
            death_year=death_year,
            state=state,
            limit=limit,
        )

        # Convert burial records to death records
        for burial in burial_records:
            death_record = DeathRecord(
                name=burial.name,
                death_date=burial.death_date,
                birth_date=burial.birth_date,
                death_place=burial.cemetery_location,
                burial_location=burial.cemetery_location,
                cemetery=burial.cemetery_name,
                source=RecordSource.FINDAGRAVE,
                source_id=burial.source_id,
                source_url=burial.memorial_url,
            )
            results.append(death_record)

        # Add FamilySearch SSDI search guidance
        familysearch_url = self.get_familysearch_search_url(
            firstname=firstname,
            lastname=lastname,
            birth_year=birth_year,
            death_year=death_year,
            record_type="ssdi",
        )

        # Add a guidance record pointing to FamilySearch
        if len(results) < limit:
            guidance_record = DeathRecord(
                name=f"{firstname} {lastname}".strip() if firstname else lastname,
                source=RecordSource.FAMILYSEARCH,
                source_url=familysearch_url,
                obituary_text="Search FamilySearch for Social Security Death Index records (free account required)",
            )
            results.append(guidance_record)

        return results[:limit]

    # =========================================================================
    # Marriage Record Search
    # =========================================================================

    async def search_marriage_records(
        self,
        spouse_name: str,
        other_spouse: str = "",
        year_from: int = None,
        year_to: int = None,
        state: str = "",
        county: str = "",
        limit: int = 50,
    ) -> List[MarriageRecord]:
        """
        Search for marriage records.

        Note: Most marriage records require in-person or mail requests.
        This method provides:
        - State vital records office information
        - FamilySearch search URLs for historical records
        - County clerk contact information

        Args:
            spouse_name: Name of one spouse
            other_spouse: Name of other spouse (optional)
            year_from: Start year
            year_to: End year
            state: State filter
            county: County filter
            limit: Maximum results

        Returns:
            List of MarriageRecord objects (mostly guidance records)
        """
        results = []

        # Parse names
        name_parts = spouse_name.split()
        firstname = name_parts[0] if name_parts else ""
        lastname = (
            name_parts[-1]
            if len(name_parts) > 1
            else name_parts[0] if name_parts else ""
        )

        # Generate FamilySearch URL for historical marriage records
        familysearch_url = self.get_familysearch_search_url(
            firstname=firstname, lastname=lastname, record_type="marriages"
        )

        # Add FamilySearch guidance
        results.append(
            MarriageRecord(
                spouse1_name=spouse_name,
                spouse2_name=other_spouse or "Unknown",
                state=state or "US",
                source=RecordSource.FAMILYSEARCH,
                source_url=familysearch_url,
            )
        )

        # Add state vital records office info
        if state:
            office = self.get_state_vital_records_office(state)
            results.append(
                MarriageRecord(
                    spouse1_name=spouse_name,
                    spouse2_name=other_spouse or "Unknown",
                    state=state,
                    source=RecordSource.STATE_RECORDS,
                    source_url=office.get("url", ""),
                )
            )

        return results[:limit]

    # =========================================================================
    # Divorce Record Search
    # =========================================================================

    async def search_divorce_records(
        self,
        party_name: str,
        other_party: str = "",
        year_from: int = None,
        year_to: int = None,
        state: str = "",
        county: str = "",
        limit: int = 50,
    ) -> List[DivorceRecord]:
        """
        Search for divorce records.

        Note: Divorce records are court records, typically found at:
        - County clerk of court
        - State vital records office (index only)

        Args:
            party_name: Name of one party
            other_party: Name of other party (optional)
            year_from: Start year
            year_to: End year
            state: State filter
            county: County filter
            limit: Maximum results

        Returns:
            List of DivorceRecord objects (guidance records with lookup URLs)
        """
        results = []

        # Add state vital records office info
        if state:
            office = self.get_state_vital_records_office(state)
            years = office.get("years_on_file", {})

            results.append(
                DivorceRecord(
                    party1_name=party_name,
                    party2_name=other_party or "Unknown",
                    state=state,
                    court=office.get("name", f"{state} Vital Records"),
                    source=RecordSource.STATE_RECORDS,
                    source_url=office.get("url", ""),
                )
            )

        # Generate court records search URL
        if state and county:
            search_query = f"{county} county {state} divorce records"
            court_search_url = (
                f"https://www.google.com/search?q={quote_plus(search_query)}"
            )

            results.append(
                DivorceRecord(
                    party1_name=party_name,
                    party2_name=other_party or "Unknown",
                    state=state,
                    county=county,
                    court=f"{county} County Court",
                    source=RecordSource.COUNTY_RECORDS,
                    source_url=court_search_url,
                )
            )

        return results[:limit]

    # =========================================================================
    # Cemetery/Burial Search
    # =========================================================================

    async def search_cemetery_records(
        self,
        name: str,
        cemetery: str = "",
        city: str = "",
        state: str = "",
        limit: int = 50,
    ) -> List[BurialRecord]:
        """
        Search cemetery/burial records.

        Primary source: Find A Grave (free, comprehensive)

        Args:
            name: Deceased person's name
            cemetery: Cemetery name filter
            city: City filter
            state: State filter
            limit: Maximum results

        Returns:
            List of BurialRecord objects
        """
        # Parse name
        name_parts = name.split()
        firstname = name_parts[0] if name_parts else ""
        lastname = (
            name_parts[-1]
            if len(name_parts) > 1
            else name_parts[0] if name_parts else ""
        )

        results = await self.search_find_a_grave(
            firstname=firstname,
            lastname=lastname,
            cemetery_name=cemetery,
            city=city,
            state=state,
            limit=limit,
        )

        # If no results, add BillionGraves search guidance
        if not results:
            billiongraves_url = f"https://billiongraves.com/search?given_names={quote_plus(firstname)}&family_names={quote_plus(lastname)}"
            if state:
                billiongraves_url += f"&state={quote_plus(state)}"

            results.append(
                BurialRecord(
                    name=name,
                    source=RecordSource.BILLIONGRAVES,
                    memorial_url=billiongraves_url,
                    bio_text="Search BillionGraves for additional cemetery records",
                )
            )

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return {
            "request_count": self.request_count,
            "last_request_time": (
                self.last_request_time.isoformat() if self.last_request_time else None
            ),
            "states_configured": len(STATE_VITAL_RECORDS_OFFICES),
            "supported_sources": [s.value for s in RecordSource],
        }


# =============================================================================
# Synchronous Wrappers
# =============================================================================


def get_vital_records_office(state: str) -> Dict[str, Any]:
    """
    Get state vital records office information.

    Synchronous function - no async required.

    Args:
        state: Two-letter state code

    Returns:
        Office contact information
    """
    api = VitalRecordsAPI()
    return api.get_state_vital_records_office(state)


def get_all_vital_records_offices() -> Dict[str, Dict[str, Any]]:
    """Get all state vital records offices."""
    return STATE_VITAL_RECORDS_OFFICES.copy()


def search_death_records_sync(
    lastname: str,
    firstname: str = "",
    birth_year: int = None,
    death_year: int = None,
    state: str = "",
    limit: int = 50,
) -> List[DeathRecord]:
    """
    Search death records synchronously.

    Args:
        lastname: Last name (required)
        firstname: First name
        birth_year: Year of birth
        death_year: Year of death
        state: State filter
        limit: Maximum results

    Returns:
        List of DeathRecord objects
    """
    api = VitalRecordsAPI()

    async def _search():
        try:
            return await api.search_death_records(
                lastname=lastname,
                firstname=firstname,
                birth_year=birth_year,
                death_year=death_year,
                state=state,
                limit=limit,
            )
        finally:
            await api.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def search_burial_records_sync(
    name: str, cemetery: str = "", city: str = "", state: str = "", limit: int = 50
) -> List[BurialRecord]:
    """
    Search burial/cemetery records synchronously.

    Args:
        name: Deceased person's name
        cemetery: Cemetery name filter
        city: City filter
        state: State filter
        limit: Maximum results

    Returns:
        List of BurialRecord objects
    """
    api = VitalRecordsAPI()

    async def _search():
        try:
            return await api.search_cemetery_records(
                name=name, cemetery=cemetery, city=city, state=state, limit=limit
            )
        finally:
            await api.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def search_marriage_records_sync(
    spouse_name: str, other_spouse: str = "", state: str = "", limit: int = 50
) -> List[MarriageRecord]:
    """
    Search marriage records synchronously.

    Args:
        spouse_name: Name of one spouse
        other_spouse: Name of other spouse
        state: State filter
        limit: Maximum results

    Returns:
        List of MarriageRecord objects (guidance records)
    """
    api = VitalRecordsAPI()

    async def _search():
        try:
            return await api.search_marriage_records(
                spouse_name=spouse_name,
                other_spouse=other_spouse,
                state=state,
                limit=limit,
            )
        finally:
            await api.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def get_familysearch_url(
    firstname: str = "",
    lastname: str = "",
    birth_year: int = None,
    death_year: int = None,
    record_type: str = "deaths",
) -> str:
    """
    Get a FamilySearch search URL.

    Synchronous function - generates URL without HTTP request.

    Args:
        firstname: First name
        lastname: Last name
        birth_year: Year of birth
        death_year: Year of death
        record_type: Record type (deaths, marriages, ssdi)

    Returns:
        FamilySearch search URL
    """
    api = VitalRecordsAPI()
    return api.get_familysearch_search_url(
        firstname=firstname,
        lastname=lastname,
        birth_year=birth_year,
        death_year=death_year,
        record_type=record_type,
    )


# =============================================================================
# Legacy Class (for backward compatibility)
# =============================================================================


class VitalRecordsScraper:
    """
    Legacy scraper class for backward compatibility.

    DEPRECATED: Use VitalRecordsAPI instead.
    """

    def __init__(self):
        """Initialize vital records scraper"""
        self._api = VitalRecordsAPI()
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter: Dict[str, datetime] = {}
        self._requests_per_minute = 30
        logger.warning("VitalRecordsScraper is deprecated - use VitalRecordsAPI")

    async def _get_session(self) -> aiohttp.ClientSession:
        return await self._api._get_session()

    async def close(self):
        await self._api.close()

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        return self._api._parse_date(date_str)

    def get_state_vital_records_office(self, state: str) -> Dict[str, Any]:
        return self._api.get_state_vital_records_office(state)

    async def search_death_indices(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        birth_year: Optional[int] = None,
        death_year: Optional[int] = None,
        state: Optional[str] = None,
        limit: int = 50,
    ) -> List[DeathRecord]:
        return await self._api.search_death_records(
            lastname=last_name,
            firstname=first_name or "",
            birth_year=birth_year,
            death_year=death_year,
            state=state or "",
            limit=limit,
        )

    async def search_marriage_indices(
        self,
        spouse_name: str,
        other_spouse: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        state: Optional[str] = None,
        county: Optional[str] = None,
        limit: int = 50,
    ) -> List[MarriageRecord]:
        return await self._api.search_marriage_records(
            spouse_name=spouse_name,
            other_spouse=other_spouse or "",
            year_from=year_from,
            year_to=year_to,
            state=state or "",
            county=county or "",
            limit=limit,
        )

    async def search_divorce_records(
        self,
        party_name: str,
        other_party: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        state: Optional[str] = None,
        county: Optional[str] = None,
        limit: int = 50,
    ) -> List[DivorceRecord]:
        return await self._api.search_divorce_records(
            party_name=party_name,
            other_party=other_party or "",
            year_from=year_from,
            year_to=year_to,
            state=state or "",
            county=county or "",
            limit=limit,
        )

    async def search_cemetery_records(
        self,
        name: str,
        cemetery: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 50,
    ) -> List[BurialRecord]:
        return await self._api.search_cemetery_records(
            name=name,
            cemetery=cemetery or "",
            city=city or "",
            state=state or "",
            limit=limit,
        )
