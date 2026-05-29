"""
Paid Data API Integrations

Premium data providers for comprehensive property, business, and people data.
These APIs require enterprise subscriptions and credentials.

Available Providers:
- CoreLogic: Property data, valuations, foreclosures (~$5,000-50,000/year)
- ATTOM: Property data, comps, hazards, schools (~$2,000-20,000/year)
- LexisNexis: People search, business reports, court records (~$10,000+/year)

Usage Notes:
- All APIs require valid credentials from the respective providers
- LexisNexis requires FCRA compliance and permissible purpose for person searches
- Rate limits and data access vary by subscription tier
"""

# ATTOM API
from datagod.scrapers.paid.attom_api import ATTOMAPI  # Property data; Enums
from datagod.scrapers.paid.attom_api import (
    ATTOMAPIClient,
    ATTOMProperty,
    ATTOMSearch,
    HazardRisk,
    MarketTrend,
    NeighborhoodData,
    RiskLevel,
    SalesComparable,
    SchoolInfo,
    SchoolType,
    create_attom_client,
)

# CoreLogic API
from datagod.scrapers.paid.corelogic_api import (  # Property data; Enums
    AVMResult,
    CoreLogicAPI,
    CoreLogicAPIClient,
    ForeclosureRecord,
    ForeclosureStatus,
    MortgageRecord,
    PropertyCharacteristics,
    PropertySearch,
    PropertyType,
    SaleTransaction,
    TaxAssessment,
    TransactionType,
    create_corelogic_client,
)

# LexisNexis API
from datagod.scrapers.paid.lexisnexis_api import (  # Data records; Search params; Enums
    AssetRecord,
    BusinessRecord,
    BusinessSearch,
    CourtRecord,
    LexisNexisAPI,
    LexisNexisAPIClient,
    PermissiblePurpose,
    PersonRecord,
    PersonSearch,
    RecordType,
    create_lexisnexis_client,
)

__all__ = [
    # CoreLogic
    "CoreLogicAPI",
    "CoreLogicAPIClient",
    "create_corelogic_client",
    "PropertyCharacteristics",
    "TaxAssessment",
    "SaleTransaction",
    "MortgageRecord",
    "ForeclosureRecord",
    "AVMResult",
    "PropertySearch",
    "PropertyType",
    "TransactionType",
    "ForeclosureStatus",
    # ATTOM
    "ATTOMAPI",
    "ATTOMAPIClient",
    "create_attom_client",
    "ATTOMProperty",
    "SalesComparable",
    "NeighborhoodData",
    "SchoolInfo",
    "HazardRisk",
    "MarketTrend",
    "ATTOMSearch",
    "RiskLevel",
    "SchoolType",
    # LexisNexis
    "LexisNexisAPI",
    "LexisNexisAPIClient",
    "create_lexisnexis_client",
    "PersonRecord",
    "BusinessRecord",
    "CourtRecord",
    "AssetRecord",
    "PersonSearch",
    "BusinessSearch",
    "PermissiblePurpose",
    "RecordType",
]
