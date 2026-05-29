"""
Harris County, Texas Scraper - Property, Recorder, and Court Records.

Harris County is the third most populous county in the US (4.7M+ people)
and includes the city of Houston.

Data Sources:
- Appraisal District: https://hcad.org/ (property data)
- County Clerk: https://countyclerk.harriscountytx.gov/ (deeds, mortgages, liens)
- District Clerk: https://www.hcdistrictclerk.com/ (civil/criminal cases)
- Tax Office: https://www.hctax.net/ (tax info)

Note: Harris County has excellent online systems with public APIs.
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from .base_county_scraper import (
    BaseCountyScraper,
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

# Harris County Configuration
HARRIS_COUNTY_CONFIG = CountyConfig(
    state="TX",
    county_name="Harris County",
    fips_code="48201",
    seat="Houston",
    population=4731145,
    assessor_url="https://hcad.org/",
    recorder_url="https://countyclerk.harriscountytx.gov/",
    clerk_url="https://www.hcdistrictclerk.com/",
    courts_url="https://www.hcdistrictclerk.com/",
    treasurer_url="https://www.hctax.net/",
    gis_url="https://pdata.hcad.org/",
    requires_session=True,
    rate_limit_seconds=1.5,
)


class HarrisCountyScraper(BaseCountyScraper):
    """
    Scraper for Harris County, Texas public records.

    Implements property searches via HCAD (Harris County Appraisal District),
    deed/mortgage searches via the County Clerk, and court case
    searches via the District Clerk portal.
    """

    # Harris County endpoints
    HCAD_API = "https://pdata.hcad.org/api"
    HCAD_SEARCH = "https://hcad.org/property-search/"
    COUNTY_CLERK_SEARCH = "https://countyclerk.harriscountytx.gov/en/RecordsSearch"
    DISTRICT_CLERK_SEARCH = "https://www.hcdistrictclerk.com/edocs/public/"
    TAX_SEARCH = "https://www.hctax.net/Property/PropertyTax"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize Harris County scraper."""
        super().__init__(HARRIS_COUNTY_CONFIG, session)

    # ==================== Property/Appraisal Methods ====================

    async def search_property_by_address(
        self, address: str, city: Optional[str] = None, zip_code: Optional[str] = None
    ) -> List[PropertyRecord]:
        """
        Search HCAD by address.
        """
        await self._ensure_session()
        results = []

        try:
            # HCAD property search API
            search_url = "https://pdata.hcad.org/api/property/search"

            params = {
                "address": address,
                "city": city or "",
                "zip": zip_code or "",
                "limit": 50,
            }

            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("properties", data.get("results", [])):
                        try:
                            account = item.get("account", item.get("Account", ""))
                            if not account:
                                continue

                            record = PropertyRecord(
                                parcel_id=str(account),
                                address=item.get("site_addr", item.get("SiteAddress")),
                                city=item.get("city", city or "Houston"),
                                state="TX",
                                zip_code=item.get("zip", zip_code),
                                owner_name=item.get(
                                    "owner_name", item.get("OwnerName")
                                ),
                                property_class=item.get(
                                    "state_class", item.get("StateClass")
                                ),
                                assessed_value=self._parse_currency(
                                    item.get(
                                        "appraised_val", item.get("AppraisedValue")
                                    )
                                ),
                                land_value=self._parse_currency(
                                    item.get("land_val", item.get("LandValue"))
                                ),
                                improvement_value=self._parse_currency(
                                    item.get("impr_val", item.get("ImprovementValue"))
                                ),
                                market_value=self._parse_currency(
                                    item.get("market_val", item.get("MarketValue"))
                                ),
                                tax_year=item.get("tax_year", item.get("TaxYear")),
                                acres=float(item.get("acreage", 0) or 0),
                                square_feet=int(item.get("land_sqft", 0) or 0),
                                year_built=item.get("yr_built", item.get("YearBuilt")),
                                legal_description=item.get(
                                    "legal_desc", item.get("LegalDescription")
                                ),
                                county="Harris County",
                                fips_code="48201",
                                raw_data=item,
                            )
                            results.append(record)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    async def search_property_by_owner(self, owner_name: str) -> List[PropertyRecord]:
        """
        Search HCAD by owner name.
        """
        await self._ensure_session()
        results = []

        try:
            search_url = "https://pdata.hcad.org/api/property/owner"

            params = {
                "owner": owner_name.upper(),
                "limit": 100,
            }

            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("properties", data.get("results", [])):
                        try:
                            account = item.get("account", "")
                            if not account:
                                continue

                            record = PropertyRecord(
                                parcel_id=str(account),
                                address=item.get("site_addr"),
                                city=item.get("city", "Houston"),
                                state="TX",
                                zip_code=item.get("zip"),
                                owner_name=item.get("owner_name", owner_name),
                                assessed_value=self._parse_currency(
                                    item.get("appraised_val")
                                ),
                                market_value=self._parse_currency(
                                    item.get("market_val")
                                ),
                                property_class=item.get("state_class"),
                                county="Harris County",
                                fips_code="48201",
                                raw_data=item,
                            )
                            results.append(record)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    async def search_property_by_parcel(
        self, parcel_id: str
    ) -> Optional[PropertyRecord]:
        """
        Get property details by HCAD account number.

        Harris County uses account numbers like: XXXX-XX-XXXX-XXXX-XXX
        """
        await self._ensure_session()

        # Clean account number
        account = re.sub(r"[^0-9]", "", parcel_id)

        try:
            detail_url = f"https://pdata.hcad.org/api/property/{account}"

            async with self.session.get(detail_url) as response:
                if response.status == 200:
                    data = await response.json()

                    record = PropertyRecord(
                        parcel_id=account,
                        address=data.get("site_addr", data.get("SiteAddress")),
                        city=data.get("city", "Houston"),
                        state="TX",
                        zip_code=data.get("zip"),
                        owner_name=data.get("owner_name", data.get("OwnerName")),
                        owner_address=data.get("mail_addr", data.get("MailingAddress")),
                        property_class=data.get("state_class", data.get("StateClass")),
                        land_use=data.get(
                            "land_use_desc", data.get("LandUseDescription")
                        ),
                        assessed_value=self._parse_currency(data.get("appraised_val")),
                        land_value=self._parse_currency(data.get("land_val")),
                        improvement_value=self._parse_currency(data.get("impr_val")),
                        market_value=self._parse_currency(data.get("market_val")),
                        tax_year=data.get("tax_year"),
                        acres=float(data.get("acreage", 0) or 0),
                        square_feet=int(data.get("land_sqft", 0) or 0),
                        building_sqft=int(data.get("bldg_sqft", 0) or 0),
                        year_built=data.get("yr_built"),
                        bedrooms=int(data.get("bedrooms", 0) or 0),
                        bathrooms=float(data.get("bathrooms", 0) or 0),
                        legal_description=data.get("legal_desc"),
                        subdivision=data.get("subdivision"),
                        school_district=data.get("school_dist"),
                        latitude=data.get("latitude"),
                        longitude=data.get("longitude"),
                        county="Harris County",
                        fips_code="48201",
                        raw_data=data,
                    )

                    return record

        except aiohttp.ClientError:
            pass

        return None

    # ==================== Recorder/County Clerk Methods ====================

    async def search_deeds_by_name(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        as_grantor: bool = True,
        as_grantee: bool = True,
    ) -> List[DeedRecord]:
        """
        Search Harris County Clerk records by party name.
        """
        await self._ensure_session()
        results = []

        try:
            search_url = "https://countyclerk.harriscountytx.gov/Apps/CCLERK/PRS/search"

            start = start_date.strftime("%m/%d/%Y") if start_date else "01/01/1970"
            end = (
                end_date.strftime("%m/%d/%Y")
                if end_date
                else datetime.now().strftime("%m/%d/%Y")
            )

            search_data = {
                "searchType": "name",
                "partyName": name.upper(),
                "startDate": start,
                "endDate": end,
                "grantor": "true" if as_grantor else "false",
                "grantee": "true" if as_grantee else "false",
            }

            async with self.session.post(search_url, data=search_data) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("documents", data.get("results", [])):
                        try:
                            doc_num = item.get(
                                "documentNumber", item.get("doc_number", "")
                            )
                            if not doc_num:
                                continue

                            record = DeedRecord(
                                document_number=str(doc_num),
                                record_type=item.get(
                                    "instrumentType", item.get("doc_type", "Unknown")
                                ),
                                grantor=item.get("grantor"),
                                grantee=item.get("grantee"),
                                recording_date=self._parse_date(
                                    item.get("filedDate", item.get("recording_date"))
                                ),
                                document_date=self._parse_date(
                                    item.get("documentDate")
                                ),
                                consideration=self._parse_currency(
                                    item.get("consideration")
                                ),
                                book=item.get("volume"),
                                page=item.get("page"),
                                parcel_id=item.get("accountNumber"),
                                legal_description=item.get("legalDescription"),
                                county="Harris County",
                                state="TX",
                                fips_code="48201",
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
        end_date: Optional[datetime] = None,
    ) -> List[DeedRecord]:
        """
        Search Harris County Clerk by account number.
        """
        await self._ensure_session()
        results = []

        account = re.sub(r"[^0-9]", "", parcel_id)

        try:
            search_url = "https://countyclerk.harriscountytx.gov/Apps/CCLERK/PRS/search"

            start = start_date.strftime("%m/%d/%Y") if start_date else "01/01/1970"
            end = (
                end_date.strftime("%m/%d/%Y")
                if end_date
                else datetime.now().strftime("%m/%d/%Y")
            )

            search_data = {
                "searchType": "account",
                "accountNumber": account,
                "startDate": start,
                "endDate": end,
            }

            async with self.session.post(search_url, data=search_data) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get("documents", data.get("results", [])):
                        try:
                            doc_num = item.get("documentNumber", "")
                            if not doc_num:
                                continue

                            record = DeedRecord(
                                document_number=str(doc_num),
                                record_type=item.get("instrumentType", "Unknown"),
                                grantor=item.get("grantor"),
                                grantee=item.get("grantee"),
                                recording_date=self._parse_date(item.get("filedDate")),
                                consideration=self._parse_currency(
                                    item.get("consideration")
                                ),
                                parcel_id=account,
                                county="Harris County",
                                state="TX",
                                fips_code="48201",
                                raw_data=item,
                            )
                            results.append(record)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        return results

    # ==================== Court/District Clerk Methods ====================

    async def search_court_cases_by_name(
        self,
        name: str,
        case_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CourtCase]:
        """
        Search Harris County District Clerk cases by party name.
        """
        await self._ensure_session()
        results = []

        try:
            search_url = "https://www.hcdistrictclerk.com/edocs/public/search.aspx"

            search_data = {
                "searchType": "party",
                "partyName": name.upper(),
                "caseType": case_type or "All",
            }

            if start_date:
                search_data["startDate"] = start_date.strftime("%m/%d/%Y")
            if end_date:
                search_data["endDate"] = end_date.strftime("%m/%d/%Y")

            html = await self._post(search_url, data=search_data)
            if not html:
                return results

            soup = BeautifulSoup(html, "html.parser")

            for row in soup.select("tr.case-row, .case-result, tbody tr"):
                try:
                    cells = row.select("td")
                    if len(cells) < 3:
                        continue

                    case_num = cells[0].get_text(strip=True)
                    if not case_num or case_num.lower() in ["case number", ""]:
                        continue

                    case = CourtCase(
                        case_number=case_num,
                        case_type=(
                            cells[1].get_text(strip=True)
                            if len(cells) > 1
                            else "Unknown"
                        ),
                        case_title=(
                            cells[2].get_text(strip=True) if len(cells) > 2 else None
                        ),
                        filing_date=(
                            self._parse_date(cells[3].get_text(strip=True))
                            if len(cells) > 3
                            else None
                        ),
                        status=(
                            cells[4].get_text(strip=True) if len(cells) > 4 else None
                        ),
                        court=cells[5].get_text(strip=True) if len(cells) > 5 else None,
                        county="Harris County",
                        state="TX",
                        fips_code="48201",
                    )

                    # Parse parties from case title
                    if case.case_title and " vs " in case.case_title.lower():
                        parts = re.split(
                            r"\s+v[s.]?\s+", case.case_title, flags=re.IGNORECASE
                        )
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
        self, case_number: str
    ) -> Optional[CourtCase]:
        """
        Get Harris County District Clerk case by case number.
        """
        await self._ensure_session()

        try:
            detail_url = f"https://www.hcdistrictclerk.com/edocs/public/CaseDetail.aspx?caseID={case_number}"

            html = await self._get(detail_url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            case = CourtCase(
                case_number=case_number,
                case_type="Unknown",
                county="Harris County",
                state="TX",
                fips_code="48201",
            )

            # Parse case details
            for row in soup.select(".detail-row, tr"):
                label = row.select_one(".label, th, td:first-child")
                value = row.select_one(".value, td:last-child")

                if not label or not value:
                    continue

                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)

                if "case type" in label_text or "type" in label_text:
                    case.case_type = value_text
                elif "status" in label_text:
                    case.status = value_text
                elif "filed" in label_text or "filing date" in label_text:
                    case.filing_date = self._parse_date(value_text)
                elif "court" in label_text:
                    case.court = value_text
                elif "judge" in label_text:
                    case.judge = value_text
                elif "style" in label_text or "title" in label_text:
                    case.case_title = value_text

            # Parse parties
            parties_section = soup.select_one("#parties, .parties-table")
            if parties_section:
                for party_row in parties_section.select("tr"):
                    cells = party_row.select("td")
                    if len(cells) >= 2:
                        party_type = cells[0].get_text(strip=True)
                        party_name = cells[1].get_text(strip=True)
                        case.parties.append(
                            {
                                "type": party_type,
                                "name": self._clean_name(party_name),
                            }
                        )

            return case

        except aiohttp.ClientError:
            pass

        return None

    # ==================== Tax Methods ====================

    async def get_tax_info(self, parcel_id: str) -> Optional[TaxRecord]:
        """
        Get tax information from Harris County Tax Office.
        """
        await self._ensure_session()

        account = re.sub(r"[^0-9]", "", parcel_id)

        try:
            search_url = (
                f"https://www.hctax.net/Property/PropertySearch?account={account}"
            )

            html = await self._get(search_url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            record = TaxRecord(
                parcel_id=account,
                tax_year=datetime.now().year,
                county="Harris County",
                state="TX",
                fips_code="48201",
            )

            # Parse tax details
            for row in soup.select(".tax-detail tr, .property-row"):
                label = row.select_one("th, .label, td:first-child")
                value = row.select_one("td:last-child, .value")

                if not label or not value:
                    continue

                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)

                if "owner" in label_text:
                    record.owner_name = self._clean_name(value_text)
                elif "address" in label_text and "property" in label_text:
                    record.property_address = value_text
                elif "appraised" in label_text or "assessed" in label_text:
                    record.assessed_value = self._parse_currency(value_text)
                elif "taxable" in label_text:
                    record.taxable_value = self._parse_currency(value_text)
                elif "total tax" in label_text or "tax amount" in label_text:
                    record.tax_amount = self._parse_currency(value_text)
                elif "amount due" in label_text or "balance" in label_text:
                    record.amount_due = self._parse_currency(value_text)
                elif "paid" in label_text:
                    record.amount_paid = self._parse_currency(value_text)
                elif "status" in label_text:
                    record.status = value_text

            return record

        except aiohttp.ClientError:
            pass

        return None


# Synchronous wrapper functions
def search_harris_county_property_sync(
    address: Optional[str] = None,
    owner: Optional[str] = None,
    account: Optional[str] = None,
) -> List[PropertyRecord]:
    """Synchronous wrapper for Harris County property search."""

    async def _search():
        async with HarrisCountyScraper() as scraper:
            if account:
                result = await scraper.search_property_by_parcel(account)
                return [result] if result else []
            elif owner:
                return await scraper.search_property_by_owner(owner)
            elif address:
                return await scraper.search_property_by_address(address)
            return []

    return asyncio.run(_search())


def search_harris_county_deeds_sync(
    name: Optional[str] = None, parcel_id: Optional[str] = None
) -> List[DeedRecord]:
    """Synchronous wrapper for Harris County deed search."""

    async def _search():
        async with HarrisCountyScraper() as scraper:
            if parcel_id:
                return await scraper.search_deeds_by_parcel(parcel_id)
            elif name:
                return await scraper.search_deeds_by_name(name)
            return []

    return asyncio.run(_search())


# Export
__all__ = [
    "HarrisCountyScraper",
    "HARRIS_COUNTY_CONFIG",
    "search_harris_county_property_sync",
    "search_harris_county_deeds_sync",
]
