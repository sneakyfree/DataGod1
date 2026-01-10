"""
Business Filings Scraper Module

Provides unified access to business filings across jurisdictions:
- Corporate search (corporations, LLCs, partnerships)
- UCC filings search
- Annual reports
- Registered agent information

Supports:
- Secretary of State APIs (50 states)
- OpenCorporates API (free tier)
- State-specific scrapers for major states

Uses async/aiohttp for efficient API access.
"""

import logging
import asyncio
import aiohttp
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, quote

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
    COOPERATIVE = "cooperative"
    JOINT_VENTURE = "joint_venture"
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
    CANCELED = "canceled"
    EXPIRED = "expired"
    ADMIN_DISSOLVED = "administratively_dissolved"
    UNKNOWN = "unknown"


class FilingType(Enum):
    """Types of business filings"""
    ARTICLES_OF_INCORPORATION = "articles_of_incorporation"
    ARTICLES_OF_ORGANIZATION = "articles_of_organization"
    CERTIFICATE_OF_FORMATION = "certificate_of_formation"
    ANNUAL_REPORT = "annual_report"
    BIENNIAL_REPORT = "biennial_report"
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
    UCC_CONTINUATION = "ucc_continuation"
    FOREIGN_QUALIFICATION = "foreign_qualification"
    STATEMENT_OF_INFORMATION = "statement_of_information"
    CERTIFICATE_OF_GOOD_STANDING = "certificate_of_good_standing"
    DBA_FILING = "dba_filing"
    CONVERSION = "conversion"
    RESTATED_ARTICLES = "restated_articles"


@dataclass
class RegisteredAgent:
    """Registered agent information"""
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    is_commercial: bool = False
    agent_type: Optional[str] = None
    effective_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'is_commercial': self.is_commercial,
            'agent_type': self.agent_type,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None
        }


@dataclass
class Officer:
    """Business officer or member"""
    name: str
    title: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'title': self.title,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
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
    description: Optional[str] = None
    fee_paid: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'filing_number': self.filing_number,
            'filing_type': self.filing_type.value,
            'filing_date': self.filing_date.isoformat(),
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'document_url': self.document_url,
            'pages': self.pages,
            'description': self.description,
            'fee_paid': self.fee_paid
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
    expiration_date: Optional[date] = None
    last_annual_report: Optional[date] = None
    registered_agent: Optional[RegisteredAgent] = None
    principal_address: Optional[str] = None
    principal_city: Optional[str] = None
    principal_state: Optional[str] = None
    principal_zip: Optional[str] = None
    mailing_address: Optional[str] = None
    officers: List[Officer] = field(default_factory=list)
    filings: List[BusinessFiling] = field(default_factory=list)
    ein: Optional[str] = None
    jurisdiction: Optional[str] = None
    jurisdiction_of_formation: Optional[str] = None
    previous_names: List[str] = field(default_factory=list)
    naics_code: Optional[str] = None
    sic_code: Optional[str] = None
    purpose: Optional[str] = None
    source_url: str = ""
    source_system: str = ""
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
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'last_annual_report': self.last_annual_report.isoformat() if self.last_annual_report else None,
            'registered_agent': self.registered_agent.to_dict() if self.registered_agent else None,
            'principal_address': self.principal_address,
            'principal_city': self.principal_city,
            'principal_state': self.principal_state,
            'principal_zip': self.principal_zip,
            'mailing_address': self.mailing_address,
            'officers': [o.to_dict() for o in self.officers],
            'filings': [f.to_dict() for f in self.filings],
            'ein': self.ein,
            'jurisdiction': self.jurisdiction,
            'jurisdiction_of_formation': self.jurisdiction_of_formation,
            'previous_names': self.previous_names,
            'naics_code': self.naics_code,
            'sic_code': self.sic_code,
            'purpose': self.purpose,
            'source_url': self.source_url,
            'source_system': self.source_system,
            'fetched_at': self.fetched_at.isoformat()
        }


@dataclass
class UCCFiling:
    """Represents a UCC filing record"""
    filing_number: str
    filing_date: date
    filing_type: str
    status: str = "active"
    lapse_date: Optional[date] = None
    secured_party: Optional[str] = None
    secured_party_address: Optional[str] = None
    secured_party_city: Optional[str] = None
    secured_party_state: Optional[str] = None
    debtor_name: Optional[str] = None
    debtor_address: Optional[str] = None
    debtor_city: Optional[str] = None
    debtor_state: Optional[str] = None
    debtor_type: Optional[str] = None  # individual or organization
    collateral_description: Optional[str] = None
    state: Optional[str] = None
    filing_office: Optional[str] = None
    amendments: List[Dict[str, Any]] = field(default_factory=list)
    source_url: str = ""
    source_system: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'filing_number': self.filing_number,
            'filing_date': self.filing_date.isoformat(),
            'filing_type': self.filing_type,
            'status': self.status,
            'lapse_date': self.lapse_date.isoformat() if self.lapse_date else None,
            'secured_party': self.secured_party,
            'secured_party_address': self.secured_party_address,
            'secured_party_city': self.secured_party_city,
            'secured_party_state': self.secured_party_state,
            'debtor_name': self.debtor_name,
            'debtor_address': self.debtor_address,
            'debtor_city': self.debtor_city,
            'debtor_state': self.debtor_state,
            'debtor_type': self.debtor_type,
            'collateral_description': self.collateral_description,
            'state': self.state,
            'filing_office': self.filing_office,
            'amendments': self.amendments,
            'source_url': self.source_url,
            'source_system': self.source_system,
            'fetched_at': self.fetched_at.isoformat()
        }


# State Secretary of State configurations
STATE_SOS_CONFIGS: Dict[str, Dict[str, Any]] = {
    'CA': {
        'name': 'California Secretary of State',
        'url': 'https://bizfileonline.sos.ca.gov/',
        'search_url': 'https://bizfileonline.sos.ca.gov/search/business',
        'api_available': True,
        'has_ucc': True,
    },
    'TX': {
        'name': 'Texas Secretary of State',
        'url': 'https://www.sos.state.tx.us/',
        'search_url': 'https://mycpa.cpa.state.tx.us/coa/',
        'api_available': False,
        'has_ucc': True,
    },
    'FL': {
        'name': 'Florida Division of Corporations',
        'url': 'https://dos.myflorida.com/sunbiz/',
        'search_url': 'https://search.sunbiz.org/Inquiry/CorporationSearch/ByName',
        'api_url': 'https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResultsJSON',
        'api_available': True,
        'has_ucc': True,
    },
    'NY': {
        'name': 'New York Department of State',
        'url': 'https://www.dos.ny.gov/',
        'search_url': 'https://apps.dos.ny.gov/publicInquiry/',
        'api_available': False,
        'has_ucc': True,
    },
    'DE': {
        'name': 'Delaware Division of Corporations',
        'url': 'https://corp.delaware.gov/',
        'search_url': 'https://icis.corp.delaware.gov/ecorp/entitysearch/namesearch.aspx',
        'api_available': False,
        'has_ucc': True,
        'notes': 'Delaware is popular for incorporation - high volume',
    },
    'NV': {
        'name': 'Nevada Secretary of State',
        'url': 'https://www.nvsos.gov/',
        'search_url': 'https://esos.nv.gov/EntitySearch/OnlineEntitySearch',
        'api_url': 'https://esos.nv.gov/EntitySearch/api/search',
        'api_available': True,
        'has_ucc': True,
    },
    'IL': {
        'name': 'Illinois Secretary of State',
        'url': 'https://www.ilsos.gov/',
        'search_url': 'https://www.ilsos.gov/corporatellc/',
        'api_available': False,
        'has_ucc': True,
    },
    'PA': {
        'name': 'Pennsylvania Department of State',
        'url': 'https://www.dos.pa.gov/',
        'search_url': 'https://www.corporations.pa.gov/search/corpsearch',
        'api_available': False,
        'has_ucc': True,
    },
    'OH': {
        'name': 'Ohio Secretary of State',
        'url': 'https://www.ohiosos.gov/',
        'search_url': 'https://businesssearch.ohiosos.gov/',
        'api_available': False,
        'has_ucc': True,
    },
    'GA': {
        'name': 'Georgia Secretary of State',
        'url': 'https://sos.ga.gov/',
        'search_url': 'https://ecorp.sos.ga.gov/BusinessSearch',
        'api_url': 'https://ecorp.sos.ga.gov/BusinessSearch/api/search',
        'api_available': True,
        'has_ucc': True,
    },
    'NC': {
        'name': 'North Carolina Secretary of State',
        'url': 'https://www.sosnc.gov/',
        'search_url': 'https://www.sosnc.gov/online_services/search/by_title/_Business_Registration',
        'api_available': False,
        'has_ucc': True,
    },
    'MI': {
        'name': 'Michigan LARA',
        'url': 'https://www.michigan.gov/lara/',
        'search_url': 'https://cofs.lara.state.mi.us/SearchApi/Search/Search',
        'api_available': True,
        'has_ucc': True,
    },
    'NJ': {
        'name': 'New Jersey Division of Revenue',
        'url': 'https://www.njportal.com/DOR/BusinessFormation/',
        'search_url': 'https://www.njportal.com/DOR/BusinessNameSearch/',
        'api_available': False,
        'has_ucc': True,
    },
    'VA': {
        'name': 'Virginia State Corporation Commission',
        'url': 'https://www.scc.virginia.gov/',
        'search_url': 'https://cis.scc.virginia.gov/EntitySearch/Index',
        'api_available': False,
        'has_ucc': True,
    },
    'WA': {
        'name': 'Washington Secretary of State',
        'url': 'https://www.sos.wa.gov/',
        'search_url': 'https://ccfs.sos.wa.gov/',
        'api_url': 'https://ccfs.sos.wa.gov/api/BusinessSearch',
        'api_available': True,
        'has_ucc': True,
    },
    'AZ': {
        'name': 'Arizona Corporation Commission',
        'url': 'https://azcc.gov/',
        'search_url': 'https://ecorp.azcc.gov/EntitySearch/Index',
        'api_available': False,
        'has_ucc': True,
    },
    'MA': {
        'name': 'Massachusetts Secretary of the Commonwealth',
        'url': 'https://www.sec.state.ma.us/',
        'search_url': 'https://corp.sec.state.ma.us/CorpWeb/CorpSearch/CorpSearch.aspx',
        'api_available': False,
        'has_ucc': True,
    },
    'CO': {
        'name': 'Colorado Secretary of State',
        'url': 'https://www.sos.state.co.us/',
        'search_url': 'https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do',
        'api_url': 'https://data.colorado.gov/resource/4ykn-tg5h.json',
        'api_available': True,
        'has_ucc': True,
    },
    'MD': {
        'name': 'Maryland SDAT',
        'url': 'https://dat.maryland.gov/',
        'search_url': 'https://egov.maryland.gov/BusinessExpress/EntitySearch',
        'api_available': False,
        'has_ucc': True,
    },
    'WI': {
        'name': 'Wisconsin DFI',
        'url': 'https://www.wdfi.org/',
        'search_url': 'https://www.wdfi.org/apps/CorpSearch/',
        'api_available': False,
        'has_ucc': True,
    },
}

# Add remaining states with basic config
for state in ['AL', 'AK', 'AR', 'CT', 'HI', 'ID', 'IN', 'IA', 'KS', 'KY', 'LA',
              'ME', 'MN', 'MS', 'MO', 'MT', 'NE', 'NH', 'NM', 'ND', 'OK', 'OR',
              'RI', 'SC', 'SD', 'TN', 'UT', 'VT', 'WV', 'WY']:
    if state not in STATE_SOS_CONFIGS:
        STATE_SOS_CONFIGS[state] = {
            'name': f'{state} Secretary of State',
            'url': f'https://www.sos.{state.lower()}.gov/',
            'api_available': False,
            'has_ucc': True,
        }


class BusinessFilingsAPI:
    """
    Unified Business Filings API client.

    Provides access to business entity data through:
    - OpenCorporates API (free tier - 50 requests/day)
    - State-specific Secretary of State APIs
    - Web scraping fallback for states without APIs

    Uses async/aiohttp for efficient multi-source queries.
    """

    CATEGORY = "business_filings"
    DISPLAY_NAME = "Business Filings"

    # OpenCorporates API (free public data)
    OPENCORPORATES_BASE = "https://api.opencorporates.com/v0.4"

    # Common entity type keywords
    CORP_KEYWORDS = ['corp', 'corporation', 'inc', 'incorporated']
    LLC_KEYWORDS = ['llc', 'l.l.c.', 'limited liability company']
    LLP_KEYWORDS = ['llp', 'l.l.p.', 'limited liability partnership']
    LP_KEYWORDS = ['lp', 'l.p.', 'limited partnership']

    def __init__(self, api_key: str = None, timeout: int = 30):
        """
        Initialize business filings API client.

        Args:
            api_key: OpenCorporates API key (optional, increases rate limit)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.environ.get('OPENCORPORATES_API_KEY')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request = 0.0
        # Rate limit: 50/day without key, 500/day with key
        self._rate_limit_delay = 1.0 if self.api_key else 2.0
        self.state_configs = STATE_SOS_CONFIGS
        logger.info("BusinessFilingsAPI initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {
                'User-Agent': 'DataGod/1.0 (Business Records Research)',
                'Accept': 'application/json',
            }
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=headers
            )
        return self._session

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        import time
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request = time.time()

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # ========== OpenCorporates Search ==========

    async def search_opencorporates(
        self,
        query: str,
        jurisdiction_code: str = "",
        status: str = "",
        company_type: str = "",
        limit: int = 30
    ) -> List[BusinessEntity]:
        """
        Search companies via OpenCorporates API.

        OpenCorporates aggregates business data from official registries
        worldwide, including all US states.

        Args:
            query: Company name search query
            jurisdiction_code: State code (e.g., 'us_ca' for California)
            status: Filter by status ('active', 'inactive')
            company_type: Filter by company type
            limit: Maximum results to return

        Returns:
            List of matching BusinessEntity objects
        """
        logger.info(f"Searching OpenCorporates: {query}")

        await self._rate_limit()
        session = await self._get_session()

        # Build API URL
        params = {
            'q': query,
            'per_page': min(limit, 100),
        }

        if jurisdiction_code:
            # Convert state code to OpenCorporates format (us_ca, us_tx, etc.)
            if len(jurisdiction_code) == 2:
                jurisdiction_code = f"us_{jurisdiction_code.lower()}"
            params['jurisdiction_code'] = jurisdiction_code

        if status:
            params['status'] = status.lower()

        if company_type:
            params['company_type'] = company_type

        if self.api_key:
            params['api_token'] = self.api_key

        url = f"{self.OPENCORPORATES_BASE}/companies/search"
        entities = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', {}).get('companies', [])

                    for item in results:
                        company = item.get('company', {})
                        entity = self._parse_opencorporates_company(company)
                        if entity:
                            entities.append(entity)

                elif response.status == 401:
                    logger.warning("OpenCorporates: Invalid API key")
                elif response.status == 429:
                    logger.warning("OpenCorporates: Rate limit exceeded")
                    await asyncio.sleep(60)
                else:
                    logger.warning(f"OpenCorporates returned status {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"OpenCorporates search failed: {e}")
        except Exception as e:
            logger.error(f"OpenCorporates error: {e}")

        return entities

    def _parse_opencorporates_company(self, company: Dict[str, Any]) -> Optional[BusinessEntity]:
        """Parse OpenCorporates company data into BusinessEntity."""
        try:
            # Parse jurisdiction to state code
            jurisdiction = company.get('jurisdiction_code', '')
            state = ''
            if jurisdiction.startswith('us_'):
                state = jurisdiction[3:].upper()

            # Parse company type
            company_type = company.get('company_type', '').lower()
            entity_type = self._classify_entity_type_oc(company_type, company.get('name', ''))

            # Parse status
            status = self._parse_status(company.get('current_status', ''))

            # Parse dates
            formation_date = self._parse_date(company.get('incorporation_date'))
            dissolution_date = self._parse_date(company.get('dissolution_date'))

            # Parse registered agent
            agent_data = company.get('registered_agent', {}) or {}
            registered_agent = None
            if agent_data.get('name'):
                registered_agent = RegisteredAgent(
                    name=agent_data.get('name', ''),
                    address=agent_data.get('address'),
                )

            # Parse officers
            officers = []
            for officer_data in company.get('officers', []) or []:
                officer_info = officer_data.get('officer', {})
                if officer_info.get('name'):
                    officers.append(Officer(
                        name=officer_info.get('name', ''),
                        title=officer_info.get('position'),
                        start_date=self._parse_date(officer_info.get('start_date')),
                        end_date=self._parse_date(officer_info.get('end_date'))
                    ))

            entity = BusinessEntity(
                entity_id=company.get('company_number', ''),
                entity_name=company.get('name', ''),
                entity_type=entity_type,
                state=state,
                status=status,
                formation_date=formation_date,
                dissolution_date=dissolution_date,
                registered_agent=registered_agent,
                principal_address=company.get('registered_address_in_full'),
                officers=officers,
                jurisdiction=jurisdiction,
                previous_names=[n.get('company_name', '') for n in (company.get('previous_names') or [])],
                source_url=company.get('opencorporates_url', ''),
                source_system='OpenCorporates',
                raw_data=company,
                fetched_at=datetime.now()
            )

            return entity

        except Exception as e:
            logger.warning(f"Error parsing OpenCorporates company: {e}")
            return None

    def _classify_entity_type_oc(self, company_type: str, name: str) -> EntityType:
        """Classify entity type from OpenCorporates data."""
        type_lower = company_type.lower()
        name_lower = name.lower()

        # Check company_type field first
        if 'llc' in type_lower or 'limited liability company' in type_lower:
            return EntityType.LLC
        elif 'llp' in type_lower or 'limited liability partnership' in type_lower:
            return EntityType.LLP
        elif 'lp' in type_lower or 'limited partnership' in type_lower:
            return EntityType.LP
        elif 'nonprofit' in type_lower or 'non-profit' in type_lower:
            return EntityType.NONPROFIT
        elif 'corporation' in type_lower or 'corp' in type_lower:
            if 'foreign' in type_lower:
                return EntityType.FOREIGN_CORP
            return EntityType.CORPORATION
        elif 'trust' in type_lower:
            return EntityType.TRUST
        elif 'cooperative' in type_lower:
            return EntityType.COOPERATIVE

        # Fall back to name analysis
        return self._classify_entity_type(name)

    async def get_company_details(
        self,
        company_number: str,
        jurisdiction_code: str
    ) -> Optional[BusinessEntity]:
        """
        Get detailed company information from OpenCorporates.

        Args:
            company_number: Company registration number
            jurisdiction_code: Jurisdiction code (e.g., 'us_ca')

        Returns:
            BusinessEntity with full details
        """
        logger.info(f"Getting company details: {company_number} in {jurisdiction_code}")

        await self._rate_limit()
        session = await self._get_session()

        # Normalize jurisdiction code
        if len(jurisdiction_code) == 2:
            jurisdiction_code = f"us_{jurisdiction_code.lower()}"

        url = f"{self.OPENCORPORATES_BASE}/companies/{jurisdiction_code}/{company_number}"
        params = {}
        if self.api_key:
            params['api_token'] = self.api_key

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    company = data.get('results', {}).get('company', {})
                    return self._parse_opencorporates_company(company)
                elif response.status == 404:
                    logger.info(f"Company not found: {company_number}")
                else:
                    logger.warning(f"OpenCorporates returned status {response.status}")

        except Exception as e:
            logger.error(f"Error getting company details: {e}")

        return None

    # ========== State-Specific Search ==========

    async def search_state(
        self,
        state: str,
        query: str,
        entity_type: EntityType = None,
        status: EntityStatus = None,
        include_inactive: bool = False,
        limit: int = 50
    ) -> List[BusinessEntity]:
        """
        Search business entities in a specific state.

        Routes to state-specific API or scraper based on availability.

        Args:
            state: Two-letter state code
            query: Business name search query
            entity_type: Filter by entity type
            status: Filter by status
            include_inactive: Include inactive entities
            limit: Maximum results

        Returns:
            List of matching BusinessEntity objects
        """
        state = state.upper()
        logger.info(f"Searching {state} businesses: {query}")

        if state not in self.state_configs:
            logger.warning(f"No configuration for state {state}")
            return []

        config = self.state_configs[state]

        # Route to appropriate handler based on state capabilities
        if config.get('api_available'):
            return await self._search_state_api(state, query, entity_type, status, include_inactive, limit)
        else:
            # Fall back to OpenCorporates for this state
            return await self.search_opencorporates(
                query=query,
                jurisdiction_code=f"us_{state.lower()}",
                status='active' if not include_inactive else '',
                limit=limit
            )

    async def _search_state_api(
        self,
        state: str,
        query: str,
        entity_type: EntityType = None,
        status: EntityStatus = None,
        include_inactive: bool = False,
        limit: int = 50
    ) -> List[BusinessEntity]:
        """Search states with known API endpoints."""
        config = self.state_configs[state]

        await self._rate_limit()
        session = await self._get_session()

        entities = []

        # State-specific implementations
        if state == 'FL':
            entities = await self._search_florida_sunbiz(session, query, limit)
        elif state == 'NV':
            entities = await self._search_nevada(session, query, limit)
        elif state == 'WA':
            entities = await self._search_washington(session, query, limit)
        elif state == 'GA':
            entities = await self._search_georgia(session, query, limit)
        elif state == 'MI':
            entities = await self._search_michigan(session, query, limit)
        elif state == 'CO':
            entities = await self._search_colorado(session, query, limit)
        elif state == 'CA':
            entities = await self._search_california(session, query, limit)
        else:
            # Fallback to OpenCorporates
            entities = await self.search_opencorporates(
                query=query,
                jurisdiction_code=f"us_{state.lower()}",
                limit=limit
            )

        return entities

    async def _search_florida_sunbiz(
        self,
        session: aiohttp.ClientSession,
        query: str,
        limit: int
    ) -> List[BusinessEntity]:
        """Search Florida Sunbiz database."""
        url = "https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResultsJSON"

        params = {
            'searchNameOrder': query.upper(),
            'searchType': 'SearchByName',
        }

        entities = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get('rows', [])[:limit]:
                        # Parse Sunbiz format
                        entity = BusinessEntity(
                            entity_id=item.get('documentNumber', ''),
                            entity_name=item.get('corporationName', ''),
                            entity_type=self._classify_entity_type(item.get('corporationName', '')),
                            state='FL',
                            status=self._parse_status(item.get('status', '')),
                            formation_date=self._parse_date(item.get('filingDate')),
                            source_url=f"https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResultDetail?inquirytype=EntityName&directionType=Initial&searchNameOrder={quote(query)}&aggregateId={item.get('aggregateId', '')}",
                            source_system='Florida Sunbiz',
                            raw_data=item,
                            fetched_at=datetime.now()
                        )
                        entities.append(entity)
        except Exception as e:
            logger.error(f"Florida Sunbiz search error: {e}")

        return entities

    async def _search_nevada(
        self,
        session: aiohttp.ClientSession,
        query: str,
        limit: int
    ) -> List[BusinessEntity]:
        """Search Nevada SOS database."""
        url = "https://esos.nv.gov/EntitySearch/OnlineEntitySearch"

        # Nevada uses POST with form data
        data = {
            'EntityName': query,
            'StatusID': '0',  # All statuses
        }

        entities = []

        try:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    # Parse HTML response
                    html = await response.text()
                    entities = self._parse_nevada_results(html, limit)
        except Exception as e:
            logger.error(f"Nevada search error: {e}")

        return entities

    def _parse_nevada_results(self, html: str, limit: int) -> List[BusinessEntity]:
        """Parse Nevada SOS search results."""
        entities = []

        # Look for result rows
        row_pattern = r'<tr[^>]*class="[^"]*entity-row[^"]*"[^>]*>(.*?)</tr>'
        rows = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)

        for row in rows[:limit]:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 3:
                clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]

                # Extract entity ID from link
                id_match = re.search(r'EntityId=(\w+)', row)
                entity_id = id_match.group(1) if id_match else clean[0]

                try:
                    entity = BusinessEntity(
                        entity_id=entity_id,
                        entity_name=clean[0] if clean else '',
                        entity_type=self._classify_entity_type(clean[0] if clean else ''),
                        state='NV',
                        status=self._parse_status(clean[2] if len(clean) > 2 else ''),
                        source_url=f"https://esos.nv.gov/EntitySearch/BusinessInformation?EntityId={entity_id}",
                        source_system='Nevada SOS',
                        fetched_at=datetime.now()
                    )
                    entities.append(entity)
                except Exception:
                    pass

        return entities

    async def _search_washington(
        self,
        session: aiohttp.ClientSession,
        query: str,
        limit: int
    ) -> List[BusinessEntity]:
        """Search Washington CCFS database."""
        url = "https://ccfs.sos.wa.gov/api/BusinessSearch"

        params = {
            'businessName': query,
            'page': 1,
            'pageSize': limit,
        }

        entities = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get('businesses', []):
                        entity = BusinessEntity(
                            entity_id=item.get('ubi', ''),
                            entity_name=item.get('businessName', ''),
                            entity_type=self._classify_entity_type(item.get('businessType', '')),
                            state='WA',
                            status=self._parse_status(item.get('status', '')),
                            formation_date=self._parse_date(item.get('filingDate')),
                            principal_address=item.get('principalAddress'),
                            source_url=f"https://ccfs.sos.wa.gov/#/BusinessSearch/{item.get('ubi', '')}",
                            source_system='Washington CCFS',
                            raw_data=item,
                            fetched_at=datetime.now()
                        )
                        entities.append(entity)
        except Exception as e:
            logger.error(f"Washington search error: {e}")

        return entities

    async def _search_georgia(
        self,
        session: aiohttp.ClientSession,
        query: str,
        limit: int
    ) -> List[BusinessEntity]:
        """Search Georgia Corporations Division."""
        url = "https://ecorp.sos.ga.gov/BusinessSearch"

        params = {
            'searchType': 'business',
            'searchQuery': query,
        }

        entities = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    # Parse HTML or JSON response
                    html = await response.text()
                    entities = self._parse_georgia_results(html, limit)
        except Exception as e:
            logger.error(f"Georgia search error: {e}")

        return entities

    def _parse_georgia_results(self, html: str, limit: int) -> List[BusinessEntity]:
        """Parse Georgia Corporations Division results."""
        entities = []

        # Pattern for Georgia results
        row_pattern = r'<tr[^>]*>(.*?)</tr>'
        rows = re.findall(row_pattern, html, re.DOTALL)

        for row in rows[:limit + 1]:  # +1 to skip header
            if 'Control Number' in row:
                continue  # Skip header

            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 4:
                clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]

                try:
                    entity = BusinessEntity(
                        entity_id=clean[0] if clean else '',
                        entity_name=clean[1] if len(clean) > 1 else '',
                        entity_type=self._classify_entity_type(clean[1] if len(clean) > 1 else ''),
                        state='GA',
                        status=self._parse_status(clean[3] if len(clean) > 3 else ''),
                        formation_date=self._parse_date(clean[2] if len(clean) > 2 else ''),
                        source_url=f"https://ecorp.sos.ga.gov/BusinessSearch/BusinessInformation?controlNumber={clean[0]}",
                        source_system='Georgia SOS',
                        fetched_at=datetime.now()
                    )
                    entities.append(entity)
                except Exception:
                    pass

        return entities

    async def _search_michigan(
        self,
        session: aiohttp.ClientSession,
        query: str,
        limit: int
    ) -> List[BusinessEntity]:
        """Search Michigan LARA COFS database."""
        url = "https://cofs.lara.state.mi.us/SearchApi/Search/Search"

        params = {
            'searchType': 'EntityName',
            'searchString': query,
            'page': 1,
            'pageSize': limit,
        }

        entities = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get('results', []):
                        entity = BusinessEntity(
                            entity_id=item.get('id', ''),
                            entity_name=item.get('entityName', ''),
                            entity_type=self._classify_entity_type(item.get('entityType', '')),
                            state='MI',
                            status=self._parse_status(item.get('status', '')),
                            formation_date=self._parse_date(item.get('formationDate')),
                            source_url=f"https://cofs.lara.state.mi.us/CorpWeb/CorpSearch/CorpSummary.aspx?ID={item.get('id', '')}",
                            source_system='Michigan LARA',
                            raw_data=item,
                            fetched_at=datetime.now()
                        )
                        entities.append(entity)
        except Exception as e:
            logger.error(f"Michigan search error: {e}")

        return entities

    async def _search_colorado(
        self,
        session: aiohttp.ClientSession,
        query: str,
        limit: int
    ) -> List[BusinessEntity]:
        """Search Colorado via open data portal."""
        url = "https://data.colorado.gov/resource/4ykn-tg5h.json"

        params = {
            '$q': query,
            '$limit': limit,
            '$order': 'entityname ASC',
        }

        entities = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data:
                        entity = BusinessEntity(
                            entity_id=item.get('entityid', ''),
                            entity_name=item.get('entityname', ''),
                            entity_type=self._classify_entity_type(item.get('entitytype', '')),
                            state='CO',
                            status=self._parse_status(item.get('entitystatus', '')),
                            formation_date=self._parse_date(item.get('entityformdate')),
                            principal_address=item.get('principaladdress1'),
                            principal_city=item.get('principalcity'),
                            principal_state=item.get('principalstate'),
                            principal_zip=item.get('principalzipcode'),
                            source_url=f"https://www.sos.state.co.us/biz/BusinessEntityDetail.do?masterFileId={item.get('entityid', '')}",
                            source_system='Colorado Open Data',
                            raw_data=item,
                            fetched_at=datetime.now()
                        )
                        entities.append(entity)
        except Exception as e:
            logger.error(f"Colorado search error: {e}")

        return entities

    async def _search_california(
        self,
        session: aiohttp.ClientSession,
        query: str,
        limit: int
    ) -> List[BusinessEntity]:
        """Search California bizfile database."""
        # California doesn't have a public API, use OpenCorporates
        return await self.search_opencorporates(
            query=query,
            jurisdiction_code='us_ca',
            limit=limit
        )

    # ========== UCC Filings ==========

    async def search_ucc_filings(
        self,
        state: str,
        debtor_name: str = "",
        secured_party: str = "",
        filing_number: str = "",
        include_terminated: bool = False,
        limit: int = 50
    ) -> List[UCCFiling]:
        """
        Search UCC filings in a state.

        UCC filings are recorded at the state level (Secretary of State)
        for most collateral types.

        Args:
            state: Two-letter state code
            debtor_name: Debtor name to search
            secured_party: Secured party name
            filing_number: Specific filing number
            include_terminated: Include terminated filings
            limit: Maximum results

        Returns:
            List of matching UCCFiling objects
        """
        state = state.upper()
        logger.info(f"Searching UCC filings in {state}")

        if state not in self.state_configs:
            logger.warning(f"No UCC configuration for state {state}")
            return []

        config = self.state_configs[state]
        if not config.get('has_ucc'):
            logger.warning(f"UCC search not available for {state}")
            return []

        await self._rate_limit()
        session = await self._get_session()

        filings = []

        # Most states don't have public UCC APIs
        # Would need state-specific implementation

        return filings

    # ========== Utility Methods ==========

    def _classify_entity_type(self, name: str) -> EntityType:
        """Classify entity type based on name."""
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
        elif 'nonprofit' in name_lower or 'non-profit' in name_lower or 'foundation' in name_lower:
            return EntityType.NONPROFIT
        elif 'trust' in name_lower:
            return EntityType.TRUST
        elif 'professional' in name_lower or 'p.c.' in name_lower or 'p.a.' in name_lower:
            return EntityType.PROFESSIONAL_CORP
        elif 'benefit' in name_lower:
            return EntityType.BENEFIT_CORP
        elif 'cooperative' in name_lower or 'co-op' in name_lower:
            return EntityType.COOPERATIVE

        return EntityType.UNKNOWN

    def _parse_status(self, status_text: str) -> EntityStatus:
        """Parse entity status from text."""
        if not status_text:
            return EntityStatus.UNKNOWN

        status_lower = status_text.lower().strip()

        if any(s in status_lower for s in ['active', 'good standing', 'current', 'exists']):
            return EntityStatus.ACTIVE
        elif any(s in status_lower for s in ['inactive', 'not in good standing', 'delinquent']):
            return EntityStatus.INACTIVE
        elif 'dissolved' in status_lower:
            if 'admin' in status_lower:
                return EntityStatus.ADMIN_DISSOLVED
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
        elif 'canceled' in status_lower or 'cancelled' in status_lower:
            return EntityStatus.CANCELED
        elif 'expired' in status_lower:
            return EntityStatus.EXPIRED

        return EntityStatus.UNKNOWN

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date from various formats."""
        if not date_str:
            return None

        # Handle ISO format with time
        if 'T' in str(date_str):
            date_str = str(date_str).split('T')[0]

        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m-%d-%Y',
            '%Y%m%d',
            '%d-%b-%Y',
            '%B %d, %Y',
            '%b %d, %Y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).strip(), fmt).date()
            except ValueError:
                continue

        return None

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        states_with_api = [s for s, c in self.state_configs.items() if c.get('api_available')]
        states_with_ucc = [s for s, c in self.state_configs.items() if c.get('has_ucc')]

        return {
            'category': self.CATEGORY,
            'display_name': self.DISPLAY_NAME,
            'total_states': len(self.state_configs),
            'states_with_api': len(states_with_api),
            'states_api_list': states_with_api,
            'states_with_ucc': len(states_with_ucc),
            'opencorporates_enabled': True,
            'entity_types': [t.value for t in EntityType],
            'entity_statuses': [s.value for s in EntityStatus],
            'filing_types': [f.value for f in FilingType],
        }


# ========== Synchronous Wrappers ==========

def search_businesses(
    entity_name: str,
    states: List[str] = None,
    include_inactive: bool = False,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search business entities across states (synchronous wrapper).

    Args:
        entity_name: Business name to search
        states: List of state codes (None = use OpenCorporates national search)
        include_inactive: Include inactive entities
        limit: Maximum results

    Returns:
        List of BusinessEntity dictionaries
    """
    async def _search():
        async with BusinessFilingsAPI() as api:
            if states:
                results = []
                for state in states:
                    entities = await api.search_state(
                        state=state,
                        query=entity_name,
                        include_inactive=include_inactive,
                        limit=limit // len(states) if states else limit
                    )
                    results.extend(entities)
                return [e.to_dict() for e in results[:limit]]
            else:
                entities = await api.search_opencorporates(
                    query=entity_name,
                    limit=limit
                )
                return [e.to_dict() for e in entities]

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result()
        return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def search_state_businesses(
    state: str,
    entity_name: str,
    include_inactive: bool = False,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Search businesses in a specific state (synchronous)."""
    async def _search():
        async with BusinessFilingsAPI() as api:
            entities = await api.search_state(
                state=state,
                query=entity_name,
                include_inactive=include_inactive,
                limit=limit
            )
            return [e.to_dict() for e in entities]

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result()
        return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def get_company_details(
    company_number: str,
    state: str
) -> Optional[Dict[str, Any]]:
    """Get detailed company information (synchronous)."""
    async def _get():
        async with BusinessFilingsAPI() as api:
            entity = await api.get_company_details(
                company_number=company_number,
                jurisdiction_code=state
            )
            return entity.to_dict() if entity else None

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _get())
                return future.result()
        return loop.run_until_complete(_get())
    except RuntimeError:
        return asyncio.run(_get())


def search_ucc(
    debtor_name: str = None,
    secured_party: str = None,
    states: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Search UCC filings across states (synchronous wrapper).

    Args:
        debtor_name: Debtor name to search
        secured_party: Secured party name
        states: List of state codes

    Returns:
        List of UCCFiling dictionaries
    """
    async def _search():
        async with BusinessFilingsAPI() as api:
            results = []
            for state in (states or []):
                filings = await api.search_ucc_filings(
                    state=state,
                    debtor_name=debtor_name or '',
                    secured_party=secured_party or ''
                )
                results.extend(filings)
            return [f.to_dict() for f in results]

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result()
        return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def get_available_states() -> Dict[str, Any]:
    """Get all available state configurations."""
    api = BusinessFilingsAPI()
    return {
        'states': {
            state: {
                'name': config['name'],
                'url': config.get('url'),
                'api_available': config.get('api_available', False),
                'has_ucc': config.get('has_ucc', False),
            }
            for state, config in api.state_configs.items()
        },
        'coverage': api.get_coverage_stats(),
    }


# ========== Legacy Abstract Base Class (for backwards compatibility) ==========

class BusinessFilingsScraper(ABC):
    """
    Abstract base class for business filings scrapers.
    Maintained for backwards compatibility.
    """

    CORP_KEYWORDS = ['corp', 'corporation', 'inc', 'incorporated']
    LLC_KEYWORDS = ['llc', 'l.l.c.', 'limited liability company']
    LLP_KEYWORDS = ['llp', 'l.l.p.', 'limited liability partnership']
    LP_KEYWORDS = ['lp', 'l.p.', 'limited partnership']

    def __init__(self, state_code: str, config: Dict[str, Any] = None):
        self.state_code = state_code.upper()
        self.config = config or {}
        logger.info(f"Initialized BusinessFilingsScraper for {self.state_code}")

    @abstractmethod
    def search_entities(self, search: Any) -> List[BusinessEntity]:
        pass

    @abstractmethod
    def get_entity_details(self, entity_id: str) -> Optional[BusinessEntity]:
        pass

    @abstractmethod
    def search_ucc_filings(self, search: Any) -> List[UCCFiling]:
        pass

    @abstractmethod
    def get_ucc_details(self, filing_number: str) -> Optional[UCCFiling]:
        pass


class StateSOSScraper(BusinessFilingsScraper):
    """Legacy state SOS scraper - use BusinessFilingsAPI instead."""

    def __init__(self, state_code: str, config: Dict[str, Any] = None):
        super().__init__(state_code=state_code, config=config)
        self._api = BusinessFilingsAPI()

    def search_entities(self, search: Any) -> List[BusinessEntity]:
        return asyncio.run(self._api.search_state(
            state=self.state_code,
            query=getattr(search, 'entity_name', '') or ''
        ))

    def get_entity_details(self, entity_id: str) -> Optional[BusinessEntity]:
        return asyncio.run(self._api.get_company_details(
            company_number=entity_id,
            jurisdiction_code=self.state_code
        ))

    def search_ucc_filings(self, search: Any) -> List[UCCFiling]:
        return asyncio.run(self._api.search_ucc_filings(
            state=self.state_code,
            debtor_name=getattr(search, 'debtor_name', '') or ''
        ))

    def get_ucc_details(self, filing_number: str) -> Optional[UCCFiling]:
        return None
