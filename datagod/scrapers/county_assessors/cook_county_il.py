"""
Cook County, Illinois Assessor Scraper

Cook County (Chicago) is the second most populous county in the US.
The Cook County Assessor's Office maintains property records for
approximately 1.8 million parcels.

Website: https://www.cookcountyassessor.com/
PIN Format: XX-XX-XXX-XXX-XXXX (14 digits with dashes)
           Township-Section-Block-Lot-Unit

The Cook County Assessor provides:
- Property characteristics
- Assessment values (triennial reassessment cycle)
- Sales history
- Tax exemptions
- Appeals information
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
    CountyAssessorBase,
    PropertyType,
    PropertyClass,
    ExemptionType,
    PropertyAssessment,
    PropertyCharacteristics,
    TaxAssessment,
    OwnershipRecord,
    SaleRecord,
    AssessorSearchCriteria,
    AssessorSearchResult,
)

logger = logging.getLogger(__name__)


class CookCountyAssessor(CountyAssessorBase):
    """
    Cook County, Illinois Assessor scraper.

    Uses the Cook County Assessor's public data portal.
    """

    COUNTY_NAME = "Cook County"
    STATE = "IL"
    FIPS_CODE = "17031"
    BASE_URL = "https://www.cookcountyassessor.com/"
    SYSTEM_NAME = "Cook County Assessor Portal"

    # PIN format: XX-XX-XXX-XXX-XXXX
    PARCEL_ID_FORMAT = "XX-XX-XXX-XXX-XXXX (14 digits)"
    PARCEL_ID_PATTERN = r"^\d{2}-\d{2}-\d{3}-\d{3}-\d{4}$"

    # API endpoints
    API_BASE = "https://www.cookcountyassessor.com/api/"

    # Township codes
    TOWNSHIPS = {
        "10": "Barrington",
        "11": "Berwyn",
        "12": "Bloom",
        "13": "Bremen",
        "14": "Calumet",
        "15": "Cicero",
        "16": "Elk Grove",
        "17": "Evanston",
        "18": "Hanover",
        "19": "Hyde Park",
        "20": "Jefferson",
        "21": "Lake",
        "22": "Lake View",
        "23": "Lemont",
        "24": "Leyden",
        "25": "Lyons",
        "26": "Maine",
        "27": "New Trier",
        "28": "Niles",
        "29": "Northfield",
        "30": "Norwood Park",
        "31": "Oak Park",
        "32": "Orland",
        "33": "Palatine",
        "34": "Palos",
        "35": "Proviso",
        "36": "Rich",
        "37": "River Forest",
        "38": "Riverside",
        "39": "Rogers Park",
        "40": "Schaumburg",
        "41": "South Chicago",
        "42": "Stickney",
        "43": "Thornton",
        "44": "Wheeling",
        "45": "Worth",
    }

    def _format_pin(self, pin: str) -> str:
        """Format a PIN with dashes if not already formatted."""
        # Remove existing dashes and spaces
        clean = pin.replace("-", "").replace(" ", "").strip()

        if len(clean) == 14:
            return f"{clean[:2]}-{clean[2:4]}-{clean[4:7]}-{clean[7:10]}-{clean[10:14]}"
        return pin

    def _validate_pin(self, pin: str) -> bool:
        """Validate a Cook County PIN format."""
        formatted = self._format_pin(pin)
        return bool(re.match(self.PARCEL_ID_PATTERN, formatted))

    def _get_township_name(self, pin: str) -> str:
        """Get township name from PIN."""
        formatted = self._format_pin(pin)
        township_code = formatted[:2]
        return self.TOWNSHIPS.get(township_code, "Unknown")

    async def search_by_address(
        self,
        street_address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        max_results: int = 100
    ) -> AssessorSearchResult:
        """Search for properties by address."""
        import time
        start_time = time.time()

        # Cook County uses a search API
        search_url = f"{self.API_BASE}property-search"

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
            logger.error(f"Cook County address search failed: {e}")
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
        results = json_response.get("results", [])

        for item in results[:max_results]:
            prop = self._parse_search_result(item)
            if prop:
                properties.append(prop)

        search_time = int((time.time() - start_time) * 1000)

        return AssessorSearchResult(
            properties=properties,
            total_count=json_response.get("total", len(properties)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=AssessorSearchCriteria(
                street_address=street_address,
                city=city,
                zip_code=zip_code
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def search_by_parcel_id(
        self,
        parcel_id: str
    ) -> Optional[PropertyAssessment]:
        """Search for a property by PIN."""
        formatted_pin = self._format_pin(parcel_id)

        if not self._validate_pin(formatted_pin):
            logger.warning(f"Invalid Cook County PIN format: {parcel_id}")
            return None

        return await self.get_property_detail(formatted_pin)

    async def search_by_owner(
        self,
        owner_name: str,
        max_results: int = 100
    ) -> AssessorSearchResult:
        """Search for properties by owner name."""
        import time
        start_time = time.time()

        search_url = f"{self.API_BASE}property-search"

        params = {
            "owner": owner_name,
            "limit": min(max_results, 100),
        }

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Cook County owner search failed: {e}")
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
        results = json_response.get("results", [])

        for item in results[:max_results]:
            prop = self._parse_search_result(item)
            if prop:
                properties.append(prop)

        search_time = int((time.time() - start_time) * 1000)

        return AssessorSearchResult(
            properties=properties,
            total_count=json_response.get("total", len(properties)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=AssessorSearchCriteria(owner_name=owner_name),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_property_detail(
        self,
        parcel_id: str
    ) -> Optional[PropertyAssessment]:
        """Get detailed property information."""
        formatted_pin = self._format_pin(parcel_id)

        detail_url = f"{self.API_BASE}property/{formatted_pin}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"Cook County property detail failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_property_detail(json_response, formatted_pin)

    def _parse_search_result(self, item: Dict[str, Any]) -> Optional[PropertyAssessment]:
        """Parse a search result item."""
        pin = item.get("pin", "")
        if not pin:
            return None

        return PropertyAssessment(
            parcel_id=self._format_pin(pin),
            property_address=item.get("address", ""),
            city=item.get("city", ""),
            state=self.STATE,
            zip_code=item.get("zip", ""),
            county=self.COUNTY_NAME,
            property_type=self._parse_property_type(item.get("propertyType", "")),
            assessed_value=self._parse_decimal(str(item.get("assessedValue", ""))),
            market_value=self._parse_decimal(str(item.get("marketValue", ""))),
            current_owner=OwnershipRecord(
                owner_name=item.get("owner", ""),
            ) if item.get("owner") else None,
            source_url=f"{self.BASE_URL}pin/{self._format_pin(pin)}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_property_detail(
        self,
        data: Dict[str, Any],
        pin: str
    ) -> PropertyAssessment:
        """Parse detailed property data."""
        # Parse characteristics
        chars = data.get("characteristics", {})
        characteristics = PropertyCharacteristics(
            year_built=self._parse_int(str(chars.get("yearBuilt", ""))),
            building_sqft=self._parse_int(str(chars.get("buildingSqft", ""))),
            living_sqft=self._parse_int(str(chars.get("livingSqft", ""))),
            bedrooms=self._parse_int(str(chars.get("bedrooms", ""))),
            bathrooms=self._parse_float(str(chars.get("bathrooms", ""))),
            full_baths=self._parse_int(str(chars.get("fullBaths", ""))),
            half_baths=self._parse_int(str(chars.get("halfBaths", ""))),
            stories=self._parse_float(str(chars.get("stories", ""))),
            basement=chars.get("basement"),
            garage_type=chars.get("garageType"),
            garage_spaces=self._parse_int(str(chars.get("garageSpaces", ""))),
            lot_sqft=self._parse_int(str(chars.get("lotSqft", ""))),
            construction_type=chars.get("constructionType"),
            exterior_wall=chars.get("exteriorWall"),
            roof_type=chars.get("roofType"),
            central_air=chars.get("centralAir", False),
            fireplace_count=self._parse_int(str(chars.get("fireplaces", ""))),
            raw_characteristics=chars,
        )

        # Parse assessment history
        assessment_history = []
        for assessment in data.get("assessmentHistory", []):
            tax_assessment = TaxAssessment(
                tax_year=assessment.get("year", 0),
                assessed_value_land=self._parse_decimal(str(assessment.get("landValue", ""))),
                assessed_value_improvements=self._parse_decimal(str(assessment.get("improvementValue", ""))),
                assessed_value_total=self._parse_decimal(str(assessment.get("totalValue", ""))),
                market_value_total=self._parse_decimal(str(assessment.get("marketValue", ""))),
            )
            assessment_history.append(tax_assessment)

        # Parse sales history
        sales_history = []
        for sale in data.get("salesHistory", []):
            sale_record = SaleRecord(
                sale_date=self._parse_date(sale.get("date", "")) or date.today(),
                sale_price=self._parse_decimal(str(sale.get("price", ""))) or Decimal(0),
                buyer_name=sale.get("buyer"),
                seller_name=sale.get("seller"),
                document_number=sale.get("docNumber"),
                document_type=sale.get("deedType"),
            )
            sales_history.append(sale_record)

        # Parse ownership
        owner_data = data.get("owner", {})
        current_owner = OwnershipRecord(
            owner_name=owner_data.get("name", ""),
            mailing_address=owner_data.get("mailingAddress"),
            mailing_city=owner_data.get("mailingCity"),
            mailing_state=owner_data.get("mailingState"),
            mailing_zip=owner_data.get("mailingZip"),
        ) if owner_data.get("name") else None

        # Parse exemptions
        exemptions = []
        for exemption in data.get("exemptions", []):
            exemption_type = exemption.get("type", "").upper()
            if "HOMEOWNER" in exemption_type or "HOMESTEAD" in exemption_type:
                exemptions.append(ExemptionType.HOMESTEAD)
            elif "SENIOR" in exemption_type:
                exemptions.append(ExemptionType.SENIOR_CITIZEN)
            elif "VETERAN" in exemption_type:
                exemptions.append(ExemptionType.VETERAN)
            elif "DISABLED" in exemption_type:
                exemptions.append(ExemptionType.DISABILITY)

        # Get current assessment
        current_assessment = assessment_history[0] if assessment_history else None

        return PropertyAssessment(
            parcel_id=pin,
            property_address=data.get("address", ""),
            city=data.get("city", ""),
            state=self.STATE,
            zip_code=data.get("zip", ""),
            county=self.COUNTY_NAME,
            legal_description=data.get("legalDescription"),
            subdivision=data.get("subdivision"),
            property_type=self._parse_property_type(data.get("propertyType", "")),
            property_use=data.get("propertyUse"),
            assessed_value=current_assessment.assessed_value_total if current_assessment else None,
            market_value=current_assessment.market_value_total if current_assessment else None,
            land_value=current_assessment.assessed_value_land if current_assessment else None,
            improvement_value=current_assessment.assessed_value_improvements if current_assessment else None,
            tax_year=current_assessment.tax_year if current_assessment else None,
            characteristics=characteristics,
            assessment_history=assessment_history,
            current_owner=current_owner,
            sales_history=sales_history,
            last_sale_date=sales_history[0].sale_date if sales_history else None,
            last_sale_price=sales_history[0].sale_price if sales_history else None,
            latitude=self._parse_float(str(data.get("latitude", ""))),
            longitude=self._parse_float(str(data.get("longitude", ""))),
            neighborhood=self._get_township_name(pin),
            source_url=f"{self.BASE_URL}pin/{pin}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )


# Convenience functions

def search_cook_county_address(address: str, **kwargs) -> AssessorSearchResult:
    """Search Cook County properties by address."""
    assessor = CookCountyAssessor()

    async def _search():
        async with assessor:
            return await assessor.search_by_address(address, **kwargs)
    return asyncio.run(_search())


def search_cook_county_owner(owner_name: str, **kwargs) -> AssessorSearchResult:
    """Search Cook County properties by owner name."""
    assessor = CookCountyAssessor()

    async def _search():
        async with assessor:
            return await assessor.search_by_owner(owner_name, **kwargs)
    return asyncio.run(_search())


def get_cook_county_property(pin: str) -> Optional[PropertyAssessment]:
    """Get Cook County property details by PIN."""
    assessor = CookCountyAssessor()

    async def _get():
        async with assessor:
            return await assessor.get_property_detail(pin)
    return asyncio.run(_get())
