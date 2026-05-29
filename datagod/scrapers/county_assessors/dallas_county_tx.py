"""
Dallas County, Texas Assessor Scraper

Dallas County is the ninth most populous county in the US with approximately
2.6 million residents. The Dallas Central Appraisal District (DCAD) maintains
property records for approximately 800,000 parcels.

Website: https://www.dallascad.org/
Account Format: Various formats accepted
               Property ID, Geographic ID, Account Number

The Dallas Central Appraisal District provides:
- Property characteristics
- Appraised values (annual reappraisal cycle)
- Sales history
- Tax exemptions (Homestead, Over 65, Disabled Veteran, etc.)
- Protest information
- Tax rate information for all jurisdictions
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


class DallasCountyAssessor(CountyAssessorBase):
    """
    Dallas County, Texas Appraisal District scraper.

    Uses the Dallas Central Appraisal District (DCAD) public data portal.
    """

    COUNTY_NAME = "Dallas County"
    STATE = "TX"
    FIPS_CODE = "48113"
    BASE_URL = "https://www.dallascad.org/"
    SYSTEM_NAME = "Dallas Central Appraisal District (DCAD)"

    # Account format: Various (property ID or account number)
    PARCEL_ID_FORMAT = "Property ID or Account Number"
    PARCEL_ID_PATTERN = r"^\d{6,12}$"

    # API endpoints
    SEARCH_URL = "https://www.dallascad.org/api/property/search"
    DETAIL_URL = "https://www.dallascad.org/api/property/detail"

    # Texas property class codes (DCAD specific)
    PROPERTY_CLASSES = {
        "A1": "Single Family Residential",
        "A2": "Mobile Home (Real Property)",
        "B1": "Multi-Family",
        "B2": "Multi-Family (4+)",
        "C1": "Vacant Lots",
        "C2": "Colonia Lots",
        "D1": "Qualified Ag Land",
        "D2": "Non-Qualified Ag Land",
        "E1": "Farm/Ranch Improved",
        "E2": "Farm/Ranch Land Only",
        "F1": "Commercial Real Property",
        "F2": "Industrial Real Property",
        "G1": "Oil, Gas, Minerals",
        "J1": "Water Systems",
        "J2": "Gas Systems",
        "J3": "Electric Companies",
        "J4": "Telephone Companies",
        "J5": "Railroads",
        "J6": "Pipelines",
        "J7": "Cable TV",
        "L1": "Commercial Personal Property",
        "L2": "Industrial Personal Property",
        "M1": "Tangible Other Personal Property",
        "M2": "Mobile Homes (Personal)",
        "N1": "Intangible Personal Property",
        "O1": "Residential Inventory",
        "S1": "Special Inventory",
        "X1": "Exempt Property",
    }

    # Major cities in Dallas County
    CITIES = {
        "DALLAS": "Dallas",
        "IRVING": "Irving",
        "GARLAND": "Garland",
        "GRAND PRAIRIE": "Grand Prairie",
        "MESQUITE": "Mesquite",
        "CARROLLTON": "Carrollton",
        "RICHARDSON": "Richardson",
        "ROWLETT": "Rowlett",
        "DESOTO": "DeSoto",
        "DUNCANVILLE": "Duncanville",
        "LANCASTER": "Lancaster",
        "CEDAR HILL": "Cedar Hill",
        "FARMERS BRANCH": "Farmers Branch",
        "COPPELL": "Coppell",
        "ADDISON": "Addison",
        "BALCH SPRINGS": "Balch Springs",
        "GLENN HEIGHTS": "Glenn Heights",
        "HUTCHINS": "Hutchins",
        "WILMER": "Wilmer",
        "SEAGOVILLE": "Seagoville",
        "SUNNYVALE": "Sunnyvale",
        "SACHSE": "Sachse",
        "WYLIE": "Wylie",
    }

    # Texas exemption types
    EXEMPTION_CODES = {
        "HS": ExemptionType.HOMESTEAD,
        "OV65": ExemptionType.SENIOR_CITIZEN,
        "OV65S": ExemptionType.SENIOR_CITIZEN,
        "DP": ExemptionType.DISABILITY,
        "DV1": ExemptionType.DISABLED_VETERAN,
        "DV2": ExemptionType.DISABLED_VETERAN,
        "DV3": ExemptionType.DISABLED_VETERAN,
        "DV4": ExemptionType.DISABLED_VETERAN,
        "DVHS": ExemptionType.DISABLED_VETERAN,
        "FR": ExemptionType.FREEZE,
        "AG": ExemptionType.AGRICULTURAL,
        "CHAR": ExemptionType.CHARITABLE,
        "REL": ExemptionType.RELIGIOUS,
        "GOVT": ExemptionType.GOVERNMENT,
        "HIST": ExemptionType.HISTORIC,
        "SOL": ExemptionType.SOLAR_ENERGY,
    }

    def _parse_property_class(self, code: str) -> PropertyType:
        """Parse property class code to property type."""
        if not code:
            return PropertyType.UNKNOWN

        code = code.upper()[:2]

        if code == "A1":
            return PropertyType.SINGLE_FAMILY
        elif code == "A2":
            return PropertyType.MOBILE_HOME
        elif code in ("B1", "B2"):
            return PropertyType.MULTI_FAMILY
        elif code in ("C1", "C2"):
            return PropertyType.VACANT_LAND
        elif code in ("D1", "D2", "E1", "E2"):
            return PropertyType.AGRICULTURAL
        elif code == "F1":
            return PropertyType.COMMERCIAL
        elif code == "F2":
            return PropertyType.INDUSTRIAL
        elif code.startswith("G"):
            return PropertyType.OTHER  # Minerals
        elif code.startswith("J"):
            return PropertyType.UTILITY
        elif code.startswith("L"):
            return PropertyType.COMMERCIAL  # Personal property
        elif code == "M2":
            return PropertyType.MOBILE_HOME
        elif code == "X1":
            return PropertyType.EXEMPT

        return PropertyType.UNKNOWN

    def _parse_exemptions(self, exemption_string: str) -> List[ExemptionType]:
        """Parse exemption codes to list of ExemptionType."""
        exemptions = []
        if not exemption_string:
            return exemptions

        codes = exemption_string.upper().replace(",", " ").split()
        for code in codes:
            if code in self.EXEMPTION_CODES:
                exemptions.append(self.EXEMPTION_CODES[code])

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
            logger.error(f"Dallas County address search failed: {e}")
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
        """Search for a property by account/property ID."""
        # Clean the parcel ID
        clean_id = parcel_id.replace("-", "").replace(" ", "").strip()

        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL, params={"propertyId": clean_id}
            )

            if json_response.get("property"):
                return self._parse_property_detail(json_response["property"])

        except Exception as e:
            logger.error(f"Dallas County parcel search failed: {e}")

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
            logger.error(f"Dallas County owner search failed: {e}")
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
        clean_id = parcel_id.replace("-", "").replace(" ", "").strip()

        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL, params={"propertyId": clean_id, "include": "all"}
            )

            if json_response.get("property"):
                return self._parse_property_detail(
                    json_response["property"], include_history=True
                )

        except Exception as e:
            logger.error(f"Dallas County property detail failed: {e}")

        return None

    def _parse_search_result(
        self, data: Dict[str, Any]
    ) -> Optional[PropertyAssessment]:
        """Parse a search result into PropertyAssessment."""
        prop_id = data.get("propertyId", data.get("accountNumber", ""))
        if not prop_id:
            return None

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
            parcel_id=str(prop_id),
            property_address=data.get("siteAddress", data.get("address", "")),
            city=data.get("city", data.get("siteCity", "")),
            state="TX",
            zip_code=data.get("zip", data.get("siteZip")),
            county=self.COUNTY_NAME,
            property_type=self._parse_property_class(
                data.get("propertyClass", data.get("stateCode", ""))
            ),
            assessed_value=self._parse_decimal(data.get("appraisedValue")),
            market_value=self._parse_decimal(data.get("marketValue")),
            land_value=self._parse_decimal(data.get("landValue")),
            improvement_value=self._parse_decimal(data.get("improvementValue")),
            current_owner=owner_info,
            source_url=f"{self.BASE_URL}SearchOwner.aspx?PropertyID={prop_id}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

    def _parse_property_detail(
        self, data: Dict[str, Any], include_history: bool = False
    ) -> PropertyAssessment:
        """Parse detailed property data."""
        prop_id = data.get("propertyId", data.get("accountNumber", ""))

        # Parse characteristics
        chars_data = data.get("characteristics", data.get("improvements", {}))
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
            lot_sqft=self._parse_int(chars_data.get("landSqft")),
            lot_acres=self._parse_float(chars_data.get("landAcres")),
            garage_sqft=self._parse_int(chars_data.get("garageSqft")),
            pool=chars_data.get("pool", False),
            construction_type=chars_data.get("constructionType"),
            roof_type=chars_data.get("roofType"),
            exterior_wall=chars_data.get("exteriorWall"),
            foundation=chars_data.get("foundation"),
            heating_type=chars_data.get("heatingType"),
            cooling_type=chars_data.get("coolingType"),
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
                exemptions = self._parse_exemptions(assessment.get("exemptions", ""))
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
                            assessment.get("appraisedValue")
                        ),
                        market_value_total=self._parse_decimal(
                            assessment.get("marketValue")
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

        # Parse sales history (deed transfers)
        sales_history = []
        if include_history:
            for sale in data.get("deedHistory", data.get("salesHistory", [])):
                sale_date = self._parse_date(sale.get("deedDate", sale.get("saleDate")))
                if sale_date:
                    sales_history.append(
                        SaleRecord(
                            sale_date=sale_date,
                            sale_price=self._parse_decimal(
                                sale.get("consideration", sale.get("salePrice"))
                            )
                            or Decimal(0),
                            buyer_name=sale.get("grantee"),
                            seller_name=sale.get("grantor"),
                            document_number=sale.get("deedBook"),
                            document_type=sale.get("deedType"),
                        )
                    )

        return PropertyAssessment(
            parcel_id=str(prop_id),
            property_address=data.get("siteAddress", data.get("address", "")),
            city=data.get("city", data.get("siteCity", "")),
            state="TX",
            zip_code=data.get("zip", data.get("siteZip")),
            county=self.COUNTY_NAME,
            legal_description=data.get("legalDescription"),
            property_type=self._parse_property_class(
                data.get("propertyClass", data.get("stateCode", ""))
            ),
            neighborhood=data.get("neighborhood"),
            assessed_value=self._parse_decimal(data.get("appraisedValue")),
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
            census_tract=data.get("censusTract"),
            source_url=f"{self.BASE_URL}SearchOwner.aspx?PropertyID={prop_id}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )


# Synchronous convenience functions


def get_dallas_county_property(property_id: str) -> Optional[PropertyAssessment]:
    """Get Dallas County property by property ID."""

    async def _get():
        async with DallasCountyAssessor() as assessor:
            return await assessor.get_property_detail(property_id)

    return asyncio.run(_get())


def search_dallas_county_by_address(
    address: str,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    max_results: int = 100,
) -> AssessorSearchResult:
    """Search Dallas County properties by address."""

    async def _search():
        async with DallasCountyAssessor() as assessor:
            return await assessor.search_by_address(
                address, city=city, zip_code=zip_code, max_results=max_results
            )

    return asyncio.run(_search())


def search_dallas_county_by_owner(
    owner_name: str, max_results: int = 100
) -> AssessorSearchResult:
    """Search Dallas County properties by owner name."""

    async def _search():
        async with DallasCountyAssessor() as assessor:
            return await assessor.search_by_owner(owner_name, max_results=max_results)

    return asyncio.run(_search())
