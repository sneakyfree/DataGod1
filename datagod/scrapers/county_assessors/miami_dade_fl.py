"""
Miami-Dade County, Florida Property Appraiser Scraper

Miami-Dade County is the seventh most populous county in the US with
approximately 2.7 million residents and 900,000+ parcels.

Website: https://www.miamidade.gov/pa/
Folio Format: XX-XXXX-XXX-XXXX (13 digits with dashes)
              District-Section-Subdivision-Parcel

The Miami-Dade County Property Appraiser provides:
- Property characteristics
- Assessment values (annual cycle)
- Sales history
- Tax exemptions (Homestead, Senior, Widow, Disabled Veteran)
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


class MiamiDadeCountyAssessor(CountyAssessorBase):
    """
    Miami-Dade County, Florida Property Appraiser scraper.

    Uses the Miami-Dade Property Appraiser's public portal.
    """

    COUNTY_NAME = "Miami-Dade County"
    STATE = "FL"
    FIPS_CODE = "12086"
    BASE_URL = "https://www.miamidade.gov/pa/"
    SYSTEM_NAME = "Miami-Dade Property Appraiser"

    # Folio format: XX-XXXX-XXX-XXXX (13 digits)
    PARCEL_ID_FORMAT = "XX-XXXX-XXX-XXXX (Folio Number)"
    PARCEL_ID_PATTERN = r"^\d{2}-\d{4}-\d{3}-\d{4}$"

    # API endpoints
    API_BASE = "https://www.miamidade.gov/Apps/PA/propertysearch/api/"
    PROPERTY_SEARCH = "https://www.miamidade.gov/Apps/PA/propertysearch/"

    # Municipal codes
    MUNICIPALITIES = {
        "01": "Unincorporated Miami-Dade",
        "02": "Miami",
        "03": "Miami Beach",
        "04": "Coral Gables",
        "05": "Hialeah",
        "06": "North Miami",
        "07": "North Miami Beach",
        "08": "Opa-locka",
        "09": "South Miami",
        "10": "Homestead",
        "11": "Florida City",
        "12": "Miami Springs",
        "13": "Virginia Gardens",
        "14": "Sweetwater",
        "15": "West Miami",
        "16": "El Portal",
        "17": "Biscayne Park",
        "18": "Miami Shores",
        "19": "Surfside",
        "20": "Bay Harbor Islands",
        "21": "Bal Harbour",
        "22": "Indian Creek",
        "23": "Golden Beach",
        "24": "Aventura",
        "25": "Sunny Isles Beach",
        "26": "Key Biscayne",
        "27": "Pinecrest",
        "28": "Palmetto Bay",
        "29": "Cutler Bay",
        "30": "Doral",
        "31": "Miami Gardens",
        "32": "Miami Lakes",
        "33": "Medley",
        "34": "Islandia",
    }

    # Property use codes (Florida DOR codes)
    USE_CODES = {
        "00": "Vacant Residential",
        "01": "Single Family",
        "02": "Mobile Home",
        "03": "Multi-Family (2-9 units)",
        "04": "Condominium",
        "05": "Cooperatives",
        "06": "Retirement Homes",
        "07": "Miscellaneous Residential",
        "08": "Multi-Family (10+ units)",
        "10": "Vacant Commercial",
        "11": "Stores",
        "12": "Mixed Use (Store/Office/Residential)",
        "13": "Department Stores",
        "14": "Supermarkets",
        "15": "Regional Shopping Centers",
        "16": "Community Shopping Centers",
        "17": "Office Buildings",
        "18": "Banks/Savings & Loan",
        "19": "Professional Service Buildings",
        "20": "Airports/Terminals",
        "21": "Restaurants/Cafeterias",
        "22": "Drive-in Restaurants",
        "23": "Financial Institutions",
        "24": "Insurance Company Offices",
        "25": "Repair Service Shops",
        "26": "Service Stations",
        "27": "Auto Sales/Repair",
        "28": "Parking Lots/Garages",
        "29": "Wholesale Outlets",
        "30": "Florist/Greenhouses",
        "31": "Drive-in Theater",
        "32": "Enclosed Theater",
        "33": "Nightclubs/Bars/Lounges",
        "34": "Bowling Alleys/Skating Rinks",
        "35": "Tourist Attractions",
        "36": "Camps",
        "37": "Race Tracks",
        "38": "Golf Courses",
        "39": "Hotels/Motels",
        "40": "Vacant Industrial",
        "41": "Light Manufacturing",
        "42": "Heavy Manufacturing",
        "43": "Lumber Yards",
        "44": "Packing Plants",
        "45": "Canneries/Distilleries",
        "46": "Other Food Processing",
        "47": "Mineral Processing",
        "48": "Warehousing/Distribution",
        "49": "Open Storage",
    }

    def _format_folio(self, folio: str) -> str:
        """Format a folio number with dashes if not already formatted."""
        # Remove existing dashes, spaces, and periods
        clean = folio.replace("-", "").replace(" ", "").replace(".", "").strip()

        if len(clean) == 13:
            return f"{clean[:2]}-{clean[2:6]}-{clean[6:9]}-{clean[9:13]}"
        return folio

    def _validate_folio(self, folio: str) -> bool:
        """Validate a Miami-Dade County folio format."""
        formatted = self._format_folio(folio)
        return bool(re.match(self.PARCEL_ID_PATTERN, formatted))

    def _get_municipality(self, folio: str) -> str:
        """Get municipality name from folio number."""
        formatted = self._format_folio(folio)
        muni_code = formatted[:2]
        return self.MUNICIPALITIES.get(muni_code, "Unknown")

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

        search_url = f"{self.API_BASE}search"

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
            logger.error(f"Miami-Dade address search failed: {e}")
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
        results = json_response.get(
            "properties", json_response.get("results", json_response.get("Parcel", []))
        )

        if isinstance(results, dict):
            results = [results]

        for item in results[:max_results]:
            prop = self._parse_search_result(item)
            if prop:
                properties.append(prop)

        search_time = int((time.time() - start_time) * 1000)

        return AssessorSearchResult(
            properties=properties,
            total_count=json_response.get(
                "totalCount", json_response.get("RecordCount", len(properties))
            ),
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
        """Search for a property by folio number."""
        formatted_folio = self._format_folio(parcel_id)

        if not self._validate_folio(formatted_folio):
            logger.warning(f"Invalid Miami-Dade folio format: {parcel_id}")
            return None

        return await self.get_property_detail(formatted_folio)

    async def search_by_owner(
        self, owner_name: str, max_results: int = 100
    ) -> AssessorSearchResult:
        """Search for properties by owner name."""
        import time

        start_time = time.time()

        search_url = f"{self.API_BASE}search"

        params = {
            "owner": owner_name,
            "limit": min(max_results, 100),
        }

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Miami-Dade owner search failed: {e}")
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
        results = json_response.get(
            "properties", json_response.get("results", json_response.get("Parcel", []))
        )

        if isinstance(results, dict):
            results = [results]

        for item in results[:max_results]:
            prop = self._parse_search_result(item)
            if prop:
                properties.append(prop)

        search_time = int((time.time() - start_time) * 1000)

        return AssessorSearchResult(
            properties=properties,
            total_count=json_response.get(
                "totalCount", json_response.get("RecordCount", len(properties))
            ),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=AssessorSearchCriteria(owner_name=owner_name),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_property_detail(self, parcel_id: str) -> Optional[PropertyAssessment]:
        """Get detailed property information."""
        formatted_folio = self._format_folio(parcel_id)

        # Remove dashes for API call
        folio_clean = formatted_folio.replace("-", "")
        detail_url = f"{self.API_BASE}parcel/{folio_clean}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"Miami-Dade property detail failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_property_detail(json_response, formatted_folio)

    def _parse_search_result(
        self, item: Dict[str, Any]
    ) -> Optional[PropertyAssessment]:
        """Parse a search result item."""
        folio = item.get("folio", item.get("FolioNumber", item.get("FOLIO", "")))
        if not folio:
            return None

        formatted_folio = self._format_folio(str(folio))

        return PropertyAssessment(
            parcel_id=formatted_folio,
            property_address=item.get(
                "situsAddress", item.get("SitusAddress", item.get("address", ""))
            ),
            city=item.get("situsCity", item.get("Municipality", item.get("city", ""))),
            state=self.STATE,
            zip_code=item.get("situsZip", item.get("SitusZip", item.get("zip", ""))),
            county=self.COUNTY_NAME,
            property_type=self._parse_property_type(
                item.get("useCode", item.get("DORCode", ""))
            ),
            assessed_value=self._parse_decimal(
                str(
                    item.get(
                        "assessedValue",
                        item.get("AssessedValue", item.get("JustValue", "")),
                    )
                )
            ),
            market_value=self._parse_decimal(
                str(item.get("marketValue", item.get("JustValue", "")))
            ),
            current_owner=(
                OwnershipRecord(
                    owner_name=item.get(
                        "ownerName", item.get("Owner1", item.get("owner", ""))
                    ),
                )
                if item.get("ownerName") or item.get("Owner1") or item.get("owner")
                else None
            ),
            source_url=f"{self.PROPERTY_SEARCH}#/folio/{formatted_folio.replace('-', '')}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_property_detail(
        self, data: Dict[str, Any], folio: str
    ) -> PropertyAssessment:
        """Parse detailed property data."""
        # Handle nested structure from Miami-Dade API
        property_info = data.get("PropertyInfo", data)
        building_info = data.get("BuildingInfo", data.get("Building", {}))
        land_info = data.get("LandInfo", data.get("Land", {}))
        value_info = data.get("ValueInfo", data.get("Values", {}))

        if isinstance(building_info, list) and building_info:
            building_info = building_info[0]

        # Parse characteristics
        characteristics = PropertyCharacteristics(
            year_built=self._parse_int(
                str(building_info.get("YearBuilt", building_info.get("yearBuilt", "")))
            ),
            effective_year_built=self._parse_int(
                str(
                    building_info.get(
                        "EffectiveYearBuilt", building_info.get("actualYearBuilt", "")
                    )
                )
            ),
            building_sqft=self._parse_int(
                str(building_info.get("GrossArea", building_info.get("totalSqft", "")))
            ),
            living_sqft=self._parse_int(
                str(
                    building_info.get("LivingArea", building_info.get("livingArea", ""))
                )
            ),
            bedrooms=self._parse_int(
                str(building_info.get("Bedrooms", building_info.get("bedrooms", "")))
            ),
            bathrooms=self._parse_float(
                str(building_info.get("Bathrooms", building_info.get("bathrooms", "")))
            ),
            full_baths=self._parse_int(str(building_info.get("FullBaths", ""))),
            half_baths=self._parse_int(str(building_info.get("HalfBaths", ""))),
            stories=self._parse_float(
                str(building_info.get("Stories", building_info.get("floors", "")))
            ),
            units=self._parse_int(
                str(building_info.get("Units", building_info.get("numberOfUnits", "")))
            ),
            garage_type=building_info.get("GarageType", building_info.get("parking")),
            garage_spaces=self._parse_int(
                str(
                    building_info.get(
                        "GarageSpaces", building_info.get("parkingSpaces", "")
                    )
                )
            ),
            lot_sqft=self._parse_int(
                str(land_info.get("LandSqFt", land_info.get("sqft", "")))
            ),
            lot_acres=self._parse_float(
                str(land_info.get("Acres", land_info.get("acres", "")))
            ),
            construction_type=building_info.get(
                "ConstructionType", building_info.get("construction")
            ),
            exterior_wall=building_info.get(
                "ExteriorWall", building_info.get("exterior")
            ),
            roof_type=building_info.get("RoofType", building_info.get("roof")),
            foundation_type=building_info.get(
                "Foundation", building_info.get("foundation")
            ),
            central_air=building_info.get("AC") == "Y"
            or "CENTRAL" in str(building_info.get("Cooling", "")).upper(),
            heating_type=building_info.get("Heating", building_info.get("heat")),
            pool=building_info.get("Pool") == "Y"
            or building_info.get("hasPool", False),
            fireplace_count=self._parse_int(str(building_info.get("Fireplaces", ""))),
            raw_characteristics=building_info,
        )

        # Parse value history - Florida uses Just Value, Assessed Value, Taxable Value
        assessment_history = []
        value_history = data.get("ValueHistory", data.get("valueHistory", []))

        if value_info and not value_history:
            # Single year data
            value_history = [value_info]

        for assessment in value_history:
            tax_assessment = TaxAssessment(
                tax_year=assessment.get("TaxYear", assessment.get("year", 0)),
                assessed_value_land=self._parse_decimal(
                    str(assessment.get("LandValue", assessment.get("landValue", "")))
                ),
                assessed_value_improvements=self._parse_decimal(
                    str(
                        assessment.get(
                            "BuildingValue", assessment.get("buildingValue", "")
                        )
                    )
                ),
                assessed_value_total=self._parse_decimal(
                    str(
                        assessment.get(
                            "AssessedValue", assessment.get("assessedValue", "")
                        )
                    )
                ),
                market_value_total=self._parse_decimal(
                    str(assessment.get("JustValue", assessment.get("justValue", "")))
                ),
                taxable_value=self._parse_decimal(
                    str(
                        assessment.get(
                            "TaxableValue", assessment.get("taxableValue", "")
                        )
                    )
                ),
            )
            assessment_history.append(tax_assessment)

        # Parse sales history
        sales_history = []
        for sale in data.get(
            "SalesHistory", data.get("Sales", data.get("salesHistory", []))
        ):
            sale_record = SaleRecord(
                sale_date=self._parse_date(
                    sale.get(
                        "SaleDate", sale.get("DateOfSale", sale.get("saleDate", ""))
                    )
                )
                or date.today(),
                sale_price=self._parse_decimal(
                    str(
                        sale.get(
                            "SalePrice", sale.get("Price", sale.get("salePrice", ""))
                        )
                    )
                )
                or Decimal(0),
                buyer_name=sale.get("Grantee", sale.get("buyer")),
                seller_name=sale.get("Grantor", sale.get("seller")),
                document_number=(
                    sale.get("ORBook", "") + "/" + sale.get("ORPage", "")
                    if sale.get("ORBook")
                    else sale.get("docNumber")
                ),
                document_type=sale.get(
                    "DeedType", sale.get("InstrumentType", sale.get("deedType"))
                ),
                qualified_sale=sale.get("QualifiedSale", sale.get("Qualified")) == "Y",
            )
            sales_history.append(sale_record)

        # Parse ownership
        owner1 = property_info.get(
            "Owner1", property_info.get("ownerName", data.get("Owner1", ""))
        )
        owner2 = property_info.get("Owner2", data.get("Owner2", ""))
        owner_name = f"{owner1} / {owner2}" if owner2 else owner1

        mailing = data.get("MailingAddress", data.get("Mailing", {}))

        current_owner = (
            OwnershipRecord(
                owner_name=owner_name,
                mailing_address=mailing.get(
                    "Address",
                    mailing.get("address", property_info.get("MailingAddress")),
                ),
                mailing_city=mailing.get(
                    "City", mailing.get("city", property_info.get("MailingCity"))
                ),
                mailing_state=mailing.get(
                    "State", mailing.get("state", property_info.get("MailingState"))
                ),
                mailing_zip=mailing.get(
                    "Zip", mailing.get("zip", property_info.get("MailingZip"))
                ),
            )
            if owner_name
            else None
        )

        # Parse exemptions - Florida has many exemption types
        exemptions = []
        exemption_data = data.get("Exemptions", data.get("exemptions", []))

        if isinstance(exemption_data, str):
            exemption_data = [{"type": exemption_data}]
        elif isinstance(exemption_data, dict):
            exemption_data = [exemption_data]

        for exemption in exemption_data:
            exemption_type = str(
                exemption.get(
                    "type", exemption.get("ExemptionType", exemption.get("Code", ""))
                )
            ).upper()

            if "HOMESTEAD" in exemption_type or exemption_type == "HX":
                exemptions.append(ExemptionType.HOMESTEAD)
            elif "SENIOR" in exemption_type or "ADDITIONAL" in exemption_type:
                exemptions.append(ExemptionType.SENIOR_CITIZEN)
            elif "WIDOW" in exemption_type or "WIDOWER" in exemption_type:
                exemptions.append(ExemptionType.WIDOW_WIDOWER)
            elif "DISABLED" in exemption_type and "VETERAN" in exemption_type:
                exemptions.append(ExemptionType.DISABLED_VETERAN)
            elif "VETERAN" in exemption_type:
                exemptions.append(ExemptionType.VETERAN)
            elif "DISABLED" in exemption_type or "DISABILITY" in exemption_type:
                exemptions.append(ExemptionType.DISABILITY)
            elif "BLIND" in exemption_type:
                exemptions.append(ExemptionType.BLIND)
            elif "NONPROFIT" in exemption_type or "CHARITABLE" in exemption_type:
                exemptions.append(ExemptionType.CHARITABLE)
            elif "RELIGIOUS" in exemption_type or "CHURCH" in exemption_type:
                exemptions.append(ExemptionType.RELIGIOUS)
            elif (
                "GOVERNMENT" in exemption_type
                or "COUNTY" in exemption_type
                or "STATE" in exemption_type
            ):
                exemptions.append(ExemptionType.GOVERNMENT)

        # Get current assessment
        current_assessment = assessment_history[0] if assessment_history else None

        # Get DOR use code and description
        use_code = property_info.get("DORCode", property_info.get("UseCode", ""))
        use_description = self.USE_CODES.get(
            use_code, property_info.get("UseDescription", "")
        )

        # Build property URL
        folio_clean = folio.replace("-", "")

        return PropertyAssessment(
            parcel_id=folio,
            property_address=property_info.get(
                "SitusAddress",
                property_info.get("situsAddress", data.get("SitusAddress", "")),
            ),
            city=property_info.get(
                "Municipality", property_info.get("city", self._get_municipality(folio))
            ),
            state=self.STATE,
            zip_code=property_info.get("SitusZip", property_info.get("zip", "")),
            county=self.COUNTY_NAME,
            legal_description=property_info.get(
                "LegalDescription", property_info.get("legal")
            ),
            subdivision=property_info.get(
                "Subdivision", property_info.get("subdivision")
            ),
            property_type=self._parse_property_type(use_code),
            property_class=self._parse_property_class(use_code),
            property_use=use_description,
            zoning=property_info.get("Zoning", property_info.get("zoning")),
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
            latitude=self._parse_float(
                str(
                    property_info.get(
                        "Latitude", property_info.get("lat", data.get("Latitude", ""))
                    )
                )
            ),
            longitude=self._parse_float(
                str(
                    property_info.get(
                        "Longitude", property_info.get("lng", data.get("Longitude", ""))
                    )
                )
            ),
            neighborhood=property_info.get(
                "Neighborhood", property_info.get("neighborhood")
            ),
            source_url=f"{self.PROPERTY_SEARCH}#/folio/{folio_clean}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

    def _parse_property_type(self, use_code: str) -> Optional[PropertyType]:
        """Parse Florida DOR use codes to PropertyType."""
        if not use_code:
            return None

        code = str(use_code).strip()[:2].zfill(2)

        code_mapping = {
            "00": PropertyType.VACANT_LAND,
            "01": PropertyType.SINGLE_FAMILY,
            "02": PropertyType.MOBILE_HOME,
            "03": PropertyType.MULTI_FAMILY,
            "04": PropertyType.CONDOMINIUM,
            "05": PropertyType.COOPERATIVE,
            "06": PropertyType.MULTI_FAMILY,  # Retirement
            "07": PropertyType.SINGLE_FAMILY,  # Misc residential
            "08": PropertyType.MULTI_FAMILY,  # 10+ units
            "10": PropertyType.VACANT_LAND,
            "11": PropertyType.COMMERCIAL,
            "12": PropertyType.MIXED_USE,
            "13": PropertyType.COMMERCIAL,
            "14": PropertyType.COMMERCIAL,
            "15": PropertyType.COMMERCIAL,
            "16": PropertyType.COMMERCIAL,
            "17": PropertyType.COMMERCIAL,
            "18": PropertyType.COMMERCIAL,
            "19": PropertyType.COMMERCIAL,
            "20": PropertyType.COMMERCIAL,
            "39": PropertyType.COMMERCIAL,  # Hotels
            "40": PropertyType.VACANT_LAND,  # Industrial vacant
            "41": PropertyType.INDUSTRIAL,
            "42": PropertyType.INDUSTRIAL,
            "48": PropertyType.INDUSTRIAL,  # Warehouse
        }

        return code_mapping.get(code)

    def _parse_property_class(self, use_code: str) -> Optional[PropertyClass]:
        """Parse Florida DOR use codes to PropertyClass."""
        if not use_code:
            return None

        code = str(use_code).strip()[:1]

        class_mapping = {
            "0": PropertyClass.RESIDENTIAL,
            "1": PropertyClass.COMMERCIAL,
            "2": PropertyClass.COMMERCIAL,
            "3": PropertyClass.COMMERCIAL,
            "4": PropertyClass.INDUSTRIAL,
            "5": PropertyClass.AGRICULTURAL,
            "6": PropertyClass.INSTITUTIONAL,
            "7": PropertyClass.GOVERNMENT,
            "8": PropertyClass.MISCELLANEOUS,
            "9": PropertyClass.EXEMPT,
        }

        return class_mapping.get(code)


# Convenience functions


def search_miami_dade_address(address: str, **kwargs) -> AssessorSearchResult:
    """Search Miami-Dade County properties by address."""
    assessor = MiamiDadeCountyAssessor()

    async def _search():
        async with assessor:
            return await assessor.search_by_address(address, **kwargs)

    return asyncio.run(_search())


def search_miami_dade_owner(owner_name: str, **kwargs) -> AssessorSearchResult:
    """Search Miami-Dade County properties by owner name."""
    assessor = MiamiDadeCountyAssessor()

    async def _search():
        async with assessor:
            return await assessor.search_by_owner(owner_name, **kwargs)

    return asyncio.run(_search())


def get_miami_dade_property(folio: str) -> Optional[PropertyAssessment]:
    """Get Miami-Dade County property details by folio number."""
    assessor = MiamiDadeCountyAssessor()

    async def _get():
        async with assessor:
            return await assessor.get_property_detail(folio)

    return asyncio.run(_get())
