"""
Harris County, Texas Appraisal District Scraper

Harris County (Houston) is the third most populous county in the US with
approximately 4.7 million residents and 1.8 million parcels.

Website: https://hcad.org/
Account Format: XXXXXXXXX-XXX-XXX (Account Number with optional suffix)
                Map ID: XXX-XXX-XXX-XXXX

The Harris County Appraisal District (HCAD) provides:
- Property characteristics
- Appraisal values (annual cycle)
- Sales/deed history
- Tax exemptions
- Ownership information
- Building sketches
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aiohttp

from .base import (
    AssessorSearchCriteria,
    AssessorSearchResult,
    CountyAssessorBase,
    ExemptionType,
    OwnershipRecord,
    PropertyAssessment,
    PropertyCharacteristics,
    PropertyClass,
    PropertyType,
    SaleRecord,
    TaxAssessment,
)

logger = logging.getLogger(__name__)


class HarrisCountyAssessor(CountyAssessorBase):
    """
    Harris County, Texas Appraisal District scraper.

    Uses HCAD's public property search and APIs.
    """

    COUNTY_NAME = "Harris County"
    STATE = "TX"
    FIPS_CODE = "48201"
    BASE_URL = "https://hcad.org/"
    SYSTEM_NAME = "Harris County Appraisal District (HCAD)"

    # Account number format (varies)
    PARCEL_ID_FORMAT = "Account Number (varies) or Map ID XXX-XXX-XXX-XXXX"
    PARCEL_ID_PATTERN = r"^\d{7,15}$"

    # API/Search endpoints
    SEARCH_URL = "https://public.hcad.org/records/search.asp"
    DETAIL_URL = "https://public.hcad.org/records/Real.asp"
    API_BASE = "https://pdata.hcad.org/api/"

    # Property state codes
    STATE_CODES = {
        "A": "Real Property - Residential",
        "B": "Real Property - Multi-Family",
        "C": "Real Property - Vacant Land",
        "D": "Real Property - Commercial",
        "E": "Real Property - Industrial",
        "F": "Real Property - Farm/Ranch",
        "G": "Real Property - Mineral",
        "H": "Real Property - Oil & Gas",
        "J": "Utilities",
        "L": "Personal Property - Commercial",
        "M": "Personal Property - Mobile Home",
        "O": "Personal Property - Other",
    }

    # School district codes
    SCHOOL_DISTRICTS = {
        "001": "Houston ISD",
        "002": "Aldine ISD",
        "003": "Alief ISD",
        "004": "Clear Creek ISD",
        "005": "Crosby ISD",
        "006": "Cypress-Fairbanks ISD",
        "007": "Deer Park ISD",
        "008": "Fort Bend ISD",
        "009": "Galena Park ISD",
        "010": "Goose Creek CISD",
        "011": "Huffman ISD",
        "012": "Humble ISD",
        "013": "Katy ISD",
        "014": "Klein ISD",
        "015": "La Porte ISD",
        "016": "Pasadena ISD",
        "017": "Sheldon ISD",
        "018": "Spring ISD",
        "019": "Spring Branch ISD",
        "020": "Tomball ISD",
    }

    def _normalize_account(self, account: str) -> str:
        """Normalize an account number by removing non-digits."""
        return re.sub(r"[^\d]", "", account.strip())

    def _validate_account(self, account: str) -> bool:
        """Validate a Harris County account number format."""
        normalized = self._normalize_account(account)
        return bool(re.match(self.PARCEL_ID_PATTERN, normalized))

    async def search_by_address(
        self,
        street_address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        max_results: int = 100,
    ) -> AssessorSearchResult:
        """Search for properties by address."""
        import time

        start_time = time.time()

        search_url = f"{self.API_BASE}property/search"

        # Parse address components
        params = {
            "streetAddress": street_address,
            "limit": min(max_results, 100),
        }

        if city:
            params["city"] = city
        if zip_code:
            params["zip"] = zip_code

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Harris County address search failed: {e}")
            return AssessorSearchResult(
                properties=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=AssessorSearchCriteria(street_address=street_address),
                warnings=[str(e)],
            )

        # Parse results
        properties = []
        results = json_response.get("properties", json_response.get("results", []))

        for item in results[:max_results]:
            prop = self._parse_search_result(item)
            if prop:
                properties.append(prop)

        search_time = int((time.time() - start_time) * 1000)

        return AssessorSearchResult(
            properties=properties,
            total_count=json_response.get("totalCount", len(properties)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=AssessorSearchCriteria(
                street_address=street_address, city=city, zip_code=zip_code
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def search_by_parcel_id(self, parcel_id: str) -> Optional[PropertyAssessment]:
        """Search for a property by account number."""
        normalized = self._normalize_account(parcel_id)

        if not self._validate_account(normalized):
            logger.warning(f"Invalid Harris County account format: {parcel_id}")
            return None

        return await self.get_property_detail(normalized)

    async def search_by_owner(
        self, owner_name: str, max_results: int = 100
    ) -> AssessorSearchResult:
        """Search for properties by owner name."""
        import time

        start_time = time.time()

        search_url = f"{self.API_BASE}property/search"

        # HCAD searches by last name first
        name_parts = owner_name.split(",") if "," in owner_name else owner_name.split()

        params = {
            "ownerName": owner_name,
            "limit": min(max_results, 100),
        }

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Harris County owner search failed: {e}")
            return AssessorSearchResult(
                properties=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=AssessorSearchCriteria(owner_name=owner_name),
                warnings=[str(e)],
            )

        properties = []
        results = json_response.get("properties", json_response.get("results", []))

        for item in results[:max_results]:
            prop = self._parse_search_result(item)
            if prop:
                properties.append(prop)

        search_time = int((time.time() - start_time) * 1000)

        return AssessorSearchResult(
            properties=properties,
            total_count=json_response.get("totalCount", len(properties)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=AssessorSearchCriteria(owner_name=owner_name),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_property_detail(self, parcel_id: str) -> Optional[PropertyAssessment]:
        """Get detailed property information."""
        normalized = self._normalize_account(parcel_id)

        detail_url = f"{self.API_BASE}property/{normalized}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"Harris County property detail failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_property_detail(json_response, normalized)

    def _parse_search_result(
        self, item: Dict[str, Any]
    ) -> Optional[PropertyAssessment]:
        """Parse a search result item."""
        account = item.get("accountNumber", item.get("account", ""))
        if not account:
            return None

        normalized = self._normalize_account(str(account))

        return PropertyAssessment(
            parcel_id=normalized,
            property_address=item.get("situsAddress", item.get("address", "")),
            city=item.get("situsCity", item.get("city", "")),
            state=self.STATE,
            zip_code=item.get("situsZip", item.get("zip", "")),
            county=self.COUNTY_NAME,
            property_type=self._parse_property_type(
                item.get("stateCode", item.get("propertyType", ""))
            ),
            assessed_value=self._parse_decimal(
                str(item.get("appraisedValue", item.get("totalValue", "")))
            ),
            market_value=self._parse_decimal(str(item.get("marketValue", ""))),
            current_owner=(
                OwnershipRecord(
                    owner_name=item.get("ownerName", item.get("owner", "")),
                )
                if item.get("ownerName") or item.get("owner")
                else None
            ),
            source_url=f"{self.DETAIL_URL}?account={normalized}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_property_detail(
        self, data: Dict[str, Any], account: str
    ) -> PropertyAssessment:
        """Parse detailed property data."""
        # Parse characteristics - HCAD provides extensive building data
        chars = data.get("buildingInfo", data.get("characteristics", {}))
        land_info = data.get("landInfo", {})

        characteristics = PropertyCharacteristics(
            year_built=self._parse_int(
                str(chars.get("yearBuilt", chars.get("effectiveYear", "")))
            ),
            building_sqft=self._parse_int(
                str(chars.get("totalArea", chars.get("buildingSqft", "")))
            ),
            living_sqft=self._parse_int(
                str(chars.get("livingArea", chars.get("mainArea", "")))
            ),
            bedrooms=self._parse_int(
                str(chars.get("bedrooms", chars.get("numberOfBedrooms", "")))
            ),
            bathrooms=self._parse_float(str(chars.get("bathrooms", ""))),
            full_baths=self._parse_int(
                str(chars.get("fullBaths", chars.get("fullBathrooms", "")))
            ),
            half_baths=self._parse_int(
                str(chars.get("halfBaths", chars.get("halfBathrooms", "")))
            ),
            stories=self._parse_float(
                str(chars.get("stories", chars.get("numberOfStories", "")))
            ),
            basement=chars.get("basement", chars.get("basementDescription")),
            garage_type=chars.get("garageType", chars.get("garageDescription")),
            garage_spaces=self._parse_int(
                str(chars.get("garageCapacity", chars.get("garageSpaces", "")))
            ),
            lot_sqft=self._parse_int(
                str(land_info.get("landArea", land_info.get("lotSqft", "")))
            ),
            lot_acres=self._parse_float(str(land_info.get("acres", ""))),
            construction_type=chars.get("constructionType", chars.get("frameType")),
            exterior_wall=chars.get("exteriorWall", chars.get("exteriorType")),
            roof_type=chars.get("roofType", chars.get("roofDescription")),
            foundation_type=chars.get("foundationType", chars.get("foundation")),
            central_air=chars.get("centralAir") == "Y"
            or chars.get("airConditioning") == "Yes",
            heating_type=chars.get("heatingType", chars.get("heatType")),
            pool=chars.get("pool") == "Y" or chars.get("hasPool", False),
            fireplace_count=self._parse_int(
                str(chars.get("fireplaces", chars.get("numberOfFireplaces", "")))
            ),
            raw_characteristics=chars,
        )

        # Parse appraisal/value history
        assessment_history = []
        for assessment in data.get("valueHistory", data.get("appraisalHistory", [])):
            tax_assessment = TaxAssessment(
                tax_year=assessment.get("taxYear", assessment.get("year", 0)),
                assessed_value_land=self._parse_decimal(
                    str(
                        assessment.get("landValue", assessment.get("landAppraisal", ""))
                    )
                ),
                assessed_value_improvements=self._parse_decimal(
                    str(
                        assessment.get(
                            "improvementValue", assessment.get("buildingAppraisal", "")
                        )
                    )
                ),
                assessed_value_total=self._parse_decimal(
                    str(
                        assessment.get(
                            "totalAppraisal", assessment.get("appraisedValue", "")
                        )
                    )
                ),
                market_value_total=self._parse_decimal(
                    str(assessment.get("marketValue", ""))
                ),
                taxable_value=self._parse_decimal(
                    str(assessment.get("taxableValue", ""))
                ),
            )
            assessment_history.append(tax_assessment)

        # Parse deed/sales history
        sales_history = []
        for sale in data.get("deedHistory", data.get("salesHistory", [])):
            sale_record = SaleRecord(
                sale_date=self._parse_date(
                    sale.get("deedDate", sale.get("saleDate", ""))
                )
                or date.today(),
                sale_price=self._parse_decimal(
                    str(sale.get("consideration", sale.get("salePrice", "")))
                )
                or Decimal(0),
                buyer_name=sale.get("grantee", sale.get("buyer")),
                seller_name=sale.get("grantor", sale.get("seller")),
                document_number=sale.get("deedVolPage", sale.get("docNumber")),
                document_type=sale.get("deedType", sale.get("documentType")),
            )
            sales_history.append(sale_record)

        # Parse ownership
        owner_data = data.get("owner", data.get("ownerInfo", {}))
        if isinstance(owner_data, str):
            owner_data = {"name": owner_data}

        current_owner = (
            OwnershipRecord(
                owner_name=owner_data.get(
                    "name", owner_data.get("ownerName", data.get("ownerName", ""))
                ),
                mailing_address=owner_data.get(
                    "mailingAddress", owner_data.get("address")
                ),
                mailing_city=owner_data.get("mailingCity", owner_data.get("city")),
                mailing_state=owner_data.get("mailingState", owner_data.get("state")),
                mailing_zip=owner_data.get("mailingZip", owner_data.get("zip")),
            )
            if owner_data.get("name")
            or owner_data.get("ownerName")
            or data.get("ownerName")
            else None
        )

        # Parse exemptions - Texas has many exemption types
        exemptions = []
        exemption_list = data.get("exemptions", [])
        if isinstance(exemption_list, str):
            exemption_list = [{"type": exemption_list}]

        for exemption in exemption_list:
            exemption_type = str(
                exemption.get("type", exemption.get("code", ""))
            ).upper()
            if "HS" in exemption_type or "HOMESTEAD" in exemption_type:
                exemptions.append(ExemptionType.HOMESTEAD)
            elif "OV65" in exemption_type or "OVER 65" in exemption_type:
                exemptions.append(ExemptionType.SENIOR_CITIZEN)
            elif "DP" in exemption_type or "DISABLED" in exemption_type:
                exemptions.append(ExemptionType.DISABILITY)
            elif "DV" in exemption_type or "VETERAN" in exemption_type:
                exemptions.append(ExemptionType.VETERAN)
            elif "AG" in exemption_type or "AGRICULTURAL" in exemption_type:
                exemptions.append(ExemptionType.AGRICULTURAL)
            elif "CH" in exemption_type or "CHARITABLE" in exemption_type:
                exemptions.append(ExemptionType.CHARITABLE)
            elif "REL" in exemption_type or "RELIGIOUS" in exemption_type:
                exemptions.append(ExemptionType.RELIGIOUS)

        # Get current assessment
        current_assessment = assessment_history[0] if assessment_history else None

        # Get school district
        school_code = data.get("schoolDistrictCode", "")
        school_district = self.SCHOOL_DISTRICTS.get(school_code, school_code)

        return PropertyAssessment(
            parcel_id=account,
            property_address=data.get("situsAddress", data.get("address", "")),
            city=data.get("situsCity", data.get("city", "")),
            state=self.STATE,
            zip_code=data.get("situsZip", data.get("zip", "")),
            county=self.COUNTY_NAME,
            legal_description=data.get("legalDescription"),
            subdivision=data.get("subdivision", data.get("neighborhood")),
            property_type=self._parse_property_type(
                data.get("stateCode", data.get("propertyType", ""))
            ),
            property_class=self._parse_property_class(data.get("stateCode", "")),
            property_use=data.get("useDescription", data.get("propertyUse")),
            zoning=data.get("zoning"),
            assessed_value=(
                current_assessment.assessed_value_total if current_assessment else None
            ),
            market_value=(
                current_assessment.market_value_total if current_assessment else None
            ),
            land_value=(
                current_assessment.assessed_value_land if current_assessment else None
            ),
            improvement_value=(
                current_assessment.assessed_value_improvements
                if current_assessment
                else None
            ),
            tax_year=current_assessment.tax_year if current_assessment else None,
            taxable_value=(
                current_assessment.taxable_value if current_assessment else None
            ),
            characteristics=characteristics,
            assessment_history=assessment_history,
            current_owner=current_owner,
            exemptions=exemptions if exemptions else None,
            sales_history=sales_history,
            last_sale_date=sales_history[0].sale_date if sales_history else None,
            last_sale_price=sales_history[0].sale_price if sales_history else None,
            latitude=self._parse_float(str(data.get("latitude", data.get("lat", "")))),
            longitude=self._parse_float(
                str(data.get("longitude", data.get("lng", "")))
            ),
            neighborhood=data.get("neighborhood", data.get("neighborhoodCode")),
            school_district=school_district,
            source_url=f"{self.DETAIL_URL}?account={account}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

    def _parse_property_type(self, state_code: str) -> Optional[PropertyType]:
        """Parse HCAD state codes to PropertyType."""
        if not state_code:
            return None

        code_upper = str(state_code).upper().strip()[:1]

        code_mapping = {
            "A": PropertyType.SINGLE_FAMILY,
            "B": PropertyType.MULTI_FAMILY,
            "C": PropertyType.VACANT_LAND,
            "D": PropertyType.COMMERCIAL,
            "E": PropertyType.INDUSTRIAL,
            "F": PropertyType.AGRICULTURAL,
            "G": PropertyType.MINERAL_RIGHTS,
            "H": PropertyType.MINERAL_RIGHTS,
            "M": PropertyType.MOBILE_HOME,
        }

        return code_mapping.get(code_upper)

    def _parse_property_class(self, state_code: str) -> Optional[PropertyClass]:
        """Parse HCAD state codes to PropertyClass."""
        if not state_code:
            return None

        code_upper = str(state_code).upper().strip()[:1]

        class_mapping = {
            "A": PropertyClass.RESIDENTIAL,
            "B": PropertyClass.RESIDENTIAL,
            "C": PropertyClass.VACANT,
            "D": PropertyClass.COMMERCIAL,
            "E": PropertyClass.INDUSTRIAL,
            "F": PropertyClass.AGRICULTURAL,
            "G": PropertyClass.MINERAL,
            "H": PropertyClass.MINERAL,
            "L": PropertyClass.COMMERCIAL,
            "M": PropertyClass.RESIDENTIAL,
        }

        return class_mapping.get(code_upper)


# Convenience functions


def search_harris_county_address(address: str, **kwargs) -> AssessorSearchResult:
    """Search Harris County properties by address."""
    assessor = HarrisCountyAssessor()

    async def _search():
        async with assessor:
            return await assessor.search_by_address(address, **kwargs)

    return asyncio.run(_search())


def search_harris_county_owner(owner_name: str, **kwargs) -> AssessorSearchResult:
    """Search Harris County properties by owner name."""
    assessor = HarrisCountyAssessor()

    async def _search():
        async with assessor:
            return await assessor.search_by_owner(owner_name, **kwargs)

    return asyncio.run(_search())


def get_harris_county_property(account: str) -> Optional[PropertyAssessment]:
    """Get Harris County property details by account number."""
    assessor = HarrisCountyAssessor()

    async def _get():
        async with assessor:
            return await assessor.get_property_detail(account)

    return asyncio.run(_get())
