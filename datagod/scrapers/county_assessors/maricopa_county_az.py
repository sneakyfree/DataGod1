"""
Maricopa County, Arizona Assessor Scraper

Maricopa County (Phoenix) is the fourth most populous county in the US with
approximately 4.4 million residents and 1.7 million parcels.

Website: https://mcassessor.maricopa.gov/
APN Format: XXX-XX-XXX or XXX-XX-XXXX (with optional suffix)
           Book-Map-Parcel

The Maricopa County Assessor provides:
- Property characteristics
- Assessment values (annual cycle)
- Sales history
- Tax exemptions
- Ownership information
- Legal descriptions
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


class MaricopaCountyAssessor(CountyAssessorBase):
    """
    Maricopa County, Arizona Assessor scraper.

    Uses the Maricopa County Assessor's public portal.
    """

    COUNTY_NAME = "Maricopa County"
    STATE = "AZ"
    FIPS_CODE = "04013"
    BASE_URL = "https://mcassessor.maricopa.gov/"
    SYSTEM_NAME = "Maricopa County Assessor Portal"

    # APN format: XXX-XX-XXX or XXX-XX-XXXX
    PARCEL_ID_FORMAT = "XXX-XX-XXX or XXX-XX-XXXX"
    PARCEL_ID_PATTERN = r"^\d{3}-\d{2}-\d{3,4}[A-Z]?$"

    # API endpoints
    API_BASE = "https://mcassessor.maricopa.gov/api/"
    PARCEL_SEARCH = "https://mcassessor.maricopa.gov/parcel/"

    # Cities in Maricopa County
    CITIES = [
        "Phoenix",
        "Mesa",
        "Chandler",
        "Scottsdale",
        "Gilbert",
        "Glendale",
        "Tempe",
        "Peoria",
        "Surprise",
        "Avondale",
        "Goodyear",
        "Buckeye",
        "Casa Grande",
        "San Tan Valley",
        "Fountain Hills",
        "Paradise Valley",
        "Cave Creek",
        "Carefree",
        "Queen Creek",
        "El Mirage",
        "Litchfield Park",
        "Tolleson",
        "Wickenburg",
        "Youngtown",
        "Guadalupe",
        "Apache Junction",
    ]

    # Property use codes
    USE_CODES = {
        "100": "Single Family Residence",
        "110": "Manufactured Home",
        "120": "Townhouse/Rowhouse",
        "130": "Condominium",
        "140": "Patio Home",
        "200": "Multi-Family (2-4 units)",
        "210": "Apartments (5+ units)",
        "300": "Vacant Residential",
        "310": "Vacant Commercial",
        "400": "Commercial Retail",
        "410": "Commercial Office",
        "420": "Commercial Industrial",
        "500": "Agricultural",
        "510": "Ranch/Farm",
        "600": "Government",
        "610": "Schools",
        "620": "Religious",
    }

    def _format_apn(self, apn: str) -> str:
        """Format an APN with dashes if not already formatted."""
        # Remove existing dashes and spaces
        clean = apn.replace("-", "").replace(" ", "").strip().upper()

        # Handle suffix letter
        suffix = ""
        if clean and clean[-1].isalpha():
            suffix = clean[-1]
            clean = clean[:-1]

        if len(clean) == 8:
            return f"{clean[:3]}-{clean[3:5]}-{clean[5:8]}{suffix}"
        elif len(clean) == 9:
            return f"{clean[:3]}-{clean[3:5]}-{clean[5:9]}{suffix}"
        return apn

    def _validate_apn(self, apn: str) -> bool:
        """Validate a Maricopa County APN format."""
        formatted = self._format_apn(apn)
        return bool(re.match(self.PARCEL_ID_PATTERN, formatted))

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

        params = {
            "address": street_address,
            "limit": min(max_results, 100),
        }

        if city:
            params["city"] = city
        if zip_code:
            params["zip"] = zip_code

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Maricopa County address search failed: {e}")
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
            logger.warning(f"Invalid Maricopa County APN format: {parcel_id}")
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
            logger.error(f"Maricopa County owner search failed: {e}")
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

    async def search_by_subdivision(
        self, subdivision_name: str, max_results: int = 100
    ) -> AssessorSearchResult:
        """Search for properties by subdivision name."""
        import time

        start_time = time.time()

        search_url = f"{self.API_BASE}parcel/search"

        params = {
            "subdivision": subdivision_name,
            "limit": min(max_results, 100),
        }

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Maricopa County subdivision search failed: {e}")
            return AssessorSearchResult(
                properties=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=AssessorSearchCriteria(),
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
            search_criteria=AssessorSearchCriteria(),
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
            logger.error(f"Maricopa County property detail failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_property_detail(json_response, formatted_apn)

    def _parse_search_result(
        self, item: Dict[str, Any]
    ) -> Optional[PropertyAssessment]:
        """Parse a search result item."""
        apn = item.get("apn", item.get("parcelNumber", ""))
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
            property_type=self._parse_property_type(
                item.get("useCode", item.get("propertyType", ""))
            ),
            assessed_value=self._parse_decimal(
                str(item.get("fullCashValue", item.get("assessedValue", "")))
            ),
            market_value=self._parse_decimal(
                str(item.get("marketValue", item.get("limitedValue", "")))
            ),
            current_owner=(
                OwnershipRecord(
                    owner_name=item.get("ownerName", item.get("owner", "")),
                )
                if item.get("ownerName") or item.get("owner")
                else None
            ),
            source_url=f"{self.PARCEL_SEARCH}{formatted_apn.replace('-', '')}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_property_detail(
        self, data: Dict[str, Any], apn: str
    ) -> PropertyAssessment:
        """Parse detailed property data."""
        # Parse characteristics
        chars = data.get("improvements", data.get("characteristics", {}))
        if isinstance(chars, list) and chars:
            chars = chars[0]  # Take first improvement record

        land_data = data.get("land", {})

        characteristics = PropertyCharacteristics(
            year_built=self._parse_int(
                str(chars.get("yearBuilt", chars.get("effectiveYear", "")))
            ),
            building_sqft=self._parse_int(
                str(chars.get("totalSqft", chars.get("buildingArea", "")))
            ),
            living_sqft=self._parse_int(
                str(chars.get("livingSqft", chars.get("livingArea", "")))
            ),
            bedrooms=self._parse_int(str(chars.get("bedrooms", ""))),
            bathrooms=self._parse_float(
                str(chars.get("bathrooms", chars.get("totalBaths", "")))
            ),
            full_baths=self._parse_int(str(chars.get("fullBaths", ""))),
            half_baths=self._parse_int(
                str(chars.get("halfBaths", chars.get("threeQuarterBaths", "")))
            ),
            stories=self._parse_float(
                str(chars.get("stories", chars.get("numberOfStories", "")))
            ),
            garage_type=chars.get("garageType", chars.get("parkingType")),
            garage_spaces=self._parse_int(
                str(chars.get("garageSpaces", chars.get("parkingSpaces", "")))
            ),
            lot_sqft=self._parse_int(
                str(land_data.get("sqft", land_data.get("landArea", "")))
            ),
            lot_acres=self._parse_float(str(land_data.get("acres", ""))),
            construction_type=chars.get("constructionType", chars.get("construction")),
            exterior_wall=chars.get("exteriorWall", chars.get("exterior")),
            roof_type=chars.get("roofType", chars.get("roof")),
            foundation_type=chars.get("foundationType", chars.get("foundation")),
            central_air=chars.get("cooling") == "Central"
            or "AIR" in str(chars.get("cooling", "")).upper(),
            heating_type=chars.get("heating", chars.get("heatingType")),
            pool=chars.get("pool", False)
            or "POOL" in str(chars.get("amenities", "")).upper(),
            fireplace_count=self._parse_int(str(chars.get("fireplaces", ""))),
            raw_characteristics=chars,
        )

        # Parse value history - Arizona uses Full Cash Value (FCV) and Limited Property Value (LPV)
        assessment_history = []
        for assessment in data.get("valueHistory", data.get("valuations", [])):
            tax_assessment = TaxAssessment(
                tax_year=assessment.get("taxYear", assessment.get("year", 0)),
                assessed_value_land=self._parse_decimal(
                    str(assessment.get("landValue", assessment.get("landFCV", "")))
                ),
                assessed_value_improvements=self._parse_decimal(
                    str(
                        assessment.get(
                            "improvementValue", assessment.get("improvementFCV", "")
                        )
                    )
                ),
                assessed_value_total=self._parse_decimal(
                    str(assessment.get("fullCashValue", assessment.get("totalFCV", "")))
                ),
                market_value_total=self._parse_decimal(
                    str(assessment.get("limitedValue", assessment.get("LPV", "")))
                ),
            )
            assessment_history.append(tax_assessment)

        # Parse sales history
        sales_history = []
        for sale in data.get("salesHistory", data.get("transfers", [])):
            sale_record = SaleRecord(
                sale_date=self._parse_date(
                    sale.get("saleDate", sale.get("recordingDate", ""))
                )
                or date.today(),
                sale_price=self._parse_decimal(
                    str(sale.get("salePrice", sale.get("consideration", "")))
                )
                or Decimal(0),
                buyer_name=sale.get("grantee", sale.get("buyer")),
                seller_name=sale.get("grantor", sale.get("seller")),
                document_number=sale.get("documentNumber", sale.get("docketPage")),
                document_type=sale.get("deedType", sale.get("documentType")),
                qualified_sale=sale.get("qualified", sale.get("isQualified")),
            )
            sales_history.append(sale_record)

        # Parse ownership
        owner_data = data.get("owner", data.get("ownership", {}))
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

        # Parse exemptions - Arizona has different exemption types
        exemptions = []
        exemption_data = data.get("exemptions", [])
        if isinstance(exemption_data, str):
            exemption_data = [{"type": exemption_data}]

        for exemption in exemption_data:
            exemption_type = str(
                exemption.get("type", exemption.get("code", ""))
            ).upper()
            if "HOMEOWNER" in exemption_type or "WIDOW" in exemption_type:
                exemptions.append(ExemptionType.HOMESTEAD)
            elif "SENIOR" in exemption_type or "65" in exemption_type:
                exemptions.append(ExemptionType.SENIOR_CITIZEN)
            elif "VETERAN" in exemption_type or "DISABLED VET" in exemption_type:
                exemptions.append(ExemptionType.VETERAN)
            elif "DISABLED" in exemption_type:
                exemptions.append(ExemptionType.DISABILITY)
            elif "NONPROFIT" in exemption_type or "501" in exemption_type:
                exemptions.append(ExemptionType.CHARITABLE)
            elif "CHURCH" in exemption_type or "RELIGIOUS" in exemption_type:
                exemptions.append(ExemptionType.RELIGIOUS)
            elif "GOVERNMENT" in exemption_type:
                exemptions.append(ExemptionType.GOVERNMENT)

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
            legal_description=data.get("legalDescription", data.get("legal")),
            subdivision=data.get("subdivision", data.get("subdivisionName")),
            property_type=self._parse_property_type(
                data.get("useCode", data.get("propertyType", ""))
            ),
            property_class=self._parse_property_class(data.get("useCode", "")),
            property_use=data.get(
                "useDescription", self.USE_CODES.get(data.get("useCode", ""))
            ),
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
            neighborhood=data.get("neighborhood", data.get("area")),
            source_url=f"{self.PARCEL_SEARCH}{apn_clean}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

    def _parse_property_type(self, use_code: str) -> Optional[PropertyType]:
        """Parse Maricopa County use codes to PropertyType."""
        if not use_code:
            return None

        code = (
            str(use_code).strip()[:3]
            if len(str(use_code)) >= 3
            else str(use_code).strip()
        )

        code_mapping = {
            "100": PropertyType.SINGLE_FAMILY,
            "110": PropertyType.MOBILE_HOME,
            "120": PropertyType.TOWNHOUSE,
            "130": PropertyType.CONDOMINIUM,
            "140": PropertyType.SINGLE_FAMILY,  # Patio home
            "200": PropertyType.MULTI_FAMILY,
            "210": PropertyType.MULTI_FAMILY,
            "300": PropertyType.VACANT_LAND,
            "310": PropertyType.VACANT_LAND,
            "400": PropertyType.COMMERCIAL,
            "410": PropertyType.COMMERCIAL,
            "420": PropertyType.INDUSTRIAL,
            "500": PropertyType.AGRICULTURAL,
            "510": PropertyType.AGRICULTURAL,
            "600": PropertyType.EXEMPT,
            "610": PropertyType.EXEMPT,
            "620": PropertyType.EXEMPT,
        }

        return code_mapping.get(code)

    def _parse_property_class(self, use_code: str) -> Optional[PropertyClass]:
        """Parse Maricopa County use codes to PropertyClass."""
        if not use_code:
            return None

        code = str(use_code).strip()[:1]

        class_mapping = {
            "1": PropertyClass.RESIDENTIAL,
            "2": PropertyClass.RESIDENTIAL,
            "3": PropertyClass.VACANT,
            "4": PropertyClass.COMMERCIAL,
            "5": PropertyClass.AGRICULTURAL,
            "6": PropertyClass.EXEMPT,
        }

        return class_mapping.get(code)


# Convenience functions


def search_maricopa_county_address(address: str, **kwargs) -> AssessorSearchResult:
    """Search Maricopa County properties by address."""
    assessor = MaricopaCountyAssessor()

    async def _search():
        async with assessor:
            return await assessor.search_by_address(address, **kwargs)

    return asyncio.run(_search())


def search_maricopa_county_owner(owner_name: str, **kwargs) -> AssessorSearchResult:
    """Search Maricopa County properties by owner name."""
    assessor = MaricopaCountyAssessor()

    async def _search():
        async with assessor:
            return await assessor.search_by_owner(owner_name, **kwargs)

    return asyncio.run(_search())


def get_maricopa_county_property(apn: str) -> Optional[PropertyAssessment]:
    """Get Maricopa County property details by APN."""
    assessor = MaricopaCountyAssessor()

    async def _get():
        async with assessor:
            return await assessor.get_property_detail(apn)

    return asyncio.run(_get())
