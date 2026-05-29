"""
Orange County, California Assessor Scraper

Orange County is the sixth most populous county in the US with approximately
3.2 million residents. The Orange County Assessor's Office maintains records
for approximately 650,000 parcels.

Website: https://www.ocgov.com/assessor
APN Format: XXX-XXX-XX (Book-Page-Parcel)
           8 digits, also seen as XXX-XXX-XXX (9 digits)

The Orange County Assessor provides:
- Property characteristics
- Assessed values (Proposition 13 base year system)
- Sales history
- Tax exemptions
- Business property assessments
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


class OrangeCountyAssessor(CountyAssessorBase):
    """
    Orange County, California Assessor scraper.

    Uses the Orange County Assessor public data portal.
    """

    COUNTY_NAME = "Orange County"
    STATE = "CA"
    FIPS_CODE = "06059"
    BASE_URL = "https://www.ocgov.com/assessor/"
    SYSTEM_NAME = "Orange County Assessor"

    # APN format: XXX-XXX-XX or XXX-XXX-XXX
    PARCEL_ID_FORMAT = "XXX-XXX-XX (8 digits)"
    PARCEL_ID_PATTERN = r"^\d{3}-\d{3}-\d{2,3}$"

    # API endpoints
    SEARCH_URL = "https://ocgov.com/assessor/api/property"
    DETAIL_URL = "https://ocgov.com/assessor/api/property/detail"

    # Orange County city codes
    CITIES = {
        "01": "Aliso Viejo",
        "02": "Anaheim",
        "03": "Brea",
        "04": "Buena Park",
        "05": "Costa Mesa",
        "06": "Cypress",
        "07": "Dana Point",
        "08": "Fountain Valley",
        "09": "Fullerton",
        "10": "Garden Grove",
        "11": "Huntington Beach",
        "12": "Irvine",
        "13": "La Habra",
        "14": "La Palma",
        "15": "Laguna Beach",
        "16": "Laguna Hills",
        "17": "Laguna Niguel",
        "18": "Laguna Woods",
        "19": "Lake Forest",
        "20": "Los Alamitos",
        "21": "Mission Viejo",
        "22": "Newport Beach",
        "23": "Orange",
        "24": "Placentia",
        "25": "Rancho Santa Margarita",
        "26": "San Clemente",
        "27": "San Juan Capistrano",
        "28": "Santa Ana",
        "29": "Seal Beach",
        "30": "Stanton",
        "31": "Tustin",
        "32": "Villa Park",
        "33": "Westminster",
        "34": "Yorba Linda",
        "99": "Unincorporated",
    }

    # Use code mappings (California standardized)
    USE_CODES = {
        "00": "Vacant Residential",
        "01": "Single Family Residence",
        "02": "Two Units",
        "03": "Three Units",
        "04": "Four Units",
        "05": "Five or More Units",
        "06": "Mobile Home Park",
        "07": "Condominium",
        "08": "Stock Cooperative",
        "10": "Vacant Commercial",
        "11": "Commercial Store/Building",
        "12": "Shopping Center",
        "13": "Office Building",
        "14": "Hotel/Motel",
        "15": "Mixed Use",
        "20": "Vacant Industrial",
        "21": "Light Manufacturing",
        "22": "Heavy Manufacturing",
        "23": "Warehouse/Distribution",
        "30": "Vacant Agricultural",
        "31": "Agricultural Production",
        "50": "Exempt - Government",
        "51": "Exempt - Religious",
        "52": "Exempt - Educational",
        "53": "Exempt - Charitable",
    }

    def _format_apn(self, apn: str) -> str:
        """Format an APN with dashes if not already formatted."""
        # Remove existing dashes, spaces, and dots
        clean = apn.replace("-", "").replace(" ", "").replace(".", "").strip()

        if len(clean) == 8:
            return f"{clean[:3]}-{clean[3:6]}-{clean[6:8]}"
        elif len(clean) == 9:
            return f"{clean[:3]}-{clean[3:6]}-{clean[6:9]}"
        return apn

    def _validate_apn(self, apn: str) -> bool:
        """Validate an Orange County APN format."""
        formatted = self._format_apn(apn)
        return bool(re.match(self.PARCEL_ID_PATTERN, formatted))

    def _parse_use_code(self, code: str) -> PropertyType:
        """Parse use code to property type."""
        if not code:
            return PropertyType.UNKNOWN

        code = str(code).zfill(2)[:2]

        if code == "01":
            return PropertyType.SINGLE_FAMILY
        elif code in ("02", "03", "04", "05"):
            return PropertyType.MULTI_FAMILY
        elif code == "00":
            return PropertyType.VACANT_LAND
        elif code == "06":
            return PropertyType.MOBILE_HOME
        elif code == "07":
            return PropertyType.CONDO
        elif code == "08":
            return PropertyType.COOPERATIVE
        elif code in ("10", "11", "12"):
            return PropertyType.RETAIL
        elif code == "13":
            return PropertyType.OFFICE
        elif code == "14":
            return PropertyType.HOTEL_MOTEL
        elif code == "15":
            return PropertyType.MIXED_USE
        elif code in ("20", "21", "22", "23"):
            return PropertyType.INDUSTRIAL
        elif code in ("30", "31"):
            return PropertyType.AGRICULTURAL
        elif code.startswith("5"):
            return PropertyType.EXEMPT

        return PropertyType.UNKNOWN

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

        params = {
            "address": street_address,
            "limit": min(max_results, 100),
        }

        if city:
            params["city"] = city
        if zip_code:
            params["zip"] = zip_code

        try:
            json_response = await self._fetch_json(self.SEARCH_URL, params=params)
        except Exception as e:
            logger.error(f"Orange County address search failed: {e}")
            return AssessorSearchResult(
                properties=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=AssessorSearchCriteria(street_address=street_address),
                warnings=[str(e)],
            )

        properties = []
        results = json_response.get("results", json_response.get("properties", []))

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
                street_address=street_address, city=city, zip_code=zip_code
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def search_by_parcel_id(self, parcel_id: str) -> Optional[PropertyAssessment]:
        """Search for a property by APN."""
        formatted_apn = self._format_apn(parcel_id)

        if not self._validate_apn(formatted_apn):
            logger.warning(f"Invalid Orange County APN format: {parcel_id}")
            return None

        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL, params={"apn": formatted_apn}
            )

            if json_response.get("property"):
                return self._parse_property_detail(json_response["property"])

        except Exception as e:
            logger.error(f"Orange County parcel search failed: {e}")

        return None

    async def search_by_owner(
        self, owner_name: str, max_results: int = 100
    ) -> AssessorSearchResult:
        """Search for properties by owner name."""
        import time

        start_time = time.time()

        params = {
            "owner": owner_name,
            "limit": min(max_results, 100),
        }

        try:
            json_response = await self._fetch_json(self.SEARCH_URL, params=params)
        except Exception as e:
            logger.error(f"Orange County owner search failed: {e}")
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
        results = json_response.get("results", json_response.get("properties", []))

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

    async def get_property_detail(self, parcel_id: str) -> Optional[PropertyAssessment]:
        """Get detailed property information."""
        formatted_apn = self._format_apn(parcel_id)

        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL, params={"apn": formatted_apn, "include": "all"}
            )

            if json_response.get("property"):
                return self._parse_property_detail(
                    json_response["property"], include_history=True
                )

        except Exception as e:
            logger.error(f"Orange County property detail failed: {e}")

        return None

    def _parse_search_result(
        self, data: Dict[str, Any]
    ) -> Optional[PropertyAssessment]:
        """Parse a search result into PropertyAssessment."""
        apn = data.get("apn", data.get("parcelNumber", ""))
        if not apn:
            return None

        formatted_apn = self._format_apn(apn)

        owner_info = None
        if data.get("owner") or data.get("ownerName"):
            owner_info = OwnershipRecord(
                owner_name=data.get("owner", data.get("ownerName", "Unknown")),
                mailing_address=data.get("mailingAddress"),
                mailing_city=data.get("mailingCity"),
                mailing_state=data.get("mailingState"),
                mailing_zip=data.get("mailingZip"),
            )

        return PropertyAssessment(
            parcel_id=formatted_apn,
            property_address=data.get("siteAddress", data.get("address", "")),
            city=data.get("city", data.get("siteCity", "")),
            state="CA",
            zip_code=data.get("zip", data.get("siteZip")),
            county=self.COUNTY_NAME,
            property_type=self._parse_use_code(
                data.get("useCode", data.get("propertyUseCode", ""))
            ),
            assessed_value=self._parse_decimal(data.get("assessedValue")),
            market_value=self._parse_decimal(data.get("marketValue")),
            land_value=self._parse_decimal(data.get("landValue")),
            improvement_value=self._parse_decimal(data.get("improvementValue")),
            current_owner=owner_info,
            source_url=f"{self.BASE_URL}property/{formatted_apn}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

    def _parse_property_detail(
        self, data: Dict[str, Any], include_history: bool = False
    ) -> PropertyAssessment:
        """Parse detailed property data."""
        apn = data.get("apn", data.get("parcelNumber", ""))
        formatted_apn = self._format_apn(apn)

        # Parse characteristics
        chars_data = data.get("characteristics", data.get("building", {}))
        characteristics = PropertyCharacteristics(
            year_built=self._parse_int(chars_data.get("yearBuilt")),
            effective_year=self._parse_int(chars_data.get("effectiveYear")),
            building_sqft=self._parse_int(chars_data.get("buildingSqft")),
            living_sqft=self._parse_int(chars_data.get("livingSqft")),
            bedrooms=self._parse_int(chars_data.get("bedrooms")),
            bathrooms=self._parse_float(chars_data.get("bathrooms")),
            full_baths=self._parse_int(chars_data.get("fullBaths")),
            half_baths=self._parse_int(chars_data.get("halfBaths")),
            stories=self._parse_float(chars_data.get("stories")),
            lot_sqft=self._parse_int(chars_data.get("lotSqft")),
            lot_acres=self._parse_float(chars_data.get("lotAcres")),
            garage_spaces=self._parse_int(chars_data.get("garageSpaces")),
            pool=chars_data.get("pool", False),
            construction_type=chars_data.get("constructionType"),
            roof_type=chars_data.get("roofType"),
            exterior_wall=chars_data.get("exteriorWall"),
            central_air=chars_data.get("centralAir", False),
            zoning=data.get("zoning"),
            raw_characteristics=chars_data,
        )

        # Parse owner
        owner_data = data.get("owner", {})
        current_owner = OwnershipRecord(
            owner_name=owner_data.get("name", data.get("ownerName", "Unknown")),
            mailing_address=owner_data.get("mailingAddress"),
            mailing_city=owner_data.get("mailingCity"),
            mailing_state=owner_data.get("mailingState"),
            mailing_zip=owner_data.get("mailingZip"),
        )

        # Parse assessment history
        assessment_history = []
        if include_history:
            for assessment in data.get("assessmentHistory", []):
                assessment_history.append(
                    TaxAssessment(
                        tax_year=self._parse_int(assessment.get("year")) or 0,
                        assessed_value_land=self._parse_decimal(
                            assessment.get("landValue")
                        ),
                        assessed_value_improvements=self._parse_decimal(
                            assessment.get("improvementValue")
                        ),
                        assessed_value_total=self._parse_decimal(
                            assessment.get("totalValue")
                        ),
                        exemption_amount=self._parse_decimal(
                            assessment.get("exemptionAmount")
                        ),
                        taxable_value=self._parse_decimal(
                            assessment.get("taxableValue")
                        ),
                    )
                )

        # Parse sales history
        sales_history = []
        if include_history:
            for sale in data.get("salesHistory", []):
                sale_date = self._parse_date(sale.get("saleDate"))
                if sale_date:
                    sales_history.append(
                        SaleRecord(
                            sale_date=sale_date,
                            sale_price=self._parse_decimal(sale.get("salePrice"))
                            or Decimal(0),
                            buyer_name=sale.get("grantee"),
                            seller_name=sale.get("grantor"),
                            document_number=sale.get("documentNumber"),
                            document_type=sale.get("documentType"),
                        )
                    )

        return PropertyAssessment(
            parcel_id=formatted_apn,
            property_address=data.get("siteAddress", data.get("address", "")),
            city=data.get("city", data.get("siteCity", "")),
            state="CA",
            zip_code=data.get("zip", data.get("siteZip")),
            county=self.COUNTY_NAME,
            legal_description=data.get("legalDescription"),
            property_type=self._parse_use_code(
                data.get("useCode", data.get("propertyUseCode", ""))
            ),
            assessed_value=self._parse_decimal(data.get("assessedValue")),
            market_value=self._parse_decimal(data.get("marketValue")),
            land_value=self._parse_decimal(data.get("landValue")),
            improvement_value=self._parse_decimal(data.get("improvementValue")),
            tax_year=self._parse_int(data.get("taxYear")),
            characteristics=characteristics,
            current_owner=current_owner,
            assessment_history=assessment_history,
            sales_history=sales_history,
            last_sale_date=sales_history[0].sale_date if sales_history else None,
            last_sale_price=sales_history[0].sale_price if sales_history else None,
            latitude=self._parse_float(data.get("latitude")),
            longitude=self._parse_float(data.get("longitude")),
            source_url=f"{self.BASE_URL}property/{formatted_apn}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )


# Synchronous convenience functions


def get_orange_county_property(apn: str) -> Optional[PropertyAssessment]:
    """Get Orange County property by APN."""

    async def _get():
        async with OrangeCountyAssessor() as assessor:
            return await assessor.get_property_detail(apn)

    return asyncio.run(_get())


def search_orange_county_by_address(
    address: str,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    max_results: int = 100,
) -> AssessorSearchResult:
    """Search Orange County properties by address."""

    async def _search():
        async with OrangeCountyAssessor() as assessor:
            return await assessor.search_by_address(
                address, city=city, zip_code=zip_code, max_results=max_results
            )

    return asyncio.run(_search())


def search_orange_county_by_owner(
    owner_name: str, max_results: int = 100
) -> AssessorSearchResult:
    """Search Orange County properties by owner name."""

    async def _search():
        async with OrangeCountyAssessor() as assessor:
            return await assessor.search_by_owner(owner_name, max_results=max_results)

    return asyncio.run(_search())
