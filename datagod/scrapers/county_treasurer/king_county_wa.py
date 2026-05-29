"""
King County, Washington Treasury Scraper

King County (2.3M population) maintains property tax records through
the King County Treasury Operations.

System: King County Property Tax Information
URL: https://kingcounty.gov/treasury/
FIPS: 53033

Washington property taxes are due in two installments:
- 1st half: Due April 30
- 2nd half: Due October 31
- Interest accrues at 1% per month on delinquent taxes

Washington does not have a state income tax, so property taxes
tend to be higher. There is no property tax cap in Washington.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from .base import (
    CountyTreasurerBase,
    LienStatus,
    PaymentMethod,
    PropertyTaxRecord,
    TaxBill,
    TaxBillItem,
    TaxLien,
    TaxPayment,
    TaxSaleProperty,
    TaxSaleType,
    TaxSearchCriteria,
    TaxSearchResult,
    TaxStatus,
)

logger = logging.getLogger(__name__)


class KingCountyTreasurer(CountyTreasurerBase):
    """
    Scraper for King County Treasury Operations.

    King County uses a custom web application for property tax lookup.
    Uses 10-digit parcel numbers.
    """

    COUNTY_NAME = "King County"
    STATE = "Washington"
    FIPS_CODE = "53033"
    BASE_URL = "https://payment.kingcounty.gov/"
    SEARCH_URL = "https://payment.kingcounty.gov/Home/PropertyTaxSearch"
    DETAIL_URL = "https://payment.kingcounty.gov/api/property"
    SYSTEM_NAME = "King County Treasury"

    # Washington tax calendar
    TAX_YEAR_START = "01-01"  # Calendar year
    FIRST_INSTALLMENT_DUE = "04-30"
    SECOND_INSTALLMENT_DUE = "10-31"
    DELINQUENT_DATE = "06-01"  # After first half deadline

    REQUEST_DELAY = 1.5

    def _format_parcel(self, parcel: str) -> str:
        """Format parcel number to 10-digit format."""
        import re

        digits = re.sub(r"[^0-9]", "", parcel)
        return digits.zfill(10)[:10]

    async def get_tax_record(self, parcel_id: str) -> Optional[PropertyTaxRecord]:
        """Get property tax record by parcel number."""
        formatted_parcel = self._format_parcel(parcel_id)

        try:
            data = await self._fetch_json(f"{self.DETAIL_URL}/{formatted_parcel}")
        except Exception as e:
            logger.error(f"King County tax record lookup failed: {e}")
            return None

        if not data:
            return None

        record = PropertyTaxRecord(
            parcel_id=formatted_parcel,
            property_address=data.get("propertyAddress"),
            city=data.get("city"),
            state="WA",
            zip_code=data.get("zipCode"),
            county=self.COUNTY_NAME,
            owner_name=data.get("ownerName"),
            owner_address=data.get("mailingAddress"),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(str(data.get("taxableValue", ""))),
            current_tax_year=data.get("taxYear"),
            current_tax_amount=self._parse_decimal(str(data.get("totalTax", ""))),
            current_amount_paid=self._parse_decimal(str(data.get("amountPaid", ""))),
            current_balance_due=self._parse_decimal(str(data.get("balanceDue", ""))),
            tax_status=self._parse_tax_status(data.get("status", "")),
            is_delinquent=data.get("isDelinquent", False),
            years_delinquent=data.get("yearsDelinquent", 0),
            total_delinquent=self._parse_decimal(str(data.get("totalDelinquent", ""))),
            source_url=f"{self.BASE_URL}property/{formatted_parcel}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

        # Parse exemptions (Washington has senior/disabled, etc.)
        for exemption in data.get("exemptions", []):
            record.exemptions.append(exemption.get("type", ""))
        record.exemption_amount = self._parse_decimal(
            str(data.get("exemptionAmount", ""))
        )

        # Parse tax bills
        for bill_data in data.get("taxBills", []):
            bill = TaxBill(
                bill_number=bill_data.get("statementNumber"),
                tax_year=bill_data.get("taxYear", 0),
                parcel_id=formatted_parcel,
                property_address=data.get("propertyAddress"),
                owner_name=data.get("ownerName"),
                assessed_value=self._parse_decimal(
                    str(bill_data.get("assessedValue", ""))
                ),
                net_tax=self._parse_decimal(str(bill_data.get("baseTax", ""))),
                penalties=self._parse_decimal(str(bill_data.get("penalties", ""))),
                interest=self._parse_decimal(str(bill_data.get("interest", ""))),
                total_due=self._parse_decimal(str(bill_data.get("totalDue", ""))),
                amount_paid=self._parse_decimal(str(bill_data.get("amountPaid", ""))),
                balance_due=self._parse_decimal(str(bill_data.get("balanceDue", ""))),
                payment_status=self._parse_tax_status(bill_data.get("status", "")),
                due_date=self._parse_date(bill_data.get("dueDate", "")),
                installment_number=bill_data.get("installment"),
                total_installments=2,  # Washington has 2 installments
                raw_data=bill_data,
            )

            # Parse line items (different levy districts)
            for item in bill_data.get("lineItems", []):
                line_item = TaxBillItem(
                    description=item.get("district", ""),
                    amount=self._parse_decimal(str(item.get("amount", "")))
                    or Decimal(0),
                    taxing_authority=item.get("district"),
                    tax_rate=self._parse_decimal(str(item.get("rate", ""))),
                    raw_data=item,
                )
                bill.line_items.append(line_item)

            record.tax_bills.append(bill)

        # Parse payment history
        for payment_data in data.get("payments", []):
            payment = TaxPayment(
                payment_id=payment_data.get("receiptNumber"),
                parcel_id=formatted_parcel,
                tax_year=payment_data.get("taxYear", 0),
                payment_date=self._parse_date(payment_data.get("paymentDate", "")),
                payment_amount=self._parse_decimal(str(payment_data.get("amount", "")))
                or Decimal(0),
                receipt_number=payment_data.get("receiptNumber"),
                installment_number=payment_data.get("installment"),
                raw_data=payment_data,
            )
            record.payment_history.append(payment)

        return record

    async def search_by_address(
        self,
        street_address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        max_results: int = 100,
    ) -> TaxSearchResult:
        """Search for tax records by property address."""
        import time

        start_time = time.time()

        params = {
            "address": street_address,
            "limit": min(max_results, 100),
        }
        if city:
            params["city"] = city
        if zip_code:
            params["zip"] = zip_code

        try:
            data = await self._fetch_json(self.SEARCH_URL, params=params)
        except Exception as e:
            logger.error(f"King County address search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                warnings=[str(e)],
            )

        records = []
        for item in data.get("results", [])[:max_results]:
            record = PropertyTaxRecord(
                parcel_id=item.get("parcelNumber", ""),
                property_address=item.get("address"),
                city=item.get("city"),
                state="WA",
                county=self.COUNTY_NAME,
                owner_name=item.get("ownerName"),
                assessed_value=self._parse_decimal(str(item.get("assessedValue", ""))),
                current_balance_due=self._parse_decimal(
                    str(item.get("balanceDue", ""))
                ),
                tax_status=self._parse_tax_status(item.get("status", "")),
                source_system=self.SYSTEM_NAME,
            )
            records.append(record)

        search_time = int((time.time() - start_time) * 1000)

        return TaxSearchResult(
            records=records,
            total_count=data.get("total", len(records)),
            has_more=data.get("hasMore", False),
            search_criteria=TaxSearchCriteria(property_address=street_address),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def search_by_owner(
        self, owner_name: str, max_results: int = 100
    ) -> TaxSearchResult:
        """Search for tax records by owner name."""
        import time

        start_time = time.time()

        params = {
            "ownerName": owner_name,
            "limit": min(max_results, 100),
        }

        try:
            data = await self._fetch_json(self.SEARCH_URL, params=params)
        except Exception as e:
            logger.error(f"King County owner search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                warnings=[str(e)],
            )

        records = []
        for item in data.get("results", [])[:max_results]:
            record = PropertyTaxRecord(
                parcel_id=item.get("parcelNumber", ""),
                property_address=item.get("address"),
                city=item.get("city"),
                state="WA",
                county=self.COUNTY_NAME,
                owner_name=item.get("ownerName"),
                assessed_value=self._parse_decimal(str(item.get("assessedValue", ""))),
                current_balance_due=self._parse_decimal(
                    str(item.get("balanceDue", ""))
                ),
                tax_status=self._parse_tax_status(item.get("status", "")),
                source_system=self.SYSTEM_NAME,
            )
            records.append(record)

        search_time = int((time.time() - start_time) * 1000)

        return TaxSearchResult(
            records=records,
            total_count=data.get("total", len(records)),
            has_more=data.get("hasMore", False),
            search_criteria=TaxSearchCriteria(owner_name=owner_name),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


# Synchronous convenience functions


def get_king_county_tax_record(parcel_id: str) -> Optional[PropertyTaxRecord]:
    """Get King County property tax record by parcel number."""

    async def _get():
        async with KingCountyTreasurer() as treasurer:
            return await treasurer.get_tax_record(parcel_id)

    return asyncio.run(_get())


def search_king_county_tax_by_address(
    address: str, city: Optional[str] = None, max_results: int = 100
) -> TaxSearchResult:
    """Search King County tax records by address."""

    async def _search():
        async with KingCountyTreasurer() as treasurer:
            return await treasurer.search_by_address(
                address, city=city, max_results=max_results
            )

    return asyncio.run(_search())


def search_king_county_tax_by_owner(
    owner_name: str, max_results: int = 100
) -> TaxSearchResult:
    """Search King County tax records by owner name."""

    async def _search():
        async with KingCountyTreasurer() as treasurer:
            return await treasurer.search_by_owner(owner_name, max_results=max_results)

    return asyncio.run(_search())
