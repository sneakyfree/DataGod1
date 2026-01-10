"""
Maricopa County, Arizona Treasurer Scraper

Maricopa County Treasurer manages property tax collection for over
1.7 million parcels across Maricopa County, the fourth most populous
county in the United States (includes Phoenix metropolitan area).

Website: https://treasurer.maricopa.gov/
Property Tax Search: https://treasurer.maricopa.gov/taxpayer/

The Maricopa County Treasurer provides:
- Property tax information
- Tax lien certificates
- Payment history
- Over-the-counter tax lien sales
- Tax lien auctions
- Redemption information
- Mobile home taxes

Tax Calendar (Maricopa County, Arizona):
- Tax year: Calendar year (January 1 - December 31)
- First half due: October 1
- First half delinquent: November 1
- Second half due: March 1
- Second half delinquent: May 1
- Tax lien sale: February (certificates on prior year taxes)

Arizona is a tax lien state - county sells liens, not property directly.
Interest rate on liens: 16% per annum (competitive bidding may lower)
Redemption period: 3 years before foreclosure
"""

import asyncio
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import aiohttp

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


class MaricopaCountyTreasurer(CountyTreasurerBase):
    """
    Maricopa County, Arizona Treasurer scraper.

    Uses the Maricopa County Treasurer's property tax portal.
    APN format: XXX-XX-XXX or XXX-XX-XXXX (with optional letter suffix)
    """

    COUNTY_NAME = "Maricopa County"
    STATE = "AZ"
    FIPS_CODE = "04013"
    BASE_URL = "https://treasurer.maricopa.gov/"
    TAX_SEARCH_URL = "https://treasurer.maricopa.gov/taxpayer/"
    SYSTEM_NAME = "Maricopa County Treasurer"

    # API endpoints
    API_BASE = "https://treasurer.maricopa.gov/api/"

    # Tax calendar (Arizona)
    TAX_YEAR_START = "01-01"
    FIRST_HALF_DUE = "10-01"
    FIRST_HALF_DELINQUENT = "11-01"
    SECOND_HALF_DUE = "03-01"
    SECOND_HALF_DELINQUENT = "05-01"

    # Tax lien info
    LIEN_INTEREST_RATE = Decimal("0.16")  # 16% per annum (max)
    REDEMPTION_PERIOD_YEARS = 3

    # Property classifications (Arizona)
    PROPERTY_CLASSES = {
        "1": "Mining (net proceeds)",
        "2": "Commercial/Industrial",
        "3": "Agricultural",
        "4": "Residential",
        "5": "Railroad/Airline Flight",
        "6": "Owner-Occupied Residential",
        "7": "Historic",
        "8": "Rental Residential",
        "9": "Vacant Land",
    }

    # Major taxing entities
    TAXING_ENTITIES = {
        "COUNTY": "Maricopa County",
        "STATE": "State of Arizona",
        "PHX": "City of Phoenix",
        "MESA": "City of Mesa",
        "SCOT": "City of Scottsdale",
        "CHAND": "City of Chandler",
        "GILBERT": "Town of Gilbert",
        "TEMPE": "City of Tempe",
        "GLEN": "City of Glendale",
        "PEORIA": "City of Peoria",
        "FLOOD": "Flood Control District",
        "LIBRARY": "Library District",
        "COLLEGE": "Community College District",
        "SCHOOL": "School District",
        "FIRE": "Fire District",
        "SPEC": "Special District",
    }

    def _format_apn(self, apn: str) -> str:
        """Format APN to standard Maricopa County format: XXX-XX-XXX or XXX-XX-XXXX"""
        # Remove any existing dashes, spaces
        cleaned = re.sub(r"[\s-]", "", apn.upper())

        # Extract digits and optional letter suffix
        match = re.match(r"(\d{3})(\d{2})(\d{3,4})([A-Z])?", cleaned)
        if match:
            book, map_num, parcel, suffix = match.groups()
            base = f"{book}-{map_num}-{parcel}"
            return f"{base}{suffix}" if suffix else base

        return apn  # Return as-is if doesn't match pattern

    async def get_tax_record(
        self,
        parcel_id: str
    ) -> Optional[PropertyTaxRecord]:
        """Get property tax record by APN."""
        formatted_apn = self._format_apn(parcel_id)
        detail_url = f"{self.API_BASE}parcel/{formatted_apn}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"Maricopa County tax record fetch failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_tax_record(json_response)

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

        search_url = f"{self.API_BASE}search/address"

        params = {
            "address": street_address,
            "limit": min(max_results, 100),
        }

        if city:
            params["city"] = city
        if zip_code:
            params["zip"] = zip_code

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Maricopa County address search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                search_criteria=TaxSearchCriteria(property_address=street_address),
                warnings=[str(e)],
            )

        records = []
        results = json_response.get("parcels", json_response.get("results", []))

        for item in results[:max_results]:
            record = self._parse_search_result(item)
            if record:
                records.append(record)

        search_time = int((time.time() - start_time) * 1000)

        return TaxSearchResult(
            records=records,
            total_count=json_response.get("totalCount", len(records)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
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

        search_url = f"{self.API_BASE}search/owner"

        params = {
            "name": owner_name,
            "limit": min(max_results, 100),
        }

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Maricopa County owner search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                search_criteria=TaxSearchCriteria(owner_name=owner_name),
                warnings=[str(e)],
            )

        records = []
        results = json_response.get("parcels", json_response.get("results", []))

        for item in results[:max_results]:
            record = self._parse_search_result(item)
            if record:
                records.append(record)

        search_time = int((time.time() - start_time) * 1000)

        return TaxSearchResult(
            records=records,
            total_count=json_response.get("totalCount", len(records)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=TaxSearchCriteria(owner_name=owner_name),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_delinquent_properties(
        self,
        min_amount: Optional[Decimal] = None,
        max_results: int = 500
    ) -> TaxSearchResult:
        """Get list of delinquent properties."""
        import time
        start_time = time.time()

        delinquent_url = f"{self.API_BASE}delinquent"

        params = {"limit": min(max_results, 500)}
        if min_amount:
            params["minAmount"] = str(min_amount)

        try:
            json_response = await self._fetch_json(delinquent_url, params=params)
        except Exception as e:
            logger.error(f"Maricopa County delinquent list failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                warnings=[str(e)],
            )

        records = []
        results = json_response.get("parcels", json_response.get("results", []))

        for item in results[:max_results]:
            record = self._parse_search_result(item)
            if record:
                record.is_delinquent = True
                record.tax_status = TaxStatus.DELINQUENT
                records.append(record)

        search_time = int((time.time() - start_time) * 1000)

        return TaxSearchResult(
            records=records,
            total_count=json_response.get("totalCount", len(records)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=TaxSearchCriteria(delinquent_only=True, min_amount_due=min_amount),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_tax_sale_properties(
        self,
        sale_type: Optional[TaxSaleType] = None,
        upcoming_only: bool = True,
        max_results: int = 500
    ) -> List[TaxSaleProperty]:
        """Get tax lien certificates available for sale."""
        sale_url = f"{self.API_BASE}taxsale"

        params = {"limit": min(max_results, 500)}
        if upcoming_only:
            params["upcoming"] = "true"
        if sale_type:
            params["type"] = sale_type.value

        try:
            json_response = await self._fetch_json(sale_url, params=params)
        except Exception as e:
            logger.error(f"Maricopa County tax sale list failed: {e}")
            return []

        properties = []
        results = json_response.get("certificates", json_response.get("results", []))

        for item in results[:max_results]:
            prop = self._parse_tax_sale_property(item)
            if prop:
                properties.append(prop)

        return properties

    async def get_tax_liens(
        self,
        parcel_id: Optional[str] = None,
        status: Optional[LienStatus] = None,
        max_results: int = 100
    ) -> List[TaxLien]:
        """Get tax lien certificates."""
        liens_url = f"{self.API_BASE}liens"

        params = {"limit": min(max_results, 100)}
        if parcel_id:
            params["apn"] = self._format_apn(parcel_id)
        if status:
            params["status"] = status.value

        try:
            json_response = await self._fetch_json(liens_url, params=params)
        except Exception as e:
            logger.error(f"Maricopa County tax liens failed: {e}")
            return []

        liens = []
        results = json_response.get("liens", json_response.get("certificates", []))

        for item in results[:max_results]:
            lien = self._parse_tax_lien(item)
            if lien:
                liens.append(lien)

        return liens

    async def get_otc_liens(
        self,
        max_results: int = 500
    ) -> List[TaxLien]:
        """Get over-the-counter (OTC) tax liens available for purchase."""
        otc_url = f"{self.API_BASE}otc"

        params = {"limit": min(max_results, 500)}

        try:
            json_response = await self._fetch_json(otc_url, params=params)
        except Exception as e:
            logger.error(f"Maricopa County OTC liens failed: {e}")
            return []

        liens = []
        results = json_response.get("liens", json_response.get("certificates", []))

        for item in results[:max_results]:
            lien = self._parse_tax_lien(item)
            if lien:
                liens.append(lien)

        return liens

    def _parse_search_result(self, item: Dict[str, Any]) -> Optional[PropertyTaxRecord]:
        """Parse a search result item into PropertyTaxRecord."""
        apn = item.get("apn", item.get("parcelNumber", item.get("parcel", "")))
        if not apn:
            return None

        formatted_apn = self._format_apn(apn)

        # Parse current tax info
        current_tax = self._parse_decimal(str(item.get("totalTax", item.get("taxAmount", ""))))
        balance_due = self._parse_decimal(str(item.get("balanceDue", item.get("amountDue", ""))))
        amount_paid = self._parse_decimal(str(item.get("amountPaid", "")))

        # Determine status
        status_str = item.get("status", item.get("paymentStatus", ""))
        tax_status = self._parse_tax_status(status_str)
        is_delinquent = "DELINQUENT" in str(status_str).upper() or item.get("isDelinquent", False)
        has_lien = item.get("hasLien", item.get("hasCertificate", False))

        # Parse exemptions (Arizona exemptions)
        exemptions = []
        if item.get("seniorFreeze") or item.get("hasSeniorFreeze"):
            exemptions.append("Senior Property Valuation Freeze")
        if item.get("widowExemption"):
            exemptions.append("Widow/Widower Exemption")
        if item.get("disabledExemption"):
            exemptions.append("Disabled Person Exemption")
        if item.get("veteranExemption"):
            exemptions.append("Veteran Exemption")
        for ex in item.get("exemptions", []):
            if ex not in exemptions:
                exemptions.append(ex)

        # Get property class description
        prop_class = item.get("propertyClass", item.get("class", ""))
        prop_class_desc = self.PROPERTY_CLASSES.get(str(prop_class), "")

        return PropertyTaxRecord(
            parcel_id=formatted_apn,
            property_address=item.get("address", item.get("situsAddress")),
            city=item.get("city", item.get("situsCity")),
            state=self.STATE,
            zip_code=item.get("zip", item.get("situsZip")),
            county=self.COUNTY_NAME,
            owner_name=item.get("owner", item.get("ownerName")),
            owner_address=item.get("ownerAddress", item.get("mailingAddress")),
            assessed_value=self._parse_decimal(str(item.get("assessedValue", item.get("limitedValue", "")))),
            taxable_value=self._parse_decimal(str(item.get("taxableValue", item.get("netAssessed", "")))),
            market_value=self._parse_decimal(str(item.get("fullCashValue", item.get("fcv", "")))),
            current_tax_year=self._parse_int(str(item.get("taxYear", ""))),
            current_tax_amount=current_tax,
            current_amount_paid=amount_paid,
            current_balance_due=balance_due,
            tax_status=tax_status,
            is_delinquent=is_delinquent,
            years_delinquent=self._parse_int(str(item.get("yearsDelinquent", "0"))) or 0,
            total_delinquent=self._parse_decimal(str(item.get("totalDelinquent", item.get("priorDue", "")))),
            exemptions=exemptions,
            exemption_amount=self._parse_decimal(str(item.get("exemptionAmount", ""))),
            has_tax_lien=has_lien,
            source_url=f"{self.TAX_SEARCH_URL}?apn={formatted_apn}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_tax_record(self, data: Dict[str, Any]) -> PropertyTaxRecord:
        """Parse detailed tax record data."""
        apn = data.get("apn", data.get("parcelNumber", data.get("parcel", "")))
        formatted_apn = self._format_apn(apn)

        # Parse tax bills
        tax_bills = []
        for bill_data in data.get("taxBills", data.get("taxes", [])):
            bill = self._parse_tax_bill(bill_data, formatted_apn)
            if bill:
                tax_bills.append(bill)

        # Sort bills by year (most recent first)
        tax_bills.sort(key=lambda b: (b.tax_year, b.installment_number or 0), reverse=True)

        # Parse payment history
        payment_history = []
        for payment_data in data.get("payments", data.get("paymentHistory", [])):
            payment = self._parse_payment(payment_data, formatted_apn)
            if payment:
                payment_history.append(payment)

        # Parse liens (tax certificates)
        liens = []
        for lien_data in data.get("liens", data.get("certificates", [])):
            lien = self._parse_tax_lien(lien_data)
            if lien:
                liens.append(lien)

        # Parse exemptions
        exemptions = []
        exemption_amount = Decimal(0)

        if data.get("seniorFreeze") or data.get("hasSeniorFreeze"):
            exemptions.append("Senior Property Valuation Freeze")
        if data.get("widowExemption"):
            exemptions.append("Widow/Widower Exemption")
            exemption_amount += Decimal("3000")
        if data.get("disabledExemption"):
            exemptions.append("Disabled Person Exemption")
            exemption_amount += Decimal("3000")
        if data.get("veteranExemption"):
            exemptions.append("Veteran Exemption")
            exemption_amount += Decimal("3000")

        for ex_data in data.get("exemptions", []):
            if isinstance(ex_data, str):
                if ex_data not in exemptions:
                    exemptions.append(ex_data)
            elif isinstance(ex_data, dict):
                exemptions.append(ex_data.get("type", ex_data.get("name", "Exemption")))
                amt = self._parse_decimal(str(ex_data.get("amount", "")))
                if amt:
                    exemption_amount += amt

        # Parse special assessments
        special_assessments = []
        for assess_data in data.get("specialAssessments", data.get("specialDistricts", [])):
            item = TaxBillItem(
                description=assess_data.get("description", assess_data.get("name", "Special Assessment")),
                amount=self._parse_decimal(str(assess_data.get("amount", ""))) or Decimal(0),
                taxing_authority=assess_data.get("district", assess_data.get("entity")),
                tax_rate=self._parse_decimal(str(assess_data.get("rate", ""))),
                raw_data=assess_data,
            )
            special_assessments.append(item)

        # Calculate totals
        current_tax = self._parse_decimal(str(data.get("totalTax", data.get("currentYearTax", ""))))
        balance_due = self._parse_decimal(str(data.get("balanceDue", data.get("totalDue", ""))))
        amount_paid = self._parse_decimal(str(data.get("amountPaid", "")))
        total_delinquent = self._parse_decimal(str(data.get("totalDelinquent", data.get("priorYearsDue", ""))))

        # Determine status
        status_str = data.get("status", data.get("paymentStatus", ""))
        tax_status = self._parse_tax_status(status_str)
        is_delinquent = "DELINQUENT" in str(status_str).upper() or data.get("isDelinquent", False)
        has_lien = len(liens) > 0 or data.get("hasCertificate", False)

        if not is_delinquent and total_delinquent and total_delinquent > 0:
            is_delinquent = True

        if is_delinquent:
            tax_status = TaxStatus.DELINQUENT

        return PropertyTaxRecord(
            parcel_id=formatted_apn,
            property_address=data.get("address", data.get("situsAddress")),
            city=data.get("city", data.get("situsCity")),
            state=self.STATE,
            zip_code=data.get("zip", data.get("situsZip")),
            county=self.COUNTY_NAME,
            owner_name=data.get("owner", data.get("ownerName")),
            owner_address=data.get("ownerAddress", data.get("mailingAddress")),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", data.get("limitedValue", "")))),
            taxable_value=self._parse_decimal(str(data.get("taxableValue", data.get("netAssessed", "")))),
            market_value=self._parse_decimal(str(data.get("fullCashValue", data.get("fcv", "")))),
            current_tax_year=self._parse_int(str(data.get("taxYear", ""))),
            current_tax_amount=current_tax,
            current_amount_paid=amount_paid,
            current_balance_due=balance_due,
            tax_status=tax_status,
            is_delinquent=is_delinquent,
            years_delinquent=self._parse_int(str(data.get("yearsDelinquent", "0"))) or 0,
            total_delinquent=total_delinquent,
            exemptions=exemptions,
            exemption_amount=exemption_amount if exemption_amount > 0 else None,
            tax_bills=tax_bills,
            payment_history=payment_history,
            has_tax_lien=has_lien,
            liens=liens,
            special_assessments=special_assessments,
            source_url=f"{self.TAX_SEARCH_URL}?apn={formatted_apn}",
            source_system=self.SYSTEM_NAME,
            last_updated=self._parse_datetime(data.get("lastUpdated", "")),
            raw_data=data,
        )

    def _parse_tax_bill(self, data: Dict[str, Any], apn: str) -> Optional[TaxBill]:
        """Parse a tax bill record."""
        tax_year = self._parse_int(str(data.get("taxYear", data.get("year", ""))))
        if not tax_year:
            return None

        # Parse line items (from different taxing entities)
        line_items = []
        for item_data in data.get("lineItems", data.get("entities", data.get("taxingJurisdictions", []))):
            entity_code = item_data.get("code", item_data.get("entityCode", ""))
            entity_name = self.TAXING_ENTITIES.get(entity_code, item_data.get("name", item_data.get("jurisdiction", "")))

            item = TaxBillItem(
                description=entity_name or item_data.get("description", ""),
                amount=self._parse_decimal(str(item_data.get("amount", item_data.get("tax", "")))) or Decimal(0),
                taxing_authority=entity_name,
                tax_rate=self._parse_decimal(str(item_data.get("rate", ""))),
                assessed_value=self._parse_decimal(str(item_data.get("netAssessed", ""))),
                raw_data=item_data,
            )
            line_items.append(item)

        # Determine installment
        installment = self._parse_int(str(data.get("installment", "")))
        half = data.get("half", data.get("period", ""))
        if "FIRST" in str(half).upper() or "1ST" in str(half).upper():
            installment = 1
        elif "SECOND" in str(half).upper() or "2ND" in str(half).upper():
            installment = 2

        return TaxBill(
            bill_number=data.get("billNumber", data.get("statementId")),
            tax_year=tax_year,
            parcel_id=apn,
            property_address=data.get("address", data.get("situsAddress")),
            owner_name=data.get("owner", data.get("ownerName")),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", data.get("limitedValue", "")))),
            taxable_value=self._parse_decimal(str(data.get("netAssessed", data.get("taxableValue", "")))),
            tax_rate=self._parse_decimal(str(data.get("combinedRate", data.get("taxRate", "")))),
            gross_tax=self._parse_decimal(str(data.get("grossTax", data.get("totalTax", "")))),
            exemptions=self._parse_decimal(str(data.get("exemptions", ""))),
            net_tax=self._parse_decimal(str(data.get("netTax", ""))),
            penalties=self._parse_decimal(str(data.get("penalty", data.get("interest", "")))),
            interest=self._parse_decimal(str(data.get("interest", ""))),
            fees=self._parse_decimal(str(data.get("costs", data.get("fees", "")))),
            total_due=self._parse_decimal(str(data.get("totalDue", data.get("amountDue", "")))),
            amount_paid=self._parse_decimal(str(data.get("amountPaid", ""))),
            balance_due=self._parse_decimal(str(data.get("balanceDue", ""))),
            payment_status=self._parse_tax_status(data.get("status", "")),
            bill_date=self._parse_date(data.get("billDate", "")),
            due_date=self._parse_date(data.get("dueDate", "")),
            delinquent_date=self._parse_date(data.get("delinquentDate", "")),
            installment_number=installment,
            total_installments=2,  # Arizona has 2 installments
            line_items=line_items,
            source_url=f"{self.TAX_SEARCH_URL}?apn={apn}&year={tax_year}",
            raw_data=data,
        )

    def _parse_payment(self, data: Dict[str, Any], apn: str) -> Optional[TaxPayment]:
        """Parse a payment record."""
        payment_date = self._parse_date(data.get("paymentDate", data.get("date", "")))
        amount = self._parse_decimal(str(data.get("amount", data.get("paymentAmount", ""))))

        if not amount:
            return None

        # Parse payment method
        method_str = data.get("paymentMethod", data.get("method", data.get("type", "")))
        method = PaymentMethod.UNKNOWN
        if method_str:
            upper = method_str.upper()
            if "CHECK" in upper:
                method = PaymentMethod.CHECK
            elif "CASH" in upper:
                method = PaymentMethod.CASH
            elif "CREDIT" in upper or "CARD" in upper:
                method = PaymentMethod.CREDIT_CARD
            elif "ACH" in upper or "EFT" in upper or "ELECTRONIC" in upper:
                method = PaymentMethod.ACH
            elif "ESCROW" in upper:
                method = PaymentMethod.ESCROW
            elif "ONLINE" in upper or "WEB" in upper:
                method = PaymentMethod.ONLINE

        return TaxPayment(
            payment_id=data.get("paymentId", data.get("transactionId", data.get("receiptNumber"))),
            parcel_id=apn,
            tax_year=self._parse_int(str(data.get("taxYear", ""))) or 0,
            payment_date=payment_date,
            payment_amount=amount,
            payment_method=method,
            principal_paid=self._parse_decimal(str(data.get("principal", data.get("taxPaid", "")))),
            interest_paid=self._parse_decimal(str(data.get("interest", ""))),
            penalty_paid=self._parse_decimal(str(data.get("penalty", ""))),
            fees_paid=self._parse_decimal(str(data.get("costs", data.get("fees", "")))),
            receipt_number=data.get("receiptNumber", data.get("confirmationNumber")),
            check_number=data.get("checkNumber"),
            payer_name=data.get("payer", data.get("payerName")),
            installment_number=self._parse_int(str(data.get("installment", data.get("half", "")))),
            raw_data=data,
        )

    def _parse_tax_lien(self, data: Dict[str, Any]) -> Optional[TaxLien]:
        """Parse a tax lien certificate record."""
        cert_number = data.get("certificateNumber", data.get("certNumber", data.get("lienNumber", "")))
        apn = data.get("apn", data.get("parcelNumber", ""))

        if not cert_number and not apn:
            return None

        formatted_apn = self._format_apn(apn) if apn else ""

        # Parse tax years covered
        tax_years = data.get("taxYears", data.get("years", []))
        if isinstance(tax_years, str):
            tax_years = [int(y.strip()) for y in tax_years.split(",") if y.strip().isdigit()]
        elif isinstance(tax_years, int):
            tax_years = [tax_years]

        # Calculate redemption deadline (3 years from sale in Arizona)
        sale_date = self._parse_date(data.get("saleDate", ""))
        redemption_deadline = None
        if sale_date:
            from datetime import timedelta
            redemption_deadline = date(
                sale_date.year + self.REDEMPTION_PERIOD_YEARS,
                sale_date.month,
                sale_date.day
            )

        return TaxLien(
            lien_number=str(cert_number) if cert_number else f"CERT-{formatted_apn}",
            parcel_id=formatted_apn,
            lien_date=sale_date,
            lien_amount=self._parse_decimal(str(data.get("faceAmount", data.get("purchaseAmount", "")))),
            face_value=self._parse_decimal(str(data.get("faceAmount", data.get("taxAmount", "")))),
            interest_rate=self._parse_decimal(str(data.get("interestRate", data.get("bidRate", "")))) or self.LIEN_INTEREST_RATE,
            accrued_interest=self._parse_decimal(str(data.get("accruedInterest", ""))),
            penalties=self._parse_decimal(str(data.get("subTaxes", data.get("subsequentTaxes", "")))),
            total_due=self._parse_decimal(str(data.get("redemptionAmount", data.get("totalDue", "")))),
            status=self._parse_lien_status(data.get("status", "")),
            property_address=data.get("address", data.get("situsAddress")),
            owner_name=data.get("owner", data.get("ownerName")),
            legal_description=data.get("legalDescription"),
            tax_years=tax_years,
            holder_name=data.get("holder", data.get("investor", data.get("purchaser"))),
            holder_address=data.get("holderAddress", data.get("investorAddress")),
            assignment_date=self._parse_date(data.get("assignmentDate", "")),
            redemption_date=self._parse_date(data.get("redemptionDate", "")),
            redemption_amount=self._parse_decimal(str(data.get("redemptionAmount", ""))),
            redemption_deadline=redemption_deadline or self._parse_date(data.get("redemptionDeadline", "")),
            sale_date=sale_date,
            sale_type=TaxSaleType.TAX_LIEN_SALE,  # Arizona is a lien state
            sale_amount=self._parse_decimal(str(data.get("purchaseAmount", data.get("bidAmount", "")))),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.BASE_URL}certificate/{cert_number}",
            raw_data=data,
        )

    def _parse_tax_sale_property(self, data: Dict[str, Any]) -> Optional[TaxSaleProperty]:
        """Parse a tax sale property listing (tax lien certificate)."""
        apn = data.get("apn", data.get("parcelNumber", ""))
        if not apn:
            return None

        formatted_apn = self._format_apn(apn)

        # Parse delinquent years
        tax_years = data.get("taxYears", data.get("years", []))
        if isinstance(tax_years, str):
            tax_years = [int(y.strip()) for y in tax_years.split(",") if y.strip().isdigit()]
        elif isinstance(tax_years, int):
            tax_years = [tax_years]

        # Determine sale type
        is_otc = data.get("isOTC", data.get("overTheCounter", False))
        sale_type = TaxSaleType.OVER_THE_COUNTER if is_otc else TaxSaleType.TAX_LIEN_SALE

        return TaxSaleProperty(
            sale_id=data.get("saleId", data.get("certificateNumber", data.get("itemNumber"))),
            parcel_id=formatted_apn,
            property_address=data.get("address", data.get("situsAddress")),
            city=data.get("city", data.get("situsCity")),
            zip_code=data.get("zip", data.get("situsZip")),
            legal_description=data.get("legalDescription"),
            property_type=self.PROPERTY_CLASSES.get(str(data.get("propertyClass", "")), data.get("propertyType")),
            owner_name=data.get("owner", data.get("ownerName")),
            owner_address=data.get("ownerAddress", data.get("mailingAddress")),
            tax_years_delinquent=tax_years,
            total_taxes_due=self._parse_decimal(str(data.get("taxesDue", ""))),
            penalties_due=self._parse_decimal(str(data.get("interest", ""))),
            interest_due=self._parse_decimal(str(data.get("interest", ""))),
            fees_due=self._parse_decimal(str(data.get("costs", ""))),
            total_amount_due=self._parse_decimal(str(data.get("faceAmount", data.get("openingBid", "")))),
            sale_type=sale_type,
            sale_date=self._parse_date(data.get("saleDate", "")),
            auction_date=self._parse_date(data.get("auctionDate", data.get("saleDate", ""))),
            minimum_bid=self._parse_decimal(str(data.get("faceAmount", data.get("openingBid", "")))),
            opening_bid=self._parse_decimal(str(data.get("openingBid", ""))),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", data.get("limitedValue", "")))),
            market_value=self._parse_decimal(str(data.get("fullCashValue", data.get("fcv", "")))),
            status=data.get("status", ""),
            sold=data.get("sold", False),
            winning_bid=self._parse_decimal(str(data.get("winningBid", data.get("purchaseAmount", "")))),
            winning_bidder=data.get("buyer", data.get("investor")),
            redemption_period_ends=self._parse_date(data.get("redemptionDeadline", "")),
            redeemable=True,  # Arizona liens are redeemable for 3 years
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.BASE_URL}taxsale?apn={formatted_apn}",
            raw_data=data,
        )

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """Parse a datetime string."""
        if not dt_str or dt_str.strip() == "":
            return None

        dt_str = dt_str.strip()

        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %I:%M %p",
            "%Y-%m-%dT%H:%M:%SZ",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue

        # Try parsing as date only
        d = self._parse_date(dt_str)
        if d:
            return datetime.combine(d, datetime.min.time())

        return None


# Convenience functions

def get_maricopa_county_tax_record(parcel_id: str) -> Optional[PropertyTaxRecord]:
    """Get Maricopa County tax record by APN."""
    treasurer = MaricopaCountyTreasurer()

    async def _get():
        async with treasurer:
            return await treasurer.get_tax_record(parcel_id)
    return asyncio.run(_get())


def search_maricopa_county_by_address(
    street_address: str,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    **kwargs
) -> TaxSearchResult:
    """Search Maricopa County tax records by address."""
    treasurer = MaricopaCountyTreasurer()

    async def _search():
        async with treasurer:
            return await treasurer.search_by_address(street_address, city, zip_code, **kwargs)
    return asyncio.run(_search())


def search_maricopa_county_by_owner(owner_name: str, **kwargs) -> TaxSearchResult:
    """Search Maricopa County tax records by owner name."""
    treasurer = MaricopaCountyTreasurer()

    async def _search():
        async with treasurer:
            return await treasurer.search_by_owner(owner_name, **kwargs)
    return asyncio.run(_search())
