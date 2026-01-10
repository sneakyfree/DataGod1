"""
SEC API Integration

Collects Securities and Exchange Commission public data including:
- Corporate filings (10-K, 10-Q, 8-K)
- Insider trading (Form 4)
- Beneficial ownership (13F, 13D, 13G)
- IPO filings (S-1)
- Company facts and submissions
- EDGAR full-text search
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger(__name__)


class FilingType(Enum):
    """SEC filing types."""
    FORM_10K = "10-K"  # Annual report
    FORM_10Q = "10-Q"  # Quarterly report
    FORM_8K = "8-K"  # Current report
    FORM_4 = "4"  # Insider trading
    FORM_13F = "13F-HR"  # Institutional holdings
    FORM_13D = "SC 13D"  # Beneficial ownership >5%
    FORM_13G = "SC 13G"  # Passive beneficial ownership
    FORM_S1 = "S-1"  # IPO registration
    FORM_DEF14A = "DEF 14A"  # Proxy statement
    FORM_20F = "20-F"  # Foreign private issuer annual
    FORM_6K = "6-K"  # Foreign private issuer current
    FORM_N1A = "N-1A"  # Mutual fund prospectus
    FORM_ADV = "ADV"  # Investment adviser registration


class FilingStatus(Enum):
    """Filing status."""
    ACCEPTED = "accepted"
    PENDING = "pending"
    AMENDED = "amended"
    WITHDRAWN = "withdrawn"


@dataclass
class SECFiling:
    """SEC filing record data structure."""
    accession_number: str
    cik: str
    company_name: str
    filing_type: FilingType
    filing_date: date
    accepted_date: Optional[datetime] = None
    document_count: int = 0
    primary_document: Optional[str] = None
    primary_doc_description: Optional[str] = None
    form_description: Optional[str] = None
    items: List[str] = field(default_factory=list)
    size: Optional[int] = None
    is_xbrl: bool = False
    is_inline_xbrl: bool = False
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    sic_code: Optional[str] = None
    sic_description: Optional[str] = None
    state_of_incorporation: Optional[str] = None
    fiscal_year_end: Optional[str] = None
    filing_url: str = ""
    source_url: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'accession_number': self.accession_number,
            'cik': self.cik,
            'company_name': self.company_name,
            'filing_type': self.filing_type.value if isinstance(self.filing_type, FilingType) else self.filing_type,
            'filing_date': self.filing_date.isoformat() if self.filing_date else None,
            'accepted_date': self.accepted_date.isoformat() if self.accepted_date else None,
            'document_count': self.document_count,
            'primary_document': self.primary_document,
            'primary_doc_description': self.primary_doc_description,
            'form_description': self.form_description,
            'items': self.items,
            'size': self.size,
            'is_xbrl': self.is_xbrl,
            'is_inline_xbrl': self.is_inline_xbrl,
            'ticker': self.ticker,
            'exchange': self.exchange,
            'sic_code': self.sic_code,
            'sic_description': self.sic_description,
            'state_of_incorporation': self.state_of_incorporation,
            'fiscal_year_end': self.fiscal_year_end,
            'filing_url': self.filing_url,
            'source_url': self.source_url,
        }


@dataclass
class InsiderTransaction:
    """Insider trading transaction (Form 4)."""
    accession_number: str
    cik: str
    company_name: str
    company_cik: str
    insider_name: str
    insider_title: Optional[str] = None
    is_director: bool = False
    is_officer: bool = False
    is_ten_percent_owner: bool = False
    transaction_date: Optional[date] = None
    transaction_type: Optional[str] = None  # P=Purchase, S=Sale, etc.
    shares: Optional[float] = None
    price_per_share: Optional[float] = None
    total_value: Optional[float] = None
    shares_owned_after: Optional[float] = None
    direct_or_indirect: Optional[str] = None
    filing_date: Optional[date] = None
    source_url: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'accession_number': self.accession_number,
            'cik': self.cik,
            'company_name': self.company_name,
            'company_cik': self.company_cik,
            'insider_name': self.insider_name,
            'insider_title': self.insider_title,
            'is_director': self.is_director,
            'is_officer': self.is_officer,
            'is_ten_percent_owner': self.is_ten_percent_owner,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'transaction_type': self.transaction_type,
            'shares': self.shares,
            'price_per_share': self.price_per_share,
            'total_value': self.total_value,
            'shares_owned_after': self.shares_owned_after,
            'direct_or_indirect': self.direct_or_indirect,
            'filing_date': self.filing_date.isoformat() if self.filing_date else None,
            'source_url': self.source_url,
        }


# SEC API endpoints (all free, no auth required)
SEC_API_ENDPOINTS = {
    'submissions': {
        'name': 'Company Submissions',
        'base_url': 'https://data.sec.gov/submissions/',
        'description': 'Get all filings for a company by CIK',
        'format': 'CIK{cik}.json',
    },
    'company_facts': {
        'name': 'Company Facts',
        'base_url': 'https://data.sec.gov/api/xbrl/companyfacts/',
        'description': 'XBRL company financial facts',
        'format': 'CIK{cik}.json',
    },
    'company_concept': {
        'name': 'Company Concept',
        'base_url': 'https://data.sec.gov/api/xbrl/companyconcept/',
        'description': 'Single XBRL concept for a company',
        'format': 'CIK{cik}/{taxonomy}/{concept}.json',
    },
    'frames': {
        'name': 'XBRL Frames',
        'base_url': 'https://data.sec.gov/api/xbrl/frames/',
        'description': 'Cross-company XBRL data for a concept/period',
        'format': '{taxonomy}/{concept}/{unit}/{period}.json',
    },
    'full_text_search': {
        'name': 'Full-Text Search',
        'base_url': 'https://efts.sec.gov/LATEST/search-index',
        'description': 'Search filing documents',
    },
    'edgar_archives': {
        'name': 'EDGAR Archives',
        'base_url': 'https://www.sec.gov/cgi-bin/browse-edgar',
        'description': 'Direct EDGAR filing access',
    },
    'company_tickers': {
        'name': 'Company Tickers',
        'base_url': 'https://www.sec.gov/files/company_tickers.json',
        'description': 'All company CIK to ticker mappings',
    },
}


class SECApiScraper:
    """
    SEC EDGAR API integration for corporate filings.

    Features:
    - Company filing searches
    - Insider trading (Form 4)
    - Institutional holdings (13F)
    - Full-text search
    - XBRL financial data
    - All FREE, no API key required
    """

    CATEGORY = "sec_filings"
    DISPLAY_NAME = "SEC Corporate Filings"

    # Rate limiting: SEC allows ~10 requests/second
    RATE_LIMIT_DELAY = 0.1  # 100ms between requests

    def __init__(self):
        """Initialize the SEC API scraper."""
        self.endpoints = SEC_API_ENDPOINTS
        self.filings: List[SECFiling] = []
        self.user_agent = "DataGod/1.0 (contact@datagod.io)"  # SEC requires user-agent
        self._ticker_cache: Dict[str, Dict[str, Any]] = {}
        self._last_request_time = 0
        logger.info("SECApiScraper initialized")

    def _format_cik(self, cik: str) -> str:
        """Format CIK to 10 digits with leading zeros."""
        return cik.zfill(10)

    async def _rate_limit(self):
        """Implement rate limiting for SEC API."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    async def _make_request(self, url: str, session: aiohttp.ClientSession = None) -> Dict[str, Any]:
        """Make HTTP request to SEC API with proper headers and rate limiting."""
        await self._rate_limit()

        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
        }

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    logger.warning(f"SEC API 404: {url}")
                    return {}
                elif response.status == 429:
                    logger.warning("SEC API rate limit hit, waiting...")
                    await asyncio.sleep(5)
                    return await self._make_request(url, session)
                else:
                    logger.error(f"SEC API error {response.status}: {url}")
                    return {}
        except asyncio.TimeoutError:
            logger.error(f"SEC API timeout: {url}")
            return {}
        except Exception as e:
            logger.error(f"SEC API request failed: {e}")
            return {}
        finally:
            if close_session:
                await session.close()

    async def get_all_tickers(self) -> Dict[str, Any]:
        """
        Get mapping of all company tickers to CIKs.

        Returns:
            Dictionary of ticker -> company info
        """
        if self._ticker_cache:
            return self._ticker_cache

        logger.info("Fetching all company tickers from SEC")
        url = self.endpoints['company_tickers']['base_url']

        data = await self._make_request(url)
        if not data:
            return {}

        # Build lookup by ticker and CIK
        ticker_map = {}
        for item in data.values():
            ticker = item.get('ticker', '')
            cik = str(item.get('cik_str', ''))
            title = item.get('title', '')

            if ticker:
                ticker_map[ticker.upper()] = {
                    'cik': cik,
                    'ticker': ticker.upper(),
                    'company_name': title,
                }
            if cik:
                ticker_map[f"CIK{cik}"] = {
                    'cik': cik,
                    'ticker': ticker.upper() if ticker else '',
                    'company_name': title,
                }

        self._ticker_cache = ticker_map
        logger.info(f"Loaded {len(data)} company tickers")
        return ticker_map

    async def search_company(
        self,
        company_name: str = "",
        cik: str = "",
        ticker: str = ""
    ) -> Dict[str, Any]:
        """
        Search for a company by name, CIK, or ticker.

        Args:
            company_name: Company name search
            cik: Central Index Key
            ticker: Stock ticker symbol

        Returns:
            Company information
        """
        logger.info(f"Searching SEC company: {company_name or cik or ticker}")

        # If we have a ticker, look it up
        if ticker:
            tickers = await self.get_all_tickers()
            if ticker.upper() in tickers:
                company_info = tickers[ticker.upper()]
                cik = company_info['cik']

        # If we have a CIK, get full company info from submissions
        if cik:
            formatted_cik = self._format_cik(cik)
            url = f"{self.endpoints['submissions']['base_url']}CIK{formatted_cik}.json"
            data = await self._make_request(url)

            if data:
                return {
                    'cik': data.get('cik', cik),
                    'company_name': data.get('name', ''),
                    'ticker': data.get('tickers', [''])[0] if data.get('tickers') else '',
                    'exchange': data.get('exchanges', [''])[0] if data.get('exchanges') else '',
                    'sic_code': data.get('sic', ''),
                    'sic_description': data.get('sicDescription', ''),
                    'state_of_incorporation': data.get('stateOfIncorporation', ''),
                    'fiscal_year_end': data.get('fiscalYearEnd', ''),
                    'ein': data.get('ein', ''),
                    'phone': data.get('phone', ''),
                    'addresses': data.get('addresses', {}),
                    'website': data.get('website', ''),
                    'filings_count': len(data.get('filings', {}).get('recent', {}).get('accessionNumber', [])),
                }

        # If searching by name, search through ticker list
        if company_name:
            tickers = await self.get_all_tickers()
            matches = []
            search_term = company_name.upper()
            for key, info in tickers.items():
                if search_term in info.get('company_name', '').upper():
                    matches.append(info)
                    if len(matches) >= 10:
                        break
            return {'matches': matches}

        return {}

    async def get_company_filings(
        self,
        cik: str,
        filing_type: FilingType = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> List[SECFiling]:
        """
        Get filings for a company.

        Args:
            cik: Central Index Key
            filing_type: Filter by filing type
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum results

        Returns:
            List of SEC filings
        """
        logger.info(f"Getting filings for CIK {cik}")
        filings = []

        formatted_cik = self._format_cik(cik)
        url = f"{self.endpoints['submissions']['base_url']}CIK{formatted_cik}.json"
        data = await self._make_request(url)

        if not data or 'filings' not in data:
            return filings

        company_name = data.get('name', '')
        company_tickers = data.get('tickers', [])
        ticker = company_tickers[0] if company_tickers else ''
        exchanges = data.get('exchanges', [])
        exchange = exchanges[0] if exchanges else ''
        sic_code = data.get('sic', '')
        sic_description = data.get('sicDescription', '')
        state_of_inc = data.get('stateOfIncorporation', '')
        fiscal_year_end = data.get('fiscalYearEnd', '')

        recent = data['filings'].get('recent', {})
        accession_numbers = recent.get('accessionNumber', [])
        forms = recent.get('form', [])
        filing_dates = recent.get('filingDate', [])
        primary_docs = recent.get('primaryDocument', [])
        primary_descriptions = recent.get('primaryDocDescription', [])

        target_form = filing_type.value if filing_type else None

        for i, acc_num in enumerate(accession_numbers):
            if i >= limit:
                break

            form = forms[i] if i < len(forms) else ''

            # Filter by filing type if specified
            if target_form and form != target_form:
                continue

            filing_date_str = filing_dates[i] if i < len(filing_dates) else ''
            try:
                filing_dt = datetime.strptime(filing_date_str, '%Y-%m-%d').date() if filing_date_str else None
            except ValueError:
                filing_dt = None

            # Apply date filters
            if start_date and filing_dt and filing_dt < start_date:
                continue
            if end_date and filing_dt and filing_dt > end_date:
                continue

            # Try to map form to FilingType enum
            try:
                form_type = FilingType(form)
            except ValueError:
                form_type = form  # Use string if not in enum

            primary_doc = primary_docs[i] if i < len(primary_docs) else ''
            acc_num_formatted = acc_num.replace('-', '')
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_num_formatted}/{primary_doc}"

            filing = SECFiling(
                accession_number=acc_num,
                cik=cik,
                company_name=company_name,
                filing_type=form_type,
                filing_date=filing_dt,
                primary_document=primary_doc,
                primary_doc_description=primary_descriptions[i] if i < len(primary_descriptions) else '',
                ticker=ticker,
                exchange=exchange,
                sic_code=sic_code,
                sic_description=sic_description,
                state_of_incorporation=state_of_inc,
                fiscal_year_end=fiscal_year_end,
                filing_url=filing_url,
                source_url=url,
            )
            filings.append(filing)

        logger.info(f"Found {len(filings)} filings for CIK {cik}")
        return filings

    async def get_insider_transactions(
        self,
        cik: str = "",
        ticker: str = "",
        insider_cik: str = "",
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> List[InsiderTransaction]:
        """
        Get insider trading transactions (Form 4).

        Args:
            cik: Company CIK
            ticker: Company ticker
            insider_cik: Specific insider CIK
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum results

        Returns:
            List of insider transactions
        """
        logger.info(f"Getting insider transactions for {cik or ticker or insider_cik}")
        transactions = []

        # Resolve ticker to CIK if needed
        if ticker and not cik:
            tickers = await self.get_all_tickers()
            if ticker.upper() in tickers:
                cik = tickers[ticker.upper()]['cik']

        search_cik = insider_cik or cik
        if not search_cik:
            return transactions

        # Get Form 4 filings
        filings = await self.get_company_filings(
            cik=search_cik,
            filing_type=FilingType.FORM_4,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        # Note: Full Form 4 XML parsing would require additional implementation
        # For now, return basic filing info as transactions
        for filing in filings:
            transaction = InsiderTransaction(
                accession_number=filing.accession_number,
                cik=search_cik,
                company_name=filing.company_name,
                company_cik=cik,
                insider_name="",  # Would need XML parsing
                filing_date=filing.filing_date,
                source_url=filing.filing_url,
                raw_data={'filing': filing.to_dict()},
            )
            transactions.append(transaction)

        return transactions

    async def get_institutional_holdings(
        self,
        cik: str = "",
        ticker: str = "",
        holder_cik: str = "",
        quarter: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Get institutional holdings (13F filings).

        Args:
            cik: Company CIK to find holders
            ticker: Company ticker
            holder_cik: Specific institution CIK
            quarter: Quarter (e.g., "2025Q4")

        Returns:
            List of institutional holdings
        """
        logger.info(f"Getting institutional holdings for {cik or ticker or holder_cik}")
        holdings = []

        if holder_cik:
            # Get 13F-HR filings for the institution
            filings = await self.get_company_filings(
                cik=holder_cik,
                filing_type=FilingType.FORM_13F,
                limit=10
            )

            for filing in filings:
                holdings.append({
                    'holder_cik': holder_cik,
                    'holder_name': filing.company_name,
                    'filing_date': filing.filing_date.isoformat() if filing.filing_date else None,
                    'accession_number': filing.accession_number,
                    'filing_url': filing.filing_url,
                    'quarter': quarter or 'latest',
                })

        return holdings

    async def get_company_facts(
        self,
        cik: str,
        concept: str = ""
    ) -> Dict[str, Any]:
        """
        Get XBRL company facts.

        Args:
            cik: Central Index Key
            concept: Specific XBRL concept (optional)

        Returns:
            Company financial facts
        """
        logger.info(f"Getting company facts for CIK {cik}")

        formatted_cik = self._format_cik(cik)

        if concept:
            # Get specific concept
            url = f"{self.endpoints['company_concept']['base_url']}CIK{formatted_cik}/us-gaap/{concept}.json"
        else:
            # Get all company facts
            url = f"{self.endpoints['company_facts']['base_url']}CIK{formatted_cik}.json"

        data = await self._make_request(url)

        if not data:
            return {}

        return {
            'cik': cik,
            'entity_name': data.get('entityName', ''),
            'facts': data.get('facts', {}),
            'source_url': url,
        }

    async def search_filings_fulltext(
        self,
        query: str,
        filing_types: List[str] = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> List[SECFiling]:
        """
        Full-text search across SEC filings using EDGAR Full-Text Search.

        Args:
            query: Search query
            filing_types: Filter by filing types
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum results

        Returns:
            List of matching filings
        """
        logger.info(f"Full-text search: {query}")
        results = []

        # Build EFTS search URL
        base_url = "https://efts.sec.gov/LATEST/search-index"

        params = {
            'q': query,
            'dateRange': 'custom',
            'startdt': start_date.strftime('%Y-%m-%d') if start_date else '',
            'enddt': end_date.strftime('%Y-%m-%d') if end_date else '',
        }

        if filing_types:
            params['forms'] = ','.join(filing_types)

        # Note: EFTS has a different API structure - using JSON endpoint
        search_url = f"https://efts.sec.gov/LATEST/search-index?q={query}"
        if start_date:
            search_url += f"&dateRange=custom&startdt={start_date.strftime('%Y-%m-%d')}"
        if end_date:
            search_url += f"&enddt={end_date.strftime('%Y-%m-%d')}"

        data = await self._make_request(search_url)

        if data and 'hits' in data:
            hits = data['hits'].get('hits', [])[:limit]
            for hit in hits:
                source = hit.get('_source', {})

                try:
                    filing_date = datetime.strptime(
                        source.get('file_date', ''), '%Y-%m-%d'
                    ).date()
                except (ValueError, TypeError):
                    filing_date = None

                form = source.get('form', '')
                try:
                    form_type = FilingType(form)
                except ValueError:
                    form_type = form

                filing = SECFiling(
                    accession_number=source.get('accession_number', ''),
                    cik=source.get('cik', ''),
                    company_name=source.get('display_names', [''])[0] if source.get('display_names') else '',
                    filing_type=form_type,
                    filing_date=filing_date,
                    source_url=search_url,
                )
                results.append(filing)

        return results

    async def get_recent_filings(
        self,
        filing_type: FilingType = None,
        limit: int = 100
    ) -> List[SECFiling]:
        """
        Get recent SEC filings using RSS feed.

        Args:
            filing_type: Filter by filing type
            limit: Maximum results

        Returns:
            List of recent filings
        """
        logger.info(f"Getting recent filings")

        # Use a high-volume filer like Apple (AAPL) to get recent market activity
        # or search all recent filings via EFTS
        today = date.today()
        thirty_days_ago = date(today.year, today.month - 1 if today.month > 1 else 12, today.day)

        if filing_type:
            return await self.search_filings_fulltext(
                query="*",
                filing_types=[filing_type.value],
                start_date=thirty_days_ago,
                end_date=today,
                limit=limit
            )
        else:
            return await self.search_filings_fulltext(
                query="*",
                start_date=thirty_days_ago,
                end_date=today,
                limit=limit
            )

    async def get_beneficial_ownership(
        self,
        cik: str = "",
        ticker: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Get beneficial ownership filings (13D/13G).

        Args:
            cik: Company CIK
            ticker: Company ticker

        Returns:
            List of beneficial ownership records
        """
        logger.info(f"Getting beneficial ownership for {cik or ticker}")
        records = []

        if ticker and not cik:
            tickers = await self.get_all_tickers()
            if ticker.upper() in tickers:
                cik = tickers[ticker.upper()]['cik']

        if not cik:
            return records

        # Get both SC 13D and SC 13G filings
        for filing_type in [FilingType.FORM_13D, FilingType.FORM_13G]:
            filings = await self.get_company_filings(
                cik=cik,
                filing_type=filing_type,
                limit=50
            )

            for filing in filings:
                records.append({
                    'type': filing_type.value,
                    'cik': cik,
                    'company_name': filing.company_name,
                    'filing_date': filing.filing_date.isoformat() if filing.filing_date else None,
                    'accession_number': filing.accession_number,
                    'filing_url': filing.filing_url,
                })

        return records

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        return {
            'category': self.CATEGORY,
            'display_name': self.DISPLAY_NAME,
            'api_endpoints': len(self.endpoints),
            'endpoint_names': list(self.endpoints.keys()),
            'filing_types': [t.value for t in FilingType],
            'auth_required': False,
            'rate_limit': '10 requests/second',
            'status': 'implemented',
        }

    # Synchronous wrappers for non-async usage
    def search_company_sync(self, **kwargs) -> Dict[str, Any]:
        """Synchronous wrapper for search_company."""
        return asyncio.get_event_loop().run_until_complete(self.search_company(**kwargs))

    def get_company_filings_sync(self, cik: str, **kwargs) -> List[SECFiling]:
        """Synchronous wrapper for get_company_filings."""
        return asyncio.get_event_loop().run_until_complete(self.get_company_filings(cik, **kwargs))

    def get_all_tickers_sync(self) -> Dict[str, Any]:
        """Synchronous wrapper for get_all_tickers."""
        return asyncio.get_event_loop().run_until_complete(self.get_all_tickers())


# Module-level convenience functions
def get_sec_scraper() -> SECApiScraper:
    """Get SEC API scraper instance."""
    return SECApiScraper()


async def search_sec_filings_async(
    cik: str = "",
    ticker: str = "",
    filing_type: str = "",
    **kwargs
) -> List[Dict[str, Any]]:
    """Search SEC filings asynchronously."""
    scraper = get_sec_scraper()

    if ticker and not cik:
        tickers = await scraper.get_all_tickers()
        if ticker.upper() in tickers:
            cik = tickers[ticker.upper()]['cik']

    ft = None
    if filing_type:
        try:
            ft = FilingType(filing_type)
        except ValueError:
            pass

    records = await scraper.get_company_filings(cik, ft, **kwargs)
    return [r.to_dict() for r in records]


def search_sec_filings(
    cik: str = "",
    ticker: str = "",
    filing_type: str = "",
    **kwargs
) -> List[Dict[str, Any]]:
    """Search SEC filings (synchronous wrapper)."""
    return asyncio.get_event_loop().run_until_complete(
        search_sec_filings_async(cik, ticker, filing_type, **kwargs)
    )


def get_available_endpoints() -> Dict[str, Any]:
    """Get all available SEC API endpoints."""
    return SEC_API_ENDPOINTS
