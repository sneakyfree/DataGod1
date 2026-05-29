"""
County Sheriff and Inmate Scrapers Package

This package contains scrapers for extracting inmate, arrest, and jail
information from county sheriff offices across the United States.

County Sheriff departments typically maintain records of:
- Current jail inmates (booking, charges, bail)
- Recent arrests (booking records)
- Warrant searches (active warrants)
- Sex offender registrations (per state registry)
- Registered offender checks
- Jail roster (daily population)

Most counties provide public access through:
- Online inmate lookup portals
- Jail roster websites
- Sheriff department websites
- Third-party jail information systems (JailBase, VINELink)

Note: Access to this data varies significantly by jurisdiction.
Some counties provide extensive public access while others restrict
information to basic booking data only.
"""

from .base import (
    ArrestRecord,
    BondInformation,
    BondType,
    BookingRecord,
    ChargeSeverity,
    ChargeType,
    InmateCharge,
    InmateRecord,
    InmateSearchCriteria,
    InmateSearchResult,
    InmateStatus,
    ReleaseType,
    SheriffInmateBase,
    VisitationInfo,
    WarrantRecord,
)
from .cook_county_il import (
    CookCountySheriff,
    get_cook_county_inmate,
    search_cook_county_inmates,
)
from .harris_county_tx import (
    HarrisCountySheriff,
    get_harris_county_inmate,
    search_harris_county_inmates,
)
from .los_angeles_ca import (
    LosAngelesCountySheriff,
    get_la_county_inmate,
    search_la_county_inmates,
)
from .maricopa_county_az import (
    MaricopaCountySheriff,
    get_maricopa_county_inmate,
    search_maricopa_county_inmates,
)
from .miami_dade_fl import (
    MiamiDadeCorrections,
    get_miami_dade_inmate,
    search_miami_dade_inmates,
)

__all__ = [
    # Base classes and types
    "SheriffInmateBase",
    "InmateStatus",
    "ChargeType",
    "ChargeSeverity",
    "BondType",
    "ReleaseType",
    "InmateRecord",
    "BookingRecord",
    "InmateCharge",
    "BondInformation",
    "VisitationInfo",
    "ArrestRecord",
    "WarrantRecord",
    "InmateSearchCriteria",
    "InmateSearchResult",
    # Cook County, IL
    "CookCountySheriff",
    "search_cook_county_inmates",
    "get_cook_county_inmate",
    # Los Angeles County, CA
    "LosAngelesCountySheriff",
    "search_la_county_inmates",
    "get_la_county_inmate",
    # Harris County, TX
    "HarrisCountySheriff",
    "search_harris_county_inmates",
    "get_harris_county_inmate",
    # Maricopa County, AZ
    "MaricopaCountySheriff",
    "search_maricopa_county_inmates",
    "get_maricopa_county_inmate",
    # Miami-Dade County, FL
    "MiamiDadeCorrections",
    "search_miami_dade_inmates",
    "get_miami_dade_inmate",
]
