"""
Clark County, Nevada Assessor Scraper

Clark County (Las Vegas) is the eleventh most populous county in the US with
approximately 2.3 million residents. The Clark County Assessor's Office
maintains property records for approximately 800,000 parcels.

Website: https://www.clarkcountynv.gov/assessor/
APN Format: XXX-XX-XXX-XXX (12 digits, Book-Page-Block-Parcel)

The Clark County Assessor provides:
- Property characteristics
- Assessed values (based on tax cap regulations)
- Sales history
- Tax exemptions (Veteran, Senior, Disabled, etc.)
- Taxable value calculations
- Tax district information
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


class ClarkCountyAssessor(CountyAssessorBase):
    """
    Clark County, Nevada Assessor scraper.

    Uses the Clark County Assessor public data portal.
    Nevada has unique property tax caps (3% owner-occupied, 8% other).
    """

    COUNTY_NAME = "Clark County"
    STATE = "NV"
    FIPS_CODE = "32003"
    BASE_URL = "https://www.clarkcountynv.gov/assessor/"
    SYSTEM_NAME = "Clark County Assessor"

    # APN format: XXX-XX-XXX-XXX (12 digits)
    PARCEL_ID_FORMAT = "XXX-XX-XXX-XXX (Book-Page-Block-Parcel)"
    PARCEL_ID_PATTERN = r"^\d{3}-\d{2}-\d{3}-\d{3}$"

    # API endpoints
    SEARCH_URL = "https://maps.clarkcountynv.gov/assessor/api/property/search"
    DETAIL_URL = "https://maps.clarkcountynv.gov/assessor/api/property/detail"

    # Nevada property categories
    PROPERTY_CATEGORIES = {
        "1": "Vacant Land - Residential",
        "2": "Single Family Residential",
        "3": "Duplex",
        "4": "Apartment 3-4 Units",
        "5": "Apartment 5+ Units",
        "6": "Commercial",
        "7": "Industrial",
        "8": "Mobile Home",
        "9": "Mixed Use",
        "10": "Agricultural",
        "11": "Exempt",
        "12": "Timeshare",
        "13": "Hotel/Motel",
        "14": "Casino/Gaming",
    }

    # Major areas in Clark County
    AREAS = {
        "01": "Las Vegas Downtown",
        "02": "Las Vegas West",
        "03": "Las Vegas East",
        "04": "Las Vegas North",
        "05": "Las Vegas South",
        "06": "Summerlin",
        "07": "Spring Valley",
        "08": "Enterprise",
        "09": "Paradise",
        "10": "Winchester",
        "11": "Whitney",
        "12": "Sunrise Manor",
        "13": "North Las Vegas",
        "14": "Henderson Downtown",
        "15": "Henderson Green Valley",
        "16": "Henderson East",
        "17": "Boulder City",
        "18": "Laughlin",
        "19": "Mesquite",
        "20": "Moapa Valley",
        "21": "Indian Springs",
        "22": "Blue Diamond",
        "23": "Mt Charleston",
        "24": "Primm",
        "25": "Jean",
    }

    # Nevada tax cap rates
    TAX_CAP_OWNER_OCCUPIED = Decimal("0.03")  # 3% annual increase cap
    TAX_CAP_OTHER = Decimal("0.08")  # 8% annual increase cap

    # Exemption codes
    EXEMPTION_CODES = {
        "VET": ExemptionType.VETERAN,
        "BLINDVET": ExemptionType.VETERAN,
        "DISVET": ExemptionType.DISABLED_VETERAN,
        "SENIOR": ExemptionType.SENIOR_CITIZEN,
        "DISABLED": ExemptionType.DISABILITY,
        "SURVIVING": ExemptionType.WIDOW_WIDOWER,
        "HOMESTEAD": ExemptionType.HOMESTEAD,
        "RELIGIOUS": ExemptionType.RELIGIOUS,
        "CHARITABLE": ExemptionType.CHARITABLE,
        "GOVT": ExemptionType.GOVERNMENT,
        "SCHOOL": ExemptionType.EDUCATIONAL,
    }

    def _format_apn(self, apn: str) -> str:
        """Format an APN with dashes if not already formatted."""
        # Remove existing dashes, spaces
        clean = apn.replace("-", "").replace(" ", "").strip()

        if len(clean) == 12:
            return f"{clean[:3]}-{clean[3:5]}-{clean[5:8]}-{clean[8:12]}"
        return apn

    def _validate_apn(self, apn: str) -> bool:
        """Validate a Clark County APN format."""
        formatted = self._format_apn(apn)
        return bool(re.match(self.PARCEL_ID_PATTERN, formatted))

    def _parse_property_category(self, code: str) -> PropertyType:
        """Parse property category to property type."""
        if not code:
            return PropertyType.UNKNOWN

        code = str(code).strip()

        if code == "1":
            return PropertyType.VACANT_LAND
        elif code == "2":
            return PropertyType.SINGLE_FAMILY
        elif code in ("3", "4", "5"):
            return PropertyType.MULTI_FAMILY
        elif code == "6":
            return PropertyType.COMMERCIAL
        elif code == "7":
            return PropertyType.INDUSTRIAL
        elif code == "8":
            return PropertyType.MOBILE_HOME
        elif code == "9":
            return PropertyType.MIXED_USE
        elif code == "10":
            return PropertyType.AGRICULTURAL
        elif code == "11":
            return PropertyType.EXEMPT
        elif code == "12":
            return PropertyType.CONDO  # Timeshare
        elif code in ("13", "14"):
            return PropertyType.HOTEL_MOTEL

        return PropertyType.UNKNOWN

    def _parse_exemptions(self, exemption_data: Any) -> List[ExemptionType]:
        """Parse exemption data to list of ExemptionType."""
        exemptions = []
        if not exemption_data:
            return exemptions

        if isinstance(exemption_data, str):
            codes = exemption_data.upper().replace(",", " ").split()
        elif isinstance(exemption_data, list):
            codes = [str(e).upper() for e in exemption_data]
        else:
            return exemptions

        for code in codes:
            for key, exemption_type in self.EXEMPTION_CODES.items():
                if key in code:
                    exemptions.append(exemption_type)
                    break

        return exemptions

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
            logger.error(f"Clark County address search failed: {e}")
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
            logger.warning(f"Invalid Clark County APN format: {parcel_id}")
            return None

        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL, params={"apn": formatted_apn}
            )

            if json_response.get("property"):
                return self._parse_property_detail(json_response["property"])

        except Exception as e:
            logger.error(f"Clark County parcel search failed: {e}")

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
            logger.error(f"Clark County owner search failed: {e}")
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
            logger.error(f"Clark County property detail failed: {e}")

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
            city=data.get("city", data.get("siteCity", "Las Vegas")),
            state="NV",
            zip_code=data.get("zip", data.get("siteZip")),
            county=self.COUNTY_NAME,
            property_type=self._parse_property_category(
                data.get("propertyCategory", data.get("useCode", ""))
            ),
            assessed_value=self._parse_decimal(data.get("taxableValue")),
            market_value=self._parse_decimal(data.get("totalValue")),
            land_value=self._parse_decimal(data.get("landValue")),
            improvement_value=self._parse_decimal(data.get("improvementValue")),
            current_owner=owner_info,
            source_url=f"{self.BASE_URL}AssessorParcel/?parcel={formatted_apn}",
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
        chars_data = data.get("characteristics", data.get("residential", {}))
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
            garage_sqft=self._parse_int(chars_data.get("garageSqft")),
            garage_spaces=self._parse_int(chars_data.get("garageSpaces")),
            pool=chars_data.get("pool", False),
            pool_type=chars_data.get("poolType"),
            central_air=chars_data.get("cooling", "").upper()
            in ("CENTRAL", "AC", "YES"),
            heating_type=chars_data.get("heating"),
            cooling_type=chars_data.get("cooling"),
            construction_type=chars_data.get("constructionType"),
            roof_type=chars_data.get("roofType"),
            exterior_wall=chars_data.get("exteriorWall"),
            quality=chars_data.get("quality"),
            condition=chars_data.get("condition"),
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
            for assessment in data.get("valueHistory", []):
                exemptions = self._parse_exemptions(assessment.get("exemptions"))
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
                            assessment.get("assessedValue")
                        ),
                        market_value_total=self._parse_decimal(
                            assessment.get("totalValue")
                        ),
                        exemptions=exemptions,
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
                sale_date = self._parse_date(
                    sale.get("saleDate", sale.get("recordedDate"))
                )
                if sale_date:
                    sales_history.append(
                        SaleRecord(
                            sale_date=sale_date,
                            sale_price=self._parse_decimal(sale.get("salePrice"))
                            or Decimal(0),
                            buyer_name=sale.get("grantee", sale.get("buyer")),
                            seller_name=sale.get("grantor", sale.get("seller")),
                            document_number=sale.get("documentNumber"),
                            document_type=sale.get("documentType"),
                            sale_type=sale.get("saleType"),
                        )
                    )

        return PropertyAssessment(
            parcel_id=formatted_apn,
            property_address=data.get("siteAddress", data.get("address", "")),
            city=data.get("city", data.get("siteCity", "Las Vegas")),
            state="NV",
            zip_code=data.get("zip", data.get("siteZip")),
            county=self.COUNTY_NAME,
            legal_description=data.get("legalDescription"),
            subdivision=data.get("subdivision"),
            property_type=self._parse_property_category(
                data.get("propertyCategory", data.get("useCode", ""))
            ),
            property_use=data.get("propertyUse"),
            neighborhood=data.get("area"),
            assessed_value=self._parse_decimal(data.get("taxableValue")),
            market_value=self._parse_decimal(data.get("totalValue")),
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
            source_url=f"{self.BASE_URL}AssessorParcel/?parcel={formatted_apn}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )


# Synchronous convenience functions


def get_clark_county_property(apn: str) -> Optional[PropertyAssessment]:
    """Get Clark County property by APN."""

    async def _get():
        async with ClarkCountyAssessor() as assessor:
            return await assessor.get_property_detail(apn)

    return asyncio.run(_get())


def search_clark_county_by_address(
    address: str,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    max_results: int = 100,
) -> AssessorSearchResult:
    """Search Clark County properties by address."""

    async def _search():
        async with ClarkCountyAssessor() as assessor:
            return await assessor.search_by_address(
                address, city=city, zip_code=zip_code, max_results=max_results
            )

    return asyncio.run(_search())


def search_clark_county_by_owner(
    owner_name: str, max_results: int = 100
) -> AssessorSearchResult:
    """Search Clark County properties by owner name."""

    async def _search():
        async with ClarkCountyAssessor() as assessor:
            return await assessor.search_by_owner(owner_name, max_results=max_results)

    return asyncio.run(_search())
