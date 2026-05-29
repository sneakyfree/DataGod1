"""
Cook County, Illinois Recorder of Deeds Scraper

Cook County is the second most populous county in the United States (5.2M+)
and includes Chicago. The recorder's office maintains records dating back to 1871.

System: Custom web application
URL: https://www.cookcountyrecorder.com/
FIPS: 17031

Available searches:
- Name search (grantor/grantee)
- Document number search
- PIN (Property Index Number) search
- Address search (limited)
- Book/Page search

Note: Some searches may require registration for full access.
Images are available for purchase ($1.00/page typically).
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin

import aiohttp
from bs4 import BeautifulSoup

from .base import (
    CountyRecorderBase,
    DocumentParty,
    DocumentStatus,
    DocumentType,
    LegalDescription,
    PartyRole,
    RecordedDocument,
    SearchCriteria,
    SearchResult,
)

logger = logging.getLogger(__name__)


class CookCountyRecorder(CountyRecorderBase):
    """
    Scraper for Cook County, Illinois Recorder of Deeds.

    Cook County uses a custom web application for public record searches.
    The system provides access to recorded documents from 1985 to present.
    Earlier records (1871-1984) may require in-person research.
    """

    COUNTY_NAME = "Cook County"
    STATE = "Illinois"
    STATE_ABBREV = "IL"
    FIPS_CODE = "17031"

    BASE_URL = "https://www.cookcountyrecorder.com/"
    SEARCH_URL = "https://www.cookcountyrecorder.com/search"
    SYSTEM_NAME = "Cook County Recorder Custom System"

    REQUEST_DELAY = 2.0  # Be respectful of their servers
    MAX_RETRIES = 3
    TIMEOUT = 45

    REQUIRES_LOGIN = False
    REQUIRES_CAPTCHA = False  # May have CAPTCHA for bulk searches

    # Cook County PIN format: XX-XX-XXX-XXX-XXXX
    PIN_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{3}-\d{3}-\d{4}$")

    # Document type mappings specific to Cook County
    COOK_COUNTY_DOC_TYPES = {
        "DEED": DocumentType.WARRANTY_DEED,
        "WD": DocumentType.WARRANTY_DEED,
        "WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "QCD": DocumentType.QUITCLAIM_DEED,
        "QUIT CLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "QUITCLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "TD": DocumentType.TRUSTEES_DEED,
        "TRUSTEE'S DEED": DocumentType.TRUSTEES_DEED,
        "TRUSTEES DEED": DocumentType.TRUSTEES_DEED,
        "MTG": DocumentType.MORTGAGE,
        "MORTGAGE": DocumentType.MORTGAGE,
        "RELEASE": DocumentType.MORTGAGE_RELEASE,
        "REL": DocumentType.MORTGAGE_RELEASE,
        "RELEASE OF MORTGAGE": DocumentType.MORTGAGE_RELEASE,
        "SATISFACTION": DocumentType.MORTGAGE_RELEASE,
        "ASGN": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT OF MORTGAGE": DocumentType.MORTGAGE_ASSIGNMENT,
        "ML": DocumentType.MECHANICS_LIEN,
        "MECHANICS LIEN": DocumentType.MECHANICS_LIEN,
        "MECHANIC'S LIEN": DocumentType.MECHANICS_LIEN,
        "CONSTRUCTION LIEN": DocumentType.MECHANICS_LIEN,
        "LP": DocumentType.LIS_PENDENS,
        "LIS PENDENS": DocumentType.LIS_PENDENS,
        "NOTICE OF LIS PENDENS": DocumentType.LIS_PENDENS,
        "JL": DocumentType.JUDGMENT_LIEN,
        "JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "JUDGMENT LIEN": DocumentType.JUDGMENT_LIEN,
        "FTL": DocumentType.TAX_LIEN_FEDERAL,
        "FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "IRS LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "STL": DocumentType.TAX_LIEN_STATE,
        "STATE TAX LIEN": DocumentType.TAX_LIEN_STATE,
        "IL TAX LIEN": DocumentType.TAX_LIEN_STATE,
        "UCC": DocumentType.UCC_FINANCING,
        "UCC-1": DocumentType.UCC_FINANCING,
        "UCC FINANCING STATEMENT": DocumentType.UCC_FINANCING,
        "PLAT": DocumentType.PLAT_MAP,
        "PLAT OF SUBDIVISION": DocumentType.PLAT_MAP,
        "SUBDIVISION PLAT": DocumentType.SUBDIVISION_MAP,
        "EASEMENT": DocumentType.EASEMENT,
        "COVENANT": DocumentType.RESTRICTIVE_COVENANT,
        "DECLARATION": DocumentType.DECLARATION,
        "AFFIDAVIT": DocumentType.AFFIDAVIT,
        "AFF": DocumentType.AFFIDAVIT,
        "POA": DocumentType.POWER_OF_ATTORNEY,
        "POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,
        "LEASE": DocumentType.LEASE,
        "MEMORANDUM OF LEASE": DocumentType.MEMORANDUM,
    }

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the Cook County recorder scraper."""
        super().__init__(session)
        self._search_token: Optional[str] = None

    async def _initialize_session(self):
        """Initialize a search session and get any required tokens."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        # Visit the main search page to get any CSRF tokens or session cookies
        status, html = await self._fetch(self.SEARCH_URL)
        if status != 200:
            logger.warning(f"Failed to initialize session: HTTP {status}")
            return

        soup = self._parse_html(html)

        # Look for CSRF or verification token
        token_input = soup.find("input", {"name": "__RequestVerificationToken"})
        if token_input:
            self._search_token = token_input.get("value")
            logger.debug("Obtained search verification token")

    def _parse_cook_county_document_type(self, raw_type: str) -> DocumentType:
        """Parse Cook County-specific document type strings."""
        if not raw_type:
            return DocumentType.UNKNOWN

        raw_type = raw_type.upper().strip()

        # Check Cook County specific mappings first
        if raw_type in self.COOK_COUNTY_DOC_TYPES:
            return self.COOK_COUNTY_DOC_TYPES[raw_type]

        # Fall back to base class parsing
        return self._parse_document_type(raw_type)

    def _parse_pin(self, pin_str: str) -> Optional[str]:
        """Parse and validate a Cook County PIN (Property Index Number)."""
        if not pin_str:
            return None

        # Remove spaces and standardize dashes
        pin_str = pin_str.strip().replace(" ", "-")

        # If already in correct format, return as-is
        if self.PIN_PATTERN.match(pin_str):
            return pin_str

        # Try to format a PIN without dashes (14 digits)
        digits = re.sub(r"[^\d]", "", pin_str)
        if len(digits) == 14:
            return f"{digits[0:2]}-{digits[2:4]}-{digits[4:7]}-{digits[7:10]}-{digits[10:14]}"

        logger.warning(f"Invalid Cook County PIN format: {pin_str}")
        return pin_str  # Return as-is, let the search handle it

    def _parse_search_results(self, html: str) -> List[RecordedDocument]:
        """Parse search results HTML into RecordedDocument objects."""
        documents = []
        soup = self._parse_html(html)

        # Find the results table
        results_table = soup.find("table", {"class": "results"}) or soup.find(
            "table", {"id": "searchResults"}
        )
        if not results_table:
            # Try alternative selectors
            results_table = soup.find(
                "table", class_=lambda x: x and "result" in x.lower()
            )

        if not results_table:
            logger.debug("No results table found in HTML")
            return documents

        rows = results_table.find_all("tr")[1:]  # Skip header row

        for row in rows:
            try:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                doc = self._parse_result_row(cells)
                if doc:
                    documents.append(doc)

            except Exception as e:
                logger.warning(f"Error parsing result row: {e}")
                continue

        return documents

    def _parse_result_row(self, cells: List) -> Optional[RecordedDocument]:
        """Parse a single result row into a RecordedDocument."""
        try:
            # Column order may vary - this is a typical layout:
            # Doc Number | Doc Type | Recorded Date | Grantor | Grantee | PIN | Consideration

            doc_number = cells[0].get_text(strip=True) if len(cells) > 0 else None
            if not doc_number:
                return None

            doc_type_raw = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            recorded_date_str = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            grantor_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            grantee_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            pin_text = cells[5].get_text(strip=True) if len(cells) > 5 else ""
            consideration_text = cells[6].get_text(strip=True) if len(cells) > 6 else ""

            # Check for document link
            doc_link = cells[0].find("a")
            source_url = None
            if doc_link and doc_link.get("href"):
                source_url = urljoin(self.BASE_URL, doc_link.get("href"))

            # Parse parties
            parties = []
            grantors = []
            grantees = []

            if grantor_text:
                for name in grantor_text.split(";"):
                    name = name.strip()
                    if name:
                        grantors.append(self._normalize_name(name))
                        parties.append(
                            DocumentParty(
                                name=self._normalize_name(name),
                                role=PartyRole.GRANTOR,
                                raw_name=name,
                            )
                        )

            if grantee_text:
                for name in grantee_text.split(";"):
                    name = name.strip()
                    if name:
                        grantees.append(self._normalize_name(name))
                        parties.append(
                            DocumentParty(
                                name=self._normalize_name(name),
                                role=PartyRole.GRANTEE,
                                raw_name=name,
                            )
                        )

            # Parse legal descriptions
            legal_descriptions = []
            parcels = []
            if pin_text:
                pin = self._parse_pin(pin_text)
                if pin:
                    parcels.append(pin)
                    legal_descriptions.append(
                        LegalDescription(
                            full_description=f"PIN: {pin}", parcel_number=pin, apn=pin
                        )
                    )

            return RecordedDocument(
                document_number=doc_number,
                document_type=self._parse_cook_county_document_type(doc_type_raw),
                document_type_raw=doc_type_raw,
                recorded_date=self._parse_date(recorded_date_str),
                parties=parties,
                grantors=grantors,
                grantees=grantees,
                legal_descriptions=legal_descriptions,
                parcels=parcels,
                consideration=self._parse_amount(consideration_text),
                county=self.COUNTY_NAME,
                state=self.STATE_ABBREV,
                fips_code=self.FIPS_CODE,
                source_url=source_url,
                raw_data={
                    "doc_type_raw": doc_type_raw,
                    "grantor_raw": grantor_text,
                    "grantee_raw": grantee_text,
                    "pin_raw": pin_text,
                },
            )

        except Exception as e:
            logger.warning(f"Error parsing result row: {e}")
            return None

    async def search_by_name(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        party_type: str = "either",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        document_types: Optional[List[DocumentType]] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """
        Search Cook County records by party name.

        Args:
            last_name: Last name or business name
            first_name: First name (optional)
            party_type: "grantor", "grantee", or "either"
            start_date: Start of recording date range
            end_date: End of recording date range
            document_types: Filter by document types
            max_results: Maximum results to return

        Returns:
            SearchResult with matching documents
        """
        import time

        start_time = time.time()

        if not self._search_token:
            await self._initialize_session()

        # Build search parameters
        params = {
            "searchType": "name",
            "lastName": last_name,
        }

        if first_name:
            params["firstName"] = first_name

        if party_type.lower() == "grantor":
            params["partyType"] = "G"
        elif party_type.lower() == "grantee":
            params["partyType"] = "E"
        else:
            params["partyType"] = "B"  # Both

        if start_date:
            params["startDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            params["endDate"] = end_date.strftime("%m/%d/%Y")

        if self._search_token:
            params["__RequestVerificationToken"] = self._search_token

        # Execute search
        search_url = f"{self.SEARCH_URL}/name"
        all_documents = []
        page = 1
        has_more = True

        while has_more and len(all_documents) < max_results:
            params["page"] = page
            params["pageSize"] = min(50, max_results - len(all_documents))

            try:
                status, html = await self._fetch(search_url, method="POST", data=params)

                if status != 200:
                    logger.warning(f"Search returned HTTP {status}")
                    break

                documents = self._parse_search_results(html)

                if not documents:
                    has_more = False
                else:
                    # Filter by document types if specified
                    if document_types:
                        documents = [
                            d for d in documents if d.document_type in document_types
                        ]

                    all_documents.extend(documents)
                    page += 1

                    # Check if we got fewer results than requested
                    if len(documents) < params["pageSize"]:
                        has_more = False

            except Exception as e:
                logger.error(f"Error during name search: {e}")
                break

        elapsed_ms = int((time.time() - start_time) * 1000)

        return SearchResult(
            documents=all_documents[:max_results],
            total_count=len(all_documents),
            page_number=1,
            page_size=max_results,
            has_more=len(all_documents) > max_results,
            search_criteria=SearchCriteria(
                last_name=last_name,
                first_name=first_name,
                party_type=party_type,
                start_date=start_date,
                end_date=end_date,
                document_types=document_types or [],
            ),
            search_time_ms=elapsed_ms,
            source_system=self.SYSTEM_NAME,
        )

    async def search_by_document_number(
        self, document_number: str
    ) -> Optional[RecordedDocument]:
        """
        Search for a specific document by its recording number.

        Args:
            document_number: The document/instrument number

        Returns:
            RecordedDocument if found, None otherwise
        """
        if not self._search_token:
            await self._initialize_session()

        params = {
            "searchType": "document",
            "documentNumber": document_number.strip(),
        }

        if self._search_token:
            params["__RequestVerificationToken"] = self._search_token

        search_url = f"{self.SEARCH_URL}/document"

        try:
            status, html = await self._fetch(search_url, method="POST", data=params)

            if status != 200:
                logger.warning(f"Document search returned HTTP {status}")
                return None

            documents = self._parse_search_results(html)

            if documents:
                # Get full details for the document
                return await self.get_document_detail(documents[0].document_number)

            return None

        except Exception as e:
            logger.error(f"Error during document search: {e}")
            return None

    async def search_by_parcel(
        self,
        parcel_number: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        document_types: Optional[List[DocumentType]] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """
        Search Cook County records by PIN (Property Index Number).

        Args:
            parcel_number: The Cook County PIN
            start_date: Start of recording date range
            end_date: End of recording date range
            document_types: Filter by document types
            max_results: Maximum results to return

        Returns:
            SearchResult with matching documents
        """
        import time

        start_time = time.time()

        if not self._search_token:
            await self._initialize_session()

        # Parse and validate PIN
        pin = self._parse_pin(parcel_number)
        if not pin:
            return SearchResult(
                documents=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(parcel_number=parcel_number),
                search_time_ms=0,
                source_system=self.SYSTEM_NAME,
                warnings=["Invalid PIN format"],
            )

        params = {
            "searchType": "pin",
            "pin": pin,
        }

        if start_date:
            params["startDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            params["endDate"] = end_date.strftime("%m/%d/%Y")

        if self._search_token:
            params["__RequestVerificationToken"] = self._search_token

        search_url = f"{self.SEARCH_URL}/pin"
        all_documents = []
        page = 1
        has_more = True

        while has_more and len(all_documents) < max_results:
            params["page"] = page
            params["pageSize"] = min(50, max_results - len(all_documents))

            try:
                status, html = await self._fetch(search_url, method="POST", data=params)

                if status != 200:
                    logger.warning(f"PIN search returned HTTP {status}")
                    break

                documents = self._parse_search_results(html)

                if not documents:
                    has_more = False
                else:
                    if document_types:
                        documents = [
                            d for d in documents if d.document_type in document_types
                        ]

                    all_documents.extend(documents)
                    page += 1

                    if len(documents) < params["pageSize"]:
                        has_more = False

            except Exception as e:
                logger.error(f"Error during PIN search: {e}")
                break

        elapsed_ms = int((time.time() - start_time) * 1000)

        return SearchResult(
            documents=all_documents[:max_results],
            total_count=len(all_documents),
            page_number=1,
            page_size=max_results,
            has_more=len(all_documents) > max_results,
            search_criteria=SearchCriteria(
                parcel_number=pin,
                start_date=start_date,
                end_date=end_date,
                document_types=document_types or [],
            ),
            search_time_ms=elapsed_ms,
            source_system=self.SYSTEM_NAME,
        )

    async def search_by_address(
        self,
        address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """
        Search Cook County records by property address.

        Note: Cook County's address search is limited. For best results,
        first look up the PIN using the Cook County Assessor's website
        and then search by PIN.

        Args:
            address: Street address
            city: City name (Chicago, etc.)
            zip_code: ZIP code
            start_date: Start of recording date range
            end_date: End of recording date range
            max_results: Maximum results to return

        Returns:
            SearchResult with matching documents
        """
        import time

        start_time = time.time()

        if not self._search_token:
            await self._initialize_session()

        params = {
            "searchType": "address",
            "streetAddress": address,
        }

        if city:
            params["city"] = city

        if zip_code:
            params["zipCode"] = zip_code

        if start_date:
            params["startDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            params["endDate"] = end_date.strftime("%m/%d/%Y")

        if self._search_token:
            params["__RequestVerificationToken"] = self._search_token

        search_url = f"{self.SEARCH_URL}/address"

        try:
            status, html = await self._fetch(search_url, method="POST", data=params)

            if status != 200:
                logger.warning(f"Address search returned HTTP {status}")
                return SearchResult(
                    documents=[],
                    total_count=0,
                    page_number=1,
                    page_size=max_results,
                    has_more=False,
                    search_criteria=SearchCriteria(property_address=address),
                    search_time_ms=int((time.time() - start_time) * 1000),
                    source_system=self.SYSTEM_NAME,
                    warnings=[f"Search returned HTTP {status}"],
                )

            documents = self._parse_search_results(html)

            elapsed_ms = int((time.time() - start_time) * 1000)

            return SearchResult(
                documents=documents[:max_results],
                total_count=len(documents),
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(
                    property_address=address, start_date=start_date, end_date=end_date
                ),
                search_time_ms=elapsed_ms,
                source_system=self.SYSTEM_NAME,
                warnings=[
                    "Address search has limited functionality. Consider using PIN search for more complete results."
                ],
            )

        except Exception as e:
            logger.error(f"Error during address search: {e}")
            return SearchResult(
                documents=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(property_address=address),
                search_time_ms=int((time.time() - start_time) * 1000),
                source_system=self.SYSTEM_NAME,
                warnings=[str(e)],
            )

    async def get_document_detail(
        self, document_number: str
    ) -> Optional[RecordedDocument]:
        """
        Get detailed information for a specific document.

        Args:
            document_number: The document/instrument number

        Returns:
            RecordedDocument with full details, or None if not found
        """
        detail_url = f"{self.BASE_URL}/document/detail/{document_number}"

        try:
            status, html = await self._fetch(detail_url)

            if status != 200:
                logger.warning(f"Document detail returned HTTP {status}")
                return None

            soup = self._parse_html(html)

            # Parse document detail page
            doc = RecordedDocument(
                document_number=document_number,
                county=self.COUNTY_NAME,
                state=self.STATE_ABBREV,
                fips_code=self.FIPS_CODE,
                source_url=detail_url,
            )

            # Find document info sections
            info_table = soup.find("table", {"class": "document-info"}) or soup.find(
                "dl", {"class": "document-details"}
            )

            if info_table:
                doc = self._parse_document_detail_table(info_table, doc)

            # Parse parties section
            parties_section = soup.find("div", {"class": "parties"}) or soup.find(
                "table", {"class": "parties"}
            )
            if parties_section:
                doc.parties = self._parse_parties_section(parties_section)
                doc.grantors = doc.get_grantors()
                doc.grantees = doc.get_grantees()

            # Parse legal descriptions
            legal_section = soup.find(
                "div", {"class": "legal-description"}
            ) or soup.find("table", {"class": "legal"})
            if legal_section:
                doc.legal_descriptions = self._parse_legal_section(legal_section)
                doc.parcels = [
                    ld.parcel_number
                    for ld in doc.legal_descriptions
                    if ld.parcel_number
                ]

            # Check for image availability
            image_link = soup.find("a", {"class": "view-image"}) or soup.find(
                "a", text=re.compile(r"view.*image", re.I)
            )
            if image_link:
                doc.image_available = True
                doc.image_url = urljoin(self.BASE_URL, image_link.get("href", ""))

            # Parse page count if available
            page_info = soup.find(text=re.compile(r"pages?:", re.I))
            if page_info:
                match = re.search(r"(\d+)\s*pages?", page_info, re.I)
                if match:
                    doc.page_count = int(match.group(1))

            return doc

        except Exception as e:
            logger.error(f"Error getting document detail: {e}")
            return None

    def _parse_document_detail_table(
        self, table, doc: RecordedDocument
    ) -> RecordedDocument:
        """Parse the document info table/list on the detail page."""
        try:
            # Handle both table and definition list formats
            if table.name == "dl":
                items = zip(table.find_all("dt"), table.find_all("dd"))
                for dt, dd in items:
                    label = dt.get_text(strip=True).lower().rstrip(":")
                    value = dd.get_text(strip=True)
                    doc = self._apply_detail_field(doc, label, value)
            else:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["th", "td"])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower().rstrip(":")
                        value = cells[1].get_text(strip=True)
                        doc = self._apply_detail_field(doc, label, value)

        except Exception as e:
            logger.warning(f"Error parsing document detail table: {e}")

        return doc

    def _apply_detail_field(
        self, doc: RecordedDocument, label: str, value: str
    ) -> RecordedDocument:
        """Apply a parsed field to the document."""
        label = label.lower()

        if "document" in label and "number" in label:
            doc.document_number = value
        elif "instrument" in label:
            doc.instrument_number = value
        elif "type" in label:
            doc.document_type_raw = value
            doc.document_type = self._parse_cook_county_document_type(value)
        elif "recorded" in label or "recording date" in label:
            doc.recorded_date = self._parse_date(value)
        elif "execution" in label or "executed" in label:
            doc.execution_date = self._parse_date(value)
        elif "consideration" in label or "amount" in label:
            doc.consideration = self._parse_amount(value)
        elif "book" in label:
            doc.book = value
        elif "page" in label:
            doc.page = value
        elif "transfer tax" in label:
            doc.transfer_tax = self._parse_amount(value)

        return doc

    def _parse_parties_section(self, section) -> List[DocumentParty]:
        """Parse the parties section of the detail page."""
        parties = []

        try:
            # Look for grantor section
            grantor_section = section.find(text=re.compile(r"grantor", re.I))
            if grantor_section:
                parent = grantor_section.find_parent(["tr", "div", "li"])
                if parent:
                    names_text = parent.get_text()
                    # Extract names after "Grantor:" label
                    names_part = re.sub(
                        r".*grantor[s]?:?\s*", "", names_text, flags=re.I
                    )
                    for name in re.split(r"[;,]", names_part):
                        name = name.strip()
                        if name:
                            parties.append(
                                DocumentParty(
                                    name=self._normalize_name(name),
                                    role=PartyRole.GRANTOR,
                                    raw_name=name,
                                )
                            )

            # Look for grantee section
            grantee_section = section.find(text=re.compile(r"grantee", re.I))
            if grantee_section:
                parent = grantee_section.find_parent(["tr", "div", "li"])
                if parent:
                    names_text = parent.get_text()
                    names_part = re.sub(
                        r".*grantee[s]?:?\s*", "", names_text, flags=re.I
                    )
                    for name in re.split(r"[;,]", names_part):
                        name = name.strip()
                        if name:
                            parties.append(
                                DocumentParty(
                                    name=self._normalize_name(name),
                                    role=PartyRole.GRANTEE,
                                    raw_name=name,
                                )
                            )

        except Exception as e:
            logger.warning(f"Error parsing parties section: {e}")

        return parties

    def _parse_legal_section(self, section) -> List[LegalDescription]:
        """Parse the legal description section of the detail page."""
        legal_descriptions = []

        try:
            # Find PIN numbers
            pin_matches = re.findall(
                r"\d{2}-\d{2}-\d{3}-\d{3}-\d{4}", section.get_text()
            )
            for pin in pin_matches:
                legal_descriptions.append(
                    LegalDescription(
                        full_description=f"PIN: {pin}", parcel_number=pin, apn=pin
                    )
                )

            # Look for subdivision/lot/block info
            text = section.get_text()
            lot_match = re.search(r"lot\s+(\d+)", text, re.I)
            block_match = re.search(r"block\s+(\d+)", text, re.I)
            subdivision_match = re.search(r"subdivision[:\s]+([^,\n]+)", text, re.I)

            if lot_match or block_match or subdivision_match:
                # If we have lot/block info, add it to existing or create new
                if legal_descriptions:
                    ld = legal_descriptions[0]
                    if lot_match:
                        ld.lot = lot_match.group(1)
                    if block_match:
                        ld.block = block_match.group(1)
                    if subdivision_match:
                        ld.subdivision = subdivision_match.group(1).strip()
                else:
                    legal_descriptions.append(
                        LegalDescription(
                            full_description=text.strip(),
                            lot=lot_match.group(1) if lot_match else None,
                            block=block_match.group(1) if block_match else None,
                            subdivision=(
                                subdivision_match.group(1).strip()
                                if subdivision_match
                                else None
                            ),
                        )
                    )

        except Exception as e:
            logger.warning(f"Error parsing legal section: {e}")

        return legal_descriptions

    async def search_by_book_page(
        self, book: str, page: str
    ) -> Optional[RecordedDocument]:
        """
        Search for a document by book and page number.

        This is primarily useful for older documents recorded before
        the electronic document numbering system.

        Args:
            book: Book number
            page: Page number

        Returns:
            RecordedDocument if found, None otherwise
        """
        if not self._search_token:
            await self._initialize_session()

        params = {
            "searchType": "bookpage",
            "book": book,
            "page": page,
        }

        if self._search_token:
            params["__RequestVerificationToken"] = self._search_token

        search_url = f"{self.SEARCH_URL}/bookpage"

        try:
            status, html = await self._fetch(search_url, method="POST", data=params)

            if status != 200:
                return None

            documents = self._parse_search_results(html)
            if documents:
                return await self.get_document_detail(documents[0].document_number)

            return None

        except Exception as e:
            logger.error(f"Error during book/page search: {e}")
            return None


# Convenience functions for synchronous usage


def search_cook_county_by_name(
    last_name: str, first_name: Optional[str] = None, **kwargs
) -> SearchResult:
    """Search Cook County records by name (synchronous)."""

    async def _search():
        async with CookCountyRecorder() as recorder:
            return await recorder.search_by_name(last_name, first_name, **kwargs)

    return asyncio.run(_search())


def search_cook_county_by_pin(pin: str, **kwargs) -> SearchResult:
    """Search Cook County records by PIN (synchronous)."""

    async def _search():
        async with CookCountyRecorder() as recorder:
            return await recorder.search_by_parcel(pin, **kwargs)

    return asyncio.run(_search())


def get_cook_county_document(document_number: str) -> Optional[RecordedDocument]:
    """Get a Cook County document by number (synchronous)."""

    async def _get():
        async with CookCountyRecorder() as recorder:
            return await recorder.get_document_detail(document_number)

    return asyncio.run(_get())
