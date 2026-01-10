"""
County Treasurer/Tax Collector Scrapers Package

This package provides scrapers for property tax records, tax liens,
and tax sale information from county treasurer/tax collector offices.

Supported counties:
- Cook County, IL (Cook County Treasurer)
- Los Angeles County, CA (LA County Treasurer-Tax Collector)
- Harris County, TX (Harris County Tax Office)
- Maricopa County, AZ (Maricopa County Treasurer)
- Miami-Dade County, FL (Miami-Dade Tax Collector)
- San Diego County, CA (San Diego County TTC)
- Orange County, CA (Orange County TTC)
- Dallas County, TX (Dallas County Tax Office)
- King County, WA (King County Treasury)
- Clark County, NV (Clark County Treasurer)
"""

from .base import (
    # Enums
    TaxStatus,
    LienStatus,
    TaxSaleType,
    PaymentMethod,
    # Dataclasses
    TaxBillItem,
    TaxBill,
    TaxPayment,
    TaxLien,
    TaxSaleProperty,
    PropertyTaxRecord,
    TaxSearchCriteria,
    TaxSearchResult,
    # Base class
    CountyTreasurerBase,
)

from .cook_county_il import (
    CookCountyTreasurer,
    get_cook_county_tax_record,
    search_cook_county_by_address,
    search_cook_county_by_owner,
)

from .los_angeles_ca import (
    LosAngelesCountyTreasurer,
    get_la_county_tax_record,
    search_la_county_by_address,
    search_la_county_by_owner,
)

from .harris_county_tx import (
    HarrisCountyTreasurer,
    get_harris_county_tax_record,
    search_harris_county_by_address,
    search_harris_county_by_owner,
)

from .maricopa_county_az import (
    MaricopaCountyTreasurer,
    get_maricopa_county_tax_record,
    search_maricopa_county_by_address,
    search_maricopa_county_by_owner,
)

from .miami_dade_fl import (
    MiamiDadeCountyTreasurer,
    get_miami_dade_tax_record,
    search_miami_dade_by_address,
    search_miami_dade_by_owner,
)

from .san_diego_ca import (
    SanDiegoCountyTreasurer,
    get_san_diego_tax_record,
    search_san_diego_tax_by_address,
    search_san_diego_tax_by_owner,
)

from .orange_county_ca import (
    OrangeCountyTreasurer,
    get_orange_county_tax_record,
    search_orange_county_tax_by_address,
    search_orange_county_tax_by_owner,
)

from .dallas_county_tx import (
    DallasCountyTreasurer,
    get_dallas_county_tax_record,
    search_dallas_county_tax_by_address,
    search_dallas_county_tax_by_owner,
)

from .king_county_wa import (
    KingCountyTreasurer,
    get_king_county_tax_record,
    search_king_county_tax_by_address,
    search_king_county_tax_by_owner,
)

from .clark_county_nv import (
    ClarkCountyTreasurer,
    get_clark_county_tax_record,
    search_clark_county_tax_by_address,
    search_clark_county_tax_by_owner,
)

__all__ = [
    # Enums
    "TaxStatus",
    "LienStatus",
    "TaxSaleType",
    "PaymentMethod",
    # Dataclasses
    "TaxBillItem",
    "TaxBill",
    "TaxPayment",
    "TaxLien",
    "TaxSaleProperty",
    "PropertyTaxRecord",
    "TaxSearchCriteria",
    "TaxSearchResult",
    # Base class
    "CountyTreasurerBase",
    # Cook County IL
    "CookCountyTreasurer",
    "get_cook_county_tax_record",
    "search_cook_county_by_address",
    "search_cook_county_by_owner",
    # Los Angeles County CA
    "LosAngelesCountyTreasurer",
    "get_la_county_tax_record",
    "search_la_county_by_address",
    "search_la_county_by_owner",
    # Harris County TX
    "HarrisCountyTreasurer",
    "get_harris_county_tax_record",
    "search_harris_county_by_address",
    "search_harris_county_by_owner",
    # Maricopa County AZ
    "MaricopaCountyTreasurer",
    "get_maricopa_county_tax_record",
    "search_maricopa_county_by_address",
    "search_maricopa_county_by_owner",
    # Miami-Dade County FL
    "MiamiDadeCountyTreasurer",
    "get_miami_dade_tax_record",
    "search_miami_dade_by_address",
    "search_miami_dade_by_owner",
    # San Diego County CA
    "SanDiegoCountyTreasurer",
    "get_san_diego_tax_record",
    "search_san_diego_tax_by_address",
    "search_san_diego_tax_by_owner",
    # Orange County CA
    "OrangeCountyTreasurer",
    "get_orange_county_tax_record",
    "search_orange_county_tax_by_address",
    "search_orange_county_tax_by_owner",
    # Dallas County TX
    "DallasCountyTreasurer",
    "get_dallas_county_tax_record",
    "search_dallas_county_tax_by_address",
    "search_dallas_county_tax_by_owner",
    # King County WA
    "KingCountyTreasurer",
    "get_king_county_tax_record",
    "search_king_county_tax_by_address",
    "search_king_county_tax_by_owner",
    # Clark County NV
    "ClarkCountyTreasurer",
    "get_clark_county_tax_record",
    "search_clark_county_tax_by_address",
    "search_clark_county_tax_by_owner",
]
