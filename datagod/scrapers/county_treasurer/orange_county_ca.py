"""
Orange County, California Treasurer-Tax Collector Scraper

Orange County (3.2M population) maintains property tax records through
the Treasurer-Tax Collector's Office.

System: Custom web application
URL: https://ttc.ocgov.com/
FIPS: 06059

California property taxes are due in two installments:
- 1st installment: Due November 1, delinquent December 10
- 2nd installment: Due February 1, delinquent April 10

Tax rate: ~1% of assessed value plus voter-approved bonds and assessments
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


class OrangeCountyTreasurer(CountyTreasurerBase):
    """
    Scraper for Orange County Treasurer-Tax Collector.

    Orange County uses a custom web application for property tax lookup.
    APNs are formatted as XXX-XXX-XX or XXX-XXX-XXX.
    """

    COUNTY_NAME = "Orange County"
    STATE = "California"
    FIPS_CODE = "06059"
    BASE_URL = "https://ttc.ocgov.com/"
    SEARCH_URL = "https://ttc.ocgov.com/api/propertytax/search"
    DETAIL_URL = "https://ttc.ocgov.com/api/propertytax/parcel"
    SYSTEM_NAME = "Orange County TTC"

    # California tax calendar
    TAX_YEAR_START = "07-01"  # Fiscal year
    FIRST_INSTALLMENT_DUE = "11-01"
    SECOND_INSTALLMENT_DUE = "02-01"
    DELINQUENT_DATE = "06-30"

    REQUEST_DELAY = 1.5

    def _format_apn(self, apn: str) -> str:
        """Format APN to standard format."""
        import re
        digits = re.sub(r'[^0-9]', '', apn)
        if len(digits) == 8:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:8]}"
        elif len(digits) == 9:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:9]}"
        return apn

    async def get_tax_record(
        self,
        parcel_id: str
    ) -> Optional[PropertyTaxRecord]:
        """Get property tax record by parcel ID (APN)."""
        formatted_apn = self._format_apn(parcel_id)

        try:
            data = await self._fetch_json(
                f"{self.DETAIL_URL}/{formatted_apn}"
            )
        except Exception as e:
            logger.error(f"Orange County tax record lookup failed: {e}")
            return None

        if not data:
            return None

        record = PropertyTaxRecord(
            parcel_id=formatted_apn,
            property_address=data.get("propertyAddress"),
            city=data.get("city"),
            state="CA",
            zip_code=data.get("zipCode"),
            county=self.COUNTY_NAME,
            owner_name=data.get("ownerName"),
            owner_address=data.get("mailingAddress"),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(str(data.get("netTaxableValue", ""))),
            current_tax_year=data.get("taxYear"),
            current_tax_amount=self._parse_decimal(str(data.get("totalTax", ""))),
            current_amount_paid=self._parse_decimal(str(data.get("amountPaid", ""))),
            current_balance_due=self._parse_decimal(str(data.get("balanceDue", ""))),
            tax_status=self._parse_tax_status(data.get("status", "")),
            is_delinquent=data.get("isDelinquent", False),
            source_url=f"{self.BASE_URL}parcel/{formatted_apn}",
            source_system=self.SYSTEM_NAME,
            raw_data=data,
        )

        # Parse exemptions
        for exemption in data.get("exemptions", []):
            record.exemptions.append(exemption.get("type", ""))

        # Parse tax bills
        for bill_data in data.get("taxBills", []):
            bill = TaxBill(
                bill_number=bill_data.get("billNumber"),
                tax_year=bill_data.get("taxYear", 0),
                parcel_id=formatted_apn,
                property_address=data.get("propertyAddress"),
                owner_name=data.get("ownerName"),
                assessed_value=self._parse_decimal(str(bill_data.get("assessedValue", ""))),
                net_tax=self._parse_decimal(str(bill_data.get("netTax", ""))),
                total_due=self._parse_decimal(str(bill_data.get("totalDue", ""))),
                amount_paid=self._parse_decimal(str(bill_data.get("amountPaid", ""))),
                balance_due=self._parse_decimal(str(bill_data.get("balanceDue", ""))),
                payment_status=self._parse_tax_status(bill_data.get("status", "")),
                due_date=self._parse_date(bill_data.get("dueDate", "")),
                installment_number=bill_data.get("installment"),
                raw_data=bill_data,
            )
            record.tax_bills.append(bill)

        # Parse payment history
        for payment_data in data.get("payments", []):
            payment = TaxPayment(
                payment_id=payment_data.get("confirmationNumber"),
                parcel_id=formatted_apn,
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
            logger.error(f"Orange County address search failed: {e}")
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
                state="CA",
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
            logger.error(f"Orange County owner search failed: {e}")
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
                state="CA",
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

def get_orange_county_tax_record(parcel_id: str) -> Optional[PropertyTaxRecord]:
    """Get Orange County property tax record by APN."""
    async def _get():
        async with OrangeCountyTreasurer() as treasurer:
            return await treasurer.get_tax_record(parcel_id)
    return asyncio.run(_get())


def search_orange_county_tax_by_address(
    address: str,
    city: Optional[str] = None,
    max_results: int = 100
) -> TaxSearchResult:
    """Search Orange County tax records by address."""
    async def _search():
        async with OrangeCountyTreasurer() as treasurer:
            return await treasurer.search_by_address(address, city=city, max_results=max_results)
    return asyncio.run(_search())


def search_orange_county_tax_by_owner(
    owner_name: str,
    max_results: int = 100
) -> TaxSearchResult:
    """Search Orange County tax records by owner name."""
    async def _search():
        async with OrangeCountyTreasurer() as treasurer:
            return await treasurer.search_by_owner(owner_name, max_results=max_results)
    return asyncio.run(_search())
