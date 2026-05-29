"""
Regulatory Records Scraper - OSHA, MSHA, SEC, CPSC, and state regulatory data.

Free Public Sources:
- OSHA: Workplace safety inspections, violations, injuries
- MSHA: Mine safety data
- SEC: EDGAR filings, enforcement actions
- CPSC: Product recalls and safety reports
- State regulatory agencies
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp


class ViolationType(Enum):
    """Regulatory violation types."""

    SERIOUS = "serious"
    WILLFUL = "willful"
    REPEAT = "repeat"
    OTHER_THAN_SERIOUS = "other_than_serious"
    FAILURE_TO_ABATE = "failure_to_abate"
    UNCLASSIFIED = "unclassified"


class InspectionType(Enum):
    """OSHA inspection types."""

    PROGRAMMED = "programmed"
    COMPLAINT = "complaint"
    REFERRAL = "referral"
    ACCIDENT = "accident"
    FOLLOWUP = "followup"
    UNPROGRAMMED = "unprogrammed"


class SECFilingType(Enum):
    """SEC filing types."""

    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"
    FORM_4 = "4"
    FORM_DEF14A = "DEF 14A"
    FORM_S1 = "S-1"
    FORM_13F = "13F"
    FORM_13D = "SC 13D"
    FORM_144 = "144"
    OTHER = "other"


@dataclass
class OSHAInspection:
    """OSHA workplace inspection record."""

    activity_number: str
    establishment_name: str
    site_address: str
    site_city: str
    site_state: str
    site_zip: str
    naics_code: Optional[str] = None
    inspection_type: Optional[str] = None
    open_date: Optional[datetime] = None
    close_case_date: Optional[datetime] = None
    total_violations: int = 0
    serious_violations: int = 0
    willful_violations: int = 0
    repeat_violations: int = 0
    other_violations: int = 0
    total_penalties: float = 0.0
    fatalities: int = 0
    hospitalized: int = 0
    union_status: Optional[str] = None
    sic_code: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OSHAViolation:
    """OSHA violation detail."""

    citation_id: str
    activity_number: str
    violation_type: str
    standard_code: str
    standard_description: Optional[str] = None
    penalty_amount: float = 0.0
    current_penalty: float = 0.0
    gravity: Optional[str] = None
    abate_date: Optional[datetime] = None
    issuance_date: Optional[datetime] = None
    contested: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MSHAInspection:
    """MSHA mine inspection record."""

    event_number: str
    mine_id: str
    mine_name: str
    mine_type: Optional[str] = None
    operator_name: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    inspection_begin_date: Optional[datetime] = None
    inspection_end_date: Optional[datetime] = None
    violations_count: int = 0
    total_assessed: float = 0.0
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SECFiling:
    """SEC EDGAR filing record."""

    accession_number: str
    cik: str
    company_name: str
    form_type: str
    filing_date: Optional[datetime] = None
    period_of_report: Optional[datetime] = None
    file_number: Optional[str] = None
    film_number: Optional[str] = None
    items: Optional[str] = None
    size: Optional[int] = None
    is_xbrl: bool = False
    is_inline_xbrl: bool = False
    primary_document: Optional[str] = None
    primary_doc_description: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SECEnforcement:
    """SEC enforcement action."""

    action_id: str
    title: str
    action_date: Optional[datetime] = None
    action_type: Optional[str] = None
    respondents: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    civil_penalties: float = 0.0
    disgorgement: float = 0.0
    url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProductRecall:
    """CPSC product recall."""

    recall_id: str
    recall_number: str
    product_name: str
    recall_date: Optional[datetime] = None
    description: Optional[str] = None
    hazard: Optional[str] = None
    remedy: Optional[str] = None
    units: Optional[str] = None
    injuries: int = 0
    deaths: int = 0
    manufacturer: Optional[str] = None
    retailer: Optional[str] = None
    in_store_date: Optional[datetime] = None
    images: List[str] = field(default_factory=list)
    url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


# State regulatory agencies URLs
STATE_REGULATORY_URLS = {
    "AL": {
        "labor": "https://labor.alabama.gov/",
        "environment": "https://adem.alabama.gov/",
        "insurance": "https://aldoi.gov/",
    },
    "AK": {
        "labor": "https://labor.alaska.gov/",
        "environment": "https://dec.alaska.gov/",
        "commerce": "https://www.commerce.alaska.gov/",
    },
    "AZ": {
        "labor": "https://www.azica.gov/",
        "environment": "https://azdeq.gov/",
        "insurance": "https://difi.az.gov/",
    },
    "AR": {
        "labor": "https://www.labor.arkansas.gov/",
        "environment": "https://www.adeq.state.ar.us/",
        "insurance": "https://insurance.arkansas.gov/",
    },
    "CA": {
        "labor": "https://www.dir.ca.gov/",
        "osha": "https://www.dir.ca.gov/dosh/",
        "environment": "https://calepa.ca.gov/",
        "insurance": "https://www.insurance.ca.gov/",
    },
    "CO": {
        "labor": "https://cdle.colorado.gov/",
        "environment": "https://cdphe.colorado.gov/",
        "insurance": "https://doi.colorado.gov/",
    },
    "CT": {
        "labor": "https://www.ctdol.state.ct.us/",
        "osha": "https://www.ctdol.state.ct.us/osha/osha.htm",
        "environment": "https://portal.ct.gov/DEEP",
    },
    "DE": {
        "labor": "https://labor.delaware.gov/",
        "environment": "https://dnrec.alpha.delaware.gov/",
    },
    "DC": {"labor": "https://does.dc.gov/", "environment": "https://doee.dc.gov/"},
    "FL": {
        "labor": "https://www.floridajobs.org/",
        "environment": "https://floridadep.gov/",
        "insurance": "https://www.myfloridacfo.com/",
    },
    "GA": {
        "labor": "https://dol.georgia.gov/",
        "environment": "https://epd.georgia.gov/",
        "insurance": "https://oci.georgia.gov/",
    },
    "HI": {
        "labor": "https://labor.hawaii.gov/",
        "hiosh": "https://labor.hawaii.gov/hiosh/",
        "environment": "https://health.hawaii.gov/",
    },
    "ID": {
        "labor": "https://www.labor.idaho.gov/",
        "environment": "https://www.deq.idaho.gov/",
    },
    "IL": {
        "labor": "https://www.illinois.gov/idol/",
        "environment": "https://www2.illinois.gov/epa/",
        "insurance": "https://insurance.illinois.gov/",
    },
    "IN": {
        "labor": "https://www.in.gov/dol/",
        "iosha": "https://www.in.gov/dol/iosha/",
        "environment": "https://www.in.gov/idem/",
    },
    "IA": {
        "labor": "https://www.iowadivisionoflabor.gov/",
        "iosh": "https://www.iowaosha.gov/",
        "environment": "https://www.iowadnr.gov/",
    },
    "KS": {
        "labor": "https://www.dol.ks.gov/",
        "environment": "https://www.kdhe.ks.gov/",
    },
    "KY": {
        "labor": "https://labor.ky.gov/",
        "kyosh": "https://labor.ky.gov/standards/Pages/default.aspx",
        "environment": "https://eec.ky.gov/",
    },
    "LA": {
        "labor": "https://www.laworks.net/",
        "environment": "https://deq.louisiana.gov/",
    },
    "ME": {
        "labor": "https://www.maine.gov/labor/",
        "environment": "https://www.maine.gov/dep/",
    },
    "MD": {
        "labor": "https://www.dllr.state.md.us/",
        "mosh": "https://www.dllr.state.md.us/labor/mosh/",
        "environment": "https://mde.maryland.gov/",
    },
    "MA": {
        "labor": "https://www.mass.gov/orgs/department-of-labor-standards",
        "environment": "https://www.mass.gov/orgs/massachusetts-department-of-environmental-protection",
    },
    "MI": {
        "labor": "https://www.michigan.gov/leo/",
        "miosha": "https://www.michigan.gov/leo/bureaus-agencies/miosha",
        "environment": "https://www.michigan.gov/egle/",
    },
    "MN": {
        "labor": "https://www.dli.mn.gov/",
        "mnosha": "https://www.dli.mn.gov/business/workplace-safety-and-health",
        "environment": "https://www.pca.state.mn.us/",
    },
    "MS": {"labor": "https://mdes.ms.gov/", "environment": "https://www.mdeq.ms.gov/"},
    "MO": {"labor": "https://labor.mo.gov/", "environment": "https://dnr.mo.gov/"},
    "MT": {"labor": "https://erd.dli.mt.gov/", "environment": "https://deq.mt.gov/"},
    "NE": {
        "labor": "https://dol.nebraska.gov/",
        "environment": "http://www.deq.state.ne.us/",
    },
    "NV": {
        "labor": "https://labor.nv.gov/",
        "nvosha": "https://dir.nv.gov/OSHA/Home/",
        "environment": "https://ndep.nv.gov/",
    },
    "NH": {
        "labor": "https://www.nh.gov/labor/",
        "environment": "https://www.des.nh.gov/",
    },
    "NJ": {
        "labor": "https://www.nj.gov/labor/",
        "peosh": "https://www.nj.gov/labor/safetyandhealth/",
        "environment": "https://www.nj.gov/dep/",
    },
    "NM": {
        "labor": "https://www.dws.state.nm.us/",
        "environment": "https://www.env.nm.gov/",
    },
    "NY": {
        "labor": "https://dol.ny.gov/",
        "pesh": "https://dol.ny.gov/public-employee-safety-and-health-pesh",
        "environment": "https://www.dec.ny.gov/",
    },
    "NC": {
        "labor": "https://www.labor.nc.gov/",
        "ncosha": "https://www.labor.nc.gov/safety-and-health",
        "environment": "https://deq.nc.gov/",
    },
    "ND": {"labor": "https://www.nd.gov/labor/", "environment": "https://deq.nd.gov/"},
    "OH": {"labor": "https://com.ohio.gov/", "environment": "https://epa.ohio.gov/"},
    "OK": {
        "labor": "https://oklahoma.gov/labor.html",
        "environment": "https://www.deq.ok.gov/",
    },
    "OR": {
        "labor": "https://www.oregon.gov/boli/",
        "orosha": "https://osha.oregon.gov/",
        "environment": "https://www.oregon.gov/deq/",
    },
    "PA": {
        "labor": "https://www.dli.pa.gov/",
        "environment": "https://www.dep.pa.gov/",
    },
    "RI": {"labor": "https://dlt.ri.gov/", "environment": "http://www.dem.ri.gov/"},
    "SC": {
        "labor": "https://llr.sc.gov/",
        "scosha": "https://llr.sc.gov/osha/",
        "environment": "https://scdhec.gov/",
    },
    "SD": {"labor": "https://dlr.sd.gov/", "environment": "https://danr.sd.gov/"},
    "TN": {
        "labor": "https://www.tn.gov/workforce.html",
        "tosha": "https://www.tn.gov/workforce/employees/safety-health.html",
        "environment": "https://www.tn.gov/environment.html",
    },
    "TX": {
        "labor": "https://www.twc.texas.gov/",
        "environment": "https://www.tceq.texas.gov/",
        "insurance": "https://www.tdi.texas.gov/",
    },
    "UT": {
        "labor": "https://laborcommission.utah.gov/",
        "uosh": "https://laborcommission.utah.gov/divisions/uosh/",
        "environment": "https://deq.utah.gov/",
    },
    "VT": {
        "labor": "https://labor.vermont.gov/",
        "vosha": "https://labor.vermont.gov/vosha",
        "environment": "https://dec.vermont.gov/",
    },
    "VA": {
        "labor": "https://www.doli.virginia.gov/",
        "vosh": "https://www.doli.virginia.gov/vosh/",
        "environment": "https://www.deq.virginia.gov/",
    },
    "WA": {
        "labor": "https://www.lni.wa.gov/",
        "dosh": "https://www.lni.wa.gov/safety-health/",
        "environment": "https://ecology.wa.gov/",
    },
    "WV": {"labor": "https://labor.wv.gov/", "environment": "https://dep.wv.gov/"},
    "WI": {
        "labor": "https://dwd.wisconsin.gov/",
        "environment": "https://dnr.wisconsin.gov/",
    },
    "WY": {
        "labor": "https://dws.wyo.gov/",
        "wyosha": "https://wyomingworkforce.org/businesses-and-employers/osha/",
        "environment": "https://deq.wyoming.gov/",
    },
}


class RegulatoryRecordsScraper:
    """
    Scraper for regulatory records from OSHA, MSHA, SEC, CPSC, and state agencies.

    Free Public APIs:
    - OSHA Enforcement Data: https://enforcedata.dol.gov/
    - MSHA Data: https://arlweb.msha.gov/OpenGovernmentData/
    - SEC EDGAR: https://www.sec.gov/cgi-bin/browse-edgar
    - CPSC Recalls: https://www.cpsc.gov/Recalls/CPSC-Recalls-API
    """

    # Federal API endpoints
    OSHA_API_BASE = "https://enforcedata.dol.gov/api"
    MSHA_DATA_URL = "https://arlweb.msha.gov/OpenGovernmentData/"
    SEC_EDGAR_BASE = "https://www.sec.gov/cgi-bin/browse-edgar"
    SEC_FULL_TEXT = "https://efts.sec.gov/LATEST/search-index"
    SEC_COMPANY_SEARCH = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
    CPSC_API_BASE = "https://www.saferproducts.gov/RestWebServices"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the regulatory records scraper."""
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

    # ==================== OSHA Methods ====================

    async def search_osha_inspections(
        self,
        establishment_name: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        naics: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[OSHAInspection]:
        """
        Search OSHA inspection records.

        The DOL Enforcement Data API provides free access to OSHA data.
        """
        await self._ensure_session()

        # Build query parameters
        params = {"format": "json", "limit": limit}

        if establishment_name:
            params["estab_name"] = establishment_name
        if state:
            params["site_state"] = state.upper()
        if city:
            params["site_city"] = city
        if zip_code:
            params["site_zip"] = zip_code
        if naics:
            params["naics_code"] = naics
        if start_date:
            params["open_date_from"] = start_date
        if end_date:
            params["open_date_to"] = end_date

        results = []

        try:
            url = f"{self.OSHA_API_BASE}/inspection"
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get(
                        "results", data if isinstance(data, list) else []
                    ):
                        try:
                            inspection = OSHAInspection(
                                activity_number=str(item.get("activity_nr", "")),
                                establishment_name=item.get("estab_name", ""),
                                site_address=item.get("site_address", ""),
                                site_city=item.get("site_city", ""),
                                site_state=item.get("site_state", ""),
                                site_zip=item.get("site_zip", ""),
                                naics_code=item.get("naics_code"),
                                inspection_type=item.get("insp_type"),
                                total_violations=int(
                                    item.get("total_violations", 0) or 0
                                ),
                                serious_violations=int(
                                    item.get("serious_violations", 0) or 0
                                ),
                                willful_violations=int(
                                    item.get("willful_violations", 0) or 0
                                ),
                                repeat_violations=int(
                                    item.get("repeat_violations", 0) or 0
                                ),
                                other_violations=int(
                                    item.get("other_violations", 0) or 0
                                ),
                                total_penalties=float(
                                    item.get("total_penalties", 0) or 0
                                ),
                                fatalities=int(item.get("nr_in_estab", 0) or 0),
                                hospitalized=int(item.get("nr_exposed", 0) or 0),
                                union_status=item.get("union_status"),
                                sic_code=item.get("sic_code"),
                                raw_data=item,
                            )

                            # Parse dates
                            if item.get("open_date"):
                                try:
                                    inspection.open_date = datetime.strptime(
                                        item["open_date"][:10], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            if item.get("close_case_date"):
                                try:
                                    inspection.close_case_date = datetime.strptime(
                                        item["close_case_date"][:10], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            results.append(inspection)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    async def get_osha_violations(self, activity_number: str) -> List[OSHAViolation]:
        """Get violations for a specific OSHA inspection."""
        await self._ensure_session()

        results = []

        try:
            url = f"{self.OSHA_API_BASE}/violation"
            params = {"activity_nr": activity_number, "format": "json"}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get(
                        "results", data if isinstance(data, list) else []
                    ):
                        try:
                            violation = OSHAViolation(
                                citation_id=str(item.get("citation_id", "")),
                                activity_number=str(item.get("activity_nr", "")),
                                violation_type=item.get("viol_type", ""),
                                standard_code=item.get("standard", ""),
                                standard_description=item.get("standard_text"),
                                penalty_amount=float(
                                    item.get("initial_penalty", 0) or 0
                                ),
                                current_penalty=float(
                                    item.get("current_penalty", 0) or 0
                                ),
                                gravity=item.get("gravity"),
                                contested=bool(item.get("contested")),
                                raw_data=item,
                            )

                            if item.get("abate_date"):
                                try:
                                    violation.abate_date = datetime.strptime(
                                        item["abate_date"][:10], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            results.append(violation)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    # ==================== SEC EDGAR Methods ====================

    async def search_sec_filings(
        self,
        company_name: Optional[str] = None,
        cik: Optional[str] = None,
        form_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 40,
    ) -> List[SECFiling]:
        """
        Search SEC EDGAR filings.

        Free API - no registration required.
        Rate limit: 10 requests per second.
        """
        await self._ensure_session()

        results = []

        try:
            # Use SEC full-text search API
            url = "https://efts.sec.gov/LATEST/search-index"

            query_parts = []
            if company_name:
                query_parts.append(f'companyName:"{company_name}"')
            if form_type:
                query_parts.append(f'formType:"{form_type}"')

            params = {
                "q": " AND ".join(query_parts) if query_parts else "*",
                "dateRange": "custom",
                "startdt": start_date or "2020-01-01",
                "enddt": end_date or datetime.now().strftime("%Y-%m-%d"),
                "from": 0,
                "size": limit,
            }

            if cik:
                params["ciks"] = cik.zfill(10)

            headers = {
                "User-Agent": "DataGod Research contact@example.com",
                "Accept": "application/json",
            }

            # Alternative: use the submissions API for company filings
            if cik:
                cik_padded = cik.zfill(10)
                submissions_url = (
                    f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
                )

                async with self.session.get(
                    submissions_url, headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        company = data.get("name", "")
                        filings = data.get("filings", {}).get("recent", {})

                        accession_numbers = filings.get("accessionNumber", [])
                        form_types = filings.get("form", [])
                        filing_dates = filings.get("filingDate", [])
                        primary_docs = filings.get("primaryDocument", [])

                        for i in range(min(limit, len(accession_numbers))):
                            if form_type and form_types[i] != form_type:
                                continue

                            filing = SECFiling(
                                accession_number=accession_numbers[i],
                                cik=cik,
                                company_name=company,
                                form_type=form_types[i],
                                primary_document=(
                                    primary_docs[i] if i < len(primary_docs) else None
                                ),
                                raw_data={
                                    "accessionNumber": accession_numbers[i],
                                    "form": form_types[i],
                                    "filingDate": (
                                        filing_dates[i]
                                        if i < len(filing_dates)
                                        else None
                                    ),
                                },
                            )

                            if i < len(filing_dates):
                                try:
                                    filing.filing_date = datetime.strptime(
                                        filing_dates[i], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            results.append(filing)

        except aiohttp.ClientError:
            pass

        return results

    async def get_sec_company_info(self, cik: str) -> Optional[Dict[str, Any]]:
        """Get company information from SEC."""
        await self._ensure_session()

        try:
            cik_padded = cik.zfill(10)
            url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

            headers = {
                "User-Agent": "DataGod Research contact@example.com",
                "Accept": "application/json",
            }

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()

        except aiohttp.ClientError:
            pass

        return None

    # ==================== CPSC Methods ====================

    async def search_product_recalls(
        self,
        product_name: Optional[str] = None,
        manufacturer: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[ProductRecall]:
        """
        Search CPSC product recalls.

        Free API - no registration required.
        """
        await self._ensure_session()

        results = []

        try:
            url = f"{self.CPSC_API_BASE}/Recall"
            params = {"format": "json"}

            if product_name:
                params["RecallTitle"] = product_name
            if manufacturer:
                params["Manufacturer"] = manufacturer
            if start_date:
                params["RecallDateStart"] = start_date
            if end_date:
                params["RecallDateEnd"] = end_date

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data[:limit] if isinstance(data, list) else []:
                        try:
                            recall = ProductRecall(
                                recall_id=str(item.get("RecallID", "")),
                                recall_number=item.get("RecallNumber", ""),
                                product_name=item.get("Title", ""),
                                description=item.get("Description"),
                                hazard=item.get("Hazard"),
                                remedy=item.get("Remedy"),
                                units=item.get("NumberOfUnits"),
                                injuries=int(item.get("Injuries", 0) or 0),
                                deaths=int(item.get("Deaths", 0) or 0),
                                url=item.get("URL"),
                                raw_data=item,
                            )

                            if item.get("RecallDate"):
                                try:
                                    recall.recall_date = datetime.strptime(
                                        item["RecallDate"][:10], "%Y-%m-%d"
                                    )
                                except (ValueError, TypeError):
                                    pass

                            # Get manufacturers
                            manufacturers = item.get("Manufacturers", [])
                            if manufacturers and isinstance(manufacturers, list):
                                recall.manufacturer = ", ".join(
                                    [
                                        m.get("Name", "")
                                        for m in manufacturers
                                        if m.get("Name")
                                    ]
                                )

                            # Get retailers
                            retailers = item.get("Retailers", [])
                            if retailers and isinstance(retailers, list):
                                recall.retailer = ", ".join(
                                    [
                                        r.get("Name", "")
                                        for r in retailers
                                        if r.get("Name")
                                    ]
                                )

                            # Get images
                            images = item.get("Images", [])
                            if images and isinstance(images, list):
                                recall.images = [
                                    img.get("URL") for img in images if img.get("URL")
                                ]

                            results.append(recall)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    # ==================== State Regulatory Methods ====================

    def get_state_regulatory_urls(self, state: str) -> Dict[str, str]:
        """Get regulatory agency URLs for a state."""
        return STATE_REGULATORY_URLS.get(state.upper(), {})

    def get_state_osha_plan(self, state: str) -> Optional[str]:
        """
        Check if state has its own OSHA plan.

        22 states have their own OSHA-approved plans that cover
        private sector workers.
        """
        state_plans = {
            "AK",
            "AZ",
            "CA",
            "HI",
            "IN",
            "IA",
            "KY",
            "MD",
            "MI",
            "MN",
            "NV",
            "NM",
            "NC",
            "OR",
            "SC",
            "TN",
            "UT",
            "VT",
            "VA",
            "WA",
            "WY",
        }

        state_upper = state.upper()
        if state_upper in state_plans:
            urls = STATE_REGULATORY_URLS.get(state_upper, {})
            # Return state OSHA URL if available
            for key in [
                "osha",
                "dosh",
                "hiosh",
                "iosha",
                "iosh",
                "kyosh",
                "mosh",
                "miosha",
                "mnosha",
                "nvosha",
                "ncosha",
                "orosha",
                "scosha",
                "tosha",
                "uosh",
                "vosha",
                "vosh",
                "wyosha",
                "pesh",
                "peosh",
            ]:
                if key in urls:
                    return urls[key]
            return urls.get("labor")

        return None

    def get_all_states_regulatory(self) -> Dict[str, Dict[str, str]]:
        """Get regulatory URLs for all states."""
        return STATE_REGULATORY_URLS.copy()


# Synchronous wrapper functions
def search_osha_inspections_sync(
    establishment_name: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    **kwargs,
) -> List[OSHAInspection]:
    """Synchronous wrapper for OSHA inspection search."""

    async def _search():
        async with RegulatoryRecordsScraper() as scraper:
            return await scraper.search_osha_inspections(
                establishment_name=establishment_name, state=state, city=city, **kwargs
            )

    return asyncio.run(_search())


def search_sec_filings_sync(
    company_name: Optional[str] = None,
    cik: Optional[str] = None,
    form_type: Optional[str] = None,
    **kwargs,
) -> List[SECFiling]:
    """Synchronous wrapper for SEC filing search."""

    async def _search():
        async with RegulatoryRecordsScraper() as scraper:
            return await scraper.search_sec_filings(
                company_name=company_name, cik=cik, form_type=form_type, **kwargs
            )

    return asyncio.run(_search())


def search_product_recalls_sync(
    product_name: Optional[str] = None, manufacturer: Optional[str] = None, **kwargs
) -> List[ProductRecall]:
    """Synchronous wrapper for CPSC recall search."""

    async def _search():
        async with RegulatoryRecordsScraper() as scraper:
            return await scraper.search_product_recalls(
                product_name=product_name, manufacturer=manufacturer, **kwargs
            )

    return asyncio.run(_search())


# Export all
__all__ = [
    "RegulatoryRecordsScraper",
    "OSHAInspection",
    "OSHAViolation",
    "MSHAInspection",
    "SECFiling",
    "SECEnforcement",
    "ProductRecall",
    "ViolationType",
    "InspectionType",
    "SECFilingType",
    "STATE_REGULATORY_URLS",
    "search_osha_inspections_sync",
    "search_sec_filings_sync",
    "search_product_recalls_sync",
]
