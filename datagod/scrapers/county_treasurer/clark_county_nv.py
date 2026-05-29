"""
Clark County, Nevada Treasurer Scraper

Clark County (2.3M population) maintains property tax records through
the Clark County Treasurer's Office.

System: Custom web application
URL: https://www.clarkcountynv.gov/government/elected_officials/county_treasurer/
FIPS: 32003

Nevada property taxes are due in four installments:
- 1st quarter: Due 3rd Monday in August
- 2nd quarter: Due 1st Monday in October
- 3rd quarter: Due 1st Monday in January
- 4th quarter: Due 1st Monday in March

Nevada has a property tax cap of 3% for owner-occupied and 8% for other properties.
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


class ClarkCountyTreasurer(CountyTreasurerBase):
    """
    Scraper for Clark County Treasurer's Office.

    Clark County (Las Vegas area) uses a custom web application for property tax lookup.
    APNs are formatted as XXX-XX-XXX-XXX.
    """

    COUNTY_NAME = "Clark County"
    STATE = "Nevada"
    FIPS_CODE = "32003"
    BASE_URL = "https://www.clarkcountynv.gov/treasurer/"
    SEARCH_URL = "https://www.clarkcountynv.gov/treasurer/api/search"
    DETAIL_URL = "https://www.clarkcountynv.gov/treasurer/api/property"
    SYSTEM_NAME = "Clark County Treasurer"

    # Nevada tax calendar (quarterly payments)
    TAX_YEAR_START = "07-01"  # Fiscal year
    FIRST_INSTALLMENT_DUE = "08-15"  # 3rd Monday August (approximate)
    SECOND_INSTALLMENT_DUE = "10-01"  # 1st Monday October (approximate)
    THIRD_INSTALLMENT_DUE = "01-01"  # 1st Monday January (approximate)
    FOURTH_INSTALLMENT_DUE = "03-01"  # 1st Monday March (approximate)

    REQUEST_DELAY = 1.5

    def _format_apn(self, apn: str) -> str:
        """Format APN to standard XXX-XX-XXX-XXX format."""
        import re

        digits = re.sub(r"[^0-9]", "", apn)
        if len(digits) >= 11:
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:8]}-{digits[8:11]}"
        return apn

    async def get_tax_record(self, parcel_id: str) -> Optional[PropertyTaxRecord]:
        """Get property tax record by APN."""
        formatted_apn = self._format_apn(parcel_id)

        try:
            data = await self._fetch_json(f"{self.DETAIL_URL}/{formatted_apn}")
        except Exception as e:
            logger.error(f"Clark County tax record lookup failed: {e}")
            return None

        if not data:
            return None

        record = PropertyTaxRecord(
            parcel_id=formatted_apn,
            property_address=data.get("propertyAddress"),
            city=data.get("city"),
            state="NV",
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
            source_url=f"{self.BASE_URL}property/{formatted_apn}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

        # Parse exemptions (Nevada has veteran, blind, senior citizen, etc.)
        for exemption in data.get("exemptions", []):
            record.exemptions.append(exemption.get("type", ""))
        record.exemption_amount = self._parse_decimal(
            str(data.get("exemptionAmount", ""))
        )

        # Parse tax bills
        for bill_data in data.get("taxBills", []):
            bill = TaxBill(
                bill_number=bill_data.get("billNumber"),
                tax_year=bill_data.get("taxYear", 0),
                parcel_id=formatted_apn,
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
                installment_number=bill_data.get("quarter"),
                total_installments=4,  # Nevada has 4 quarterly installments
                raw_data=bill_data,
            )

            # Parse line items (different taxing entities)
            for item in bill_data.get("lineItems", []):
                line_item = TaxBillItem(
                    description=item.get("entity", ""),
                    amount=self._parse_decimal(str(item.get("amount", "")))
                    or Decimal(0),
                    taxing_authority=item.get("entity"),
                    tax_rate=self._parse_decimal(str(item.get("rate", ""))),
                    raw_data=item,
                )
                bill.line_items.append(line_item)

            record.tax_bills.append(bill)

        # Parse payment history
        for payment_data in data.get("payments", []):
            payment = TaxPayment(
                payment_id=payment_data.get("receiptNumber"),
                parcel_id=formatted_apn,
                tax_year=payment_data.get("taxYear", 0),
                payment_date=self._parse_date(payment_data.get("paymentDate", "")),
                payment_amount=self._parse_decimal(str(payment_data.get("amount", "")))
                or Decimal(0),
                receipt_number=payment_data.get("receiptNumber"),
                installment_number=payment_data.get("quarter"),
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
            logger.error(f"Clark County address search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                warnings=[str(e)],
            )

        records = []
        for item in data.get("results", [])[:max_results]:
            record = PropertyTaxRecord(
                parcel_id=item.get("apn", ""),
                property_address=item.get("address"),
                city=item.get("city"),
                state="NV",
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
            logger.error(f"Clark County owner search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                warnings=[str(e)],
            )

        records = []
        for item in data.get("results", [])[:max_results]:
            record = PropertyTaxRecord(
                parcel_id=item.get("apn", ""),
                property_address=item.get("address"),
                city=item.get("city"),
                state="NV",
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


def get_clark_county_tax_record(parcel_id: str) -> Optional[PropertyTaxRecord]:
    """Get Clark County property tax record by APN."""

    async def _get():
        async with ClarkCountyTreasurer() as treasurer:
            return await treasurer.get_tax_record(parcel_id)

    return asyncio.run(_get())


def search_clark_county_tax_by_address(
    address: str, city: Optional[str] = None, max_results: int = 100
) -> TaxSearchResult:
    """Search Clark County tax records by address."""

    async def _search():
        async with ClarkCountyTreasurer() as treasurer:
            return await treasurer.search_by_address(
                address, city=city, max_results=max_results
            )

    return asyncio.run(_search())


def search_clark_county_tax_by_owner(
    owner_name: str, max_results: int = 100
) -> TaxSearchResult:
    """Search Clark County tax records by owner name."""

    async def _search():
        async with ClarkCountyTreasurer() as treasurer:
            return await treasurer.search_by_owner(owner_name, max_results=max_results)

    return asyncio.run(_search())
