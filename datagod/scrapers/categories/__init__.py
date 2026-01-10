"""
Data Category Scrapers

This module provides specialized scrapers for different data categories:
- Court Records (civil, criminal, family, probate)
- Business Filings (corporations, LLCs, partnerships, UCC)
- Professional Licenses (real estate, loan officers, attorneys)
- Federal Sources (USPTO, SEC EDGAR, FDIC, Census, BLS, FHFA)
- News API (NewsAPI.org, local news aggregation)
"""

from datagod.scrapers.categories.court_records import (
    CourtRecordsScraper,
    CaseSearch,
    PartySearch,
    CourtCase,
    CaseParty,
    CaseType,
    CaseStatus,
    PartyType,
    StateCourtScraper,
    search_court_records
)

from datagod.scrapers.categories.business_filings import (
    BusinessFilingsScraper,
    CorporateSearch,
    UCCSearch,
    BusinessEntity,
    UCCFiling,
    EntityType,
    EntityStatus,
    FilingType,
    RegisteredAgent,
    Officer,
    BusinessFiling,
    StateSOSScraper,
    search_businesses,
    search_ucc
)

from datagod.scrapers.categories.professional_licenses import (
    ProfessionalLicensesScraper,
    LicenseSearch,
    ProfessionalLicense,
    LicenseType,
    LicenseStatus,
    DisciplinaryAction,
    Employer,
    StateLicenseBoardScraper,
    NMLSScraper,
    search_professional_licenses,
    verify_professional_license
)

from datagod.scrapers.categories.federal_sources import (
    # USPTO
    USPTOScraper,
    Trademark,
    Patent,
    TrademarkSearch,
    PatentSearch,
    TrademarkStatus,
    PatentType,
    PatentStatus,
    # SEC EDGAR
    SECEdgarScraper,
    SECFiling,
    SECCompany,
    SECSearch,
    SECFilingType,
    # FDIC
    FDICScraper,
    Bank,
    BankBranch,
    BankSearch,
    BankStatus,
    # Census
    CensusScraper,
    CensusData,
    CensusSearch,
    # FHFA
    FHFAScraper,
    HousePriceIndex,
    # BLS
    BLSScraper,
    LaborStatistic,
    UnemploymentData,
    # Convenience functions
    search_trademarks,
    search_sec_filings,
    search_banks
)

from datagod.scrapers.categories.news_api import (
    # NewsAPI
    NewsAPIScraper,
    NewsArticle,
    NewsSource,
    NewsSearch,
    NewsCategory,
    NewsSentiment,
    NewsSourceType,
    # Google News
    GoogleNewsScraper,
    # Local News
    LocalNewsAggregator,
    # Press Releases
    PressReleaseAggregator,
    PressRelease,
    # Entity News
    EntityNewsFinder,
    EntityNewsSearch,
    # Convenience functions
    search_news,
    search_entity_news,
    get_local_headlines
)

__all__ = [
    # Court Records
    'CourtRecordsScraper',
    'CaseSearch',
    'PartySearch',
    'CourtCase',
    'CaseParty',
    'CaseType',
    'CaseStatus',
    'PartyType',
    'StateCourtScraper',
    'search_court_records',
    # Business Filings
    'BusinessFilingsScraper',
    'CorporateSearch',
    'UCCSearch',
    'BusinessEntity',
    'UCCFiling',
    'EntityType',
    'EntityStatus',
    'FilingType',
    'RegisteredAgent',
    'Officer',
    'BusinessFiling',
    'StateSOSScraper',
    'search_businesses',
    'search_ucc',
    # Professional Licenses
    'ProfessionalLicensesScraper',
    'LicenseSearch',
    'ProfessionalLicense',
    'LicenseType',
    'LicenseStatus',
    'DisciplinaryAction',
    'Employer',
    'StateLicenseBoardScraper',
    'NMLSScraper',
    'search_professional_licenses',
    'verify_professional_license',
    # Federal Sources - USPTO
    'USPTOScraper',
    'Trademark',
    'Patent',
    'TrademarkSearch',
    'PatentSearch',
    'TrademarkStatus',
    'PatentType',
    'PatentStatus',
    # Federal Sources - SEC
    'SECEdgarScraper',
    'SECFiling',
    'SECCompany',
    'SECSearch',
    'SECFilingType',
    # Federal Sources - FDIC
    'FDICScraper',
    'Bank',
    'BankBranch',
    'BankSearch',
    'BankStatus',
    # Federal Sources - Census
    'CensusScraper',
    'CensusData',
    'CensusSearch',
    # Federal Sources - FHFA
    'FHFAScraper',
    'HousePriceIndex',
    # Federal Sources - BLS
    'BLSScraper',
    'LaborStatistic',
    'UnemploymentData',
    # Federal Sources - Functions
    'search_trademarks',
    'search_sec_filings',
    'search_banks',
    # News API
    'NewsAPIScraper',
    'NewsArticle',
    'NewsSource',
    'NewsSearch',
    'NewsCategory',
    'NewsSentiment',
    'NewsSourceType',
    'GoogleNewsScraper',
    'LocalNewsAggregator',
    'PressReleaseAggregator',
    'PressRelease',
    'EntityNewsFinder',
    'EntityNewsSearch',
    'search_news',
    'search_entity_news',
    'get_local_headlines',
]
