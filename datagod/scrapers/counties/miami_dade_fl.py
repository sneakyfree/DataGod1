"""
Miami-Dade County, Florida Scraper.

Covers property, recorder, and court records for Miami-Dade County.
Population: ~2.7 million (7th largest US county)
FIPS Code: 12086

Data Sources:
- Property Appraiser: https://www.miamidade.gov/pa/
- Clerk of Courts: https://www.miami-dadeclerk.com/
- Court Records: https://www.miami-dadeclerk.com/court-records.asp
- Tax Collector: https://www.miamidade.gov/taxcollector/
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp
from bs4 import BeautifulSoup

from .base_county_scraper import (
    BaseCountyScraper,
    CaseStatus,
    CaseType,
    CountyConfig,
    CourtCase,
    DeedRecord,
    LienRecord,
    MortgageRecord,
    PropertyRecord,
    RecordType,
    TaxRecord,
)

logger = logging.getLogger(__name__)

# Miami-Dade County configuration
MIAMI_DADE_COUNTY_CONFIG = CountyConfig(
    state="FL",
    county_name="Miami-Dade County",
    fips_code="12086",
    seat="Miami",
    population=2716940,
    assessor_url="https://www.miamidade.gov/pa/",
    recorder_url="https://www.miami-dadeclerk.com/oficialrecords/",
    clerk_url="https://www.miami-dadeclerk.com/",
    court_url="https://www.miami-dadeclerk.com/court-records.asp",
    treasurer_url="https://www.miamidade.gov/taxcollector/",
    gis_url="https://gisweb.miamidade.gov/",
)


class MiamiDadeCountyScraper(BaseCountyScraper):
    """
    Scraper for Miami-Dade County, Florida public records.

    Integrates with:
    - Miami-Dade Property Appraiser
    - Miami-Dade Clerk of Courts (Official Records)
    - Miami-Dade County Court System
    - Miami-Dade Tax Collector
    """

    def __init__(self, config: Optional[CountyConfig] = None):
        """Initialize Miami-Dade County scraper."""
        super().__init__(config or MIAMI_DADE_COUNTY_CONFIG)

        # API endpoints
        self.pa_api = "https://www.miamidade.gov/pa/api/"
        self.pa_search = "https://www.miamidade.gov/pa/property_search.asp"
        self.clerk_api = "https://www.miami-dadeclerk.com/api/"
        self.recorder_search = (
            "https://www.miami-dadeclerk.com/officialrecords/search.aspx"
        )
        self.court_search = "https://www.miami-dadeclerk.com/casesearch/"
        self.tax_api = "https://www.miamidade.gov/taxcollector/api/"

    async def _create_session(self) -> aiohttp.ClientSession:
        """Create aiohttp session with appropriate headers."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        return aiohttp.ClientSession(headers=headers)

    # ==================== Property Records ====================

    async def search_property_by_address(
        self, address: str, city: Optional[str] = None, zip_code: Optional[str] = None
    ) -> List[PropertyRecord]:
        """
        Search Miami-Dade Property Appraiser by address.
        """
        results = []

        try:
            async with await self._create_session() as session:
                params = {
                    "searchType": "address",
                    "address": address,
                }

                if city:
                    params["city"] = city
                if zip_code:
                    params["zip"] = zip_code

                url = self.pa_search

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        results_table = soup.find("table", {"id": "searchResults"})
                        if results_table:
                            for row in results_table.find_all("tr")[1:]:
                                cols = row.find_all("td")
                                if len(cols) >= 4:
                                    folio = cols[0].get_text(strip=True)
                                    prop_address = cols[1].get_text(strip=True)
                                    owner = cols[2].get_text(strip=True)
                                    prop_city = (
                                        cols[3].get_text(strip=True)
                                        if len(cols) > 3
                                        else city
                                    )

                                    record = PropertyRecord(
                                        parcel_id=folio,
                                        address=prop_address,
                                        city=prop_city or "Miami",
                                        state="FL",
                                        county="Miami-Dade",
                                        owner_name=owner,
                                        source_url=f"{self.config.assessor_url}property_search.asp?folio={folio}",
                                    )
                                    results.append(record)

        except Exception as e:
            logger.error(f"Error searching Miami-Dade property by address: {e}")

        return results

    async def search_property_by_owner(self, owner_name: str) -> List[PropertyRecord]:
        """
        Search Miami-Dade Property Appraiser by owner name.
        """
        results = []

        try:
            async with await self._create_session() as session:
                params = {
                    "searchType": "owner",
                    "owner": owner_name,
                }

                url = self.pa_search

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        results_table = soup.find("table", {"id": "searchResults"})
                        if results_table:
                            for row in results_table.find_all("tr")[1:]:
                                cols = row.find_all("td")
                                if len(cols) >= 3:
                                    folio = cols[0].get_text(strip=True)
                                    address = cols[1].get_text(strip=True)
                                    owner = cols[2].get_text(strip=True)

                                    record = PropertyRecord(
                                        parcel_id=folio,
                                        address=address,
                                        state="FL",
                                        county="Miami-Dade",
                                        owner_name=owner,
                                        source_url=f"{self.config.assessor_url}property_search.asp?folio={folio}",
                                    )
                                    results.append(record)

        except Exception as e:
            logger.error(f"Error searching Miami-Dade property by owner: {e}")

        return results

    async def search_property_by_parcel(
        self, parcel_id: str
    ) -> Optional[PropertyRecord]:
        """
        Get detailed property information by Folio Number.

        Miami-Dade uses Folio Numbers in format: XX-XXXX-XXX-XXXX
        """
        try:
            # Normalize folio (remove dashes)
            normalized_folio = parcel_id.replace("-", "").replace(" ", "")

            async with await self._create_session() as session:
                url = f"{self.config.assessor_url}property_search.asp"
                params = {"folio": normalized_folio}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        details = {}

                        # Owner section
                        owner_section = soup.find("div", {"id": "ownerInfo"})
                        if owner_section:
                            owner_name = owner_section.find("span", {"id": "ownerName"})
                            details["owner"] = (
                                owner_name.get_text(strip=True) if owner_name else None
                            )

                            mailing = owner_section.find(
                                "div", {"id": "mailingAddress"}
                            )
                            details["mailing_address"] = (
                                mailing.get_text(strip=True) if mailing else None
                            )

                        # Property address
                        addr_div = soup.find("div", {"id": "propertyAddress"})
                        address = addr_div.get_text(strip=True) if addr_div else None

                        # Valuation
                        value_section = soup.find("div", {"id": "assessment"})
                        if value_section:
                            land = value_section.find("span", {"id": "landValue"})
                            bldg = value_section.find("span", {"id": "buildingValue"})
                            total = value_section.find("span", {"id": "totalValue"})
                            market = value_section.find("span", {"id": "marketValue"})
                            assessed = value_section.find(
                                "span", {"id": "assessedValue"}
                            )

                            details["land_value"] = self._parse_currency(
                                land.get_text() if land else "0"
                            )
                            details["building_value"] = self._parse_currency(
                                bldg.get_text() if bldg else "0"
                            )
                            details["total_value"] = self._parse_currency(
                                total.get_text() if total else "0"
                            )
                            details["market_value"] = self._parse_currency(
                                market.get_text() if market else "0"
                            )
                            details["assessed_value"] = self._parse_currency(
                                assessed.get_text() if assessed else "0"
                            )

                        # Property characteristics
                        char_section = soup.find("div", {"id": "propertyInfo"})
                        if char_section:
                            year_built = char_section.find("span", {"id": "yearBuilt"})
                            sqft = char_section.find("span", {"id": "livingArea"})
                            lot_size = char_section.find("span", {"id": "lotSize"})
                            beds = char_section.find("span", {"id": "bedrooms"})
                            baths = char_section.find("span", {"id": "bathrooms"})
                            use = char_section.find("span", {"id": "useCode"})
                            zone = char_section.find("span", {"id": "zoning"})

                            details["year_built"] = self._parse_int(
                                year_built.get_text() if year_built else "0"
                            )
                            details["sqft"] = self._parse_int(
                                sqft.get_text() if sqft else "0"
                            )
                            details["lot_sqft"] = self._parse_int(
                                lot_size.get_text() if lot_size else "0"
                            )
                            details["bedrooms"] = self._parse_int(
                                beds.get_text() if beds else "0"
                            )
                            details["bathrooms"] = (
                                float(baths.get_text()) if baths else None
                            )
                            details["use_code"] = (
                                use.get_text(strip=True) if use else None
                            )
                            details["zoning"] = (
                                zone.get_text(strip=True) if zone else None
                            )

                        # Legal description
                        legal_div = soup.find("div", {"id": "legalDescription"})
                        details["legal_description"] = (
                            legal_div.get_text(strip=True) if legal_div else None
                        )

                        return PropertyRecord(
                            parcel_id=parcel_id,
                            address=address,
                            city=details.get("city", "Miami"),
                            state="FL",
                            county="Miami-Dade",
                            owner_name=details.get("owner"),
                            mailing_address=details.get("mailing_address"),
                            land_value=details.get("land_value", 0.0),
                            improvement_value=details.get("building_value", 0.0),
                            assessed_value=details.get("assessed_value", 0.0),
                            market_value=details.get("market_value", 0.0),
                            property_type=details.get("use_code"),
                            zoning=details.get("zoning"),
                            legal_description=details.get("legal_description"),
                            year_built=details.get("year_built"),
                            building_sqft=details.get("sqft"),
                            lot_sqft=details.get("lot_sqft"),
                            bedrooms=details.get("bedrooms"),
                            bathrooms=details.get("bathrooms"),
                            source_url=str(response.url),
                            raw_data=details,
                        )

        except Exception as e:
            logger.error(f"Error getting Miami-Dade property {parcel_id}: {e}")

        return None

    # ==================== Deed/Recorder Records ====================

    async def search_deeds_by_name(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        as_grantor: bool = True,
        as_grantee: bool = True,
    ) -> List[DeedRecord]:
        """
        Search Miami-Dade Clerk Official Records for deeds by party name.
        """
        results = []

        try:
            async with await self._create_session() as session:
                params = {
                    "name": name,
                    "docType": "DEED",
                }

                if start_date:
                    params["fromDate"] = start_date.strftime("%m/%d/%Y")
                if end_date:
                    params["toDate"] = end_date.strftime("%m/%d/%Y")
                if as_grantor and not as_grantee:
                    params["partyType"] = "1"  # Grantor
                elif as_grantee and not as_grantor:
                    params["partyType"] = "2"  # Grantee

                url = self.recorder_search

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        results_table = soup.find("table", {"id": "resultsGrid"})
                        if results_table:
                            for row in results_table.find_all("tr")[1:]:
                                cols = row.find_all("td")
                                if len(cols) >= 6:
                                    cfn = cols[0].get_text(
                                        strip=True
                                    )  # Clerk File Number
                                    doc_type = cols[1].get_text(strip=True)
                                    rec_date = cols[2].get_text(strip=True)
                                    grantor = cols[3].get_text(strip=True)
                                    grantee = cols[4].get_text(strip=True)
                                    consideration = (
                                        cols[5].get_text(strip=True)
                                        if len(cols) > 5
                                        else "0"
                                    )

                                    record = DeedRecord(
                                        document_number=cfn,
                                        record_type=doc_type,
                                        recording_date=self._parse_date(rec_date),
                                        grantor=grantor,
                                        grantee=grantee,
                                        consideration=self._parse_currency(
                                            consideration
                                        ),
                                        county="Miami-Dade",
                                        state="FL",
                                        source_url=f"{self.config.recorder_url}document.aspx?cfn={cfn}",
                                    )
                                    results.append(record)

        except Exception as e:
            logger.error(f"Error searching Miami-Dade deeds by name: {e}")

        return results

    async def search_deeds_by_parcel(
        self,
        parcel_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[DeedRecord]:
        """Search recorder by folio number."""
        results = []

        try:
            async with await self._create_session() as session:
                params = {
                    "folio": parcel_id.replace("-", ""),
                }

                if start_date:
                    params["fromDate"] = start_date.strftime("%m/%d/%Y")
                if end_date:
                    params["toDate"] = end_date.strftime("%m/%d/%Y")

                url = self.recorder_search

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        results_table = soup.find("table", {"id": "resultsGrid"})
                        if results_table:
                            for row in results_table.find_all("tr")[1:]:
                                cols = row.find_all("td")
                                if len(cols) >= 5:
                                    record = DeedRecord(
                                        document_number=cols[0].get_text(strip=True),
                                        record_type=cols[1].get_text(strip=True),
                                        recording_date=self._parse_date(
                                            cols[2].get_text(strip=True)
                                        ),
                                        grantor=cols[3].get_text(strip=True),
                                        grantee=cols[4].get_text(strip=True),
                                        parcel_id=parcel_id,
                                        county="Miami-Dade",
                                        state="FL",
                                        source_url=f"{self.config.recorder_url}document.aspx?cfn={cols[0].get_text(strip=True)}",
                                    )
                                    results.append(record)

        except Exception as e:
            logger.error(f"Error searching Miami-Dade deeds by parcel: {e}")

        return results

    async def search_mortgages(
        self,
        name: Optional[str] = None,
        parcel_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[MortgageRecord]:
        """Search for mortgage records (Florida uses Mortgages, not Deeds of Trust)."""
        results = []

        try:
            async with await self._create_session() as session:
                params = {
                    "docType": "MORTGAGE",
                }

                if name:
                    params["name"] = name
                if parcel_id:
                    params["folio"] = parcel_id.replace("-", "")
                if start_date:
                    params["fromDate"] = start_date.strftime("%m/%d/%Y")
                if end_date:
                    params["toDate"] = end_date.strftime("%m/%d/%Y")

                url = self.recorder_search

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        results_table = soup.find("table", {"id": "resultsGrid"})
                        if results_table:
                            for row in results_table.find_all("tr")[1:]:
                                cols = row.find_all("td")
                                if len(cols) >= 6:
                                    record = MortgageRecord(
                                        document_number=cols[0].get_text(strip=True),
                                        record_type="MORTGAGE",
                                        recording_date=self._parse_date(
                                            cols[2].get_text(strip=True)
                                        ),
                                        mortgagor=cols[3].get_text(
                                            strip=True
                                        ),  # Borrower
                                        mortgagee=cols[4].get_text(
                                            strip=True
                                        ),  # Lender
                                        loan_amount=self._parse_currency(
                                            cols[5].get_text(strip=True)
                                        ),
                                        parcel_id=parcel_id,
                                        county="Miami-Dade",
                                        state="FL",
                                        source_url=f"{self.config.recorder_url}document.aspx?cfn={cols[0].get_text(strip=True)}",
                                    )
                                    results.append(record)

        except Exception as e:
            logger.error(f"Error searching Miami-Dade mortgages: {e}")

        return results

    async def search_liens(
        self,
        name: Optional[str] = None,
        parcel_id: Optional[str] = None,
        lien_type: Optional[str] = None,
    ) -> List[LienRecord]:
        """Search for lien records."""
        results = []

        try:
            async with await self._create_session() as session:
                lien_types = [
                    "LIEN",
                    "TAX LIEN",
                    "CONSTRUCTION LIEN",
                    "JUDGMENT",
                    "LIS PENDENS",
                ]

                for lt in lien_types:
                    if lien_type and lien_type.upper() not in lt:
                        continue

                    params = {"docType": lt}
                    if name:
                        params["name"] = name
                    if parcel_id:
                        params["folio"] = parcel_id.replace("-", "")

                    url = self.recorder_search

                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, "html.parser")

                            results_table = soup.find("table", {"id": "resultsGrid"})
                            if results_table:
                                for row in results_table.find_all("tr")[1:]:
                                    cols = row.find_all("td")
                                    if len(cols) >= 5:
                                        record = LienRecord(
                                            document_number=cols[0].get_text(
                                                strip=True
                                            ),
                                            lien_type=lt,
                                            recording_date=self._parse_date(
                                                cols[2].get_text(strip=True)
                                            ),
                                            debtor=cols[3].get_text(strip=True),
                                            creditor=cols[4].get_text(strip=True),
                                            amount=(
                                                self._parse_currency(
                                                    cols[5].get_text(strip=True)
                                                )
                                                if len(cols) > 5
                                                else 0.0
                                            ),
                                            parcel_id=parcel_id,
                                            county="Miami-Dade",
                                            state="FL",
                                            source_url=f"{self.config.recorder_url}document.aspx?cfn={cols[0].get_text(strip=True)}",
                                        )
                                        results.append(record)

                    await asyncio.sleep(self.rate_limit_delay)

        except Exception as e:
            logger.error(f"Error searching Miami-Dade liens: {e}")

        return results

    # ==================== Court Records ====================

    async def search_court_cases_by_name(
        self,
        name: str,
        case_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CourtCase]:
        """
        Search Miami-Dade Clerk court cases by party name.

        Case types: Civil, Criminal, Family, Probate, Juvenile, Traffic
        """
        results = []

        try:
            async with await self._create_session() as session:
                params = {
                    "partyName": name,
                }

                if case_type:
                    params["caseType"] = case_type
                if start_date:
                    params["startDate"] = start_date.strftime("%m/%d/%Y")
                if end_date:
                    params["endDate"] = end_date.strftime("%m/%d/%Y")

                url = self.court_search

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        results_table = soup.find("table", {"id": "caseResults"})
                        if results_table:
                            for row in results_table.find_all("tr")[1:]:
                                cols = row.find_all("td")
                                if len(cols) >= 5:
                                    case_number = cols[0].get_text(strip=True)
                                    case_title = cols[1].get_text(strip=True)
                                    filing_date = cols[2].get_text(strip=True)
                                    ct = cols[3].get_text(strip=True)
                                    status = cols[4].get_text(strip=True)

                                    # Parse parties from title
                                    plaintiff = None
                                    defendant = None
                                    if " vs " in case_title.lower():
                                        parts = case_title.lower().split(" vs ")
                                        plaintiff = parts[0].strip().title()
                                        defendant = (
                                            parts[1].strip().title()
                                            if len(parts) > 1
                                            else None
                                        )
                                    elif " v " in case_title.lower():
                                        parts = case_title.lower().split(" v ")
                                        plaintiff = parts[0].strip().title()
                                        defendant = (
                                            parts[1].strip().title()
                                            if len(parts) > 1
                                            else None
                                        )

                                    record = CourtCase(
                                        case_number=case_number,
                                        case_type=ct,
                                        case_title=case_title,
                                        filing_date=self._parse_date(filing_date),
                                        plaintiff=plaintiff,
                                        defendant=defendant,
                                        status=status,
                                        court="Miami-Dade County Court",
                                        county="Miami-Dade",
                                        state="FL",
                                        source_url=f"{self.court_search}case.aspx?caseNumber={case_number}",
                                    )
                                    results.append(record)

        except Exception as e:
            logger.error(f"Error searching Miami-Dade court cases: {e}")

        return results

    async def search_court_cases_by_case_number(
        self, case_number: str
    ) -> Optional[CourtCase]:
        """Get detailed case information by case number."""
        try:
            async with await self._create_session() as session:
                url = f"{self.court_search}case.aspx"
                params = {"caseNumber": case_number}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        details = {}

                        # Case header
                        case_title = soup.find("h1", class_="caseTitle")
                        details["title"] = (
                            case_title.get_text(strip=True) if case_title else None
                        )

                        # Case info
                        info_div = soup.find("div", {"id": "caseInfo"})
                        if info_div:
                            for row in info_div.find_all("div", class_="infoRow"):
                                label = row.find("span", class_="label")
                                value = row.find("span", class_="value")
                                if label and value:
                                    key = (
                                        label.get_text(strip=True)
                                        .lower()
                                        .replace(" ", "_")
                                        .replace(":", "")
                                    )
                                    details[key] = value.get_text(strip=True)

                        # Parties
                        parties_div = soup.find("div", {"id": "parties"})
                        if parties_div:
                            plaintiff = parties_div.find("div", class_="plaintiff")
                            defendant = parties_div.find("div", class_="defendant")
                            details["plaintiff"] = (
                                plaintiff.get_text(strip=True) if plaintiff else None
                            )
                            details["defendant"] = (
                                defendant.get_text(strip=True) if defendant else None
                            )

                        # Docket
                        docket_entries = []
                        docket_table = soup.find("table", {"id": "docketTable"})
                        if docket_table:
                            for row in docket_table.find_all("tr")[1:]:
                                cols = row.find_all("td")
                                if len(cols) >= 2:
                                    docket_entries.append(
                                        {
                                            "date": cols[0].get_text(strip=True),
                                            "entry": cols[1].get_text(strip=True),
                                        }
                                    )

                        return CourtCase(
                            case_number=case_number,
                            case_type=details.get("case_type", ""),
                            case_title=details.get("title", ""),
                            filing_date=self._parse_date(details.get("filing_date")),
                            plaintiff=details.get("plaintiff"),
                            defendant=details.get("defendant"),
                            status=details.get("status", ""),
                            judge=details.get("judge"),
                            court="Miami-Dade County Court",
                            county="Miami-Dade",
                            state="FL",
                            source_url=str(response.url),
                            docket_entries=docket_entries,
                            raw_data=details,
                        )

        except Exception as e:
            logger.error(f"Error getting Miami-Dade court case {case_number}: {e}")

        return None

    async def search_civil_cases(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CourtCase]:
        """Search civil cases."""
        return await self.search_court_cases_by_name(
            name=name, case_type="CA", start_date=start_date, end_date=end_date  # Civil
        )

    async def search_family_cases(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CourtCase]:
        """Search family court cases."""
        return await self.search_court_cases_by_name(
            name=name,
            case_type="DR",  # Domestic Relations
            start_date=start_date,
            end_date=end_date,
        )

    async def search_probate_cases(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CourtCase]:
        """Search probate cases."""
        return await self.search_court_cases_by_name(
            name=name,
            case_type="CP",  # Probate
            start_date=start_date,
            end_date=end_date,
        )

    async def search_eviction_cases(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CourtCase]:
        """Search eviction cases (Florida specific)."""
        return await self.search_court_cases_by_name(
            name=name,
            case_type="CC",  # County Civil (includes evictions)
            start_date=start_date,
            end_date=end_date,
        )

    # ==================== Tax Records ====================

    async def search_tax_records(
        self, parcel_id: str, tax_year: Optional[int] = None
    ) -> List[TaxRecord]:
        """
        Search Miami-Dade Tax Collector for tax records.
        """
        results = []

        try:
            normalized_folio = parcel_id.replace("-", "").replace(" ", "")

            async with await self._create_session() as session:
                url = f"{self.config.treasurer_url}search.asp"
                params = {"folio": normalized_folio}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Parse tax information
                        tax_table = soup.find("table", {"id": "taxBills"})
                        if tax_table:
                            for row in tax_table.find_all("tr")[1:]:
                                cols = row.find_all("td")
                                if len(cols) >= 5:
                                    year = self._parse_int(cols[0].get_text(strip=True))
                                    if tax_year and year != tax_year:
                                        continue

                                    record = TaxRecord(
                                        parcel_id=parcel_id,
                                        tax_year=year,
                                        assessed_value=self._parse_currency(
                                            cols[1].get_text(strip=True)
                                        ),
                                        tax_amount=self._parse_currency(
                                            cols[2].get_text(strip=True)
                                        ),
                                        amount_paid=self._parse_currency(
                                            cols[3].get_text(strip=True)
                                        ),
                                        amount_due=self._parse_currency(
                                            cols[4].get_text(strip=True)
                                        ),
                                        status=(
                                            cols[5].get_text(strip=True)
                                            if len(cols) > 5
                                            else ""
                                        ),
                                        county="Miami-Dade",
                                        state="FL",
                                        source_url=str(response.url),
                                    )
                                    results.append(record)

        except Exception as e:
            logger.error(f"Error searching Miami-Dade tax records: {e}")

        return results

    # ==================== Helper Methods ====================

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse various date formats."""
        if not date_str:
            return None

        formats = [
            "%m/%d/%Y",
            "%Y-%m-%d",
            "%m-%d-%Y",
            "%B %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        return None

    def _parse_currency(self, value: str) -> float:
        """Parse currency string to float."""
        if not value:
            return 0.0
        try:
            cleaned = value.replace("$", "").replace(",", "").strip()
            return float(cleaned)
        except ValueError:
            return 0.0

    def _parse_int(self, value: str) -> int:
        """Parse integer from string."""
        if not value:
            return 0
        try:
            cleaned = value.replace(",", "").strip()
            return int(float(cleaned))
        except ValueError:
            return 0


# Synchronous wrapper functions
def search_property_by_address(
    address: str, city: Optional[str] = None, zip_code: Optional[str] = None
) -> List[PropertyRecord]:
    """Synchronous wrapper for property search by address."""
    scraper = MiamiDadeCountyScraper()
    return asyncio.run(scraper.search_property_by_address(address, city, zip_code))


def search_property_by_owner(owner_name: str) -> List[PropertyRecord]:
    """Synchronous wrapper for property search by owner."""
    scraper = MiamiDadeCountyScraper()
    return asyncio.run(scraper.search_property_by_owner(owner_name))


def search_deeds_by_name(
    name: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[DeedRecord]:
    """Synchronous wrapper for deed search."""
    scraper = MiamiDadeCountyScraper()
    return asyncio.run(scraper.search_deeds_by_name(name, start_date, end_date))


def search_court_cases(name: str, case_type: Optional[str] = None) -> List[CourtCase]:
    """Synchronous wrapper for court case search."""
    scraper = MiamiDadeCountyScraper()
    return asyncio.run(scraper.search_court_cases_by_name(name, case_type))


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    async def main():
        scraper = MiamiDadeCountyScraper()

        print(f"Miami-Dade County Scraper - {scraper.config.county_name}")
        print(f"FIPS: {scraper.config.fips_code}")
        print(f"Population: {scraper.config.population:,}")
        print(f"County Seat: {scraper.config.seat}")
        print()

        if len(sys.argv) > 1:
            query = sys.argv[1]
            print(f"Searching for: {query}")

            properties = await scraper.search_property_by_address(query)
            print(f"\nFound {len(properties)} properties")
            for prop in properties[:3]:
                print(f"  - {prop.parcel_id}: {prop.address} ({prop.owner_name})")

    asyncio.run(main())
