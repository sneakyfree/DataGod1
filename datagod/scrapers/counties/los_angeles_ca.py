"""
Los Angeles County, California Scraper - Property, Recorder, and Court Records.

Los Angeles County is the most populous county in the US (10M+ people).

Data Sources:
- Assessor: https://assessor.lacounty.gov/ (property data)
- Recorder: https://www.lavote.gov/apps/ocrportal/ (deeds, mortgages, liens)
- Superior Court: https://www.lacourt.org/ (court cases)
- Treasurer: https://ttc.lacounty.gov/ (tax info)

Note: LA County has modern APIs and portals for most services.
"""

import asyncio
import aiohttp
import re
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
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
)


# Los Angeles County Configuration
LA_COUNTY_CONFIG = CountyConfig(
    state="CA",
    county_name="Los Angeles County",
    fips_code="06037",
    seat="Los Angeles",
    population=10014009,
    assessor_url="https://assessor.lacounty.gov/",
    recorder_url="https://www.lavote.gov/apps/ocrportal/",
    clerk_url="https://www.lacourt.org/",
    courts_url="https://www.lacourt.org/",
    treasurer_url="https://ttc.lacounty.gov/",
    gis_url="https://assessor.lacounty.gov/assessor-map/",
    requires_session=True,
    rate_limit_seconds=2.0,
)


class LosAngelesCountyScraper(BaseCountyScraper):
    """
    Scraper for Los Angeles County, California public records.

    Implements property searches via the LA County Assessor,
    deed/mortgage searches via the Recorder, and court case
    searches via the Superior Court portal.
    """

    # LA County endpoints
    ASSESSOR_API = "https://portal.assessor.lacounty.gov/api"
    ASSESSOR_SEARCH = "https://portal.assessor.lacounty.gov/parceldetail"
    RECORDER_PORTAL = "https://www.lavote.gov/apps/ocrportal/"
    COURT_PORTAL = "https://www.lacourt.org/casesummary/ui/"
    TREASURER_SEARCH = "https://ttc.lacounty.gov/proptax/"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize Los Angeles County scraper."""
        super().__init__(LA_COUNTY_CONFIG, session)

    # ==================== Property/Assessor Methods ====================

    async def search_property_by_address(
        self,
        address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None
    ) -> List[PropertyRecord]:
        """
        Search LA County Assessor by address.
        """
        await self._ensure_session()
        results = []

        try:
            # LA County Assessor API
            search_url = f"{self.ASSESSOR_API}/search"

            query = address
            if city:
                query += f", {city}"
            if zip_code:
                query += f" {zip_code}"

            params = {
                "search": query,
                "type": "address",
                "limit": 50,
            }

            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("Parcels", data.get("results", [])):
                        try:
                            ain = item.get("AIN", item.get("ain", item.get("parcel_id", "")))
                            if not ain:
                                continue

                            record = PropertyRecord(
                                parcel_id=str(ain),
                                address=item.get("PropertyAddress", item.get("address")),
                                city=item.get("City", city),
                                state="CA",
                                zip_code=item.get("ZipCode", zip_code),
                                owner_name=item.get("OwnerName", item.get("owner")),
                                property_class=item.get("UseCode", item.get("use_code")),
                                assessed_value=self._parse_currency(item.get("TotalValue", item.get("assessed_value"))),
                                land_value=self._parse_currency(item.get("LandValue", item.get("land_value"))),
                                improvement_value=self._parse_currency(item.get("ImpValue", item.get("improvement_value"))),
                                square_feet=int(item.get("LandSqFt", 0) or 0),
                                year_built=item.get("YearBuilt"),
                                county="Los Angeles County",
                                fips_code="06037",
                                raw_data=item,
                            )
                            results.append(record)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        # Fallback to scraping if API fails
        if not results:
            results = await self._search_assessor_scrape(address, city, zip_code)

        return results

    async def _search_assessor_scrape(
        self,
        address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None
    ) -> List[PropertyRecord]:
        """Fallback scrape method for assessor search."""
        results = []

        try:
            search_url = "https://portal.assessor.lacounty.gov/parceldetail"
            params = {"ain": "", "address": address}

            html = await self._get(search_url, params=params)
            if not html:
                return results

            soup = BeautifulSoup(html, 'html.parser')

            for row in soup.select('.parcel-result, tr.result'):
                try:
                    ain_el = row.select_one('.ain, [data-ain]')
                    addr_el = row.select_one('.address')

                    if not ain_el:
                        continue

                    ain = ain_el.get_text(strip=True) or ain_el.get('data-ain', '')

                    record = PropertyRecord(
                        parcel_id=ain,
                        address=addr_el.get_text(strip=True) if addr_el else address,
                        city=city,
                        state="CA",
                        county="Los Angeles County",
                        fips_code="06037",
                    )
                    results.append(record)
                except (AttributeError, ValueError):
                    continue

        except Exception:
            pass

        return results

    async def search_property_by_owner(
        self,
        owner_name: str
    ) -> List[PropertyRecord]:
        """
        Search LA County Assessor by owner name.
        """
        await self._ensure_session()
        results = []

        try:
            search_url = f"{self.ASSESSOR_API}/search"

            params = {
                "search": owner_name.upper(),
                "type": "owner",
                "limit": 100,
            }

            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("Parcels", data.get("results", [])):
                        try:
                            ain = item.get("AIN", item.get("ain", ""))
                            if not ain:
                                continue

                            record = PropertyRecord(
                                parcel_id=str(ain),
                                address=item.get("PropertyAddress"),
                                city=item.get("City"),
                                state="CA",
                                zip_code=item.get("ZipCode"),
                                owner_name=item.get("OwnerName", owner_name),
                                assessed_value=self._parse_currency(item.get("TotalValue")),
                                property_class=item.get("UseCode"),
                                county="Los Angeles County",
                                fips_code="06037",
                                raw_data=item,
                            )
                            results.append(record)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    async def search_property_by_parcel(
        self,
        parcel_id: str
    ) -> Optional[PropertyRecord]:
        """
        Get property details by AIN (Assessor's Identification Number).

        LA County AINs are 10-digit numbers.
        """
        await self._ensure_session()

        # Clean AIN - remove dashes if present
        ain = re.sub(r'[^0-9]', '', parcel_id)

        try:
            # Direct AIN lookup
            detail_url = f"{self.ASSESSOR_API}/parcel/{ain}"

            async with self.session.get(detail_url) as response:
                if response.status == 200:
                    data = await response.json()

                    record = PropertyRecord(
                        parcel_id=ain,
                        address=data.get("PropertyAddress", data.get("SitusAddress")),
                        city=data.get("City"),
                        state="CA",
                        zip_code=data.get("ZipCode"),
                        owner_name=data.get("OwnerName", data.get("Owner1")),
                        owner_address=data.get("MailingAddress"),
                        property_class=data.get("UseCode", data.get("UseDescription")),
                        land_use=data.get("UseDescription"),
                        assessed_value=self._parse_currency(data.get("TotalValue")),
                        land_value=self._parse_currency(data.get("LandValue")),
                        improvement_value=self._parse_currency(data.get("ImpValue")),
                        market_value=self._parse_currency(data.get("MarketValue")),
                        tax_year=data.get("TaxYear"),
                        square_feet=int(data.get("LandSqFt", 0) or 0),
                        building_sqft=int(data.get("BldgSqFt", 0) or 0),
                        year_built=data.get("YearBuilt"),
                        bedrooms=int(data.get("Bedrooms", 0) or 0),
                        bathrooms=float(data.get("Bathrooms", 0) or 0),
                        legal_description=data.get("LegalDescription"),
                        latitude=data.get("Latitude"),
                        longitude=data.get("Longitude"),
                        county="Los Angeles County",
                        fips_code="06037",
                        raw_data=data,
                    )

                    return record

        except aiohttp.ClientError:
            pass

        # Fallback to scraping
        return await self._get_property_detail_scrape(ain)

    async def _get_property_detail_scrape(self, ain: str) -> Optional[PropertyRecord]:
        """Fallback scrape for property details."""
        try:
            url = f"https://portal.assessor.lacounty.gov/parceldetail/{ain}"

            html = await self._get(url)
            if not html:
                return None

            soup = BeautifulSoup(html, 'html.parser')

            record = PropertyRecord(
                parcel_id=ain,
                county="Los Angeles County",
                state="CA",
                fips_code="06037",
            )

            # Parse property info from page
            for row in soup.select('.property-detail tr, .detail-row'):
                label = row.select_one('th, .label')
                value = row.select_one('td, .value')

                if not label or not value:
                    continue

                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)

                if 'address' in label_text and 'situs' in label_text:
                    record.address = value_text
                elif 'owner' in label_text:
                    record.owner_name = self._clean_name(value_text)
                elif 'total value' in label_text or 'assessed' in label_text:
                    record.assessed_value = self._parse_currency(value_text)
                elif 'land value' in label_text:
                    record.land_value = self._parse_currency(value_text)
                elif 'improvement' in label_text:
                    record.improvement_value = self._parse_currency(value_text)
                elif 'use code' in label_text:
                    record.property_class = value_text
                elif 'year built' in label_text:
                    try:
                        record.year_built = int(value_text)
                    except ValueError:
                        pass

            return record

        except Exception:
            pass

        return None

    # ==================== Recorder Methods ====================

    async def search_deeds_by_name(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        as_grantor: bool = True,
        as_grantee: bool = True
    ) -> List[DeedRecord]:
        """
        Search LA County Recorder by party name.
        """
        await self._ensure_session()
        results = []

        try:
            search_url = "https://www.lavote.gov/apps/ocrportal/api/search"

            start = start_date.strftime("%Y-%m-%d") if start_date else "1900-01-01"
            end = end_date.strftime("%Y-%m-%d") if end_date else datetime.now().strftime("%Y-%m-%d")

            search_data = {
                "searchType": "name",
                "name": name.upper(),
                "startDate": start,
                "endDate": end,
                "searchGrantor": as_grantor,
                "searchGrantee": as_grantee,
                "limit": 100,
            }

            async with self.session.post(search_url, json=search_data) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("documents", data.get("results", [])):
                        try:
                            doc_num = item.get("documentNumber", item.get("doc_num", ""))
                            if not doc_num:
                                continue

                            record = DeedRecord(
                                document_number=str(doc_num),
                                record_type=item.get("documentType", item.get("doc_type", "Unknown")),
                                grantor=item.get("grantor"),
                                grantee=item.get("grantee"),
                                recording_date=self._parse_date(item.get("recordingDate")),
                                document_date=self._parse_date(item.get("documentDate")),
                                consideration=self._parse_currency(item.get("consideration")),
                                book=item.get("book"),
                                page=item.get("page"),
                                parcel_id=item.get("ain"),
                                county="Los Angeles County",
                                state="CA",
                                fips_code="06037",
                                raw_data=item,
                            )
                            results.append(record)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    async def search_deeds_by_parcel(
        self,
        parcel_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[DeedRecord]:
        """
        Search LA County Recorder by AIN.
        """
        await self._ensure_session()
        results = []

        ain = re.sub(r'[^0-9]', '', parcel_id)

        try:
            search_url = "https://www.lavote.gov/apps/ocrportal/api/search"

            start = start_date.strftime("%Y-%m-%d") if start_date else "1900-01-01"
            end = end_date.strftime("%Y-%m-%d") if end_date else datetime.now().strftime("%Y-%m-%d")

            search_data = {
                "searchType": "ain",
                "ain": ain,
                "startDate": start,
                "endDate": end,
                "limit": 100,
            }

            async with self.session.post(search_url, json=search_data) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("documents", data.get("results", [])):
                        try:
                            doc_num = item.get("documentNumber", "")
                            if not doc_num:
                                continue

                            record = DeedRecord(
                                document_number=str(doc_num),
                                record_type=item.get("documentType", "Unknown"),
                                grantor=item.get("grantor"),
                                grantee=item.get("grantee"),
                                recording_date=self._parse_date(item.get("recordingDate")),
                                consideration=self._parse_currency(item.get("consideration")),
                                parcel_id=ain,
                                county="Los Angeles County",
                                state="CA",
                                fips_code="06037",
                                raw_data=item,
                            )
                            results.append(record)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    # ==================== Court Methods ====================

    async def search_court_cases_by_name(
        self,
        name: str,
        case_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CourtCase]:
        """
        Search LA County Superior Court cases by party name.
        """
        await self._ensure_session()
        results = []

        try:
            # LA County Superior Court case search
            search_url = "https://www.lacourt.org/casesummary/ui/CaseSummary.aspx"

            # The court uses a form-based search
            search_data = {
                "ctl00$MainContent$txtPartyName": name.upper(),
                "ctl00$MainContent$ddlCaseType": case_type or "ALL",
                "ctl00$MainContent$btnSearch": "Search",
            }

            html = await self._post(search_url, data=search_data)
            if not html:
                return results

            soup = BeautifulSoup(html, 'html.parser')

            # Parse search results
            results_table = soup.select_one('#MainContent_gvSearchResults, .case-results')
            if results_table:
                for row in results_table.select('tr')[1:]:  # Skip header
                    try:
                        cells = row.select('td')
                        if len(cells) < 3:
                            continue

                        case_num = cells[0].get_text(strip=True)
                        if not case_num:
                            continue

                        case = CourtCase(
                            case_number=case_num,
                            case_type=cells[1].get_text(strip=True) if len(cells) > 1 else "Unknown",
                            case_title=cells[2].get_text(strip=True) if len(cells) > 2 else None,
                            filing_date=self._parse_date(cells[3].get_text(strip=True)) if len(cells) > 3 else None,
                            status=cells[4].get_text(strip=True) if len(cells) > 4 else None,
                            county="Los Angeles County",
                            state="CA",
                            fips_code="06037",
                        )

                        # Parse plaintiff/defendant from case title
                        if case.case_title and ' vs ' in case.case_title.lower():
                            parts = re.split(r'\s+v[s.]?\s+', case.case_title, flags=re.IGNORECASE)
                            if len(parts) >= 2:
                                case.plaintiff = self._clean_name(parts[0])
                                case.defendant = self._clean_name(parts[1])

                        results.append(case)

                    except (AttributeError, IndexError, ValueError):
                        continue

        except aiohttp.ClientError:
            pass

        return results

    async def search_court_cases_by_number(
        self,
        case_number: str
    ) -> Optional[CourtCase]:
        """
        Get LA County Superior Court case by case number.
        """
        await self._ensure_session()

        try:
            detail_url = f"https://www.lacourt.org/casesummary/ui/CaseSummary.aspx?caseNumber={case_number}"

            html = await self._get(detail_url)
            if not html:
                return None

            soup = BeautifulSoup(html, 'html.parser')

            case = CourtCase(
                case_number=case_number,
                case_type="Unknown",
                county="Los Angeles County",
                state="CA",
                fips_code="06037",
            )

            # Parse case details
            for row in soup.select('.case-detail tr, .detail-row'):
                label = row.select_one('th, .label, td:first-child')
                value = row.select_one('td:last-child, .value')

                if not label or not value:
                    continue

                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)

                if 'case type' in label_text:
                    case.case_type = value_text
                elif 'status' in label_text:
                    case.status = value_text
                elif 'filing date' in label_text or 'filed' in label_text:
                    case.filing_date = self._parse_date(value_text)
                elif 'judge' in label_text:
                    case.judge = value_text
                elif 'plaintiff' in label_text or 'petitioner' in label_text:
                    case.plaintiff = self._clean_name(value_text)
                elif 'defendant' in label_text or 'respondent' in label_text:
                    case.defendant = self._clean_name(value_text)

            return case

        except aiohttp.ClientError:
            pass

        return None

    # ==================== Tax Methods ====================

    async def get_tax_info(self, parcel_id: str) -> Optional[TaxRecord]:
        """
        Get tax information from LA County Treasurer.
        """
        await self._ensure_session()

        ain = re.sub(r'[^0-9]', '', parcel_id)

        try:
            search_url = f"https://ttc.lacounty.gov/proptax/api/parcel/{ain}"

            async with self.session.get(search_url) as response:
                if response.status == 200:
                    data = await response.json()

                    record = TaxRecord(
                        parcel_id=ain,
                        tax_year=data.get("TaxYear", datetime.now().year),
                        owner_name=data.get("OwnerName"),
                        property_address=data.get("PropertyAddress"),
                        assessed_value=self._parse_currency(data.get("AssessedValue")),
                        taxable_value=self._parse_currency(data.get("TaxableValue")),
                        tax_amount=self._parse_currency(data.get("TaxAmount")),
                        amount_paid=self._parse_currency(data.get("AmountPaid")),
                        amount_due=self._parse_currency(data.get("AmountDue")),
                        status=data.get("Status"),
                        county="Los Angeles County",
                        state="CA",
                        fips_code="06037",
                        raw_data=data,
                    )

                    if data.get("DueDate"):
                        record.due_date = self._parse_date(data["DueDate"])

                    return record

        except aiohttp.ClientError:
            pass

        return None


# Synchronous wrapper functions
def search_la_county_property_sync(
    address: Optional[str] = None,
    owner: Optional[str] = None,
    ain: Optional[str] = None
) -> List[PropertyRecord]:
    """Synchronous wrapper for LA County property search."""
    async def _search():
        async with LosAngelesCountyScraper() as scraper:
            if ain:
                result = await scraper.search_property_by_parcel(ain)
                return [result] if result else []
            elif owner:
                return await scraper.search_property_by_owner(owner)
            elif address:
                return await scraper.search_property_by_address(address)
            return []
    return asyncio.run(_search())


def search_la_county_deeds_sync(
    name: Optional[str] = None,
    parcel_id: Optional[str] = None
) -> List[DeedRecord]:
    """Synchronous wrapper for LA County deed search."""
    async def _search():
        async with LosAngelesCountyScraper() as scraper:
            if parcel_id:
                return await scraper.search_deeds_by_parcel(parcel_id)
            elif name:
                return await scraper.search_deeds_by_name(name)
            return []
    return asyncio.run(_search())


# Export
__all__ = [
    "LosAngelesCountyScraper",
    "LA_COUNTY_CONFIG",
    "search_la_county_property_sync",
    "search_la_county_deeds_sync",
]
