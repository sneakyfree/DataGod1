"""
UCC (Uniform Commercial Code) Filings Scraper Module

Provides comprehensive access to UCC filings across all US states:
- UCC-1 Initial Financing Statements
- UCC-3 Amendments, Continuations, Terminations
- Debtor/Secured Party searches
- Collateral searches

UCC filings are recorded at the Secretary of State level for most collateral,
except for fixtures and timber (county recorder) and titled vehicles (DMV).

Uses async/aiohttp for efficient multi-state queries.
"""

import logging
import asyncio
import aiohttp
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, quote
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class UCCFilingType(Enum):
    """Types of UCC filings"""
    UCC1 = "UCC-1"  # Initial Financing Statement
    UCC1AP = "UCC-1AP"  # Additional Party
    UCC3 = "UCC-3"  # Amendment
    UCC3_AMENDMENT = "UCC-3 Amendment"
    UCC3_ASSIGNMENT = "UCC-3 Assignment"
    UCC3_CONTINUATION = "UCC-3 Continuation"
    UCC3_TERMINATION = "UCC-3 Termination"
    UCC3_PARTIAL_RELEASE = "UCC-3 Partial Release"
    UCC3_FULL_RELEASE = "UCC-3 Full Release"
    UCC5 = "UCC-5"  # Information Statement
    UCC11 = "UCC-11"  # Information Request
    FEDERAL_TAX_LIEN = "Federal Tax Lien"
    STATE_TAX_LIEN = "State Tax Lien"
    JUDGMENT_LIEN = "Judgment Lien"
    UNKNOWN = "Unknown"


class UCCStatus(Enum):
    """UCC filing status values"""
    ACTIVE = "active"
    TERMINATED = "terminated"
    LAPSED = "lapsed"
    AMENDED = "amended"
    CONTINUED = "continued"
    ASSIGNED = "assigned"
    UNKNOWN = "unknown"


class DebtorType(Enum):
    """Types of debtors"""
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"
    TRUST = "trust"
    ESTATE = "estate"
    TRANSMITTING_UTILITY = "transmitting_utility"
    UNKNOWN = "unknown"


class CollateralType(Enum):
    """Common collateral types"""
    ACCOUNTS = "accounts"
    INVENTORY = "inventory"
    EQUIPMENT = "equipment"
    FARM_PRODUCTS = "farm_products"
    CONSUMER_GOODS = "consumer_goods"
    GENERAL_INTANGIBLES = "general_intangibles"
    INSTRUMENTS = "instruments"
    INVESTMENT_PROPERTY = "investment_property"
    CHATTEL_PAPER = "chattel_paper"
    DEPOSIT_ACCOUNTS = "deposit_accounts"
    FIXTURES = "fixtures"
    TIMBER = "timber"
    MINERALS = "minerals"
    ALL_ASSETS = "all_assets"
    SPECIFIC_COLLATERAL = "specific_collateral"
    UNKNOWN = "unknown"


@dataclass
class UCCParty:
    """Represents a party (debtor or secured party) in a UCC filing"""
    name: str
    party_type: str = "debtor"  # "debtor" or "secured_party"
    organization_type: Optional[DebtorType] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: str = "US"
    organization_id: Optional[str] = None  # EIN, SSN last 4, etc.
    jurisdiction: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'party_type': self.party_type,
            'organization_type': self.organization_type.value if self.organization_type else None,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'country': self.country,
            'organization_id': self.organization_id,
            'jurisdiction': self.jurisdiction,
        }


@dataclass
class UCCAmendment:
    """Represents a UCC-3 amendment or related filing"""
    filing_number: str
    filing_date: date
    amendment_type: UCCFilingType
    description: Optional[str] = None
    document_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'filing_number': self.filing_number,
            'filing_date': self.filing_date.isoformat(),
            'amendment_type': self.amendment_type.value,
            'description': self.description,
            'document_url': self.document_url,
        }


@dataclass
class UCCFiling:
    """Represents a complete UCC filing record"""
    filing_number: str
    state: str
    filing_date: date
    filing_type: UCCFilingType = UCCFilingType.UCC1
    status: UCCStatus = UCCStatus.ACTIVE
    lapse_date: Optional[date] = None

    # Parties
    debtors: List[UCCParty] = field(default_factory=list)
    secured_parties: List[UCCParty] = field(default_factory=list)

    # Collateral
    collateral_description: Optional[str] = None
    collateral_types: List[CollateralType] = field(default_factory=list)

    # Filing details
    filing_office: Optional[str] = None
    file_number: Optional[str] = None
    original_filing_number: Optional[str] = None  # For amendments

    # History
    amendments: List[UCCAmendment] = field(default_factory=list)

    # Metadata
    pages: int = 0
    document_url: Optional[str] = None
    source_url: str = ""
    source_system: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'filing_number': self.filing_number,
            'state': self.state,
            'filing_date': self.filing_date.isoformat(),
            'filing_type': self.filing_type.value,
            'status': self.status.value,
            'lapse_date': self.lapse_date.isoformat() if self.lapse_date else None,
            'debtors': [d.to_dict() for d in self.debtors],
            'secured_parties': [sp.to_dict() for sp in self.secured_parties],
            'collateral_description': self.collateral_description,
            'collateral_types': [ct.value for ct in self.collateral_types],
            'filing_office': self.filing_office,
            'file_number': self.file_number,
            'original_filing_number': self.original_filing_number,
            'amendments': [a.to_dict() for a in self.amendments],
            'pages': self.pages,
            'document_url': self.document_url,
            'source_url': self.source_url,
            'source_system': self.source_system,
            'fetched_at': self.fetched_at.isoformat(),
        }


# State UCC Search Endpoints
STATE_UCC_CONFIGS: Dict[str, Dict[str, Any]] = {
    'CA': {
        'name': 'California Secretary of State - UCC',
        'search_url': 'https://bizfileonline.sos.ca.gov/search/ucc',
        'api_available': False,
        'search_type': 'web_form',
        'notes': 'Free online search, results shown on screen',
    },
    'TX': {
        'name': 'Texas Secretary of State - UCC',
        'search_url': 'https://direct.sos.state.tx.us/ucc/default.asp',
        'api_available': False,
        'search_type': 'web_form',
        'notes': 'SOSDirect system, free limited searches',
    },
    'FL': {
        'name': 'Florida Secured Transaction Registry',
        'search_url': 'https://ccfcorp.dos.state.fl.us/ucc/ucc_search.html',
        'api_url': 'https://ccfcorp.dos.state.fl.us/ucc/ucc_search_results.html',
        'api_available': True,
        'search_type': 'form_post',
    },
    'NY': {
        'name': 'New York Department of State - UCC',
        'search_url': 'https://appext20.dos.ny.gov/pls/ucc_public/web_ucc_search.main',
        'api_available': False,
        'search_type': 'web_form',
    },
    'IL': {
        'name': 'Illinois Secretary of State - UCC',
        'search_url': 'https://www.ilsos.gov/uccweb/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'PA': {
        'name': 'Pennsylvania Department of State - UCC',
        'search_url': 'https://www.corporations.pa.gov/search/uccsearch',
        'api_available': False,
        'search_type': 'web_form',
    },
    'OH': {
        'name': 'Ohio Secretary of State - UCC',
        'search_url': 'https://www5.sos.state.oh.us/ords/f?p=UCC:1',
        'api_available': False,
        'search_type': 'oracle_apex',
    },
    'GA': {
        'name': 'Georgia Superior Court Clerks - UCC',
        'search_url': 'https://www.gsccca.org/search',
        'api_available': False,
        'search_type': 'web_form',
        'notes': 'Georgia files UCC at county level',
    },
    'NC': {
        'name': 'North Carolina Secretary of State - UCC',
        'search_url': 'https://www.sosnc.gov/online_services/search/ucc',
        'api_available': False,
        'search_type': 'web_form',
    },
    'MI': {
        'name': 'Michigan Department of State - UCC',
        'search_url': 'https://cofs.lara.state.mi.us/SearchApi/Search/Search?searchType=UCC',
        'api_url': 'https://cofs.lara.state.mi.us/SearchApi/Search/Search',
        'api_available': True,
        'search_type': 'json_api',
    },
    'NJ': {
        'name': 'New Jersey Department of Treasury - UCC',
        'search_url': 'https://www.nj.gov/treasury/revenue/dcr/geninfo/ucc.shtml',
        'api_available': False,
        'search_type': 'web_form',
    },
    'VA': {
        'name': 'Virginia State Corporation Commission - UCC',
        'search_url': 'https://cis.scc.virginia.gov/EntitySearch/UCCIndex',
        'api_available': False,
        'search_type': 'web_form',
    },
    'WA': {
        'name': 'Washington Secretary of State - UCC',
        'search_url': 'https://ccfs.sos.wa.gov/',
        'api_url': 'https://ccfs.sos.wa.gov/api/UCCSearch',
        'api_available': True,
        'search_type': 'json_api',
    },
    'AZ': {
        'name': 'Arizona Secretary of State - UCC',
        'search_url': 'https://ecorp.azcc.gov/UCCSearch',
        'api_available': False,
        'search_type': 'web_form',
    },
    'MA': {
        'name': 'Massachusetts Secretary of State - UCC',
        'search_url': 'https://corp.sec.state.ma.us/ucc/ucc.asp',
        'api_available': False,
        'search_type': 'web_form',
    },
    'CO': {
        'name': 'Colorado Secretary of State - UCC',
        'search_url': 'https://www.sos.state.co.us/pubs/UCC/search.html',
        'api_available': False,
        'search_type': 'web_form',
    },
    'MD': {
        'name': 'Maryland SDAT - UCC',
        'search_url': 'https://sdatcert1.resiusa.org/UCC-Charter/index.aspx',
        'api_available': False,
        'search_type': 'web_form',
    },
    'WI': {
        'name': 'Wisconsin DFI - UCC',
        'search_url': 'https://www.wdfi.org/apps/uccsearch/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'MN': {
        'name': 'Minnesota Secretary of State - UCC',
        'search_url': 'https://mblsportal.sos.state.mn.us/UCC/UCCSearch',
        'api_available': False,
        'search_type': 'web_form',
    },
    'MO': {
        'name': 'Missouri Secretary of State - UCC',
        'search_url': 'https://bsd.sos.mo.gov/UCC/UCCSearch.aspx',
        'api_available': False,
        'search_type': 'web_form',
    },
    'IN': {
        'name': 'Indiana Secretary of State - UCC',
        'search_url': 'https://bsd.sos.in.gov/ucc/ucc-search.aspx',
        'api_available': False,
        'search_type': 'web_form',
    },
    'TN': {
        'name': 'Tennessee Secretary of State - UCC',
        'search_url': 'https://tnbear.tn.gov/UCC/UCCIndex.aspx',
        'api_available': False,
        'search_type': 'web_form',
    },
    'NV': {
        'name': 'Nevada Secretary of State - UCC',
        'search_url': 'https://esos.nv.gov/UCCSearch/UCCSearch',
        'api_url': 'https://esos.nv.gov/UCCSearch/api/search',
        'api_available': True,
        'search_type': 'json_api',
    },
    'OR': {
        'name': 'Oregon Secretary of State - UCC',
        'search_url': 'https://sos.oregon.gov/business/pages/ucc-search.aspx',
        'api_available': False,
        'search_type': 'web_form',
    },
    'KY': {
        'name': 'Kentucky Secretary of State - UCC',
        'search_url': 'https://app.sos.ky.gov/uccsearch/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'SC': {
        'name': 'South Carolina Secretary of State - UCC',
        'search_url': 'https://businessfilings.sc.gov/ucc/search',
        'api_available': False,
        'search_type': 'web_form',
    },
    'AL': {
        'name': 'Alabama Secretary of State - UCC',
        'search_url': 'https://www.sos.alabama.gov/business-services/ucc',
        'api_available': False,
        'search_type': 'web_form',
    },
    'LA': {
        'name': 'Louisiana Secretary of State - UCC',
        'search_url': 'https://coraweb.sos.la.gov/UCC/UCCSearch.aspx',
        'api_available': False,
        'search_type': 'web_form',
    },
    'OK': {
        'name': 'Oklahoma Secretary of State - UCC',
        'search_url': 'https://www.sos.ok.gov/ucc/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'CT': {
        'name': 'Connecticut Secretary of State - UCC',
        'search_url': 'https://www.concord-sots.ct.gov/CONCORD/online',
        'api_available': False,
        'search_type': 'web_form',
    },
    'IA': {
        'name': 'Iowa Secretary of State - UCC',
        'search_url': 'https://sos.iowa.gov/search/ucc/search.aspx',
        'api_available': False,
        'search_type': 'web_form',
    },
    'UT': {
        'name': 'Utah Division of Corporations - UCC',
        'search_url': 'https://secure.utah.gov/uccsearch/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'AR': {
        'name': 'Arkansas Secretary of State - UCC',
        'search_url': 'https://www.sos.arkansas.gov/corps/ucc/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'MS': {
        'name': 'Mississippi Secretary of State - UCC',
        'search_url': 'https://corp.sos.ms.gov/ucc/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'KS': {
        'name': 'Kansas Secretary of State - UCC',
        'search_url': 'https://www.kansas.gov/bess/flow/main?execution=e1s1',
        'api_available': False,
        'search_type': 'web_form',
    },
    'NE': {
        'name': 'Nebraska Secretary of State - UCC',
        'search_url': 'https://www.nebraska.gov/sos/ucc/index.cgi',
        'api_available': False,
        'search_type': 'web_form',
    },
    'NM': {
        'name': 'New Mexico Secretary of State - UCC',
        'search_url': 'https://portal.sos.state.nm.us/UCC/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'WV': {
        'name': 'West Virginia Secretary of State - UCC',
        'search_url': 'https://apps.wv.gov/SOS/ucc/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'ID': {
        'name': 'Idaho Secretary of State - UCC',
        'search_url': 'https://sosbiz.idaho.gov/search/ucc',
        'api_available': False,
        'search_type': 'web_form',
    },
    'HI': {
        'name': 'Hawaii DCCA - UCC',
        'search_url': 'https://hbe.ehawaii.gov/documents/ucc.html',
        'api_available': False,
        'search_type': 'web_form',
    },
    'ME': {
        'name': 'Maine Secretary of State - UCC',
        'search_url': 'https://www.maine.gov/sos/cec/corp/ucc.html',
        'api_available': False,
        'search_type': 'web_form',
    },
    'NH': {
        'name': 'New Hampshire Secretary of State - UCC',
        'search_url': 'https://quickstart.sos.nh.gov/online/UCC',
        'api_available': False,
        'search_type': 'web_form',
    },
    'RI': {
        'name': 'Rhode Island Secretary of State - UCC',
        'search_url': 'https://ucc.sec.state.ri.us/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'MT': {
        'name': 'Montana Secretary of State - UCC',
        'search_url': 'https://biz.sosmt.gov/search/ucc',
        'api_available': False,
        'search_type': 'web_form',
    },
    'DE': {
        'name': 'Delaware Department of State - UCC',
        'search_url': 'https://icis.corp.delaware.gov/UCCSearch/UCCSearch',
        'api_available': False,
        'search_type': 'web_form',
    },
    'SD': {
        'name': 'South Dakota Secretary of State - UCC',
        'search_url': 'https://sdsos.gov/ucc/',
        'api_available': False,
        'search_type': 'web_form',
    },
    'ND': {
        'name': 'North Dakota Secretary of State - UCC',
        'search_url': 'https://firststop.sos.nd.gov/search/ucc',
        'api_available': False,
        'search_type': 'web_form',
    },
    'AK': {
        'name': 'Alaska Division of Corporations - UCC',
        'search_url': 'https://www.commerce.alaska.gov/cbp/Main/Search.aspx',
        'api_available': False,
        'search_type': 'web_form',
    },
    'VT': {
        'name': 'Vermont Secretary of State - UCC',
        'search_url': 'https://www.vtsosonline.com/online/UCCFilingSearch',
        'api_available': False,
        'search_type': 'web_form',
    },
    'WY': {
        'name': 'Wyoming Secretary of State - UCC',
        'search_url': 'https://wyobiz.wyo.gov/business/ucc.aspx',
        'api_available': False,
        'search_type': 'web_form',
    },
    'DC': {
        'name': 'District of Columbia - UCC',
        'search_url': 'https://corponline.dcra.dc.gov/UCCSearch.aspx',
        'api_available': False,
        'search_type': 'web_form',
    },
}


class UCCFilingsAPI:
    """
    Unified UCC Filings API client.

    Provides access to UCC filing data across all 50 states through:
    - State-specific APIs where available
    - Web scraping for states without APIs
    - Standardized data model for all results

    Uses async/aiohttp for efficient multi-state queries.
    """

    CATEGORY = "ucc_filings"
    DISPLAY_NAME = "UCC Filings"

    def __init__(self, timeout: int = 30):
        """
        Initialize UCC filings API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request = 0.0
        self._rate_limit_delay = 1.5  # Be respectful to state servers
        self.state_configs = STATE_UCC_CONFIGS
        logger.info("UCCFilingsAPI initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {
                'User-Agent': 'DataGod/1.0 (UCC Records Research)',
                'Accept': 'text/html,application/xhtml+xml,application/json',
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

    # ========== Main Search Methods ==========

    async def search_by_debtor(
        self,
        state: str,
        debtor_name: str,
        debtor_type: DebtorType = None,
        include_terminated: bool = False,
        limit: int = 50
    ) -> List[UCCFiling]:
        """
        Search UCC filings by debtor name.

        Args:
            state: Two-letter state code
            debtor_name: Debtor name to search
            debtor_type: Filter by debtor type (individual/organization)
            include_terminated: Include terminated/lapsed filings
            limit: Maximum results

        Returns:
            List of matching UCCFiling objects
        """
        state = state.upper()
        logger.info(f"Searching UCC filings in {state} for debtor: {debtor_name}")

        if state not in self.state_configs:
            logger.warning(f"No UCC configuration for state {state}")
            return []

        config = self.state_configs[state]
        await self._rate_limit()
        session = await self._get_session()

        # Route to appropriate handler
        if config.get('api_available'):
            return await self._search_api(
                state, session, debtor_name=debtor_name,
                debtor_type=debtor_type, include_terminated=include_terminated, limit=limit
            )
        else:
            return await self._search_web_form(
                state, session, config, debtor_name=debtor_name,
                include_terminated=include_terminated, limit=limit
            )

    async def search_by_secured_party(
        self,
        state: str,
        secured_party_name: str,
        include_terminated: bool = False,
        limit: int = 50
    ) -> List[UCCFiling]:
        """
        Search UCC filings by secured party name.

        Args:
            state: Two-letter state code
            secured_party_name: Secured party name to search
            include_terminated: Include terminated/lapsed filings
            limit: Maximum results

        Returns:
            List of matching UCCFiling objects
        """
        state = state.upper()
        logger.info(f"Searching UCC filings in {state} for secured party: {secured_party_name}")

        if state not in self.state_configs:
            logger.warning(f"No UCC configuration for state {state}")
            return []

        config = self.state_configs[state]
        await self._rate_limit()
        session = await self._get_session()

        if config.get('api_available'):
            return await self._search_api(
                state, session, secured_party=secured_party_name,
                include_terminated=include_terminated, limit=limit
            )
        else:
            return await self._search_web_form(
                state, session, config, secured_party=secured_party_name,
                include_terminated=include_terminated, limit=limit
            )

    async def search_by_filing_number(
        self,
        state: str,
        filing_number: str
    ) -> Optional[UCCFiling]:
        """
        Get UCC filing by filing number.

        Args:
            state: Two-letter state code
            filing_number: UCC filing number

        Returns:
            UCCFiling object or None
        """
        state = state.upper()
        logger.info(f"Looking up UCC filing {filing_number} in {state}")

        if state not in self.state_configs:
            logger.warning(f"No UCC configuration for state {state}")
            return None

        config = self.state_configs[state]
        await self._rate_limit()
        session = await self._get_session()

        filings = await self._search_api(
            state, session, filing_number=filing_number, limit=1
        ) if config.get('api_available') else await self._search_web_form(
            state, session, config, filing_number=filing_number, limit=1
        )

        return filings[0] if filings else None

    async def search_multi_state(
        self,
        states: List[str],
        debtor_name: str = None,
        secured_party: str = None,
        include_terminated: bool = False,
        limit_per_state: int = 25
    ) -> List[UCCFiling]:
        """
        Search UCC filings across multiple states.

        Args:
            states: List of state codes
            debtor_name: Debtor name to search
            secured_party: Secured party name
            include_terminated: Include terminated filings
            limit_per_state: Max results per state

        Returns:
            Combined list of UCCFiling objects
        """
        logger.info(f"Searching UCC filings across {len(states)} states")

        tasks = []
        for state in states:
            if debtor_name:
                tasks.append(self.search_by_debtor(
                    state, debtor_name, include_terminated=include_terminated,
                    limit=limit_per_state
                ))
            elif secured_party:
                tasks.append(self.search_by_secured_party(
                    state, secured_party, include_terminated=include_terminated,
                    limit=limit_per_state
                ))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_filings = []
        for result in results:
            if isinstance(result, list):
                all_filings.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"State search failed: {result}")

        return all_filings

    # ========== State-Specific API Handlers ==========

    async def _search_api(
        self,
        state: str,
        session: aiohttp.ClientSession,
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        debtor_type: DebtorType = None,
        include_terminated: bool = False,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Route to state-specific API handler."""

        if state == 'FL':
            return await self._search_florida(session, debtor_name, secured_party, filing_number, limit)
        elif state == 'MI':
            return await self._search_michigan(session, debtor_name, secured_party, filing_number, limit)
        elif state == 'WA':
            return await self._search_washington(session, debtor_name, secured_party, filing_number, limit)
        elif state == 'NV':
            return await self._search_nevada(session, debtor_name, secured_party, filing_number, limit)
        else:
            # Fallback to web form
            config = self.state_configs.get(state, {})
            return await self._search_web_form(state, session, config, debtor_name, secured_party, filing_number, include_terminated, limit)

    async def _search_florida(
        self,
        session: aiohttp.ClientSession,
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Search Florida UCC database."""
        url = "https://ccfcorp.dos.state.fl.us/ucc/ucc_search_results.html"

        data = {}
        if debtor_name:
            data['DebtorName'] = debtor_name
            data['SearchType'] = 'DEBTOR'
        elif secured_party:
            data['SecuredPartyName'] = secured_party
            data['SearchType'] = 'SECURED'
        elif filing_number:
            data['FileNumber'] = filing_number
            data['SearchType'] = 'FILENUMBER'
        else:
            return []

        filings = []

        try:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    html = await response.text()
                    filings = self._parse_florida_results(html, limit)
        except Exception as e:
            logger.error(f"Florida UCC search error: {e}")

        return filings

    def _parse_florida_results(self, html: str, limit: int) -> List[UCCFiling]:
        """Parse Florida UCC search results."""
        filings = []
        soup = BeautifulSoup(html, 'html.parser')

        # Find result table rows
        rows = soup.select('table.results tr')

        for row in rows[1:limit + 1]:  # Skip header
            cells = row.find_all('td')
            if len(cells) >= 4:
                try:
                    filing_number = cells[0].get_text(strip=True)
                    filing_date = self._parse_date(cells[1].get_text(strip=True))
                    debtor_name = cells[2].get_text(strip=True)
                    status_text = cells[3].get_text(strip=True) if len(cells) > 3 else ''

                    if filing_date:
                        filing = UCCFiling(
                            filing_number=filing_number,
                            state='FL',
                            filing_date=filing_date,
                            filing_type=UCCFilingType.UCC1,
                            status=self._parse_status(status_text),
                            debtors=[UCCParty(name=debtor_name, party_type='debtor')],
                            source_url=f"https://ccfcorp.dos.state.fl.us/ucc/ucc_detail.html?FileNumber={filing_number}",
                            source_system='Florida UCC Registry',
                            fetched_at=datetime.now()
                        )
                        filings.append(filing)
                except Exception as e:
                    logger.warning(f"Error parsing Florida row: {e}")

        return filings

    async def _search_michigan(
        self,
        session: aiohttp.ClientSession,
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Search Michigan UCC database."""
        url = "https://cofs.lara.state.mi.us/SearchApi/Search/Search"

        params = {
            'searchType': 'UCC',
            'page': 1,
            'pageSize': limit,
        }

        if debtor_name:
            params['searchString'] = debtor_name
            params['partyType'] = 'Debtor'
        elif secured_party:
            params['searchString'] = secured_party
            params['partyType'] = 'SecuredParty'
        elif filing_number:
            params['searchString'] = filing_number
            params['searchBy'] = 'FileNumber'
        else:
            return []

        filings = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get('results', []):
                        filing = self._parse_michigan_item(item)
                        if filing:
                            filings.append(filing)
        except Exception as e:
            logger.error(f"Michigan UCC search error: {e}")

        return filings

    def _parse_michigan_item(self, item: Dict[str, Any]) -> Optional[UCCFiling]:
        """Parse Michigan UCC result item."""
        try:
            filing_date = self._parse_date(item.get('filingDate'))
            if not filing_date:
                return None

            filing = UCCFiling(
                filing_number=item.get('fileNumber', ''),
                state='MI',
                filing_date=filing_date,
                filing_type=self._classify_filing_type(item.get('filingType', '')),
                status=self._parse_status(item.get('status', '')),
                lapse_date=self._parse_date(item.get('lapseDate')),
                collateral_description=item.get('collateralDescription'),
                source_url=f"https://cofs.lara.state.mi.us/CorpWeb/CorpSearch/UCCSummary.aspx?ID={item.get('fileNumber', '')}",
                source_system='Michigan LARA UCC',
                raw_data=item,
                fetched_at=datetime.now()
            )

            # Add debtors
            for debtor in item.get('debtors', []):
                filing.debtors.append(UCCParty(
                    name=debtor.get('name', ''),
                    party_type='debtor',
                    address=debtor.get('address'),
                    city=debtor.get('city'),
                    state=debtor.get('state'),
                    zip_code=debtor.get('zip'),
                ))

            # Add secured parties
            for sp in item.get('securedParties', []):
                filing.secured_parties.append(UCCParty(
                    name=sp.get('name', ''),
                    party_type='secured_party',
                    address=sp.get('address'),
                    city=sp.get('city'),
                    state=sp.get('state'),
                    zip_code=sp.get('zip'),
                ))

            return filing
        except Exception as e:
            logger.warning(f"Error parsing Michigan item: {e}")
            return None

    async def _search_washington(
        self,
        session: aiohttp.ClientSession,
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Search Washington UCC database."""
        url = "https://ccfs.sos.wa.gov/api/UCCSearch"

        params = {
            'page': 1,
            'pageSize': limit,
        }

        if debtor_name:
            params['debtorName'] = debtor_name
        elif secured_party:
            params['securedPartyName'] = secured_party
        elif filing_number:
            params['fileNumber'] = filing_number
        else:
            return []

        filings = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get('filings', []):
                        filing_date = self._parse_date(item.get('filingDate'))
                        if filing_date:
                            filing = UCCFiling(
                                filing_number=item.get('fileNumber', ''),
                                state='WA',
                                filing_date=filing_date,
                                filing_type=self._classify_filing_type(item.get('filingType', '')),
                                status=self._parse_status(item.get('status', '')),
                                lapse_date=self._parse_date(item.get('lapseDate')),
                                source_url=f"https://ccfs.sos.wa.gov/#/UCC/{item.get('fileNumber', '')}",
                                source_system='Washington CCFS UCC',
                                raw_data=item,
                                fetched_at=datetime.now()
                            )
                            filings.append(filing)
        except Exception as e:
            logger.error(f"Washington UCC search error: {e}")

        return filings

    async def _search_nevada(
        self,
        session: aiohttp.ClientSession,
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Search Nevada UCC database."""
        url = "https://esos.nv.gov/UCCSearch/api/search"

        params = {}
        if debtor_name:
            params['DebtorName'] = debtor_name
        elif secured_party:
            params['SecuredPartyName'] = secured_party
        elif filing_number:
            params['FileNumber'] = filing_number
        else:
            return []

        filings = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get('results', [])[:limit]:
                        filing_date = self._parse_date(item.get('filingDate'))
                        if filing_date:
                            filing = UCCFiling(
                                filing_number=item.get('fileNumber', ''),
                                state='NV',
                                filing_date=filing_date,
                                status=self._parse_status(item.get('status', '')),
                                source_url=f"https://esos.nv.gov/UCCSearch/UCCDetail?FileNumber={item.get('fileNumber', '')}",
                                source_system='Nevada SOS UCC',
                                raw_data=item,
                                fetched_at=datetime.now()
                            )
                            filings.append(filing)
        except Exception as e:
            logger.error(f"Nevada UCC search error: {e}")

        return filings

    # ========== Web Form Scrapers ==========

    async def _search_web_form(
        self,
        state: str,
        session: aiohttp.ClientSession,
        config: Dict[str, Any],
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        include_terminated: bool = False,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Generic web form scraper for states without APIs."""
        search_url = config.get('search_url')
        if not search_url:
            logger.warning(f"No search URL for state {state}")
            return []

        filings = []

        # State-specific form handlers
        if state == 'CA':
            filings = await self._search_california_web(session, debtor_name, secured_party, filing_number, limit)
        elif state == 'TX':
            filings = await self._search_texas_web(session, debtor_name, secured_party, filing_number, limit)
        elif state == 'NY':
            filings = await self._search_newyork_web(session, debtor_name, secured_party, filing_number, limit)
        elif state == 'IL':
            filings = await self._search_illinois_web(session, debtor_name, secured_party, filing_number, limit)
        else:
            # Generic form handler
            filings = await self._search_generic_web(state, session, config, debtor_name, secured_party, filing_number, limit)

        return filings

    async def _search_california_web(
        self,
        session: aiohttp.ClientSession,
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Search California UCC via web form."""
        url = "https://bizfileonline.sos.ca.gov/api/Records/UCCSearch"

        data = {}
        if debtor_name:
            data['debtorName'] = debtor_name
        elif secured_party:
            data['securedPartyName'] = secured_party
        elif filing_number:
            data['fileNumber'] = filing_number
        else:
            return []

        filings = []

        try:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    for item in result.get('results', [])[:limit]:
                        filing_date = self._parse_date(item.get('filingDate'))
                        if filing_date:
                            filing = UCCFiling(
                                filing_number=item.get('fileNumber', ''),
                                state='CA',
                                filing_date=filing_date,
                                status=self._parse_status(item.get('status', '')),
                                source_url=f"https://bizfileonline.sos.ca.gov/search/ucc/detail/{item.get('fileNumber', '')}",
                                source_system='California SOS UCC',
                                raw_data=item,
                                fetched_at=datetime.now()
                            )

                            # Add parties
                            for d in item.get('debtors', []):
                                filing.debtors.append(UCCParty(
                                    name=d.get('name', ''),
                                    party_type='debtor',
                                    address=d.get('address'),
                                    city=d.get('city'),
                                    state=d.get('state'),
                                    zip_code=d.get('zipCode'),
                                ))

                            filings.append(filing)
        except Exception as e:
            logger.error(f"California UCC search error: {e}")

        return filings

    async def _search_texas_web(
        self,
        session: aiohttp.ClientSession,
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Search Texas UCC via SOSDirect."""
        url = "https://direct.sos.state.tx.us/ucc/ucc-search"

        data = {
            'action': 'search',
        }
        if debtor_name:
            data['debtor_name'] = debtor_name
        elif secured_party:
            data['sp_name'] = secured_party
        elif filing_number:
            data['file_number'] = filing_number
        else:
            return []

        filings = []

        try:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    html = await response.text()
                    filings = self._parse_texas_results(html, limit)
        except Exception as e:
            logger.error(f"Texas UCC search error: {e}")

        return filings

    def _parse_texas_results(self, html: str, limit: int) -> List[UCCFiling]:
        """Parse Texas UCC search results."""
        filings = []
        soup = BeautifulSoup(html, 'html.parser')

        # Find result rows
        rows = soup.select('table tr.result-row, table.results tr')

        for row in rows[:limit]:
            cells = row.find_all('td')
            if len(cells) >= 3:
                try:
                    filing_number = cells[0].get_text(strip=True)
                    filing_date = self._parse_date(cells[1].get_text(strip=True))
                    debtor_name = cells[2].get_text(strip=True) if len(cells) > 2 else ''

                    if filing_date:
                        filing = UCCFiling(
                            filing_number=filing_number,
                            state='TX',
                            filing_date=filing_date,
                            debtors=[UCCParty(name=debtor_name, party_type='debtor')] if debtor_name else [],
                            source_url=f"https://direct.sos.state.tx.us/ucc/ucc-detail?file={filing_number}",
                            source_system='Texas SOSDirect UCC',
                            fetched_at=datetime.now()
                        )
                        filings.append(filing)
                except Exception as e:
                    logger.warning(f"Error parsing Texas row: {e}")

        return filings

    async def _search_newyork_web(
        self,
        session: aiohttp.ClientSession,
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Search New York UCC via web form."""
        url = "https://appext20.dos.ny.gov/pls/ucc_public/web_ucc_search.results"

        data = {}
        if debtor_name:
            data['p_debtor_name'] = debtor_name
            data['p_search_type'] = 'D'
        elif secured_party:
            data['p_sp_name'] = secured_party
            data['p_search_type'] = 'S'
        elif filing_number:
            data['p_file_number'] = filing_number
            data['p_search_type'] = 'F'
        else:
            return []

        filings = []

        try:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    html = await response.text()
                    filings = self._parse_newyork_results(html, limit)
        except Exception as e:
            logger.error(f"New York UCC search error: {e}")

        return filings

    def _parse_newyork_results(self, html: str, limit: int) -> List[UCCFiling]:
        """Parse New York UCC search results."""
        filings = []
        soup = BeautifulSoup(html, 'html.parser')

        # Find result table
        table = soup.find('table', class_='ucc-results') or soup.find('table')
        if not table:
            return filings

        rows = table.find_all('tr')[1:limit + 1]  # Skip header

        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                try:
                    filing_number = cells[0].get_text(strip=True)
                    filing_date = self._parse_date(cells[1].get_text(strip=True))
                    status_text = cells[2].get_text(strip=True) if len(cells) > 2 else ''

                    if filing_date:
                        filing = UCCFiling(
                            filing_number=filing_number,
                            state='NY',
                            filing_date=filing_date,
                            status=self._parse_status(status_text),
                            source_url=f"https://appext20.dos.ny.gov/pls/ucc_public/web_ucc_search.detail?p_file_number={filing_number}",
                            source_system='New York DOS UCC',
                            fetched_at=datetime.now()
                        )
                        filings.append(filing)
                except Exception as e:
                    logger.warning(f"Error parsing NY row: {e}")

        return filings

    async def _search_illinois_web(
        self,
        session: aiohttp.ClientSession,
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Search Illinois UCC via web form."""
        url = "https://www.ilsos.gov/uccweb/ucc_search.html"

        data = {}
        if debtor_name:
            data['debtor_name'] = debtor_name
        elif secured_party:
            data['sp_name'] = secured_party
        elif filing_number:
            data['file_number'] = filing_number
        else:
            return []

        filings = []

        try:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    html = await response.text()
                    filings = self._parse_illinois_results(html, limit)
        except Exception as e:
            logger.error(f"Illinois UCC search error: {e}")

        return filings

    def _parse_illinois_results(self, html: str, limit: int) -> List[UCCFiling]:
        """Parse Illinois UCC search results."""
        filings = []
        soup = BeautifulSoup(html, 'html.parser')

        rows = soup.select('table tr')

        for row in rows[1:limit + 1]:
            cells = row.find_all('td')
            if len(cells) >= 3:
                try:
                    filing_number = cells[0].get_text(strip=True)
                    filing_date = self._parse_date(cells[1].get_text(strip=True))

                    if filing_date:
                        filing = UCCFiling(
                            filing_number=filing_number,
                            state='IL',
                            filing_date=filing_date,
                            source_url=f"https://www.ilsos.gov/uccweb/ucc_detail.html?file={filing_number}",
                            source_system='Illinois SOS UCC',
                            fetched_at=datetime.now()
                        )
                        filings.append(filing)
                except Exception as e:
                    logger.warning(f"Error parsing Illinois row: {e}")

        return filings

    async def _search_generic_web(
        self,
        state: str,
        session: aiohttp.ClientSession,
        config: Dict[str, Any],
        debtor_name: str = None,
        secured_party: str = None,
        filing_number: str = None,
        limit: int = 50
    ) -> List[UCCFiling]:
        """Generic web form handler for states without specific implementation."""
        search_url = config.get('search_url')
        if not search_url:
            return []

        filings = []

        # Try common form parameter patterns
        data_patterns = [
            {'debtor_name': debtor_name, 'sp_name': secured_party, 'file_number': filing_number},
            {'DebtorName': debtor_name, 'SecuredParty': secured_party, 'FileNumber': filing_number},
            {'txtDebtor': debtor_name, 'txtSecuredParty': secured_party, 'txtFileNum': filing_number},
        ]

        for params in data_patterns:
            # Filter out None values
            data = {k: v for k, v in params.items() if v}
            if not data:
                continue

            try:
                async with session.post(search_url, data=data) as response:
                    if response.status == 200:
                        html = await response.text()
                        filings = self._parse_generic_results(state, html, search_url, limit)
                        if filings:
                            break
            except Exception as e:
                logger.debug(f"Generic search attempt failed for {state}: {e}")
                continue

        return filings

    def _parse_generic_results(self, state: str, html: str, base_url: str, limit: int) -> List[UCCFiling]:
        """Parse generic UCC search results HTML."""
        filings = []
        soup = BeautifulSoup(html, 'html.parser')

        # Try to find any table with results
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:limit + 1]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    try:
                        # Look for filing number pattern
                        text_content = [c.get_text(strip=True) for c in cells]

                        # Try to identify filing number and date
                        filing_number = None
                        filing_date = None

                        for text in text_content:
                            # Common UCC filing number patterns
                            if re.match(r'^[\dA-Z]{8,20}$', text) or re.match(r'^\d{4}-\d+', text):
                                filing_number = text
                            # Try to parse as date
                            parsed_date = self._parse_date(text)
                            if parsed_date:
                                filing_date = parsed_date

                        if filing_number and filing_date:
                            filing = UCCFiling(
                                filing_number=filing_number,
                                state=state,
                                filing_date=filing_date,
                                source_url=base_url,
                                source_system=f'{state} SOS UCC',
                                fetched_at=datetime.now()
                            )
                            filings.append(filing)
                    except Exception:
                        continue

        return filings

    # ========== Utility Methods ==========

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

    def _parse_status(self, status_text: str) -> UCCStatus:
        """Parse UCC status from text."""
        if not status_text:
            return UCCStatus.UNKNOWN

        status_lower = status_text.lower().strip()

        if any(s in status_lower for s in ['active', 'current', 'filed']):
            return UCCStatus.ACTIVE
        elif any(s in status_lower for s in ['terminated', 'released']):
            return UCCStatus.TERMINATED
        elif any(s in status_lower for s in ['lapsed', 'expired']):
            return UCCStatus.LAPSED
        elif 'amended' in status_lower:
            return UCCStatus.AMENDED
        elif 'continued' in status_lower:
            return UCCStatus.CONTINUED
        elif 'assigned' in status_lower:
            return UCCStatus.ASSIGNED

        return UCCStatus.UNKNOWN

    def _classify_filing_type(self, type_text: str) -> UCCFilingType:
        """Classify UCC filing type from text."""
        if not type_text:
            return UCCFilingType.UCC1

        type_lower = type_text.lower()

        if 'continuation' in type_lower:
            return UCCFilingType.UCC3_CONTINUATION
        elif 'termination' in type_lower:
            return UCCFilingType.UCC3_TERMINATION
        elif 'assignment' in type_lower:
            return UCCFilingType.UCC3_ASSIGNMENT
        elif 'amendment' in type_lower:
            return UCCFilingType.UCC3_AMENDMENT
        elif 'partial release' in type_lower:
            return UCCFilingType.UCC3_PARTIAL_RELEASE
        elif 'release' in type_lower:
            return UCCFilingType.UCC3_FULL_RELEASE
        elif 'ucc-3' in type_lower or 'ucc3' in type_lower:
            return UCCFilingType.UCC3
        elif 'federal tax lien' in type_lower:
            return UCCFilingType.FEDERAL_TAX_LIEN
        elif 'state tax lien' in type_lower:
            return UCCFilingType.STATE_TAX_LIEN
        elif 'judgment' in type_lower:
            return UCCFilingType.JUDGMENT_LIEN
        elif 'additional party' in type_lower or 'ucc-1ap' in type_lower:
            return UCCFilingType.UCC1AP

        return UCCFilingType.UCC1

    def _classify_collateral(self, description: str) -> List[CollateralType]:
        """Classify collateral types from description."""
        if not description:
            return [CollateralType.UNKNOWN]

        desc_lower = description.lower()
        types = []

        if 'all assets' in desc_lower or 'all personal property' in desc_lower:
            types.append(CollateralType.ALL_ASSETS)
        if 'account' in desc_lower:
            types.append(CollateralType.ACCOUNTS)
        if 'inventory' in desc_lower:
            types.append(CollateralType.INVENTORY)
        if 'equipment' in desc_lower:
            types.append(CollateralType.EQUIPMENT)
        if 'farm product' in desc_lower:
            types.append(CollateralType.FARM_PRODUCTS)
        if 'consumer good' in desc_lower:
            types.append(CollateralType.CONSUMER_GOODS)
        if 'general intangible' in desc_lower:
            types.append(CollateralType.GENERAL_INTANGIBLES)
        if 'instrument' in desc_lower:
            types.append(CollateralType.INSTRUMENTS)
        if 'investment' in desc_lower:
            types.append(CollateralType.INVESTMENT_PROPERTY)
        if 'chattel paper' in desc_lower:
            types.append(CollateralType.CHATTEL_PAPER)
        if 'deposit account' in desc_lower:
            types.append(CollateralType.DEPOSIT_ACCOUNTS)
        if 'fixture' in desc_lower:
            types.append(CollateralType.FIXTURES)
        if 'timber' in desc_lower:
            types.append(CollateralType.TIMBER)
        if 'mineral' in desc_lower or 'oil' in desc_lower or 'gas' in desc_lower:
            types.append(CollateralType.MINERALS)

        if not types:
            types.append(CollateralType.SPECIFIC_COLLATERAL)

        return types

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        states_with_api = [s for s, c in self.state_configs.items() if c.get('api_available')]

        return {
            'category': self.CATEGORY,
            'display_name': self.DISPLAY_NAME,
            'total_states': len(self.state_configs),
            'states_with_api': len(states_with_api),
            'states_api_list': states_with_api,
            'filing_types': [t.value for t in UCCFilingType],
            'status_types': [s.value for s in UCCStatus],
            'collateral_types': [c.value for c in CollateralType],
        }


# ========== Synchronous Wrappers ==========

def search_ucc_by_debtor(
    debtor_name: str,
    states: List[str] = None,
    include_terminated: bool = False,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search UCC filings by debtor name (synchronous wrapper).

    Args:
        debtor_name: Debtor name to search
        states: List of state codes (None = search all states)
        include_terminated: Include terminated filings
        limit: Maximum results

    Returns:
        List of UCCFiling dictionaries
    """
    async def _search():
        async with UCCFilingsAPI() as api:
            if states:
                return await api.search_multi_state(
                    states=states,
                    debtor_name=debtor_name,
                    include_terminated=include_terminated,
                    limit_per_state=limit // len(states) if states else limit
                )
            else:
                # Search major states
                major_states = ['CA', 'TX', 'FL', 'NY', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI']
                return await api.search_multi_state(
                    states=major_states,
                    debtor_name=debtor_name,
                    include_terminated=include_terminated,
                    limit_per_state=limit // 10
                )

    try:
        results = asyncio.run(_search())
        return [f.to_dict() for f in results]
    except RuntimeError:
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(_search())
        return [f.to_dict() for f in results]


def search_ucc_by_secured_party(
    secured_party_name: str,
    states: List[str] = None,
    include_terminated: bool = False,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search UCC filings by secured party name (synchronous wrapper).

    Args:
        secured_party_name: Secured party name to search
        states: List of state codes
        include_terminated: Include terminated filings
        limit: Maximum results

    Returns:
        List of UCCFiling dictionaries
    """
    async def _search():
        async with UCCFilingsAPI() as api:
            if states:
                return await api.search_multi_state(
                    states=states,
                    secured_party=secured_party_name,
                    include_terminated=include_terminated,
                    limit_per_state=limit // len(states) if states else limit
                )
            else:
                major_states = ['CA', 'TX', 'FL', 'NY', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI']
                return await api.search_multi_state(
                    states=major_states,
                    secured_party=secured_party_name,
                    include_terminated=include_terminated,
                    limit_per_state=limit // 10
                )

    try:
        results = asyncio.run(_search())
        return [f.to_dict() for f in results]
    except RuntimeError:
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(_search())
        return [f.to_dict() for f in results]


def search_ucc_by_state(
    state: str,
    debtor_name: str = None,
    secured_party: str = None,
    filing_number: str = None,
    include_terminated: bool = False,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search UCC filings in a specific state (synchronous wrapper).

    Args:
        state: Two-letter state code
        debtor_name: Debtor name to search
        secured_party: Secured party name
        filing_number: Specific filing number
        include_terminated: Include terminated filings
        limit: Maximum results

    Returns:
        List of UCCFiling dictionaries
    """
    async def _search():
        async with UCCFilingsAPI() as api:
            if filing_number:
                result = await api.search_by_filing_number(state, filing_number)
                return [result] if result else []
            elif debtor_name:
                return await api.search_by_debtor(
                    state, debtor_name, include_terminated=include_terminated, limit=limit
                )
            elif secured_party:
                return await api.search_by_secured_party(
                    state, secured_party, include_terminated=include_terminated, limit=limit
                )
            return []

    try:
        results = asyncio.run(_search())
        return [f.to_dict() for f in results]
    except RuntimeError:
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(_search())
        return [f.to_dict() for f in results]


def get_ucc_filing(state: str, filing_number: str) -> Optional[Dict[str, Any]]:
    """
    Get UCC filing details by filing number (synchronous wrapper).

    Args:
        state: Two-letter state code
        filing_number: UCC filing number

    Returns:
        UCCFiling dictionary or None
    """
    async def _get():
        async with UCCFilingsAPI() as api:
            result = await api.search_by_filing_number(state, filing_number)
            return result

    try:
        result = asyncio.run(_get())
        return result.to_dict() if result else None
    except RuntimeError:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_get())
        return result.to_dict() if result else None


def get_available_states() -> Dict[str, Any]:
    """Get all available state UCC configurations."""
    api = UCCFilingsAPI()
    return {
        'states': {
            state: {
                'name': config['name'],
                'search_url': config.get('search_url'),
                'api_available': config.get('api_available', False),
            }
            for state, config in api.state_configs.items()
        },
        'coverage': api.get_coverage_stats(),
    }
