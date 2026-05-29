"""
Education Records Scraper - Teacher licenses, school data, NCES, college scorecard.

Free Public Sources:
- NCES (National Center for Education Statistics): School/district data
- College Scorecard API: Higher education data
- State teacher license lookup databases
- School report cards
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp


class SchoolLevel(Enum):
    """School level types."""

    ELEMENTARY = "elementary"
    MIDDLE = "middle"
    HIGH = "high"
    COMBINED = "combined"
    PRESCHOOL = "preschool"
    OTHER = "other"


class SchoolType(Enum):
    """School type classifications."""

    PUBLIC = "public"
    PRIVATE = "private"
    CHARTER = "charter"
    MAGNET = "magnet"
    VIRTUAL = "virtual"


class LicenseStatus(Enum):
    """Teacher license status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PENDING = "pending"


@dataclass
class School:
    """Public/private school record."""

    nces_id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    phone: Optional[str] = None
    school_type: Optional[str] = None
    school_level: Optional[str] = None
    district_name: Optional[str] = None
    district_id: Optional[str] = None
    enrollment: Optional[int] = None
    teachers_fte: Optional[float] = None
    student_teacher_ratio: Optional[float] = None
    title_i_eligible: Optional[bool] = None
    magnet: Optional[bool] = None
    charter: Optional[bool] = None
    virtual: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    website: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchoolDistrict:
    """School district record."""

    nces_id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    superintendent: Optional[str] = None
    schools_count: Optional[int] = None
    enrollment: Optional[int] = None
    teachers_fte: Optional[float] = None
    revenue_total: Optional[float] = None
    expenditure_total: Optional[float] = None
    expenditure_per_pupil: Optional[float] = None
    website: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TeacherLicense:
    """Teacher license record."""

    license_number: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    state: Optional[str] = None
    license_type: Optional[str] = None
    subject_areas: List[str] = field(default_factory=list)
    grade_levels: List[str] = field(default_factory=list)
    status: Optional[str] = None
    issue_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    endorsements: List[str] = field(default_factory=list)
    employer: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class College:
    """College/university record from College Scorecard."""

    unit_id: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    url: Optional[str] = None
    ownership: Optional[str] = None  # Public, Private nonprofit, Private for-profit
    highest_degree: Optional[str] = None
    predominant_degree: Optional[str] = None
    undergraduate_enrollment: Optional[int] = None
    admission_rate: Optional[float] = None
    sat_avg: Optional[int] = None
    act_midpoint: Optional[int] = None
    avg_net_price: Optional[float] = None
    tuition_in_state: Optional[float] = None
    tuition_out_state: Optional[float] = None
    completion_rate_4yr: Optional[float] = None
    completion_rate_150pct: Optional[float] = None
    median_earnings_10yr: Optional[float] = None
    default_rate_3yr: Optional[float] = None
    pell_grant_rate: Optional[float] = None
    federal_loan_rate: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


# State teacher license lookup URLs
STATE_TEACHER_LICENSE_URLS = {
    "AL": "https://tcert.alsde.edu/Portal/Public/PublicSearch.aspx",
    "AK": "https://www.eed.alaska.gov/teachercertification/",
    "AZ": "https://azcert.ade.az.gov/",
    "AR": "https://adedata.arkansas.gov/stc/",
    "CA": "https://educator.ctc.ca.gov/",
    "CO": "https://www.cde.state.co.us/cdeprof/licensure_educator_lookup",
    "CT": "https://portal.ct.gov/SDE/Certification/Search-for-Educators",
    "DE": "https://deeds.doe.k12.de.us/",
    "DC": "https://osse.dc.gov/page/educator-credentialing",
    "FL": "https://flcertify.fldoe.org/datamart/",
    "GA": "https://www.gapsc.com/Certification/Lookup.aspx",
    "HI": "https://lisweb.doe.k12.hi.us/tlpp/",
    "ID": "https://apps.sde.idaho.gov/CertLookUp/",
    "IL": "https://www.isbe.net/Pages/Educator-Licensure-Information-System.aspx",
    "IN": "https://license.doe.in.gov/",
    "IA": "https://boee.iowa.gov/license-lookup",
    "KS": "https://svapp15586.ksde.org/TLC/",
    "KY": "https://epsb.ky.gov/mod/data/view.php?d=5",
    "LA": "https://teachlouisiana.ldoe.org/",
    "ME": "https://www.maine.gov/doe/cert/search",
    "MD": "https://mdcertonline.msde.maryland.gov/MSFSearchCert/CertSearch.aspx",
    "MA": "https://www.doe.mass.edu/licensure/search/",
    "MI": "https://mdoe.state.mi.us/MOECS/PublicCredentialSearch.aspx",
    "MN": "https://public.education.mn.gov/PELSB/",
    "MS": "https://www.mdek12.org/OEL/cert_lookup",
    "MO": "https://apps.dese.mo.gov/MCCE/",
    "MT": "https://ebiz.mt.gov/pol/",
    "NE": "https://nce.education.ne.gov/",
    "NV": "https://nvteachers.doe.nv.gov/",
    "NH": "https://my.doe.nh.gov/myNHDOE/Educator/EducatorSearch.aspx",
    "NJ": "https://www.state.nj.us/cgi-bin/education/license/",
    "NM": "https://www.ped.state.nm.us/licensure/",
    "NY": "http://www.highered.nysed.gov/tcert/teach/verify.html",
    "NC": "https://vo.licensure.ncpublicschools.gov/verification/",
    "ND": "https://secure.nd.gov/espb/",
    "OH": "https://ohid.ohio.gov/wps/portal/gov/ohid/search-for-a-license",
    "OK": "https://sde.ok.gov/teacher-certification",
    "OR": "https://secure.tspc.oregon.gov/lookup/",
    "PA": "https://www.pa.gov/guides/become-a-teacher/",
    "RI": "https://www.ride.ri.gov/TeachersAdministrators/EducatorCertification.aspx",
    "SC": "https://ed.sc.gov/educators/certification/",
    "SD": "https://sdsos.gov/general-information/professionalandoccupationalboards/occupational-boards/default.aspx",
    "TN": "https://www.tn.gov/education/licensing.html",
    "TX": "https://secure.sbec.state.tx.us/sbeconline/virtcert.asp",
    "UT": "https://cactus.schools.utah.gov/PersonSearch/Search",
    "VT": "https://alis.vermont.gov/ALISLicenseSearch/advancedsearch",
    "VA": "https://p1pe.doe.virginia.gov/TEACH/LicenseSearch.do",
    "WA": "https://fortress.wa.gov/ospi/apps/CertView/",
    "WV": "https://wvde.us/certification/",
    "WI": "https://dpi.wi.gov/tepdl/licensing",
    "WY": "https://edu.wyoming.gov/for-educators/ptsb/",
}


class EducationRecordsScraper:
    """
    Scraper for education records from NCES, College Scorecard, and state agencies.

    Free Public APIs:
    - NCES EDGE API: https://nces.ed.gov/programs/edge/
    - College Scorecard API: https://collegescorecard.ed.gov/data/
    - State teacher license databases (varies by state)
    """

    # API endpoints
    NCES_API_BASE = "https://nces.ed.gov/api"
    COLLEGE_SCORECARD_BASE = "https://api.data.gov/ed/collegescorecard/v1"
    EDGE_API_BASE = "https://nces.ed.gov/programs/edge"

    def __init__(
        self,
        session: Optional[aiohttp.ClientSession] = None,
        college_scorecard_api_key: Optional[str] = None,
    ):
        """
        Initialize the education records scraper.

        Args:
            session: Optional aiohttp session
            college_scorecard_api_key: Free API key from api.data.gov
        """
        self.session = session
        self._owns_session = session is None
        self.api_key = college_scorecard_api_key or "DEMO_KEY"

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

    # ==================== College Scorecard Methods ====================

    async def search_colleges(
        self,
        name: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        ownership: Optional[
            str
        ] = None,  # "public", "private_nonprofit", "private_for_profit"
        min_enrollment: Optional[int] = None,
        max_enrollment: Optional[int] = None,
        fields: Optional[List[str]] = None,
        limit: int = 20,
        page: int = 0,
    ) -> List[College]:
        """
        Search colleges using College Scorecard API.

        Free API key from api.data.gov - 1000 requests/hour default.
        """
        await self._ensure_session()

        results = []

        # Default fields to retrieve
        default_fields = [
            "id",
            "school.name",
            "school.city",
            "school.state",
            "school.zip",
            "school.school_url",
            "school.ownership",
            "school.degrees_awarded.highest",
            "school.degrees_awarded.predominant",
            "latest.student.size",
            "latest.admissions.admission_rate.overall",
            "latest.admissions.sat_scores.average.overall",
            "latest.admissions.act_scores.midpoint.cumulative",
            "latest.cost.avg_net_price.overall",
            "latest.cost.tuition.in_state",
            "latest.cost.tuition.out_of_state",
            "latest.completion.rate_suppressed.overall",
            "latest.completion.rate_suppressed.lt_four_year_150percent",
            "latest.earnings.10_yrs_after_entry.median",
            "latest.repayment.3_yr_repayment.overall",
            "latest.aid.pell_grant_rate",
            "latest.aid.federal_loan_rate",
            "location.lat",
            "location.lon",
        ]

        try:
            url = f"{self.COLLEGE_SCORECARD_BASE}/schools.json"

            params = {
                "api_key": self.api_key,
                "per_page": limit,
                "page": page,
                "fields": ",".join(fields or default_fields),
            }

            # Add filters
            if name:
                params["school.name"] = name
            if state:
                params["school.state"] = state.upper()
            if city:
                params["school.city"] = city
            if zip_code:
                params["school.zip"] = zip_code
            if ownership:
                ownership_map = {
                    "public": 1,
                    "private_nonprofit": 2,
                    "private_for_profit": 3,
                }
                params["school.ownership"] = ownership_map.get(ownership, ownership)
            if min_enrollment:
                params["latest.student.size__range"] = f"{min_enrollment}.."
            if max_enrollment:
                if "latest.student.size__range" in params:
                    params["latest.student.size__range"] = (
                        f"{min_enrollment}..{max_enrollment}"
                    )
                else:
                    params["latest.student.size__range"] = f"..{max_enrollment}"

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("results", []):
                        try:
                            # Map ownership
                            ownership_map = {
                                1: "Public",
                                2: "Private nonprofit",
                                3: "Private for-profit",
                            }

                            college = College(
                                unit_id=str(item.get("id", "")),
                                name=item.get("school.name", ""),
                                city=item.get("school.city"),
                                state=item.get("school.state"),
                                zip_code=item.get("school.zip"),
                                url=item.get("school.school_url"),
                                ownership=ownership_map.get(
                                    item.get("school.ownership")
                                ),
                                highest_degree=item.get(
                                    "school.degrees_awarded.highest"
                                ),
                                predominant_degree=item.get(
                                    "school.degrees_awarded.predominant"
                                ),
                                undergraduate_enrollment=item.get(
                                    "latest.student.size"
                                ),
                                admission_rate=item.get(
                                    "latest.admissions.admission_rate.overall"
                                ),
                                sat_avg=item.get(
                                    "latest.admissions.sat_scores.average.overall"
                                ),
                                act_midpoint=item.get(
                                    "latest.admissions.act_scores.midpoint.cumulative"
                                ),
                                avg_net_price=item.get(
                                    "latest.cost.avg_net_price.overall"
                                ),
                                tuition_in_state=item.get(
                                    "latest.cost.tuition.in_state"
                                ),
                                tuition_out_state=item.get(
                                    "latest.cost.tuition.out_of_state"
                                ),
                                completion_rate_4yr=item.get(
                                    "latest.completion.rate_suppressed.overall"
                                ),
                                completion_rate_150pct=item.get(
                                    "latest.completion.rate_suppressed.lt_four_year_150percent"
                                ),
                                median_earnings_10yr=item.get(
                                    "latest.earnings.10_yrs_after_entry.median"
                                ),
                                default_rate_3yr=item.get(
                                    "latest.repayment.3_yr_repayment.overall"
                                ),
                                pell_grant_rate=item.get("latest.aid.pell_grant_rate"),
                                federal_loan_rate=item.get(
                                    "latest.aid.federal_loan_rate"
                                ),
                                latitude=item.get("location.lat"),
                                longitude=item.get("location.lon"),
                                raw_data=item,
                            )
                            results.append(college)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    async def get_college_by_id(self, unit_id: str) -> Optional[College]:
        """Get detailed college information by IPEDS Unit ID."""
        await self._ensure_session()

        try:
            url = f"{self.COLLEGE_SCORECARD_BASE}/schools.json"

            params = {"api_key": self.api_key, "id": unit_id, "per_page": 1}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    if results:
                        item = results[0]
                        ownership_map = {
                            1: "Public",
                            2: "Private nonprofit",
                            3: "Private for-profit",
                        }

                        return College(
                            unit_id=str(item.get("id", "")),
                            name=item.get("school.name", ""),
                            city=item.get("school.city"),
                            state=item.get("school.state"),
                            zip_code=item.get("school.zip"),
                            url=item.get("school.school_url"),
                            ownership=ownership_map.get(item.get("school.ownership")),
                            raw_data=item,
                        )

        except aiohttp.ClientError:
            pass

        return None

    # ==================== NCES Methods ====================

    async def search_schools_nces(
        self,
        name: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        district_id: Optional[str] = None,
        school_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[School]:
        """
        Search K-12 schools using NCES data.

        Note: NCES doesn't have a full REST API, but provides downloadable
        data files. This method uses the EDGE geocoder for basic lookups.
        For full data, download from https://nces.ed.gov/ccd/
        """
        await self._ensure_session()

        results = []

        # NCES provides school search through their web interface
        # For programmatic access, we can use EDGE API for geocoded data
        try:
            # EDGE API provides geographic data for schools
            url = "https://nces.ed.gov/programs/edge/graphicservices/rest/services/EDGE_GEOCODE_PUBLICSCH_2122/MapServer/0/query"

            params = {
                "where": "1=1",
                "outFields": "*",
                "f": "json",
                "returnGeometry": "false",
                "resultRecordCount": limit,
            }

            # Build where clause
            where_parts = []
            if state:
                where_parts.append(f"MSTATE='{state.upper()}'")
            if city:
                where_parts.append(f"UPPER(MCITY) LIKE '%{city.upper()}%'")
            if name:
                where_parts.append(f"UPPER(NAME) LIKE '%{name.upper()}%'")
            if district_id:
                where_parts.append(f"LEAID='{district_id}'")

            if where_parts:
                params["where"] = " AND ".join(where_parts)

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for feature in data.get("features", []):
                        attrs = feature.get("attributes", {})
                        try:
                            school = School(
                                nces_id=str(attrs.get("NCESSCH", "")),
                                name=attrs.get("NAME", ""),
                                address=attrs.get("MSTREET1"),
                                city=attrs.get("MCITY"),
                                state=attrs.get("MSTATE"),
                                zip_code=attrs.get("MZIP"),
                                county=attrs.get("NMCNTY"),
                                phone=attrs.get("PHONE"),
                                school_level=attrs.get("LEVEL"),
                                district_name=attrs.get("LEANAME"),
                                district_id=attrs.get("LEAID"),
                                enrollment=attrs.get("ENROLLMENT"),
                                latitude=attrs.get("LAT"),
                                longitude=attrs.get("LON"),
                                raw_data=attrs,
                            )
                            results.append(school)
                        except (KeyError, ValueError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    async def search_districts_nces(
        self, name: Optional[str] = None, state: Optional[str] = None, limit: int = 100
    ) -> List[SchoolDistrict]:
        """Search school districts using NCES EDGE API."""
        await self._ensure_session()

        results = []

        try:
            url = "https://nces.ed.gov/programs/edge/graphicservices/rest/services/EDGE_GEOCODE_PUBLICLEA_2122/MapServer/0/query"

            params = {
                "where": "1=1",
                "outFields": "*",
                "f": "json",
                "returnGeometry": "false",
                "resultRecordCount": limit,
            }

            where_parts = []
            if state:
                where_parts.append(f"MSTATE='{state.upper()}'")
            if name:
                where_parts.append(f"UPPER(NAME) LIKE '%{name.upper()}%'")

            if where_parts:
                params["where"] = " AND ".join(where_parts)

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for feature in data.get("features", []):
                        attrs = feature.get("attributes", {})
                        try:
                            district = SchoolDistrict(
                                nces_id=str(attrs.get("LEAID", "")),
                                name=attrs.get("NAME", ""),
                                address=attrs.get("MSTREET1"),
                                city=attrs.get("MCITY"),
                                state=attrs.get("MSTATE"),
                                zip_code=attrs.get("MZIP"),
                                phone=attrs.get("PHONE"),
                                schools_count=attrs.get("SCHLCOUNT"),
                                enrollment=attrs.get("ENROLLMENT"),
                                raw_data=attrs,
                            )
                            results.append(district)
                        except (KeyError, ValueError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    # ==================== Teacher License Methods ====================

    def get_teacher_license_lookup_url(self, state: str) -> Optional[str]:
        """Get the teacher license lookup URL for a state."""
        return STATE_TEACHER_LICENSE_URLS.get(state.upper())

    def get_all_teacher_license_urls(self) -> Dict[str, str]:
        """Get all state teacher license lookup URLs."""
        return STATE_TEACHER_LICENSE_URLS.copy()

    # ==================== Helper Methods ====================

    def get_nces_data_download_urls(self) -> Dict[str, str]:
        """
        Get URLs for NCES downloadable data files.

        For comprehensive data, download files directly from NCES.
        """
        return {
            "ccd_schools": "https://nces.ed.gov/ccd/files.asp",
            "ccd_districts": "https://nces.ed.gov/ccd/files.asp",
            "private_schools": "https://nces.ed.gov/surveys/pss/pssdata.asp",
            "ipeds_colleges": "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx",
            "school_finances": "https://nces.ed.gov/ccd/f33agency.asp",
        }

    def get_education_resources(self) -> Dict[str, str]:
        """Get useful education data resources."""
        return {
            "nces_main": "https://nces.ed.gov/",
            "college_scorecard": "https://collegescorecard.ed.gov/",
            "school_digger": "https://www.schooldigger.com/",
            "great_schools": "https://www.greatschools.org/",
            "niche": "https://www.niche.com/",
            "public_school_review": "https://www.publicschoolreview.com/",
        }


# Synchronous wrapper functions
def search_colleges_sync(
    name: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    **kwargs,
) -> List[College]:
    """Synchronous wrapper for college search."""

    async def _search():
        async with EducationRecordsScraper() as scraper:
            return await scraper.search_colleges(
                name=name, state=state, city=city, **kwargs
            )

    return asyncio.run(_search())


def search_schools_sync(
    name: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    **kwargs,
) -> List[School]:
    """Synchronous wrapper for K-12 school search."""

    async def _search():
        async with EducationRecordsScraper() as scraper:
            return await scraper.search_schools_nces(
                name=name, state=state, city=city, **kwargs
            )

    return asyncio.run(_search())


def search_districts_sync(
    name: Optional[str] = None, state: Optional[str] = None, **kwargs
) -> List[SchoolDistrict]:
    """Synchronous wrapper for school district search."""

    async def _search():
        async with EducationRecordsScraper() as scraper:
            return await scraper.search_districts_nces(name=name, state=state, **kwargs)

    return asyncio.run(_search())


# Export all
__all__ = [
    "EducationRecordsScraper",
    "School",
    "SchoolDistrict",
    "TeacherLicense",
    "College",
    "SchoolLevel",
    "SchoolType",
    "LicenseStatus",
    "STATE_TEACHER_LICENSE_URLS",
    "search_colleges_sync",
    "search_schools_sync",
    "search_districts_sync",
]
