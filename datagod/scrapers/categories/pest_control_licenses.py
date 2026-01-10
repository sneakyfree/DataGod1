"""
Pest Control Licenses Scraper

This module provides scrapers for pest control operator and applicator
license records from state agriculture and regulatory departments.

Data sources:
- State Department of Agriculture
- State Structural Pest Control Boards
- EPA Certified Pesticide Applicators
- State Pesticide Regulatory Programs

Includes:
- Pest Control Operators (PCO)
- Pesticide Applicators
- Certified Applicators (Commercial/Private)
- Termite Operators
- Fumigators
- Wood Destroying Organism (WDO) Inspectors
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, Dict, Any, List
import aiohttp


class LicenseType(Enum):
    """Types of pest control licenses"""
    OPERATOR = "pest_control_operator"
    APPLICATOR = "pesticide_applicator"
    CERTIFIED_COMMERCIAL = "certified_commercial_applicator"
    CERTIFIED_PRIVATE = "certified_private_applicator"
    TECHNICIAN = "pest_control_technician"
    FUMIGATOR = "fumigator"
    TERMITE_OPERATOR = "termite_operator"
    WDO_INSPECTOR = "wood_destroying_organism_inspector"
    STRUCTURAL = "structural_pest_control"
    AGRICULTURAL = "agricultural_pest_control"
    LAWN_ORNAMENTAL = "lawn_ornamental"
    MOSQUITO_CONTROL = "mosquito_control"
    WILDLIFE_CONTROL = "wildlife_damage_control"
    REGISTERED_TECHNICIAN = "registered_technician"


class LicenseStatus(Enum):
    """License status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PENDING = "pending"
    INACTIVE = "inactive"
    PROBATION = "probation"


class CategoryType(Enum):
    """Pest control category certifications"""
    GENERAL = "general_pest"
    TERMITE = "termite_subterranean"
    DRYWOOD_TERMITE = "drywood_termite"
    FUMIGATION = "fumigation"
    RODENT = "rodent_control"
    ORNAMENTAL_TURF = "ornamental_turf"
    AGRICULTURAL_PLANT = "agricultural_plant"
    RIGHT_OF_WAY = "right_of_way"
    AQUATIC = "aquatic_pest"
    FOREST = "forest_pest"
    PUBLIC_HEALTH = "public_health"
    REGULATORY = "regulatory_pest"
    SEED_TREATMENT = "seed_treatment"
    AERIAL = "aerial_application"
    DEMONSTRATION_RESEARCH = "demonstration_research"
    WOOD_PRESERVATIVE = "wood_preservative"


@dataclass
class PestControlLicense:
    """Pest control license record"""
    license_number: str
    license_type: LicenseType
    status: LicenseStatus
    state: str
    holder_name: str
    holder_type: str  # individual or company
    company_name: Optional[str] = None
    dba_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    issue_date: Optional[date] = None
    expiration_date: Optional[date] = None
    categories: List[CategoryType] = field(default_factory=list)
    category_descriptions: List[str] = field(default_factory=list)
    insurance_on_file: bool = False
    bond_on_file: bool = False
    epa_certification: Optional[str] = None
    continuing_education_due: Optional[date] = None
    data_source: str = "State Agriculture/Pest Control Board"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "license_number": self.license_number,
            "license_type": self.license_type.value,
            "status": self.status.value,
            "state": self.state,
            "holder_name": self.holder_name,
            "holder_type": self.holder_type,
            "company_name": self.company_name,
            "dba_name": self.dba_name,
            "address": self.address,
            "city": self.city,
            "zip_code": self.zip_code,
            "phone": self.phone,
            "email": self.email,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "categories": [c.value for c in self.categories],
            "category_descriptions": self.category_descriptions,
            "insurance_on_file": self.insurance_on_file,
            "bond_on_file": self.bond_on_file,
            "epa_certification": self.epa_certification,
            "continuing_education_due": self.continuing_education_due.isoformat() if self.continuing_education_due else None,
            "data_source": self.data_source,
        }


@dataclass
class DisciplinaryAction:
    """Disciplinary action against a license holder"""
    action_id: str
    license_number: str
    action_date: date
    action_type: str
    description: str
    violation_type: Optional[str] = None
    fine_amount: Optional[float] = None
    suspension_days: Optional[int] = None
    probation_months: Optional[int] = None
    resolved: bool = False
    resolution_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "license_number": self.license_number,
            "action_date": self.action_date.isoformat(),
            "action_type": self.action_type,
            "description": self.description,
            "violation_type": self.violation_type,
            "fine_amount": self.fine_amount,
            "suspension_days": self.suspension_days,
            "probation_months": self.probation_months,
            "resolved": self.resolved,
            "resolution_date": self.resolution_date.isoformat() if self.resolution_date else None,
        }


@dataclass
class PestControlCompany:
    """Pest control company information"""
    company_id: str
    company_name: str
    dba_name: Optional[str] = None
    state: str = ""
    license_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    owner_name: Optional[str] = None
    qualifying_manager: Optional[str] = None
    services_offered: List[str] = field(default_factory=list)
    service_areas: List[str] = field(default_factory=list)
    insurance_carrier: Optional[str] = None
    bond_amount: Optional[float] = None
    years_in_business: Optional[int] = None
    employees_count: Optional[int] = None
    status: LicenseStatus = LicenseStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "dba_name": self.dba_name,
            "state": self.state,
            "license_number": self.license_number,
            "address": self.address,
            "city": self.city,
            "zip_code": self.zip_code,
            "phone": self.phone,
            "website": self.website,
            "owner_name": self.owner_name,
            "qualifying_manager": self.qualifying_manager,
            "services_offered": self.services_offered,
            "service_areas": self.service_areas,
            "insurance_carrier": self.insurance_carrier,
            "bond_amount": self.bond_amount,
            "years_in_business": self.years_in_business,
            "employees_count": self.employees_count,
            "status": self.status.value,
        }


# State pest control licensing agencies
STATE_PEST_CONTROL_AGENCIES: Dict[str, Dict[str, str]] = {
    "AL": {
        "agency": "Alabama Department of Agriculture and Industries",
        "division": "Pesticide Management Section",
        "website": "https://agi.alabama.gov/pesticide-management/",
        "phone": "334-240-7223",
    },
    "AK": {
        "agency": "Alaska Department of Environmental Conservation",
        "division": "Pesticide Control Program",
        "website": "https://dec.alaska.gov/eh/pest/",
        "phone": "907-269-7644",
    },
    "AZ": {
        "agency": "Arizona Department of Agriculture",
        "division": "Environmental Services Division",
        "website": "https://agriculture.az.gov/pesticides-pest-control",
        "phone": "602-542-3578",
    },
    "AR": {
        "agency": "Arkansas State Plant Board",
        "division": "Pesticide Division",
        "website": "https://www.aad.arkansas.gov/arkansas-state-plant-board",
        "phone": "501-225-1598",
    },
    "CA": {
        "agency": "California Structural Pest Control Board",
        "division": "Department of Pesticide Regulation",
        "website": "https://www.pestboard.ca.gov/",
        "phone": "916-561-8700",
    },
    "CO": {
        "agency": "Colorado Department of Agriculture",
        "division": "Division of Plant Industry",
        "website": "https://ag.colorado.gov/plants/pesticides",
        "phone": "303-869-9050",
    },
    "CT": {
        "agency": "Connecticut Department of Energy and Environmental Protection",
        "division": "Pesticide Management Program",
        "website": "https://portal.ct.gov/DEEP/Pesticides/Pesticides",
        "phone": "860-424-3369",
    },
    "DE": {
        "agency": "Delaware Department of Agriculture",
        "division": "Pesticide Section",
        "website": "https://agriculture.delaware.gov/pesticide-management/",
        "phone": "302-698-4500",
    },
    "FL": {
        "agency": "Florida Department of Agriculture and Consumer Services",
        "division": "Division of Agricultural Environmental Services",
        "website": "https://www.fdacs.gov/Business-Services/Pest-Control",
        "phone": "850-617-7997",
    },
    "GA": {
        "agency": "Georgia Department of Agriculture",
        "division": "Structural Pest Control Commission",
        "website": "https://agr.georgia.gov/structural-pest-control",
        "phone": "404-656-3641",
    },
    "HI": {
        "agency": "Hawaii Department of Agriculture",
        "division": "Pesticides Branch",
        "website": "https://hdoa.hawaii.gov/pi/pest/",
        "phone": "808-973-9401",
    },
    "ID": {
        "agency": "Idaho State Department of Agriculture",
        "division": "Division of Agricultural Resources",
        "website": "https://agri.idaho.gov/main/plants/pesticides/",
        "phone": "208-332-8610",
    },
    "IL": {
        "agency": "Illinois Department of Agriculture",
        "division": "Bureau of Environmental Programs",
        "website": "https://www2.illinois.gov/sites/agr/Pesticides/",
        "phone": "217-785-2427",
    },
    "IN": {
        "agency": "Indiana State Chemist",
        "division": "Office of Indiana State Chemist",
        "website": "https://www.oisc.purdue.edu/pesticide/",
        "phone": "765-494-1492",
    },
    "IA": {
        "agency": "Iowa Department of Agriculture and Land Stewardship",
        "division": "Pesticide Bureau",
        "website": "https://iowaagriculture.gov/pesticide",
        "phone": "515-281-8591",
    },
    "KS": {
        "agency": "Kansas Department of Agriculture",
        "division": "Pesticide and Fertilizer Program",
        "website": "https://agriculture.ks.gov/divisions-programs/pesticide-fertilizer",
        "phone": "785-564-6688",
    },
    "KY": {
        "agency": "Kentucky Department of Agriculture",
        "division": "Pesticide Regulatory Branch",
        "website": "https://www.kyagr.com/enviro/pesticides-app.html",
        "phone": "502-573-0282",
    },
    "LA": {
        "agency": "Louisiana Department of Agriculture and Forestry",
        "division": "Structural Pest Control Commission",
        "website": "https://www.ldaf.state.la.us/pesticide/",
        "phone": "225-925-3763",
    },
    "ME": {
        "agency": "Maine Board of Pesticides Control",
        "division": "Department of Agriculture, Conservation and Forestry",
        "website": "https://www.maine.gov/dacf/php/pesticides/",
        "phone": "207-287-2731",
    },
    "MD": {
        "agency": "Maryland Department of Agriculture",
        "division": "Pesticide Regulation Section",
        "website": "https://mda.maryland.gov/plants-pests/Pages/pesticide_regulation.aspx",
        "phone": "410-841-5710",
    },
    "MA": {
        "agency": "Massachusetts Department of Agricultural Resources",
        "division": "Pesticide Program",
        "website": "https://www.mass.gov/pesticide-program",
        "phone": "617-626-1700",
    },
    "MI": {
        "agency": "Michigan Department of Agriculture and Rural Development",
        "division": "Pesticide and Plant Pest Management Division",
        "website": "https://www.michigan.gov/mdard/environment/pesticides",
        "phone": "517-284-5644",
    },
    "MN": {
        "agency": "Minnesota Department of Agriculture",
        "division": "Pesticide and Fertilizer Management Division",
        "website": "https://www.mda.state.mn.us/pesticide-fertilizer",
        "phone": "651-201-6121",
    },
    "MS": {
        "agency": "Mississippi Department of Agriculture and Commerce",
        "division": "Bureau of Plant Industry",
        "website": "https://www.mdac.ms.gov/bureaus-departments/bureau-of-plant-industry/",
        "phone": "662-325-3390",
    },
    "MO": {
        "agency": "Missouri Department of Agriculture",
        "division": "Bureau of Pesticide Control",
        "website": "https://agriculture.mo.gov/plants/pesticides/",
        "phone": "573-751-5504",
    },
    "MT": {
        "agency": "Montana Department of Agriculture",
        "division": "Agricultural Sciences Division",
        "website": "https://agr.mt.gov/Pesticides",
        "phone": "406-444-5400",
    },
    "NE": {
        "agency": "Nebraska Department of Agriculture",
        "division": "Pesticide Program",
        "website": "https://nda.nebraska.gov/pesticide/index.html",
        "phone": "402-471-2394",
    },
    "NV": {
        "agency": "Nevada Department of Agriculture",
        "division": "Plant Industry Division",
        "website": "https://agri.nv.gov/Plant/Pesticides/Pesticides_Main/",
        "phone": "775-353-3600",
    },
    "NH": {
        "agency": "New Hampshire Division of Pesticide Control",
        "division": "Department of Agriculture, Markets and Food",
        "website": "https://www.agriculture.nh.gov/divisions/pesticide-control/",
        "phone": "603-271-3550",
    },
    "NJ": {
        "agency": "New Jersey Department of Environmental Protection",
        "division": "Pesticide Control Program",
        "website": "https://www.nj.gov/dep/enforcement/pcp/",
        "phone": "609-984-6507",
    },
    "NM": {
        "agency": "New Mexico Department of Agriculture",
        "division": "Pesticide Compliance",
        "website": "https://www.nmda.nmsu.edu/pesticides/",
        "phone": "575-646-2133",
    },
    "NY": {
        "agency": "New York State Department of Environmental Conservation",
        "division": "Bureau of Pesticides Management",
        "website": "https://www.dec.ny.gov/chemical/298.html",
        "phone": "518-402-8748",
    },
    "NC": {
        "agency": "North Carolina Department of Agriculture and Consumer Services",
        "division": "Structural Pest Control and Pesticides Division",
        "website": "https://www.ncagr.gov/SPCAP/structural/",
        "phone": "919-733-6100",
    },
    "ND": {
        "agency": "North Dakota Department of Agriculture",
        "division": "Pesticide Division",
        "website": "https://www.nd.gov/ndda/program/pesticide-program",
        "phone": "701-328-2231",
    },
    "OH": {
        "agency": "Ohio Department of Agriculture",
        "division": "Pesticide Regulation",
        "website": "https://agri.ohio.gov/divisions/plant-health/pesticides",
        "phone": "614-728-6200",
    },
    "OK": {
        "agency": "Oklahoma Department of Agriculture, Food and Forestry",
        "division": "Consumer Protection Services",
        "website": "https://ag.ok.gov/divisions/consumer-protection-services/pesticides/",
        "phone": "405-522-5966",
    },
    "OR": {
        "agency": "Oregon Department of Agriculture",
        "division": "Pesticides Program",
        "website": "https://www.oregon.gov/oda/programs/pesticides/",
        "phone": "503-986-4635",
    },
    "PA": {
        "agency": "Pennsylvania Department of Agriculture",
        "division": "Bureau of Plant Industry",
        "website": "https://www.agriculture.pa.gov/Plants_Land_Water/PlantIndustry/Pages/Pesticides.aspx",
        "phone": "717-772-5214",
    },
    "RI": {
        "agency": "Rhode Island Department of Environmental Management",
        "division": "Pesticides Section",
        "website": "http://www.dem.ri.gov/programs/agriculture/pesticides.php",
        "phone": "401-222-2781",
    },
    "SC": {
        "agency": "Clemson University - SC Department of Pesticide Regulation",
        "division": "Department of Pesticide Regulation",
        "website": "https://www.clemson.edu/public/regulatory/pesticide-regulation/",
        "phone": "864-646-2150",
    },
    "SD": {
        "agency": "South Dakota Department of Agriculture and Natural Resources",
        "division": "Agricultural Services Division",
        "website": "https://danr.sd.gov/Agriculture/Pesticides/",
        "phone": "605-773-4432",
    },
    "TN": {
        "agency": "Tennessee Department of Agriculture",
        "division": "Regulatory Services",
        "website": "https://www.tn.gov/agriculture/businesses/ag-inputs/pesticides.html",
        "phone": "615-837-5148",
    },
    "TX": {
        "agency": "Texas Department of Agriculture",
        "division": "Structural Pest Control Service",
        "website": "https://www.texasagriculture.gov/regulatory-programs/pesticides/",
        "phone": "512-463-7476",
    },
    "UT": {
        "agency": "Utah Department of Agriculture and Food",
        "division": "Division of Plant Industry",
        "website": "https://ag.utah.gov/farmers/pesticide-information/",
        "phone": "801-538-7181",
    },
    "VT": {
        "agency": "Vermont Agency of Agriculture, Food and Markets",
        "division": "Plant Industry, Laboratories and Consumer Assurance Division",
        "website": "https://agriculture.vermont.gov/public-health-agricultural-resource-management-division/pesticide-programs",
        "phone": "802-828-2431",
    },
    "VA": {
        "agency": "Virginia Department of Agriculture and Consumer Services",
        "division": "Office of Pesticide Services",
        "website": "https://www.vdacs.virginia.gov/plant-industry-services-pesticides.shtml",
        "phone": "804-786-3798",
    },
    "WA": {
        "agency": "Washington State Department of Agriculture",
        "division": "Pesticide Management Division",
        "website": "https://agr.wa.gov/departments/pesticide-management",
        "phone": "360-902-2040",
    },
    "WV": {
        "agency": "West Virginia Department of Agriculture",
        "division": "Pesticide Regulatory Programs",
        "website": "https://agriculture.wv.gov/divisions/plant-industries/pesticide-regulatory-programs/",
        "phone": "304-558-2214",
    },
    "WI": {
        "agency": "Wisconsin Department of Agriculture, Trade and Consumer Protection",
        "division": "Pest Management",
        "website": "https://datcp.wi.gov/Pages/Programs_Services/Pesticides.aspx",
        "phone": "608-224-4500",
    },
    "WY": {
        "agency": "Wyoming Department of Agriculture",
        "division": "Technical Services Division",
        "website": "https://agriculture.wy.gov/divisions/technical-services/pesticide-program",
        "phone": "307-777-6585",
    },
}


class BasePestControlAPI:
    """Base class for pest control license data access"""

    REQUEST_DELAY = 1.0

    def __init__(self, state: str):
        self.state = state.upper()
        self.session: Optional[aiohttp.ClientSession] = None
        self.state_info = STATE_PEST_CONTROL_AGENCIES.get(self.state, {})

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "DataGod Pest Control License Research/1.0",
                "Accept": "application/json, text/html",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def get_licensing_agency(self) -> Dict[str, str]:
        """Get state pest control licensing agency information"""
        return self.state_info

    async def search_licenses(
        self,
        name: Optional[str] = None,
        license_number: Optional[str] = None,
        company_name: Optional[str] = None,
        city: Optional[str] = None,
        license_type: Optional[LicenseType] = None,
        status: Optional[LicenseStatus] = None,
    ) -> List[PestControlLicense]:
        """Search for pest control licenses"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        # Would query state licensing database
        # Return sample structure
        results = []

        sample_license = PestControlLicense(
            license_number=license_number or f"{self.state}PCO-12345",
            license_type=license_type or LicenseType.OPERATOR,
            status=status or LicenseStatus.ACTIVE,
            state=self.state,
            holder_name=name or "Sample Pest Control",
            holder_type="company",
            company_name=company_name,
            city=city,
            issue_date=date(2020, 1, 15),
            expiration_date=date(2025, 1, 15),
            categories=[CategoryType.GENERAL, CategoryType.TERMITE],
            category_descriptions=["General Household Pest", "Termite - Subterranean"],
            insurance_on_file=True,
            bond_on_file=True,
        )

        # Apply filters
        if name and name.lower() not in sample_license.holder_name.lower():
            return results
        if license_number and sample_license.license_number != license_number:
            return results

        results.append(sample_license)
        return results

    async def verify_license(
        self,
        license_number: str
    ) -> Optional[PestControlLicense]:
        """Verify a pest control license"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        results = await self.search_licenses(license_number=license_number)
        return results[0] if results else None

    async def search_companies(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        service_type: Optional[str] = None,
    ) -> List[PestControlCompany]:
        """Search for pest control companies"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        # Would query state business registry
        results = []

        sample_company = PestControlCompany(
            company_id=f"{self.state}-COMP-001",
            company_name=name or "ABC Pest Control",
            state=self.state,
            city=city,
            license_number=f"{self.state}PCO-12345",
            services_offered=["General Pest Control", "Termite Treatment", "Rodent Control"],
            status=LicenseStatus.ACTIVE,
        )

        if name and name.lower() not in sample_company.company_name.lower():
            return results

        results.append(sample_company)
        return results

    async def get_disciplinary_actions(
        self,
        license_number: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> List[DisciplinaryAction]:
        """Get disciplinary actions against license holders"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        # Would query enforcement database
        # Return sample structure
        return []


# State-specific implementations
class CaliforniaPestControlAPI(BasePestControlAPI):
    """California Structural Pest Control Board"""

    BASE_URL = "https://www.pestboard.ca.gov/licensee/"

    def __init__(self):
        super().__init__("CA")


class TexasPestControlAPI(BasePestControlAPI):
    """Texas Structural Pest Control Service"""

    BASE_URL = "https://www.texasagriculture.gov/regulatory-programs/pesticides/"

    def __init__(self):
        super().__init__("TX")


class FloridaPestControlAPI(BasePestControlAPI):
    """Florida FDACS Pest Control"""

    BASE_URL = "https://www.fdacs.gov/Business-Services/Pest-Control"

    def __init__(self):
        super().__init__("FL")


class NewYorkPestControlAPI(BasePestControlAPI):
    """New York DEC Pesticides"""

    BASE_URL = "https://www.dec.ny.gov/chemical/298.html"

    def __init__(self):
        super().__init__("NY")


# API Registry
STATE_PEST_CONTROL_APIS: Dict[str, type] = {
    "CA": CaliforniaPestControlAPI,
    "TX": TexasPestControlAPI,
    "FL": FloridaPestControlAPI,
    "NY": NewYorkPestControlAPI,
}


def get_pest_control_api(state: str) -> BasePestControlAPI:
    """Get the appropriate pest control API for a state"""
    state_upper = state.upper()
    api_class = STATE_PEST_CONTROL_APIS.get(state_upper, BasePestControlAPI)
    if api_class == BasePestControlAPI:
        return BasePestControlAPI(state_upper)
    return api_class()


# Convenience functions

def get_state_pest_control_agency(state: str) -> Dict[str, str]:
    """Get state pest control licensing agency information"""
    return STATE_PEST_CONTROL_AGENCIES.get(state.upper(), {})


def search_pest_control_licenses(
    state: str,
    name: Optional[str] = None,
    license_number: Optional[str] = None,
    company_name: Optional[str] = None,
    city: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search for pest control licenses"""
    async def _search():
        api = get_pest_control_api(state)
        async with api:
            results = await api.search_licenses(
                name=name,
                license_number=license_number,
                company_name=company_name,
                city=city,
            )
            return [r.to_dict() for r in results]
    return asyncio.run(_search())


def verify_pest_control_license(
    state: str,
    license_number: str
) -> Optional[Dict[str, Any]]:
    """Verify a pest control license"""
    async def _verify():
        api = get_pest_control_api(state)
        async with api:
            result = await api.verify_license(license_number)
            return result.to_dict() if result else None
    return asyncio.run(_verify())


def search_pest_control_companies(
    state: str,
    name: Optional[str] = None,
    city: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search for pest control companies"""
    async def _search():
        api = get_pest_control_api(state)
        async with api:
            results = await api.search_companies(name=name, city=city)
            return [r.to_dict() for r in results]
    return asyncio.run(_search())


def search_all_states_pest_control(
    name: Optional[str] = None,
    company_name: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Search for pest control licenses across all states"""
    async def _search():
        results = {}
        for state in STATE_PEST_CONTROL_AGENCIES.keys():
            api = get_pest_control_api(state)
            async with api:
                state_results = await api.search_licenses(
                    name=name,
                    company_name=company_name,
                )
                if state_results:
                    results[state] = [r.to_dict() for r in state_results]
        return results
    return asyncio.run(_search())


# Module exports
__all__ = [
    # Enums
    "LicenseType",
    "LicenseStatus",
    "CategoryType",
    # Dataclasses
    "PestControlLicense",
    "DisciplinaryAction",
    "PestControlCompany",
    # Data
    "STATE_PEST_CONTROL_AGENCIES",
    # API Classes
    "BasePestControlAPI",
    "STATE_PEST_CONTROL_APIS",
    # Convenience functions
    "get_state_pest_control_agency",
    "search_pest_control_licenses",
    "verify_pest_control_license",
    "search_pest_control_companies",
    "search_all_states_pest_control",
]
