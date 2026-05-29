"""
Miami-Dade County, Florida Tax Collector Scraper

Miami-Dade County Tax Collector manages property tax collection for
approximately 900,000 parcels across Miami-Dade County, the most
populous county in Florida.

Website: https://www.miamidade.gov/taxcollector/
Property Tax Search: https://www.miamidade.gov/taxcollector/property-search.asp

The Miami-Dade Tax Collector provides:
- Property tax information
- Tax certificates
- Payment history
- Tax deed sales
- Delinquent tax information
- Payment plans

Tax Calendar (Miami-Dade County, Florida):
- Tax year: Calendar year (January 1 - December 31)
- Bills mailed: November 1
- Due date: March 31
- Discounts: 4% Nov, 3% Dec, 2% Jan, 1% Feb
- Delinquent: April 1
- Tax certificate sale: June 1
- Tax deed application: After 2 years

Florida is a tax certificate state (not lien):
- Certificates earn 18% max interest (competitive bidding)
- After 2 years, certificate holder can apply for tax deed
- 22-year redemption period limit
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


class MiamiDadeCountyTreasurer(CountyTreasurerBase):
    """
    Miami-Dade County, Florida Tax Collector scraper.

    Uses the Miami-Dade Tax Collector property tax portal.
    Folio format: XX-XXXX-XXX-XXXX (13 digits)
    """

    COUNTY_NAME = "Miami-Dade County"
    STATE = "FL"
    FIPS_CODE = "12086"
    BASE_URL = "https://www.miamidade.gov/taxcollector/"
    TAX_SEARCH_URL = "https://www.miamidade.gov/taxcollector/property-search.asp"
    SYSTEM_NAME = "Miami-Dade County Tax Collector"

    # API endpoints
    API_BASE = "https://www.miamidade.gov/taxcollector/api/"

    # Tax calendar (Florida)
    TAX_YEAR_START = "01-01"
    BILLS_MAILED = "11-01"
    DUE_DATE = "03-31"
    DELINQUENT_DATE = "04-01"
    CERTIFICATE_SALE = "06-01"

    # Florida discount schedule
    DISCOUNT_SCHEDULE = {
        11: Decimal("0.04"),  # November: 4%
        12: Decimal("0.03"),  # December: 3%
        1: Decimal("0.02"),  # January: 2%
        2: Decimal("0.01"),  # February: 1%
        3: Decimal("0.00"),  # March: 0%
    }

    # Tax certificate info
    MAX_INTEREST_RATE = Decimal("0.18")  # 18% per annum
    DEED_APPLICATION_YEARS = 2
    REDEMPTION_LIMIT_YEARS = 22

    # Major taxing authorities
    TAXING_AUTHORITIES = {
        "COUNTY": "Miami-Dade County",
        "SCHOOL": "Miami-Dade County School Board",
        "SFWMD": "South Florida Water Management District",
        "FIU": "Florida International University",
        "CHILD": "Children's Trust",
        "JACKSON": "Jackson Memorial Hospital",
        "LIBRARY": "Miami-Dade Public Library",
        "CITY_MIAMI": "City of Miami",
        "CITY_HIALEAH": "City of Hialeah",
        "CITY_MIAMI_BEACH": "City of Miami Beach",
        "CITY_CORAL_GABLES": "City of Coral Gables",
        "CITY_HOMESTEAD": "City of Homestead",
    }

    # Property use codes (Florida DOR)
    PROPERTY_USE_CODES = {
        "00": "Vacant Residential",
        "01": "Single Family",
        "02": "Mobile Home",
        "03": "Multi-Family (2-9 units)",
        "04": "Condominium",
        "05": "Cooperatives",
        "06": "Retirement Home",
        "07": "Miscellaneous Residential",
        "08": "Multi-Family (10+ units)",
        "10": "Vacant Commercial",
        "11": "Store",
        "12": "Mixed Use (store/office)",
        "14": "Supermarket",
        "16": "Community Shopping Center",
        "17": "Regional Shopping Center",
        "18": "Office (1 story)",
        "19": "Office (multi-story)",
        "20": "Airport/Bus Terminal",
    }

    def _format_folio(self, folio: str) -> str:
        """Format folio number to standard Miami-Dade format: XX-XXXX-XXX-XXXX"""
        # Remove any existing dashes, spaces, or non-digits
        digits = re.sub(r"[^0-9]", "", folio)

        if len(digits) == 13:
            return f"{digits[0:2]}-{digits[2:6]}-{digits[6:9]}-{digits[9:13]}"

        return folio  # Return as-is if not 13 digits

    def _parse_folio(self, folio: str) -> Dict[str, str]:
        """Parse folio into components."""
        digits = re.sub(r"[^0-9]", "", folio)

        if len(digits) != 13:
            return {"raw": folio}

        return {
            "municipality": digits[0:2],
            "township_range": digits[2:6],
            "section": digits[6:9],
            "parcel": digits[9:13],
            "formatted": self._format_folio(folio),
        }

    def _calculate_discount(self, amount: Decimal, month: int) -> Decimal:
        """Calculate Florida early payment discount."""
        rate = self.DISCOUNT_SCHEDULE.get(month, Decimal("0.00"))
        return amount * rate

    async def get_tax_record(self, parcel_id: str) -> Optional[PropertyTaxRecord]:
        """Get property tax record by folio number."""
        formatted_folio = self._format_folio(parcel_id)
        detail_url = f"{self.API_BASE}property/{formatted_folio}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"Miami-Dade tax record fetch failed: {e}")
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
            logger.error(f"Miami-Dade address search failed: {e}")
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
            logger.error(f"Miami-Dade owner search failed: {e}")
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
            logger.error(f"Miami-Dade delinquent list failed: {e}")
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
        """Get properties with tax certificates for sale or tax deed applications."""
        sale_url = f"{self.API_BASE}taxsale"

        params = {"limit": min(max_results, 500)}
        if upcoming_only:
            params["upcoming"] = "true"
        if sale_type:
            params["type"] = sale_type.value

        try:
            json_response = await self._fetch_json(sale_url, params=params)
        except Exception as e:
            logger.error(f"Miami-Dade tax sale list failed: {e}")
            return []

        properties = []
        results = json_response.get("properties", json_response.get("certificates", []))

        for item in results[:max_results]:
            prop = self._parse_tax_sale_property(item)
            if prop:
                properties.append(prop)

        return properties

    async def get_tax_liens(
        self,
        parcel_id: Optional[str] = None,
        status: Optional[LienStatus] = None,
        max_results: int = 100,
    ) -> List[TaxLien]:
        """Get tax certificates (Florida terminology for liens)."""
        certs_url = f"{self.API_BASE}certificates"

        params = {"limit": min(max_results, 100)}
        if parcel_id:
            params["folio"] = self._format_folio(parcel_id)
        if status:
            params["status"] = status.value

        try:
            json_response = await self._fetch_json(certs_url, params=params)
        except Exception as e:
            logger.error(f"Miami-Dade tax certificates failed: {e}")
            return []

        liens = []
        results = json_response.get("certificates", json_response.get("results", []))

        for item in results[:max_results]:
            lien = self._parse_tax_lien(item)
            if lien:
                liens.append(lien)

        return liens

    def _parse_search_result(self, item: Dict[str, Any]) -> Optional[PropertyTaxRecord]:
        """Parse a search result item into PropertyTaxRecord."""
        folio = item.get("folio", item.get("folioNumber", item.get("parcel", "")))
        if not folio:
            return None

        formatted_folio = self._format_folio(folio)

        # Parse current tax info
        current_tax = self._parse_decimal(
            str(item.get("totalTax", item.get("taxAmount", "")))
        )
        balance_due = self._parse_decimal(
            str(item.get("balanceDue", item.get("amountDue", "")))
        )
        amount_paid = self._parse_decimal(str(item.get("amountPaid", "")))

        # Determine status
        status_str = item.get("status", item.get("paymentStatus", ""))
        tax_status = self._parse_tax_status(status_str)
        is_delinquent = "DELINQUENT" in str(status_str).upper() or item.get(
            "isDelinquent", False
        )
        has_cert = item.get("hasCertificate", item.get("certSold", False))

        # Parse exemptions (Florida exemptions)
        exemptions = []
        if item.get("homesteadExemption") or item.get("hasHomestead"):
            exemptions.append("Homestead Exemption")
        if item.get("seniorExemption") or item.get("hasSenior"):
            exemptions.append("Senior Exemption")
        if item.get("widowExemption"):
            exemptions.append("Widow/Widower Exemption")
        if item.get("disabledExemption"):
            exemptions.append("Disability Exemption")
        if item.get("veteranExemption"):
            exemptions.append("Veteran Exemption")
        if item.get("blindExemption"):
            exemptions.append("Blind Person Exemption")
        for ex in item.get("exemptions", []):
            if ex not in exemptions:
                exemptions.append(ex)

        # Get property use description
        use_code = item.get("useCode", item.get("dor", ""))
        use_desc = self.PROPERTY_USE_CODES.get(str(use_code), "")

        return PropertyTaxRecord(
            parcel_id=formatted_folio,
            property_address=item.get("address", item.get("situsAddress")),
            city=item.get("city", item.get("situsCity")),
            state=self.STATE,
            zip_code=item.get("zip", item.get("situsZip")),
            county=self.COUNTY_NAME,
            owner_name=item.get("owner", item.get("ownerName")),
            owner_address=item.get("ownerAddress", item.get("mailingAddress")),
            assessed_value=self._parse_decimal(str(item.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(str(item.get("taxableValue", ""))),
            market_value=self._parse_decimal(
                str(item.get("justValue", item.get("marketValue", "")))
            ),
            current_tax_year=self._parse_int(str(item.get("taxYear", ""))),
            current_tax_amount=current_tax,
            current_amount_paid=amount_paid,
            current_balance_due=balance_due,
            tax_status=tax_status,
            is_delinquent=is_delinquent,
            years_delinquent=self._parse_int(str(item.get("yearsDelinquent", "0")))
            or 0,
            total_delinquent=self._parse_decimal(
                str(item.get("totalDelinquent", item.get("priorDue", "")))
            ),
            exemptions=exemptions,
            exemption_amount=self._parse_decimal(str(item.get("exemptionAmount", ""))),
            has_tax_lien=has_cert,
            source_url=f"{self.TAX_SEARCH_URL}?folio={formatted_folio}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_tax_record(self, data: Dict[str, Any]) -> PropertyTaxRecord:
        """Parse detailed tax record data."""
        folio = data.get("folio", data.get("folioNumber", data.get("parcel", "")))
        formatted_folio = self._format_folio(folio)

        # Parse tax bills
        tax_bills = []
        for bill_data in data.get("taxBills", data.get("bills", [])):
            bill = self._parse_tax_bill(bill_data, formatted_folio)
            if bill:
                tax_bills.append(bill)

        # Sort bills by year (most recent first)
        tax_bills.sort(key=lambda b: b.tax_year, reverse=True)

        # Parse payment history
        payment_history = []
        for payment_data in data.get("payments", data.get("paymentHistory", [])):
            payment = self._parse_payment(payment_data, formatted_folio)
            if payment:
                payment_history.append(payment)

        # Parse tax certificates (liens)
        liens = []
        for cert_data in data.get("certificates", data.get("taxCertificates", [])):
            lien = self._parse_tax_lien(cert_data)
            if lien:
                liens.append(lien)

        # Parse exemptions
        exemptions = []
        exemption_amount = Decimal(0)

        if data.get("homesteadExemption") or data.get("hasHomestead"):
            exemptions.append("Homestead Exemption")
            exemption_amount += Decimal("50000")  # Standard HOX up to $50K
        if data.get("seniorExemption") or data.get("hasSenior"):
            exemptions.append("Senior Exemption")
            exemption_amount += Decimal("50000")  # Additional senior exemption
        if data.get("widowExemption"):
            exemptions.append("Widow/Widower Exemption")
            exemption_amount += Decimal("5000")
        if data.get("disabledExemption"):
            exemptions.append("Disability Exemption")
            exemption_amount += Decimal("5000")
        if data.get("veteranExemption"):
            exemptions.append("Veteran Exemption")
        if data.get("blindExemption"):
            exemptions.append("Blind Person Exemption")
            exemption_amount += Decimal("5000")

        for ex_data in data.get("exemptions", []):
            if isinstance(ex_data, str):
                if ex_data not in exemptions:
                    exemptions.append(ex_data)
            elif isinstance(ex_data, dict):
                exemptions.append(ex_data.get("type", ex_data.get("name", "Exemption")))
                amt = self._parse_decimal(str(ex_data.get("amount", "")))
                if amt:
                    exemption_amount += amt

        # Parse special assessments (non-ad valorem)
        special_assessments = []
        for assess_data in data.get("nonAdValorem", data.get("specialAssessments", [])):
            item = TaxBillItem(
                description=assess_data.get(
                    "description", assess_data.get("name", "Non-Ad Valorem Assessment")
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
            str(data.get("totalTax", data.get("currentYearTax", "")))
        )
        balance_due = self._parse_decimal(
            str(data.get("balanceDue", data.get("totalDue", "")))
        )
        amount_paid = self._parse_decimal(str(data.get("amountPaid", "")))
        total_delinquent = self._parse_decimal(
            str(data.get("totalDelinquent", data.get("priorYearsDue", "")))
        )

        # Determine status
        status_str = data.get("status", data.get("paymentStatus", ""))
        tax_status = self._parse_tax_status(status_str)
        is_delinquent = "DELINQUENT" in str(status_str).upper() or data.get(
            "isDelinquent", False
        )
        has_cert = len(liens) > 0 or data.get("certSold", False)

        if not is_delinquent and total_delinquent and total_delinquent > 0:
            is_delinquent = True

        if is_delinquent:
            tax_status = TaxStatus.DELINQUENT

        return PropertyTaxRecord(
            parcel_id=formatted_folio,
            property_address=data.get("address", data.get("situsAddress")),
            city=data.get("city", data.get("situsCity")),
            state=self.STATE,
            zip_code=data.get("zip", data.get("situsZip")),
            county=self.COUNTY_NAME,
            owner_name=data.get("owner", data.get("ownerName")),
            owner_address=data.get("ownerAddress", data.get("mailingAddress")),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(str(data.get("taxableValue", ""))),
            market_value=self._parse_decimal(
                str(data.get("justValue", data.get("marketValue", "")))
            ),
            current_tax_year=self._parse_int(str(data.get("taxYear", ""))),
            current_tax_amount=current_tax,
            current_amount_paid=amount_paid,
            current_balance_due=balance_due,
            tax_status=tax_status,
            is_delinquent=is_delinquent,
            years_delinquent=self._parse_int(str(data.get("yearsDelinquent", "0")))
            or 0,
            total_delinquent=total_delinquent,
            exemptions=exemptions,
            exemption_amount=exemption_amount if exemption_amount > 0 else None,
            tax_bills=tax_bills,
            payment_history=payment_history,
            has_tax_lien=has_cert,
            liens=liens,
            special_assessments=special_assessments,
            source_url=f"{self.TAX_SEARCH_URL}?folio={formatted_folio}",
            source_system=self.SYSTEM_NAME,
            last_updated=self._parse_datetime(data.get("lastUpdated", "")),
            raw_data=data,
        )

    def _parse_tax_bill(self, data: Dict[str, Any], folio: str) -> Optional[TaxBill]:
        """Parse a tax bill record."""
        tax_year = self._parse_int(str(data.get("taxYear", data.get("year", ""))))
        if not tax_year:
            return None

        # Parse line items (from different taxing authorities)
        line_items = []

        # Ad valorem taxes
        for item_data in data.get("adValorem", data.get("taxingAuthorities", [])):
            authority_code = item_data.get("code", item_data.get("authorityCode", ""))
            authority_name = self.TAXING_AUTHORITIES.get(
                authority_code, item_data.get("name", item_data.get("authority", ""))
            )

            item = TaxBillItem(
                description=authority_name
                or item_data.get("description", "Ad Valorem Tax"),
                amount=self._parse_decimal(
                    str(item_data.get("amount", item_data.get("tax", "")))
                )
                or Decimal(0),
                taxing_authority=authority_name,
                tax_rate=self._parse_decimal(
                    str(item_data.get("rate", item_data.get("millage", "")))
                ),
                assessed_value=self._parse_decimal(
                    str(item_data.get("taxableValue", ""))
                ),
                raw_data=item_data,
            )
            line_items.append(item)

        # Non-ad valorem assessments
        for item_data in data.get("nonAdValorem", []):
            item = TaxBillItem(
                description=item_data.get(
                    "description", item_data.get("name", "Non-Ad Valorem")
                ),
                amount=self._parse_decimal(str(item_data.get("amount", "")))
                or Decimal(0),
                taxing_authority=item_data.get("authority", item_data.get("district")),
                raw_data=item_data,
            )
            line_items.append(item)

        # Calculate discount if applicable
        gross_tax = self._parse_decimal(
            str(data.get("grossTax", data.get("totalTax", "")))
        )
        discount = self._parse_decimal(str(data.get("discount", "")))

        return TaxBill(
            bill_number=data.get("billNumber", data.get("receiptNumber")),
            tax_year=tax_year,
            parcel_id=folio,
            property_address=data.get("address", data.get("situsAddress")),
            owner_name=data.get("owner", data.get("ownerName")),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            taxable_value=self._parse_decimal(str(data.get("taxableValue", ""))),
            tax_rate=self._parse_decimal(
                str(data.get("combinedMillage", data.get("taxRate", "")))
            ),
            gross_tax=gross_tax,
            exemptions=self._parse_decimal(str(data.get("exemptions", ""))),
            net_tax=self._parse_decimal(str(data.get("netTax", ""))),
            penalties=self._parse_decimal(
                str(data.get("interest", data.get("penalties", "")))
            ),
            interest=self._parse_decimal(str(data.get("interest", ""))),
            fees=self._parse_decimal(str(data.get("fees", data.get("costs", "")))),
            total_due=self._parse_decimal(
                str(data.get("totalDue", data.get("amountDue", "")))
            ),
            amount_paid=self._parse_decimal(str(data.get("amountPaid", ""))),
            balance_due=self._parse_decimal(str(data.get("balanceDue", ""))),
            payment_status=self._parse_tax_status(data.get("status", "")),
            bill_date=self._parse_date(data.get("billDate", "")),
            due_date=self._parse_date(data.get("dueDate", "")),
            delinquent_date=self._parse_date(data.get("delinquentDate", "")),
            installment_number=1,  # Florida is single payment (with discounts)
            total_installments=1,
            line_items=line_items,
            source_url=f"{self.TAX_SEARCH_URL}?folio={folio}&year={tax_year}",
            raw_data=data,
        )

    def _parse_payment(self, data: Dict[str, Any], folio: str) -> Optional[TaxPayment]:
        """Parse a payment record."""
        payment_date = self._parse_date(data.get("paymentDate", data.get("date", "")))
        amount = self._parse_decimal(
            str(data.get("amount", data.get("paymentAmount", "")))
        )

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
            payment_id=data.get(
                "paymentId", data.get("transactionId", data.get("receiptNumber"))
            ),
            parcel_id=folio,
            tax_year=self._parse_int(str(data.get("taxYear", ""))) or 0,
            payment_date=payment_date,
            payment_amount=amount,
            payment_method=method,
            principal_paid=self._parse_decimal(
                str(data.get("principal", data.get("taxPaid", "")))
            ),
            interest_paid=self._parse_decimal(str(data.get("interest", ""))),
            penalty_paid=self._parse_decimal(str(data.get("penalty", ""))),
            fees_paid=self._parse_decimal(str(data.get("fees", data.get("costs", "")))),
            receipt_number=data.get("receiptNumber", data.get("confirmationNumber")),
            check_number=data.get("checkNumber"),
            payer_name=data.get("payer", data.get("payerName")),
            raw_data=data,
        )

    def _parse_tax_lien(self, data: Dict[str, Any]) -> Optional[TaxLien]:
        """Parse a tax certificate record (Florida term for liens)."""
        cert_number = data.get(
            "certificateNumber", data.get("certNumber", data.get("lienNumber", ""))
        )
        folio = data.get("folio", data.get("folioNumber", data.get("parcel", "")))

        if not cert_number and not folio:
            return None

        formatted_folio = self._format_folio(folio) if folio else ""

        # Parse tax years covered
        tax_years = data.get("taxYears", data.get("years", []))
        if isinstance(tax_years, str):
            tax_years = [
                int(y.strip()) for y in tax_years.split(",") if y.strip().isdigit()
            ]
        elif isinstance(tax_years, int):
            tax_years = [tax_years]

        # Calculate redemption deadline
        sale_date = self._parse_date(data.get("saleDate", ""))
        redemption_deadline = None
        if sale_date:
            # Tax deed can be applied after 2 years, expires at 22 years
            redemption_deadline = date(
                sale_date.year + self.DEED_APPLICATION_YEARS,
                sale_date.month,
                sale_date.day,
            )

        return TaxLien(
            lien_number=str(cert_number) if cert_number else f"CERT-{formatted_folio}",
            parcel_id=formatted_folio,
            lien_date=sale_date,
            lien_amount=self._parse_decimal(
                str(data.get("faceAmount", data.get("purchaseAmount", "")))
            ),
            face_value=self._parse_decimal(
                str(data.get("faceAmount", data.get("taxAmount", "")))
            ),
            interest_rate=self._parse_decimal(
                str(data.get("bidRate", data.get("interestRate", "")))
            )
            or self.MAX_INTEREST_RATE,
            accrued_interest=self._parse_decimal(str(data.get("accruedInterest", ""))),
            penalties=self._parse_decimal(
                str(data.get("omittedTaxes", data.get("subsequentTaxes", "")))
            ),
            total_due=self._parse_decimal(
                str(data.get("redemptionAmount", data.get("totalDue", "")))
            ),
            status=self._parse_lien_status(data.get("status", "")),
            property_address=data.get("address", data.get("situsAddress")),
            owner_name=data.get("owner", data.get("ownerName")),
            legal_description=data.get("legalDescription"),
            tax_years=tax_years,
            holder_name=data.get(
                "holder", data.get("certificateHolder", data.get("purchaser"))
            ),
            holder_address=data.get("holderAddress"),
            assignment_date=self._parse_date(data.get("assignmentDate", "")),
            redemption_date=self._parse_date(data.get("redemptionDate", "")),
            redemption_amount=self._parse_decimal(
                str(data.get("redemptionAmount", ""))
            ),
            redemption_deadline=redemption_deadline
            or self._parse_date(data.get("deedApplicationDate", "")),
            sale_date=sale_date,
            sale_type=TaxSaleType.TAX_LIEN_SALE,  # Florida uses tax certificates
            sale_amount=self._parse_decimal(
                str(data.get("purchaseAmount", data.get("bidAmount", "")))
            ),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.BASE_URL}certificate/{cert_number}",
            raw_data=data,
        )

    def _parse_tax_sale_property(
        self, data: Dict[str, Any]
    ) -> Optional[TaxSaleProperty]:
        """Parse a tax sale property listing."""
        folio = data.get("folio", data.get("folioNumber", data.get("parcel", "")))
        if not folio:
            return None

        formatted_folio = self._format_folio(folio)

        # Parse delinquent years
        tax_years = data.get("taxYears", data.get("years", []))
        if isinstance(tax_years, str):
            tax_years = [
                int(y.strip()) for y in tax_years.split(",") if y.strip().isdigit()
            ]
        elif isinstance(tax_years, int):
            tax_years = [tax_years]

        # Determine sale type
        is_deed_sale = data.get("isDeedSale", data.get("taxDeed", False))
        sale_type = (
            TaxSaleType.TAX_DEED_SALE if is_deed_sale else TaxSaleType.TAX_LIEN_SALE
        )

        return TaxSaleProperty(
            sale_id=data.get(
                "saleId", data.get("certificateNumber", data.get("itemNumber"))
            ),
            parcel_id=formatted_folio,
            property_address=data.get("address", data.get("situsAddress")),
            city=data.get("city", data.get("situsCity")),
            zip_code=data.get("zip", data.get("situsZip")),
            legal_description=data.get("legalDescription"),
            property_type=self.PROPERTY_USE_CODES.get(
                str(data.get("useCode", "")), data.get("propertyType")
            ),
            owner_name=data.get("owner", data.get("ownerName")),
            owner_address=data.get("ownerAddress", data.get("mailingAddress")),
            tax_years_delinquent=tax_years,
            total_taxes_due=self._parse_decimal(str(data.get("taxesDue", ""))),
            penalties_due=self._parse_decimal(str(data.get("interest", ""))),
            interest_due=self._parse_decimal(str(data.get("interest", ""))),
            fees_due=self._parse_decimal(str(data.get("costs", data.get("fees", "")))),
            total_amount_due=self._parse_decimal(
                str(data.get("faceAmount", data.get("openingBid", "")))
            ),
            sale_type=sale_type,
            sale_date=self._parse_date(data.get("saleDate", "")),
            auction_date=self._parse_date(
                data.get("auctionDate", data.get("saleDate", ""))
            ),
            minimum_bid=self._parse_decimal(
                str(data.get("faceAmount", data.get("openingBid", "")))
            ),
            opening_bid=self._parse_decimal(str(data.get("openingBid", ""))),
            assessed_value=self._parse_decimal(str(data.get("assessedValue", ""))),
            market_value=self._parse_decimal(
                str(data.get("justValue", data.get("marketValue", "")))
            ),
            status=data.get("status", ""),
            sold=data.get("sold", False),
            winning_bid=self._parse_decimal(
                str(data.get("winningBid", data.get("purchaseAmount", "")))
            ),
            winning_bidder=data.get("buyer", data.get("purchaser")),
            redemption_period_ends=self._parse_date(
                data.get("redemptionDeadline", data.get("deedApplicationDate", ""))
            ),
            redeemable=not is_deed_sale,  # Deed sales are not redeemable
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.BASE_URL}taxsale?folio={formatted_folio}",
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


def get_miami_dade_tax_record(parcel_id: str) -> Optional[PropertyTaxRecord]:
    """Get Miami-Dade County tax record by folio number."""
    treasurer = MiamiDadeCountyTreasurer()

    async def _get():
        async with treasurer:
            return await treasurer.get_tax_record(parcel_id)

    return asyncio.run(_get())


def search_miami_dade_by_address(
    street_address: str,
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
    **kwargs,
) -> TaxSearchResult:
    """Search Miami-Dade County tax records by address."""
    treasurer = MiamiDadeCountyTreasurer()

    async def _search():
        async with treasurer:
            return await treasurer.search_by_address(
                street_address, city, zip_code, **kwargs
            )

    return asyncio.run(_search())


def search_miami_dade_by_owner(owner_name: str, **kwargs) -> TaxSearchResult:
    """Search Miami-Dade County tax records by owner name."""
    treasurer = MiamiDadeCountyTreasurer()

    async def _search():
        async with treasurer:
            return await treasurer.search_by_owner(owner_name, **kwargs)

    return asyncio.run(_search())
