"""
Building Permits Scraper Module

Provides comprehensive access to building permit records across US jurisdictions:
- New construction permits
- Renovation/remodel permits
- Electrical, plumbing, mechanical permits
- Demolition permits
- Certificate of Occupancy
- Inspection records

Permit data comes from:
- City/County Building Departments
- Code Enforcement Offices
- Planning & Zoning Departments

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


class PermitType(Enum):
    """Types of building permits"""
    NEW_CONSTRUCTION = "new_construction"
    ADDITION = "addition"
    ALTERATION = "alteration"
    RENOVATION = "renovation"
    REMODEL = "remodel"
    REPAIR = "repair"
    DEMOLITION = "demolition"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    MECHANICAL = "mechanical"
    HVAC = "hvac"
    ROOFING = "roofing"
    SOLAR = "solar"
    POOL = "pool"
    FENCE = "fence"
    DECK = "deck"
    GARAGE = "garage"
    ADU = "adu"  # Accessory Dwelling Unit
    SIGN = "sign"
    GRADING = "grading"
    FIRE_ALARM = "fire_alarm"
    SPRINKLER = "sprinkler"
    FOUNDATION = "foundation"
    TEMPORARY = "temporary"
    CERTIFICATE_OF_OCCUPANCY = "certificate_of_occupancy"
    OTHER = "other"


class PermitStatus(Enum):
    """Permit status values"""
    APPLIED = "applied"
    PENDING_REVIEW = "pending_review"
    PLAN_CHECK = "plan_check"
    APPROVED = "approved"
    ISSUED = "issued"
    ACTIVE = "active"
    INSPECTION_REQUIRED = "inspection_required"
    INSPECTION_SCHEDULED = "inspection_scheduled"
    INSPECTION_PASSED = "inspection_passed"
    INSPECTION_FAILED = "inspection_failed"
    CORRECTIONS_REQUIRED = "corrections_required"
    HOLD = "hold"
    FINALED = "finaled"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REVOKED = "revoked"
    DENIED = "denied"
    UNKNOWN = "unknown"


class PropertyUse(Enum):
    """Property use types"""
    RESIDENTIAL_SINGLE = "residential_single"
    RESIDENTIAL_MULTI = "residential_multi"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"
    INSTITUTIONAL = "institutional"
    AGRICULTURAL = "agricultural"
    UNKNOWN = "unknown"


@dataclass
class Contractor:
    """Contractor information"""
    name: str
    license_number: Optional[str] = None
    license_type: Optional[str] = None
    company_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_owner_builder: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'license_number': self.license_number,
            'license_type': self.license_type,
            'company_name': self.company_name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'phone': self.phone,
            'email': self.email,
            'is_owner_builder': self.is_owner_builder,
        }


@dataclass
class Inspection:
    """Building inspection record"""
    inspection_date: date
    inspection_type: str
    inspector_name: Optional[str] = None
    result: Optional[str] = None  # passed, failed, partial
    comments: Optional[str] = None
    scheduled_time: Optional[str] = None
    actual_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'inspection_date': self.inspection_date.isoformat(),
            'inspection_type': self.inspection_type,
            'inspector_name': self.inspector_name,
            'result': self.result,
            'comments': self.comments,
            'scheduled_time': self.scheduled_time,
            'actual_time': self.actual_time,
        }


@dataclass
class BuildingPermit:
    """Represents a building permit record"""
    # Identifiers
    permit_number: str
    state: str
    jurisdiction: str  # City or County
    application_date: date

    # Property info
    property_address: Optional[str] = None
    property_city: Optional[str] = None
    property_zip: Optional[str] = None
    parcel_number: Optional[str] = None
    property_use: PropertyUse = PropertyUse.UNKNOWN

    # Permit details
    permit_type: PermitType = PermitType.OTHER
    permit_subtype: Optional[str] = None
    permit_status: PermitStatus = PermitStatus.UNKNOWN
    work_description: Optional[str] = None

    # Project info
    project_name: Optional[str] = None
    scope_of_work: Optional[str] = None
    square_footage: Optional[int] = None
    stories: Optional[int] = None
    units: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None

    # Financial
    valuation: Optional[float] = None  # Project value
    permit_fee: Optional[float] = None
    plan_check_fee: Optional[float] = None
    impact_fees: Optional[float] = None
    total_fees: Optional[float] = None

    # Dates
    issue_date: Optional[date] = None
    expiration_date: Optional[date] = None
    final_date: Optional[date] = None

    # Parties
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None
    applicant_name: Optional[str] = None
    contractor: Optional[Contractor] = None

    # Inspections
    inspections: List[Inspection] = field(default_factory=list)

    # Related permits
    related_permits: List[str] = field(default_factory=list)

    # Metadata
    document_url: Optional[str] = None
    source_url: str = ""
    source_system: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'permit_number': self.permit_number,
            'state': self.state,
            'jurisdiction': self.jurisdiction,
            'application_date': self.application_date.isoformat(),
            'property_address': self.property_address,
            'property_city': self.property_city,
            'property_zip': self.property_zip,
            'parcel_number': self.parcel_number,
            'property_use': self.property_use.value,
            'permit_type': self.permit_type.value,
            'permit_subtype': self.permit_subtype,
            'permit_status': self.permit_status.value,
            'work_description': self.work_description,
            'project_name': self.project_name,
            'scope_of_work': self.scope_of_work,
            'square_footage': self.square_footage,
            'stories': self.stories,
            'units': self.units,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'valuation': self.valuation,
            'permit_fee': self.permit_fee,
            'plan_check_fee': self.plan_check_fee,
            'impact_fees': self.impact_fees,
            'total_fees': self.total_fees,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'final_date': self.final_date.isoformat() if self.final_date else None,
            'owner_name': self.owner_name,
            'owner_address': self.owner_address,
            'applicant_name': self.applicant_name,
            'contractor': self.contractor.to_dict() if self.contractor else None,
            'inspections': [i.to_dict() for i in self.inspections],
            'related_permits': self.related_permits,
            'document_url': self.document_url,
            'source_url': self.source_url,
            'source_system': self.source_system,
            'fetched_at': self.fetched_at.isoformat(),
        }


# Major city/jurisdiction permit systems
JURISDICTION_PERMIT_SOURCES: Dict[str, Dict[str, Any]] = {
    # California
    'CA_LOS_ANGELES': {
        'name': 'City of Los Angeles',
        'url': 'https://www.ladbsservices.lacity.org/',
        'api_url': 'https://data.lacity.org/resource/yv23-pmwf.json',
        'api_available': True,
        'system': 'LADBS',
    },
    'CA_SAN_FRANCISCO': {
        'name': 'City of San Francisco',
        'url': 'https://dbiweb02.sfgov.org/dbipts/',
        'api_url': 'https://data.sfgov.org/resource/i98e-djp9.json',
        'api_available': True,
        'system': 'DBI',
    },
    'CA_SAN_DIEGO': {
        'name': 'City of San Diego',
        'url': 'https://www.sandiego.gov/development-services',
        'api_url': 'https://data.sandiego.gov/datasets/building-permits/',
        'api_available': True,
        'system': 'DSD',
    },
    'CA_SAN_JOSE': {
        'name': 'City of San Jose',
        'url': 'https://www.sanjoseca.gov/your-government/departments/planning-building-code-enforcement',
        'api_available': False,
    },
    # Texas
    'TX_HOUSTON': {
        'name': 'City of Houston',
        'url': 'https://www.houstonpermittingcenter.org/',
        'api_url': 'https://data.houstontx.gov/dataset/building-permits',
        'api_available': True,
        'system': 'HPC',
    },
    'TX_DALLAS': {
        'name': 'City of Dallas',
        'url': 'https://www.dallascityhall.com/departments/sustainabledevelopment/buildinginspection/',
        'api_available': False,
    },
    'TX_AUSTIN': {
        'name': 'City of Austin',
        'url': 'https://www.austintexas.gov/department/development-services',
        'api_url': 'https://data.austintexas.gov/resource/3syk-w9eu.json',
        'api_available': True,
        'system': 'AMANDA',
    },
    'TX_SAN_ANTONIO': {
        'name': 'City of San Antonio',
        'url': 'https://www.sanantonio.gov/DSD',
        'api_available': False,
    },
    # Florida
    'FL_MIAMI': {
        'name': 'City of Miami',
        'url': 'https://www.miamigov.com/Government/Departments/Building-Department',
        'api_available': False,
    },
    'FL_MIAMI_DADE': {
        'name': 'Miami-Dade County',
        'url': 'https://www.miamidade.gov/permits/',
        'api_available': False,
    },
    'FL_JACKSONVILLE': {
        'name': 'City of Jacksonville',
        'url': 'https://www.coj.net/departments/planning-and-development',
        'api_available': False,
    },
    # New York
    'NY_NEW_YORK': {
        'name': 'New York City',
        'url': 'https://www1.nyc.gov/site/buildings/index.page',
        'api_url': 'https://data.cityofnewyork.us/resource/ipu4-2vj7.json',
        'api_available': True,
        'system': 'DOB NOW',
    },
    # Illinois
    'IL_CHICAGO': {
        'name': 'City of Chicago',
        'url': 'https://www.chicago.gov/city/en/depts/bldgs.html',
        'api_url': 'https://data.cityofchicago.org/resource/ydr8-5enu.json',
        'api_available': True,
        'system': 'CDPH',
    },
    # Arizona
    'AZ_PHOENIX': {
        'name': 'City of Phoenix',
        'url': 'https://www.phoenix.gov/pdd',
        'api_url': 'https://www.phoenixopendata.com/dataset/building-permits',
        'api_available': True,
    },
    # Nevada
    'NV_LAS_VEGAS': {
        'name': 'City of Las Vegas',
        'url': 'https://www.lasvegasnevada.gov/Government/Departments/Building-and-Safety',
        'api_available': False,
    },
    'NV_CLARK_COUNTY': {
        'name': 'Clark County',
        'url': 'https://www.clarkcountynv.gov/government/departments/building_and_fire_prevention/',
        'api_available': False,
    },
    # Washington
    'WA_SEATTLE': {
        'name': 'City of Seattle',
        'url': 'https://www.seattle.gov/sdci',
        'api_url': 'https://data.seattle.gov/resource/mags-97de.json',
        'api_available': True,
        'system': 'SDCI',
    },
    # Colorado
    'CO_DENVER': {
        'name': 'City of Denver',
        'url': 'https://www.denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/Community-Planning-and-Development',
        'api_url': 'https://www.denvergov.org/opendata/dataset/building-permits',
        'api_available': True,
    },
    # Georgia
    'GA_ATLANTA': {
        'name': 'City of Atlanta',
        'url': 'https://www.atlantaga.gov/government/departments/city-planning',
        'api_available': False,
    },
    # Massachusetts
    'MA_BOSTON': {
        'name': 'City of Boston',
        'url': 'https://www.boston.gov/departments/inspectional-services',
        'api_url': 'https://data.boston.gov/dataset/building-permits',
        'api_available': True,
    },
}


class BuildingPermitsAPI:
    """
    Unified Building Permits API client.

    Provides access to building permit data from city and county systems.
    Supports major metropolitan areas with open data portals.

    Uses async/aiohttp for efficient multi-source queries.
    """

    CATEGORY = "building_permits"
    DISPLAY_NAME = "Building Permits"

    def __init__(self, timeout: int = 30):
        """
        Initialize building permits API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request = 0.0
        self._rate_limit_delay = 1.0
        self.jurisdiction_sources = JURISDICTION_PERMIT_SOURCES
        logger.info("BuildingPermitsAPI initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {
                'User-Agent': 'DataGod/1.0 (Permit Records Research)',
                'Accept': 'application/json,text/html',
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
        city: str,
        address: str,
        limit: int = 25
    ) -> List[BuildingPermit]:
        """
        Search building permits by property address.

        Args:
            state: Two-letter state code
            city: City name
            address: Street address
            limit: Maximum results

        Returns:
            List of matching BuildingPermit objects
        """
        state = state.upper()
        logger.info(f"Searching permits in {city}, {state} for address: {address}")

        await self._rate_limit()
        session = await self._get_session()

        jurisdiction_key = f"{state}_{city.upper().replace(' ', '_')}"

        if jurisdiction_key in self.jurisdiction_sources:
            return await self._search_jurisdiction(session, jurisdiction_key, address=address, limit=limit)

        # Try county-level if city not found
        county_key = f"{state}_{city.upper().replace(' ', '_').replace('CITY_OF_', '')}_COUNTY"
        if county_key in self.jurisdiction_sources:
            return await self._search_jurisdiction(session, county_key, address=address, limit=limit)

        return []

    async def search_by_permit_number(
        self,
        state: str,
        city: str,
        permit_number: str
    ) -> Optional[BuildingPermit]:
        """
        Get building permit by permit number.

        Args:
            state: Two-letter state code
            city: City name
            permit_number: Permit number

        Returns:
            BuildingPermit or None
        """
        state = state.upper()
        logger.info(f"Looking up permit {permit_number} in {city}, {state}")

        await self._rate_limit()
        session = await self._get_session()

        jurisdiction_key = f"{state}_{city.upper().replace(' ', '_')}"

        permits = await self._search_jurisdiction(session, jurisdiction_key, permit_number=permit_number, limit=1)
        return permits[0] if permits else None

    async def search_by_owner(
        self,
        state: str,
        city: str,
        owner_name: str,
        limit: int = 50
    ) -> List[BuildingPermit]:
        """
        Search building permits by property owner name.

        Args:
            state: Two-letter state code
            city: City name
            owner_name: Property owner name
            limit: Maximum results

        Returns:
            List of matching BuildingPermit objects
        """
        state = state.upper()
        logger.info(f"Searching permits in {city}, {state} for owner: {owner_name}")

        await self._rate_limit()
        session = await self._get_session()

        jurisdiction_key = f"{state}_{city.upper().replace(' ', '_')}"

        return await self._search_jurisdiction(session, jurisdiction_key, owner_name=owner_name, limit=limit)

    async def search_by_contractor(
        self,
        state: str,
        city: str,
        contractor_name: str,
        license_number: str = None,
        limit: int = 50
    ) -> List[BuildingPermit]:
        """
        Search building permits by contractor.

        Args:
            state: Two-letter state code
            city: City name
            contractor_name: Contractor name
            license_number: Contractor license number
            limit: Maximum results

        Returns:
            List of matching BuildingPermit objects
        """
        state = state.upper()
        logger.info(f"Searching permits in {city}, {state} for contractor: {contractor_name}")

        await self._rate_limit()
        session = await self._get_session()

        jurisdiction_key = f"{state}_{city.upper().replace(' ', '_')}"

        return await self._search_jurisdiction(session, jurisdiction_key, contractor_name=contractor_name, limit=limit)

    async def search_recent_permits(
        self,
        state: str,
        city: str,
        permit_type: PermitType = None,
        days_back: int = 30,
        limit: int = 100
    ) -> List[BuildingPermit]:
        """
        Search recent building permits.

        Args:
            state: Two-letter state code
            city: City name
            permit_type: Filter by permit type
            days_back: Number of days to search back
            limit: Maximum results

        Returns:
            List of BuildingPermit objects
        """
        state = state.upper()
        logger.info(f"Searching recent permits in {city}, {state}")

        await self._rate_limit()
        session = await self._get_session()

        from datetime import timedelta
        date_from = date.today() - timedelta(days=days_back)

        jurisdiction_key = f"{state}_{city.upper().replace(' ', '_')}"

        return await self._search_jurisdiction(session, jurisdiction_key, date_from=date_from, permit_type=permit_type, limit=limit)

    async def search_high_value_permits(
        self,
        state: str,
        city: str,
        min_value: float = 1000000,
        permit_type: PermitType = None,
        limit: int = 50
    ) -> List[BuildingPermit]:
        """
        Search high-value building permits.

        Args:
            state: Two-letter state code
            city: City name
            min_value: Minimum valuation threshold
            permit_type: Filter by permit type
            limit: Maximum results

        Returns:
            List of BuildingPermit objects
        """
        state = state.upper()
        logger.info(f"Searching high-value permits in {city}, {state}")

        await self._rate_limit()
        session = await self._get_session()

        jurisdiction_key = f"{state}_{city.upper().replace(' ', '_')}"

        permits = await self._search_jurisdiction(session, jurisdiction_key, permit_type=permit_type, limit=limit * 2)

        # Filter by value
        high_value = [p for p in permits if p.valuation and p.valuation >= min_value]
        return sorted(high_value, key=lambda x: x.valuation or 0, reverse=True)[:limit]

    # ========== Jurisdiction-Specific Searches ==========

    async def _search_jurisdiction(
        self,
        session: aiohttp.ClientSession,
        jurisdiction_key: str,
        address: str = None,
        permit_number: str = None,
        owner_name: str = None,
        contractor_name: str = None,
        permit_type: PermitType = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50
    ) -> List[BuildingPermit]:
        """Route to jurisdiction-specific search implementation."""

        if jurisdiction_key not in self.jurisdiction_sources:
            return []

        config = self.jurisdiction_sources[jurisdiction_key]
        state = jurisdiction_key.split('_')[0]

        # Route to API-based searches
        if config.get('api_available') and config.get('api_url'):
            return await self._search_open_data_api(
                session, jurisdiction_key, config,
                address, permit_number, owner_name, contractor_name,
                permit_type, date_from, date_to, limit
            )
        else:
            # Fall back to web scraping
            return await self._search_web(
                session, jurisdiction_key, config,
                address, permit_number, owner_name, limit
            )

    async def _search_open_data_api(
        self,
        session: aiohttp.ClientSession,
        jurisdiction_key: str,
        config: Dict[str, Any],
        address: str = None,
        permit_number: str = None,
        owner_name: str = None,
        contractor_name: str = None,
        permit_type: PermitType = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 50
    ) -> List[BuildingPermit]:
        """Search via Open Data API (Socrata/CKAN)."""
        api_url = config.get('api_url')
        if not api_url:
            return []

        state = jurisdiction_key.split('_')[0]
        jurisdiction_name = config.get('name', '')

        # Build Socrata/CKAN-style query
        params = {
            '$limit': limit,
            '$order': 'issue_date DESC' if 'issue_date' in api_url else ':id DESC',
        }

        # Build where clause
        where_clauses = []

        if address:
            # Different field names across systems
            address_fields = ['address', 'property_address', 'street_address', 'location', 'job_location']
            where_clauses.append(f"upper(address) LIKE upper('%{address}%')")

        if permit_number:
            permit_fields = ['permit_number', 'permit_no', 'job_number', 'application_number']
            where_clauses.append(f"permit_number = '{permit_number}'")

        if owner_name:
            where_clauses.append(f"upper(owner_name) LIKE upper('%{owner_name}%')")

        if date_from:
            where_clauses.append(f"issue_date >= '{date_from.isoformat()}'")

        if where_clauses:
            params['$where'] = ' AND '.join(where_clauses)

        permits = []

        try:
            async with session.get(api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    permits = self._parse_open_data_results(data, state, jurisdiction_name, limit)
        except Exception as e:
            logger.error(f"Open data API search error for {jurisdiction_key}: {e}")

        return permits

    def _parse_open_data_results(self, data: List[Dict[str, Any]], state: str, jurisdiction: str, limit: int) -> List[BuildingPermit]:
        """Parse Open Data API results."""
        permits = []

        for item in data[:limit]:
            try:
                # Try various field names used across different systems
                app_date = self._parse_date(
                    item.get('application_date') or item.get('filing_date') or
                    item.get('issued_date') or item.get('issue_date') or
                    item.get('permit_creation_date')
                )

                if not app_date:
                    app_date = date.today()

                permit = BuildingPermit(
                    permit_number=item.get('permit_number') or item.get('permit_no') or
                                  item.get('job_number') or item.get('application_number') or '',
                    state=state,
                    jurisdiction=jurisdiction,
                    application_date=app_date,
                    property_address=item.get('address') or item.get('property_address') or
                                     item.get('street_address') or item.get('job_location'),
                    property_city=item.get('city'),
                    property_zip=item.get('zip') or item.get('zip_code') or item.get('postal_code'),
                    parcel_number=item.get('parcel_number') or item.get('apn') or item.get('block_lot'),
                    permit_type=self._classify_permit_type(
                        item.get('permit_type') or item.get('work_type') or item.get('job_type') or ''
                    ),
                    permit_subtype=item.get('permit_subtype') or item.get('sub_type'),
                    permit_status=self._parse_status(
                        item.get('status') or item.get('permit_status') or item.get('job_status') or ''
                    ),
                    work_description=item.get('description') or item.get('work_description') or
                                     item.get('job_description'),
                    valuation=self._parse_float(
                        item.get('valuation') or item.get('estimated_cost') or
                        item.get('job_value') or item.get('total_cost')
                    ),
                    permit_fee=self._parse_float(item.get('permit_fee') or item.get('fee')),
                    total_fees=self._parse_float(item.get('total_fee') or item.get('total_fees')),
                    issue_date=self._parse_date(item.get('issue_date') or item.get('issued_date')),
                    expiration_date=self._parse_date(item.get('expiration_date') or item.get('expire_date')),
                    final_date=self._parse_date(item.get('final_date') or item.get('finaled_date')),
                    owner_name=item.get('owner_name') or item.get('property_owner'),
                    owner_address=item.get('owner_address'),
                    applicant_name=item.get('applicant_name') or item.get('applicant'),
                    source_system='Open Data Portal',
                    raw_data=item,
                    fetched_at=datetime.now()
                )

                # Extract contractor if available
                contractor_name = item.get('contractor_name') or item.get('contractor')
                if contractor_name:
                    permit.contractor = Contractor(
                        name=contractor_name,
                        license_number=item.get('contractor_license') or item.get('license_number'),
                        company_name=item.get('contractor_company'),
                        phone=item.get('contractor_phone'),
                    )

                permits.append(permit)

            except Exception as e:
                logger.warning(f"Error parsing permit record: {e}")

        return permits

    async def _search_web(
        self,
        session: aiohttp.ClientSession,
        jurisdiction_key: str,
        config: Dict[str, Any],
        address: str = None,
        permit_number: str = None,
        owner_name: str = None,
        limit: int = 50
    ) -> List[BuildingPermit]:
        """Search via web scraping."""
        url = config.get('url')
        if not url:
            return []

        state = jurisdiction_key.split('_')[0]
        jurisdiction_name = config.get('name', '')

        permits = []

        # Try common search endpoints
        search_paths = [
            '/search',
            '/permits/search',
            '/permit-search',
            '/Search.aspx',
            '/PermitSearch',
        ]

        for path in search_paths:
            try:
                search_url = url.rstrip('/') + path
                data = {}

                if address:
                    data['address'] = address
                elif permit_number:
                    data['permit_number'] = permit_number
                elif owner_name:
                    data['owner'] = owner_name

                async with session.post(search_url, data=data) as response:
                    if response.status == 200:
                        html = await response.text()
                        permits = self._parse_web_results(html, state, jurisdiction_name, limit)
                        if permits:
                            break
            except Exception as e:
                logger.debug(f"Web search failed for {jurisdiction_key} at {path}: {e}")
                continue

        return permits

    def _parse_web_results(self, html: str, state: str, jurisdiction: str, limit: int) -> List[BuildingPermit]:
        """Parse web scraping results."""
        permits = []
        soup = BeautifulSoup(html, 'html.parser')

        # Try to find permit listings in various formats
        rows = soup.select('table tr, .permit-row, .result-item, div[class*="permit"]')

        for row in rows[1:limit + 1]:  # Skip potential header
            cells = row.find_all(['td', 'div', 'span'])
            if len(cells) >= 3:
                try:
                    # Try to extract permit info
                    text_content = [c.get_text(strip=True) for c in cells]

                    permit_number = None
                    app_date = None
                    address = None

                    for text in text_content:
                        # Look for permit number patterns
                        if re.match(r'^[A-Z0-9]{4,}-', text) or re.match(r'^\d{4,}[A-Z]', text):
                            permit_number = text
                        # Try to parse as date
                        parsed_date = self._parse_date(text)
                        if parsed_date:
                            app_date = parsed_date
                        # Look for address patterns
                        if re.match(r'^\d+\s+\w+', text) and len(text) > 10:
                            address = text

                    if permit_number:
                        permit = BuildingPermit(
                            permit_number=permit_number,
                            state=state,
                            jurisdiction=jurisdiction,
                            application_date=app_date or date.today(),
                            property_address=address,
                            source_system='Web Scraper',
                            fetched_at=datetime.now()
                        )
                        permits.append(permit)

                except Exception:
                    continue

        return permits

    # ========== Utility Methods ==========

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date from various formats."""
        if not date_str:
            return None

        if isinstance(date_str, date):
            return date_str

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

    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse float from various formats."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.]', '', str(value))
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    def _parse_status(self, status_text: str) -> PermitStatus:
        """Parse permit status from text."""
        if not status_text:
            return PermitStatus.UNKNOWN

        status_lower = status_text.lower().strip()

        if 'issued' in status_lower:
            return PermitStatus.ISSUED
        elif 'approved' in status_lower:
            return PermitStatus.APPROVED
        elif 'active' in status_lower:
            return PermitStatus.ACTIVE
        elif 'final' in status_lower or 'closed' in status_lower:
            return PermitStatus.FINALED
        elif 'complete' in status_lower:
            return PermitStatus.COMPLETED
        elif 'pending' in status_lower:
            return PermitStatus.PENDING_REVIEW
        elif 'plan check' in status_lower or 'review' in status_lower:
            return PermitStatus.PLAN_CHECK
        elif 'applied' in status_lower or 'submitted' in status_lower:
            return PermitStatus.APPLIED
        elif 'expired' in status_lower:
            return PermitStatus.EXPIRED
        elif 'cancelled' in status_lower or 'canceled' in status_lower:
            return PermitStatus.CANCELLED
        elif 'denied' in status_lower:
            return PermitStatus.DENIED
        elif 'hold' in status_lower:
            return PermitStatus.HOLD
        elif 'inspection' in status_lower:
            if 'passed' in status_lower:
                return PermitStatus.INSPECTION_PASSED
            elif 'failed' in status_lower:
                return PermitStatus.INSPECTION_FAILED
            elif 'scheduled' in status_lower:
                return PermitStatus.INSPECTION_SCHEDULED
            return PermitStatus.INSPECTION_REQUIRED

        return PermitStatus.UNKNOWN

    def _classify_permit_type(self, type_text: str) -> PermitType:
        """Classify permit type from text."""
        if not type_text:
            return PermitType.OTHER

        type_lower = type_text.lower()

        if 'new construct' in type_lower or 'new build' in type_lower:
            return PermitType.NEW_CONSTRUCTION
        elif 'addition' in type_lower:
            return PermitType.ADDITION
        elif 'alteration' in type_lower:
            return PermitType.ALTERATION
        elif 'renov' in type_lower:
            return PermitType.RENOVATION
        elif 'remodel' in type_lower:
            return PermitType.REMODEL
        elif 'repair' in type_lower:
            return PermitType.REPAIR
        elif 'demol' in type_lower:
            return PermitType.DEMOLITION
        elif 'electric' in type_lower:
            return PermitType.ELECTRICAL
        elif 'plumb' in type_lower:
            return PermitType.PLUMBING
        elif 'mechan' in type_lower:
            return PermitType.MECHANICAL
        elif 'hvac' in type_lower or 'air condition' in type_lower or 'heating' in type_lower:
            return PermitType.HVAC
        elif 'roof' in type_lower:
            return PermitType.ROOFING
        elif 'solar' in type_lower or 'pv' in type_lower or 'photovoltaic' in type_lower:
            return PermitType.SOLAR
        elif 'pool' in type_lower or 'spa' in type_lower:
            return PermitType.POOL
        elif 'fence' in type_lower:
            return PermitType.FENCE
        elif 'deck' in type_lower or 'patio' in type_lower:
            return PermitType.DECK
        elif 'garage' in type_lower or 'carport' in type_lower:
            return PermitType.GARAGE
        elif 'adu' in type_lower or 'accessory' in type_lower or 'granny' in type_lower:
            return PermitType.ADU
        elif 'sign' in type_lower:
            return PermitType.SIGN
        elif 'grad' in type_lower or 'excav' in type_lower:
            return PermitType.GRADING
        elif 'fire alarm' in type_lower:
            return PermitType.FIRE_ALARM
        elif 'sprinkler' in type_lower:
            return PermitType.SPRINKLER
        elif 'foundation' in type_lower:
            return PermitType.FOUNDATION
        elif 'temporary' in type_lower:
            return PermitType.TEMPORARY
        elif 'certificate of occupancy' in type_lower or 'c of o' in type_lower or 'c/o' in type_lower:
            return PermitType.CERTIFICATE_OF_OCCUPANCY

        return PermitType.OTHER

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        jurisdictions_with_api = [j for j, c in self.jurisdiction_sources.items() if c.get('api_available')]

        return {
            'category': self.CATEGORY,
            'display_name': self.DISPLAY_NAME,
            'total_jurisdictions': len(self.jurisdiction_sources),
            'jurisdictions_with_api': len(jurisdictions_with_api),
            'permit_types': [t.value for t in PermitType],
            'permit_statuses': [s.value for s in PermitStatus],
        }


# ========== Synchronous Wrappers ==========

def search_permits_by_address(
    address: str,
    state: str,
    city: str,
    limit: int = 25
) -> List[Dict[str, Any]]:
    """
    Search building permits by address (synchronous wrapper).

    Args:
        address: Street address
        state: Two-letter state code
        city: City name
        limit: Maximum results

    Returns:
        List of BuildingPermit dictionaries
    """
    async def _search():
        async with BuildingPermitsAPI() as api:
            permits = await api.search_by_address(state, city, address, limit)
            return [p.to_dict() for p in permits]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def search_permits_by_owner(
    owner_name: str,
    state: str,
    city: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search building permits by owner name (synchronous wrapper).

    Args:
        owner_name: Property owner name
        state: Two-letter state code
        city: City name
        limit: Maximum results

    Returns:
        List of BuildingPermit dictionaries
    """
    async def _search():
        async with BuildingPermitsAPI() as api:
            permits = await api.search_by_owner(state, city, owner_name, limit)
            return [p.to_dict() for p in permits]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def search_permits_by_contractor(
    contractor_name: str,
    state: str,
    city: str,
    license_number: str = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search building permits by contractor (synchronous wrapper).

    Args:
        contractor_name: Contractor name
        state: Two-letter state code
        city: City name
        license_number: Contractor license number
        limit: Maximum results

    Returns:
        List of BuildingPermit dictionaries
    """
    async def _search():
        async with BuildingPermitsAPI() as api:
            permits = await api.search_by_contractor(state, city, contractor_name, license_number, limit)
            return [p.to_dict() for p in permits]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def get_permit(
    permit_number: str,
    state: str,
    city: str
) -> Optional[Dict[str, Any]]:
    """
    Get building permit by permit number (synchronous wrapper).

    Args:
        permit_number: Permit number
        state: Two-letter state code
        city: City name

    Returns:
        BuildingPermit dictionary or None
    """
    async def _get():
        async with BuildingPermitsAPI() as api:
            permit = await api.search_by_permit_number(state, city, permit_number)
            return permit.to_dict() if permit else None

    try:
        return asyncio.run(_get())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())


def get_recent_permits(
    state: str,
    city: str,
    permit_type: str = None,
    days_back: int = 30,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get recent building permits (synchronous wrapper).

    Args:
        state: Two-letter state code
        city: City name
        permit_type: Filter by permit type
        days_back: Number of days to search back
        limit: Maximum results

    Returns:
        List of BuildingPermit dictionaries
    """
    async def _search():
        async with BuildingPermitsAPI() as api:
            type_enum = None
            if permit_type:
                try:
                    type_enum = PermitType(permit_type)
                except ValueError:
                    pass
            permits = await api.search_recent_permits(state, city, type_enum, days_back, limit)
            return [p.to_dict() for p in permits]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def get_high_value_permits(
    state: str,
    city: str,
    min_value: float = 1000000,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get high-value building permits (synchronous wrapper).

    Args:
        state: Two-letter state code
        city: City name
        min_value: Minimum valuation
        limit: Maximum results

    Returns:
        List of BuildingPermit dictionaries
    """
    async def _search():
        async with BuildingPermitsAPI() as api:
            permits = await api.search_high_value_permits(state, city, min_value, None, limit)
            return [p.to_dict() for p in permits]

    try:
        return asyncio.run(_search())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_search())


def get_available_jurisdictions() -> Dict[str, List[str]]:
    """Get jurisdictions with building permit search support by state."""
    api = BuildingPermitsAPI()
    result = {}
    for jurisdiction_key, config in api.jurisdiction_sources.items():
        parts = jurisdiction_key.split('_', 1)
        if len(parts) == 2:
            state, city = parts
            if state not in result:
                result[state] = []
            result[state].append(config.get('name', city.replace('_', ' ').title()))
    return result
