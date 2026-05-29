"""
King County, Washington Assessor Scraper

King County (Seattle) is the thirteenth most populous county in the US with
approximately 2.3 million residents. The King County Assessor's Office
maintains property records for approximately 700,000 parcels.

Website: https://blue.kingcounty.com/Assessor/eRealProperty/
Parcel Number Format: XXXXXXXXXX (10 digits)
                     Typically split as Major (6) + Minor (4)

The King County Assessor provides:
- Property characteristics
- Assessed values (annual reappraisal cycle)
- Sales history
- Tax exemptions (Senior/Disabled Citizen, Open Space, etc.)
- Current use valuations
- Environmentally sensitive areas
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


class KingCountyAssessor(CountyAssessorBase):
    """
    King County, Washington Assessor scraper.

    Uses the King County Assessor's eRealProperty portal.
    """

    COUNTY_NAME = "King County"
    STATE = "WA"
    FIPS_CODE = "53033"
    BASE_URL = "https://blue.kingcounty.com/Assessor/eRealProperty/"
    SYSTEM_NAME = "King County eRealProperty"

    # Parcel format: 10 digits (Major 6 + Minor 4)
    PARCEL_ID_FORMAT = "XXXXXXXXXX (10 digits)"
    PARCEL_ID_PATTERN = r"^\d{10}$"

    # API endpoints
    SEARCH_URL = "https://blue.kingcounty.com/Assessor/api/property/search"
    DETAIL_URL = "https://blue.kingcounty.com/Assessor/api/property/detail"

    # Washington property use codes
    PROPERTY_USES = {
        "1": "Household - Single Family",
        "2": "Household - Duplex",
        "3": "Household - Triplex",
        "4": "Household - Fourplex",
        "5": "Household - 5+ Units",
        "6": "Condominium",
        "7": "Mobile Home",
        "11": "Vacant - Residential",
        "12": "Vacant - Commercial",
        "13": "Vacant - Industrial",
        "14": "Vacant - Agricultural",
        "21": "Commercial - Retail",
        "22": "Commercial - Office",
        "23": "Commercial - Warehouse",
        "24": "Commercial - Restaurant",
        "25": "Commercial - Hotel/Motel",
        "26": "Commercial - Auto Service",
        "27": "Commercial - Shopping Center",
        "28": "Commercial - Mixed Use",
        "31": "Industrial - Light",
        "32": "Industrial - Heavy",
        "33": "Industrial - Warehouse",
        "41": "Agricultural - Cropland",
        "42": "Agricultural - Timber",
        "43": "Agricultural - Pasture",
        "51": "Exempt - Government",
        "52": "Exempt - Religious",
        "53": "Exempt - Educational",
        "54": "Exempt - Charitable",
        "55": "Exempt - Other",
    }

    # King County cities
    CITIES = {
        "SEATTLE": "Seattle",
        "BELLEVUE": "Bellevue",
        "KENT": "Kent",
        "RENTON": "Renton",
        "FEDERAL WAY": "Federal Way",
        "KIRKLAND": "Kirkland",
        "AUBURN": "Auburn",
        "REDMOND": "Redmond",
        "SAMMAMISH": "Sammamish",
        "SHORELINE": "Shoreline",
        "BURIEN": "Burien",
        "BOTHELL": "Bothell",
        "ISSAQUAH": "Issaquah",
        "MAPLE VALLEY": "Maple Valley",
        "MERCER ISLAND": "Mercer Island",
        "TUKWILA": "Tukwila",
        "COVINGTON": "Covington",
        "WOODINVILLE": "Woodinville",
        "SEATAC": "SeaTac",
        "KENMORE": "Kenmore",
        "NEWCASTLE": "Newcastle",
        "NORMANDY PARK": "Normandy Park",
        "LAKE FOREST PARK": "Lake Forest Park",
        "CLYDE HILL": "Clyde Hill",
        "MEDINA": "Medina",
        "YARROW POINT": "Yarrow Point",
        "HUNTS POINT": "Hunts Point",
    }

    # Exemption codes for Washington
    EXEMPTION_CODES = {
        "SENIOR": ExemptionType.SENIOR_CITIZEN,
        "DISABLED": ExemptionType.DISABILITY,
        "VET": ExemptionType.VETERAN,
        "DISVET": ExemptionType.DISABLED_VETERAN,
        "OPENSPACE": ExemptionType.AGRICULTURAL,  # Current Use - Open Space
        "FARM": ExemptionType.AGRICULTURAL,
        "TIMBER": ExemptionType.AGRICULTURAL,
        "NONPROFIT": ExemptionType.CHARITABLE,
        "HISTORIC": ExemptionType.HISTORIC,
        "RELIGIOUS": ExemptionType.RELIGIOUS,
        "GOVT": ExemptionType.GOVERNMENT,
        "SCHOOL": ExemptionType.EDUCATIONAL,
    }

    def _format_parcel(self, parcel: str) -> str:
        """Format a parcel number to standard 10-digit format."""
        # Remove dashes, spaces
        clean = parcel.replace("-", "").replace(" ", "").strip()
        # Pad with leading zeros if needed
        return clean.zfill(10)

    def _validate_parcel(self, parcel: str) -> bool:
        """Validate a King County parcel number format."""
        formatted = self._format_parcel(parcel)
        return bool(re.match(self.PARCEL_ID_PATTERN, formatted))

    def _parse_use_code(self, code: str) -> PropertyType:
        """Parse use code to property type."""
        if not code:
            return PropertyType.UNKNOWN

        code = str(code).strip()

        if code == "1":
            return PropertyType.SINGLE_FAMILY
        elif code in ("2", "3", "4", "5"):
            return PropertyType.MULTI_FAMILY
        elif code == "6":
            return PropertyType.CONDO
        elif code == "7":
            return PropertyType.MOBILE_HOME
        elif code in ("11", "12", "13", "14"):
            return PropertyType.VACANT_LAND
        elif code in ("21", "24", "26", "27"):
            return PropertyType.RETAIL
        elif code == "22":
            return PropertyType.OFFICE
        elif code in ("23", "33"):
            return PropertyType.WAREHOUSE
        elif code == "25":
            return PropertyType.HOTEL_MOTEL
        elif code == "28":
            return PropertyType.MIXED_USE
        elif code in ("31", "32"):
            return PropertyType.INDUSTRIAL
        elif code in ("41", "42", "43"):
            return PropertyType.AGRICULTURAL
        elif code.startswith("5"):
            return PropertyType.EXEMPT

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
            logger.error(f"King County address search failed: {e}")
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
        """Search for a property by parcel number."""
        formatted_parcel = self._format_parcel(parcel_id)

        if not self._validate_parcel(formatted_parcel):
            logger.warning(f"Invalid King County parcel format: {parcel_id}")
            return None

        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL, params={"parcel": formatted_parcel}
            )

            if json_response.get("property"):
                return self._parse_property_detail(json_response["property"])

        except Exception as e:
            logger.error(f"King County parcel search failed: {e}")

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
            logger.error(f"King County owner search failed: {e}")
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
        formatted_parcel = self._format_parcel(parcel_id)

        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL, params={"parcel": formatted_parcel, "include": "all"}
            )

            if json_response.get("property"):
                return self._parse_property_detail(
                    json_response["property"], include_history=True
                )

        except Exception as e:
            logger.error(f"King County property detail failed: {e}")

        return None

    def _parse_search_result(
        self, data: Dict[str, Any]
    ) -> Optional[PropertyAssessment]:
        """Parse a search result into PropertyAssessment."""
        parcel = data.get("parcel", data.get("parcelNumber", ""))
        if not parcel:
            return None

        formatted_parcel = self._format_parcel(parcel)

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
            parcel_id=formatted_parcel,
            property_address=data.get("siteAddress", data.get("address", "")),
            city=data.get("city", data.get("siteCity", "")),
            state="WA",
            zip_code=data.get("zip", data.get("siteZip")),
            county=self.COUNTY_NAME,
            property_type=self._parse_use_code(
                data.get("presentUse", data.get("propertyUse", ""))
            ),
            assessed_value=self._parse_decimal(data.get("assessedValue")),
            market_value=self._parse_decimal(data.get("appraisedValue")),
            land_value=self._parse_decimal(data.get("landValue")),
            improvement_value=self._parse_decimal(data.get("improvementValue")),
            current_owner=owner_info,
            source_url=f"{self.BASE_URL}Dashboard.aspx?ParcelNbr={formatted_parcel}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

    def _parse_property_detail(
        self, data: Dict[str, Any], include_history: bool = False
    ) -> PropertyAssessment:
        """Parse detailed property data."""
        parcel = data.get("parcel", data.get("parcelNumber", ""))
        formatted_parcel = self._format_parcel(parcel)

        # Parse characteristics - King County has detailed building data
        chars_data = data.get("residential", data.get("building", {}))
        characteristics = PropertyCharacteristics(
            year_built=self._parse_int(
                chars_data.get("yrBuilt", chars_data.get("yearBuilt"))
            ),
            effective_year=self._parse_int(chars_data.get("yrRenovated")),
            building_sqft=self._parse_int(
                chars_data.get("sqFtTotLiving", chars_data.get("buildingSqft"))
            ),
            living_sqft=self._parse_int(chars_data.get("sqFtTotLiving")),
            gross_sqft=self._parse_int(chars_data.get("sqFtTotBasement", 0))
            + self._parse_int(chars_data.get("sqFtTotLiving", 0)),
            bedrooms=self._parse_int(chars_data.get("bedrooms")),
            bathrooms=self._parse_float(chars_data.get("bathFullCount", 0))
            + (self._parse_float(chars_data.get("bathHalfCount", 0)) * 0.5),
            full_baths=self._parse_int(chars_data.get("bathFullCount")),
            half_baths=self._parse_int(chars_data.get("bathHalfCount")),
            stories=self._parse_float(chars_data.get("stories")),
            lot_sqft=self._parse_int(data.get("sqFtLot", chars_data.get("lotSqft"))),
            lot_acres=self._parse_float(data.get("acres")),
            garage_sqft=self._parse_int(chars_data.get("sqFtGarageAttached", 0))
            + self._parse_int(chars_data.get("sqFtGarageDetached", 0)),
            basement_sqft=self._parse_int(chars_data.get("sqFtTotBasement")),
            basement_finished_sqft=self._parse_int(chars_data.get("sqFtFinBasement")),
            fireplace_count=self._parse_int(chars_data.get("fireplaces")),
            pool=chars_data.get("pool", False),
            condition=chars_data.get("condition"),
            quality=chars_data.get("bldgGrade"),  # King County grade system
            construction_type=chars_data.get("constClass"),
            roof_type=chars_data.get("roofType"),
            exterior_wall=chars_data.get("extFinish"),
            heating_type=chars_data.get("heatSystem"),
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
                            assessment.get("totalValue")
                        ),
                        market_value_total=self._parse_decimal(
                            assessment.get("appraisedValue")
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
            for sale in data.get("salesHistory", data.get("sales", [])):
                sale_date = self._parse_date(
                    sale.get("saleDate", sale.get("documentDate"))
                )
                if sale_date:
                    sales_history.append(
                        SaleRecord(
                            sale_date=sale_date,
                            sale_price=self._parse_decimal(sale.get("salePrice"))
                            or Decimal(0),
                            buyer_name=sale.get("grantee", sale.get("buyerName")),
                            seller_name=sale.get("grantor", sale.get("sellerName")),
                            document_number=sale.get(
                                "exciseTaxNbr", sale.get("documentNumber")
                            ),
                            document_type=sale.get("saleInstrument"),
                            sale_type=sale.get("saleReason"),
                            is_valid_sale=sale.get("principalUse", "Y") == "Y",
                        )
                    )

        return PropertyAssessment(
            parcel_id=formatted_parcel,
            property_address=data.get("siteAddress", data.get("address", "")),
            city=data.get("city", data.get("siteCity", "")),
            state="WA",
            zip_code=data.get("zip", data.get("siteZip")),
            county=self.COUNTY_NAME,
            legal_description=data.get("legalDescription"),
            property_type=self._parse_use_code(
                data.get("presentUse", data.get("propertyUse", ""))
            ),
            property_use=data.get("presentUse"),
            neighborhood=data.get("area"),
            assessed_value=self._parse_decimal(data.get("assessedValue")),
            market_value=self._parse_decimal(data.get("appraisedValue")),
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
            source_url=f"{self.BASE_URL}Dashboard.aspx?ParcelNbr={formatted_parcel}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )


# Synchronous convenience functions


def get_king_county_property(parcel_number: str) -> Optional[PropertyAssessment]:
    """Get King County property by parcel number."""

    async def _get():
        async with KingCountyAssessor() as assessor:
            return await assessor.get_property_detail(parcel_number)

    return asyncio.run(_get())


def search_king_county_by_address(
    address: str,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    max_results: int = 100,
) -> AssessorSearchResult:
    """Search King County properties by address."""

    async def _search():
        async with KingCountyAssessor() as assessor:
            return await assessor.search_by_address(
                address, city=city, zip_code=zip_code, max_results=max_results
            )

    return asyncio.run(_search())


def search_king_county_by_owner(
    owner_name: str, max_results: int = 100
) -> AssessorSearchResult:
    """Search King County properties by owner name."""

    async def _search():
        async with KingCountyAssessor() as assessor:
            return await assessor.search_by_owner(owner_name, max_results=max_results)

    return asyncio.run(_search())
