"""
Los Angeles County, California Assessor Scraper

Los Angeles County is the most populous county in the US with approximately
10 million residents and 2.5 million parcels.

Website: https://assessor.lacounty.gov/
APN Format: XXXX-XXX-XXX (10 digits with dashes)
           Book-Page-Parcel

The LA County Assessor provides:
- Property characteristics
- Assessment values
- Sales history
- Tax exemptions
- Ownership information
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


class LosAngelesCountyAssessor(CountyAssessorBase):
    """
    Los Angeles County, California Assessor scraper.

    Uses the LA County Assessor's public portal and APIs.
    """

    COUNTY_NAME = "Los Angeles County"
    STATE = "CA"
    FIPS_CODE = "06037"
    BASE_URL = "https://assessor.lacounty.gov/"
    SYSTEM_NAME = "LA County Assessor Portal"

    # APN format: XXXX-XXX-XXX (Book-Page-Parcel)
    PARCEL_ID_FORMAT = "XXXX-XXX-XXX (10 digits)"
    PARCEL_ID_PATTERN = r"^\d{4}-\d{3}-\d{3}$"

    # API endpoints
    PORTAL_URL = "https://portal.assessor.lacounty.gov/"
    API_BASE = "https://portal.assessor.lacounty.gov/api/"

    # Regional Assessment offices
    REGIONAL_OFFICES = {
        "CENTRAL": "Central District - Downtown LA",
        "WEST": "West District - Culver City",
        "SOUTH": "South District - Norwalk",
        "EAST": "East District - Pomona",
        "NORTH": "North District - Van Nuys",
    }

    def _format_apn(self, apn: str) -> str:
        """Format an APN with dashes if not already formatted."""
        # Remove existing dashes, spaces, and periods
        clean = apn.replace("-", "").replace(" ", "").replace(".", "").strip()

        if len(clean) == 10:
            return f"{clean[:4]}-{clean[4:7]}-{clean[7:10]}"
        return apn

    def _validate_apn(self, apn: str) -> bool:
        """Validate a Los Angeles County APN format."""
        formatted = self._format_apn(apn)
        return bool(re.match(self.PARCEL_ID_PATTERN, formatted))

    def _get_map_book(self, apn: str) -> str:
        """Extract map book number from APN."""
        formatted = self._format_apn(apn)
        return formatted.split("-")[0] if "-" in formatted else ""

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

        search_url = f"{self.API_BASE}parcel/search"

        # Build address search string
        address_parts = [street_address]
        if city:
            address_parts.append(city)
        if zip_code:
            address_parts.append(zip_code)

        params = {
            "address": " ".join(address_parts),
            "limit": min(max_results, 100),
        }

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"LA County address search failed: {e}")
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
        results = json_response.get("parcels", json_response.get("results", []))

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
        """Search for a property by APN."""
        formatted_apn = self._format_apn(parcel_id)

        if not self._validate_apn(formatted_apn):
            logger.warning(f"Invalid LA County APN format: {parcel_id}")
            return None

        return await self.get_property_detail(formatted_apn)

    async def search_by_owner(
        self, owner_name: str, max_results: int = 100
    ) -> AssessorSearchResult:
        """Search for properties by owner name."""
        import time

        start_time = time.time()

        search_url = f"{self.API_BASE}parcel/search"

        params = {
            "owner": owner_name,
            "limit": min(max_results, 100),
        }

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"LA County owner search failed: {e}")
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
        results = json_response.get("parcels", json_response.get("results", []))

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
        formatted_apn = self._format_apn(parcel_id)

        # Remove dashes for API call
        apn_clean = formatted_apn.replace("-", "")
        detail_url = f"{self.API_BASE}parcel/{apn_clean}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"LA County property detail failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_property_detail(json_response, formatted_apn)

    def _parse_search_result(
        self, item: Dict[str, Any]
    ) -> Optional[PropertyAssessment]:
        """Parse a search result item."""
        apn = item.get("ain", item.get("apn", ""))
        if not apn:
            return None

        formatted_apn = self._format_apn(str(apn))

        return PropertyAssessment(
            parcel_id=formatted_apn,
            property_address=item.get("situsAddress", item.get("address", "")),
            city=item.get("situsCity", item.get("city", "")),
            state=self.STATE,
            zip_code=item.get("situsZip", item.get("zip", "")),
            county=self.COUNTY_NAME,
            property_type=self._parse_property_type(item.get("useCode", "")),
            assessed_value=self._parse_decimal(
                str(item.get("assessedValue", item.get("totalValue", "")))
            ),
            market_value=self._parse_decimal(str(item.get("marketValue", ""))),
            current_owner=(
                OwnershipRecord(
                    owner_name=item.get("ownerName", item.get("owner", "")),
                )
                if item.get("ownerName") or item.get("owner")
                else None
            ),
            source_url=f"{self.PORTAL_URL}parceldetail/{self._format_apn(str(apn)).replace('-', '')}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_property_detail(
        self, data: Dict[str, Any], apn: str
    ) -> PropertyAssessment:
        """Parse detailed property data."""
        # Parse characteristics
        chars = data.get("characteristics", data.get("propertyInfo", {}))
        characteristics = PropertyCharacteristics(
            year_built=self._parse_int(
                str(chars.get("yearBuilt", chars.get("effectiveYearBuilt", "")))
            ),
            building_sqft=self._parse_int(
                str(chars.get("buildingSqft", chars.get("improvementSqft", "")))
            ),
            living_sqft=self._parse_int(
                str(chars.get("livingSqft", chars.get("livingArea", "")))
            ),
            bedrooms=self._parse_int(
                str(chars.get("bedrooms", chars.get("numberOfBedrooms", "")))
            ),
            bathrooms=self._parse_float(
                str(chars.get("bathrooms", chars.get("totalBathrooms", "")))
            ),
            full_baths=self._parse_int(str(chars.get("fullBaths", ""))),
            half_baths=self._parse_int(str(chars.get("halfBaths", ""))),
            stories=self._parse_float(
                str(chars.get("stories", chars.get("numberOfStories", "")))
            ),
            basement=chars.get("basement", chars.get("basementType")),
            garage_type=chars.get("garageType", chars.get("parkingType")),
            garage_spaces=self._parse_int(
                str(chars.get("garageSpaces", chars.get("parkingSpaces", "")))
            ),
            lot_sqft=self._parse_int(
                str(chars.get("lotSqft", chars.get("landArea", "")))
            ),
            lot_acres=self._parse_float(str(chars.get("lotAcres", ""))),
            construction_type=chars.get("constructionType", chars.get("construction")),
            exterior_wall=chars.get("exteriorWall", chars.get("exterior")),
            roof_type=chars.get("roofType", chars.get("roofCover")),
            central_air=chars.get("centralAir", chars.get("airConditioning", False)),
            heating_type=chars.get("heatingType", chars.get("heating")),
            pool=chars.get("pool", chars.get("hasPool", False)),
            fireplace_count=self._parse_int(
                str(chars.get("fireplaces", chars.get("numberOfFireplaces", "")))
            ),
            raw_characteristics=chars,
        )

        # Parse assessment/value history
        assessment_history = []
        for assessment in data.get("valueHistory", data.get("assessmentHistory", [])):
            tax_assessment = TaxAssessment(
                tax_year=assessment.get("rollYear", assessment.get("year", 0)),
                assessed_value_land=self._parse_decimal(
                    str(assessment.get("landValue", ""))
                ),
                assessed_value_improvements=self._parse_decimal(
                    str(assessment.get("improvementValue", ""))
                ),
                assessed_value_total=self._parse_decimal(
                    str(
                        assessment.get(
                            "totalValue", assessment.get("assessedValue", "")
                        )
                    )
                ),
                market_value_total=self._parse_decimal(
                    str(assessment.get("marketValue", ""))
                ),
            )
            assessment_history.append(tax_assessment)

        # Parse sales/transfer history
        sales_history = []
        for sale in data.get("salesHistory", data.get("transferHistory", [])):
            sale_record = SaleRecord(
                sale_date=self._parse_date(
                    sale.get("recordingDate", sale.get("saleDate", ""))
                )
                or date.today(),
                sale_price=self._parse_decimal(
                    str(sale.get("documentAmount", sale.get("salePrice", "")))
                )
                or Decimal(0),
                buyer_name=sale.get("grantee", sale.get("buyer")),
                seller_name=sale.get("grantor", sale.get("seller")),
                document_number=sale.get("documentNumber", sale.get("docNumber")),
                document_type=sale.get("documentType", sale.get("deedType")),
            )
            sales_history.append(sale_record)

        # Parse ownership
        owner_data = data.get("owner", data.get("ownerInfo", {}))
        if isinstance(owner_data, str):
            owner_data = {"name": owner_data}

        current_owner = (
            OwnershipRecord(
                owner_name=owner_data.get("name", owner_data.get("ownerName", "")),
                mailing_address=owner_data.get(
                    "mailingAddress", owner_data.get("address")
                ),
                mailing_city=owner_data.get("mailingCity", owner_data.get("city")),
                mailing_state=owner_data.get("mailingState", owner_data.get("state")),
                mailing_zip=owner_data.get("mailingZip", owner_data.get("zip")),
            )
            if owner_data.get("name") or owner_data.get("ownerName")
            else None
        )

        # Parse exemptions
        exemptions = []
        for exemption in data.get("exemptions", []):
            exemption_type = exemption.get(
                "type", exemption.get("exemptionType", "")
            ).upper()
            if "HOMEOWNER" in exemption_type or "HOMESTEAD" in exemption_type:
                exemptions.append(ExemptionType.HOMESTEAD)
            elif "SENIOR" in exemption_type:
                exemptions.append(ExemptionType.SENIOR_CITIZEN)
            elif "VETERAN" in exemption_type or "VET" in exemption_type:
                exemptions.append(ExemptionType.VETERAN)
            elif "DISABLED" in exemption_type:
                exemptions.append(ExemptionType.DISABILITY)
            elif "CHURCH" in exemption_type or "RELIGIOUS" in exemption_type:
                exemptions.append(ExemptionType.RELIGIOUS)
            elif "NONPROFIT" in exemption_type or "CHARITABLE" in exemption_type:
                exemptions.append(ExemptionType.CHARITABLE)

        # Get current assessment
        current_assessment = assessment_history[0] if assessment_history else None

        # Build property URL
        apn_clean = apn.replace("-", "")

        return PropertyAssessment(
            parcel_id=apn,
            property_address=data.get("situsAddress", data.get("address", "")),
            city=data.get("situsCity", data.get("city", "")),
            state=self.STATE,
            zip_code=data.get("situsZip", data.get("zip", "")),
            county=self.COUNTY_NAME,
            legal_description=data.get("legalDescription"),
            subdivision=data.get("tractName", data.get("subdivision")),
            property_type=self._parse_property_type(
                data.get("useCode", data.get("propertyType", ""))
            ),
            property_use=data.get("useDescription", data.get("propertyUse")),
            zoning=data.get("zoning", data.get("zoningCode")),
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
            neighborhood=data.get("neighborhoodCode"),
            source_url=f"{self.PORTAL_URL}parceldetail/{apn_clean}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

    def _parse_property_type(self, use_code: str) -> Optional[PropertyType]:
        """Parse LA County use codes to PropertyType."""
        if not use_code:
            return None

        use_upper = str(use_code).upper()

        # LA County use code patterns
        if use_upper.startswith("01") or "SINGLE" in use_upper:
            return PropertyType.SINGLE_FAMILY
        elif use_upper.startswith("02") or "DUPLEX" in use_upper:
            return PropertyType.MULTI_FAMILY
        elif (
            use_upper.startswith("03")
            or "TRIPLEX" in use_upper
            or "FOURPLEX" in use_upper
        ):
            return PropertyType.MULTI_FAMILY
        elif use_upper.startswith("04") or "APARTMENT" in use_upper:
            return PropertyType.MULTI_FAMILY
        elif use_upper.startswith("05") or "CONDO" in use_upper:
            return PropertyType.CONDOMINIUM
        elif use_upper.startswith("06") or "MOBILE" in use_upper:
            return PropertyType.MOBILE_HOME
        elif use_upper.startswith("1") or "COMMERCIAL" in use_upper:
            return PropertyType.COMMERCIAL
        elif use_upper.startswith("2") or "INDUSTRIAL" in use_upper:
            return PropertyType.INDUSTRIAL
        elif use_upper.startswith("3") or "OFFICE" in use_upper:
            return PropertyType.COMMERCIAL
        elif use_upper.startswith("4") or "RETAIL" in use_upper:
            return PropertyType.COMMERCIAL
        elif use_upper.startswith("6") or "AGRICULTURAL" in use_upper:
            return PropertyType.AGRICULTURAL
        elif "VACANT" in use_upper or "LAND" in use_upper:
            return PropertyType.VACANT_LAND
        elif "TOWNHOME" in use_upper or "TOWNHOUSE" in use_upper:
            return PropertyType.TOWNHOUSE

        return None


# Convenience functions


def search_la_county_address(address: str, **kwargs) -> AssessorSearchResult:
    """Search Los Angeles County properties by address."""
    assessor = LosAngelesCountyAssessor()

    async def _search():
        async with assessor:
            return await assessor.search_by_address(address, **kwargs)

    return asyncio.run(_search())


def search_la_county_owner(owner_name: str, **kwargs) -> AssessorSearchResult:
    """Search Los Angeles County properties by owner name."""
    assessor = LosAngelesCountyAssessor()

    async def _search():
        async with assessor:
            return await assessor.search_by_owner(owner_name, **kwargs)

    return asyncio.run(_search())


def get_la_county_property(apn: str) -> Optional[PropertyAssessment]:
    """Get Los Angeles County property details by APN."""
    assessor = LosAngelesCountyAssessor()

    async def _get():
        async with assessor:
            return await assessor.get_property_detail(apn)

    return asyncio.run(_get())
