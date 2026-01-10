"""
Base classes for County Treasurer/Tax Collector Scrapers

This module provides abstract base classes and common data structures for
scraping property tax, tax lien, and tax sale information from county
treasurer/tax collector offices.

Data categories supported:
- Property tax records (current and historical)
- Tax liens and certificates
- Tax sales and auctions
- Delinquent tax lists
- Payment history
- Redemption information
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TaxStatus(Enum):
    """Status of property tax payment."""
    CURRENT = "current"
    DELINQUENT = "delinquent"
    PAID = "paid"
    PARTIAL = "partial"
    PENDING = "pending"
    EXEMPT = "exempt"
    IN_BANKRUPTCY = "in_bankruptcy"
    TAX_SALE = "tax_sale"
    REDEEMED = "redeemed"
    FORFEITED = "forfeited"
    UNKNOWN = "unknown"


class LienStatus(Enum):
    """Status of a tax lien."""
    ACTIVE = "active"
    REDEEMED = "redeemed"
    FORECLOSED = "foreclosed"
    ASSIGNED = "assigned"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING_SALE = "pending_sale"
    SOLD = "sold"
    UNKNOWN = "unknown"


class TaxSaleType(Enum):
    """Type of tax sale."""
    TAX_LIEN_SALE = "tax_lien_sale"
    TAX_DEED_SALE = "tax_deed_sale"
    SCAVENGER_SALE = "scavenger_sale"
    FORFEITURE_SALE = "forfeiture_sale"
    REDEMPTION_SALE = "redemption_sale"
    AUCTION = "auction"
    OVER_THE_COUNTER = "over_the_counter"
    ONLINE_AUCTION = "online_auction"
    UNKNOWN = "unknown"


class PaymentMethod(Enum):
    """Method of tax payment."""
    CASH = "cash"
    CHECK = "check"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    ACH = "ach"
    WIRE = "wire"
    ESCROW = "escrow"
    ONLINE = "online"
    MAIL = "mail"
    IN_PERSON = "in_person"
    UNKNOWN = "unknown"


@dataclass
class TaxBillItem:
    """Individual line item on a tax bill."""
    description: str
    amount: Decimal
    taxing_authority: Optional[str] = None
    tax_rate: Optional[Decimal] = None
    assessed_value: Optional[Decimal] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaxBill:
    """Property tax bill for a specific period."""
    bill_number: Optional[str] = None
    tax_year: int = 0
    parcel_id: str = ""
    property_address: Optional[str] = None
    owner_name: Optional[str] = None

    # Values
    assessed_value: Optional[Decimal] = None
    taxable_value: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None

    # Bill amounts
    gross_tax: Optional[Decimal] = None
    exemptions: Optional[Decimal] = None
    net_tax: Optional[Decimal] = None
    penalties: Optional[Decimal] = None
    interest: Optional[Decimal] = None
    fees: Optional[Decimal] = None
    total_due: Optional[Decimal] = None

    # Payment info
    amount_paid: Optional[Decimal] = None
    balance_due: Optional[Decimal] = None
    payment_status: TaxStatus = TaxStatus.UNKNOWN

    # Dates
    bill_date: Optional[date] = None
    due_date: Optional[date] = None
    delinquent_date: Optional[date] = None

    # Installments (some jurisdictions)
    installment_number: Optional[int] = None
    total_installments: Optional[int] = None

    # Line items
    line_items: List[TaxBillItem] = field(default_factory=list)

    # Source
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaxPayment:
    """Record of a tax payment."""
    payment_id: Optional[str] = None
    parcel_id: str = ""
    tax_year: int = 0

    # Payment details
    payment_date: Optional[date] = None
    payment_amount: Decimal = Decimal(0)
    payment_method: PaymentMethod = PaymentMethod.UNKNOWN

    # What was paid
    principal_paid: Optional[Decimal] = None
    interest_paid: Optional[Decimal] = None
    penalty_paid: Optional[Decimal] = None
    fees_paid: Optional[Decimal] = None

    # Receipt/confirmation
    receipt_number: Optional[str] = None
    check_number: Optional[str] = None
    payer_name: Optional[str] = None

    # Installment info
    installment_number: Optional[int] = None

    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaxLien:
    """Tax lien certificate record."""
    lien_number: str
    parcel_id: str

    # Lien details
    lien_date: Optional[date] = None
    lien_amount: Optional[Decimal] = None
    face_value: Optional[Decimal] = None

    # Interest/penalties
    interest_rate: Optional[Decimal] = None
    accrued_interest: Optional[Decimal] = None
    penalties: Optional[Decimal] = None
    total_due: Optional[Decimal] = None

    # Status
    status: LienStatus = LienStatus.UNKNOWN

    # Property info
    property_address: Optional[str] = None
    owner_name: Optional[str] = None
    legal_description: Optional[str] = None

    # Tax years covered
    tax_years: List[int] = field(default_factory=list)

    # Holder info (if assigned/sold)
    holder_name: Optional[str] = None
    holder_address: Optional[str] = None
    assignment_date: Optional[date] = None

    # Redemption
    redemption_date: Optional[date] = None
    redemption_amount: Optional[Decimal] = None
    redemption_deadline: Optional[date] = None

    # Sale info
    sale_date: Optional[date] = None
    sale_type: Optional[TaxSaleType] = None
    sale_amount: Optional[Decimal] = None

    # Source
    county: str = ""
    state: str = ""
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaxSaleProperty:
    """Property listed for tax sale."""
    sale_id: Optional[str] = None
    parcel_id: str = ""

    # Property info
    property_address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    legal_description: Optional[str] = None
    property_type: Optional[str] = None

    # Owner info
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None

    # Tax info
    tax_years_delinquent: List[int] = field(default_factory=list)
    total_taxes_due: Optional[Decimal] = None
    penalties_due: Optional[Decimal] = None
    interest_due: Optional[Decimal] = None
    fees_due: Optional[Decimal] = None
    total_amount_due: Optional[Decimal] = None

    # Sale info
    sale_type: TaxSaleType = TaxSaleType.UNKNOWN
    sale_date: Optional[date] = None
    auction_date: Optional[date] = None
    minimum_bid: Optional[Decimal] = None
    opening_bid: Optional[Decimal] = None

    # Assessed values
    assessed_value: Optional[Decimal] = None
    market_value: Optional[Decimal] = None

    # Status
    status: str = ""
    sold: bool = False
    winning_bid: Optional[Decimal] = None
    winning_bidder: Optional[str] = None

    # Redemption
    redemption_period_ends: Optional[date] = None
    redeemable: bool = True

    # Source
    county: str = ""
    state: str = ""
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PropertyTaxRecord:
    """Complete property tax record with history."""
    parcel_id: str
    property_address: Optional[str] = None
    city: Optional[str] = None
    state: str = ""
    zip_code: Optional[str] = None
    county: str = ""

    # Current owner
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None

    # Current values
    assessed_value: Optional[Decimal] = None
    taxable_value: Optional[Decimal] = None
    market_value: Optional[Decimal] = None

    # Current tax status
    current_tax_year: Optional[int] = None
    current_tax_amount: Optional[Decimal] = None
    current_amount_paid: Optional[Decimal] = None
    current_balance_due: Optional[Decimal] = None
    tax_status: TaxStatus = TaxStatus.UNKNOWN

    # Delinquency info
    is_delinquent: bool = False
    years_delinquent: int = 0
    total_delinquent: Optional[Decimal] = None

    # Exemptions
    exemptions: List[str] = field(default_factory=list)
    exemption_amount: Optional[Decimal] = None

    # History
    tax_bills: List[TaxBill] = field(default_factory=list)
    payment_history: List[TaxPayment] = field(default_factory=list)

    # Liens
    has_tax_lien: bool = False
    liens: List[TaxLien] = field(default_factory=list)

    # Special assessments
    special_assessments: List[TaxBillItem] = field(default_factory=list)

    # Source
    source_url: Optional[str] = None
    source_system: Optional[str] = None
    last_updated: Optional[datetime] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaxSearchCriteria:
    """Search criteria for tax record lookup."""
    parcel_id: Optional[str] = None
    property_address: Optional[str] = None
    owner_name: Optional[str] = None
    tax_year: Optional[int] = None
    tax_status: Optional[TaxStatus] = None
    delinquent_only: bool = False
    min_amount_due: Optional[Decimal] = None


@dataclass
class TaxSearchResult:
    """Result from a tax record search operation."""
    records: List[PropertyTaxRecord]
    total_count: int = 0
    page_number: int = 1
    page_size: int = 100
    has_more: bool = False
    search_criteria: Optional[TaxSearchCriteria] = None
    warnings: List[str] = field(default_factory=list)
    search_time_ms: Optional[int] = None
    source_system: Optional[str] = None


class CountyTreasurerBase(ABC):
    """
    Abstract base class for county treasurer/tax collector scrapers.

    Provides common functionality for searching property tax records,
    tax liens, and tax sale information maintained by county
    treasurer/tax collector offices.
    """

    # Class-level constants (override in subclasses)
    COUNTY_NAME: str = ""
    STATE: str = ""
    FIPS_CODE: str = ""
    BASE_URL: str = ""
    SYSTEM_NAME: str = ""

    # Tax calendar (varies by jurisdiction)
    TAX_YEAR_START: str = "01-01"  # MM-DD
    FIRST_INSTALLMENT_DUE: str = ""
    SECOND_INSTALLMENT_DUE: str = ""
    DELINQUENT_DATE: str = ""

    # Rate limiting
    REQUEST_DELAY: float = 1.0
    MAX_RETRIES: int = 3

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_request_time: float = 0

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; DataGod/1.0; Public Records Research)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            self.session = None

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    async def _fetch_html(self, url: str, params: Optional[Dict] = None) -> str:
        """Fetch HTML content from a URL."""
        await self._rate_limit()

        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        for attempt in range(self.MAX_RETRIES):
            try:
                async with self.session.get(url, params=params, timeout=30) as response:
                    response.raise_for_status()
                    return await response.text()
            except aiohttp.ClientError as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        return ""

    async def _fetch_json(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Fetch JSON content from a URL."""
        await self._rate_limit()

        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        for attempt in range(self.MAX_RETRIES):
            try:
                async with self.session.get(url, params=params, timeout=30) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        return {}

    # Utility parsing methods

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string in various formats."""
        if not date_str or date_str.strip() == "":
            return None

        date_str = date_str.strip()

        formats = [
            "%m/%d/%Y",
            "%Y-%m-%d",
            "%m-%d-%Y",
            "%d-%b-%Y",
            "%B %d, %Y",
            "%m/%d/%y",
            "%Y%m%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _parse_decimal(self, value_str: str) -> Optional[Decimal]:
        """Parse a decimal/money value."""
        if not value_str or value_str.strip() == "":
            return None

        # Remove currency symbols, commas, and spaces
        cleaned = re.sub(r"[$,\s]", "", value_str.strip())

        # Handle parentheses for negative values
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]

        try:
            return Decimal(cleaned)
        except Exception:
            return None

    def _parse_int(self, value_str: str) -> Optional[int]:
        """Parse an integer value."""
        if not value_str or value_str.strip() == "":
            return None

        cleaned = re.sub(r"[^\d-]", "", value_str.strip())

        try:
            return int(cleaned)
        except ValueError:
            return None

    def _parse_tax_status(self, status_str: str) -> TaxStatus:
        """Parse tax payment status from string."""
        if not status_str:
            return TaxStatus.UNKNOWN

        upper = status_str.upper()

        if "PAID" in upper or "CURRENT" in upper:
            return TaxStatus.PAID
        elif "DELINQUENT" in upper or "PAST DUE" in upper or "OVERDUE" in upper:
            return TaxStatus.DELINQUENT
        elif "PARTIAL" in upper:
            return TaxStatus.PARTIAL
        elif "PENDING" in upper:
            return TaxStatus.PENDING
        elif "EXEMPT" in upper:
            return TaxStatus.EXEMPT
        elif "BANKRUPTCY" in upper:
            return TaxStatus.IN_BANKRUPTCY
        elif "SALE" in upper or "AUCTION" in upper:
            return TaxStatus.TAX_SALE
        elif "REDEEM" in upper:
            return TaxStatus.REDEEMED
        elif "FORFEIT" in upper:
            return TaxStatus.FORFEITED

        return TaxStatus.UNKNOWN

    def _parse_lien_status(self, status_str: str) -> LienStatus:
        """Parse lien status from string."""
        if not status_str:
            return LienStatus.UNKNOWN

        upper = status_str.upper()

        if "ACTIVE" in upper or "OPEN" in upper:
            return LienStatus.ACTIVE
        elif "REDEEM" in upper:
            return LienStatus.REDEEMED
        elif "FORECLOSE" in upper:
            return LienStatus.FORECLOSED
        elif "ASSIGN" in upper:
            return LienStatus.ASSIGNED
        elif "CANCEL" in upper:
            return LienStatus.CANCELLED
        elif "EXPIRE" in upper:
            return LienStatus.EXPIRED
        elif "PENDING" in upper:
            return LienStatus.PENDING_SALE
        elif "SOLD" in upper:
            return LienStatus.SOLD

        return LienStatus.UNKNOWN

    def _parse_sale_type(self, type_str: str) -> TaxSaleType:
        """Parse tax sale type from string."""
        if not type_str:
            return TaxSaleType.UNKNOWN

        upper = type_str.upper()

        if "LIEN" in upper:
            return TaxSaleType.TAX_LIEN_SALE
        elif "DEED" in upper:
            return TaxSaleType.TAX_DEED_SALE
        elif "SCAVENGER" in upper:
            return TaxSaleType.SCAVENGER_SALE
        elif "FORFEIT" in upper:
            return TaxSaleType.FORFEITURE_SALE
        elif "ONLINE" in upper:
            return TaxSaleType.ONLINE_AUCTION
        elif "AUCTION" in upper:
            return TaxSaleType.AUCTION
        elif "COUNTER" in upper or "OTC" in upper:
            return TaxSaleType.OVER_THE_COUNTER

        return TaxSaleType.UNKNOWN

    # Abstract methods (must be implemented by subclasses)

    @abstractmethod
    async def get_tax_record(
        self,
        parcel_id: str
    ) -> Optional[PropertyTaxRecord]:
        """Get property tax record by parcel ID."""
        pass

    @abstractmethod
    async def search_by_address(
        self,
        street_address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        max_results: int = 100
    ) -> TaxSearchResult:
        """Search for tax records by property address."""
        pass

    @abstractmethod
    async def search_by_owner(
        self,
        owner_name: str,
        max_results: int = 100
    ) -> TaxSearchResult:
        """Search for tax records by owner name."""
        pass

    async def get_tax_bill(
        self,
        parcel_id: str,
        tax_year: Optional[int] = None
    ) -> Optional[TaxBill]:
        """Get tax bill for a specific year."""
        record = await self.get_tax_record(parcel_id)
        if not record or not record.tax_bills:
            return None

        if tax_year:
            for bill in record.tax_bills:
                if bill.tax_year == tax_year:
                    return bill
            return None

        # Return most recent bill
        return record.tax_bills[0] if record.tax_bills else None

    async def get_payment_history(
        self,
        parcel_id: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> List[TaxPayment]:
        """Get payment history for a property."""
        record = await self.get_tax_record(parcel_id)
        if not record:
            return []

        payments = record.payment_history

        if start_year:
            payments = [p for p in payments if p.tax_year >= start_year]
        if end_year:
            payments = [p for p in payments if p.tax_year <= end_year]

        return payments

    async def get_delinquent_properties(
        self,
        min_amount: Optional[Decimal] = None,
        max_results: int = 500
    ) -> TaxSearchResult:
        """Get list of delinquent properties."""
        # Default implementation - override for systems with delinquent list
        return TaxSearchResult(
            records=[],
            total_count=0,
            warnings=["Delinquent property list not available for this jurisdiction"],
        )

    async def get_tax_sale_properties(
        self,
        sale_type: Optional[TaxSaleType] = None,
        upcoming_only: bool = True,
        max_results: int = 500
    ) -> List[TaxSaleProperty]:
        """Get properties scheduled for tax sale."""
        # Default returns empty - override for systems with tax sale data
        return []

    async def get_tax_liens(
        self,
        parcel_id: Optional[str] = None,
        status: Optional[LienStatus] = None,
        max_results: int = 100
    ) -> List[TaxLien]:
        """Get tax liens, optionally filtered by parcel or status."""
        # Default returns empty - override for systems with lien data
        return []
