"""
Maricopa County, Arizona Scraper.

Covers property, recorder, and court records for Maricopa County (Phoenix).
Population: ~4.4 million (4th largest US county)
FIPS Code: 04013

Data Sources:
- Assessor: https://mcassessor.maricopa.gov/
- Recorder: https://recorder.maricopa.gov/
- Superior Court: https://superiorcourt.maricopa.gov/
- Treasurer: https://treasurer.maricopa.gov/
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
    CountyConfig,
    PropertyRecord,
    DeedRecord,
    MortgageRecord,
    TaxRecord,
    CourtCase,
    LienRecord,
    RecordType,
    CaseType,
    CaseStatus,
)

logger = logging.getLogger(__name__)

# Maricopa County configuration
MARICOPA_COUNTY_CONFIG = CountyConfig(
    state="AZ",
    county_name="Maricopa County",
    fips_code="04013",
    seat="Phoenix",
    population=4420568,
    assessor_url="https://mcassessor.maricopa.gov/",
    recorder_url="https://recorder.maricopa.gov/",
    clerk_url="https://clerkofcourt.maricopa.gov/",
    court_url="https://superiorcourt.maricopa.gov/",
    treasurer_url="https://treasurer.maricopa.gov/",
    gis_url="https://gis.maricopa.gov/",
)


class MaricopaCountyScraper(BaseCountyScraper):
    """
    Scraper for Maricopa County, Arizona public records.

    Integrates with:
    - Maricopa County Assessor (property valuations)
    - Maricopa County Recorder (deeds, mortgages, liens)
    - Maricopa County Superior Court (civil, criminal, family cases)
    - Maricopa County Treasurer (tax records)
    """

    def __init__(self, config: Optional[CountyConfig] = None):
        """Initialize Maricopa County scraper."""
        super().__init__(config or MARICOPA_COUNTY_CONFIG)

        # API endpoints
        self.assessor_api = "https://mcassessor.maricopa.gov/mcs/api/"
        self.recorder_search = "https://recorder.maricopa.gov/recdocdata/"
        self.court_search = "https://superiorcourt.maricopa.gov/docket/"
        self.treasurer_api = "https://treasurer.maricopa.gov/Parcel/api/"

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
        self,
        address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None
    ) -> List[PropertyRecord]:
        """
        Search Maricopa County Assessor by address.

        Uses the assessor's parcel search API.
        """
        results = []

        try:
            async with await self._create_session() as session:
                # Build search query
                search_address = address
                if city:
                    search_address += f", {city}"
                if zip_code:
                    search_address += f" {zip_code}"

                params = {
                    "address": search_address,
                    "searchType": "address",
                }

                url = f"{self.assessor_api}parcel/search"

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        for parcel in data.get("parcels", []):
                            record = await self._parse_assessor_parcel(parcel)
                            if record:
                                results.append(record)
                    else:
                        # Fallback to HTML scraping
                        results = await self._scrape_assessor_address(session, address, city, zip_code)

        except Exception as e:
            logger.error(f"Error searching Maricopa property by address: {e}")

        return results

    async def _scrape_assessor_address(
        self,
        session: aiohttp.ClientSession,
        address: str,
        city: Optional[str],
        zip_code: Optional[str]
    ) -> List[PropertyRecord]:
        """Scrape assessor website for property by address."""
        results = []

        try:
            search_url = f"{self.config.assessor_url}?s={address}"

            async with session.get(search_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Parse search results table
                    for row in soup.select("table.results tr")[1:]:  # Skip header
                        cols = row.find_all("td")
                        if len(cols) >= 4:
                            parcel_link = cols[0].find("a")
                            if parcel_link:
                                parcel_id = parcel_link.get_text(strip=True)
                                parcel_address = cols[1].get_text(strip=True)
                                owner = cols[2].get_text(strip=True)

                                record = PropertyRecord(
                                    parcel_id=parcel_id,
                                    address=parcel_address,
                                    city=city or "Phoenix",
                                    state="AZ",
                                    county="Maricopa",
                                    owner_name=owner,
                                    source_url=f"{self.config.assessor_url}parcel/{parcel_id}",
                                    raw_data={"scraped": True},
                                )
                                results.append(record)

        except Exception as e:
            logger.error(f"Error scraping Maricopa assessor: {e}")

        return results

    async def search_property_by_owner(self, owner_name: str) -> List[PropertyRecord]:
        """
        Search Maricopa County Assessor by owner name.
        """
        results = []

        try:
            async with await self._create_session() as session:
                params = {
                    "owner": owner_name,
                    "searchType": "owner",
                }

                url = f"{self.assessor_api}parcel/search"

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        for parcel in data.get("parcels", []):
                            record = await self._parse_assessor_parcel(parcel)
                            if record:
                                results.append(record)
                    else:
                        # Fallback to scraping
                        search_url = f"{self.config.assessor_url}?owner={owner_name}"
                        async with session.get(search_url) as resp:
                            if resp.status == 200:
                                html = await resp.text()
                                soup = BeautifulSoup(html, "html.parser")

                                for row in soup.select("table.results tr")[1:]:
                                    cols = row.find_all("td")
                                    if len(cols) >= 3:
                                        parcel_id = cols[0].get_text(strip=True)
                                        address = cols[1].get_text(strip=True)

                                        record = PropertyRecord(
                                            parcel_id=parcel_id,
                                            address=address,
                                            state="AZ",
                                            county="Maricopa",
                                            owner_name=owner_name,
                                            source_url=f"{self.config.assessor_url}parcel/{parcel_id}",
                                        )
                                        results.append(record)

        except Exception as e:
            logger.error(f"Error searching Maricopa property by owner: {e}")

        return results

    async def search_property_by_parcel(self, parcel_id: str) -> Optional[PropertyRecord]:
        """
        Get detailed property information by APN (Assessor's Parcel Number).

        Maricopa APNs are in format: XXX-XX-XXX or XXXXXXXXX
        """
        try:
            # Normalize parcel ID (remove dashes)
            normalized_apn = parcel_id.replace("-", "").replace(" ", "")

            async with await self._create_session() as session:
                url = f"{self.assessor_api}parcel/{normalized_apn}"

                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return await self._parse_assessor_detail(data)
                    else:
                        # Scrape detail page
                        return await self._scrape_parcel_detail(session, parcel_id)

        except Exception as e:
            logger.error(f"Error getting Maricopa parcel {parcel_id}: {e}")

        return None

    async def _scrape_parcel_detail(
        self,
        session: aiohttp.ClientSession,
        parcel_id: str
    ) -> Optional[PropertyRecord]:
        """Scrape detailed parcel information from assessor website."""
        try:
            url = f"{self.config.assessor_url}parcel/{parcel_id}"

            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Extract property details
                    details = {}

                    # Owner information section
                    owner_section = soup.find("div", class_="owner-info")
                    if owner_section:
                        owner_name = owner_section.find("span", class_="owner-name")
                        details["owner"] = owner_name.get_text(strip=True) if owner_name else None

                        mailing = owner_section.find("span", class_="mailing-address")
                        details["mailing_address"] = mailing.get_text(strip=True) if mailing else None

                    # Property address
                    addr_elem = soup.find("span", class_="property-address")
                    address = addr_elem.get_text(strip=True) if addr_elem else None

                    # Valuation section
                    value_section = soup.find("div", class_="valuation")
                    if value_section:
                        fcv = value_section.find("span", {"data-field": "fcv"})
                        lcv = value_section.find("span", {"data-field": "lcv"})
                        details["full_cash_value"] = self._parse_currency(fcv.get_text() if fcv else "0")
                        details["limited_value"] = self._parse_currency(lcv.get_text() if lcv else "0")

                    # Property characteristics
                    char_section = soup.find("div", class_="characteristics")
                    if char_section:
                        year_built = char_section.find("span", {"data-field": "year-built"})
                        sqft = char_section.find("span", {"data-field": "sqft"})
                        lot_size = char_section.find("span", {"data-field": "lot-size"})

                        details["year_built"] = int(year_built.get_text()) if year_built else None
                        details["sqft"] = int(sqft.get_text().replace(",", "")) if sqft else None
                        details["lot_sqft"] = int(lot_size.get_text().replace(",", "")) if lot_size else None

                    return PropertyRecord(
                        parcel_id=parcel_id,
                        address=address,
                        city=details.get("city", "Phoenix"),
                        state="AZ",
                        county="Maricopa",
                        owner_name=details.get("owner"),
                        mailing_address=details.get("mailing_address"),
                        assessed_value=details.get("limited_value", 0.0),
                        market_value=details.get("full_cash_value", 0.0),
                        year_built=details.get("year_built"),
                        building_sqft=details.get("sqft"),
                        lot_sqft=details.get("lot_sqft"),
                        source_url=url,
                        raw_data=details,
                    )

        except Exception as e:
            logger.error(f"Error scraping Maricopa parcel detail: {e}")

        return None

    async def _parse_assessor_parcel(self, data: Dict[str, Any]) -> Optional[PropertyRecord]:
        """Parse assessor API parcel data into PropertyRecord."""
        try:
            return PropertyRecord(
                parcel_id=data.get("apn", data.get("parcelId", "")),
                address=data.get("situsAddress", data.get("address", "")),
                city=data.get("situsCity", "Phoenix"),
                state="AZ",
                county="Maricopa",
                zip_code=data.get("situsZip"),
                owner_name=data.get("ownerName", data.get("owner", "")),
                assessed_value=float(data.get("limitedValue", 0)),
                market_value=float(data.get("fullCashValue", 0)),
                land_value=float(data.get("landValue", 0)),
                improvement_value=float(data.get("improvementValue", 0)),
                property_class=data.get("propertyClass"),
                legal_description=data.get("legalDescription"),
                source_url=f"{self.config.assessor_url}parcel/{data.get('apn', '')}",
                raw_data=data,
            )
        except Exception as e:
            logger.error(f"Error parsing Maricopa assessor parcel: {e}")
            return None

    async def _parse_assessor_detail(self, data: Dict[str, Any]) -> Optional[PropertyRecord]:
        """Parse detailed assessor API response."""
        try:
            parcel = data.get("parcel", data)

            return PropertyRecord(
                parcel_id=parcel.get("apn", ""),
                address=parcel.get("situsAddress", ""),
                city=parcel.get("situsCity", "Phoenix"),
                state="AZ",
                county="Maricopa",
                zip_code=parcel.get("situsZip"),
                owner_name=parcel.get("ownerName", ""),
                mailing_address=parcel.get("mailingAddress"),
                assessed_value=float(parcel.get("limitedValue", 0)),
                market_value=float(parcel.get("fullCashValue", 0)),
                land_value=float(parcel.get("landValue", 0)),
                improvement_value=float(parcel.get("improvementValue", 0)),
                tax_amount=float(parcel.get("taxAmount", 0)),
                tax_year=parcel.get("taxYear"),
                property_class=parcel.get("propertyClass"),
                property_type=parcel.get("propertyUse"),
                legal_description=parcel.get("legalDescription"),
                subdivision=parcel.get("subdivision"),
                year_built=parcel.get("yearBuilt"),
                building_sqft=parcel.get("buildingSqFt"),
                lot_sqft=parcel.get("lotSqFt"),
                lot_acres=parcel.get("lotAcres"),
                bedrooms=parcel.get("bedrooms"),
                bathrooms=parcel.get("bathrooms"),
                stories=parcel.get("stories"),
                pool=parcel.get("hasPool", False),
                source_url=f"{self.config.assessor_url}parcel/{parcel.get('apn', '')}",
                raw_data=data,
            )
        except Exception as e:
            logger.error(f"Error parsing Maricopa assessor detail: {e}")
            return None

    # ==================== Deed/Recorder Records ====================

    async def search_deeds_by_name(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        as_grantor: bool = True,
        as_grantee: bool = True
    ) -> List[DeedRecord]:
        """
        Search Maricopa County Recorder for deeds by party name.

        The recorder's office maintains records of deeds, mortgages, liens,
        releases, and other recorded documents.
        """
        results = []

        try:
            async with await self._create_session() as session:
                # Build search parameters
                params = {
                    "name": name,
                    "docType": "DEED",
                }

                if start_date:
                    params["startDate"] = start_date.strftime("%m/%d/%Y")
                if end_date:
                    params["endDate"] = end_date.strftime("%m/%d/%Y")
                if as_grantor and not as_grantee:
                    params["party"] = "grantor"
                elif as_grantee and not as_grantor:
                    params["party"] = "grantee"

                url = f"{self.recorder_search}search"

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Parse results table
                        for row in soup.select("table#searchResults tr")[1:]:
                            cols = row.find_all("td")
                            if len(cols) >= 6:
                                doc_num = cols[0].get_text(strip=True)
                                doc_type = cols[1].get_text(strip=True)
                                rec_date = cols[2].get_text(strip=True)
                                grantor = cols[3].get_text(strip=True)
                                grantee = cols[4].get_text(strip=True)
                                consideration = cols[5].get_text(strip=True)

                                record = DeedRecord(
                                    document_number=doc_num,
                                    record_type=doc_type,
                                    recording_date=self._parse_date(rec_date),
                                    grantor=grantor,
                                    grantee=grantee,
                                    consideration=self._parse_currency(consideration),
                                    county="Maricopa",
                                    state="AZ",
                                    source_url=f"{self.config.recorder_url}document/{doc_num}",
                                    raw_data={"columns": [c.get_text(strip=True) for c in cols]},
                                )
                                results.append(record)

        except Exception as e:
            logger.error(f"Error searching Maricopa deeds by name: {e}")

        return results

    async def search_deeds_by_parcel(
        self,
        parcel_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[DeedRecord]:
        """Search recorder by parcel number."""
        results = []

        try:
            async with await self._create_session() as session:
                params = {
                    "apn": parcel_id.replace("-", ""),
                }

                if start_date:
                    params["startDate"] = start_date.strftime("%m/%d/%Y")
                if end_date:
                    params["endDate"] = end_date.strftime("%m/%d/%Y")

                url = f"{self.recorder_search}parcelsearch"

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        for row in soup.select("table#searchResults tr")[1:]:
                            cols = row.find_all("td")
                            if len(cols) >= 5:
                                record = DeedRecord(
                                    document_number=cols[0].get_text(strip=True),
                                    record_type=cols[1].get_text(strip=True),
                                    recording_date=self._parse_date(cols[2].get_text(strip=True)),
                                    grantor=cols[3].get_text(strip=True),
                                    grantee=cols[4].get_text(strip=True),
                                    parcel_id=parcel_id,
                                    county="Maricopa",
                                    state="AZ",
                                    source_url=f"{self.config.recorder_url}document/{cols[0].get_text(strip=True)}",
                                )
                                results.append(record)

        except Exception as e:
            logger.error(f"Error searching Maricopa deeds by parcel: {e}")

        return results

    async def search_mortgages(
        self,
        name: Optional[str] = None,
        parcel_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[MortgageRecord]:
        """Search for mortgage records in Maricopa County."""
        results = []

        try:
            async with await self._create_session() as session:
                params = {
                    "docType": "DEED OF TRUST",  # Arizona uses Deeds of Trust
                }

                if name:
                    params["name"] = name
                if parcel_id:
                    params["apn"] = parcel_id.replace("-", "")
                if start_date:
                    params["startDate"] = start_date.strftime("%m/%d/%Y")
                if end_date:
                    params["endDate"] = end_date.strftime("%m/%d/%Y")

                url = f"{self.recorder_search}search"

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        for row in soup.select("table#searchResults tr")[1:]:
                            cols = row.find_all("td")
                            if len(cols) >= 6:
                                record = MortgageRecord(
                                    document_number=cols[0].get_text(strip=True),
                                    record_type="DEED OF TRUST",
                                    recording_date=self._parse_date(cols[2].get_text(strip=True)),
                                    trustor=cols[3].get_text(strip=True),  # Borrower
                                    beneficiary=cols[4].get_text(strip=True),  # Lender
                                    loan_amount=self._parse_currency(cols[5].get_text(strip=True)),
                                    parcel_id=parcel_id,
                                    county="Maricopa",
                                    state="AZ",
                                    source_url=f"{self.config.recorder_url}document/{cols[0].get_text(strip=True)}",
                                )
                                results.append(record)

        except Exception as e:
            logger.error(f"Error searching Maricopa mortgages: {e}")

        return results

    async def search_liens(
        self,
        name: Optional[str] = None,
        parcel_id: Optional[str] = None,
        lien_type: Optional[str] = None
    ) -> List[LienRecord]:
        """Search for liens in Maricopa County Recorder."""
        results = []

        try:
            async with await self._create_session() as session:
                # Lien document types
                lien_types = ["LIEN", "TAX LIEN", "MECHANICS LIEN", "JUDGMENT LIEN"]

                for lt in lien_types:
                    if lien_type and lien_type.upper() not in lt:
                        continue

                    params = {"docType": lt}
                    if name:
                        params["name"] = name
                    if parcel_id:
                        params["apn"] = parcel_id.replace("-", "")

                    url = f"{self.recorder_search}search"

                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, "html.parser")

                            for row in soup.select("table#searchResults tr")[1:]:
                                cols = row.find_all("td")
                                if len(cols) >= 5:
                                    record = LienRecord(
                                        document_number=cols[0].get_text(strip=True),
                                        lien_type=lt,
                                        recording_date=self._parse_date(cols[2].get_text(strip=True)),
                                        debtor=cols[3].get_text(strip=True),
                                        creditor=cols[4].get_text(strip=True),
                                        amount=self._parse_currency(cols[5].get_text(strip=True)) if len(cols) > 5 else 0.0,
                                        parcel_id=parcel_id,
                                        county="Maricopa",
                                        state="AZ",
                                        source_url=f"{self.config.recorder_url}document/{cols[0].get_text(strip=True)}",
                                    )
                                    results.append(record)

                    await asyncio.sleep(self.rate_limit_delay)

        except Exception as e:
            logger.error(f"Error searching Maricopa liens: {e}")

        return results

    # ==================== Court Records ====================

    async def search_court_cases_by_name(
        self,
        name: str,
        case_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CourtCase]:
        """
        Search Maricopa County Superior Court cases by party name.

        Case types include: Civil, Criminal, Family, Probate, Tax
        """
        results = []

        try:
            async with await self._create_session() as session:
                params = {
                    "party": name,
                }

                if case_type:
                    params["caseType"] = case_type.upper()
                if start_date:
                    params["startDate"] = start_date.strftime("%m/%d/%Y")
                if end_date:
                    params["endDate"] = end_date.strftime("%m/%d/%Y")

                url = f"{self.court_search}search"

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        for row in soup.select("table.caseResults tr")[1:]:
                            cols = row.find_all("td")
                            if len(cols) >= 5:
                                case_number = cols[0].get_text(strip=True)
                                case_title = cols[1].get_text(strip=True)
                                filing_date = cols[2].get_text(strip=True)
                                ct = cols[3].get_text(strip=True)
                                status = cols[4].get_text(strip=True)

                                # Parse case title for parties
                                plaintiff = None
                                defendant = None
                                if " vs " in case_title.lower():
                                    parts = case_title.lower().split(" vs ")
                                    plaintiff = parts[0].strip().title()
                                    defendant = parts[1].strip().title() if len(parts) > 1 else None
                                elif " v " in case_title.lower():
                                    parts = case_title.lower().split(" v ")
                                    plaintiff = parts[0].strip().title()
                                    defendant = parts[1].strip().title() if len(parts) > 1 else None

                                record = CourtCase(
                                    case_number=case_number,
                                    case_type=ct,
                                    case_title=case_title,
                                    filing_date=self._parse_date(filing_date),
                                    plaintiff=plaintiff,
                                    defendant=defendant,
                                    status=status,
                                    court="Maricopa County Superior Court",
                                    county="Maricopa",
                                    state="AZ",
                                    source_url=f"{self.config.court_url}case/{case_number}",
                                    raw_data={"columns": [c.get_text(strip=True) for c in cols]},
                                )
                                results.append(record)

        except Exception as e:
            logger.error(f"Error searching Maricopa court cases: {e}")

        return results

    async def search_court_cases_by_case_number(
        self,
        case_number: str
    ) -> Optional[CourtCase]:
        """Get detailed court case information by case number."""
        try:
            async with await self._create_session() as session:
                url = f"{self.court_search}case/{case_number}"

                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Parse case details
                        details = {}

                        # Case header
                        header = soup.find("div", class_="case-header")
                        if header:
                            title = header.find("h2")
                            details["title"] = title.get_text(strip=True) if title else None

                        # Case info section
                        info_section = soup.find("div", class_="case-info")
                        if info_section:
                            for row in info_section.find_all("div", class_="info-row"):
                                label = row.find("span", class_="label")
                                value = row.find("span", class_="value")
                                if label and value:
                                    key = label.get_text(strip=True).lower().replace(" ", "_")
                                    details[key] = value.get_text(strip=True)

                        # Parties section
                        parties_section = soup.find("div", class_="parties")
                        if parties_section:
                            plaintiff_div = parties_section.find("div", class_="plaintiff")
                            defendant_div = parties_section.find("div", class_="defendant")
                            details["plaintiff"] = plaintiff_div.get_text(strip=True) if plaintiff_div else None
                            details["defendant"] = defendant_div.get_text(strip=True) if defendant_div else None

                        # Docket entries
                        docket_entries = []
                        docket_table = soup.find("table", class_="docket")
                        if docket_table:
                            for row in docket_table.find_all("tr")[1:]:
                                cols = row.find_all("td")
                                if len(cols) >= 3:
                                    docket_entries.append({
                                        "date": cols[0].get_text(strip=True),
                                        "entry": cols[1].get_text(strip=True),
                                        "filed_by": cols[2].get_text(strip=True) if len(cols) > 2 else None,
                                    })

                        return CourtCase(
                            case_number=case_number,
                            case_type=details.get("case_type", ""),
                            case_title=details.get("title", ""),
                            filing_date=self._parse_date(details.get("filing_date")),
                            plaintiff=details.get("plaintiff"),
                            defendant=details.get("defendant"),
                            status=details.get("status", ""),
                            judge=details.get("judge"),
                            court="Maricopa County Superior Court",
                            county="Maricopa",
                            state="AZ",
                            source_url=url,
                            docket_entries=docket_entries,
                            raw_data=details,
                        )

        except Exception as e:
            logger.error(f"Error getting Maricopa court case {case_number}: {e}")

        return None

    async def search_civil_cases(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CourtCase]:
        """Search civil court cases (lawsuits, collections, evictions)."""
        return await self.search_court_cases_by_name(
            name=name,
            case_type="CV",  # Civil
            start_date=start_date,
            end_date=end_date
        )

    async def search_family_cases(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CourtCase]:
        """Search family court cases (divorce, custody, child support)."""
        return await self.search_court_cases_by_name(
            name=name,
            case_type="FC",  # Family Court
            start_date=start_date,
            end_date=end_date
        )

    async def search_probate_cases(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CourtCase]:
        """Search probate cases (estates, guardianships)."""
        return await self.search_court_cases_by_name(
            name=name,
            case_type="PB",  # Probate
            start_date=start_date,
            end_date=end_date
        )

    # ==================== Tax Records ====================

    async def search_tax_records(
        self,
        parcel_id: str,
        tax_year: Optional[int] = None
    ) -> List[TaxRecord]:
        """
        Search Maricopa County Treasurer for tax records.
        """
        results = []

        try:
            normalized_apn = parcel_id.replace("-", "").replace(" ", "")

            async with await self._create_session() as session:
                url = f"{self.treasurer_api}GetParcelDetails"
                params = {"parcelNumber": normalized_apn}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Parse tax information
                        for tax_year_data in data.get("taxYears", [data]):
                            if tax_year and tax_year_data.get("year") != tax_year:
                                continue

                            record = TaxRecord(
                                parcel_id=parcel_id,
                                tax_year=tax_year_data.get("year", datetime.now().year),
                                assessed_value=float(tax_year_data.get("assessedValue", 0)),
                                taxable_value=float(tax_year_data.get("limitedValue", 0)),
                                tax_amount=float(tax_year_data.get("totalTax", 0)),
                                amount_paid=float(tax_year_data.get("amountPaid", 0)),
                                amount_due=float(tax_year_data.get("amountDue", 0)),
                                status=tax_year_data.get("status", ""),
                                due_date=self._parse_date(tax_year_data.get("dueDate")),
                                county="Maricopa",
                                state="AZ",
                                source_url=f"{self.config.treasurer_url}Parcel/TaxBill?parcelNumber={normalized_apn}",
                                raw_data=tax_year_data,
                            )
                            results.append(record)
                    else:
                        # Fallback to scraping treasurer site
                        results = await self._scrape_tax_records(session, parcel_id, tax_year)

        except Exception as e:
            logger.error(f"Error searching Maricopa tax records: {e}")

        return results

    async def _scrape_tax_records(
        self,
        session: aiohttp.ClientSession,
        parcel_id: str,
        tax_year: Optional[int]
    ) -> List[TaxRecord]:
        """Scrape tax records from treasurer website."""
        results = []

        try:
            url = f"{self.config.treasurer_url}Parcel/TaxBill"
            params = {"parcelNumber": parcel_id.replace("-", "")}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Parse tax bill information
                    tax_table = soup.find("table", class_="tax-summary")
                    if tax_table:
                        for row in tax_table.find_all("tr")[1:]:
                            cols = row.find_all("td")
                            if len(cols) >= 4:
                                year = int(cols[0].get_text(strip=True))
                                if tax_year and year != tax_year:
                                    continue

                                record = TaxRecord(
                                    parcel_id=parcel_id,
                                    tax_year=year,
                                    tax_amount=self._parse_currency(cols[1].get_text(strip=True)),
                                    amount_paid=self._parse_currency(cols[2].get_text(strip=True)),
                                    amount_due=self._parse_currency(cols[3].get_text(strip=True)),
                                    status=cols[4].get_text(strip=True) if len(cols) > 4 else "",
                                    county="Maricopa",
                                    state="AZ",
                                    source_url=response.url.human_repr(),
                                )
                                results.append(record)

        except Exception as e:
            logger.error(f"Error scraping Maricopa tax records: {e}")

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
            "%b %d, %Y",
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


# Synchronous wrapper functions for convenience
def search_property_by_address(
    address: str,
    city: Optional[str] = None,
    zip_code: Optional[str] = None
) -> List[PropertyRecord]:
    """Synchronous wrapper for property search by address."""
    scraper = MaricopaCountyScraper()
    return asyncio.run(scraper.search_property_by_address(address, city, zip_code))


def search_property_by_owner(owner_name: str) -> List[PropertyRecord]:
    """Synchronous wrapper for property search by owner."""
    scraper = MaricopaCountyScraper()
    return asyncio.run(scraper.search_property_by_owner(owner_name))


def search_deeds_by_name(
    name: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[DeedRecord]:
    """Synchronous wrapper for deed search by name."""
    scraper = MaricopaCountyScraper()
    return asyncio.run(scraper.search_deeds_by_name(name, start_date, end_date))


def search_court_cases(
    name: str,
    case_type: Optional[str] = None
) -> List[CourtCase]:
    """Synchronous wrapper for court case search."""
    scraper = MaricopaCountyScraper()
    return asyncio.run(scraper.search_court_cases_by_name(name, case_type))


if __name__ == "__main__":
    # Example usage
    import sys

    logging.basicConfig(level=logging.INFO)

    async def main():
        scraper = MaricopaCountyScraper()

        print(f"Maricopa County Scraper - {scraper.config.county_name}")
        print(f"FIPS: {scraper.config.fips_code}")
        print(f"Population: {scraper.config.population:,}")
        print(f"County Seat: {scraper.config.seat}")
        print()

        # Example searches
        if len(sys.argv) > 1:
            query = sys.argv[1]
            print(f"Searching for: {query}")

            # Property search
            properties = await scraper.search_property_by_address(query)
            print(f"\nFound {len(properties)} properties")
            for prop in properties[:3]:
                print(f"  - {prop.parcel_id}: {prop.address} ({prop.owner_name})")

    asyncio.run(main())
