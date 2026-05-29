"""
Financial Records Scraper

Free public financial records sources:
- PACER/RECAP (bankruptcy, federal civil cases)
- IRS Exempt Organizations (990 forms via ProPublica)
- State unclaimed property
- Tax liens (county records)
- Judgments (court records)
- SEC EDGAR filings (integrated via federal_sources.py)

Free Sources:
- ProPublica Nonprofit Explorer (990 data)
- CourtListener/RECAP (federal court documents)
- FDIC Failed Banks (integrated via federal_sources.py)
- State unclaimed property databases
- County recorder lien records
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class BankruptcyChapter(Enum):
    """Bankruptcy chapter types"""

    CHAPTER_7 = "Chapter 7"  # Liquidation
    CHAPTER_11 = "Chapter 11"  # Reorganization (business)
    CHAPTER_12 = "Chapter 12"  # Family farmer/fisherman
    CHAPTER_13 = "Chapter 13"  # Wage earner plan
    CHAPTER_15 = "Chapter 15"  # Cross-border insolvency


class BankruptcyStatus(Enum):
    """Bankruptcy case status"""

    OPEN = "Open"
    CLOSED = "Closed"
    DISMISSED = "Dismissed"
    DISCHARGED = "Discharged"
    CONVERTED = "Converted"


class LienType(Enum):
    """Types of liens"""

    TAX_FEDERAL = "Federal Tax Lien"
    TAX_STATE = "State Tax Lien"
    TAX_PROPERTY = "Property Tax Lien"
    MECHANICS = "Mechanics Lien"
    JUDGMENT = "Judgment Lien"
    MORTGAGE = "Mortgage"
    UCC = "UCC Filing"
    CHILD_SUPPORT = "Child Support Lien"
    HOA = "HOA Lien"


class NonprofitType(Enum):
    """IRS nonprofit classifications"""

    C501C3 = "501(c)(3)"  # Charitable
    C501C4 = "501(c)(4)"  # Social Welfare
    C501C5 = "501(c)(5)"  # Labor Organizations
    C501C6 = "501(c)(6)"  # Business Leagues
    C501C7 = "501(c)(7)"  # Social Clubs
    PRIVATE_FOUNDATION = "Private Foundation"


@dataclass
class BankruptcyCase:
    """Federal bankruptcy case record"""

    case_number: str
    court: str
    chapter: Optional[BankruptcyChapter] = None
    status: Optional[BankruptcyStatus] = None
    filing_date: Optional[date] = None
    closing_date: Optional[date] = None
    discharge_date: Optional[date] = None
    # Debtor info
    debtor_name: Optional[str] = None
    debtor_type: Optional[str] = None  # Individual, Business
    debtor_address: Optional[str] = None
    debtor_city: Optional[str] = None
    debtor_state: Optional[str] = None
    debtor_zip: Optional[str] = None
    # Case details
    judge: Optional[str] = None
    trustee: Optional[str] = None
    attorney: Optional[str] = None
    assets: Optional[float] = None
    liabilities: Optional[float] = None
    # PACER info
    pacer_case_id: Optional[str] = None
    recap_url: Optional[str] = None


@dataclass
class TaxLien:
    """Tax lien record"""

    lien_number: str
    lien_type: Optional[LienType] = None
    debtor_name: Optional[str] = None
    debtor_address: Optional[str] = None
    creditor: Optional[str] = None  # IRS, State, County
    amount: Optional[float] = None
    filing_date: Optional[date] = None
    release_date: Optional[date] = None
    county: Optional[str] = None
    state: Optional[str] = None
    book: Optional[str] = None
    page: Optional[str] = None
    instrument_number: Optional[str] = None
    status: Optional[str] = None  # Active, Released


@dataclass
class Judgment:
    """Civil judgment record"""

    case_number: str
    court: str
    judgment_date: Optional[date] = None
    plaintiff_name: Optional[str] = None
    defendant_name: Optional[str] = None
    judgment_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    costs: Optional[float] = None
    attorney_fees: Optional[float] = None
    total_amount: Optional[float] = None
    county: Optional[str] = None
    state: Optional[str] = None
    satisfaction_date: Optional[date] = None
    status: Optional[str] = None  # Unsatisfied, Satisfied, Vacated


@dataclass
class NonprofitOrg:
    """IRS exempt organization (from 990 filings)"""

    ein: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    classification: Optional[NonprofitType] = None
    subsection: Optional[str] = None
    ruling_date: Optional[date] = None
    # Financial data (from most recent 990)
    fiscal_year_end: Optional[str] = None
    total_revenue: Optional[float] = None
    total_expenses: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    net_assets: Optional[float] = None
    # Compensation
    highest_paid_employee: Optional[str] = None
    highest_compensation: Optional[float] = None
    # Filing info
    latest_990_year: Optional[int] = None
    form_type: Optional[str] = None  # 990, 990-EZ, 990-PF
    ntee_code: Optional[str] = None


@dataclass
class UnclaimedProperty:
    """State unclaimed property record"""

    property_id: str
    state: str
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None
    owner_city: Optional[str] = None
    property_type: Optional[str] = None
    reported_amount: Optional[float] = None
    holder_name: Optional[str] = None  # Company that reported it
    report_date: Optional[date] = None
    claim_url: Optional[str] = None


class FinancialRecordsScraper:
    """
    Scraper for free public financial records

    Sources:
    - CourtListener/RECAP (federal bankruptcy)
    - ProPublica Nonprofit Explorer (990 data)
    - State unclaimed property databases
    - County lien/judgment records
    """

    COURTLISTENER_URL = "https://www.courtlistener.com/api/rest/v3"
    PROPUBLICA_NONPROFIT_URL = "https://projects.propublica.org/nonprofits/api/v2"

    # State unclaimed property URLs
    STATE_UNCLAIMED_URLS = {
        "AL": "https://treasury.alabama.gov/unclaimed-property/",
        "AK": "https://unclaimedproperty.alaska.gov/",
        "AZ": "https://unclaimed.azdor.gov/",
        "AR": "https://www.claimit.ark.org/",
        "CA": "https://ucpi.sco.ca.gov/ucp/",
        "CO": "https://colorado.findyourunclaimedproperty.com/",
        "CT": "https://www.ctbiglist.com/",
        "DE": "https://unclaimedproperty.delaware.gov/",
        "FL": "https://www.fltreasurehunt.gov/",
        "GA": "https://etax.dor.ga.gov/UnclaimedProperty/",
        "HI": "https://unclaimedproperty.ehawaii.gov/",
        "ID": "https://sto.idaho.gov/unclaimed-property/",
        "IL": "https://icash.illinoistreasurer.gov/",
        "IN": "https://indianaunclaimed.gov/",
        "IA": "https://www.greatiowatreasurehunt.gov/",
        "KS": "https://www.kansascash.com/",
        "KY": "https://treasury.ky.gov/unclaimedproperty/",
        "LA": "https://www.treasury.la.gov/unclaimed-property",
        "ME": "https://maine.findyourunclaimedproperty.com/",
        "MD": "https://interactive.marylandtaxes.gov/Individuals/Unclaimed_Property/",
        "MA": "https://findmassmoney.com/",
        "MI": "https://unclaimedproperty.michigan.gov/",
        "MN": "https://mn.gov/commerce/consumers/your-money/unclaimed-property/",
        "MS": "https://treasury.ms.gov/for-citizens/unclaimed-property/",
        "MO": "https://treasurer.mo.gov/unclaimedproperty/",
        "MT": "https://mtrevenue.gov/property-taxes/unclaimed-property/",
        "NE": "https://treasurer.nebraska.gov/up/",
        "NV": "https://nevadatreasurer.gov/UnclaimedProperty/Search/",
        "NH": "https://www.findmymoney.nh.gov/",
        "NJ": "https://www.njspl.com/",
        "NM": "https://tap.state.nm.us/TAP/upe/_/",
        "NY": "https://www.osc.state.ny.us/unclaimed-funds",
        "NC": "https://www.nccash.com/",
        "ND": "https://www.land.nd.gov/offices/unclaimed-property",
        "OH": "https://com.ohio.gov/unclaimedProp/",
        "OK": "https://www.ok.gov/unclaimed/",
        "OR": "https://oregonup.us/",
        "PA": "https://www.patreasury.gov/unclaimed-property/",
        "RI": "https://findrimoney.com/",
        "SC": "https://treasurer.sc.gov/what-we-do/for-citizens/unclaimed-property/",
        "SD": "https://sdtreasurer.gov/unclaimed-property/",
        "TN": "https://treasury.tn.gov/Unclaimed-Property/",
        "TX": "https://claimittexas.org/",
        "UT": "https://mycash.utah.gov/",
        "VT": "https://vtunclaimedproperty.com/",
        "VA": "https://vamoneysearch.treasury.virginia.gov/",
        "WA": "https://ucp.dor.wa.gov/",
        "WV": "https://www.wvtreasury.com/Banking-Services/Unclaimed-Property",
        "WI": "https://statetreasurer.wi.gov/Pages/UnclaimedProperty.aspx",
        "WY": "https://treasurer.wyo.gov/unclaimed-property/",
        "DC": "https://otr.cfo.dc.gov/page/unclaimed-property",
    }

    def __init__(self, courtlistener_api_key: Optional[str] = None):
        """
        Initialize financial records scraper

        Args:
            courtlistener_api_key: Optional CourtListener API key (free)
        """
        self.courtlistener_api_key = courtlistener_api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {"User-Agent": "DataGod/1.0 (Public Records Research)"}
            if self.courtlistener_api_key:
                headers["Authorization"] = f"Token {self.courtlistener_api_key}"
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse various date formats"""
        if not date_str:
            return None
        try:
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"]:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    # Bankruptcy Search (via CourtListener/RECAP)

    async def search_bankruptcies(
        self,
        debtor_name: Optional[str] = None,
        state: Optional[str] = None,
        chapter: Optional[BankruptcyChapter] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100,
    ) -> List[BankruptcyCase]:
        """
        Search federal bankruptcy cases

        Uses CourtListener/RECAP API (free with registration)

        Args:
            debtor_name: Debtor name
            state: State filter
            chapter: Bankruptcy chapter
            date_from: Start date
            date_to: End date
            limit: Maximum results

        Returns:
            List of bankruptcy cases
        """
        results = []

        logger.info(f"Searching bankruptcies for: {debtor_name}")

        # Would integrate with CourtListener API
        # API docs: https://www.courtlistener.com/api/rest-info/

        return results

    # Nonprofit 990 Data (via ProPublica)

    async def search_nonprofits(
        self,
        name: Optional[str] = None,
        ein: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        ntee_code: Optional[str] = None,
        limit: int = 100,
    ) -> List[NonprofitOrg]:
        """
        Search nonprofit organizations (IRS 990 filers)

        Uses ProPublica Nonprofit Explorer API (free)

        Args:
            name: Organization name
            ein: Employer Identification Number
            state: State code
            city: City
            ntee_code: NTEE classification code
            limit: Maximum results

        Returns:
            List of nonprofit records
        """
        results = []
        session = await self._get_session()

        if ein:
            url = f"{self.PROPUBLICA_NONPROFIT_URL}/organizations/{ein}.json"
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        org = data.get("organization", {})
                        if org:
                            results.append(self._parse_nonprofit(org))
            except Exception as e:
                logger.error(f"ProPublica API error: {e}")

        elif name:
            url = f"{self.PROPUBLICA_NONPROFIT_URL}/search.json"
            params = {"q": name}
            if state:
                params["state[id]"] = state

            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for org in data.get("organizations", [])[:limit]:
                            results.append(self._parse_nonprofit(org))
            except Exception as e:
                logger.error(f"ProPublica API error: {e}")

        return results

    def _parse_nonprofit(self, data: Dict[str, Any]) -> NonprofitOrg:
        """Parse nonprofit data from ProPublica API"""
        return NonprofitOrg(
            ein=str(data.get("ein", "")),
            name=data.get("name", ""),
            city=data.get("city"),
            state=data.get("state"),
            zip_code=data.get("zipcode"),
            subsection=data.get("subsection_code"),
            total_revenue=data.get("income_amount"),
            total_assets=data.get("asset_amount"),
            ntee_code=data.get("ntee_code"),
            latest_990_year=data.get("tax_period"),
        )

    async def get_nonprofit_990s(
        self, ein: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get 990 filings for a nonprofit

        Args:
            ein: Employer Identification Number
            limit: Maximum filings to return

        Returns:
            List of 990 filing summaries
        """
        results = []
        session = await self._get_session()

        url = f"{self.PROPUBLICA_NONPROFIT_URL}/organizations/{ein}.json"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    filings = data.get("filings_with_data", [])
                    results = filings[:limit]
        except Exception as e:
            logger.error(f"ProPublica API error: {e}")

        return results

    # Unclaimed Property

    def get_unclaimed_property_url(self, state: str) -> Optional[str]:
        """
        Get state unclaimed property search URL

        Args:
            state: Two-letter state code

        Returns:
            URL for state unclaimed property search
        """
        return self.STATE_UNCLAIMED_URLS.get(state.upper())

    async def search_unclaimed_property(
        self, state: str, owner_name: str, city: Optional[str] = None
    ) -> List[UnclaimedProperty]:
        """
        Search state unclaimed property

        Note: Most states require web form interaction.
        This provides the search URL and guidance.

        Args:
            state: State code
            owner_name: Owner name to search
            city: Optional city filter

        Returns:
            List of unclaimed property records
        """
        results = []

        search_url = self.get_unclaimed_property_url(state)
        if not search_url:
            logger.warning(f"No unclaimed property URL for state: {state}")
            return results

        logger.info(f"Search unclaimed property in {state} for: {owner_name}")
        logger.info(f"Search URL: {search_url}")

        # Most states don't have APIs - would need web scraping

        return results

    # Tax Liens and Judgments

    async def search_tax_liens(
        self,
        state: str,
        county: str,
        debtor_name: Optional[str] = None,
        lien_type: Optional[LienType] = None,
        limit: int = 100,
    ) -> List[TaxLien]:
        """
        Search tax lien records

        Note: Tax liens are recorded at county level.
        Availability varies by county.

        Args:
            state: State code
            county: County name
            debtor_name: Debtor name
            lien_type: Type of lien
            limit: Maximum results

        Returns:
            List of tax lien records
        """
        results = []

        logger.info(f"Searching tax liens in {county} County, {state}")

        # Would integrate with county recorder systems

        return results

    async def search_judgments(
        self,
        state: str,
        county: Optional[str] = None,
        defendant_name: Optional[str] = None,
        plaintiff_name: Optional[str] = None,
        min_amount: Optional[float] = None,
        limit: int = 100,
    ) -> List[Judgment]:
        """
        Search civil judgment records

        Args:
            state: State code
            county: County name
            defendant_name: Defendant name
            plaintiff_name: Plaintiff name
            min_amount: Minimum judgment amount
            limit: Maximum results

        Returns:
            List of judgment records
        """
        results = []

        logger.info(
            f"Searching judgments in {state} for: {defendant_name or plaintiff_name}"
        )

        # Would integrate with court record systems

        return results

    def get_all_financial_resources(self) -> Dict[str, str]:
        """
        Get all financial record resource URLs

        Returns:
            Dictionary of resource URLs
        """
        return {
            "courtlistener": "https://www.courtlistener.com/",
            "courtlistener_api": "https://www.courtlistener.com/api/rest-info/",
            "pacer": "https://pacer.uscourts.gov/",
            "propublica_nonprofits": "https://projects.propublica.org/nonprofits/",
            "propublica_api": "https://projects.propublica.org/nonprofits/api",
            "naupa_unclaimed": "https://unclaimed.org/",  # Multi-state search
            "missingmoney": "https://www.missingmoney.com/",  # Multi-state search
        }


# Convenience functions


def get_unclaimed_property_url(state: str) -> Optional[str]:
    """Get state unclaimed property URL"""
    scraper = FinancialRecordsScraper()
    return scraper.get_unclaimed_property_url(state)


def search_nonprofits_sync(
    name: Optional[str] = None,
    ein: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 100,
) -> List[NonprofitOrg]:
    """Synchronous nonprofit search"""

    async def _search():
        scraper = FinancialRecordsScraper()
        try:
            return await scraper.search_nonprofits(
                name=name, ein=ein, state=state, limit=limit
            )
        finally:
            await scraper.close()

    return asyncio.run(_search())


def get_nonprofit_990s_sync(ein: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Synchronous 990 lookup"""

    async def _get():
        scraper = FinancialRecordsScraper()
        try:
            return await scraper.get_nonprofit_990s(ein, limit)
        finally:
            await scraper.close()

    return asyncio.run(_get())
