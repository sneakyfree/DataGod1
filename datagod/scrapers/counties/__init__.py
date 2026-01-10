"""
County-Level Scrapers for DataGod.

This module provides scrapers for county recorder offices, courts,
assessors, and other county-level public records sources.

Pilot Counties (Top 10 by Population):
1. Cook County, IL (Chicago) - 5.2M
2. Los Angeles County, CA - 10M
3. Harris County, TX (Houston) - 4.7M
4. Maricopa County, AZ (Phoenix) - 4.4M
5. San Diego County, CA - 3.3M
6. Orange County, CA - 3.2M
7. Miami-Dade County, FL - 2.7M
8. Dallas County, TX - 2.6M
9. King County, WA (Seattle) - 2.3M
10. Clark County, NV (Las Vegas) - 2.3M
"""

from .base_county_scraper import (
    BaseCountyScraper,
    CountyConfig,
    PropertyRecord,
    DeedRecord,
    MortgageRecord,
    TaxRecord,
    CourtCase,
    LienRecord,
    RecordType,
    CaseType,
    CaseStatus,
)

# Import county-specific scrapers as they're implemented
try:
    from .cook_county_il import CookCountyScraper
except ImportError:
    CookCountyScraper = None

try:
    from .los_angeles_ca import LosAngelesCountyScraper
except ImportError:
    LosAngelesCountyScraper = None

try:
    from .harris_county_tx import HarrisCountyScraper
except ImportError:
    HarrisCountyScraper = None

try:
    from .maricopa_county_az import MaricopaCountyScraper
except ImportError:
    MaricopaCountyScraper = None

try:
    from .san_diego_ca import SanDiegoCountyScraper
except ImportError:
    SanDiegoCountyScraper = None

try:
    from .orange_county_ca import OrangeCountyScraper
except ImportError:
    OrangeCountyScraper = None

try:
    from .miami_dade_fl import MiamiDadeCountyScraper
except ImportError:
    MiamiDadeCountyScraper = None

try:
    from .dallas_county_tx import DallasCountyScraper
except ImportError:
    DallasCountyScraper = None

try:
    from .king_county_wa import KingCountyScraper
except ImportError:
    KingCountyScraper = None

try:
    from .clark_county_nv import ClarkCountyScraper
except ImportError:
    ClarkCountyScraper = None


__all__ = [
    # Base classes
    "BaseCountyScraper",
    "CountyConfig",
    "PropertyRecord",
    "DeedRecord",
    "MortgageRecord",
    "TaxRecord",
    "CourtCase",
    "LienRecord",
    "RecordType",
    "CaseType",
    "CaseStatus",
    # County scrapers
    "CookCountyScraper",
    "LosAngelesCountyScraper",
    "HarrisCountyScraper",
    "MaricopaCountyScraper",
    "SanDiegoCountyScraper",
    "OrangeCountyScraper",
    "MiamiDadeCountyScraper",
    "DallasCountyScraper",
    "KingCountyScraper",
    "ClarkCountyScraper",
]
