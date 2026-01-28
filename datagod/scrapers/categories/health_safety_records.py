"""
Health & Safety Records Scraper - Healthcare providers, nursing homes, hospital data.

Free Public Sources:
- CMS (Centers for Medicare & Medicaid Services): Provider data, nursing homes, hospitals
- HHS OIG: Healthcare fraud exclusions (LEIE)
- State health department license lookups
- Hospital Compare, Nursing Home Compare
"""

import logging

import asyncio
import aiohttp
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)



class ProviderType(Enum):
    """Healthcare provider types."""
    PHYSICIAN = "physician"
    NURSE = "nurse"
    PHARMACIST = "pharmacist"
    DENTIST = "dentist"
    THERAPIST = "therapist"
    HOSPITAL = "hospital"
    NURSING_HOME = "nursing_home"
    HOME_HEALTH = "home_health"
    HOSPICE = "hospice"
    OTHER = "other"


class LicenseStatus(Enum):
    """License status types."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PROBATION = "probation"


class StarRating(Enum):
    """CMS star rating levels."""
    ONE_STAR = 1
    TWO_STARS = 2
    THREE_STARS = 3
    FOUR_STARS = 4
    FIVE_STARS = 5


@dataclass
class HealthcareProvider:
    """Healthcare provider record."""
    npi: str  # National Provider Identifier
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    credential: Optional[str] = None
    specialty: Optional[str] = None
    organization_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    enumeration_date: Optional[datetime] = None
    last_update: Optional[datetime] = None
    gender: Optional[str] = None
    sole_proprietor: Optional[bool] = None
    entity_type: Optional[str] = None  # Individual or Organization
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NursingHome:
    """Nursing home facility record."""
    provider_number: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    county: Optional[str] = None
    ownership_type: Optional[str] = None
    certified_beds: Optional[int] = None
    total_residents: Optional[int] = None
    overall_rating: Optional[int] = None
    health_inspection_rating: Optional[int] = None
    staffing_rating: Optional[int] = None
    quality_rating: Optional[int] = None
    total_penalties: float = 0.0
    total_fines: float = 0.0
    abuse_icon: Optional[bool] = None
    in_ccrc: Optional[bool] = None
    special_focus: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Hospital:
    """Hospital facility record."""
    provider_id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    county: Optional[str] = None
    hospital_type: Optional[str] = None
    ownership: Optional[str] = None
    emergency_services: Optional[bool] = None
    overall_rating: Optional[int] = None
    mortality_rating: Optional[str] = None
    safety_rating: Optional[str] = None
    readmission_rating: Optional[str] = None
    patient_experience_rating: Optional[str] = None
    effectiveness_rating: Optional[str] = None
    timeliness_rating: Optional[str] = None
    efficient_imaging: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExcludedProvider:
    """HHS OIG excluded provider record (LEIE)."""
    npi: Optional[str] = None
    upin: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    business_name: Optional[str] = None
    general_category: Optional[str] = None
    specialty: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    exclusion_type: Optional[str] = None
    exclusion_date: Optional[datetime] = None
    reinstate_date: Optional[datetime] = None
    waiver_date: Optional[datetime] = None
    waiver_state: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HomeHealthAgency:
    """Home health agency record."""
    provider_number: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    county: Optional[str] = None
    ownership_type: Optional[str] = None
    offers_nursing: Optional[bool] = None
    offers_physical_therapy: Optional[bool] = None
    offers_occupational_therapy: Optional[bool] = None
    offers_speech_therapy: Optional[bool] = None
    offers_medical_social: Optional[bool] = None
    offers_home_health_aide: Optional[bool] = None
    quality_of_care_rating: Optional[int] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


# State health license lookup URLs
STATE_HEALTH_LICENSE_URLS = {
    "AL": {
        "medical": "https://www.albme.gov/verification/",
        "nursing": "https://www.abn.alabama.gov/verification/",
        "pharmacy": "https://www.albop.com/"
    },
    "AK": {
        "medical": "https://www.commerce.alaska.gov/cbp/Main/",
        "nursing": "https://www.commerce.alaska.gov/cbp/Main/"
    },
    "AZ": {
        "medical": "https://azbomprod.azmd.gov/GLSPublic/",
        "nursing": "https://www.azbn.gov/verification-of-licensure",
        "pharmacy": "https://pharmacy.az.gov/"
    },
    "AR": {
        "medical": "https://www.armedicalboard.org/",
        "nursing": "https://www.arsbn.org/"
    },
    "CA": {
        "medical": "https://www.mbc.ca.gov/breeze/",
        "nursing": "https://www.rn.ca.gov/verification.shtml",
        "pharmacy": "https://www.pharmacy.ca.gov/"
    },
    "CO": {
        "all": "https://apps.colorado.gov/dora/licensing/lookup/licenselookup.aspx"
    },
    "CT": {
        "all": "https://www.elicense.ct.gov/Lookup/LicenseLookup.aspx"
    },
    "DE": {
        "all": "https://delpros.delaware.gov/OH_Verification/"
    },
    "DC": {
        "all": "https://doh.dc.gov/service/professional-licensing-verification"
    },
    "FL": {
        "medical": "https://appsmqa.doh.state.fl.us/MQASearchServices/",
        "nursing": "https://appsmqa.doh.state.fl.us/MQASearchServices/",
        "pharmacy": "https://appsmqa.doh.state.fl.us/MQASearchServices/"
    },
    "GA": {
        "medical": "https://gcmb.mylicense.com/verification/",
        "nursing": "https://sos.ga.gov/PLB/verify.php"
    },
    "HI": {
        "all": "https://pvl.ehawaii.gov/pvlsearch/"
    },
    "ID": {
        "medical": "https://isecure.bom.idaho.gov/IBOMPortal/",
        "nursing": "https://ibn.idaho.gov/"
    },
    "IL": {
        "all": "https://online-dfpr.micropact.com/lookup/licenselookup.aspx"
    },
    "IN": {
        "all": "https://mylicense.in.gov/EVerification/"
    },
    "IA": {
        "medical": "https://medicalboard.iowa.gov/",
        "nursing": "https://nursing.iowa.gov/"
    },
    "KS": {
        "medical": "https://www.ksbha.org/public_searchable_database.shtml",
        "nursing": "https://www.ksbn.org/"
    },
    "KY": {
        "medical": "https://web1.ky.gov/GenSearch/",
        "nursing": "https://kbn.ky.gov/"
    },
    "LA": {
        "medical": "https://www.lsbme.la.gov/content/verification",
        "nursing": "https://www.lsbn.state.la.us/"
    },
    "ME": {
        "all": "https://www.pfr.maine.gov/ALMSOnline/"
    },
    "MD": {
        "medical": "https://www.mbp.state.md.us/bpqapp/",
        "nursing": "https://mbon.maryland.gov/"
    },
    "MA": {
        "all": "https://checkalicense.mass.gov/"
    },
    "MI": {
        "all": "https://www.michigan.gov/lara/bureau-list/bpl/health/verify"
    },
    "MN": {
        "medical": "https://www.bmp.state.mn.us/",
        "nursing": "https://www.nursingboard.state.mn.us/"
    },
    "MS": {
        "medical": "https://www.msbml.ms.gov/",
        "nursing": "https://www.msbn.ms.gov/"
    },
    "MO": {
        "all": "https://pr.mo.gov/licensee-search.asp"
    },
    "MT": {
        "all": "https://ebiz.mt.gov/pol/"
    },
    "NE": {
        "all": "https://www.nebraska.gov/LISSearch/search.cgi"
    },
    "NV": {
        "medical": "https://medboard.nv.gov/",
        "nursing": "https://nevadanursingboard.org/"
    },
    "NH": {
        "all": "https://nhlicenses.nh.gov/"
    },
    "NJ": {
        "all": "https://newjersey.mylicense.com/verification/"
    },
    "NM": {
        "medical": "https://www.nmmb.state.nm.us/",
        "nursing": "https://www.bon.state.nm.us/"
    },
    "NY": {
        "all": "https://www.op.nysed.gov/verification-search"
    },
    "NC": {
        "medical": "https://www.ncmedboard.org/",
        "nursing": "https://www.ncbon.com/"
    },
    "ND": {
        "medical": "https://www.ndbomex.com/",
        "nursing": "https://www.ndbon.org/"
    },
    "OH": {
        "medical": "https://elicense.ohio.gov/oh_verifylicense",
        "nursing": "https://elicense.ohio.gov/oh_verifylicense"
    },
    "OK": {
        "medical": "https://www.okmedicalboard.org/",
        "nursing": "https://nursing.ok.gov/"
    },
    "OR": {
        "medical": "https://www.oregon.gov/omb/",
        "nursing": "https://www.oregon.gov/osbn/"
    },
    "PA": {
        "all": "https://www.pals.pa.gov/"
    },
    "RI": {
        "all": "https://health.ri.gov/licenses/"
    },
    "SC": {
        "medical": "https://llr.sc.gov/med/",
        "nursing": "https://llr.sc.gov/nurse/"
    },
    "SD": {
        "medical": "https://www.sdbmoe.gov/",
        "nursing": "https://doh.sd.gov/boards/nursing/"
    },
    "TN": {
        "all": "https://apps.health.tn.gov/licensure/default.aspx"
    },
    "TX": {
        "medical": "https://www.tmb.state.tx.us/",
        "nursing": "https://www.bon.texas.gov/"
    },
    "UT": {
        "all": "https://dopl.utah.gov/verify.html"
    },
    "VT": {
        "all": "https://alis.vermont.gov/ALISLicenseSearch/"
    },
    "VA": {
        "all": "https://dhp.virginiainteractive.org/"
    },
    "WA": {
        "all": "https://fortress.wa.gov/doh/providercredentialsearch/"
    },
    "WV": {
        "medical": "https://www.wvbom.wv.gov/",
        "nursing": "https://www.wvrnboard.wv.gov/"
    },
    "WI": {
        "all": "https://licensesearch.wi.gov/"
    },
    "WY": {
        "medical": "https://wyomedboard.wyo.gov/",
        "nursing": "https://wsbn.wyo.gov/"
    }
}


class HealthSafetyRecordsScraper:
    """
    Scraper for health and safety records from CMS, HHS OIG, and state agencies.

    Free Public APIs:
    - NPPES NPI Registry: https://npiregistry.cms.hhs.gov/
    - CMS Provider Data: https://data.cms.gov/
    - HHS OIG LEIE: https://oig.hhs.gov/exclusions/
    - Hospital Compare / Nursing Home Compare data files
    """

    # Federal API endpoints
    NPPES_API = "https://npiregistry.cms.hhs.gov/api/"
    CMS_DATA_API = "https://data.cms.gov/provider-data/api/1"
    LEIE_DATA_URL = "https://oig.hhs.gov/exclusions/exclusions_list.asp"

    # CMS Data Catalog datasets
    CMS_DATASETS = {
        "nursing_homes": "https://data.cms.gov/provider-data/dataset/4pq5-n9py",
        "hospitals": "https://data.cms.gov/provider-data/dataset/xubh-q36u",
        "home_health": "https://data.cms.gov/provider-data/dataset/6jpm-sxkc",
        "hospice": "https://data.cms.gov/provider-data/dataset/252m-zfp9",
        "physicians": "https://data.cms.gov/provider-data/dataset/mj5m-pzi6"
    }

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the health safety records scraper."""
        self.session = session
        self._owns_session = session is None

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

    # ==================== NPPES NPI Registry Methods ====================

    async def search_providers_npi(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        organization_name: Optional[str] = None,
        npi: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        specialty: Optional[str] = None,
        limit: int = 100
    ) -> List[HealthcareProvider]:
        """
        Search healthcare providers in NPPES NPI Registry.

        Free API - no registration required.
        Rate limit: Not strictly enforced but be reasonable.
        """
        await self._ensure_session()

        results = []

        try:
            params = {"version": "2.1", "limit": limit}

            if npi:
                params["number"] = npi
            if first_name:
                params["first_name"] = first_name
            if last_name:
                params["last_name"] = last_name
            if organization_name:
                params["organization_name"] = organization_name
            if city:
                params["city"] = city
            if state:
                params["state"] = state.upper()
            if zip_code:
                params["postal_code"] = zip_code
            if specialty:
                params["taxonomy_description"] = specialty

            async with self.session.get(self.NPPES_API, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("results", []):
                        try:
                            basic = item.get("basic", {})
                            addresses = item.get("addresses", [])
                            taxonomies = item.get("taxonomies", [])

                            # Get primary address
                            primary_addr = next(
                                (a for a in addresses if a.get("address_purpose") == "LOCATION"),
                                addresses[0] if addresses else {}
                            )

                            # Get primary taxonomy/specialty
                            primary_tax = next(
                                (t for t in taxonomies if t.get("primary")),
                                taxonomies[0] if taxonomies else {}
                            )

                            entity_type = "Individual" if item.get("enumeration_type") == "NPI-1" else "Organization"

                            provider = HealthcareProvider(
                                npi=str(item.get("number", "")),
                                name=basic.get("name") or f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip(),
                                first_name=basic.get("first_name"),
                                last_name=basic.get("last_name"),
                                credential=basic.get("credential"),
                                organization_name=basic.get("organization_name"),
                                specialty=primary_tax.get("desc"),
                                address=primary_addr.get("address_1"),
                                city=primary_addr.get("city"),
                                state=primary_addr.get("state"),
                                zip_code=primary_addr.get("postal_code"),
                                phone=primary_addr.get("telephone_number"),
                                gender=basic.get("gender"),
                                sole_proprietor=basic.get("sole_proprietor") == "YES",
                                entity_type=entity_type,
                                raw_data=item
                            )

                            # Parse dates
                            if basic.get("enumeration_date"):
                                try:
                                    provider.enumeration_date = datetime.strptime(
                                        basic["enumeration_date"], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            if basic.get("last_updated"):
                                try:
                                    provider.last_update = datetime.strptime(
                                        basic["last_updated"], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            results.append(provider)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError as e:
            logger.error(f"NPPES API error in search_providers_npi: {e}")


        return results

    async def get_provider_by_npi(self, npi: str) -> Optional[HealthcareProvider]:
        """Get a specific provider by NPI number."""
        providers = await self.search_providers_npi(npi=npi, limit=1)
        return providers[0] if providers else None

    # ==================== CMS Provider Data Methods ====================

    async def search_nursing_homes(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        min_rating: Optional[int] = None,
        limit: int = 100
    ) -> List[NursingHome]:
        """
        Search nursing homes using CMS Nursing Home Compare data.

        Data source: https://data.cms.gov/provider-data/dataset/4pq5-n9py
        """
        await self._ensure_session()

        results = []

        try:
            # CMS Provider Data API
            url = "https://data.cms.gov/provider-data/api/1/datastore/query/4pq5-n9py/0"

            conditions = []
            if state:
                conditions.append({"resource": "t", "property": "state", "value": state.upper(), "operator": "="})
            if city:
                conditions.append({"resource": "t", "property": "city", "value": city.upper(), "operator": "="})
            if min_rating:
                conditions.append({"resource": "t", "property": "overall_rating", "value": str(min_rating), "operator": ">="})

            payload = {
                "limit": limit,
                "offset": 0,
                "count": True
            }

            if conditions:
                payload["conditions"] = conditions

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("results", []):
                        if name and name.lower() not in item.get("provider_name", "").lower():
                            continue

                        try:
                            nursing_home = NursingHome(
                                provider_number=str(item.get("federal_provider_number", "")),
                                name=item.get("provider_name", ""),
                                address=item.get("provider_address"),
                                city=item.get("city"),
                                state=item.get("state"),
                                zip_code=item.get("provider_zip_code"),
                                phone=item.get("provider_phone_number"),
                                county=item.get("provider_county_name"),
                                ownership_type=item.get("ownership_type"),
                                certified_beds=int(item.get("number_of_certified_beds", 0) or 0),
                                total_residents=int(item.get("average_number_of_residents_per_day", 0) or 0),
                                overall_rating=int(item.get("overall_rating", 0) or 0) if item.get("overall_rating") else None,
                                health_inspection_rating=int(item.get("health_inspection_rating", 0) or 0) if item.get("health_inspection_rating") else None,
                                staffing_rating=int(item.get("staffing_rating", 0) or 0) if item.get("staffing_rating") else None,
                                quality_rating=int(item.get("qm_rating", 0) or 0) if item.get("qm_rating") else None,
                                abuse_icon=item.get("abuse_icon") == "Y",
                                special_focus=item.get("special_focus_facility") == "Y",
                                raw_data=item
                            )
                            results.append(nursing_home)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError as e:
            logger.error(f"CMS Data API error in search_nursing_homes: {e}")


        return results

    async def search_hospitals(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        hospital_type: Optional[str] = None,
        min_rating: Optional[int] = None,
        limit: int = 100
    ) -> List[Hospital]:
        """
        Search hospitals using CMS Hospital Compare data.

        Data source: https://data.cms.gov/provider-data/dataset/xubh-q36u
        """
        await self._ensure_session()

        results = []

        try:
            url = "https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0"

            conditions = []
            if state:
                conditions.append({"resource": "t", "property": "state", "value": state.upper(), "operator": "="})
            if city:
                conditions.append({"resource": "t", "property": "city", "value": city.upper(), "operator": "="})

            payload = {
                "limit": limit,
                "offset": 0,
                "count": True
            }

            if conditions:
                payload["conditions"] = conditions

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("results", []):
                        if name and name.lower() not in item.get("facility_name", "").lower():
                            continue
                        if hospital_type and hospital_type.lower() not in item.get("hospital_type", "").lower():
                            continue
                        if min_rating and (int(item.get("hospital_overall_rating", 0) or 0) < min_rating):
                            continue

                        try:
                            hospital = Hospital(
                                provider_id=str(item.get("facility_id", "")),
                                name=item.get("facility_name", ""),
                                address=item.get("address"),
                                city=item.get("city"),
                                state=item.get("state"),
                                zip_code=item.get("zip_code"),
                                phone=item.get("phone_number"),
                                county=item.get("county_name"),
                                hospital_type=item.get("hospital_type"),
                                ownership=item.get("hospital_ownership"),
                                emergency_services=item.get("emergency_services") == "Yes",
                                overall_rating=int(item.get("hospital_overall_rating", 0) or 0) if item.get("hospital_overall_rating") else None,
                                mortality_rating=item.get("mortality_national_comparison"),
                                safety_rating=item.get("safety_of_care_national_comparison"),
                                readmission_rating=item.get("readmission_national_comparison"),
                                patient_experience_rating=item.get("patient_experience_national_comparison"),
                                effectiveness_rating=item.get("effectiveness_of_care_national_comparison"),
                                timeliness_rating=item.get("timeliness_of_care_national_comparison"),
                                efficient_imaging=item.get("efficient_use_of_medical_imaging_national_comparison"),
                                raw_data=item
                            )
                            results.append(hospital)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError as e:
            logger.error(f"CMS Data API error in search_hospitals: {e}")


        return results

    # ==================== State License Methods ====================

    def get_state_health_license_urls(self, state: str) -> Optional[Dict[str, str]]:
        """Get health license lookup URLs for a state."""
        return STATE_HEALTH_LICENSE_URLS.get(state.upper())

    def get_all_health_license_urls(self) -> Dict[str, Dict[str, str]]:
        """Get all state health license lookup URLs."""
        return STATE_HEALTH_LICENSE_URLS.copy()

    # ==================== Helper Methods ====================

    def get_cms_data_resources(self) -> Dict[str, str]:
        """Get useful CMS data resources."""
        return {
            "cms_data_portal": "https://data.cms.gov/",
            "hospital_compare": "https://www.medicare.gov/care-compare/",
            "nursing_home_compare": "https://www.medicare.gov/care-compare/",
            "physician_compare": "https://www.medicare.gov/care-compare/",
            "leie_exclusions": "https://oig.hhs.gov/exclusions/",
            "nppes_registry": "https://npiregistry.cms.hhs.gov/"
        }

    def get_data_download_urls(self) -> Dict[str, str]:
        """Get URLs for bulk data downloads."""
        return {
            "nursing_home_data": "https://data.cms.gov/provider-data/dataset/4pq5-n9py",
            "hospital_data": "https://data.cms.gov/provider-data/dataset/xubh-q36u",
            "physician_data": "https://data.cms.gov/provider-data/dataset/mj5m-pzi6",
            "home_health_data": "https://data.cms.gov/provider-data/dataset/6jpm-sxkc",
            "hospice_data": "https://data.cms.gov/provider-data/dataset/252m-zfp9",
            "leie_exclusions": "https://oig.hhs.gov/exclusions/exclusions_list.asp"
        }


# Synchronous wrapper functions
def search_providers_sync(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    state: Optional[str] = None,
    **kwargs
) -> List[HealthcareProvider]:
    """Synchronous wrapper for provider search."""
    async def _search():
        async with HealthSafetyRecordsScraper() as scraper:
            return await scraper.search_providers_npi(
                first_name=first_name,
                last_name=last_name,
                state=state,
                **kwargs
            )
    return asyncio.run(_search())


def search_nursing_homes_sync(
    name: Optional[str] = None,
    state: Optional[str] = None,
    **kwargs
) -> List[NursingHome]:
    """Synchronous wrapper for nursing home search."""
    async def _search():
        async with HealthSafetyRecordsScraper() as scraper:
            return await scraper.search_nursing_homes(
                name=name,
                state=state,
                **kwargs
            )
    return asyncio.run(_search())


def search_hospitals_sync(
    name: Optional[str] = None,
    state: Optional[str] = None,
    **kwargs
) -> List[Hospital]:
    """Synchronous wrapper for hospital search."""
    async def _search():
        async with HealthSafetyRecordsScraper() as scraper:
            return await scraper.search_hospitals(
                name=name,
                state=state,
                **kwargs
            )
    return asyncio.run(_search())


# Export all
__all__ = [
    "HealthSafetyRecordsScraper",
    "HealthcareProvider",
    "NursingHome",
    "Hospital",
    "ExcludedProvider",
    "HomeHealthAgency",
    "ProviderType",
    "LicenseStatus",
    "StarRating",
    "STATE_HEALTH_LICENSE_URLS",
    "search_providers_sync",
    "search_nursing_homes_sync",
    "search_hospitals_sync",
]
