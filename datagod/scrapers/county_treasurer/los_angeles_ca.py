"""
Los Angeles County, California Treasurer-Tax Collector Scraper

Los Angeles County Treasurer and Tax Collector (TTC) manages property
tax collection for over 2.5 million parcels across Los Angeles County,
the most populous county in the United States.

Website: https://ttc.lacounty.gov/
Property Tax Search: https://vcheck.ttc.lacounty.gov/

The LA County TTC provides:
- Secured and unsecured property tax bills
- Supplemental tax bills
- Payment history
- Tax defaulted properties
- Tax sale auctions
- Redemption information
- Payment plans

Tax Calendar (Los Angeles County):
- First installment due: November 1
- First installment delinquent: December 10
- Second installment due: February 1
- Second installment delinquent: April 10
- Fiscal year: July 1 - June 30
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


class LosAngelesCountyTreasurer(CountyTreasurerBase):
    """
    Los Angeles County Treasurer-Tax Collector scraper.

    Uses the LA County TTC property tax portal.
    APN format: XXXX-XXX-XXX (10 digits with dashes)
    """

    COUNTY_NAME = "Los Angeles County"
    STATE = "CA"
    FIPS_CODE = "06037"
    BASE_URL = "https://ttc.lacounty.gov/"
    TAX_SEARCH_URL = "https://vcheck.ttc.lacounty.gov/"
    SYSTEM_NAME = "LA County Treasurer-Tax Collector"

    # API endpoints
    API_BASE = "https://vcheck.ttc.lacounty.gov/api/"

    # Tax calendar (LA County - fiscal year basis)
    TAX_YEAR_START = "07-01"  # Fiscal year starts July 1
    FIRST_INSTALLMENT_DUE = "11-01"
    FIRST_INSTALLMENT_DELINQUENT = "12-10"
    SECOND_INSTALLMENT_DUE = "02-01"
    SECOND_INSTALLMENT_DELINQUENT = "04-10"

    # Tax Rate Areas (TRAs) - major cities
    TAX_RATE_AREAS = {
        "0001": "City of Los Angeles",
        "0002": "Unincorporated LA County",
        "0003": "City of Long Beach",
        "0004": "City of Pasadena",
        "0005": "City of Glendale",
        "0006": "City of Santa Monica",
        "0007": "City of Burbank",
        "0008": "City of Torrance",
        "0009": "City of Pomona",
        "0010": "City of West Covina",
    }

    # Special assessment districts
    SPECIAL_DISTRICTS = {
        "MELLO_ROOS": "Mello-Roos Community Facilities District",
        "AD": "Assessment District",
        "LMD": "Landscape/Lighting Maintenance District",
        "BID": "Business Improvement District",
        "CFD": "Community Facilities District",
        "FLOOD": "Flood Control District",
        "VECTOR": "Vector Control District",
    }

    def _format_apn(self, apn: str) -> str:
        """Format APN to standard LA County format: XXXX-XXX-XXX"""
        # Remove any existing dashes, spaces, or non-digits
        digits = re.sub(r"[^0-9]", "", apn)

        if len(digits) != 10:
            return apn  # Return as-is if not 10 digits

        return f"{digits[0:4]}-{digits[4:7]}-{digits[7:10]}"

    def _parse_apn(self, apn: str) -> Dict[str, str]:
        """Parse APN into components (Book-Page-Parcel)."""
        digits = re.sub(r"[^0-9]", "", apn)

        if len(digits) != 10:
            return {"raw": apn}

        return {
            "map_book": digits[0:4],
            "map_page": digits[4:7],
            "parcel": digits[7:10],
            "formatted": self._format_apn(apn),
        }

    async def get_tax_record(self, parcel_id: str) -> Optional[PropertyTaxRecord]:
        """Get property tax record by APN."""
        formatted_apn = self._format_apn(parcel_id)
        detail_url = f"{self.API_BASE}property/{formatted_apn}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"LA County tax record fetch failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_tax_record(json_response)

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
            logger.error(f"LA County address search failed: {e}")
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

        search_url = f"{self.API_BASE}search/owner"

        params = {
            "name": owner_name,
            "limit": min(max_results, 100),
        }

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"LA County owner search failed: {e}")
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
        self, min_amount: Optional[Decimal] = None, max_results: int = 500
    ) -> TaxSearchResult:
        """Get list of tax-defaulted properties."""
        import time

        start_time = time.time()

        defaulted_url = f"{self.API_BASE}defaulted"

        params = {"limit": min(max_results, 500)}
        if min_amount:
            params["minAmount"] = str(min_amount)

        try:
            json_response = await self._fetch_json(defaulted_url, params=params)
        except Exception as e:
            logger.error(f"LA County defaulted list failed: {e}")
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
            search_criteria=TaxSearchCriteria(
                delinquent_only=True, min_amount_due=min_amount
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_tax_sale_properties(
        self,
        sale_type: Optional[TaxSaleType] = None,
        upcoming_only: bool = True,
        max_results: int = 500,
    ) -> List[TaxSaleProperty]:
        """Get properties scheduled for tax sale auction."""
        sale_url = f"{self.API_BASE}auction"

        params = {"limit": min(max_results, 500)}
        if upcoming_only:
            params["upcoming"] = "true"
        if sale_type:
            params["type"] = sale_type.value

        try:
            json_response = await self._fetch_json(sale_url, params=params)
        except Exception as e:
            logger.error(f"LA County tax sale list failed: {e}")
            return []

        properties = []
        results = json_response.get("properties", json_response.get("results", []))

        for item in results[:max_results]:
            prop = self._parse_tax_sale_property(item)
            if prop:
                properties.append(prop)

        return properties

    async def get_supplemental_bills(self, parcel_id: str) -> List[TaxBill]:
        """Get supplemental tax bills for a property (due to ownership change or new construction)."""
        formatted_apn = self._format_apn(parcel_id)
        supp_url = f"{self.API_BASE}supplemental/{formatted_apn}"

        try:
            json_response = await self._fetch_json(supp_url)
        except Exception as e:
            logger.error(f"LA County supplemental bills failed: {e}")
            return []

        bills = []
        results = json_response.get("bills", json_response.get("results", []))

        for bill_data in results:
            bill = self._parse_tax_bill(bill_data, formatted_apn, is_supplemental=True)
            if bill:
                bills.append(bill)

        return bills

    def _parse_search_result(self, item: Dict[str, Any]) -> Optional[PropertyTaxRecord]:
        """Parse a search result item into PropertyTaxRecord."""
        apn = item.get("apn", item.get("parcelNumber", item.get("ain", "")))
        if not apn:
            return None

        formatted_apn = self._format_apn(apn)

        # Parse current tax info
        current_tax = self._parse_decimal(
            str(item.get("totalTax", item.get("annualTax", "")))
        )
        balance_due = self._parse_decimal(
            str(item.get("balanceDue", item.get("amountDue", "")))
        )
        amount_paid = self._parse_decimal(str(item.get("amountPaid", "")))

        # Determine status
        status_str = item.get("status", item.get("paymentStatus", ""))
        tax_status = self._parse_tax_status(status_str)

        # Check for default status (CA term for tax delinquency)
        is_defaulted = item.get("isDefaulted", item.get("taxDefaulted", False))
        is_delinquent = (
            is_defaulted
            or "DEFAULT" in str(status_str).upper()
            or (balance_due and balance_due > 0)
        )

        if is_defaulted:
            tax_status = TaxStatus.DELINQUENT

        # Parse exemptions (California exemptions)
        exemptions = []
        if item.get("homeownersExemption"):
            exemptions.append("Homeowners Exemption")
        if item.get("veteransExemption"):
            exemptions.append("Veterans Exemption")
        if item.get("disabledVeteransExemption"):
            exemptions.append("Disabled Veterans Exemption")
        if item.get("seniorExemption"):
            exemptions.append("Senior Citizens Exemption")
        for ex in item.get("exemptions", []):
            if ex not in exemptions:
                exemptions.append(ex)

        return PropertyTaxRecord(
            parcel_id=formatted_apn,
            property_address=item.get("address", item.get("situsAddress")),
            city=item.get("city", item.get("situsCity")),
            state=self.STATE,
            zip_code=item.get("zip", item.get("situsZip")),
            county=self.COUNTY_NAME,
            owner_name=item.get("owner", item.get("ownerName", item.get("assessee"))),
            owner_address=item.get("ownerAddress", item.get("mailingAddress")),
            assessed_value=self._parse_decimal(str(item.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(
                str(item.get("netAssessedValue", item.get("taxableValue", "")))
            ),
            market_value=self._parse_decimal(str(item.get("marketValue", ""))),
            current_tax_year=self._parse_int(
                str(item.get("taxYear", item.get("fiscalYear", "")))
            ),
            current_tax_amount=current_tax,
            current_amount_paid=amount_paid,
            current_balance_due=balance_due,
            tax_status=tax_status,
            is_delinquent=is_delinquent,
            years_delinquent=self._parse_int(
                str(item.get("yearsDefaulted", item.get("yearsDelinquent", "0")))
            )
            or 0,
            total_delinquent=self._parse_decimal(
                str(item.get("totalDefaulted", item.get("totalDelinquent", "")))
            ),
            exemptions=exemptions,
            exemption_amount=self._parse_decimal(str(item.get("exemptionAmount", ""))),
            has_tax_lien=is_defaulted,  # In CA, defaulted = potential lien
            source_url=f"{self.TAX_SEARCH_URL}?apn={formatted_apn}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_tax_record(self, data: Dict[str, Any]) -> PropertyTaxRecord:
        """Parse detailed tax record data."""
        apn = data.get("apn", data.get("parcelNumber", data.get("ain", "")))
        formatted_apn = self._format_apn(apn)

        # Parse tax bills (secured, unsecured, supplemental)
        tax_bills = []

        # Secured tax bills
        for bill_data in data.get("securedBills", data.get("taxBills", [])):
            bill = self._parse_tax_bill(bill_data, formatted_apn, is_secured=True)
            if bill:
                tax_bills.append(bill)

        # Unsecured tax bills
        for bill_data in data.get("unsecuredBills", []):
            bill = self._parse_tax_bill(bill_data, formatted_apn, is_secured=False)
            if bill:
                tax_bills.append(bill)

        # Supplemental tax bills
        for bill_data in data.get("supplementalBills", []):
            bill = self._parse_tax_bill(bill_data, formatted_apn, is_supplemental=True)
            if bill:
                tax_bills.append(bill)

        # Sort bills by year (most recent first)
        tax_bills.sort(
            key=lambda b: (b.tax_year, b.installment_number or 0), reverse=True
        )

        # Parse payment history
        payment_history = []
        for payment_data in data.get("payments", data.get("paymentHistory", [])):
            payment = self._parse_payment(payment_data, formatted_apn)
            if payment:
                payment_history.append(payment)

        # Parse exemptions
        exemptions = []
        exemption_amount = Decimal(0)
        for ex_data in data.get("exemptions", []):
            if isinstance(ex_data, str):
                exemptions.append(ex_data)
            elif isinstance(ex_data, dict):
                exemptions.append(ex_data.get("type", ex_data.get("name", "Exemption")))
                amt = self._parse_decimal(str(ex_data.get("amount", "")))
                if amt:
                    exemption_amount += amt

        # Check for common California exemptions
        if data.get("homeownersExemption"):
            if "Homeowners Exemption" not in exemptions:
                exemptions.append("Homeowners Exemption")
            exemption_amount += Decimal("7000")  # Standard HOX

        # Parse special assessments (Mello-Roos, etc.)
        special_assessments = []
        for assess_data in data.get(
            "specialAssessments", data.get("directCharges", [])
        ):
            item = TaxBillItem(
                description=assess_data.get(
                    "description", assess_data.get("name", "Special Assessment")
                ),
                amount=self._parse_decimal(str(assess_data.get("amount", "")))
                or Decimal(0),
                taxing_authority=assess_data.get(
                    "authority", assess_data.get("district")
                ),
                raw_data=assess_data,
            )
            special_assessments.append(item)

        # Calculate totals
        current_tax = self._parse_decimal(
            str(data.get("annualTax", data.get("totalTax", "")))
        )
        balance_due = self._parse_decimal(
            str(data.get("balanceDue", data.get("totalDue", "")))
        )
        amount_paid = self._parse_decimal(str(data.get("amountPaid", "")))
        total_defaulted = self._parse_decimal(
            str(data.get("totalDefaulted", data.get("priorDue", "")))
        )

        # Determine status
        is_defaulted = data.get("isDefaulted", data.get("taxDefaulted", False))
        status_str = data.get("status", data.get("paymentStatus", ""))
        tax_status = self._parse_tax_status(status_str)

        if is_defaulted:
            tax_status = TaxStatus.DELINQUENT

        is_delinquent = is_defaulted or bool(total_defaulted and total_defaulted > 0)

        return PropertyTaxRecord(
            parcel_id=formatted_apn,
            property_address=data.get("address", data.get("situsAddress")),
            city=data.get("city", data.get("situsCity")),
            state=self.STATE,
            zip_code=data.get("zip", data.get("situsZip")),
            county=self.COUNTY_NAME,
            owner_name=data.get("owner", data.get("ownerName", data.get("assessee"))),
            owner_address=data.get("ownerAddress", data.get("mailingAddress")),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(
                str(data.get("netAssessedValue", data.get("taxableValue", "")))
            ),
            market_value=self._parse_decimal(str(data.get("marketValue", ""))),
            current_tax_year=self._parse_int(
                str(data.get("taxYear", data.get("fiscalYear", "")))
            ),
            current_tax_amount=current_tax,
            current_amount_paid=amount_paid,
            current_balance_due=balance_due,
            tax_status=tax_status,
            is_delinquent=is_delinquent,
            years_delinquent=self._parse_int(str(data.get("yearsDefaulted", "0"))) or 0,
            total_delinquent=total_defaulted,
            exemptions=exemptions,
            exemption_amount=exemption_amount if exemption_amount > 0 else None,
            tax_bills=tax_bills,
            payment_history=payment_history,
            has_tax_lien=is_defaulted,
            special_assessments=special_assessments,
            source_url=f"{self.TAX_SEARCH_URL}?apn={formatted_apn}",
            source_system=self.SYSTEM_NAME,
            last_updated=self._parse_datetime(data.get("lastUpdated", "")),
            raw_data=data,
        )

    def _parse_tax_bill(
        self,
        data: Dict[str, Any],
        apn: str,
        is_secured: bool = True,
        is_supplemental: bool = False,
    ) -> Optional[TaxBill]:
        """Parse a tax bill record."""
        tax_year = self._parse_int(str(data.get("taxYear", data.get("fiscalYear", ""))))
        if not tax_year:
            return None

        # Parse line items / direct charges
        line_items = []
        for item_data in data.get("lineItems", data.get("taxes", [])):
            item = TaxBillItem(
                description=item_data.get("description", item_data.get("name", "")),
                amount=self._parse_decimal(
                    str(item_data.get("amount", item_data.get("tax", "")))
                )
                or Decimal(0),
                taxing_authority=item_data.get("authority", item_data.get("agency")),
                tax_rate=self._parse_decimal(str(item_data.get("rate", ""))),
                raw_data=item_data,
            )
            line_items.append(item)

        # Add special assessments / direct charges
        for assess_data in data.get(
            "directCharges", data.get("specialAssessments", [])
        ):
            item = TaxBillItem(
                description=assess_data.get("description", "Direct Charge"),
                amount=self._parse_decimal(str(assess_data.get("amount", "")))
                or Decimal(0),
                taxing_authority=assess_data.get(
                    "authority", assess_data.get("district")
                ),
                raw_data=assess_data,
            )
            line_items.append(item)

        # Determine installment info
        installment = self._parse_int(str(data.get("installment", "")))
        bill_type = data.get("billType", data.get("type", ""))

        if "1ST" in str(bill_type).upper() or "FIRST" in str(bill_type).upper():
            installment = 1
        elif "2ND" in str(bill_type).upper() or "SECOND" in str(bill_type).upper():
            installment = 2

        return TaxBill(
            bill_number=data.get("billNumber", data.get("taxBillNumber")),
            tax_year=tax_year,
            parcel_id=apn,
            property_address=data.get("address", data.get("situsAddress")),
            owner_name=data.get("owner", data.get("assessee")),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(
                str(data.get("netAssessedValue", data.get("taxableValue", "")))
            ),
            tax_rate=self._parse_decimal(str(data.get("taxRate", ""))),
            gross_tax=self._parse_decimal(
                str(data.get("grossTax", data.get("totalTax", "")))
            ),
            exemptions=self._parse_decimal(str(data.get("exemptions", ""))),
            net_tax=self._parse_decimal(str(data.get("netTax", ""))),
            penalties=self._parse_decimal(
                str(data.get("penalty", data.get("penalties", "")))
            ),
            interest=self._parse_decimal(str(data.get("interest", ""))),
            fees=self._parse_decimal(str(data.get("costs", data.get("fees", "")))),
            total_due=self._parse_decimal(
                str(data.get("totalDue", data.get("amountDue", "")))
            ),
            amount_paid=self._parse_decimal(str(data.get("amountPaid", ""))),
            balance_due=self._parse_decimal(str(data.get("balanceDue", ""))),
            payment_status=self._parse_tax_status(data.get("status", "")),
            bill_date=self._parse_date(data.get("billDate", "")),
            due_date=self._parse_date(data.get("dueDate", "")),
            delinquent_date=self._parse_date(data.get("delinquentDate", "")),
            installment_number=installment,
            total_installments=2,  # CA has 2 installments for secured taxes
            line_items=line_items,
            source_url=f"{self.TAX_SEARCH_URL}?apn={apn}&year={tax_year}",
            raw_data=data,
        )

    def _parse_payment(self, data: Dict[str, Any], apn: str) -> Optional[TaxPayment]:
        """Parse a payment record."""
        payment_date = self._parse_date(data.get("paymentDate", data.get("date", "")))
        amount = self._parse_decimal(
            str(data.get("amount", data.get("paymentAmount", "")))
        )

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
            elif "CREDIT" in upper or "CARD" in upper:
                method = PaymentMethod.CREDIT_CARD
            elif "ACH" in upper or "EFT" in upper or "ELECTRONIC" in upper:
                method = PaymentMethod.ACH
            elif "ESCROW" in upper:
                method = PaymentMethod.ESCROW
            elif "ONLINE" in upper or "WEB" in upper:
                method = PaymentMethod.ONLINE

        return TaxPayment(
            payment_id=data.get(
                "paymentId", data.get("transactionId", data.get("receiptNumber"))
            ),
            parcel_id=apn,
            tax_year=self._parse_int(
                str(data.get("taxYear", data.get("fiscalYear", "")))
            )
            or 0,
            payment_date=payment_date,
            payment_amount=amount,
            payment_method=method,
            principal_paid=self._parse_decimal(
                str(data.get("principal", data.get("taxPaid", "")))
            ),
            interest_paid=self._parse_decimal(str(data.get("interest", ""))),
            penalty_paid=self._parse_decimal(str(data.get("penalty", ""))),
            fees_paid=self._parse_decimal(str(data.get("costs", data.get("fees", "")))),
            receipt_number=data.get("receiptNumber", data.get("confirmationNumber")),
            check_number=data.get("checkNumber"),
            payer_name=data.get("payer", data.get("payerName")),
            installment_number=self._parse_int(str(data.get("installment", ""))),
            raw_data=data,
        )

    def _parse_tax_sale_property(
        self, data: Dict[str, Any]
    ) -> Optional[TaxSaleProperty]:
        """Parse a tax sale property listing."""
        apn = data.get("apn", data.get("parcelNumber", data.get("ain", "")))
        if not apn:
            return None

        formatted_apn = self._format_apn(apn)

        # Parse defaulted years
        tax_years = data.get("taxYears", data.get("yearsDefaulted", []))
        if isinstance(tax_years, str):
            tax_years = [
                int(y.strip()) for y in tax_years.split(",") if y.strip().isdigit()
            ]
        elif isinstance(tax_years, int):
            tax_years = [tax_years]

        # California uses tax deed sale (not lien sale)
        sale_type = TaxSaleType.TAX_DEED_SALE
        if data.get("isOnlineAuction"):
            sale_type = TaxSaleType.ONLINE_AUCTION

        return TaxSaleProperty(
            sale_id=data.get("saleId", data.get("itemNumber", data.get("lotNumber"))),
            parcel_id=formatted_apn,
            property_address=data.get("address", data.get("situsAddress")),
            city=data.get("city", data.get("situsCity")),
            zip_code=data.get("zip", data.get("situsZip")),
            legal_description=data.get("legalDescription"),
            property_type=data.get("propertyType", data.get("useCode")),
            owner_name=data.get("owner", data.get("assessee")),
            owner_address=data.get("ownerAddress", data.get("mailingAddress")),
            tax_years_delinquent=tax_years,
            total_taxes_due=self._parse_decimal(str(data.get("taxesDue", ""))),
            penalties_due=self._parse_decimal(str(data.get("penalties", ""))),
            interest_due=self._parse_decimal(str(data.get("interest", ""))),
            fees_due=self._parse_decimal(str(data.get("costs", ""))),
            total_amount_due=self._parse_decimal(
                str(data.get("totalDue", data.get("minimumBid", "")))
            ),
            sale_type=sale_type,
            sale_date=self._parse_date(
                data.get("saleDate", data.get("auctionDate", ""))
            ),
            auction_date=self._parse_date(data.get("auctionDate", "")),
            minimum_bid=self._parse_decimal(
                str(data.get("minimumBid", data.get("openingBid", "")))
            ),
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
            source_url=f"{self.BASE_URL}auction?apn={formatted_apn}",
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


def get_la_county_tax_record(parcel_id: str) -> Optional[PropertyTaxRecord]:
    """Get LA County tax record by APN."""
    treasurer = LosAngelesCountyTreasurer()

    async def _get():
        async with treasurer:
            return await treasurer.get_tax_record(parcel_id)

    return asyncio.run(_get())


def search_la_county_by_address(
    street_address: str,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    **kwargs,
) -> TaxSearchResult:
    """Search LA County tax records by address."""
    treasurer = LosAngelesCountyTreasurer()

    async def _search():
        async with treasurer:
            return await treasurer.search_by_address(
                street_address, city, zip_code, **kwargs
            )

    return asyncio.run(_search())


def search_la_county_by_owner(owner_name: str, **kwargs) -> TaxSearchResult:
    """Search LA County tax records by owner name."""
    treasurer = LosAngelesCountyTreasurer()

    async def _search():
        async with treasurer:
            return await treasurer.search_by_owner(owner_name, **kwargs)

    return asyncio.run(_search())
