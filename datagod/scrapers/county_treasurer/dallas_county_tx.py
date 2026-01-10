"""
Dallas County, Texas Tax Office Scraper

Dallas County (2.6M population) maintains property tax records through
the Dallas County Tax Office.

System: Custom web application
URL: https://www.dallascounty.org/tax-office/
FIPS: 48113

Texas property taxes are due January 31 of the following year.
Penalty and interest begin accruing February 1.
Texas has no state property tax - all property taxes are local.
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
    TaxStatus,
    LienStatus,
    TaxSaleType,
    PaymentMethod,
    TaxBillItem,
    TaxBill,
    TaxPayment,
    TaxLien,
    TaxSaleProperty,
    PropertyTaxRecord,
    TaxSearchCriteria,
    TaxSearchResult,
)

logger = logging.getLogger(__name__)


class DallasCountyTreasurer(CountyTreasurerBase):
    """
    Scraper for Dallas County Tax Office.

    Dallas County uses a custom web application for property tax lookup.
    Property IDs are used as the primary identifier.
    """

    COUNTY_NAME = "Dallas County"
    STATE = "Texas"
    FIPS_CODE = "48113"
    BASE_URL = "https://www.dallascounty.org/tax-office/"
    SEARCH_URL = "https://www.dallascounty.org/tax-office/api/search"
    DETAIL_URL = "https://www.dallascounty.org/tax-office/api/property"
    SYSTEM_NAME = "Dallas County Tax Office"

    # Texas tax calendar
    TAX_YEAR_START = "01-01"  # Calendar year
    FIRST_INSTALLMENT_DUE = "01-31"  # Whole tax due
    DELINQUENT_DATE = "02-01"

    REQUEST_DELAY = 1.5

    async def get_tax_record(
        self,
        parcel_id: str
    ) -> Optional[PropertyTaxRecord]:
        """Get property tax record by property ID."""
        try:
            data = await self._fetch_json(
                f"{self.DETAIL_URL}/{parcel_id}"
            )
        except Exception as e:
            logger.error(f"Dallas County tax record lookup failed: {e}")
            return None

        if not data:
            return None

        record = PropertyTaxRecord(
            parcel_id=parcel_id,
            property_address=data.get("propertyAddress"),
            city=data.get("city"),
            state="TX",
            zip_code=data.get("zipCode"),
            county=self.COUNTY_NAME,
            owner_name=data.get("ownerName"),
            owner_address=data.get("mailingAddress"),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(str(data.get("taxableValue", ""))),
            market_value=self._parse_decimal(str(data.get("marketValue", ""))),
            current_tax_year=data.get("taxYear"),
            current_tax_amount=self._parse_decimal(str(data.get("totalTax", ""))),
            current_amount_paid=self._parse_decimal(str(data.get("amountPaid", ""))),
            current_balance_due=self._parse_decimal(str(data.get("balanceDue", ""))),
            tax_status=self._parse_tax_status(data.get("status", "")),
            is_delinquent=data.get("isDelinquent", False),
            years_delinquent=data.get("yearsDelinquent", 0),
            total_delinquent=self._parse_decimal(str(data.get("totalDelinquent", ""))),
            source_url=f"{self.BASE_URL}property/{parcel_id}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

        # Parse exemptions (Texas has homestead, over-65, disability, etc.)
        for exemption in data.get("exemptions", []):
            record.exemptions.append(exemption.get("type", ""))
        record.exemption_amount = self._parse_decimal(str(data.get("exemptionAmount", "")))

        # Parse tax bills
        for bill_data in data.get("taxBills", []):
            bill = TaxBill(
                bill_number=bill_data.get("statementNumber"),
                tax_year=bill_data.get("taxYear", 0),
                parcel_id=parcel_id,
                property_address=data.get("propertyAddress"),
                owner_name=data.get("ownerName"),
                assessed_value=self._parse_decimal(str(bill_data.get("assessedValue", ""))),
                taxable_value=self._parse_decimal(str(bill_data.get("taxableValue", ""))),
                net_tax=self._parse_decimal(str(bill_data.get("baseTax", ""))),
                penalties=self._parse_decimal(str(bill_data.get("penalties", ""))),
                interest=self._parse_decimal(str(bill_data.get("interest", ""))),
                total_due=self._parse_decimal(str(bill_data.get("totalDue", ""))),
                amount_paid=self._parse_decimal(str(bill_data.get("amountPaid", ""))),
                balance_due=self._parse_decimal(str(bill_data.get("balanceDue", ""))),
                payment_status=self._parse_tax_status(bill_data.get("status", "")),
                due_date=self._parse_date(bill_data.get("dueDate", "")),
                delinquent_date=self._parse_date(bill_data.get("delinquentDate", "")),
                raw_data=bill_data,
            )

            # Parse line items (different taxing entities)
            for item in bill_data.get("lineItems", []):
                line_item = TaxBillItem(
                    description=item.get("entity", ""),
                    amount=self._parse_decimal(str(item.get("amount", ""))) or Decimal(0),
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
                parcel_id=parcel_id,
                tax_year=payment_data.get("taxYear", 0),
                payment_date=self._parse_date(payment_data.get("paymentDate", "")),
                payment_amount=self._parse_decimal(str(payment_data.get("amount", ""))) or Decimal(0),
                receipt_number=payment_data.get("receiptNumber"),
                raw_data=payment_data,
            )
            record.payment_history.append(payment)

        return record

    async def search_by_address(
        self,
        street_address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        max_results: int = 100
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
            logger.error(f"Dallas County address search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                warnings=[str(e)],
            )

        records = []
        for item in data.get("results", [])[:max_results]:
            record = PropertyTaxRecord(
                parcel_id=item.get("propertyId", ""),
                property_address=item.get("address"),
                city=item.get("city"),
                state="TX",
                county=self.COUNTY_NAME,
                owner_name=item.get("ownerName"),
                assessed_value=self._parse_decimal(str(item.get("assessedValue", ""))),
                current_balance_due=self._parse_decimal(str(item.get("balanceDue", ""))),
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
        self,
        owner_name: str,
        max_results: int = 100
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
            logger.error(f"Dallas County owner search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                warnings=[str(e)],
            )

        records = []
        for item in data.get("results", [])[:max_results]:
            record = PropertyTaxRecord(
                parcel_id=item.get("propertyId", ""),
                property_address=item.get("address"),
                city=item.get("city"),
                state="TX",
                county=self.COUNTY_NAME,
                owner_name=item.get("ownerName"),
                assessed_value=self._parse_decimal(str(item.get("assessedValue", ""))),
                current_balance_due=self._parse_decimal(str(item.get("balanceDue", ""))),
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

def get_dallas_county_tax_record(parcel_id: str) -> Optional[PropertyTaxRecord]:
    """Get Dallas County property tax record by property ID."""
    async def _get():
        async with DallasCountyTreasurer() as treasurer:
            return await treasurer.get_tax_record(parcel_id)
    return asyncio.run(_get())


def search_dallas_county_tax_by_address(
    address: str,
    city: Optional[str] = None,
    max_results: int = 100
) -> TaxSearchResult:
    """Search Dallas County tax records by address."""
    async def _search():
        async with DallasCountyTreasurer() as treasurer:
            return await treasurer.search_by_address(address, city=city, max_results=max_results)
    return asyncio.run(_search())


def search_dallas_county_tax_by_owner(
    owner_name: str,
    max_results: int = 100
) -> TaxSearchResult:
    """Search Dallas County tax records by owner name."""
    async def _search():
        async with DallasCountyTreasurer() as treasurer:
            return await treasurer.search_by_owner(owner_name, max_results=max_results)
    return asyncio.run(_search())
