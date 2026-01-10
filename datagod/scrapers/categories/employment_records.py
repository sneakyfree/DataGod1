"""
Employment Records Scraper - Government salaries, pensions, contractor data.

Free Public Sources:
- USAspending.gov: Federal contractor awards, grants
- OPM FedScope: Federal workforce statistics
- State comptroller databases for government salaries
- Public pension fund data
"""

import asyncio
import aiohttp
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class AwardType(Enum):
    """Federal award types."""
    CONTRACT = "contract"
    GRANT = "grant"
    LOAN = "loan"
    DIRECT_PAYMENT = "direct_payment"
    OTHER = "other"


class EmployeeType(Enum):
    """Government employee types."""
    FEDERAL = "federal"
    STATE = "state"
    COUNTY = "county"
    MUNICIPAL = "municipal"
    SCHOOL_DISTRICT = "school_district"


@dataclass
class FederalAward:
    """Federal spending award (contract, grant, etc.)."""
    award_id: str
    generated_unique_id: Optional[str] = None
    award_type: Optional[str] = None
    award_description: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_duns: Optional[str] = None
    recipient_uei: Optional[str] = None
    recipient_city: Optional[str] = None
    recipient_state: Optional[str] = None
    recipient_zip: Optional[str] = None
    recipient_country: Optional[str] = None
    awarding_agency: Optional[str] = None
    awarding_sub_agency: Optional[str] = None
    funding_agency: Optional[str] = None
    total_obligation: float = 0.0
    base_and_all_options: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    action_date: Optional[datetime] = None
    naics_code: Optional[str] = None
    naics_description: Optional[str] = None
    psc_code: Optional[str] = None
    place_of_performance_city: Optional[str] = None
    place_of_performance_state: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GovernmentSalary:
    """Government employee salary record."""
    employee_name: str
    agency: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    salary: float = 0.0
    overtime_pay: float = 0.0
    other_pay: float = 0.0
    total_compensation: float = 0.0
    benefits: float = 0.0
    year: Optional[int] = None
    employee_type: Optional[str] = None
    status: Optional[str] = None  # full-time, part-time
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PensionRecord:
    """Public pension record."""
    beneficiary_name: str
    pension_system: str
    employer: Optional[str] = None
    state: Optional[str] = None
    annual_benefit: float = 0.0
    years_of_service: Optional[int] = None
    retirement_date: Optional[datetime] = None
    benefit_type: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FederalAgency:
    """Federal agency employment data."""
    agency_name: str
    agency_code: Optional[str] = None
    total_employees: int = 0
    average_salary: float = 0.0
    median_salary: float = 0.0
    total_payroll: float = 0.0
    headquarters_location: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


# State salary database URLs
STATE_SALARY_DATABASES = {
    "AL": {
        "name": "Alabama Open Government",
        "url": "https://open.alabama.gov/",
        "type": "state"
    },
    "AK": {
        "name": "Alaska State Checkbook",
        "url": "https://checkbook.alaska.gov/",
        "type": "state"
    },
    "AZ": {
        "name": "Arizona Open Books",
        "url": "https://openbooks.az.gov/",
        "type": "state"
    },
    "AR": {
        "name": "Arkansas Transparency",
        "url": "https://www.ark.org/dfa/transparency/",
        "type": "state"
    },
    "CA": {
        "name": "California State Controller - Government Compensation",
        "url": "https://publicpay.ca.gov/",
        "type": "state",
        "has_api": False
    },
    "CO": {
        "name": "Colorado PEAK",
        "url": "https://data.colorado.gov/",
        "type": "state"
    },
    "CT": {
        "name": "Connecticut Open Data",
        "url": "https://data.ct.gov/",
        "type": "state"
    },
    "DE": {
        "name": "Delaware Open Data",
        "url": "https://data.delaware.gov/",
        "type": "state"
    },
    "DC": {
        "name": "DC Open Data",
        "url": "https://opendata.dc.gov/",
        "type": "district"
    },
    "FL": {
        "name": "Florida Has a Right to Know",
        "url": "https://www.floridahasarighttoknow.com/",
        "type": "state"
    },
    "GA": {
        "name": "Open Georgia",
        "url": "https://open.georgia.gov/",
        "type": "state"
    },
    "HI": {
        "name": "Hawaii Data Portal",
        "url": "https://data.hawaii.gov/",
        "type": "state"
    },
    "ID": {
        "name": "Idaho Transparent Idaho",
        "url": "https://transparent.idaho.gov/",
        "type": "state"
    },
    "IL": {
        "name": "Illinois Comptroller - Salaries",
        "url": "https://illinoiscomptroller.gov/financial-data/state-employee-salary-database/",
        "type": "state"
    },
    "IN": {
        "name": "Indiana Transparency Portal",
        "url": "https://www.in.gov/itp/",
        "type": "state"
    },
    "IA": {
        "name": "Iowa Data Portal",
        "url": "https://data.iowa.gov/",
        "type": "state"
    },
    "KS": {
        "name": "Kansas Open Gov",
        "url": "https://admin.ks.gov/offices/accounts-reports/open-gov",
        "type": "state"
    },
    "KY": {
        "name": "Kentucky OpenDoor",
        "url": "https://opendoor.ky.gov/",
        "type": "state"
    },
    "LA": {
        "name": "Louisiana Checkbook",
        "url": "https://checkbook.la.gov/",
        "type": "state"
    },
    "ME": {
        "name": "Maine Open Checkbook",
        "url": "https://www.maine.gov/dafs/bbm/opencheckbook/",
        "type": "state"
    },
    "MD": {
        "name": "Maryland Open Data",
        "url": "https://opendata.maryland.gov/",
        "type": "state"
    },
    "MA": {
        "name": "Massachusetts Open Checkbook",
        "url": "https://www.macomptroller.org/cthru/",
        "type": "state"
    },
    "MI": {
        "name": "Michigan Open Data",
        "url": "https://data.michigan.gov/",
        "type": "state"
    },
    "MN": {
        "name": "Minnesota Open Data",
        "url": "https://mn.gov/opendata/",
        "type": "state"
    },
    "MS": {
        "name": "Mississippi Transparency",
        "url": "https://www.transparency.ms.gov/",
        "type": "state"
    },
    "MO": {
        "name": "Missouri Accountability Portal",
        "url": "https://mapyourtaxes.mo.gov/",
        "type": "state"
    },
    "MT": {
        "name": "Montana Transparency",
        "url": "https://montanabudget.com/",
        "type": "state"
    },
    "NE": {
        "name": "Nebraska Open Data",
        "url": "https://statedata.nebraska.gov/",
        "type": "state"
    },
    "NV": {
        "name": "Nevada Open Gov",
        "url": "https://open.nv.gov/",
        "type": "state"
    },
    "NH": {
        "name": "New Hampshire Transparency",
        "url": "https://www.nh.gov/transparentnh/",
        "type": "state"
    },
    "NJ": {
        "name": "New Jersey Data Miner",
        "url": "https://data.nj.gov/",
        "type": "state",
        "has_api": True
    },
    "NM": {
        "name": "New Mexico Sunshine Portal",
        "url": "https://sunshineportalnm.com/",
        "type": "state"
    },
    "NY": {
        "name": "New York SeeThroughNY",
        "url": "https://www.seethroughny.net/",
        "type": "state"
    },
    "NC": {
        "name": "North Carolina Open Budget",
        "url": "https://www.osbm.nc.gov/budgetbook/",
        "type": "state"
    },
    "ND": {
        "name": "North Dakota Checkbook",
        "url": "https://www.nd.gov/omb/public/checkbook",
        "type": "state"
    },
    "OH": {
        "name": "Ohio Checkbook",
        "url": "https://checkbook.ohio.gov/",
        "type": "state"
    },
    "OK": {
        "name": "Oklahoma Open Books",
        "url": "https://openbooks.ok.gov/",
        "type": "state"
    },
    "OR": {
        "name": "Oregon Transparency",
        "url": "https://www.oregon.gov/transparency/",
        "type": "state"
    },
    "PA": {
        "name": "Pennsylvania Open Data",
        "url": "https://data.pa.gov/",
        "type": "state",
        "has_api": True
    },
    "RI": {
        "name": "Rhode Island Open Gov",
        "url": "https://opengov.ri.gov/",
        "type": "state"
    },
    "SC": {
        "name": "South Carolina Fiscal Transparency",
        "url": "https://www.cg.sc.gov/public-info/fiscal-transparency",
        "type": "state"
    },
    "SD": {
        "name": "South Dakota Open.SD",
        "url": "https://open.sd.gov/",
        "type": "state"
    },
    "TN": {
        "name": "Tennessee OpenRecords",
        "url": "https://www.tn.gov/transparenttn.html",
        "type": "state"
    },
    "TX": {
        "name": "Texas Comptroller - State Salaries",
        "url": "https://comptroller.texas.gov/transparency/open-data/",
        "type": "state",
        "has_api": True
    },
    "UT": {
        "name": "Utah Transparent",
        "url": "https://transparent.utah.gov/",
        "type": "state"
    },
    "VT": {
        "name": "Vermont Transparency",
        "url": "https://spotlight.vermont.gov/",
        "type": "state"
    },
    "VA": {
        "name": "Virginia Data Point",
        "url": "https://www.datapoint.apa.virginia.gov/",
        "type": "state"
    },
    "WA": {
        "name": "Washington Fiscal Information",
        "url": "https://fiscal.wa.gov/",
        "type": "state"
    },
    "WV": {
        "name": "West Virginia Transparency",
        "url": "https://transparency.wv.gov/",
        "type": "state"
    },
    "WI": {
        "name": "Wisconsin OpenBook",
        "url": "https://openbook.wi.gov/",
        "type": "state"
    },
    "WY": {
        "name": "Wyoming WyOpen",
        "url": "https://wyopen.wyo.gov/",
        "type": "state"
    }
}

# State pension fund databases
STATE_PENSION_DATABASES = {
    "CA": {
        "calpers": "https://www.calpers.ca.gov/",
        "calstrs": "https://www.calstrs.com/"
    },
    "TX": {
        "trs": "https://www.trs.texas.gov/",
        "ers": "https://ers.texas.gov/"
    },
    "NY": {
        "nyslrs": "https://www.osc.state.ny.us/retirement/",
        "nycers": "https://www.nycers.org/"
    },
    "FL": {
        "frs": "https://www.myfrs.com/"
    },
    "IL": {
        "surs": "https://surs.org/",
        "trs": "https://www.trsil.org/"
    },
    "PA": {
        "psers": "https://www.psers.pa.gov/",
        "sers": "https://www.sers.pa.gov/"
    },
    "OH": {
        "opers": "https://www.opers.org/",
        "strs": "https://www.strsoh.org/"
    }
}


class EmploymentRecordsScraper:
    """
    Scraper for employment and government salary records.

    Free Public APIs:
    - USAspending.gov API: Federal awards, contracts, grants
    - OPM FedScope: Federal workforce data
    - State comptroller/open data portals (varies by state)
    """

    # Federal API endpoints
    USA_SPENDING_BASE = "https://api.usaspending.gov/api/v2"
    OPM_FEDSCOPE_BASE = "https://www.opm.gov/policy-data-oversight/data-analysis-documentation/fedscope/"
    SAM_GOV_BASE = "https://api.sam.gov"

    def __init__(
        self,
        session: Optional[aiohttp.ClientSession] = None,
        sam_api_key: Optional[str] = None
    ):
        """
        Initialize the employment records scraper.

        Args:
            session: Optional aiohttp session
            sam_api_key: Free API key from SAM.gov (for contractor data)
        """
        self.session = session
        self._owns_session = session is None
        self.sam_api_key = sam_api_key

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

    # ==================== USAspending Methods ====================

    async def search_federal_awards(
        self,
        keywords: Optional[str] = None,
        recipient_name: Optional[str] = None,
        recipient_state: Optional[str] = None,
        awarding_agency: Optional[str] = None,
        award_type: Optional[str] = None,
        naics_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        limit: int = 25,
        page: int = 1
    ) -> List[FederalAward]:
        """
        Search federal spending awards using USAspending.gov API.

        Free API - no registration required.
        Rate limit: 2 requests per second.
        """
        await self._ensure_session()

        results = []

        try:
            url = f"{self.USA_SPENDING_BASE}/search/spending_by_award/"

            # Build filters
            filters = {}

            if keywords:
                filters["keywords"] = [keywords]
            if recipient_name:
                filters["recipient_search_text"] = [recipient_name]
            if recipient_state:
                filters["recipient_locations"] = [{"country": "USA", "state": recipient_state.upper()}]
            if awarding_agency:
                filters["agencies"] = [{"type": "awarding", "tier": "toptier", "name": awarding_agency}]
            if award_type:
                award_type_map = {
                    "contract": ["A", "B", "C", "D"],
                    "grant": ["02", "03", "04", "05"],
                    "loan": ["07", "08"],
                    "direct_payment": ["06", "10"]
                }
                filters["award_type_codes"] = award_type_map.get(award_type, [award_type])
            if naics_code:
                filters["naics_codes"] = [naics_code]
            if start_date or end_date:
                time_period = {}
                if start_date:
                    time_period["start_date"] = start_date
                if end_date:
                    time_period["end_date"] = end_date
                filters["time_period"] = [time_period]
            if min_amount is not None or max_amount is not None:
                filters["award_amounts"] = [{
                    "lower_bound": min_amount or 0,
                    "upper_bound": max_amount or 999999999999
                }]

            payload = {
                "filters": filters,
                "fields": [
                    "Award ID", "Recipient Name", "Start Date", "End Date",
                    "Award Amount", "Awarding Agency", "Awarding Sub Agency",
                    "Contract Award Type", "recipient_id", "Place of Performance City",
                    "Place of Performance State Code", "NAICS Code", "Description",
                    "generated_unique_award_id"
                ],
                "page": page,
                "limit": limit,
                "sort": "Award Amount",
                "order": "desc"
            }

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("results", []):
                        try:
                            award = FederalAward(
                                award_id=str(item.get("Award ID", "")),
                                generated_unique_id=item.get("generated_unique_award_id"),
                                award_type=item.get("Contract Award Type"),
                                award_description=item.get("Description"),
                                recipient_name=item.get("Recipient Name"),
                                awarding_agency=item.get("Awarding Agency"),
                                awarding_sub_agency=item.get("Awarding Sub Agency"),
                                total_obligation=float(item.get("Award Amount", 0) or 0),
                                naics_code=item.get("NAICS Code"),
                                place_of_performance_city=item.get("Place of Performance City"),
                                place_of_performance_state=item.get("Place of Performance State Code"),
                                raw_data=item
                            )

                            # Parse dates
                            if item.get("Start Date"):
                                try:
                                    award.start_date = datetime.strptime(
                                        item["Start Date"], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            if item.get("End Date"):
                                try:
                                    award.end_date = datetime.strptime(
                                        item["End Date"], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            results.append(award)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    async def get_recipient_profile(self, recipient_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed recipient profile from USAspending."""
        await self._ensure_session()

        try:
            url = f"{self.USA_SPENDING_BASE}/recipient/{recipient_id}/"

            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()

        except aiohttp.ClientError:
            pass

        return None

    async def search_agencies(
        self,
        keyword: Optional[str] = None,
        limit: int = 50
    ) -> List[FederalAgency]:
        """Search federal agencies using USAspending."""
        await self._ensure_session()

        results = []

        try:
            url = f"{self.USA_SPENDING_BASE}/references/toptier_agencies/"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("results", [])[:limit]:
                        if keyword and keyword.lower() not in item.get("agency_name", "").lower():
                            continue

                        try:
                            agency = FederalAgency(
                                agency_name=item.get("agency_name", ""),
                                agency_code=item.get("toptier_code"),
                                raw_data=item
                            )
                            results.append(agency)
                        except (KeyError, ValueError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    async def get_agency_spending(
        self,
        agency_code: str,
        fiscal_year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get agency spending summary."""
        await self._ensure_session()

        try:
            fy = fiscal_year or datetime.now().year
            url = f"{self.USA_SPENDING_BASE}/agency/{agency_code}/?fiscal_year={fy}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()

        except aiohttp.ClientError:
            pass

        return None

    # ==================== State Salary Methods ====================

    def get_state_salary_database(self, state: str) -> Optional[Dict[str, Any]]:
        """Get salary database info for a state."""
        return STATE_SALARY_DATABASES.get(state.upper())

    def get_all_state_salary_databases(self) -> Dict[str, Dict[str, Any]]:
        """Get all state salary database URLs."""
        return STATE_SALARY_DATABASES.copy()

    def get_state_pension_databases(self, state: str) -> Optional[Dict[str, str]]:
        """Get pension fund URLs for a state."""
        return STATE_PENSION_DATABASES.get(state.upper())

    def get_all_pension_databases(self) -> Dict[str, Dict[str, str]]:
        """Get all state pension database URLs."""
        return STATE_PENSION_DATABASES.copy()

    # ==================== Federal Employee Data ====================

    def get_fedscope_data_urls(self) -> Dict[str, str]:
        """
        Get URLs for OPM FedScope data files.

        FedScope provides detailed federal workforce statistics.
        Data must be downloaded - no REST API.
        """
        return {
            "employment_cube": "https://www.opm.gov/policy-data-oversight/data-analysis-documentation/fedscope/employment-trends/",
            "data_definitions": "https://www.opm.gov/policy-data-oversight/data-analysis-documentation/fedscope/definitions/",
            "quarterly_data": "https://www.opm.gov/policy-data-oversight/data-analysis-documentation/federal-employment-reports/"
        }

    def get_federal_pay_tables(self) -> Dict[str, str]:
        """Get URLs for federal pay tables."""
        return {
            "gs_pay_tables": "https://www.opm.gov/policy-data-oversight/pay-leave/salaries-wages/",
            "locality_pay": "https://www.opm.gov/policy-data-oversight/pay-leave/salaries-wages/2024/general-schedule/",
            "ses_pay": "https://www.opm.gov/policy-data-oversight/pay-leave/salaries-wages/2024/executive-senior-level/"
        }

    # ==================== Helper Methods ====================

    def get_transparency_resources(self) -> Dict[str, str]:
        """Get useful government transparency resources."""
        return {
            "usaspending": "https://www.usaspending.gov/",
            "fedspending": "https://www.fedspending.org/",
            "data_gov": "https://www.data.gov/",
            "open_gov": "https://open.usa.gov/",
            "fpds": "https://www.fpds.gov/",
            "sam_gov": "https://sam.gov/",
            "grants_gov": "https://www.grants.gov/"
        }


# Synchronous wrapper functions
def search_federal_awards_sync(
    keywords: Optional[str] = None,
    recipient_name: Optional[str] = None,
    recipient_state: Optional[str] = None,
    **kwargs
) -> List[FederalAward]:
    """Synchronous wrapper for federal award search."""
    async def _search():
        async with EmploymentRecordsScraper() as scraper:
            return await scraper.search_federal_awards(
                keywords=keywords,
                recipient_name=recipient_name,
                recipient_state=recipient_state,
                **kwargs
            )
    return asyncio.run(_search())


def search_federal_agencies_sync(
    keyword: Optional[str] = None,
    **kwargs
) -> List[FederalAgency]:
    """Synchronous wrapper for federal agency search."""
    async def _search():
        async with EmploymentRecordsScraper() as scraper:
            return await scraper.search_agencies(
                keyword=keyword,
                **kwargs
            )
    return asyncio.run(_search())


# Export all
__all__ = [
    "EmploymentRecordsScraper",
    "FederalAward",
    "GovernmentSalary",
    "PensionRecord",
    "FederalAgency",
    "AwardType",
    "EmployeeType",
    "STATE_SALARY_DATABASES",
    "STATE_PENSION_DATABASES",
    "search_federal_awards_sync",
    "search_federal_agencies_sync",
]
