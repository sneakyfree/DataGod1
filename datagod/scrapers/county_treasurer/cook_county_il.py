"""
Cook County, Illinois Treasurer Scraper

Cook County Treasurer's Office manages property tax collection for
over 1.8 million parcels across Cook County, the second largest
county in the United States by population.

Website: https://www.cookcountytreasurer.com/
Property Tax Search: https://www.cookcountytreasurer.com/setsearchparameters.aspx

The Cook County Treasurer provides:
- Current and prior year tax bills
- Payment history
- Tax sale information (annual scavenger sale)
- Delinquent tax lists
- Tax redemption information
- Estimated tax calculator

Tax Calendar (Cook County):
- First installment due: March 1
- Second installment due: Typically August (varies)
- Delinquent: After due dates + grace period
- Tax sale: Annual (November)
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


class CookCountyTreasurer(CountyTreasurerBase):
    """
    Cook County, Illinois Treasurer scraper.

    Uses the Cook County Treasurer's property tax portal.
    PIN format: XX-XX-XXX-XXX-XXXX (14 digits with dashes)
    """

    COUNTY_NAME = "Cook County"
    STATE = "IL"
    FIPS_CODE = "17031"
    BASE_URL = "https://www.cookcountytreasurer.com/"
    TAX_SEARCH_URL = "https://www.cookcountytreasurer.com/setsearchparameters.aspx"
    SYSTEM_NAME = "Cook County Treasurer Property Tax System"

    # API endpoints
    API_BASE = "https://www.cookcountytreasurer.com/api/"

    # Tax calendar (Cook County)
    TAX_YEAR_START = "01-01"
    FIRST_INSTALLMENT_DUE = "03-01"
    SECOND_INSTALLMENT_DUE = "08-01"  # Varies each year
    DELINQUENT_DATE = "09-01"

    # Township codes
    TOWNSHIPS = {
        "10": "Barrington",
        "11": "Berwyn",
        "12": "Bloom",
        "13": "Bremen",
        "14": "Calumet",
        "15": "Cicero",
        "16": "Elk Grove",
        "17": "Evanston",
        "18": "Hanover",
        "19": "Lemont",
        "20": "Leyden",
        "21": "Lyons",
        "22": "Maine",
        "23": "New Trier",
        "24": "Niles",
        "25": "Northfield",
        "26": "Norwood Park",
        "27": "Oak Park",
        "28": "Orland",
        "29": "Palatine",
        "30": "Palos",
        "31": "Proviso",
        "32": "Rich",
        "33": "River Forest",
        "34": "Riverside",
        "35": "Schaumburg",
        "36": "Stickney",
        "37": "Thornton",
        "38": "Wheeling",
        "39": "Worth",
        "70": "Hyde Park",
        "71": "Jefferson",
        "72": "Lake",
        "73": "Lake View",
        "74": "North Chicago",
        "75": "Rogers Park",
        "76": "South Chicago",
        "77": "West Chicago",
    }

    # Tax districts / levying bodies
    TAX_DISTRICTS = {
        "CITY": "City of Chicago",
        "COUNTY": "Cook County",
        "SCHOOL": "School District",
        "PARK": "Park District",
        "WATER": "Water Reclamation",
        "FOREST": "Forest Preserve",
        "LIBRARY": "Library District",
        "FIRE": "Fire Protection District",
        "MOSQUITO": "Mosquito Abatement",
        "TIF": "Tax Increment Financing",
    }

    def _format_pin(self, pin: str) -> str:
        """Format PIN to standard Cook County format: XX-XX-XXX-XXX-XXXX"""
        # Remove any existing dashes or spaces
        digits = re.sub(r"[^0-9]", "", pin)

        if len(digits) != 14:
            return pin  # Return as-is if not 14 digits

        return f"{digits[0:2]}-{digits[2:4]}-{digits[4:7]}-{digits[7:10]}-{digits[10:14]}"

    def _parse_pin(self, pin: str) -> Dict[str, str]:
        """Parse PIN into components."""
        digits = re.sub(r"[^0-9]", "", pin)

        if len(digits) != 14:
            return {"raw": pin}

        return {
            "township": digits[0:2],
            "section": digits[2:4],
            "block": digits[4:7],
            "parcel": digits[7:10],
            "suffix": digits[10:14],
            "formatted": self._format_pin(pin),
            "township_name": self.TOWNSHIPS.get(digits[0:2], "Unknown"),
        }

    async def get_tax_record(
        self,
        parcel_id: str
    ) -> Optional[PropertyTaxRecord]:
        """Get property tax record by PIN."""
        formatted_pin = self._format_pin(parcel_id)
        detail_url = f"{self.API_BASE}property/{formatted_pin}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"Cook County tax record fetch failed: {e}")
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
            logger.error(f"Cook County address search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                search_criteria=TaxSearchCriteria(property_address=street_address),
                warnings=[str(e)],
            )

        records = []
        results = json_response.get("properties", json_response.get("results", []))

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
            search_criteria=TaxSearchCriteria(
                property_address=street_address,
            ),
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
            logger.error(f"Cook County owner search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                search_criteria=TaxSearchCriteria(owner_name=owner_name),
                warnings=[str(e)],
            )

        records = []
        results = json_response.get("properties", json_response.get("results", []))

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
            logger.error(f"Cook County delinquent list failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                warnings=[str(e)],
            )

        records = []
        results = json_response.get("properties", json_response.get("results", []))

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
        """Get properties scheduled for tax sale (scavenger sale)."""
        sale_url = f"{self.API_BASE}taxsale"

        params = {"limit": min(max_results, 500)}
        if upcoming_only:
            params["upcoming"] = "true"
        if sale_type:
            params["type"] = sale_type.value

        try:
            json_response = await self._fetch_json(sale_url, params=params)
        except Exception as e:
            logger.error(f"Cook County tax sale list failed: {e}")
            return []

        properties = []
        results = json_response.get("properties", json_response.get("results", []))

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
        """Get tax liens (sold taxes)."""
        liens_url = f"{self.API_BASE}liens"

        params = {"limit": min(max_results, 100)}
        if parcel_id:
            params["pin"] = self._format_pin(parcel_id)
        if status:
            params["status"] = status.value

        try:
            json_response = await self._fetch_json(liens_url, params=params)
        except Exception as e:
            logger.error(f"Cook County tax liens failed: {e}")
            return []

        liens = []
        results = json_response.get("liens", json_response.get("results", []))

        for item in results[:max_results]:
            lien = self._parse_tax_lien(item)
            if lien:
                liens.append(lien)

        return liens

    def _parse_search_result(self, item: Dict[str, Any]) -> Optional[PropertyTaxRecord]:
        """Parse a search result item into PropertyTaxRecord."""
        pin = item.get("pin", item.get("parcelId", ""))
        if not pin:
            return None

        formatted_pin = self._format_pin(pin)
        pin_parts = self._parse_pin(pin)

        # Parse current tax info
        current_tax = self._parse_decimal(str(item.get("totalTax", item.get("taxAmount", ""))))
        balance_due = self._parse_decimal(str(item.get("balanceDue", item.get("amountDue", ""))))
        amount_paid = self._parse_decimal(str(item.get("amountPaid", "")))

        # Determine status
        status_str = item.get("status", item.get("paymentStatus", ""))
        tax_status = self._parse_tax_status(status_str)
        is_delinquent = "DELINQUENT" in str(status_str).upper() or (balance_due and balance_due > 0)

        # Parse exemptions
        exemptions = item.get("exemptions", [])
        if isinstance(exemptions, str):
            exemptions = [e.strip() for e in exemptions.split(",") if e.strip()]

        return PropertyTaxRecord(
            parcel_id=formatted_pin,
            property_address=item.get("address", item.get("propertyAddress")),
            city=item.get("city", item.get("municipality")),
            state=self.STATE,
            zip_code=item.get("zip", item.get("zipCode")),
            county=self.COUNTY_NAME,
            owner_name=item.get("owner", item.get("ownerName")),
            owner_address=item.get("ownerAddress", item.get("mailingAddress")),
            assessed_value=self._parse_decimal(str(item.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(str(item.get("taxableValue", item.get("equalized", "")))),
            market_value=self._parse_decimal(str(item.get("marketValue", ""))),
            current_tax_year=self._parse_int(str(item.get("taxYear", ""))),
            current_tax_amount=current_tax,
            current_amount_paid=amount_paid,
            current_balance_due=balance_due,
            tax_status=tax_status,
            is_delinquent=is_delinquent,
            years_delinquent=self._parse_int(str(item.get("yearsDelinquent", "0"))) or 0,
            total_delinquent=self._parse_decimal(str(item.get("totalDelinquent", ""))),
            exemptions=exemptions,
            exemption_amount=self._parse_decimal(str(item.get("exemptionAmount", ""))),
            has_tax_lien=item.get("hasTaxLien", item.get("soldTax", False)),
            source_url=f"{self.TAX_SEARCH_URL}?pin={formatted_pin}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_tax_record(self, data: Dict[str, Any]) -> PropertyTaxRecord:
        """Parse detailed tax record data."""
        pin = data.get("pin", data.get("parcelId", ""))
        formatted_pin = self._format_pin(pin)
        pin_parts = self._parse_pin(pin)

        # Parse tax bills
        tax_bills = []
        for bill_data in data.get("taxBills", data.get("bills", [])):
            bill = self._parse_tax_bill(bill_data, formatted_pin)
            if bill:
                tax_bills.append(bill)

        # Sort bills by year (most recent first)
        tax_bills.sort(key=lambda b: b.tax_year, reverse=True)

        # Parse payment history
        payment_history = []
        for payment_data in data.get("payments", data.get("paymentHistory", [])):
            payment = self._parse_payment(payment_data, formatted_pin)
            if payment:
                payment_history.append(payment)

        # Parse liens
        liens = []
        for lien_data in data.get("liens", data.get("soldTaxes", [])):
            lien = self._parse_tax_lien(lien_data)
            if lien:
                liens.append(lien)

        # Parse exemptions
        exemptions = data.get("exemptions", [])
        if isinstance(exemptions, str):
            exemptions = [e.strip() for e in exemptions.split(",") if e.strip()]

        # Parse special assessments
        special_assessments = []
        for assess_data in data.get("specialAssessments", []):
            item = TaxBillItem(
                description=assess_data.get("description", "Special Assessment"),
                amount=self._parse_decimal(str(assess_data.get("amount", ""))) or Decimal(0),
                taxing_authority=assess_data.get("authority"),
                raw_data=assess_data,
            )
            special_assessments.append(item)

        # Calculate totals
        current_tax = self._parse_decimal(str(data.get("totalTax", data.get("currentTax", ""))))
        balance_due = self._parse_decimal(str(data.get("balanceDue", data.get("totalDue", ""))))
        amount_paid = self._parse_decimal(str(data.get("amountPaid", "")))
        total_delinquent = self._parse_decimal(str(data.get("totalDelinquent", data.get("priorDue", ""))))

        # Determine status
        status_str = data.get("status", data.get("paymentStatus", ""))
        tax_status = self._parse_tax_status(status_str)
        is_delinquent = "DELINQUENT" in str(status_str).upper() or bool(total_delinquent and total_delinquent > 0)

        return PropertyTaxRecord(
            parcel_id=formatted_pin,
            property_address=data.get("address", data.get("propertyAddress")),
            city=data.get("city", data.get("municipality")),
            state=self.STATE,
            zip_code=data.get("zip", data.get("zipCode")),
            county=self.COUNTY_NAME,
            owner_name=data.get("owner", data.get("ownerName")),
            owner_address=data.get("ownerAddress", data.get("mailingAddress")),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(str(data.get("taxableValue", data.get("equalized", "")))),
            market_value=self._parse_decimal(str(data.get("marketValue", ""))),
            current_tax_year=self._parse_int(str(data.get("taxYear", ""))),
            current_tax_amount=current_tax,
            current_amount_paid=amount_paid,
            current_balance_due=balance_due,
            tax_status=tax_status,
            is_delinquent=is_delinquent,
            years_delinquent=self._parse_int(str(data.get("yearsDelinquent", "0"))) or 0,
            total_delinquent=total_delinquent,
            exemptions=exemptions,
            exemption_amount=self._parse_decimal(str(data.get("exemptionAmount", ""))),
            tax_bills=tax_bills,
            payment_history=payment_history,
            has_tax_lien=len(liens) > 0 or data.get("hasSoldTax", False),
            liens=liens,
            special_assessments=special_assessments,
            source_url=f"{self.TAX_SEARCH_URL}?pin={formatted_pin}",
            source_system=self.SYSTEM_NAME,
            last_updated=self._parse_datetime(data.get("lastUpdated", "")),
            raw_data=data,
        )

    def _parse_tax_bill(self, data: Dict[str, Any], pin: str) -> Optional[TaxBill]:
        """Parse a tax bill record."""
        tax_year = self._parse_int(str(data.get("taxYear", data.get("year", ""))))
        if not tax_year:
            return None

        # Parse line items
        line_items = []
        for item_data in data.get("lineItems", data.get("taxingBodies", [])):
            item = TaxBillItem(
                description=item_data.get("description", item_data.get("name", "")),
                amount=self._parse_decimal(str(item_data.get("amount", item_data.get("tax", "")))) or Decimal(0),
                taxing_authority=item_data.get("authority", item_data.get("district")),
                tax_rate=self._parse_decimal(str(item_data.get("rate", ""))),
                assessed_value=self._parse_decimal(str(item_data.get("eav", ""))),
                raw_data=item_data,
            )
            line_items.append(item)

        return TaxBill(
            bill_number=data.get("billNumber", data.get("billId")),
            tax_year=tax_year,
            parcel_id=pin,
            property_address=data.get("address"),
            owner_name=data.get("owner"),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(str(data.get("eav", data.get("taxableValue", "")))),
            tax_rate=self._parse_decimal(str(data.get("taxRate", data.get("rate", "")))),
            gross_tax=self._parse_decimal(str(data.get("grossTax", data.get("totalTax", "")))),
            exemptions=self._parse_decimal(str(data.get("exemptionAmount", ""))),
            net_tax=self._parse_decimal(str(data.get("netTax", ""))),
            penalties=self._parse_decimal(str(data.get("penalty", data.get("penalties", "")))),
            interest=self._parse_decimal(str(data.get("interest", ""))),
            fees=self._parse_decimal(str(data.get("fees", data.get("costs", "")))),
            total_due=self._parse_decimal(str(data.get("totalDue", data.get("amountDue", "")))),
            amount_paid=self._parse_decimal(str(data.get("amountPaid", ""))),
            balance_due=self._parse_decimal(str(data.get("balanceDue", ""))),
            payment_status=self._parse_tax_status(data.get("status", "")),
            bill_date=self._parse_date(data.get("billDate", "")),
            due_date=self._parse_date(data.get("dueDate", "")),
            delinquent_date=self._parse_date(data.get("delinquentDate", "")),
            installment_number=self._parse_int(str(data.get("installment", ""))),
            total_installments=2,  # Cook County has 2 installments
            line_items=line_items,
            source_url=f"{self.TAX_SEARCH_URL}?pin={pin}&year={tax_year}",
            raw_data=data,
        )

    def _parse_payment(self, data: Dict[str, Any], pin: str) -> Optional[TaxPayment]:
        """Parse a payment record."""
        payment_date = self._parse_date(data.get("paymentDate", data.get("date", "")))
        amount = self._parse_decimal(str(data.get("amount", data.get("paymentAmount", ""))))

        if not amount:
            return None

        # Parse payment method
        method_str = data.get("paymentMethod", data.get("method", ""))
        method = PaymentMethod.UNKNOWN
        if method_str:
            upper = method_str.upper()
            if "CHECK" in upper:
                method = PaymentMethod.CHECK
            elif "CASH" in upper:
                method = PaymentMethod.CASH
            elif "CREDIT" in upper:
                method = PaymentMethod.CREDIT_CARD
            elif "DEBIT" in upper:
                method = PaymentMethod.DEBIT_CARD
            elif "ACH" in upper or "EFT" in upper:
                method = PaymentMethod.ACH
            elif "ESCROW" in upper:
                method = PaymentMethod.ESCROW
            elif "ONLINE" in upper:
                method = PaymentMethod.ONLINE

        return TaxPayment(
            payment_id=data.get("paymentId", data.get("transactionId")),
            parcel_id=pin,
            tax_year=self._parse_int(str(data.get("taxYear", ""))) or 0,
            payment_date=payment_date,
            payment_amount=amount,
            payment_method=method,
            principal_paid=self._parse_decimal(str(data.get("principal", ""))),
            interest_paid=self._parse_decimal(str(data.get("interest", ""))),
            penalty_paid=self._parse_decimal(str(data.get("penalty", ""))),
            fees_paid=self._parse_decimal(str(data.get("fees", ""))),
            receipt_number=data.get("receiptNumber", data.get("confirmationNumber")),
            check_number=data.get("checkNumber"),
            payer_name=data.get("payer", data.get("payerName")),
            installment_number=self._parse_int(str(data.get("installment", ""))),
            raw_data=data,
        )

    def _parse_tax_lien(self, data: Dict[str, Any]) -> Optional[TaxLien]:
        """Parse a tax lien (sold tax) record."""
        lien_number = data.get("lienNumber", data.get("certificateNumber", data.get("saleId", "")))
        parcel_id = data.get("pin", data.get("parcelId", ""))

        if not lien_number and not parcel_id:
            return None

        # Parse tax years covered
        tax_years = data.get("taxYears", [])
        if isinstance(tax_years, str):
            tax_years = [int(y.strip()) for y in tax_years.split(",") if y.strip().isdigit()]
        elif isinstance(tax_years, int):
            tax_years = [tax_years]

        return TaxLien(
            lien_number=str(lien_number) if lien_number else f"LIEN-{parcel_id}",
            parcel_id=self._format_pin(parcel_id) if parcel_id else "",
            lien_date=self._parse_date(data.get("saleDate", data.get("lienDate", ""))),
            lien_amount=self._parse_decimal(str(data.get("lienAmount", data.get("saleAmount", "")))),
            face_value=self._parse_decimal(str(data.get("faceValue", data.get("taxAmount", "")))),
            interest_rate=self._parse_decimal(str(data.get("interestRate", data.get("rate", "")))),
            accrued_interest=self._parse_decimal(str(data.get("accruedInterest", ""))),
            penalties=self._parse_decimal(str(data.get("penalties", ""))),
            total_due=self._parse_decimal(str(data.get("totalDue", data.get("redemptionAmount", "")))),
            status=self._parse_lien_status(data.get("status", "")),
            property_address=data.get("address", data.get("propertyAddress")),
            owner_name=data.get("owner", data.get("ownerName")),
            legal_description=data.get("legalDescription"),
            tax_years=tax_years,
            holder_name=data.get("buyer", data.get("holderName", data.get("purchaser"))),
            holder_address=data.get("buyerAddress", data.get("holderAddress")),
            assignment_date=self._parse_date(data.get("assignmentDate", "")),
            redemption_date=self._parse_date(data.get("redemptionDate", "")),
            redemption_amount=self._parse_decimal(str(data.get("redemptionAmount", ""))),
            redemption_deadline=self._parse_date(data.get("redemptionDeadline", data.get("expirationDate", ""))),
            sale_date=self._parse_date(data.get("saleDate", "")),
            sale_type=TaxSaleType.SCAVENGER_SALE if data.get("isScavenger") else self._parse_sale_type(data.get("saleType", "")),
            sale_amount=self._parse_decimal(str(data.get("saleAmount", data.get("winningBid", "")))),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.BASE_URL}taxsale?lien={lien_number}",
            raw_data=data,
        )

    def _parse_tax_sale_property(self, data: Dict[str, Any]) -> Optional[TaxSaleProperty]:
        """Parse a tax sale property listing."""
        parcel_id = data.get("pin", data.get("parcelId", ""))
        if not parcel_id:
            return None

        formatted_pin = self._format_pin(parcel_id)

        # Parse delinquent years
        tax_years = data.get("taxYears", data.get("yearsDelinquent", []))
        if isinstance(tax_years, str):
            tax_years = [int(y.strip()) for y in tax_years.split(",") if y.strip().isdigit()]
        elif isinstance(tax_years, int):
            tax_years = [tax_years]

        return TaxSaleProperty(
            sale_id=data.get("saleId", data.get("itemNumber")),
            parcel_id=formatted_pin,
            property_address=data.get("address", data.get("propertyAddress")),
            city=data.get("city", data.get("municipality")),
            zip_code=data.get("zip", data.get("zipCode")),
            legal_description=data.get("legalDescription"),
            property_type=data.get("propertyType", data.get("class")),
            owner_name=data.get("owner", data.get("ownerName")),
            owner_address=data.get("ownerAddress"),
            tax_years_delinquent=tax_years,
            total_taxes_due=self._parse_decimal(str(data.get("taxesDue", ""))),
            penalties_due=self._parse_decimal(str(data.get("penalties", ""))),
            interest_due=self._parse_decimal(str(data.get("interest", ""))),
            fees_due=self._parse_decimal(str(data.get("fees", data.get("costs", "")))),
            total_amount_due=self._parse_decimal(str(data.get("totalDue", data.get("openingBid", "")))),
            sale_type=TaxSaleType.SCAVENGER_SALE,  # Cook County uses scavenger sale
            sale_date=self._parse_date(data.get("saleDate", "")),
            auction_date=self._parse_date(data.get("auctionDate", data.get("saleDate", ""))),
            minimum_bid=self._parse_decimal(str(data.get("minimumBid", data.get("openingBid", "")))),
            opening_bid=self._parse_decimal(str(data.get("openingBid", ""))),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            market_value=self._parse_decimal(str(data.get("marketValue", ""))),
            status=data.get("status", ""),
            sold=data.get("sold", False),
            winning_bid=self._parse_decimal(str(data.get("winningBid", ""))),
            winning_bidder=data.get("winner", data.get("buyer")),
            redemption_period_ends=self._parse_date(data.get("redemptionDeadline", "")),
            redeemable=data.get("redeemable", True),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.BASE_URL}taxsale?pin={formatted_pin}",
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

def get_cook_county_tax_record(parcel_id: str) -> Optional[PropertyTaxRecord]:
    """Get Cook County tax record by PIN."""
    treasurer = CookCountyTreasurer()

    async def _get():
        async with treasurer:
            return await treasurer.get_tax_record(parcel_id)
    return asyncio.run(_get())


def search_cook_county_by_address(
    street_address: str,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    **kwargs
) -> TaxSearchResult:
    """Search Cook County tax records by address."""
    treasurer = CookCountyTreasurer()

    async def _search():
        async with treasurer:
            return await treasurer.search_by_address(street_address, city, zip_code, **kwargs)
    return asyncio.run(_search())


def search_cook_county_by_owner(owner_name: str, **kwargs) -> TaxSearchResult:
    """Search Cook County tax records by owner name."""
    treasurer = CookCountyTreasurer()

    async def _search():
        async with treasurer:
            return await treasurer.search_by_owner(owner_name, **kwargs)
    return asyncio.run(_search())
