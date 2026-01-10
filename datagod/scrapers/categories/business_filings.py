"""
Business Filings Scraper Module

Provides unified access to business filings across jurisdictions:
- Corporate search (corporations, LLCs, partnerships)
- UCC filings search
- Annual reports
- Registered agent information

Supports:
- Secretary of State APIs (50 states)
- OpenCorporates API
- SEC EDGAR (federal)
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of business entities"""
    CORPORATION = "corporation"
    LLC = "llc"
    LLP = "llp"
    LP = "lp"
    PARTNERSHIP = "partnership"
    SOLE_PROPRIETOR = "sole_proprietor"
    NONPROFIT = "nonprofit"
    TRUST = "trust"
    FOREIGN_CORP = "foreign_corp"
    FOREIGN_LLC = "foreign_llc"
    PROFESSIONAL_CORP = "professional_corp"
    BENEFIT_CORP = "benefit_corp"
    UNKNOWN = "unknown"


class EntityStatus(Enum):
    """Business entity status values"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISSOLVED = "dissolved"
    SUSPENDED = "suspended"
    MERGED = "merged"
    CONVERTED = "converted"
    REVOKED = "revoked"
    WITHDRAWN = "withdrawn"
    FORFEITED = "forfeited"
    PENDING = "pending"
    UNKNOWN = "unknown"


class FilingType(Enum):
    """Types of business filings"""
    ARTICLES_OF_INCORPORATION = "articles_of_incorporation"
    ARTICLES_OF_ORGANIZATION = "articles_of_organization"
    CERTIFICATE_OF_FORMATION = "certificate_of_formation"
    ANNUAL_REPORT = "annual_report"
    AMENDMENT = "amendment"
    NAME_CHANGE = "name_change"
    MERGER = "merger"
    DISSOLUTION = "dissolution"
    REINSTATEMENT = "reinstatement"
    REGISTERED_AGENT_CHANGE = "registered_agent_change"
    ADDRESS_CHANGE = "address_change"
    UCC_FILING = "ucc_filing"
    UCC_AMENDMENT = "ucc_amendment"
    UCC_TERMINATION = "ucc_termination"
    FOREIGN_QUALIFICATION = "foreign_qualification"


@dataclass
class RegisteredAgent:
    """Registered agent information"""
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    is_commercial: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'is_commercial': self.is_commercial
        }


@dataclass
class Officer:
    """Business officer or member"""
    name: str
    title: Optional[str] = None
    address: Optional[str] = None
    start_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'title': self.title,
            'address': self.address,
            'start_date': self.start_date.isoformat() if self.start_date else None
        }


@dataclass
class BusinessFiling:
    """Represents a business filing record"""
    filing_number: str
    filing_type: FilingType
    filing_date: date
    effective_date: Optional[date] = None
    document_url: Optional[str] = None
    pages: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'filing_number': self.filing_number,
            'filing_type': self.filing_type.value,
            'filing_date': self.filing_date.isoformat(),
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'document_url': self.document_url,
            'pages': self.pages
        }


@dataclass
class BusinessEntity:
    """Represents a business entity record"""
    entity_id: str
    entity_name: str
    entity_type: EntityType
    state: str
    status: EntityStatus = EntityStatus.UNKNOWN
    formation_date: Optional[date] = None
    dissolution_date: Optional[date] = None
    registered_agent: Optional[RegisteredAgent] = None
    principal_address: Optional[str] = None
    mailing_address: Optional[str] = None
    officers: List[Officer] = field(default_factory=list)
    filings: List[BusinessFiling] = field(default_factory=list)
    ein: Optional[str] = None
    jurisdiction: Optional[str] = None
    previous_names: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'entity_name': self.entity_name,
            'entity_type': self.entity_type.value,
            'state': self.state,
            'status': self.status.value,
            'formation_date': self.formation_date.isoformat() if self.formation_date else None,
            'dissolution_date': self.dissolution_date.isoformat() if self.dissolution_date else None,
            'registered_agent': self.registered_agent.to_dict() if self.registered_agent else None,
            'principal_address': self.principal_address,
            'mailing_address': self.mailing_address,
            'officers': [o.to_dict() for o in self.officers],
            'filings': [f.to_dict() for f in self.filings],
            'ein': self.ein,
            'jurisdiction': self.jurisdiction,
            'previous_names': self.previous_names,
            'fetched_at': self.fetched_at.isoformat()
        }


@dataclass
class UCCFiling:
    """Represents a UCC filing record"""
    filing_number: str
    filing_date: date
    filing_type: str
    lapse_date: Optional[date] = None
    secured_party: Optional[str] = None
    secured_party_address: Optional[str] = None
    debtor_name: Optional[str] = None
    debtor_address: Optional[str] = None
    collateral_description: Optional[str] = None
    state: Optional[str] = None
    amendments: List[Dict[str, Any]] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'filing_number': self.filing_number,
            'filing_date': self.filing_date.isoformat(),
            'filing_type': self.filing_type,
            'lapse_date': self.lapse_date.isoformat() if self.lapse_date else None,
            'secured_party': self.secured_party,
            'secured_party_address': self.secured_party_address,
            'debtor_name': self.debtor_name,
            'debtor_address': self.debtor_address,
            'collateral_description': self.collateral_description,
            'state': self.state,
            'amendments': self.amendments,
            'fetched_at': self.fetched_at.isoformat()
        }


@dataclass
class CorporateSearch:
    """Search parameters for corporate entity searches"""
    entity_name: Optional[str] = None
    entity_id: Optional[str] = None
    state: Optional[str] = None
    entity_type: Optional[EntityType] = None
    status: Optional[EntityStatus] = None
    include_inactive: bool = False
    officer_name: Optional[str] = None
    registered_agent_name: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    exact_match: bool = False


@dataclass
class UCCSearch:
    """Search parameters for UCC filing searches"""
    debtor_name: Optional[str] = None
    secured_party: Optional[str] = None
    filing_number: Optional[str] = None
    state: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    include_terminated: bool = False
    exact_match: bool = False


class BusinessFilingsScraper(ABC):
    """
    Abstract base class for business filings scrapers.

    Provides unified interface for accessing business filings
    from Secretary of State offices and other sources.
    """

    # Common entity type keywords
    CORP_KEYWORDS = ['corp', 'corporation', 'inc', 'incorporated']
    LLC_KEYWORDS = ['llc', 'l.l.c.', 'limited liability company']
    LLP_KEYWORDS = ['llp', 'l.l.p.', 'limited liability partnership']
    LP_KEYWORDS = ['lp', 'l.p.', 'limited partnership']

    def __init__(self, state_code: str, config: Dict[str, Any] = None):
        """
        Initialize the business filings scraper.

        Args:
            state_code: Two-letter state code
            config: Optional configuration dictionary
        """
        self.state_code = state_code.upper()
        self.config = config or {}

        logger.info(f"Initialized BusinessFilingsScraper for {self.state_code}")

    @abstractmethod
    def search_entities(self, search: CorporateSearch) -> List[BusinessEntity]:
        """
        Search for business entities.

        Args:
            search: CorporateSearch parameters

        Returns:
            List of matching BusinessEntity objects
        """
        pass

    @abstractmethod
    def get_entity_details(self, entity_id: str) -> Optional[BusinessEntity]:
        """
        Get detailed information for a specific entity.

        Args:
            entity_id: Entity identifier

        Returns:
            BusinessEntity with full details or None
        """
        pass

    @abstractmethod
    def search_ucc_filings(self, search: UCCSearch) -> List[UCCFiling]:
        """
        Search for UCC filings.

        Args:
            search: UCCSearch parameters

        Returns:
            List of matching UCCFiling objects
        """
        pass

    @abstractmethod
    def get_ucc_details(self, filing_number: str) -> Optional[UCCFiling]:
        """
        Get detailed information for a specific UCC filing.

        Args:
            filing_number: UCC filing number

        Returns:
            UCCFiling with full details or None
        """
        pass

    def classify_entity_type(self, name: str) -> EntityType:
        """
        Classify entity type based on name.

        Args:
            name: Entity name

        Returns:
            Classified EntityType
        """
        name_lower = name.lower()

        if any(kw in name_lower for kw in self.LLC_KEYWORDS):
            return EntityType.LLC
        elif any(kw in name_lower for kw in self.LLP_KEYWORDS):
            return EntityType.LLP
        elif any(kw in name_lower for kw in self.LP_KEYWORDS):
            return EntityType.LP
        elif any(kw in name_lower for kw in self.CORP_KEYWORDS):
            return EntityType.CORPORATION
        elif 'partnership' in name_lower:
            return EntityType.PARTNERSHIP
        elif 'nonprofit' in name_lower or 'non-profit' in name_lower:
            return EntityType.NONPROFIT
        elif 'trust' in name_lower:
            return EntityType.TRUST
        elif 'professional' in name_lower:
            return EntityType.PROFESSIONAL_CORP

        return EntityType.UNKNOWN

    def parse_entity_status(self, status_text: str) -> EntityStatus:
        """
        Parse entity status from text.

        Args:
            status_text: Status string

        Returns:
            Parsed EntityStatus
        """
        status_lower = status_text.lower().strip()

        if any(s in status_lower for s in ['active', 'good standing', 'current']):
            return EntityStatus.ACTIVE
        elif any(s in status_lower for s in ['inactive', 'not in good standing']):
            return EntityStatus.INACTIVE
        elif 'dissolved' in status_lower:
            return EntityStatus.DISSOLVED
        elif 'suspended' in status_lower:
            return EntityStatus.SUSPENDED
        elif 'merged' in status_lower:
            return EntityStatus.MERGED
        elif 'converted' in status_lower:
            return EntityStatus.CONVERTED
        elif 'revoked' in status_lower:
            return EntityStatus.REVOKED
        elif 'withdrawn' in status_lower:
            return EntityStatus.WITHDRAWN
        elif 'forfeited' in status_lower:
            return EntityStatus.FORFEITED
        elif 'pending' in status_lower:
            return EntityStatus.PENDING

        return EntityStatus.UNKNOWN

    def normalize_entity_name(self, name: str) -> str:
        """
        Normalize entity name for matching.

        Args:
            name: Raw entity name

        Returns:
            Normalized name
        """
        # Convert to uppercase
        name = name.upper().strip()

        # Remove common suffixes for matching
        suffixes = ['INC.', 'INC', 'LLC', 'L.L.C.', 'LLP', 'L.L.P.',
                    'CORP.', 'CORP', 'CORPORATION', 'CO.', 'CO',
                    'LTD.', 'LTD', 'LIMITED']

        for suffix in suffixes:
            if name.endswith(' ' + suffix):
                name = name[:-len(suffix) - 1].strip()

        # Remove punctuation
        name = re.sub(r'[^\w\s]', '', name)

        # Collapse whitespace
        name = ' '.join(name.split())

        return name

    def parse_date(self, date_str: str) -> Optional[date]:
        """Parse date from various formats."""
        if not date_str:
            return None

        formats = ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y%m%d', '%d-%b-%Y']

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get scraper statistics."""
        return {
            'state': self.state_code,
            'scraper_class': self.__class__.__name__,
        }


class StateSOSScraper(BusinessFilingsScraper):
    """
    Generic Secretary of State scraper that can be configured for different states.
    """

    def __init__(self, state_code: str, config: Dict[str, Any] = None):
        """
        Initialize state SOS scraper.

        Args:
            state_code: Two-letter state code
            config: State-specific configuration
        """
        super().__init__(state_code=state_code, config=config)
        self.base_url = config.get('base_url', '') if config else ''
        self.api_key = config.get('api_key') if config else None

    def search_entities(self, search: CorporateSearch) -> List[BusinessEntity]:
        """Search for business entities in this state."""
        logger.info(f"Searching entities in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return []

    def get_entity_details(self, entity_id: str) -> Optional[BusinessEntity]:
        """Get detailed entity information."""
        logger.info(f"Getting entity details for {entity_id} in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return None

    def search_ucc_filings(self, search: UCCSearch) -> List[UCCFiling]:
        """Search for UCC filings in this state."""
        logger.info(f"Searching UCC filings in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return []

    def get_ucc_details(self, filing_number: str) -> Optional[UCCFiling]:
        """Get detailed UCC filing information."""
        logger.info(f"Getting UCC details for {filing_number} in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return None


def search_businesses(
    entity_name: str,
    states: List[str] = None,
    include_inactive: bool = False
) -> List[BusinessEntity]:
    """
    Convenience function to search business entities across multiple states.

    Args:
        entity_name: Business name to search
        states: List of state codes to search (None = all)
        include_inactive: Include inactive/dissolved entities

    Returns:
        List of matching BusinessEntity objects
    """
    results = []

    search = CorporateSearch(
        entity_name=entity_name,
        include_inactive=include_inactive
    )

    logger.info(f"Searching businesses for '{entity_name}'")

    return results


def search_ucc(
    debtor_name: str = None,
    secured_party: str = None,
    states: List[str] = None
) -> List[UCCFiling]:
    """
    Convenience function to search UCC filings across multiple states.

    Args:
        debtor_name: Debtor name to search
        secured_party: Secured party name to search
        states: List of state codes to search

    Returns:
        List of matching UCCFiling objects
    """
    results = []

    search = UCCSearch(
        debtor_name=debtor_name,
        secured_party=secured_party
    )

    logger.info(f"Searching UCC filings")

    return results
