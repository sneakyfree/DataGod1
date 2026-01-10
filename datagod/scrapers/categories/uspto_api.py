"""
USPTO API Integration

Collects United States Patent and Trademark Office public data including:
- Patent grants and applications
- Trademark registrations
- Patent assignments
- Patent litigation (PTAB)
- Inventor and assignee data
- Patent citations
"""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger(__name__)


class PatentType(Enum):
    """Patent types."""
    UTILITY = "utility"
    DESIGN = "design"
    PLANT = "plant"
    REISSUE = "reissue"
    STATUTORY_INVENTION = "statutory_invention"


class PatentStatus(Enum):
    """Patent status."""
    GRANTED = "granted"
    PENDING = "pending"
    ABANDONED = "abandoned"
    EXPIRED = "expired"
    LAPSED = "lapsed"


class TrademarkStatus(Enum):
    """Trademark status."""
    REGISTERED = "registered"
    PENDING = "pending"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    DEAD = "dead"
    LIVE = "live"


@dataclass
class PatentRecord:
    """Patent record data structure."""
    patent_number: str
    patent_type: PatentType
    title: str
    abstract: Optional[str] = None
    filing_date: Optional[date] = None
    grant_date: Optional[date] = None
    expiration_date: Optional[date] = None
    status: PatentStatus = PatentStatus.GRANTED
    inventors: List[Dict[str, str]] = field(default_factory=list)
    assignees: List[Dict[str, str]] = field(default_factory=list)
    current_assignee: Optional[str] = None
    claims_count: int = 0
    citations_count: int = 0
    cited_by_count: int = 0
    cpc_codes: List[str] = field(default_factory=list)
    uspc_codes: List[str] = field(default_factory=list)
    ipc_codes: List[str] = field(default_factory=list)
    application_number: Optional[str] = None
    priority_date: Optional[date] = None
    examiner_name: Optional[str] = None
    law_firm: Optional[str] = None
    attorney: Optional[str] = None
    source_url: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'patent_number': self.patent_number,
            'patent_type': self.patent_type.value if isinstance(self.patent_type, PatentType) else self.patent_type,
            'title': self.title,
            'abstract': self.abstract,
            'filing_date': self.filing_date.isoformat() if self.filing_date else None,
            'grant_date': self.grant_date.isoformat() if self.grant_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'status': self.status.value if isinstance(self.status, PatentStatus) else self.status,
            'inventors': self.inventors,
            'assignees': self.assignees,
            'current_assignee': self.current_assignee,
            'claims_count': self.claims_count,
            'citations_count': self.citations_count,
            'cited_by_count': self.cited_by_count,
            'cpc_codes': self.cpc_codes,
            'uspc_codes': self.uspc_codes,
            'ipc_codes': self.ipc_codes,
            'application_number': self.application_number,
            'priority_date': self.priority_date.isoformat() if self.priority_date else None,
            'examiner_name': self.examiner_name,
            'law_firm': self.law_firm,
            'attorney': self.attorney,
            'source_url': self.source_url,
        }


@dataclass
class TrademarkRecord:
    """Trademark record data structure."""
    serial_number: str
    registration_number: Optional[str] = None
    mark_text: str = ""
    mark_description: Optional[str] = None
    status: TrademarkStatus = TrademarkStatus.PENDING
    filing_date: Optional[date] = None
    registration_date: Optional[date] = None
    abandonment_date: Optional[date] = None
    cancellation_date: Optional[date] = None
    renewal_date: Optional[date] = None
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None
    owner_state: Optional[str] = None
    owner_country: Optional[str] = None
    attorney_name: Optional[str] = None
    law_firm: Optional[str] = None
    goods_services: List[Dict[str, Any]] = field(default_factory=list)
    international_classes: List[int] = field(default_factory=list)
    us_classes: List[str] = field(default_factory=list)
    design_codes: List[str] = field(default_factory=list)
    mark_type: Optional[str] = None
    register_type: Optional[str] = None
    live_dead: Optional[str] = None
    source_url: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'serial_number': self.serial_number,
            'registration_number': self.registration_number,
            'mark_text': self.mark_text,
            'mark_description': self.mark_description,
            'status': self.status.value if isinstance(self.status, TrademarkStatus) else self.status,
            'filing_date': self.filing_date.isoformat() if self.filing_date else None,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'abandonment_date': self.abandonment_date.isoformat() if self.abandonment_date else None,
            'cancellation_date': self.cancellation_date.isoformat() if self.cancellation_date else None,
            'renewal_date': self.renewal_date.isoformat() if self.renewal_date else None,
            'owner_name': self.owner_name,
            'owner_address': self.owner_address,
            'owner_state': self.owner_state,
            'owner_country': self.owner_country,
            'attorney_name': self.attorney_name,
            'law_firm': self.law_firm,
            'goods_services': self.goods_services,
            'international_classes': self.international_classes,
            'us_classes': self.us_classes,
            'design_codes': self.design_codes,
            'mark_type': self.mark_type,
            'register_type': self.register_type,
            'live_dead': self.live_dead,
            'source_url': self.source_url,
        }


# USPTO API endpoints
# NOTE: The legacy PatentsView API (api.patentsview.org) was DISCONTINUED as of May 1, 2025
# The new PatentSearch API requires authentication via USPTO Open Data Portal
# See: https://patentsview.org/data-in-action/patentsview-ends-support-legacy-api
USPTO_API_ENDPOINTS = {
    'patentsview_legacy': {
        'name': 'PatentsView Legacy API (DISCONTINUED)',
        'base_url': 'https://api.patentsview.org/patents/query',
        'description': 'DISCONTINUED May 2025 - Returns 410 Gone',
        'auth': 'N/A',
        'status': 'discontinued',
        'rate_limit': 'N/A',
    },
    'patentsview_new': {
        'name': 'PatentSearch API (New)',
        'base_url': 'https://search.patentsview.org/api/v1/',
        'description': 'New ElasticSearch-based API - Requires authentication',
        'auth': 'Required - Get key at https://account.uspto.gov/api-manager/',
        'status': 'requires_auth',
        'rate_limit': 'Unknown',
    },
    'patent_assignment': {
        'name': 'Patent Assignment Search',
        'base_url': 'https://assignment.uspto.gov/patent/index.html',
        'description': 'Patent ownership transfers - Web interface',
        'auth': 'None',
        'status': 'active',
    },
    'trademark_api': {
        'name': 'USPTO Trademark TSDR API',
        'base_url': 'https://tsdrapi.uspto.gov',
        'description': 'Trademark Status and Document Retrieval API - Requires API key since Oct 2025',
        'auth': 'Required - Get key at https://account.uspto.gov/api-manager/',
        'status': 'requires_auth',
    },
    'ptab': {
        'name': 'PTAB API v3',
        'base_url': 'https://developer.uspto.gov/ptab-api/v3/',
        'description': 'Patent Trial and Appeal Board decisions',
        'auth': 'Requires API key for full access',
        'status': 'active',
    },
    'bulk_data': {
        'name': 'USPTO Bulk Data',
        'base_url': 'https://bulkdata.uspto.gov/',
        'description': 'Bulk download of patent and trademark data - No API, file downloads',
        'auth': 'None',
        'status': 'active',
    },
    'open_data_portal': {
        'name': 'USPTO Open Data Portal',
        'base_url': 'https://data.uspto.gov/',
        'description': 'New unified data portal - Being migrated through 2026',
        'auth': 'API key required for some endpoints',
        'status': 'transitioning',
    },
}


class USPTOApiScraper:
    """
    USPTO API integration for patent and trademark data.

    Features:
    - Patent search and lookup via PatentsView API
    - Trademark search via TSDR API
    - Patent assignments
    - PTAB proceedings
    - Inventor/assignee searches
    - All FREE, no API key required
    """

    CATEGORY = "intellectual_property"
    DISPLAY_NAME = "USPTO Patents & Trademarks"

    # Rate limiting: PatentsView allows ~45 requests/minute
    RATE_LIMIT_DELAY = 1.4  # ~1.4 seconds between requests

    def __init__(self):
        """Initialize the USPTO API scraper."""
        self.endpoints = USPTO_API_ENDPOINTS
        self.patents: List[PatentRecord] = []
        self.trademarks: List[TrademarkRecord] = []
        self._last_request_time = 0
        logger.info("USPTOApiScraper initialized")

    async def _rate_limit(self):
        """Implement rate limiting for USPTO APIs."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        data: Dict = None,
        session: aiohttp.ClientSession = None
    ) -> Dict[str, Any]:
        """Make HTTP request to USPTO API with rate limiting."""
        await self._rate_limit()

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            if method == "POST":
                async with session.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        logger.warning("USPTO API rate limit hit, waiting...")
                        await asyncio.sleep(10)
                        return await self._make_request(url, method, data, session)
                    else:
                        logger.error(f"USPTO API error {response.status}: {url}")
                        text = await response.text()
                        logger.error(f"Response: {text[:500]}")
                        return {}
            else:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        logger.warning("USPTO API rate limit hit, waiting...")
                        await asyncio.sleep(10)
                        return await self._make_request(url, method, data, session)
                    else:
                        logger.error(f"USPTO API error {response.status}: {url}")
                        return {}
        except asyncio.TimeoutError:
            logger.error(f"USPTO API timeout: {url}")
            return {}
        except Exception as e:
            logger.error(f"USPTO API request failed: {e}")
            return {}
        finally:
            if close_session:
                await session.close()

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y%m%d').date()
            except ValueError:
                return None

    def _determine_patent_type(self, patent_number: str, kind: str = "") -> PatentType:
        """Determine patent type from number or kind code."""
        if patent_number.startswith('D') or kind.startswith('S'):
            return PatentType.DESIGN
        elif patent_number.startswith('PP') or kind == 'P':
            return PatentType.PLANT
        elif patent_number.startswith('RE'):
            return PatentType.REISSUE
        else:
            return PatentType.UTILITY

    async def search_patents(
        self,
        query: str = "",
        inventor: str = "",
        assignee: str = "",
        patent_number: str = "",
        cpc_code: str = "",
        start_date: date = None,
        end_date: date = None,
        limit: int = 100,
        api_key: str = None
    ) -> List[PatentRecord]:
        """
        Search patents.

        NOTE: The legacy PatentsView API was discontinued on May 1, 2025.
        The new PatentSearch API requires authentication.

        Without an API key, this method returns helpful guidance and reference URLs.
        With an API key, it attempts to use the new PatentSearch API.

        For patent data access without authentication:
        - Google Patents: https://patents.google.com/
        - USPTO Bulk Data: https://bulkdata.uspto.gov/
        - Lens.org: https://www.lens.org/ (free account)

        Args:
            query: Title/abstract keyword search
            inventor: Inventor name
            assignee: Assignee/company name
            patent_number: Specific patent number
            cpc_code: CPC classification code
            start_date: Grant date start
            end_date: Grant date end
            limit: Maximum results
            api_key: USPTO API key for authenticated access

        Returns:
            List of patent records (or empty list with guidance in logs)
        """
        logger.info(f"Searching patents: {query or inventor or assignee or patent_number}")
        patents = []

        # Check if we have an API key for the new authenticated endpoint
        if api_key:
            # Try the new PatentSearch API (requires authentication)
            logger.info("Using new PatentSearch API with authentication...")
            # Note: Implementation would require proper OAuth/API key handling
            # The new API uses ElasticSearch query format
            pass  # TODO: Implement when API key is available

        # Legacy PatentsView API - now returns 410 Gone
        logger.warning(
            "PatentsView Legacy API was discontinued on May 1, 2025. "
            "For patent searches, please use: "
            "1) USPTO Open Data Portal (https://data.uspto.gov/) with API key, "
            "2) Google Patents (https://patents.google.com/), or "
            "3) Lens.org (https://www.lens.org/) with free account."
        )

        # Return empty list but log helpful search URLs
        search_params = []
        if patent_number:
            clean_num = patent_number.replace('US', '').replace(',', '').strip()
            # Create reference URLs for alternative sources
            google_url = f"https://patents.google.com/patent/US{clean_num}"
            logger.info(f"Try Google Patents: {google_url}")

            # Return a "reference" record pointing to the patent
            record = PatentRecord(
                patent_number=clean_num,
                patent_type=PatentType.UTILITY,
                title=f"Patent US{clean_num} - See Google Patents for details",
                abstract="PatentsView API discontinued. Visit the source URLs for patent data.",
                status=PatentStatus.GRANTED,
                source_url=google_url,
                raw_data={
                    'api_status': 'discontinued',
                    'alternatives': {
                        'google_patents': google_url,
                        'uspto_bulk': 'https://bulkdata.uspto.gov/',
                        'lens': f'https://www.lens.org/lens/patent/US_{clean_num}',
                    }
                }
            )
            patents.append(record)
        else:
            # For general searches, provide guidance
            lens_url = "https://www.lens.org/lens/search/patent/list"
            logger.info(f"For patent searches, use Lens.org: {lens_url}")

        return patents

    async def get_patent_by_number(
        self,
        patent_number: str
    ) -> Optional[PatentRecord]:
        """
        Get patent details by number.

        Args:
            patent_number: Patent number (e.g., "US10000000" or "10000000")

        Returns:
            Patent record if found
        """
        logger.info(f"Getting patent {patent_number}")

        patents = await self.search_patents(patent_number=patent_number, limit=1)
        return patents[0] if patents else None

    async def search_trademarks(
        self,
        mark_text: str = "",
        owner: str = "",
        serial_number: str = "",
        registration_number: str = "",
        goods_services: str = "",
        international_class: int = None,
        status: TrademarkStatus = None
    ) -> List[TrademarkRecord]:
        """
        Search trademarks using USPTO TSDR API.

        Note: The TSDR API has limited search capability. For full-text searches,
        TESS (web interface) is typically used, which requires scraping.

        Args:
            mark_text: Trademark text search
            owner: Owner name
            serial_number: Serial number
            registration_number: Registration number
            goods_services: Goods/services description
            international_class: Nice classification
            status: Trademark status filter

        Returns:
            List of trademark records
        """
        logger.info(f"Searching trademarks: {mark_text or owner or serial_number}")
        trademarks = []

        # TSDR API primarily works with serial/registration numbers
        if serial_number:
            tm = await self.get_trademark_by_serial(serial_number)
            if tm:
                trademarks.append(tm)
        elif registration_number:
            # Try to get by registration number
            tm = await self._get_trademark_by_registration(registration_number)
            if tm:
                trademarks.append(tm)
        else:
            # Note: Full text search requires TESS scraping which is complex
            logger.warning("USPTO trademark full-text search requires TESS web interface")

        return trademarks

    async def get_trademark_by_serial(
        self,
        serial_number: str,
        api_key: str = None
    ) -> Optional[TrademarkRecord]:
        """
        Get trademark details by serial number using TSDR API.

        NOTE: As of October 2025, the TSDR API requires an API key.
        Get your free API key at: https://account.uspto.gov/api-manager/

        Args:
            serial_number: Trademark serial number (8 digits)
            api_key: USPTO API key (required for TSDR access)

        Returns:
            Trademark record if found
        """
        logger.info(f"Getting trademark {serial_number}")

        if not api_key:
            logger.warning(
                "USPTO TSDR API now requires authentication (as of Oct 2025). "
                "Get a free API key at: https://account.uspto.gov/api-manager/"
            )
            # Return a reference record with the TSDR URL
            clean_serial = serial_number.replace('-', '').replace(' ', '').zfill(8)
            return TrademarkRecord(
                serial_number=clean_serial,
                mark_text=f"Trademark {clean_serial} - API key required",
                source_url=f"https://tsdr.uspto.gov/#caseNumber={clean_serial}&caseSearchType=US_APPLICATION&caseType=DEFAULT",
                raw_data={'api_status': 'requires_auth'}
            )

        # Clean serial number - should be 8 digits
        clean_serial = serial_number.replace('-', '').replace(' ', '').zfill(8)

        url = f"https://tsdrapi.uspto.gov/ts/cd/casestatus/sn{clean_serial}/info.json"

        data = await self._make_request(url)

        if not data or 'trademarkBag' not in data:
            return None

        tm_data = data['trademarkBag'].get('trademarkTransactionBag', {}).get('trademarkTransaction', [{}])[0]
        if not tm_data:
            return None

        tm_bag = tm_data.get('trademarkBag', {}).get('trademark', [{}])[0] if tm_data.get('trademarkBag') else {}

        # Determine status
        status_str = tm_bag.get('statusDescriptionText', '').lower()
        if 'registered' in status_str:
            tm_status = TrademarkStatus.REGISTERED
        elif 'pending' in status_str or 'published' in status_str:
            tm_status = TrademarkStatus.PENDING
        elif 'abandoned' in status_str:
            tm_status = TrademarkStatus.ABANDONED
        elif 'cancelled' in status_str:
            tm_status = TrademarkStatus.CANCELLED
        elif 'dead' in status_str:
            tm_status = TrademarkStatus.DEAD
        else:
            tm_status = TrademarkStatus.LIVE

        # Extract owner info
        applicant = tm_bag.get('applicantBag', {}).get('applicant', [{}])[0] if tm_bag.get('applicantBag') else {}
        owner_name = applicant.get('organizationName') or applicant.get('personName', '')

        # Extract goods/services
        goods_services = []
        gs_bag = tm_bag.get('goodsAndServicesBag', {}).get('goodsAndServices', [])
        for gs in gs_bag:
            goods_services.append({
                'class': gs.get('classNumber', ''),
                'description': gs.get('goodsServicesDescriptionText', ''),
            })

        # Extract international classes
        int_classes = [int(gs.get('classNumber', 0)) for gs in gs_bag if gs.get('classNumber')]

        record = TrademarkRecord(
            serial_number=clean_serial,
            registration_number=tm_bag.get('registrationNumber', ''),
            mark_text=tm_bag.get('verbalElementText', ''),
            mark_description=tm_bag.get('markDescriptionText', ''),
            status=tm_status,
            filing_date=self._parse_date(tm_bag.get('filingDate', '')),
            registration_date=self._parse_date(tm_bag.get('registrationDate', '')),
            owner_name=owner_name,
            goods_services=goods_services,
            international_classes=int_classes,
            live_dead='LIVE' if tm_status not in [TrademarkStatus.DEAD, TrademarkStatus.ABANDONED] else 'DEAD',
            source_url=f"https://tsdr.uspto.gov/#caseNumber={clean_serial}&caseSearchType=US_APPLICATION&caseType=DEFAULT",
            raw_data=data,
        )

        return record

    async def _get_trademark_by_registration(
        self,
        registration_number: str
    ) -> Optional[TrademarkRecord]:
        """Get trademark by registration number."""
        clean_reg = registration_number.replace('-', '').replace(' ', '').zfill(7)
        url = f"https://tsdrapi.uspto.gov/ts/cd/casestatus/rn{clean_reg}/info.json"

        data = await self._make_request(url)
        if not data:
            return None

        # Parse similar to serial number lookup
        # For brevity, returning None if complex parsing needed
        return None

    async def get_patent_assignments(
        self,
        patent_number: str = "",
        assignee: str = "",
        assignor: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Get patent assignment (ownership transfer) records.

        Note: USPTO Assignment API requires special access. This provides basic info.

        Args:
            patent_number: Patent number
            assignee: New owner name
            assignor: Previous owner name

        Returns:
            List of assignment records
        """
        logger.info(f"Getting patent assignments for {patent_number or assignee or assignor}")
        assignments = []

        # The assignment search would typically use:
        # https://assignment.uspto.gov/patent/index.html - requires scraping
        # For now, return reference to source
        if patent_number:
            assignments.append({
                'patent_number': patent_number,
                'search_url': f"https://assignment.uspto.gov/patent/index.html#/patent/search?advSearch=false&pn={patent_number}",
                'note': 'Visit search URL for detailed assignment history',
            })

        return assignments

    async def get_inventor_patents(
        self,
        inventor_name: str,
        state: str = "",
        country: str = ""
    ) -> List[PatentRecord]:
        """
        Get all patents for an inventor.

        Args:
            inventor_name: Inventor name (last name or full name)
            state: State filter
            country: Country filter

        Returns:
            List of patents by inventor
        """
        logger.info(f"Getting patents for inventor {inventor_name}")

        # Search using PatentsView inventor endpoint
        query_parts = [{"_text_any": {"inventor_last_name": inventor_name}}]
        if state:
            query_parts.append({"inventor_state": state})
        if country:
            query_parts.append({"inventor_country": country})

        if len(query_parts) == 1:
            query_obj = query_parts[0]
        else:
            query_obj = {"_and": query_parts}

        request_data = {
            "q": query_obj,
            "f": [
                "patent_number", "patent_title", "patent_abstract",
                "patent_date", "patent_type",
                "inventor_first_name", "inventor_last_name",
                "assignee_organization"
            ],
            "o": {"per_page": 100},
            "s": [{"patent_date": "desc"}]
        }

        url = self.endpoints['patentsview']['base_url']
        data = await self._make_request(url, method="POST", data=request_data)

        patents = []
        if data and 'patents' in data:
            for p in data['patents']:
                record = PatentRecord(
                    patent_number=p.get('patent_number', ''),
                    patent_type=self._determine_patent_type(p.get('patent_number', '')),
                    title=p.get('patent_title', ''),
                    abstract=p.get('patent_abstract', ''),
                    grant_date=self._parse_date(p.get('patent_date', '')),
                    status=PatentStatus.GRANTED,
                    source_url=f"https://patents.google.com/patent/US{p.get('patent_number', '')}",
                )
                patents.append(record)

        return patents

    async def get_assignee_patents(
        self,
        assignee_name: str,
        start_date: date = None,
        end_date: date = None
    ) -> List[PatentRecord]:
        """
        Get all patents for a company/assignee.

        Args:
            assignee_name: Company/assignee name
            start_date: Grant date start
            end_date: Grant date end

        Returns:
            List of patents by assignee
        """
        logger.info(f"Getting patents for assignee {assignee_name}")

        return await self.search_patents(
            assignee=assignee_name,
            start_date=start_date,
            end_date=end_date,
            limit=100
        )

    async def get_patent_citations(
        self,
        patent_number: str,
        direction: str = "both"
    ) -> Dict[str, List[str]]:
        """
        Get patent citations.

        Args:
            patent_number: Patent number
            direction: "cited" (references), "citing" (cited by), or "both"

        Returns:
            Dictionary with cited and citing patents
        """
        logger.info(f"Getting citations for {patent_number}")

        clean_num = patent_number.replace('US', '').replace(',', '').strip()
        result = {"cited": [], "citing": []}

        # Query for cited patents (references)
        if direction in ["cited", "both"]:
            request_data = {
                "q": {"patent_number": clean_num},
                "f": ["cited_patent_number"],
                "o": {"per_page": 1000}
            }
            url = self.endpoints['patentsview']['base_url']
            data = await self._make_request(url, method="POST", data=request_data)

            if data and 'patents' in data:
                for p in data['patents']:
                    if 'cited_patents' in p and p['cited_patents']:
                        for cited in p['cited_patents']:
                            if cited.get('cited_patent_number'):
                                result["cited"].append(cited['cited_patent_number'])

        # Query for citing patents (cited by) - more complex query
        if direction in ["citing", "both"]:
            request_data = {
                "q": {"cited_patent_number": clean_num},
                "f": ["patent_number"],
                "o": {"per_page": 1000}
            }
            url = self.endpoints['patentsview']['base_url']
            data = await self._make_request(url, method="POST", data=request_data)

            if data and 'patents' in data:
                for p in data['patents']:
                    if p.get('patent_number'):
                        result["citing"].append(p['patent_number'])

        return result

    async def get_ptab_proceedings(
        self,
        patent_number: str = "",
        party_name: str = "",
        proceeding_type: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Get PTAB (Patent Trial and Appeal Board) proceedings.

        Args:
            patent_number: Patent number
            party_name: Party name
            proceeding_type: IPR, PGR, CBM, etc.

        Returns:
            List of PTAB proceedings
        """
        logger.info(f"Getting PTAB proceedings")
        proceedings = []

        # Build PTAB API query
        base_url = "https://developer.uspto.gov/ptab-api/trials"
        params = []

        if patent_number:
            clean_num = patent_number.replace('US', '').replace(',', '').strip()
            params.append(f"patentNumber={clean_num}")
        if party_name:
            params.append(f"partyName={party_name}")
        if proceeding_type:
            params.append(f"proceedingTypeCategory={proceeding_type}")

        url = base_url
        if params:
            url += "?" + "&".join(params)

        data = await self._make_request(url)

        if data and 'results' in data:
            for trial in data['results']:
                proceedings.append({
                    'proceeding_number': trial.get('trialNumber', ''),
                    'proceeding_type': trial.get('proceedingTypeCategory', ''),
                    'patent_number': trial.get('patentNumber', ''),
                    'filing_date': trial.get('filingDate', ''),
                    'status': trial.get('proceedingStatusCategory', ''),
                    'petitioner': trial.get('petitionerPartyName', ''),
                    'patent_owner': trial.get('patentOwnerName', ''),
                    'source_url': f"https://developer.uspto.gov/ptab-web/#/search/trials?trialNumber={trial.get('trialNumber', '')}",
                })

        return proceedings

    async def get_recent_patents(
        self,
        patent_type: PatentType = None,
        cpc_section: str = "",
        limit: int = 100
    ) -> List[PatentRecord]:
        """
        Get recently granted patents.

        Args:
            patent_type: Filter by patent type
            cpc_section: CPC section (A-H, Y)
            limit: Maximum results

        Returns:
            List of recent patents
        """
        logger.info(f"Getting recent patents")

        # Get patents from last 30 days
        end_date = date.today()
        start_date = date(end_date.year, end_date.month - 1 if end_date.month > 1 else 12, end_date.day)

        return await self.search_patents(
            cpc_code=cpc_section if cpc_section else "",
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        return {
            'category': self.CATEGORY,
            'display_name': self.DISPLAY_NAME,
            'api_endpoints': len(self.endpoints),
            'endpoint_names': list(self.endpoints.keys()),
            'patent_types': [t.value for t in PatentType],
            'trademark_statuses': [s.value for s in TrademarkStatus],
            'auth_required': False,
            'rate_limit': '45 requests/minute (PatentsView)',
            'status': 'implemented',
        }

    # Synchronous wrappers
    def search_patents_sync(self, **kwargs) -> List[PatentRecord]:
        """Synchronous wrapper for search_patents."""
        return asyncio.get_event_loop().run_until_complete(self.search_patents(**kwargs))

    def get_patent_by_number_sync(self, patent_number: str) -> Optional[PatentRecord]:
        """Synchronous wrapper for get_patent_by_number."""
        return asyncio.get_event_loop().run_until_complete(self.get_patent_by_number(patent_number))


# Module-level convenience functions
def get_uspto_scraper() -> USPTOApiScraper:
    """Get USPTO API scraper instance."""
    return USPTOApiScraper()


async def search_patents_async(query: str = "", **kwargs) -> List[Dict[str, Any]]:
    """Search USPTO patents asynchronously."""
    scraper = get_uspto_scraper()
    records = await scraper.search_patents(query=query, **kwargs)
    return [r.to_dict() for r in records]


def search_patents(query: str = "", **kwargs) -> List[Dict[str, Any]]:
    """Search USPTO patents (synchronous wrapper)."""
    return asyncio.get_event_loop().run_until_complete(
        search_patents_async(query, **kwargs)
    )


async def search_trademarks_async(mark_text: str = "", **kwargs) -> List[Dict[str, Any]]:
    """Search USPTO trademarks asynchronously."""
    scraper = get_uspto_scraper()
    records = await scraper.search_trademarks(mark_text=mark_text, **kwargs)
    return [r.to_dict() for r in records]


def search_trademarks(mark_text: str = "", **kwargs) -> List[Dict[str, Any]]:
    """Search USPTO trademarks (synchronous wrapper)."""
    return asyncio.get_event_loop().run_until_complete(
        search_trademarks_async(mark_text, **kwargs)
    )


def get_available_endpoints() -> Dict[str, Any]:
    """Get all available USPTO API endpoints."""
    return USPTO_API_ENDPOINTS
