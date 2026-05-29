"""
County Recorder Scrapers Package

This package contains scrapers for extracting public records from county recorder
offices across the United States. County recorders maintain official records for:

- Deed Records (property transfers, quitclaims, grant deeds)
- Mortgage Records (liens, releases, assignments)
- UCC Filings (personal property liens)
- Mechanic's Liens (construction liens)
- Judgment Liens (court judgments)
- Tax Liens (IRS, state, local tax liens)
- Lis Pendens (pending lawsuits affecting property)
- Marriage Licenses
- Death Certificates (index only in most jurisdictions)
- Military Discharges (DD-214 recordings)
- Powers of Attorney
- Notary Records
- Maps and Plats

Each county scraper inherits from CountyRecorderBase and implements
county-specific extraction logic.
"""

from .base import (
    CountyRecorderBase,
    DocumentParty,
    DocumentStatus,
    DocumentType,
    LegalDescription,
    PartyRole,
    RecordedDocument,
    SearchCriteria,
    SearchResult,
)
from .clark_county_nv import (
    ClarkCountyRecorder,
    get_clark_county_document,
    search_clark_county_by_address,
    search_clark_county_by_name,
    search_clark_county_by_parcel,
)

# County-specific implementations
from .cook_county_il import CookCountyRecorder
from .dallas_county_tx import (
    DallasCountyRecorder,
    get_dallas_county_document,
    search_dallas_county_by_name,
    search_dallas_county_by_property,
)
from .harris_county_tx import HarrisCountyRecorder
from .king_county_wa import (
    KingCountyRecorder,
    get_king_county_document,
    search_king_county_by_address,
    search_king_county_by_name,
    search_king_county_by_parcel,
)
from .los_angeles_ca import LosAngelesCountyRecorder
from .maricopa_county_az import MaricopaCountyRecorder
from .miami_dade_fl import MiamiDadeCountyRecorder
from .orange_county_ca import (
    OrangeCountyRecorder,
    get_orange_county_document,
    search_orange_county_by_address,
    search_orange_county_by_apn,
    search_orange_county_by_name,
)
from .san_diego_ca import (
    SanDiegoCountyRecorder,
    get_san_diego_document,
    search_san_diego_by_address,
    search_san_diego_by_apn,
    search_san_diego_by_name,
)

__all__ = [
    # Base classes and types
    "CountyRecorderBase",
    "DocumentType",
    "DocumentStatus",
    "PartyRole",
    "RecordedDocument",
    "DocumentParty",
    "LegalDescription",
    "SearchCriteria",
    "SearchResult",
    # County implementations
    "CookCountyRecorder",
    "LosAngelesCountyRecorder",
    "HarrisCountyRecorder",
    "MaricopaCountyRecorder",
    "MiamiDadeCountyRecorder",
    # San Diego County, CA
    "SanDiegoCountyRecorder",
    "search_san_diego_by_name",
    "search_san_diego_by_apn",
    "search_san_diego_by_address",
    "get_san_diego_document",
    # Orange County, CA
    "OrangeCountyRecorder",
    "search_orange_county_by_name",
    "search_orange_county_by_apn",
    "search_orange_county_by_address",
    "get_orange_county_document",
    # Dallas County, TX
    "DallasCountyRecorder",
    "search_dallas_county_by_name",
    "search_dallas_county_by_property",
    "get_dallas_county_document",
    # King County, WA
    "KingCountyRecorder",
    "search_king_county_by_name",
    "search_king_county_by_parcel",
    "search_king_county_by_address",
    "get_king_county_document",
    # Clark County, NV
    "ClarkCountyRecorder",
    "search_clark_county_by_name",
    "search_clark_county_by_parcel",
    "search_clark_county_by_address",
    "get_clark_county_document",
]
