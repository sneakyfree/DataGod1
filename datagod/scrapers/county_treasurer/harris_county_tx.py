"""
Harris County, Texas Tax Office Scraper

Harris County Tax Office manages property tax collection for over
1.8 million accounts across Harris County, the third most populous
county in the United States.

Website: https://www.hctax.net/
Property Tax Search: https://www.hctax.net/Property/PropertyTax

The Harris County Tax Office provides:
- Property tax statements
- Payment history
- Tax certificates
- Delinquent tax information
- Tax sales (sheriff sales)
- Payment plans
- Multiple entity billing (county, school, MUD, etc.)

Tax Calendar (Harris County, Texas):
- Tax year: Calendar year (January 1 - December 31)
- Statements mailed: October 1
- Due date: January 31
- Delinquent: February 1
- Penalty starts: February 1 (6%) + 1% per month
- Tax sale: Usually first Tuesday of month
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


class HarrisCountyTreasurer(CountyTreasurerBase):
    """
    Harris County, Texas Tax Office scraper.

    Uses the Harris County Tax Office property tax portal.
    Account format: XXXX-XXXX-XXXX or 12-digit number
    """

    COUNTY_NAME = "Harris County"
    STATE = "TX"
    FIPS_CODE = "48201"
    BASE_URL = "https://www.hctax.net/"
    TAX_SEARCH_URL = "https://www.hctax.net/Property/PropertyTax"
    SYSTEM_NAME = "Harris County Tax Office"

    # API endpoints
    API_BASE = "https://www.hctax.net/Property/api/"

    # Tax calendar (Texas)
    TAX_YEAR_START = "01-01"
    DUE_DATE = "01-31"
    DELINQUENT_DATE = "02-01"

    # Penalty schedule (Texas)
    PENALTY_SCHEDULE = {
        2: Decimal("0.06"),   # February: 6%
        3: Decimal("0.07"),   # March: 7%
        4: Decimal("0.08"),   # April: 8%
        5: Decimal("0.09"),   # May: 9%
        6: Decimal("0.10"),   # June: 10%
        7: Decimal("0.12"),   # July+: 12% + attorney fees
    }

    # Major taxing entities in Harris County
    TAXING_ENTITIES = {
        "HAR": "Harris County",
        "HOU": "City of Houston",
        "HISD": "Houston Independent School District",
        "HCC": "Houston Community College",
        "HCFC": "Harris County Flood Control",
        "HCHD": "Harris County Hospital District",
        "HCDE": "Harris County Dept of Education",
        "PORT": "Port of Houston Authority",
        "MUD": "Municipal Utility District",
        "WCID": "Water Control & Improvement District",
        "ESD": "Emergency Services District",
    }

    # School districts
    SCHOOL_DISTRICTS = {
        "001": "Houston ISD",
        "002": "Aldine ISD",
        "003": "Alief ISD",
        "004": "Clear Creek ISD",
        "005": "Crosby ISD",
        "006": "Cypress-Fairbanks ISD",
        "007": "Deer Park ISD",
        "008": "Galena Park ISD",
        "009": "Goose Creek CISD",
        "010": "Huffman ISD",
        "011": "Humble ISD",
        "012": "Katy ISD",
        "013": "Klein ISD",
        "014": "La Porte ISD",
        "015": "Pasadena ISD",
        "016": "Sheldon ISD",
        "017": "Spring ISD",
        "018": "Spring Branch ISD",
        "019": "Tomball ISD",
    }

    def _format_account(self, account: str) -> str:
        """Format account number to standard format."""
        # Remove any existing dashes, spaces, or non-digits
        digits = re.sub(r"[^0-9]", "", account)

        if len(digits) == 12:
            return f"{digits[0:4]}-{digits[4:8]}-{digits[8:12]}"

        return account  # Return as-is if not 12 digits

    async def get_tax_record(
        self,
        parcel_id: str
    ) -> Optional[PropertyTaxRecord]:
        """Get property tax record by account number."""
        formatted_account = self._format_account(parcel_id)
        detail_url = f"{self.API_BASE}account/{formatted_account}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"Harris County tax record fetch failed: {e}")
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
            logger.error(f"Harris County address search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                search_criteria=TaxSearchCriteria(property_address=street_address),
                warnings=[str(e)],
            )

        records = []
        results = json_response.get("accounts", json_response.get("results", []))

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
            logger.error(f"Harris County owner search failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                search_criteria=TaxSearchCriteria(owner_name=owner_name),
                warnings=[str(e)],
            )

        records = []
        results = json_response.get("accounts", json_response.get("results", []))

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
            logger.error(f"Harris County delinquent list failed: {e}")
            return TaxSearchResult(
                records=[],
                total_count=0,
                warnings=[str(e)],
            )

        records = []
        results = json_response.get("accounts", json_response.get("results", []))

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
        """Get properties scheduled for tax sale (sheriff sale)."""
        sale_url = f"{self.API_BASE}taxsale"

        params = {"limit": min(max_results, 500)}
        if upcoming_only:
            params["upcoming"] = "true"

        try:
            json_response = await self._fetch_json(sale_url, params=params)
        except Exception as e:
            logger.error(f"Harris County tax sale list failed: {e}")
            return []

        properties = []
        results = json_response.get("properties", json_response.get("results", []))

        for item in results[:max_results]:
            prop = self._parse_tax_sale_property(item)
            if prop:
                properties.append(prop)

        return properties

    async def get_tax_certificate(
        self,
        parcel_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get tax certificate for a property (shows taxes due to all entities)."""
        formatted_account = self._format_account(parcel_id)
        cert_url = f"{self.API_BASE}certificate/{formatted_account}"

        try:
            json_response = await self._fetch_json(cert_url)
            return json_response
        except Exception as e:
            logger.error(f"Harris County tax certificate failed: {e}")
            return None

    def _calculate_penalty(self, base_amount: Decimal, month: int) -> Decimal:
        """Calculate Texas penalty based on month."""
        if month < 2:
            return Decimal(0)

        penalty_rate = self.PENALTY_SCHEDULE.get(month, Decimal("0.12"))
        return base_amount * penalty_rate

    def _parse_search_result(self, item: Dict[str, Any]) -> Optional[PropertyTaxRecord]:
        """Parse a search result item into PropertyTaxRecord."""
        account = item.get("accountNumber", item.get("account", item.get("acct", "")))
        if not account:
            return None

        formatted_account = self._format_account(account)

        # Parse current tax info
        current_tax = self._parse_decimal(str(item.get("totalTax", item.get("taxAmount", ""))))
        balance_due = self._parse_decimal(str(item.get("balanceDue", item.get("amountDue", ""))))
        amount_paid = self._parse_decimal(str(item.get("amountPaid", "")))

        # Determine status
        status_str = item.get("status", item.get("paymentStatus", ""))
        tax_status = self._parse_tax_status(status_str)
        is_delinquent = "DELINQUENT" in str(status_str).upper() or item.get("isDelinquent", False)

        # Parse exemptions (Texas exemptions)
        exemptions = []
        if item.get("homesteadExemption") or item.get("hasHomestead"):
            exemptions.append("Homestead Exemption")
        if item.get("over65Exemption") or item.get("hasOver65"):
            exemptions.append("Over 65 Exemption")
        if item.get("disabledExemption") or item.get("hasDisabled"):
            exemptions.append("Disabled Person Exemption")
        if item.get("veteranExemption") or item.get("hasVeteran"):
            exemptions.append("Disabled Veteran Exemption")
        if item.get("agExemption") or item.get("hasAgUse"):
            exemptions.append("Agricultural Use Exemption")
        for ex in item.get("exemptions", []):
            if ex not in exemptions:
                exemptions.append(ex)

        return PropertyTaxRecord(
            parcel_id=formatted_account,
            property_address=item.get("address", item.get("propertyAddress", item.get("situs"))),
            city=item.get("city"),
            state=self.STATE,
            zip_code=item.get("zip", item.get("zipCode")),
            county=self.COUNTY_NAME,
            owner_name=item.get("owner", item.get("ownerName")),
            owner_address=item.get("ownerAddress", item.get("mailingAddress")),
            assessed_value=self._parse_decimal(str(item.get("assessedValue", item.get("appraised", "")))),
            taxable_value=self._parse_decimal(str(item.get("taxableValue", ""))),
            market_value=self._parse_decimal(str(item.get("marketValue", item.get("appraised", "")))),
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
            has_tax_lien=item.get("hasLien", item.get("inSuit", False)),
            source_url=f"{self.TAX_SEARCH_URL}?account={formatted_account}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_tax_record(self, data: Dict[str, Any]) -> PropertyTaxRecord:
        """Parse detailed tax record data."""
        account = data.get("accountNumber", data.get("account", data.get("acct", "")))
        formatted_account = self._format_account(account)

        # Parse tax bills (from multiple entities)
        tax_bills = []
        for bill_data in data.get("taxBills", data.get("statements", [])):
            bill = self._parse_tax_bill(bill_data, formatted_account)
            if bill:
                tax_bills.append(bill)

        # Sort bills by year (most recent first)
        tax_bills.sort(key=lambda b: b.tax_year, reverse=True)

        # Parse payment history
        payment_history = []
        for payment_data in data.get("payments", data.get("paymentHistory", [])):
            payment = self._parse_payment(payment_data, formatted_account)
            if payment:
                payment_history.append(payment)

        # Parse liens (if in suit)
        liens = []
        for lien_data in data.get("liens", data.get("suits", [])):
            lien = self._parse_tax_lien(lien_data)
            if lien:
                liens.append(lien)

        # Parse exemptions
        exemptions = []
        exemption_amount = Decimal(0)

        if data.get("homesteadExemption") or data.get("hasHomestead"):
            exemptions.append("Homestead Exemption")
        if data.get("over65Exemption") or data.get("hasOver65"):
            exemptions.append("Over 65 Exemption")
        if data.get("disabledExemption") or data.get("hasDisabled"):
            exemptions.append("Disabled Person Exemption")
        if data.get("veteranExemption") or data.get("hasVeteran"):
            exemptions.append("Disabled Veteran Exemption")
        if data.get("agExemption") or data.get("hasAgUse"):
            exemptions.append("Agricultural Use Exemption")

        for ex_data in data.get("exemptions", []):
            if isinstance(ex_data, str):
                if ex_data not in exemptions:
                    exemptions.append(ex_data)
            elif isinstance(ex_data, dict):
                exemptions.append(ex_data.get("type", ex_data.get("name", "Exemption")))
                amt = self._parse_decimal(str(ex_data.get("amount", "")))
                if amt:
                    exemption_amount += amt

        # Parse special assessments (MUDs, etc.)
        special_assessments = []
        for assess_data in data.get("specialAssessments", data.get("mudCharges", [])):
            item = TaxBillItem(
                description=assess_data.get("description", assess_data.get("name", "Special Assessment")),
                amount=self._parse_decimal(str(assess_data.get("amount", ""))) or Decimal(0),
                taxing_authority=assess_data.get("entity", assess_data.get("district")),
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

        if not is_delinquent and total_delinquent and total_delinquent > 0:
            is_delinquent = True

        if is_delinquent:
            tax_status = TaxStatus.DELINQUENT

        return PropertyTaxRecord(
            parcel_id=formatted_account,
            property_address=data.get("address", data.get("propertyAddress", data.get("situs"))),
            city=data.get("city"),
            state=self.STATE,
            zip_code=data.get("zip", data.get("zipCode")),
            county=self.COUNTY_NAME,
            owner_name=data.get("owner", data.get("ownerName")),
            owner_address=data.get("ownerAddress", data.get("mailingAddress")),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", data.get("appraised", "")))),
            taxable_value=self._parse_decimal(str(data.get("taxableValue", ""))),
            market_value=self._parse_decimal(str(data.get("marketValue", data.get("appraised", "")))),
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
            has_tax_lien=len(liens) > 0 or data.get("inSuit", False),
            liens=liens,
            special_assessments=special_assessments,
            source_url=f"{self.TAX_SEARCH_URL}?account={formatted_account}",
            source_system=self.SYSTEM_NAME,
            last_updated=self._parse_datetime(data.get("lastUpdated", "")),
            raw_data=data,
        )

    def _parse_tax_bill(self, data: Dict[str, Any], account: str) -> Optional[TaxBill]:
        """Parse a tax bill record."""
        tax_year = self._parse_int(str(data.get("taxYear", data.get("year", ""))))
        if not tax_year:
            return None

        # Parse line items (from different taxing entities)
        line_items = []
        for item_data in data.get("lineItems", data.get("entities", data.get("taxingUnits", []))):
            entity_code = item_data.get("code", item_data.get("entityCode", ""))
            entity_name = self.TAXING_ENTITIES.get(entity_code, item_data.get("name", item_data.get("entity", "")))

            item = TaxBillItem(
                description=entity_name or item_data.get("description", ""),
                amount=self._parse_decimal(str(item_data.get("amount", item_data.get("tax", "")))) or Decimal(0),
                taxing_authority=entity_name,
                tax_rate=self._parse_decimal(str(item_data.get("rate", ""))),
                assessed_value=self._parse_decimal(str(item_data.get("taxableValue", ""))),
                raw_data=item_data,
            )
            line_items.append(item)

        return TaxBill(
            bill_number=data.get("billNumber", data.get("statementNumber")),
            tax_year=tax_year,
            parcel_id=account,
            property_address=data.get("address", data.get("situs")),
            owner_name=data.get("owner", data.get("ownerName")),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", data.get("appraised", "")))),
            taxable_value=self._parse_decimal(str(data.get("taxableValue", ""))),
            tax_rate=self._parse_decimal(str(data.get("combinedRate", data.get("taxRate", "")))),
            gross_tax=self._parse_decimal(str(data.get("grossTax", data.get("baseTax", "")))),
            exemptions=self._parse_decimal(str(data.get("exemptionSavings", ""))),
            net_tax=self._parse_decimal(str(data.get("netTax", data.get("totalTax", "")))),
            penalties=self._parse_decimal(str(data.get("penalty", data.get("penalties", "")))),
            interest=self._parse_decimal(str(data.get("interest", ""))),
            fees=self._parse_decimal(str(data.get("attorneyFees", data.get("costs", "")))),
            total_due=self._parse_decimal(str(data.get("totalDue", data.get("amountDue", "")))),
            amount_paid=self._parse_decimal(str(data.get("amountPaid", ""))),
            balance_due=self._parse_decimal(str(data.get("balanceDue", ""))),
            payment_status=self._parse_tax_status(data.get("status", "")),
            bill_date=self._parse_date(data.get("billDate", data.get("statementDate", ""))),
            due_date=self._parse_date(data.get("dueDate", "")),
            delinquent_date=self._parse_date(data.get("delinquentDate", "")),
            installment_number=1,  # Texas is single payment (no installments)
            total_installments=1,
            line_items=line_items,
            source_url=f"{self.TAX_SEARCH_URL}?account={account}&year={tax_year}",
            raw_data=data,
        )

    def _parse_payment(self, data: Dict[str, Any], account: str) -> Optional[TaxPayment]:
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
            parcel_id=account,
            tax_year=self._parse_int(str(data.get("taxYear", ""))) or 0,
            payment_date=payment_date,
            payment_amount=amount,
            payment_method=method,
            principal_paid=self._parse_decimal(str(data.get("baseTax", data.get("principal", "")))),
            interest_paid=self._parse_decimal(str(data.get("interest", ""))),
            penalty_paid=self._parse_decimal(str(data.get("penalty", ""))),
            fees_paid=self._parse_decimal(str(data.get("attorneyFees", data.get("costs", "")))),
            receipt_number=data.get("receiptNumber", data.get("confirmationNumber")),
            check_number=data.get("checkNumber"),
            payer_name=data.get("payer", data.get("payerName")),
            raw_data=data,
        )

    def _parse_tax_lien(self, data: Dict[str, Any]) -> Optional[TaxLien]:
        """Parse a tax lien record (Texas uses suit/judgment system)."""
        lien_number = data.get("suitNumber", data.get("causeNumber", data.get("lienNumber", "")))
        account = data.get("accountNumber", data.get("account", ""))

        if not lien_number and not account:
            return None

        formatted_account = self._format_account(account) if account else ""

        # Parse tax years covered
        tax_years = data.get("taxYears", [])
        if isinstance(tax_years, str):
            tax_years = [int(y.strip()) for y in tax_years.split(",") if y.strip().isdigit()]
        elif isinstance(tax_years, int):
            tax_years = [tax_years]

        return TaxLien(
            lien_number=str(lien_number) if lien_number else f"SUIT-{formatted_account}",
            parcel_id=formatted_account,
            lien_date=self._parse_date(data.get("suitDate", data.get("filingDate", ""))),
            lien_amount=self._parse_decimal(str(data.get("judgmentAmount", data.get("lienAmount", "")))),
            face_value=self._parse_decimal(str(data.get("baseTaxes", data.get("taxAmount", "")))),
            interest_rate=self._parse_decimal(str(data.get("interestRate", ""))),
            accrued_interest=self._parse_decimal(str(data.get("interest", ""))),
            penalties=self._parse_decimal(str(data.get("penalty", ""))),
            total_due=self._parse_decimal(str(data.get("totalDue", data.get("redemptionAmount", "")))),
            status=self._parse_lien_status(data.get("status", "")),
            property_address=data.get("address", data.get("situs")),
            owner_name=data.get("owner", data.get("defendant")),
            legal_description=data.get("legalDescription"),
            tax_years=tax_years,
            holder_name=data.get("plaintiff", "Harris County et al."),
            redemption_date=self._parse_date(data.get("redemptionDate", "")),
            redemption_amount=self._parse_decimal(str(data.get("redemptionAmount", ""))),
            redemption_deadline=self._parse_date(data.get("redemptionDeadline", "")),
            sale_date=self._parse_date(data.get("saleDate", "")),
            sale_type=TaxSaleType.TAX_DEED_SALE,  # Texas uses deed sales
            sale_amount=self._parse_decimal(str(data.get("saleAmount", ""))),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.BASE_URL}suit/{lien_number}",
            raw_data=data,
        )

    def _parse_tax_sale_property(self, data: Dict[str, Any]) -> Optional[TaxSaleProperty]:
        """Parse a tax sale property listing (sheriff sale)."""
        account = data.get("accountNumber", data.get("account", ""))
        if not account:
            return None

        formatted_account = self._format_account(account)

        # Parse delinquent years
        tax_years = data.get("taxYears", data.get("yearsDelinquent", []))
        if isinstance(tax_years, str):
            tax_years = [int(y.strip()) for y in tax_years.split(",") if y.strip().isdigit()]
        elif isinstance(tax_years, int):
            tax_years = [tax_years]

        return TaxSaleProperty(
            sale_id=data.get("saleId", data.get("suitNumber", data.get("causeNumber"))),
            parcel_id=formatted_account,
            property_address=data.get("address", data.get("situs")),
            city=data.get("city"),
            zip_code=data.get("zip", data.get("zipCode")),
            legal_description=data.get("legalDescription"),
            property_type=data.get("propertyType", data.get("stateCode")),
            owner_name=data.get("owner", data.get("defendant")),
            owner_address=data.get("ownerAddress"),
            tax_years_delinquent=tax_years,
            total_taxes_due=self._parse_decimal(str(data.get("taxesDue", ""))),
            penalties_due=self._parse_decimal(str(data.get("penalty", ""))),
            interest_due=self._parse_decimal(str(data.get("interest", ""))),
            fees_due=self._parse_decimal(str(data.get("attorneyFees", data.get("costs", "")))),
            total_amount_due=self._parse_decimal(str(data.get("judgmentAmount", data.get("minimumBid", "")))),
            sale_type=TaxSaleType.TAX_DEED_SALE,  # Texas sheriff sales convey deed
            sale_date=self._parse_date(data.get("saleDate", "")),
            auction_date=self._parse_date(data.get("auctionDate", data.get("saleDate", ""))),
            minimum_bid=self._parse_decimal(str(data.get("minimumBid", data.get("judgmentAmount", "")))),
            opening_bid=self._parse_decimal(str(data.get("openingBid", ""))),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", data.get("appraised", "")))),
            market_value=self._parse_decimal(str(data.get("marketValue", data.get("appraised", "")))),
            status=data.get("status", ""),
            sold=data.get("sold", False),
            winning_bid=self._parse_decimal(str(data.get("winningBid", data.get("salePrice", "")))),
            winning_bidder=data.get("buyer", data.get("purchaser")),
            redemption_period_ends=self._parse_date(data.get("redemptionDeadline", "")),
            redeemable=data.get("redeemable", True),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.BASE_URL}taxsale?account={formatted_account}",
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

def get_harris_county_tax_record(parcel_id: str) -> Optional[PropertyTaxRecord]:
    """Get Harris County tax record by account number."""
    treasurer = HarrisCountyTreasurer()

    async def _get():
        async with treasurer:
            return await treasurer.get_tax_record(parcel_id)
    return asyncio.run(_get())


def search_harris_county_by_address(
    street_address: str,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    **kwargs
) -> TaxSearchResult:
    """Search Harris County tax records by address."""
    treasurer = HarrisCountyTreasurer()

    async def _search():
        async with treasurer:
            return await treasurer.search_by_address(street_address, city, zip_code, **kwargs)
    return asyncio.run(_search())


def search_harris_county_by_owner(owner_name: str, **kwargs) -> TaxSearchResult:
    """Search Harris County tax records by owner name."""
    treasurer = HarrisCountyTreasurer()

    async def _search():
        async with treasurer:
            return await treasurer.search_by_owner(owner_name, **kwargs)
    return asyncio.run(_search())
