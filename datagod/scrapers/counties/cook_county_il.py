"""
Cook County, Illinois Scraper - Property, Recorder, and Court Records.

Cook County is the second most populous county in the US (5.2M people)
and includes the city of Chicago.

Data Sources:
- Assessor: https://www.cookcountyassessor.com/ (property data)
- Recorder: https://www.cookcountyrecorder.com/ (deeds, mortgages, liens)
- Clerk of Court: https://www.cookcountyclerkofcourt.org/ (court cases)
- Treasurer: https://www.cookcountytreasurer.com/ (tax info)

Note: Cook County has relatively good online systems with some API-like endpoints.
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

# Cook County Configuration
COOK_COUNTY_CONFIG = CountyConfig(
    state="IL",
    county_name="Cook County",
    fips_code="17031",
    seat="Chicago",
    population=5275541,
    assessor_url="https://www.cookcountyassessor.com/",
    recorder_url="https://www.cookcountyrecorder.com/",
    clerk_url="https://www.cookcountyclerkofcourt.org/",
    courts_url="https://www.cookcountyclerkofcourt.org/",
    treasurer_url="https://www.cookcountytreasurer.com/",
    gis_url="https://maps.cookcountyil.gov/",
    requires_session=True,
    rate_limit_seconds=1.5,
)


class CookCountyScraper(BaseCountyScraper):
    """
    Scraper for Cook County, Illinois public records.

    Implements property searches via the Cook County Assessor,
    deed/mortgage searches via the Recorder, and court case
    searches via the Clerk of Court.
    """

    # API-like endpoints discovered through inspection
    ASSESSOR_API = "https://www.cookcountyassessor.com/api"
    ASSESSOR_SEARCH = "https://www.cookcountyassessor.com/address-search"
    RECORDER_SEARCH = "https://recorder.cookcounty.gov/recordersearch/home"
    COURT_SEARCH = "https://cccportal.cookcountyclerkofcourt.org/CCCPortal/"
    TREASURER_SEARCH = "https://www.cookcountytreasurer.com/setsearchparameters.aspx"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize Cook County scraper."""
        super().__init__(COOK_COUNTY_CONFIG, session)

    # ==================== Property/Assessor Methods ====================

    async def search_property_by_address(
        self, address: str, city: Optional[str] = None, zip_code: Optional[str] = None
    ) -> List[PropertyRecord]:
        """
        Search Cook County Assessor by address.

        Uses the assessor's address search functionality.
        """
        await self._ensure_session()
        results = []

        try:
            # Cook County Assessor has a search API endpoint
            search_url = f"{self.ASSESSOR_API}/address-search"

            # Build search query
            query = address
            if city:
                query += f", {city}"
            if zip_code:
                query += f" {zip_code}"

            params = {
                "q": query,
                "limit": 50,
            }

            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get(
                        "results", data if isinstance(data, list) else []
                    ):
                        try:
                            pin = item.get("pin", item.get("PIN", ""))
                            if not pin:
                                continue

                            record = PropertyRecord(
                                parcel_id=str(pin),
                                address=item.get(
                                    "address", item.get("property_address")
                                ),
                                city=item.get("city", "Chicago"),
                                state="IL",
                                zip_code=item.get("zip"),
                                owner_name=item.get("owner_name"),
                                property_class=item.get(
                                    "class", item.get("property_class")
                                ),
                                assessed_value=self._parse_currency(
                                    item.get("assessed_value")
                                ),
                                market_value=self._parse_currency(
                                    item.get("market_value")
                                ),
                                land_value=self._parse_currency(item.get("land_value")),
                                improvement_value=self._parse_currency(
                                    item.get("building_value")
                                ),
                                tax_year=item.get("tax_year"),
                                square_feet=int(item.get("land_sqft", 0) or 0),
                                building_sqft=int(item.get("building_sqft", 0) or 0),
                                year_built=item.get("year_built"),
                                township=item.get("township"),
                                county="Cook County",
                                fips_code="17031",
                                raw_data=item,
                            )
                            results.append(record)
                        except (KeyError, ValueError, TypeError):
                            continue

        except aiohttp.ClientError:
            pass

        # If API didn't work, try scraping the search page
        if not results:
            results = await self._search_assessor_scrape(address, city, zip_code)

        return results

    async def _search_assessor_scrape(
        self, address: str, city: Optional[str] = None, zip_code: Optional[str] = None
    ) -> List[PropertyRecord]:
        """Fallback: scrape assessor search results page."""
        results = []

        try:
            # Post to search form
            search_url = "https://www.cookcountyassessor.com/address-search"

            html = await self._get(search_url, params={"address": address})
            if not html:
                return results

            soup = BeautifulSoup(html, "html.parser")

            # Look for property cards/results
            for card in soup.select(".property-card, .search-result, tr.property-row"):
                try:
                    pin = card.select_one(".pin, [data-pin], .parcel-number")
                    addr = card.select_one(".address, .property-address")

                    if not pin:
                        continue

                    pin_text = pin.get_text(strip=True) or pin.get("data-pin", "")

                    record = PropertyRecord(
                        parcel_id=pin_text,
                        address=addr.get_text(strip=True) if addr else None,
                        city=city or "Chicago",
                        state="IL",
                        county="Cook County",
                        fips_code="17031",
                    )
                    results.append(record)
                except (AttributeError, ValueError):
                    continue

        except Exception:
            pass

        return results

    async def search_property_by_owner(self, owner_name: str) -> List[PropertyRecord]:
        """
        Search Cook County Assessor by owner name.
        """
        await self._ensure_session()
        results = []

        try:
            # Try API endpoint
            search_url = f"{self.ASSESSOR_API}/owner-search"

            params = {
                "q": owner_name,
                "limit": 100,
            }

            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    for item in data.get(
                        "results", data if isinstance(data, list) else []
                    ):
                        try:
                            pin = item.get("pin", item.get("PIN", ""))
                            if not pin:
                                continue

                            record = PropertyRecord(
                                parcel_id=str(pin),
                                address=item.get("address"),
                                city=item.get("city", "Chicago"),
                                state="IL",
                                owner_name=item.get("owner_name", owner_name),
                                assessed_value=self._parse_currency(
                                    item.get("assessed_value")
                                ),
                                market_value=self._parse_currency(
                                    item.get("market_value")
                                ),
                                property_class=item.get("class"),
                                township=item.get("township"),
                                county="Cook County",
                                fips_code="17031",
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
        Get property details by PIN (Property Index Number).

        Cook County PINs are 14-digit numbers in format: XX-XX-XXX-XXX-XXXX
        """
        await self._ensure_session()

        # Clean PIN - remove dashes if present
        pin = re.sub(r"[^0-9]", "", parcel_id)

        try:
            # Direct PIN lookup
            detail_url = f"https://www.cookcountyassessor.com/pin/{pin}"

            html = await self._get(detail_url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            # Extract property details from page
            record = PropertyRecord(
                parcel_id=pin,
                county="Cook County",
                state="IL",
                fips_code="17031",
            )

            # Try to find data in JSON-LD or structured data
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if data.get("@type") == "RealEstateListing":
                        record.address = data.get("address", {}).get("streetAddress")
                        record.city = data.get("address", {}).get("addressLocality")
                        record.zip_code = data.get("address", {}).get("postalCode")
                except (json.JSONDecodeError, TypeError):
                    continue

            # Parse from HTML structure
            address_el = soup.select_one(".property-address, .address, h1")
            if address_el:
                record.address = address_el.get_text(strip=True)

            owner_el = soup.select_one(".owner-name, .taxpayer")
            if owner_el:
                record.owner_name = self._clean_name(owner_el.get_text(strip=True))

            # Look for property characteristics table
            for row in soup.select("tr, .detail-row"):
                label = row.select_one("th, .label, td:first-child")
                value = row.select_one("td:last-child, .value")

                if not label or not value:
                    continue

                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)

                if "assessed" in label_text and "value" in label_text:
                    record.assessed_value = self._parse_currency(value_text)
                elif "market" in label_text and "value" in label_text:
                    record.market_value = self._parse_currency(value_text)
                elif "land" in label_text and "value" in label_text:
                    record.land_value = self._parse_currency(value_text)
                elif "building" in label_text and "value" in label_text:
                    record.improvement_value = self._parse_currency(value_text)
                elif "class" in label_text:
                    record.property_class = value_text
                elif "township" in label_text:
                    record.township = value_text
                elif "year built" in label_text:
                    try:
                        record.year_built = int(value_text)
                    except ValueError:
                        pass
                elif "sq" in label_text and "ft" in label_text:
                    try:
                        record.building_sqft = int(re.sub(r"[^0-9]", "", value_text))
                    except ValueError:
                        pass

            return record

        except aiohttp.ClientError:
            pass

        return None

    # ==================== Recorder Methods ====================

    async def search_deeds_by_name(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        as_grantor: bool = True,
        as_grantee: bool = True,
    ) -> List[DeedRecord]:
        """
        Search Cook County Recorder by party name.

        The recorder's office has documents from 1985 to present online.
        """
        await self._ensure_session()
        results = []

        try:
            # Cook County Recorder search
            search_url = "https://recorder.cookcounty.gov/recordersearch/Search/Search"

            # Format dates
            start = start_date.strftime("%m/%d/%Y") if start_date else "01/01/1985"
            end = (
                end_date.strftime("%m/%d/%Y")
                if end_date
                else datetime.now().strftime("%m/%d/%Y")
            )

            # Build search parameters
            search_data = {
                "SearchType": "Name",
                "LastName": name.upper(),
                "FirstName": "",
                "MiddleName": "",
                "StartDate": start,
                "EndDate": end,
                "SearchGrantor": "true" if as_grantor else "false",
                "SearchGrantee": "true" if as_grantee else "false",
            }

            # Post search request
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json, text/html",
            }

            html = await self._post(search_url, data=search_data, headers=headers)
            if not html:
                return results

            # Try to parse as JSON first
            try:
                data = json.loads(html)
                for item in data.get("results", []):
                    record = self._parse_recorder_result(item)
                    if record:
                        results.append(record)
            except json.JSONDecodeError:
                # Parse HTML results
                soup = BeautifulSoup(html, "html.parser")
                for row in soup.select("tr.result-row, .document-result"):
                    record = self._parse_recorder_html_row(row)
                    if record:
                        results.append(record)

        except aiohttp.ClientError:
            pass

        return results

    def _parse_recorder_result(self, item: Dict[str, Any]) -> Optional[DeedRecord]:
        """Parse a recorder search result from JSON."""
        try:
            doc_num = item.get("documentNumber", item.get("doc_number", ""))
            if not doc_num:
                return None

            record = DeedRecord(
                document_number=str(doc_num),
                record_type=item.get("documentType", item.get("doc_type", "Unknown")),
                grantor=item.get("grantor"),
                grantee=item.get("grantee"),
                consideration=self._parse_currency(item.get("consideration")),
                book=item.get("book"),
                page=item.get("page"),
                parcel_id=item.get("pin"),
                legal_description=item.get("legalDescription"),
                county="Cook County",
                state="IL",
                fips_code="17031",
                raw_data=item,
            )

            # Parse dates
            record.recording_date = self._parse_date(
                item.get("recordingDate", item.get("rec_date"))
            )
            record.document_date = self._parse_date(
                item.get("documentDate", item.get("doc_date"))
            )

            return record
        except (KeyError, ValueError):
            return None

    def _parse_recorder_html_row(self, row) -> Optional[DeedRecord]:
        """Parse a recorder search result from HTML row."""
        try:
            cells = row.select("td")
            if len(cells) < 4:
                return None

            doc_num = cells[0].get_text(strip=True)
            if not doc_num:
                return None

            record = DeedRecord(
                document_number=doc_num,
                record_type=(
                    cells[1].get_text(strip=True) if len(cells) > 1 else "Unknown"
                ),
                recording_date=(
                    self._parse_date(cells[2].get_text(strip=True))
                    if len(cells) > 2
                    else None
                ),
                grantor=cells[3].get_text(strip=True) if len(cells) > 3 else None,
                grantee=cells[4].get_text(strip=True) if len(cells) > 4 else None,
                consideration=(
                    self._parse_currency(cells[5].get_text(strip=True))
                    if len(cells) > 5
                    else 0.0
                ),
                county="Cook County",
                state="IL",
                fips_code="17031",
            )

            return record
        except (AttributeError, IndexError, ValueError):
            return None

    async def search_deeds_by_parcel(
        self,
        parcel_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[DeedRecord]:
        """
        Search Cook County Recorder by PIN.
        """
        await self._ensure_session()
        results = []

        # Clean PIN
        pin = re.sub(r"[^0-9]", "", parcel_id)

        try:
            search_url = "https://recorder.cookcounty.gov/recordersearch/Search/Search"

            start = start_date.strftime("%m/%d/%Y") if start_date else "01/01/1985"
            end = (
                end_date.strftime("%m/%d/%Y")
                if end_date
                else datetime.now().strftime("%m/%d/%Y")
            )

            search_data = {
                "SearchType": "PIN",
                "PIN": pin,
                "StartDate": start,
                "EndDate": end,
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }

            html = await self._post(search_url, data=search_data, headers=headers)
            if not html:
                return results

            try:
                data = json.loads(html)
                for item in data.get("results", []):
                    record = self._parse_recorder_result(item)
                    if record:
                        results.append(record)
            except json.JSONDecodeError:
                soup = BeautifulSoup(html, "html.parser")
                for row in soup.select("tr.result-row, .document-result"):
                    record = self._parse_recorder_html_row(row)
                    if record:
                        results.append(record)

        except aiohttp.ClientError:
            pass

        return results

    # ==================== Court Methods ====================

    async def search_court_cases_by_name(
        self,
        name: str,
        case_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CourtCase]:
        """
        Search Cook County court cases by party name.

        Cook County has separate divisions for civil, criminal, etc.
        """
        await self._ensure_session()
        results = []

        try:
            # Cook County uses a portal system
            search_url = "https://cccportal.cookcountyclerkofcourt.org/CCCPortal/Hearing/SearchParty"

            search_data = {
                "PartyName": name.upper(),
                "PartyType": "Both",  # Plaintiff and Defendant
                "Division": case_type or "All",
            }

            if start_date:
                search_data["StartDate"] = start_date.strftime("%m/%d/%Y")
            if end_date:
                search_data["EndDate"] = end_date.strftime("%m/%d/%Y")

            html = await self._post(search_url, data=search_data)
            if not html:
                return results

            soup = BeautifulSoup(html, "html.parser")

            # Parse case results
            for row in soup.select("tr.case-row, .case-result, tbody tr"):
                try:
                    cells = row.select("td")
                    if len(cells) < 3:
                        continue

                    case_num = cells[0].get_text(strip=True)
                    if not case_num or case_num.lower() == "case number":
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
                        county="Cook County",
                        state="IL",
                        fips_code="17031",
                    )

                    # Try to extract parties from case title
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
        Get Cook County court case by case number.
        """
        await self._ensure_session()

        try:
            # Direct case lookup
            detail_url = f"https://cccportal.cookcountyclerkofcourt.org/CCCPortal/Hearing/CaseDetail/{case_number}"

            html = await self._get(detail_url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            case = CourtCase(
                case_number=case_number,
                case_type="Unknown",
                county="Cook County",
                state="IL",
                fips_code="17031",
            )

            # Parse case details
            for row in soup.select(".detail-row, tr"):
                label = row.select_one(".label, th, td:first-child")
                value = row.select_one(".value, td:last-child")

                if not label or not value:
                    continue

                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)

                if "case type" in label_text or "division" in label_text:
                    case.case_type = value_text
                elif "status" in label_text:
                    case.status = value_text
                elif "filing date" in label_text:
                    case.filing_date = self._parse_date(value_text)
                elif "judge" in label_text:
                    case.judge = value_text
                elif "plaintiff" in label_text:
                    case.plaintiff = self._clean_name(value_text)
                elif "defendant" in label_text:
                    case.defendant = self._clean_name(value_text)

            # Parse parties table
            parties_table = soup.select_one(".parties-table, #parties")
            if parties_table:
                for party_row in parties_table.select("tr"):
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

            # Parse docket entries
            docket_table = soup.select_one(".docket-table, #docket")
            if docket_table:
                for entry_row in docket_table.select("tr"):
                    cells = entry_row.select("td")
                    if len(cells) >= 2:
                        case.docket_entries.append(
                            {
                                "date": cells[0].get_text(strip=True),
                                "entry": cells[1].get_text(strip=True),
                            }
                        )

            return case

        except aiohttp.ClientError:
            pass

        return None

    # ==================== Tax/Treasurer Methods ====================

    async def get_tax_info(self, parcel_id: str) -> Optional[TaxRecord]:
        """
        Get tax information from Cook County Treasurer.
        """
        await self._ensure_session()

        # Clean PIN
        pin = re.sub(r"[^0-9]", "", parcel_id)

        try:
            search_url = f"https://www.cookcountytreasurer.com/setsearchparameters.aspx?pin={pin}"

            html = await self._get(search_url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")

            record = TaxRecord(
                parcel_id=pin,
                tax_year=datetime.now().year,
                county="Cook County",
                state="IL",
                fips_code="17031",
            )

            # Parse tax info
            for row in soup.select("tr, .tax-row"):
                label = row.select_one("th, .label, td:first-child")
                value = row.select_one("td:last-child, .value")

                if not label or not value:
                    continue

                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)

                if "taxpayer" in label_text or "owner" in label_text:
                    record.owner_name = self._clean_name(value_text)
                elif "property" in label_text and "address" in label_text:
                    record.property_address = value_text
                elif "assessed" in label_text:
                    record.assessed_value = self._parse_currency(value_text)
                elif "tax amount" in label_text or "total tax" in label_text:
                    record.tax_amount = self._parse_currency(value_text)
                elif "amount due" in label_text or "balance" in label_text:
                    record.amount_due = self._parse_currency(value_text)
                elif "amount paid" in label_text:
                    record.amount_paid = self._parse_currency(value_text)
                elif "status" in label_text:
                    record.status = value_text
                elif "tax year" in label_text:
                    try:
                        record.tax_year = int(value_text)
                    except ValueError:
                        pass

            # Check for exemptions
            exemptions = soup.select(".exemption, [data-exemption]")
            for ex in exemptions:
                record.exemptions.append(ex.get_text(strip=True))

            return record

        except aiohttp.ClientError:
            pass

        return None

    # ==================== Foreclosure/Eviction Methods ====================

    async def search_foreclosures(
        self,
        address: Optional[str] = None,
        owner: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CourtCase]:
        """
        Search Cook County foreclosure cases.

        Foreclosures are filed in Chancery Division.
        """
        results = []

        # Search by owner name in Chancery Division
        if owner:
            cases = await self.search_court_cases_by_name(
                name=owner,
                case_type="CH",  # Chancery Division
                start_date=start_date,
                end_date=end_date,
            )

            # Filter to foreclosure cases
            for case in cases:
                case_type_lower = (case.case_type or "").lower()
                case_title_lower = (case.case_title or "").lower()

                if (
                    "foreclosure" in case_type_lower
                    or "foreclosure" in case_title_lower
                ):
                    results.append(case)

        return results

    async def search_evictions(
        self,
        address: Optional[str] = None,
        tenant: Optional[str] = None,
        landlord: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CourtCase]:
        """
        Search Cook County eviction cases.

        Evictions are filed in First Municipal District (M1).
        """
        results = []

        search_name = tenant or landlord

        if search_name:
            cases = await self.search_court_cases_by_name(
                name=search_name,
                case_type="M1",  # Municipal First District
                start_date=start_date,
                end_date=end_date,
            )

            # Filter to eviction cases
            for case in cases:
                case_type_lower = (case.case_type or "").lower()
                case_title_lower = (case.case_title or "").lower()

                if "eviction" in case_type_lower or "forcible" in case_title_lower:
                    results.append(case)

        return results


# Synchronous wrapper functions
def search_cook_county_property_sync(
    address: Optional[str] = None,
    owner: Optional[str] = None,
    pin: Optional[str] = None,
) -> List[PropertyRecord]:
    """Synchronous wrapper for Cook County property search."""

    async def _search():
        async with CookCountyScraper() as scraper:
            if pin:
                result = await scraper.search_property_by_parcel(pin)
                return [result] if result else []
            elif owner:
                return await scraper.search_property_by_owner(owner)
            elif address:
                return await scraper.search_property_by_address(address)
            return []

    return asyncio.run(_search())


def search_cook_county_deeds_sync(
    name: Optional[str] = None, parcel_id: Optional[str] = None
) -> List[DeedRecord]:
    """Synchronous wrapper for Cook County deed search."""

    async def _search():
        async with CookCountyScraper() as scraper:
            if parcel_id:
                return await scraper.search_deeds_by_parcel(parcel_id)
            elif name:
                return await scraper.search_deeds_by_name(name)
            return []

    return asyncio.run(_search())


def search_cook_county_cases_sync(
    name: Optional[str] = None, case_number: Optional[str] = None
) -> List[CourtCase]:
    """Synchronous wrapper for Cook County court case search."""

    async def _search():
        async with CookCountyScraper() as scraper:
            if case_number:
                result = await scraper.search_court_cases_by_number(case_number)
                return [result] if result else []
            elif name:
                return await scraper.search_court_cases_by_name(name)
            return []

    return asyncio.run(_search())


# Export
__all__ = [
    "CookCountyScraper",
    "COOK_COUNTY_CONFIG",
    "search_cook_county_property_sync",
    "search_cook_county_deeds_sync",
    "search_cook_county_cases_sync",
]
