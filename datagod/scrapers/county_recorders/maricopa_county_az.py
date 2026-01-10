"""
Maricopa County, Arizona Recorder Scraper

Maricopa County is the most populous county in Arizona and fourth most
populous in the United States (4.4M+), containing Phoenix and surrounding
cities.

System: Maricopa County Recorder's Office
URL: https://recorder.maricopa.gov/
FIPS: 04013

Available searches:
- Name search (grantor/grantee)
- Document number search
- APN (Assessor's Parcel Number) search
- Book/Page search (Docket/Page)
- Recording date search

Note: Arizona uses "Deed of Trust" similar to California.
Maricopa County provides excellent online access to recorded documents.
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
    DocumentType,
    DocumentStatus,
    PartyRole,
    RecordedDocument,
    DocumentParty,
    LegalDescription,
    SearchCriteria,
    SearchResult,
)

logger = logging.getLogger(__name__)


class MaricopaCountyRecorder(CountyRecorderBase):
    """
    Scraper for Maricopa County, Arizona Recorder's Office.

    Maricopa County provides a robust online search system for recorded
    documents. The system provides access to documents recorded from
    1871 to present, with images available for more recent documents.
    """

    COUNTY_NAME = "Maricopa County"
    STATE = "Arizona"
    STATE_ABBREV = "AZ"
    FIPS_CODE = "04013"

    BASE_URL = "https://recorder.maricopa.gov/"
    SEARCH_URL = "https://recorder.maricopa.gov/recdocdata/"
    API_URL = "https://recorder.maricopa.gov/api/"
    SYSTEM_NAME = "Maricopa County Recorder Online"

    REQUEST_DELAY = 1.5
    MAX_RETRIES = 3
    TIMEOUT = 45

    REQUIRES_LOGIN = False
    REQUIRES_CAPTCHA = False

    # Maricopa County APN format: XXX-XX-XXX or XXX-XX-XXXA (with suffix)
    APN_PATTERN = re.compile(r"^\d{3}-\d{2}-\d{3}[A-Z]?$")

    # Arizona/Maricopa County specific document types
    MARICOPA_DOC_TYPES = {
        # Deeds
        "WD": DocumentType.WARRANTY_DEED,
        "WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "GENERAL WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "SWD": DocumentType.SPECIAL_WARRANTY_DEED,
        "SPECIAL WARRANTY DEED": DocumentType.SPECIAL_WARRANTY_DEED,
        "QCD": DocumentType.QUITCLAIM_DEED,
        "QUITCLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "QUIT CLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "BD": DocumentType.BARGAIN_SALE_DEED,
        "BENEFICIARY DEED": DocumentType.GRANT_DEED,  # Arizona specific
        "BENEF DEED": DocumentType.GRANT_DEED,
        "TD": DocumentType.TRUSTEES_DEED,
        "TRUSTEE'S DEED": DocumentType.TRUSTEES_DEED,
        "TRUSTEES DEED": DocumentType.TRUSTEES_DEED,
        "DEED": DocumentType.WARRANTY_DEED,
        "CORRECTION DEED": DocumentType.CORRECTION_DEED,
        "AFFIDAVIT OF VALUE": DocumentType.AFFIDAVIT,

        # Deeds of Trust (Arizona uses DOT)
        "DOT": DocumentType.DEED_OF_TRUST,
        "DEED OF TRUST": DocumentType.DEED_OF_TRUST,
        "D/T": DocumentType.DEED_OF_TRUST,
        "TRUST DEED": DocumentType.DEED_OF_TRUST,
        "RECON": DocumentType.MORTGAGE_RELEASE,
        "RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "FULL RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "DEED OF RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "PARTIAL RECON": DocumentType.MORTGAGE_RELEASE,
        "SUB": DocumentType.SUBORDINATION_AGREEMENT,
        "SUBORDINATION": DocumentType.SUBORDINATION_AGREEMENT,
        "SUBORDINATION AGREEMENT": DocumentType.SUBORDINATION_AGREEMENT,
        "ASGN": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT OF DOT": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT OF DEED OF TRUST": DocumentType.MORTGAGE_ASSIGNMENT,
        "MOD": DocumentType.MORTGAGE_MODIFICATION,
        "MODIFICATION": DocumentType.MORTGAGE_MODIFICATION,
        "LOAN MODIFICATION": DocumentType.MORTGAGE_MODIFICATION,

        # Liens
        "ML": DocumentType.MECHANICS_LIEN,
        "MECHANIC'S LIEN": DocumentType.MECHANICS_LIEN,
        "MECHANICS LIEN": DocumentType.MECHANICS_LIEN,
        "PRELIMINARY LIEN": DocumentType.MECHANICS_LIEN,
        "RELEASE OF MECHANIC'S LIEN": DocumentType.MECHANICS_LIEN_RELEASE,
        "JL": DocumentType.JUDGMENT_LIEN,
        "JUDGMENT LIEN": DocumentType.JUDGMENT_LIEN,
        "ABSTRACT OF JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "SATISFACTION OF JUDGMENT": DocumentType.JUDGMENT_SATISFACTION,
        "RELEASE OF JUDGMENT": DocumentType.JUDGMENT_SATISFACTION,
        "FTL": DocumentType.TAX_LIEN_FEDERAL,
        "FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "NOTICE OF FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "STL": DocumentType.TAX_LIEN_STATE,
        "STATE TAX LIEN": DocumentType.TAX_LIEN_STATE,
        "RELEASE OF FED TAX LIEN": DocumentType.TAX_LIEN_RELEASE,
        "HOA": DocumentType.HOA_LIEN,
        "HOA LIEN": DocumentType.HOA_LIEN,
        "ASSESSMENT LIEN": DocumentType.HOA_LIEN,
        "LIEN": DocumentType.OTHER,

        # Foreclosure (Arizona non-judicial)
        "NTS": DocumentType.NOTICE_OF_SALE,
        "NOTICE OF TRUSTEE'S SALE": DocumentType.NOTICE_OF_SALE,
        "NOTICE OF SALE": DocumentType.NOTICE_OF_SALE,
        "TRUSTEE SALE": DocumentType.NOTICE_OF_SALE,
        "APPT SUB TRUSTEE": DocumentType.NOTICE,
        "APPOINTMENT OF SUCCESSOR TRUSTEE": DocumentType.NOTICE,
        "SUBSTITUTION OF TRUSTEE": DocumentType.NOTICE,
        "CANCELLATION OF NTS": DocumentType.NOTICE,
        "LP": DocumentType.LIS_PENDENS,
        "LIS PENDENS": DocumentType.LIS_PENDENS,
        "NOTICE OF PENDENCY": DocumentType.LIS_PENDENS,

        # UCC (fixture filings at county level)
        "UCC": DocumentType.UCC_FINANCING,
        "UCC1": DocumentType.UCC_FINANCING,
        "UCC-1": DocumentType.UCC_FINANCING,
        "FINANCING STATEMENT": DocumentType.UCC_FINANCING,
        "UCC TERMINATION": DocumentType.UCC_TERMINATION,

        # Easements and Restrictions
        "EASE": DocumentType.EASEMENT,
        "EASEMENT": DocumentType.EASEMENT,
        "GRANT OF EASEMENT": DocumentType.EASEMENT,
        "UTILITY EASEMENT": DocumentType.EASEMENT,
        "ACCESS EASEMENT": DocumentType.EASEMENT,
        "CCR": DocumentType.CC_AND_RS,
        "CC&R": DocumentType.CC_AND_RS,
        "DECLARATION OF COVENANTS": DocumentType.CC_AND_RS,
        "RESTRICTIONS": DocumentType.RESTRICTIVE_COVENANT,

        # Other common documents
        "AFF": DocumentType.AFFIDAVIT,
        "AFFIDAVIT": DocumentType.AFFIDAVIT,
        "AFFIDAVIT OF DEATH": DocumentType.AFFIDAVIT,
        "AFFIDAVIT OF SUCCESSION": DocumentType.AFFIDAVIT,
        "POA": DocumentType.POWER_OF_ATTORNEY,
        "POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,
        "DURABLE POA": DocumentType.POWER_OF_ATTORNEY,
        "REVOCATION": DocumentType.REVOCATION_OF_POA,
        "LEASE": DocumentType.LEASE,
        "MEMORANDUM OF LEASE": DocumentType.MEMORANDUM,
        "OPTION": DocumentType.OPTION_TO_PURCHASE,
        "AGREEMENT": DocumentType.AGREEMENT,
        "NOTICE": DocumentType.NOTICE,
        "DECLARATION": DocumentType.DECLARATION,

        # Maps and Plats
        "PLAT": DocumentType.PLAT_MAP,
        "FINAL PLAT": DocumentType.PLAT_MAP,
        "SUBDIVISION PLAT": DocumentType.SUBDIVISION_MAP,
        "PARCEL MAP": DocumentType.PARCEL_MAP,
        "CONDOMINIUM PLAT": DocumentType.SUBDIVISION_MAP,
        "CONDO PLAT": DocumentType.SUBDIVISION_MAP,

        # Marriage/Vital
        "MARRIAGE": DocumentType.MARRIAGE_LICENSE,
        "MARRIAGE LICENSE": DocumentType.MARRIAGE_LICENSE,
    }

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the Maricopa County recorder scraper."""
        super().__init__(session)
        self._session_token: Optional[str] = None

    async def _initialize_session(self):
        """Initialize search session."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        # Visit search page to establish session
        status, html = await self._fetch(self.SEARCH_URL)
        if status == 200:
            soup = self._parse_html(html)
            # Look for any session tokens
            token_input = soup.find("input", {"name": re.compile(r"token|csrf", re.I)})
            if token_input:
                self._session_token = token_input.get("value")
            logger.debug("Maricopa County session initialized")

    def _parse_maricopa_document_type(self, raw_type: str) -> DocumentType:
        """Parse Maricopa County-specific document type strings."""
        if not raw_type:
            return DocumentType.UNKNOWN

        raw_type = raw_type.upper().strip()

        if raw_type in self.MARICOPA_DOC_TYPES:
            return self.MARICOPA_DOC_TYPES[raw_type]

        return self._parse_document_type(raw_type)

    def _parse_apn(self, apn_str: str) -> Optional[str]:
        """Parse and validate a Maricopa County APN."""
        if not apn_str:
            return None

        # Clean up the APN
        apn_str = apn_str.strip().upper()

        # If already in correct format
        if self.APN_PATTERN.match(apn_str):
            return apn_str

        # Try to format from digits (8-9 digits)
        digits = re.sub(r"[^\dA-Z]", "", apn_str)
        if len(digits) >= 8:
            # Format as XXX-XX-XXXA
            base = digits[:8]
            suffix = digits[8:] if len(digits) > 8 else ""
            return f"{base[:3]}-{base[3:5]}-{base[5:8]}{suffix}"

        logger.warning(f"Invalid Maricopa County APN format: {apn_str}")
        return apn_str

    def _parse_search_results(self, html: str) -> List[RecordedDocument]:
        """Parse search results HTML into RecordedDocument objects."""
        documents = []
        soup = self._parse_html(html)

        # Find results table
        results_table = soup.find("table", {"id": "results"}) or \
                        soup.find("table", {"class": "results"}) or \
                        soup.find("table", {"class": "searchResults"})

        if not results_table:
            # Check for no results message
            no_results = soup.find(text=re.compile(r"no\s+(results?|records?)\s+found", re.I))
            if no_results:
                logger.debug("No results found")
            return documents

        rows = results_table.find_all("tr")[1:]  # Skip header

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
            # Maricopa County typical layout:
            # Doc Number | Docket/Page | Doc Type | Rec Date | Grantor | Grantee | APN

            doc_number = cells[0].get_text(strip=True) if len(cells) > 0 else None
            if not doc_number:
                return None

            docket_page = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            doc_type_raw = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            rec_date_str = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            grantor_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            grantee_text = cells[5].get_text(strip=True) if len(cells) > 5 else ""
            apn_text = cells[6].get_text(strip=True) if len(cells) > 6 else ""

            # Get detail link
            doc_link = cells[0].find("a")
            source_url = None
            if doc_link and doc_link.get("href"):
                source_url = urljoin(self.BASE_URL, doc_link.get("href"))

            # Parse docket/page (book/page)
            book = None
            page = None
            if docket_page:
                match = re.match(r"(\d+)\s*/\s*(\d+)", docket_page)
                if match:
                    book = match.group(1)
                    page = match.group(2)

            # Parse parties
            parties = []
            grantors = []
            grantees = []

            for name in self._split_party_names(grantor_text):
                if name:
                    grantors.append(self._normalize_name(name))
                    parties.append(DocumentParty(
                        name=self._normalize_name(name),
                        role=PartyRole.GRANTOR,
                        raw_name=name
                    ))

            for name in self._split_party_names(grantee_text):
                if name:
                    grantees.append(self._normalize_name(name))
                    parties.append(DocumentParty(
                        name=self._normalize_name(name),
                        role=PartyRole.GRANTEE,
                        raw_name=name
                    ))

            # Parse APN
            legal_descriptions = []
            parcels = []
            if apn_text:
                # May have multiple APNs separated by commas or semicolons
                for apn_part in re.split(r"[,;]", apn_text):
                    apn = self._parse_apn(apn_part.strip())
                    if apn:
                        parcels.append(apn)
                        legal_descriptions.append(LegalDescription(
                            full_description=f"APN: {apn}",
                            parcel_number=apn,
                            apn=apn
                        ))

            return RecordedDocument(
                document_number=doc_number,
                book=book,
                page=page,
                document_type=self._parse_maricopa_document_type(doc_type_raw),
                document_type_raw=doc_type_raw,
                recorded_date=self._parse_date(rec_date_str),
                parties=parties,
                grantors=grantors,
                grantees=grantees,
                legal_descriptions=legal_descriptions,
                parcels=parcels,
                county=self.COUNTY_NAME,
                state=self.STATE_ABBREV,
                fips_code=self.FIPS_CODE,
                source_url=source_url,
                raw_data={
                    "docket_page": docket_page,
                    "doc_type_raw": doc_type_raw,
                    "grantor_raw": grantor_text,
                    "grantee_raw": grantee_text,
                    "apn_raw": apn_text,
                }
            )

        except Exception as e:
            logger.warning(f"Error parsing result row: {e}")
            return None

    def _split_party_names(self, text: str) -> List[str]:
        """Split party names string into individual names."""
        if not text:
            return []

        names = []
        # Split on common separators
        parts = re.split(r"[;]|\s+AND\s+|\s+&\s+", text, flags=re.I)
        for part in parts:
            part = part.strip()
            if part and part.upper() not in ["ET AL", "ETAL", "ET UX", "ETUX"]:
                names.append(part)

        return names

    async def search_by_name(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        party_type: str = "either",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        document_types: Optional[List[DocumentType]] = None,
        max_results: int = 100
    ) -> SearchResult:
        """
        Search Maricopa County records by party name.

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

        await self._initialize_session()

        # Build search parameters
        params = {
            "lastName": last_name,
        }

        if first_name:
            params["firstName"] = first_name

        if party_type.lower() == "grantor":
            params["partyType"] = "1"  # Grantor only
        elif party_type.lower() == "grantee":
            params["partyType"] = "2"  # Grantee only
        else:
            params["partyType"] = "0"  # Both

        if start_date:
            params["startDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            params["endDate"] = end_date.strftime("%m/%d/%Y")

        # Execute search
        search_url = f"{self.SEARCH_URL}namesearch.aspx"
        all_documents = []
        page = 1
        has_more = True

        while has_more and len(all_documents) < max_results:
            params["page"] = page

            try:
                status, html = await self._fetch(
                    search_url,
                    method="POST",
                    data=params
                )

                if status != 200:
                    logger.warning(f"Name search returned HTTP {status}")
                    break

                documents = self._parse_search_results(html)

                if not documents:
                    has_more = False
                else:
                    if document_types:
                        documents = [d for d in documents if d.document_type in document_types]

                    all_documents.extend(documents)
                    page += 1

                    # Check if fewer results than expected (indicates last page)
                    if len(documents) < 25:  # Typical page size
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
                document_types=document_types or []
            ),
            search_time_ms=elapsed_ms,
            source_system=self.SYSTEM_NAME
        )

    async def search_by_document_number(
        self,
        document_number: str
    ) -> Optional[RecordedDocument]:
        """
        Search for a specific document by its recording number.

        Args:
            document_number: The document number

        Returns:
            RecordedDocument if found, None otherwise
        """
        await self._initialize_session()

        # Clean the document number
        doc_num = document_number.strip()

        params = {
            "docNumber": doc_num,
        }

        search_url = f"{self.SEARCH_URL}docsearch.aspx"

        try:
            status, html = await self._fetch(
                search_url,
                method="POST",
                data=params
            )

            if status != 200:
                logger.warning(f"Document search returned HTTP {status}")
                return None

            documents = self._parse_search_results(html)

            if documents:
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
        max_results: int = 100
    ) -> SearchResult:
        """
        Search Maricopa County records by APN.

        Args:
            parcel_number: The APN in format XXX-XX-XXX
            start_date: Start of recording date range
            end_date: End of recording date range
            document_types: Filter by document types
            max_results: Maximum results to return

        Returns:
            SearchResult with matching documents
        """
        import time
        start_time = time.time()

        await self._initialize_session()

        # Parse and validate APN
        apn = self._parse_apn(parcel_number)
        if not apn:
            return SearchResult(
                documents=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(parcel_number=parcel_number),
                search_time_ms=0,
                source_system=self.SYSTEM_NAME,
                warnings=["Invalid APN format. Use XXX-XX-XXX format."]
            )

        params = {
            "apn": apn.replace("-", ""),  # System may want no dashes
        }

        if start_date:
            params["startDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            params["endDate"] = end_date.strftime("%m/%d/%Y")

        search_url = f"{self.SEARCH_URL}apnsearch.aspx"
        all_documents = []
        page = 1
        has_more = True

        while has_more and len(all_documents) < max_results:
            params["page"] = page

            try:
                status, html = await self._fetch(
                    search_url,
                    method="POST",
                    data=params
                )

                if status != 200:
                    logger.warning(f"APN search returned HTTP {status}")
                    break

                documents = self._parse_search_results(html)

                if not documents:
                    has_more = False
                else:
                    if document_types:
                        documents = [d for d in documents if d.document_type in document_types]

                    all_documents.extend(documents)
                    page += 1

                    if len(documents) < 25:
                        has_more = False

            except Exception as e:
                logger.error(f"Error during APN search: {e}")
                break

        elapsed_ms = int((time.time() - start_time) * 1000)

        return SearchResult(
            documents=all_documents[:max_results],
            total_count=len(all_documents),
            page_number=1,
            page_size=max_results,
            has_more=len(all_documents) > max_results,
            search_criteria=SearchCriteria(
                parcel_number=apn,
                start_date=start_date,
                end_date=end_date,
                document_types=document_types or []
            ),
            search_time_ms=elapsed_ms,
            source_system=self.SYSTEM_NAME
        )

    async def search_by_address(
        self,
        address: str,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """
        Search Maricopa County records by property address.

        Note: Maricopa County Recorder doesn't directly support address search.
        For address-based searches, first look up the APN at the Maricopa
        County Assessor's website (mcassessor.maricopa.gov), then search by APN.

        Args:
            address: Street address
            city: City name (Phoenix, Scottsdale, etc.)
            zip_code: ZIP code
            start_date: Start of recording date range
            end_date: End of recording date range
            max_results: Maximum results to return

        Returns:
            SearchResult with matching documents
        """
        # Maricopa County doesn't support direct address search
        # Return empty results with helpful message
        return SearchResult(
            documents=[],
            total_count=0,
            page_number=1,
            page_size=max_results,
            has_more=False,
            search_criteria=SearchCriteria(property_address=address),
            search_time_ms=0,
            source_system=self.SYSTEM_NAME,
            warnings=[
                "Maricopa County Recorder doesn't support direct address search.",
                "Look up APN at mcassessor.maricopa.gov then search by APN.",
                "Alternatively, search by owner name."
            ]
        )

    async def search_by_docket_page(
        self,
        docket: str,
        page: str
    ) -> Optional[RecordedDocument]:
        """
        Search for a document by docket and page number.

        Args:
            docket: Docket (book) number
            page: Page number

        Returns:
            RecordedDocument if found, None otherwise
        """
        await self._initialize_session()

        params = {
            "docket": docket.strip(),
            "page": page.strip(),
        }

        search_url = f"{self.SEARCH_URL}docketsearch.aspx"

        try:
            status, html = await self._fetch(
                search_url,
                method="POST",
                data=params
            )

            if status != 200:
                return None

            documents = self._parse_search_results(html)
            if documents:
                return await self.get_document_detail(documents[0].document_number)

            return None

        except Exception as e:
            logger.error(f"Error during docket/page search: {e}")
            return None

    async def get_document_detail(
        self,
        document_number: str
    ) -> Optional[RecordedDocument]:
        """
        Get detailed information for a specific document.

        Args:
            document_number: The document number

        Returns:
            RecordedDocument with full details, or None if not found
        """
        detail_url = f"{self.SEARCH_URL}docdetail.aspx?cn={document_number}"

        try:
            status, html = await self._fetch(detail_url)

            if status != 200:
                logger.warning(f"Document detail returned HTTP {status}")
                return None

            soup = self._parse_html(html)

            doc = RecordedDocument(
                document_number=document_number,
                county=self.COUNTY_NAME,
                state=self.STATE_ABBREV,
                fips_code=self.FIPS_CODE,
                source_url=detail_url
            )

            # Parse document details
            doc = self._parse_detail_page(soup, doc)

            return doc

        except Exception as e:
            logger.error(f"Error getting document detail: {e}")
            return None

    def _parse_detail_page(self, soup: BeautifulSoup, doc: RecordedDocument) -> RecordedDocument:
        """Parse the document detail page."""
        # Find detail table/container
        detail_div = soup.find("div", {"class": "docDetail"}) or soup.find("div", {"id": "detail"})
        if not detail_div:
            detail_div = soup

        # Parse table rows or labeled elements
        for row in detail_div.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower().rstrip(":")
                value = cells[1].get_text(strip=True)
                doc = self._apply_detail_field(doc, label, value)

        # Also check for labeled spans
        for label_elem in detail_div.find_all("span", class_=re.compile(r"label")):
            label = label_elem.get_text(strip=True).lower().rstrip(":")
            value_elem = label_elem.find_next_sibling("span")
            if value_elem:
                value = value_elem.get_text(strip=True)
                doc = self._apply_detail_field(doc, label, value)

        # Parse parties
        parties_table = soup.find("table", {"id": "parties"}) or soup.find("div", {"class": "parties"})
        if parties_table:
            doc.parties = self._parse_parties(parties_table)
            doc.grantors = doc.get_grantors()
            doc.grantees = doc.get_grantees()

        # Parse APNs
        apn_section = soup.find("div", {"class": "apn"}) or soup.find("td", text=re.compile(r"apn|parcel", re.I))
        if apn_section:
            text = apn_section.get_text()
            apn_matches = re.findall(r"\d{3}-\d{2}-\d{3}[A-Z]?", text)
            for apn in apn_matches:
                doc.parcels.append(apn)
                doc.legal_descriptions.append(LegalDescription(
                    full_description=f"APN: {apn}",
                    parcel_number=apn,
                    apn=apn
                ))

        # Check for image
        image_link = soup.find("a", text=re.compile(r"view\s*image|document", re.I))
        if image_link:
            doc.image_available = True
            doc.image_url = urljoin(self.BASE_URL, image_link.get("href", ""))

        # Page count
        page_elem = soup.find(text=re.compile(r"pages?:?\s*\d+", re.I))
        if page_elem:
            match = re.search(r"(\d+)\s*pages?", str(page_elem), re.I)
            if match:
                doc.page_count = int(match.group(1))

        return doc

    def _apply_detail_field(self, doc: RecordedDocument, label: str, value: str) -> RecordedDocument:
        """Apply a parsed detail field to the document."""
        label = label.lower()

        if "document" in label and "number" in label:
            if not doc.document_number:
                doc.document_number = value
        elif "docket" in label or "book" in label:
            doc.book = value
        elif "page" in label and "count" not in label:
            doc.page = value
        elif "type" in label:
            doc.document_type_raw = value
            doc.document_type = self._parse_maricopa_document_type(value)
        elif "recorded" in label or "record date" in label:
            doc.recorded_date = self._parse_date(value)
        elif "consideration" in label or "amount" in label:
            doc.consideration = self._parse_amount(value)
        elif "transfer" in label and "fee" in label:
            doc.transfer_tax = self._parse_amount(value)

        return doc

    def _parse_parties(self, section) -> List[DocumentParty]:
        """Parse parties from the detail page."""
        parties = []

        # Look for grantor entries
        for elem in section.find_all(text=re.compile(r"grantor", re.I)):
            parent = elem.find_parent(["tr", "div"])
            if parent:
                text = parent.get_text()
                text = re.sub(r"grantor[s]?:?\s*", "", text, flags=re.I)
                for name in self._split_party_names(text):
                    parties.append(DocumentParty(
                        name=self._normalize_name(name),
                        role=PartyRole.GRANTOR,
                        raw_name=name
                    ))

        # Look for grantee entries
        for elem in section.find_all(text=re.compile(r"grantee", re.I)):
            parent = elem.find_parent(["tr", "div"])
            if parent:
                text = parent.get_text()
                text = re.sub(r"grantee[s]?:?\s*", "", text, flags=re.I)
                for name in self._split_party_names(text):
                    parties.append(DocumentParty(
                        name=self._normalize_name(name),
                        role=PartyRole.GRANTEE,
                        raw_name=name
                    ))

        return parties


# Convenience functions for synchronous usage

def search_maricopa_county_by_name(
    last_name: str,
    first_name: Optional[str] = None,
    **kwargs
) -> SearchResult:
    """Search Maricopa County records by name (synchronous)."""
    async def _search():
        async with MaricopaCountyRecorder() as recorder:
            return await recorder.search_by_name(last_name, first_name, **kwargs)
    return asyncio.run(_search())


def search_maricopa_county_by_apn(
    apn: str,
    **kwargs
) -> SearchResult:
    """Search Maricopa County records by APN (synchronous)."""
    async def _search():
        async with MaricopaCountyRecorder() as recorder:
            return await recorder.search_by_parcel(apn, **kwargs)
    return asyncio.run(_search())


def get_maricopa_county_document(
    document_number: str
) -> Optional[RecordedDocument]:
    """Get a Maricopa County document by number (synchronous)."""
    async def _get():
        async with MaricopaCountyRecorder() as recorder:
            return await recorder.get_document_detail(document_number)
    return asyncio.run(_get())
