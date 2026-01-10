"""
Court Systems Scrapers Package

This package contains scrapers for extracting public court records from
various court systems across the United States, including:

Federal Courts:
- PACER (Public Access to Court Electronic Records)
- RECAP (Free PACER archive via CourtListener)
- Bankruptcy courts
- PTAB (Patent Trial and Appeal Board)

State Courts:
- State supreme courts
- State appellate courts
- State trial courts (various systems)

County/Local Courts:
- Civil courts (lawsuits, contract disputes, property)
- Criminal courts (charges, dispositions, sentencing)
- Family courts (divorce, custody - often limited access)
- Probate courts (estates, guardianships)
- Small claims courts
- Traffic/municipal courts

Common Court Management Systems:
- Tyler Technologies (Odyssey, Odyssey Portal)
- Thomson Reuters (C-Track)
- Journal Technologies (eCourt)
- Courthouse Technologies
- Custom state/county systems
"""

# Base classes and types
from .base import (
    CourtSystemBase,
    CourtType,
    CourtLevel,
    CaseType,
    CaseStatus,
    PartyType,
    PartyRole,
    CourtCase,
    CaseParty,
    CaseEvent,
    CaseDocument,
    CaseCharge,
    SearchCriteria,
    SearchResult,
)

# Federal courts
from .pacer_recap import (
    PacerRecapAPI,
    FEDERAL_DISTRICTS,
    CIRCUIT_COURTS,
    search_federal_courts,
    get_federal_case,
    search_federal_opinions,
)

# Tyler Odyssey systems
from .tyler_odyssey import (
    TylerOdysseyBase,
    OdysseyPortalType,
    OdysseyLocation,
    ODYSSEY_INSTALLATIONS,
    IndianaMyCase,
    MinnesotaPA,
    WashingtonCourts,
    get_odyssey_scraper,
    list_available_odyssey_installations,
    search_odyssey_party,
    get_odyssey_case,
)

# State courts
from .state_courts import (
    StateCourtBase,
    StateCourtSystemType,
    StateCourtInfo,
    STATE_COURT_SYSTEMS,
    PennsylvaniaUJS,
    WisconsinCCAP,
    MissouriCaseNet,
    get_state_court_scraper,
    list_state_court_systems,
    search_state_cases,
    get_state_case,
)

# County civil courts
from .county_civil import (
    CountyCivilCourtBase,
    CivilCaseSubtype,
    CivilJudgment,
    EvictionRecord,
    ForeclosureRecord,
    SmallClaimCase,
    CookCountyCivil,
    LosAngelesCivil,
    HarrisCountyCivil,
    get_civil_court_scraper,
    list_supported_civil_courts,
    search_civil_cases,
    search_evictions,
    search_foreclosures,
)

# County criminal courts
from .county_criminal import (
    CountyCriminalCourtBase,
    ChargeLevel,
    ChargeDisposition,
    SentenceType,
    CriminalCharge,
    CriminalDefendant,
    CriminalCaseRecord,
    CookCountyCriminal,
    HarrisCountyCriminal,
    MaricopaCountyCriminal,
    get_criminal_court_scraper,
    list_supported_criminal_courts,
    search_criminal_cases,
    get_criminal_history,
    get_criminal_case,
)

__all__ = [
    # Base classes and types
    "CourtSystemBase",
    "CourtType",
    "CourtLevel",
    "CaseType",
    "CaseStatus",
    "PartyType",
    "PartyRole",
    "CourtCase",
    "CaseParty",
    "CaseEvent",
    "CaseDocument",
    "CaseCharge",
    "SearchCriteria",
    "SearchResult",

    # Federal courts
    "PacerRecapAPI",
    "FEDERAL_DISTRICTS",
    "CIRCUIT_COURTS",
    "search_federal_courts",
    "get_federal_case",
    "search_federal_opinions",

    # Tyler Odyssey
    "TylerOdysseyBase",
    "OdysseyPortalType",
    "OdysseyLocation",
    "ODYSSEY_INSTALLATIONS",
    "IndianaMyCase",
    "MinnesotaPA",
    "WashingtonCourts",
    "get_odyssey_scraper",
    "list_available_odyssey_installations",
    "search_odyssey_party",
    "get_odyssey_case",

    # State courts
    "StateCourtBase",
    "StateCourtSystemType",
    "StateCourtInfo",
    "STATE_COURT_SYSTEMS",
    "PennsylvaniaUJS",
    "WisconsinCCAP",
    "MissouriCaseNet",
    "get_state_court_scraper",
    "list_state_court_systems",
    "search_state_cases",
    "get_state_case",

    # County civil courts
    "CountyCivilCourtBase",
    "CivilCaseSubtype",
    "CivilJudgment",
    "EvictionRecord",
    "ForeclosureRecord",
    "SmallClaimCase",
    "CookCountyCivil",
    "LosAngelesCivil",
    "HarrisCountyCivil",
    "get_civil_court_scraper",
    "list_supported_civil_courts",
    "search_civil_cases",
    "search_evictions",
    "search_foreclosures",

    # County criminal courts
    "CountyCriminalCourtBase",
    "ChargeLevel",
    "ChargeDisposition",
    "SentenceType",
    "CriminalCharge",
    "CriminalDefendant",
    "CriminalCaseRecord",
    "CookCountyCriminal",
    "HarrisCountyCriminal",
    "MaricopaCountyCriminal",
    "get_criminal_court_scraper",
    "list_supported_criminal_courts",
    "search_criminal_cases",
    "get_criminal_history",
    "get_criminal_case",
]
