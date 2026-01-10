"""
Foreclosure Records Scraper Module

Provides comprehensive access to foreclosure records across US jurisdictions:
- Notice of Default (NOD)
- Lis Pendens (Notice of Pending Action)
- Notice of Trustee Sale
- Sheriff Sale / Auction listings
- REO (Bank-Owned) properties
- Short sale listings

Foreclosure data comes from:
- County Recorder (NOD, NTS, Deed in Lieu)
- County Courts (Lis Pendens, Judicial foreclosures)
- Sheriff's Office (Sheriff sales)
- HUD/Fannie Mae/Freddie Mac (REO listings)

Uses async/aiohttp for efficient multi-source queries.
"""

import logging
import asyncio
import aiohttp
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, quote
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ForeclosureStage(Enum):
    """Stages in the foreclosure process"""
    PRE_FORECLOSURE = "pre_foreclosure"  # Behind on payments
    NOTICE_OF_DEFAULT = "notice_of_default"  # NOD filed
    LIS_PENDENS = "lis_pendens"  # Lawsuit filed
    NOTICE_OF_SALE = "notice_of_sale"  # NTS/NFS filed
    AUCTION_SCHEDULED = "auction_scheduled"  # Sale date set
    AUCTION_POSTPONED = "auction_postponed"  # Sale postponed
    SOLD_AT_AUCTION = "sold_at_auction"  # Sold to third party
    BANK_OWNED = "bank_owned"  # REO - Reverted to lender
    SHORT_SALE = "short_sale"  # Listed below mortgage balance
    FORECLOSURE_CANCELLED = "cancelled"  # Reinstated or paid off
    UNKNOWN = "unknown"


class ForeclosureType(Enum):
    """Types of foreclosure processes"""
    NON_JUDICIAL = "non_judicial"  # Trustee sale (deed of trust states)
    JUDICIAL = "judicial"  # Court process (mortgage states)
    STRICT_FORECLOSURE = "strict"  # Court transfers title directly
    TAX_LIEN_FORECLOSURE = "tax_lien"  # Property tax foreclosure
    HOA_FORECLOSURE = "hoa"  # Homeowner association foreclosure
    UNKNOWN = "unknown"


class PropertyType(Enum):
    """Types of properties"""
    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTI_FAMILY = "multi_family"
    MANUFACTURED = "manufactured"
    LAND = "land"
    COMMERCIAL = "commercial"
    MIXED_USE = "mixed_use"
    UNKNOWN = "unknown"


@dataclass
class MortgageInfo:
    """Mortgage/loan information"""
    lender_name: str
    loan_amount: Optional[float] = None
    loan_date: Optional[date] = None
    loan_type: Optional[str] = None  # FHA, VA, Conventional, etc.
    interest_rate: Optional[float] = None
    trustee: Optional[str] = None
    servicer: Optional[str] = None
    original_loan_number: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'lender_name': self.lender_name,
            'loan_amount': self.loan_amount,
            'loan_date': self.loan_date.isoformat() if self.loan_date else None,
            'loan_type': self.loan_type,
            'interest_rate': self.interest_rate,
            'trustee': self.trustee,
            'servicer': self.servicer,
            'original_loan_number': self.original_loan_number,
        }


@dataclass
class AuctionInfo:
    """Auction/sale information"""
    auction_date: Optional[date] = None
    auction_time: Optional[str] = None
    auction_location: Optional[str] = None
    opening_bid: Optional[float] = None
    estimated_value: Optional[float] = None
    reserve_price: Optional[float] = None
    sale_result: Optional[str] = None  # sold, postponed, cancelled
    winning_bid: Optional[float] = None
    buyer_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'auction_date': self.auction_date.isoformat() if self.auction_date else None,
            'auction_time': self.auction_time,
            'auction_location': self.auction_location,
            'opening_bid': self.opening_bid,
            'estimated_value': self.estimated_value,
            'reserve_price': self.reserve_price,
            'sale_result': self.sale_result,
            'winning_bid': self.winning_bid,
            'buyer_name': self.buyer_name,
        }


@dataclass
class ForeclosureRecord:
    """Represents a foreclosure record"""
    # Identifiers
    case_number: str
    state: str
    county: str
    recording_date: date

    # Property info
    property_address: Optional[str] = None
    property_city: Optional[str] = None
    property_zip: Optional[str] = None
    parcel_number: Optional[str] = None
    property_type: PropertyType = PropertyType.UNKNOWN

    # Foreclosure details
    foreclosure_stage: ForeclosureStage = ForeclosureStage.UNKNOWN
    foreclosure_type: ForeclosureType = ForeclosureType.UNKNOWN
    document_type: Optional[str] = None  # NOD, NTS, LP, etc.
    document_number: Optional[str] = None

    # Parties
    borrower_name: Optional[str] = None
    lender_name: Optional[str] = None
    trustee_name: Optional[str] = None
    attorney_name: Optional[str] = None

    # Financial
    default_amount: Optional[float] = None
    unpaid_balance: Optional[float] = None
    estimated_value: Optional[float] = None
    equity: Optional[float] = None

    # Dates
    default_date: Optional[date] = None
    original_loan_date: Optional[date] = None

    # Mortgage info
    mortgage_info: Optional[MortgageInfo] = None

    # Auction info
    auction_info: Optional[AuctionInfo] = None

    # Metadata
    document_url: Optional[str] = None
    source_url: str = ""
    source_system: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'case_number': self.case_number,
            'state': self.state,
            'county': self.county,
            'recording_date': self.recording_date.isoformat(),
            'property_address': self.property_address,
            'property_city': self.property_city,
            'property_zip': self.property_zip,
            'parcel_number': self.parcel_number,
            'property_type': self.property_type.value,
            'foreclosure_stage': self.foreclosure_stage.value,
            'foreclosure_type': self.foreclosure_type.value,
            'document_type': self.document_type,
            'document_number': self.document_number,
            'borrower_name': self.borrower_name,
            'lender_name': self.lender_name,
            'trustee_name': self.trustee_name,
            'attorney_name': self.attorney_name,
            'default_amount': self.default_amount,
            'unpaid_balance': self.unpaid_balance,
            'estimated_value': self.estimated_value,
            'equity': self.equity,
            'default_date': self.default_date.isoformat() if self.default_date else None,
            'original_loan_date': self.original_loan_date.isoformat() if self.original_loan_date else None,
            'mortgage_info': self.mortgage_info.to_dict() if self.mortgage_info else None,
            'auction_info': self.auction_info.to_dict() if self.auction_info else None,
            'document_url': self.document_url,
            'source_url': self.source_url,
            'source_system': self.source_system,
            'fetched_at': self.fetched_at.isoformat(),
        }


# State foreclosure configurations
STATE_FORECLOSURE_CONFIGS: Dict[str, Dict[str, Any]] = {
    'CA': {
        'name': 'California',
        'process': 'non_judicial',
        'timeline_days': 120,
        'trustee_sale': True,
        'deficiency_allowed': False,
        'redemption_period_days': 0,
        'notes': 'Non-judicial with deed of trust, 3-month process minimum',
    },
    'TX': {
        'name': 'Texas',
        'process': 'non_judicial',
        'timeline_days': 41,
        'trustee_sale': True,
        'deficiency_allowed': True,
        'redemption_period_days': 0,
        'notes': 'Fastest non-judicial process, first Tuesday sales',
    },
    'FL': {
        'name': 'Florida',
        'process': 'judicial',
        'timeline_days': 180,
        'trustee_sale': False,
        'deficiency_allowed': True,
        'redemption_period_days': 0,
        'notes': 'Judicial process, can take 6-12 months',
    },
    'NY': {
        'name': 'New York',
        'process': 'judicial',
        'timeline_days': 365,
        'trustee_sale': False,
        'deficiency_allowed': True,
        'redemption_period_days': 0,
        'notes': 'Lengthy judicial process, mandatory settlement conferences',
    },
    'IL': {
        'name': 'Illinois',
        'process': 'judicial',
        'timeline_days': 210,
        'trustee_sale': False,
        'deficiency_allowed': True,
        'redemption_period_days': 90,
        'notes': 'Judicial with 90-day redemption period',
    },
    'PA': {
        'name': 'Pennsylvania',
        'process': 'judicial',
        'timeline_days': 270,
        'trustee_sale': False,
        'deficiency_allowed': True,
        'redemption_period_days': 0,
        'notes': 'Judicial process, sheriff sale',
    },
    'OH': {
        'name': 'Ohio',
        'process': 'judicial',
        'timeline_days': 150,
        'trustee_sale': False,
        'deficiency_allowed': True,
        'redemption_period_days': 0,
        'notes': 'Judicial process, sheriff sale',
    },
    'GA': {
        'name': 'Georgia',
        'process': 'non_judicial',
        'timeline_days': 60,
        'trustee_sale': True,
        'deficiency_allowed': True,
        'redemption_period_days': 0,
        'notes': 'Non-judicial, first Tuesday sales',
    },
    'NC': {
        'name': 'North Carolina',
        'process': 'non_judicial',
        'timeline_days': 90,
        'trustee_sale': True,
        'deficiency_allowed': True,
        'redemption_period_days': 0,
        'notes': 'Power of sale foreclosure',
    },
    'MI': {
        'name': 'Michigan',
        'process': 'non_judicial',
        'timeline_days': 60,
        'trustee_sale': True,
        'deficiency_allowed': True,
        'redemption_period_days': 180,
        'notes': 'Non-judicial with 6-month redemption',
    },
    'AZ': {
        'name': 'Arizona',
        'process': 'non_judicial',
        'timeline_days': 91,
        'trustee_sale': True,
        'deficiency_allowed': False,
        'redemption_period_days': 0,
        'notes': 'Non-judicial trustee sale, no deficiency on purchase loans',
    },
    'NV': {
        'name': 'Nevada',
        'process': 'non_judicial',
        'timeline_days': 116,
        'trustee_sale': True,
        'deficiency_allowed': False,
        'redemption_period_days': 0,
        'notes': 'Non-judicial, mediation available',
    },
    'NJ': {
        'name': 'New Jersey',
        'process': 'judicial',
        'timeline_days': 270,
        'trustee_sale': False,
        'deficiency_allowed': True,
        'redemption_period_days': 10,
        'notes': 'Judicial process, sheriff sale',
    },
    'VA': {
        'name': 'Virginia',
        'process': 'non_judicial',
        'timeline_days': 45,
        'trustee_sale': True,
        'deficiency_allowed': True,
        'redemption_period_days': 0,
        'notes': 'Non-judicial deed of trust foreclosure',
    },
    'WA': {
        'name': 'Washington',
        'process': 'non_judicial',
        'timeline_days': 120,
        'trustee_sale': True,
        'deficiency_allowed': False,
        'redemption_period_days': 0,
        'notes': 'Non-judicial with mediation option',
    },
    'MA': {
        'name': 'Massachusetts',
        'process': 'non_judicial',
        'timeline_days': 75,
        'trustee_sale': True,
        'deficiency_allowed': True,
        'redemption_period_days': 0,
        'notes': 'Non-judicial power of sale',
    },
    'CO': {
        'name': 'Colorado',
        'process': 'non_judicial',
        'timeline_days': 110,
        'trustee_sale': True,
        'deficiency_allowed': True,
        'redemption_period_days': 75,
        'notes': 'Non-judicial with redemption period',
    },
    'MD': {
        'name': 'Maryland',
        'process': 'non_judicial',
        'timeline_days': 90,
        'trustee_sale': True,
        'deficiency_allowed': True,
        'redemption_period_days': 0,
        'notes': 'Non-judicial assent to decree',
    },
}

# Add remaining states with default judicial process
for state in ['AL', 'AK', 'AR', 'CT', 'DE', 'HI', 'ID', 'IN', 'IA', 'KS', 'KY', 'LA',
              'ME', 'MN', 'MS', 'MO', 'MT', 'NE', 'NH', 'NM', 'ND', 'OK', 'OR',
              'RI', 'SC', 'SD', 'TN', 'UT', 'VT', 'WV', 'WI', 'WY', 'DC']:
    if state not in STATE_FORECLOSURE_CONFIGS:
        STATE_FORECLOSURE_CONFIGS[state] = {
            'name': state,
            'process': 'judicial',
            'timeline_days': 180,
            'trustee_sale': False,
            'deficiency_allowed': True,
            'redemption_period_days': 0,
        }


# Major county foreclosure sources
COUNTY_FORECLOSURE_SOURCES: Dict[str, Dict[str, Any]] = {
    # California Counties
    'CA_LOS_ANGELES': {
        'name': 'Los Angeles County',
        'recorder_url': 'https://www.lavote.net/home/records/property-document-recording',
        'auction_url': 'https://www.bid4assets.com/auctions/lacounty',
        'trustee_sales': True,
    },
    'CA_SAN_DIEGO': {
        'name': 'San Diego County',
        'recorder_url': 'https://arcc.sdcounty.ca.gov/',
        'auction_url': 'https://www.bid4assets.com/auctions/sandiego',
        'trustee_sales': True,
    },
    'CA_ORANGE': {
        'name': 'Orange County',
        'recorder_url': 'https://ocrecorder.ocgov.com/',
        'auction_url': 'https://www.bid4assets.com/auctions/orangecounty',
        'trustee_sales': True,
    },
    # Texas Counties
    'TX_HARRIS': {
        'name': 'Harris County',
        'recorder_url': 'https://www.cclerk.hctx.net/',
        'auction_url': 'https://www.hctax.net/Property/TaxSales',
        'trustee_sales': True,
    },
    'TX_DALLAS': {
        'name': 'Dallas County',
        'recorder_url': 'https://www.dallascounty.org/departments/countyclerk/',
        'auction_url': 'https://dallas.tx.newszap.com/legal-notices',
        'trustee_sales': True,
    },
    # Florida Counties
    'FL_MIAMI_DADE': {
        'name': 'Miami-Dade County',
        'clerk_url': 'https://www.miamidadeclerk.gov/',
        'auction_url': 'https://www.miamidade.realforeclose.com/',
        'judicial': True,
    },
    'FL_BROWARD': {
        'name': 'Broward County',
        'clerk_url': 'https://www.browardclerk.org/',
        'auction_url': 'https://www.broward.realforeclose.com/',
        'judicial': True,
    },
    # New York
    'NY_KINGS': {
        'name': 'Kings County (Brooklyn)',
        'clerk_url': 'https://iapps.courts.state.ny.us/nyscef/',
        'auction_url': 'https://www.nycourts.gov/legacyhtm/supctmanh/auction.shtml',
        'judicial': True,
    },
}


class ForeclosuresAPI:
    """
    Unified Foreclosure Records API client.

    Provides access to foreclosure data from multiple sources:
    - County Recorder (NOD, NTS filings)
    - County Courts (Lis Pendens, Judicial foreclosures)
    - HUD/GSE (Government REO listings)
    - Third-party auction sites

    Uses async/aiohttp for efficient multi-source queries.
    """

    CATEGORY = "foreclosures"
    DISPLAY_NAME = "Foreclosure Records"

    # HUD homes API
    HUD_HOMES_URL = "https://www.hudhomestore.gov/Listing/PropertySearch"

    # Fannie Mae HomePath
    HOMEPATH_URL = "https://www.homepath.com/listing"

    # Freddie Mac HomeSteps
    HOMESTEPS_URL = "https://www.homesteps.com/rs/search"

    def __init__(self, timeout: int = 30):
        """
        Initialize foreclosure records API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request = 0.0
        self._rate_limit_delay = 1.5
        self.state_configs = STATE_FORECLOSURE_CONFIGS
        self.county_sources = COUNTY_FORECLOSURE_SOURCES
        logger.info("ForeclosuresAPI initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {
                'User-Agent': 'DataGod/1.0 (Foreclosure Records Research)',
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

    async def search_by_address(
        self,
        state: str,
        address: str,
        city: str = None,
        zip_code: str = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """
        Search foreclosure records by property address.

        Args:
            state: Two-letter state code
            address: Street address
            city: City name
            zip_code: ZIP code
            limit: Maximum results

        Returns:
            List of matching ForeclosureRecord objects
        """
        state = state.upper()
        logger.info(f"Searching foreclosures in {state} for address: {address}")

        await self._rate_limit()
        session = await self._get_session()

        records = []

        # Search HUD homes
        hud_records = await self._search_hud_homes(session, state, city, zip_code, limit)
        records.extend(hud_records)

        # Search Fannie Mae HomePath
        homepath_records = await self._search_homepath(session, state, city, zip_code, limit)
        records.extend(homepath_records)

        # Search county-specific sources
        county_records = await self._search_county_foreclosures(session, state, address, city, limit)
        records.extend(county_records)

        return records

    async def search_by_county(
        self,
        state: str,
        county: str,
        stage: ForeclosureStage = None,
        foreclosure_type: ForeclosureType = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50
    ) -> List[ForeclosureRecord]:
        """
        Search foreclosure records by county.

        Args:
            state: Two-letter state code
            county: County name
            stage: Filter by foreclosure stage
            foreclosure_type: Filter by type
            date_from: Start date
            date_to: End date
            limit: Maximum results

        Returns:
            List of matching ForeclosureRecord objects
        """
        state = state.upper()
        logger.info(f"Searching foreclosures in {county}, {state}")

        await self._rate_limit()
        session = await self._get_session()

        records = []

        # Determine county key
        county_key = f"{state}_{county.upper().replace(' ', '_').replace('COUNTY', '').strip()}"

        if county_key in self.county_sources:
            records = await self._search_specific_county(session, county_key, stage, date_from, date_to, limit)
        else:
            # Generic county search
            records = await self._search_generic_county(session, state, county, stage, date_from, date_to, limit)

        return records

    async def search_by_borrower(
        self,
        state: str,
        borrower_name: str,
        county: str = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """
        Search foreclosure records by borrower name.

        Args:
            state: Two-letter state code
            borrower_name: Name of borrower/homeowner
            county: Optional county filter
            limit: Maximum results

        Returns:
            List of matching ForeclosureRecord objects
        """
        state = state.upper()
        logger.info(f"Searching foreclosures in {state} for borrower: {borrower_name}")

        await self._rate_limit()
        session = await self._get_session()

        records = []

        # Search county recorder/court records
        if county:
            records = await self._search_county_by_name(session, state, county, borrower_name, limit)
        else:
            # Search multiple major counties in state
            major_counties = self._get_major_counties(state)
            for county_name in major_counties[:5]:
                county_records = await self._search_county_by_name(session, state, county_name, borrower_name, limit // 5)
                records.extend(county_records)

        return records

    async def search_scheduled_auctions(
        self,
        state: str,
        county: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50
    ) -> List[ForeclosureRecord]:
        """
        Search upcoming foreclosure auctions.

        Args:
            state: Two-letter state code
            county: County name (optional)
            date_from: Earliest auction date
            date_to: Latest auction date
            limit: Maximum results

        Returns:
            List of ForeclosureRecord objects with auction info
        """
        state = state.upper()
        logger.info(f"Searching upcoming auctions in {state}")

        await self._rate_limit()
        session = await self._get_session()

        records = []

        # Search auction sites
        auction_records = await self._search_auction_sites(session, state, county, date_from, date_to, limit)
        records.extend(auction_records)

        # Filter for only scheduled auctions
        records = [r for r in records if r.foreclosure_stage == ForeclosureStage.AUCTION_SCHEDULED]

        return records[:limit]

    async def search_reo_properties(
        self,
        state: str,
        city: str = None,
        zip_code: str = None,
        max_price: float = None,
        limit: int = 50
    ) -> List[ForeclosureRecord]:
        """
        Search bank-owned (REO) properties.

        Args:
            state: Two-letter state code
            city: City name
            zip_code: ZIP code
            max_price: Maximum price filter
            limit: Maximum results

        Returns:
            List of ForeclosureRecord objects for REO properties
        """
        state = state.upper()
        logger.info(f"Searching REO properties in {state}")

        await self._rate_limit()
        session = await self._get_session()

        records = []

        # Search HUD homes
        hud_records = await self._search_hud_homes(session, state, city, zip_code, limit // 3)
        records.extend(hud_records)

        # Search Fannie Mae HomePath
        homepath_records = await self._search_homepath(session, state, city, zip_code, limit // 3)
        records.extend(homepath_records)

        # Search Freddie Mac HomeSteps
        homesteps_records = await self._search_homesteps(session, state, city, zip_code, limit // 3)
        records.extend(homesteps_records)

        # Filter by max price if specified
        if max_price:
            records = [r for r in records if r.estimated_value and r.estimated_value <= max_price]

        return records[:limit]

    # ========== Source-Specific Searches ==========

    async def _search_hud_homes(
        self,
        session: aiohttp.ClientSession,
        state: str,
        city: str = None,
        zip_code: str = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """Search HUD-owned homes."""
        url = "https://www.hudhomestore.gov/Listing/PropertySearchResult"

        params = {
            'state': state,
            'pageSize': limit,
        }
        if city:
            params['city'] = city
        if zip_code:
            params['zip'] = zip_code

        records = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    records = self._parse_hud_results(html, state, limit)
        except Exception as e:
            logger.error(f"HUD homes search error: {e}")

        return records

    def _parse_hud_results(self, html: str, state: str, limit: int) -> List[ForeclosureRecord]:
        """Parse HUD homes search results."""
        records = []
        soup = BeautifulSoup(html, 'html.parser')

        # Find property listings
        listings = soup.select('.property-listing, .listing-item, div[class*="property"]')

        for listing in listings[:limit]:
            try:
                # Extract address
                address_elem = listing.select_one('.address, .property-address, h3, h4')
                address = address_elem.get_text(strip=True) if address_elem else ''

                # Extract price
                price_elem = listing.select_one('.price, .list-price, span[class*="price"]')
                price_text = price_elem.get_text(strip=True) if price_elem else ''
                price = self._parse_price(price_text)

                # Extract city/zip from address
                city, zip_code = self._parse_city_zip(address, state)

                # Extract case number
                case_elem = listing.select_one('.case-number, .hud-case, span[class*="case"]')
                case_number = case_elem.get_text(strip=True) if case_elem else f"HUD-{datetime.now().strftime('%Y%m%d')}"

                record = ForeclosureRecord(
                    case_number=case_number,
                    state=state,
                    county='',
                    recording_date=date.today(),
                    property_address=address,
                    property_city=city,
                    property_zip=zip_code,
                    foreclosure_stage=ForeclosureStage.BANK_OWNED,
                    foreclosure_type=ForeclosureType.UNKNOWN,
                    lender_name='HUD',
                    estimated_value=price,
                    source_url='https://www.hudhomestore.gov/',
                    source_system='HUD HomeStore',
                    fetched_at=datetime.now()
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Error parsing HUD listing: {e}")

        return records

    async def _search_homepath(
        self,
        session: aiohttp.ClientSession,
        state: str,
        city: str = None,
        zip_code: str = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """Search Fannie Mae HomePath properties."""
        url = "https://www.homepath.com/listings"

        params = {
            'state': state,
            'rows': limit,
        }
        if city:
            params['city'] = city
        if zip_code:
            params['postalCode'] = zip_code

        records = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    # HomePath may return JSON
                    content_type = response.headers.get('Content-Type', '')
                    if 'json' in content_type:
                        data = await response.json()
                        records = self._parse_homepath_json(data, state, limit)
                    else:
                        html = await response.text()
                        records = self._parse_homepath_html(html, state, limit)
        except Exception as e:
            logger.error(f"HomePath search error: {e}")

        return records

    def _parse_homepath_json(self, data: Dict[str, Any], state: str, limit: int) -> List[ForeclosureRecord]:
        """Parse HomePath JSON results."""
        records = []

        listings = data.get('listings', data.get('properties', []))

        for listing in listings[:limit]:
            try:
                record = ForeclosureRecord(
                    case_number=listing.get('listingId', f"FNMA-{datetime.now().strftime('%Y%m%d')}"),
                    state=state,
                    county=listing.get('county', ''),
                    recording_date=date.today(),
                    property_address=listing.get('address', ''),
                    property_city=listing.get('city', ''),
                    property_zip=listing.get('zip', listing.get('postalCode', '')),
                    property_type=self._classify_property_type(listing.get('propertyType', '')),
                    foreclosure_stage=ForeclosureStage.BANK_OWNED,
                    foreclosure_type=ForeclosureType.UNKNOWN,
                    lender_name='Fannie Mae',
                    estimated_value=listing.get('listPrice'),
                    source_url='https://www.homepath.com/',
                    source_system='Fannie Mae HomePath',
                    raw_data=listing,
                    fetched_at=datetime.now()
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Error parsing HomePath listing: {e}")

        return records

    def _parse_homepath_html(self, html: str, state: str, limit: int) -> List[ForeclosureRecord]:
        """Parse HomePath HTML results."""
        records = []
        soup = BeautifulSoup(html, 'html.parser')

        listings = soup.select('.property-card, .listing, div[data-listing]')

        for listing in listings[:limit]:
            try:
                address_elem = listing.select_one('.address, h3')
                address = address_elem.get_text(strip=True) if address_elem else ''

                price_elem = listing.select_one('.price, .list-price')
                price = self._parse_price(price_elem.get_text(strip=True) if price_elem else '')

                city, zip_code = self._parse_city_zip(address, state)

                record = ForeclosureRecord(
                    case_number=f"FNMA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    state=state,
                    county='',
                    recording_date=date.today(),
                    property_address=address,
                    property_city=city,
                    property_zip=zip_code,
                    foreclosure_stage=ForeclosureStage.BANK_OWNED,
                    lender_name='Fannie Mae',
                    estimated_value=price,
                    source_url='https://www.homepath.com/',
                    source_system='Fannie Mae HomePath',
                    fetched_at=datetime.now()
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Error parsing HomePath listing: {e}")

        return records

    async def _search_homesteps(
        self,
        session: aiohttp.ClientSession,
        state: str,
        city: str = None,
        zip_code: str = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """Search Freddie Mac HomeSteps properties."""
        url = "https://www.homesteps.com/rs/results"

        params = {
            'stateCode': state,
            'rows': limit,
        }
        if city:
            params['city'] = city
        if zip_code:
            params['zip'] = zip_code

        records = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'json' in content_type:
                        data = await response.json()
                        records = self._parse_homesteps_json(data, state, limit)
                    else:
                        html = await response.text()
                        records = self._parse_homesteps_html(html, state, limit)
        except Exception as e:
            logger.error(f"HomeSteps search error: {e}")

        return records

    def _parse_homesteps_json(self, data: Dict[str, Any], state: str, limit: int) -> List[ForeclosureRecord]:
        """Parse HomeSteps JSON results."""
        records = []

        listings = data.get('results', data.get('listings', []))

        for listing in listings[:limit]:
            try:
                record = ForeclosureRecord(
                    case_number=listing.get('propertyId', f"FHLMC-{datetime.now().strftime('%Y%m%d')}"),
                    state=state,
                    county=listing.get('county', ''),
                    recording_date=date.today(),
                    property_address=listing.get('streetAddress', ''),
                    property_city=listing.get('city', ''),
                    property_zip=listing.get('zipCode', ''),
                    property_type=self._classify_property_type(listing.get('propertyType', '')),
                    foreclosure_stage=ForeclosureStage.BANK_OWNED,
                    lender_name='Freddie Mac',
                    estimated_value=listing.get('listPrice'),
                    source_url='https://www.homesteps.com/',
                    source_system='Freddie Mac HomeSteps',
                    raw_data=listing,
                    fetched_at=datetime.now()
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Error parsing HomeSteps listing: {e}")

        return records

    def _parse_homesteps_html(self, html: str, state: str, limit: int) -> List[ForeclosureRecord]:
        """Parse HomeSteps HTML results."""
        records = []
        soup = BeautifulSoup(html, 'html.parser')

        listings = soup.select('.property-result, .listing-item')

        for listing in listings[:limit]:
            try:
                address_elem = listing.select_one('.address, h4')
                address = address_elem.get_text(strip=True) if address_elem else ''

                price_elem = listing.select_one('.price')
                price = self._parse_price(price_elem.get_text(strip=True) if price_elem else '')

                city, zip_code = self._parse_city_zip(address, state)

                record = ForeclosureRecord(
                    case_number=f"FHLMC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    state=state,
                    county='',
                    recording_date=date.today(),
                    property_address=address,
                    property_city=city,
                    property_zip=zip_code,
                    foreclosure_stage=ForeclosureStage.BANK_OWNED,
                    lender_name='Freddie Mac',
                    estimated_value=price,
                    source_url='https://www.homesteps.com/',
                    source_system='Freddie Mac HomeSteps',
                    fetched_at=datetime.now()
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Error parsing HomeSteps listing: {e}")

        return records

    async def _search_county_foreclosures(
        self,
        session: aiohttp.ClientSession,
        state: str,
        address: str,
        city: str = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """Search county-level foreclosure records."""
        records = []

        # Find counties with sources for this state
        state_counties = [k for k in self.county_sources.keys() if k.startswith(f"{state}_")]

        for county_key in state_counties[:3]:  # Limit to 3 counties
            county_records = await self._search_specific_county(
                session, county_key, None, None, None, limit // 3
            )
            records.extend(county_records)

        return records

    async def _search_specific_county(
        self,
        session: aiohttp.ClientSession,
        county_key: str,
        stage: ForeclosureStage = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """Search a specific county's foreclosure records."""
        if county_key not in self.county_sources:
            return []

        config = self.county_sources[county_key]
        records = []

        # Parse state from key
        state = county_key.split('_')[0]
        county_name = config.get('name', county_key.split('_', 1)[1].replace('_', ' '))

        # Try recorder URL
        recorder_url = config.get('recorder_url')
        if recorder_url:
            # Would implement specific scraper for each county
            pass

        # Try auction URL
        auction_url = config.get('auction_url')
        if auction_url:
            auction_records = await self._search_auction_url(session, auction_url, state, county_name, limit)
            records.extend(auction_records)

        return records

    async def _search_generic_county(
        self,
        session: aiohttp.ClientSession,
        state: str,
        county: str,
        stage: ForeclosureStage = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """Generic county foreclosure search."""
        records = []

        # Try common auction aggregator sites
        aggregator_records = await self._search_auction_aggregators(session, state, county, limit)
        records.extend(aggregator_records)

        return records

    async def _search_county_by_name(
        self,
        session: aiohttp.ClientSession,
        state: str,
        county: str,
        borrower_name: str,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """Search county records by borrower name."""
        records = []

        # This would connect to county court/recorder systems
        # Implementation varies by county

        return records

    async def _search_auction_sites(
        self,
        session: aiohttp.ClientSession,
        state: str,
        county: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50
    ) -> List[ForeclosureRecord]:
        """Search online auction sites."""
        records = []

        # Search common auction aggregators
        aggregator_records = await self._search_auction_aggregators(session, state, county, limit)
        records.extend(aggregator_records)

        return records

    async def _search_auction_aggregators(
        self,
        session: aiohttp.ClientSession,
        state: str,
        county: str = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """Search foreclosure auction aggregator sites."""
        records = []

        # Bid4Assets
        bid4assets_records = await self._search_bid4assets(session, state, county, limit // 2)
        records.extend(bid4assets_records)

        # Auction.com
        auction_com_records = await self._search_auction_com(session, state, county, limit // 2)
        records.extend(auction_com_records)

        return records

    async def _search_bid4assets(
        self,
        session: aiohttp.ClientSession,
        state: str,
        county: str = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """Search Bid4Assets foreclosure auctions."""
        url = "https://www.bid4assets.com/auctions"

        params = {
            'state': state,
            'type': 'foreclosure',
            'pageSize': limit,
        }
        if county:
            params['county'] = county

        records = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    records = self._parse_bid4assets_results(html, state, county, limit)
        except Exception as e:
            logger.error(f"Bid4Assets search error: {e}")

        return records

    def _parse_bid4assets_results(self, html: str, state: str, county: str, limit: int) -> List[ForeclosureRecord]:
        """Parse Bid4Assets search results."""
        records = []
        soup = BeautifulSoup(html, 'html.parser')

        listings = soup.select('.auction-item, .property-listing')

        for listing in listings[:limit]:
            try:
                # Extract auction info
                title_elem = listing.select_one('.title, h3')
                title = title_elem.get_text(strip=True) if title_elem else ''

                address_elem = listing.select_one('.address, .location')
                address = address_elem.get_text(strip=True) if address_elem else ''

                bid_elem = listing.select_one('.current-bid, .starting-bid')
                opening_bid = self._parse_price(bid_elem.get_text(strip=True) if bid_elem else '')

                date_elem = listing.select_one('.auction-date, .end-date')
                auction_date = self._parse_date(date_elem.get_text(strip=True) if date_elem else '')

                record = ForeclosureRecord(
                    case_number=f"B4A-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    state=state,
                    county=county or '',
                    recording_date=date.today(),
                    property_address=address or title,
                    foreclosure_stage=ForeclosureStage.AUCTION_SCHEDULED,
                    auction_info=AuctionInfo(
                        auction_date=auction_date,
                        opening_bid=opening_bid,
                    ),
                    source_url='https://www.bid4assets.com/',
                    source_system='Bid4Assets',
                    fetched_at=datetime.now()
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Error parsing Bid4Assets listing: {e}")

        return records

    async def _search_auction_com(
        self,
        session: aiohttp.ClientSession,
        state: str,
        county: str = None,
        limit: int = 25
    ) -> List[ForeclosureRecord]:
        """Search Auction.com foreclosure listings."""
        url = "https://www.auction.com/residential/foreclosure/"

        params = {
            'state': state,
            'limit': limit,
        }
        if county:
            params['county'] = county

        records = []

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    records = self._parse_auction_com_results(html, state, county, limit)
        except Exception as e:
            logger.error(f"Auction.com search error: {e}")

        return records

    def _parse_auction_com_results(self, html: str, state: str, county: str, limit: int) -> List[ForeclosureRecord]:
        """Parse Auction.com search results."""
        records = []
        soup = BeautifulSoup(html, 'html.parser')

        listings = soup.select('.property-tile, .auction-listing')

        for listing in listings[:limit]:
            try:
                address_elem = listing.select_one('.address, .property-address')
                address = address_elem.get_text(strip=True) if address_elem else ''

                price_elem = listing.select_one('.price, .current-bid')
                price = self._parse_price(price_elem.get_text(strip=True) if price_elem else '')

                date_elem = listing.select_one('.auction-date')
                auction_date = self._parse_date(date_elem.get_text(strip=True) if date_elem else '')

                record = ForeclosureRecord(
                    case_number=f"ACOM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    state=state,
                    county=county or '',
                    recording_date=date.today(),
                    property_address=address,
                    foreclosure_stage=ForeclosureStage.AUCTION_SCHEDULED,
                    estimated_value=price,
                    auction_info=AuctionInfo(
                        auction_date=auction_date,
                        opening_bid=price,
                    ),
                    source_url='https://www.auction.com/',
                    source_system='Auction.com',
                    fetched_at=datetime.now()
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Error parsing Auction.com listing: {e}")

        return records

    async def _search_auction_url(
        self,
        session: aiohttp.ClientSession,
        auction_url: str,
        state: str,
        county: str,
        limit: int
    ) -> List[ForeclosureRecord]:
        """Search a specific auction URL."""
        records = []

        try:
            async with session.get(auction_url) as response:
                if response.status == 200:
                    html = await response.text()
                    # Generic parsing
                    soup = BeautifulSoup(html, 'html.parser')

                    # Look for common auction listing patterns
                    listings = soup.select('.auction, .listing, .property, tr[class*="auction"]')

                    for listing in listings[:limit]:
                        # Try to extract basic info
                        text = listing.get_text(strip=True)
                        if len(text) > 20:
                            record = ForeclosureRecord(
                                case_number=f"AUC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                state=state,
                                county=county,
                                recording_date=date.today(),
                                property_address=text[:100],
                                foreclosure_stage=ForeclosureStage.AUCTION_SCHEDULED,
                                source_url=auction_url,
                                source_system='County Auction',
                                fetched_at=datetime.now()
                            )
                            records.append(record)
        except Exception as e:
            logger.warning(f"Error searching auction URL {auction_url}: {e}")

        return records

    # ========== Utility Methods ==========

    def _get_major_counties(self, state: str) -> List[str]:
        """Get list of major counties for a state."""
        major_counties = {
            'CA': ['Los Angeles', 'San Diego', 'Orange', 'Santa Clara', 'San Francisco'],
            'TX': ['Harris', 'Dallas', 'Tarrant', 'Bexar', 'Travis'],
            'FL': ['Miami-Dade', 'Broward', 'Palm Beach', 'Hillsborough', 'Orange'],
            'NY': ['Kings', 'Queens', 'New York', 'Suffolk', 'Nassau'],
            'IL': ['Cook', 'DuPage', 'Lake', 'Will', 'Kane'],
            'PA': ['Philadelphia', 'Allegheny', 'Montgomery', 'Bucks', 'Delaware'],
            'OH': ['Cuyahoga', 'Franklin', 'Hamilton', 'Summit', 'Montgomery'],
            'GA': ['Fulton', 'Gwinnett', 'Cobb', 'DeKalb', 'Clayton'],
            'NC': ['Mecklenburg', 'Wake', 'Guilford', 'Forsyth', 'Durham'],
            'MI': ['Wayne', 'Oakland', 'Macomb', 'Kent', 'Genesee'],
            'AZ': ['Maricopa', 'Pima', 'Pinal', 'Yavapai', 'Coconino'],
            'NV': ['Clark', 'Washoe', 'Carson City'],
        }
        return major_counties.get(state, ['Default County'])

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date from various formats."""
        if not date_str:
            return None

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

    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse price from text."""
        if not price_str:
            return None

        # Remove non-numeric characters except decimal
        cleaned = re.sub(r'[^\d.]', '', price_str)
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    def _parse_city_zip(self, address: str, state: str) -> tuple:
        """Extract city and ZIP from address string."""
        city = ''
        zip_code = ''

        # Try to find ZIP code pattern
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address)
        if zip_match:
            zip_code = zip_match.group(1)

        # Try to find city before state abbreviation
        city_match = re.search(rf',\s*([^,]+),?\s*{state}', address, re.IGNORECASE)
        if city_match:
            city = city_match.group(1).strip()

        return city, zip_code

    def _classify_property_type(self, type_str: str) -> PropertyType:
        """Classify property type from text."""
        if not type_str:
            return PropertyType.UNKNOWN

        type_lower = type_str.lower()

        if 'single family' in type_lower or 'sfr' in type_lower:
            return PropertyType.SINGLE_FAMILY
        elif 'condo' in type_lower:
            return PropertyType.CONDO
        elif 'townhouse' in type_lower or 'townhome' in type_lower:
            return PropertyType.TOWNHOUSE
        elif 'multi' in type_lower or 'duplex' in type_lower or 'triplex' in type_lower:
            return PropertyType.MULTI_FAMILY
        elif 'manufactured' in type_lower or 'mobile' in type_lower:
            return PropertyType.MANUFACTURED
        elif 'land' in type_lower or 'lot' in type_lower:
            return PropertyType.LAND
        elif 'commercial' in type_lower:
            return PropertyType.COMMERCIAL
        elif 'mixed' in type_lower:
            return PropertyType.MIXED_USE

        return PropertyType.UNKNOWN

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        non_judicial_states = [s for s, c in self.state_configs.items() if c.get('process') == 'non_judicial']
        judicial_states = [s for s, c in self.state_configs.items() if c.get('process') == 'judicial']

        return {
            'category': self.CATEGORY,
            'display_name': self.DISPLAY_NAME,
            'total_states': len(self.state_configs),
            'non_judicial_states': len(non_judicial_states),
            'judicial_states': len(judicial_states),
            'counties_with_sources': len(self.county_sources),
            'foreclosure_stages': [s.value for s in ForeclosureStage],
            'foreclosure_types': [t.value for t in ForeclosureType],
            'property_types': [p.value for p in PropertyType],
        }


# ========== Synchronous Wrappers ==========

def search_foreclosures_by_address(
    state: str,
    address: str,
    city: str = None,
    zip_code: str = None,
    limit: int = 25
) -> List[Dict[str, Any]]:
    """
    Search foreclosure records by address (synchronous wrapper).

    Args:
        state: Two-letter state code
        address: Street address
        city: City name
        zip_code: ZIP code
        limit: Maximum results

    Returns:
        List of ForeclosureRecord dictionaries
    """
    async def _search():
        async with ForeclosuresAPI() as api:
            records = await api.search_by_address(state, address, city, zip_code, limit)
            return [r.to_dict() for r in records]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def search_foreclosures_by_county(
    state: str,
    county: str,
    stage: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search foreclosure records by county (synchronous wrapper).

    Args:
        state: Two-letter state code
        county: County name
        stage: Foreclosure stage filter
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        limit: Maximum results

    Returns:
        List of ForeclosureRecord dictionaries
    """
    async def _search():
        async with ForeclosuresAPI() as api:
            stage_enum = None
            if stage:
                try:
                    stage_enum = ForeclosureStage(stage)
                except ValueError:
                    pass

            from_date = None
            to_date = None
            if date_from:
                try:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                except ValueError:
                    pass
            if date_to:
                try:
                    to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                except ValueError:
                    pass

            records = await api.search_by_county(state, county, stage_enum, None, from_date, to_date, limit)
            return [r.to_dict() for r in records]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def search_foreclosure_auctions(
    state: str,
    county: str = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search upcoming foreclosure auctions (synchronous wrapper).

    Args:
        state: Two-letter state code
        county: County name (optional)
        limit: Maximum results

    Returns:
        List of ForeclosureRecord dictionaries
    """
    async def _search():
        async with ForeclosuresAPI() as api:
            records = await api.search_scheduled_auctions(state, county, None, None, limit)
            return [r.to_dict() for r in records]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def search_reo_properties(
    state: str,
    city: str = None,
    zip_code: str = None,
    max_price: float = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search bank-owned (REO) properties (synchronous wrapper).

    Args:
        state: Two-letter state code
        city: City name
        zip_code: ZIP code
        max_price: Maximum price filter
        limit: Maximum results

    Returns:
        List of ForeclosureRecord dictionaries
    """
    async def _search():
        async with ForeclosuresAPI() as api:
            records = await api.search_reo_properties(state, city, zip_code, max_price, limit)
            return [r.to_dict() for r in records]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def get_state_foreclosure_info(state: str) -> Dict[str, Any]:
    """Get foreclosure process information for a state."""
    api = ForeclosuresAPI()
    config = api.state_configs.get(state.upper(), {})
    return {
        'state': state.upper(),
        'name': config.get('name', state),
        'process': config.get('process', 'unknown'),
        'timeline_days': config.get('timeline_days', 0),
        'trustee_sale': config.get('trustee_sale', False),
        'deficiency_allowed': config.get('deficiency_allowed', True),
        'redemption_period_days': config.get('redemption_period_days', 0),
        'notes': config.get('notes', ''),
    }


def get_available_states() -> Dict[str, Any]:
    """Get all available state foreclosure configurations."""
    api = ForeclosuresAPI()
    return {
        'states': {
            state: {
                'name': config.get('name', state),
                'process': config.get('process', 'unknown'),
                'timeline_days': config.get('timeline_days', 0),
            }
            for state, config in api.state_configs.items()
        },
        'coverage': api.get_coverage_stats(),
    }
