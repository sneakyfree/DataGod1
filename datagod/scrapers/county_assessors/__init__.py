"""
County Assessors Scrapers Package

This package contains scrapers for extracting property assessment and
tax information from county assessor offices across the United States.

County assessors maintain records of:
- Property valuations (assessed value, market value)
- Property characteristics (size, bedrooms, bathrooms, etc.)
- Property ownership history
- Tax assessments and exemptions
- Property classifications (residential, commercial, agricultural)
- Improvement details (buildings, structures)
- Land characteristics

Most counties provide public access to this information through:
- Online property search portals
- GIS/mapping systems
- Downloadable data files
- API access (rare but growing)
"""

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
from .clark_county_nv import (
    ClarkCountyAssessor,
    get_clark_county_property,
    search_clark_county_by_address,
    search_clark_county_by_owner,
)
from .cook_county_il import (
    CookCountyAssessor,
    get_cook_county_property,
    search_cook_county_address,
    search_cook_county_owner,
)
from .dallas_county_tx import (
    DallasCountyAssessor,
    get_dallas_county_property,
    search_dallas_county_by_address,
    search_dallas_county_by_owner,
)
from .harris_county_tx import (
    HarrisCountyAssessor,
    get_harris_county_property,
    search_harris_county_address,
    search_harris_county_owner,
)
from .king_county_wa import (
    KingCountyAssessor,
    get_king_county_property,
    search_king_county_by_address,
    search_king_county_by_owner,
)
from .los_angeles_ca import (
    LosAngelesCountyAssessor,
    get_la_county_property,
    search_la_county_address,
    search_la_county_owner,
)
from .maricopa_county_az import (
    MaricopaCountyAssessor,
    get_maricopa_county_property,
    search_maricopa_county_address,
    search_maricopa_county_owner,
)
from .miami_dade_fl import (
    MiamiDadeCountyAssessor,
    get_miami_dade_property,
    search_miami_dade_address,
    search_miami_dade_owner,
)
from .orange_county_ca import (
    OrangeCountyAssessor,
    get_orange_county_property,
    search_orange_county_by_address,
    search_orange_county_by_owner,
)
from .san_diego_ca import (
    SanDiegoCountyAssessor,
    get_san_diego_property,
    search_san_diego_by_address,
    search_san_diego_by_owner,
)

__all__ = [
    # Base classes and types
    "CountyAssessorBase",
    "PropertyType",
    "PropertyClass",
    "ExemptionType",
    "PropertyAssessment",
    "PropertyCharacteristics",
    "TaxAssessment",
    "OwnershipRecord",
    "SaleRecord",
    "AssessorSearchCriteria",
    "AssessorSearchResult",
    # Cook County, IL
    "CookCountyAssessor",
    "search_cook_county_address",
    "search_cook_county_owner",
    "get_cook_county_property",
    # Los Angeles County, CA
    "LosAngelesCountyAssessor",
    "search_la_county_address",
    "search_la_county_owner",
    "get_la_county_property",
    # Harris County, TX
    "HarrisCountyAssessor",
    "search_harris_county_address",
    "search_harris_county_owner",
    "get_harris_county_property",
    # Maricopa County, AZ
    "MaricopaCountyAssessor",
    "search_maricopa_county_address",
    "search_maricopa_county_owner",
    "get_maricopa_county_property",
    # Miami-Dade County, FL
    "MiamiDadeCountyAssessor",
    "search_miami_dade_address",
    "search_miami_dade_owner",
    "get_miami_dade_property",
    # San Diego County, CA
    "SanDiegoCountyAssessor",
    "get_san_diego_property",
    "search_san_diego_by_address",
    "search_san_diego_by_owner",
    # Orange County, CA
    "OrangeCountyAssessor",
    "get_orange_county_property",
    "search_orange_county_by_address",
    "search_orange_county_by_owner",
    # Dallas County, TX
    "DallasCountyAssessor",
    "get_dallas_county_property",
    "search_dallas_county_by_address",
    "search_dallas_county_by_owner",
    # King County, WA
    "KingCountyAssessor",
    "get_king_county_property",
    "search_king_county_by_address",
    "search_king_county_by_owner",
    # Clark County, NV
    "ClarkCountyAssessor",
    "get_clark_county_property",
    "search_clark_county_by_address",
    "search_clark_county_by_owner",
]
