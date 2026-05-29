"""
Miami-Dade County, Florida Clerk of Courts - Official Records Scraper

Miami-Dade County is the most populous county in Florida and seventh most
populous in the United States (2.7M+), containing Miami and surrounding cities.

System: Miami-Dade County Clerk of Courts - Official Records
URL: https://www.miami-dadeclerk.com/
FIPS: 12086

Available searches:
- Name search (grantor/grantee)
- Document/CFN (Clerk's File Number) search
- Folio number search (Florida's property identifier)
- Book/Page search
- Date range search

Note: Florida uses traditional "Mortgage" terminology (not Deed of Trust).
Miami-Dade provides online access to official records.
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


class MiamiDadeCountyRecorder(CountyRecorderBase):
    """
    Scraper for Miami-Dade County, Florida Clerk of Courts - Official Records.

    Miami-Dade County provides online search access to official records
    through their Clerk of Courts system. Records are indexed by CFN
    (Clerk's File Number) and Folio number (property identifier).
    """

    COUNTY_NAME = "Miami-Dade County"
    STATE = "Florida"
    STATE_ABBREV = "FL"
    FIPS_CODE = "12086"

    BASE_URL = "https://www.miami-dadeclerk.com/"
    SEARCH_URL = "https://onlineservices.miami-dadeclerk.com/officialrecords/"
    SYSTEM_NAME = "Miami-Dade Clerk Official Records"

    REQUEST_DELAY = 2.0
    MAX_RETRIES = 3
    TIMEOUT = 45

    REQUIRES_LOGIN = False
    REQUIRES_CAPTCHA = False

    # Florida Folio number format varies by county
    # Miami-Dade format: XX-XXXX-XXX-XXXX (13 digits with dashes)
    FOLIO_PATTERN = re.compile(r"^\d{2}-\d{4}-\d{3}-\d{4}$")

    # Florida/Miami-Dade specific document types
    MIAMI_DADE_DOC_TYPES = {
        # Deeds
        "WD": DocumentType.WARRANTY_DEED,
        "WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "GENERAL WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "STATUTORY WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "SWD": DocumentType.SPECIAL_WARRANTY_DEED,
        "SPECIAL WARRANTY DEED": DocumentType.SPECIAL_WARRANTY_DEED,
        "QCD": DocumentType.QUITCLAIM_DEED,
        "QUITCLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "QUIT CLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "TD": DocumentType.TRUSTEES_DEED,
        "TRUSTEE'S DEED": DocumentType.TRUSTEES_DEED,
        "TRUSTEES DEED": DocumentType.TRUSTEES_DEED,
        "PR DEED": DocumentType.TRUSTEES_DEED,  # Personal Representative Deed
        "PERSONAL REPRESENTATIVE DEED": DocumentType.TRUSTEES_DEED,
        "TAX DEED": DocumentType.TAX_DEED,
        "DEED": DocumentType.WARRANTY_DEED,
        "CORRECTION DEED": DocumentType.CORRECTION_DEED,
        "LADYBIRD DEED": DocumentType.GRANT_DEED,  # Florida enhanced life estate deed
        "ENHANCED LIFE ESTATE DEED": DocumentType.GRANT_DEED,
        # Mortgages (Florida uses traditional mortgage, not DOT)
        "MTG": DocumentType.MORTGAGE,
        "MORTGAGE": DocumentType.MORTGAGE,
        "FIRST MORTGAGE": DocumentType.MORTGAGE,
        "SECOND MORTGAGE": DocumentType.MORTGAGE,
        "HOME EQUITY MORTGAGE": DocumentType.MORTGAGE,
        "CONSTRUCTION MORTGAGE": DocumentType.MORTGAGE,
        "SAT": DocumentType.MORTGAGE_RELEASE,
        "SATISFACTION": DocumentType.MORTGAGE_RELEASE,
        "SATISFACTION OF MORTGAGE": DocumentType.MORTGAGE_RELEASE,
        "PARTIAL SAT": DocumentType.MORTGAGE_RELEASE,
        "PARTIAL SATISFACTION": DocumentType.MORTGAGE_RELEASE,
        "CANCELLATION": DocumentType.MORTGAGE_RELEASE,
        "ASGN": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT OF MORTGAGE": DocumentType.MORTGAGE_ASSIGNMENT,
        "CORP ASGN": DocumentType.MORTGAGE_ASSIGNMENT,
        "CORPORATE ASSIGNMENT": DocumentType.MORTGAGE_ASSIGNMENT,
        "MOD": DocumentType.MORTGAGE_MODIFICATION,
        "MODIFICATION": DocumentType.MORTGAGE_MODIFICATION,
        "LOAN MODIFICATION": DocumentType.MORTGAGE_MODIFICATION,
        "SUB": DocumentType.SUBORDINATION_AGREEMENT,
        "SUBORDINATION": DocumentType.SUBORDINATION_AGREEMENT,
        "SUBORDINATION AGREEMENT": DocumentType.SUBORDINATION_AGREEMENT,
        # Liens
        "COL": DocumentType.MECHANICS_LIEN,
        "CLAIM OF LIEN": DocumentType.MECHANICS_LIEN,
        "CONSTRUCTION LIEN": DocumentType.MECHANICS_LIEN,
        "MECHANICS LIEN": DocumentType.MECHANICS_LIEN,
        "RELEASE OF LIEN": DocumentType.MECHANICS_LIEN_RELEASE,
        "SATISFACTION OF LIEN": DocumentType.MECHANICS_LIEN_RELEASE,
        "JL": DocumentType.JUDGMENT_LIEN,
        "JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "JUDGMENT LIEN": DocumentType.JUDGMENT_LIEN,
        "FINAL JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "SAT OF JUDGMENT": DocumentType.JUDGMENT_SATISFACTION,
        "SATISFACTION OF JUDGMENT": DocumentType.JUDGMENT_SATISFACTION,
        "FTL": DocumentType.TAX_LIEN_FEDERAL,
        "FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "NOTICE OF FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "STL": DocumentType.TAX_LIEN_STATE,
        "STATE TAX LIEN": DocumentType.TAX_LIEN_STATE,
        "TAX WARRANT": DocumentType.TAX_LIEN_STATE,
        "CERTIFICATE OF RELEASE": DocumentType.TAX_LIEN_RELEASE,
        "HOA LIEN": DocumentType.HOA_LIEN,
        "CLAIM OF LIEN (HOA)": DocumentType.HOA_LIEN,
        "CONDO LIEN": DocumentType.HOA_LIEN,
        # Foreclosure (Florida judicial foreclosure)
        "LP": DocumentType.LIS_PENDENS,
        "LIS PENDENS": DocumentType.LIS_PENDENS,
        "NOTICE OF LIS PENDENS": DocumentType.LIS_PENDENS,
        "NLI": DocumentType.LIS_PENDENS,
        "DISMISSAL": DocumentType.NOTICE,
        "NOTICE OF VOLUNTARY DISMISSAL": DocumentType.NOTICE,
        "CERTIFICATE OF TITLE": DocumentType.TRUSTEES_DEED,  # FL foreclosure deed
        "COT": DocumentType.TRUSTEES_DEED,
        # UCC
        "UCC": DocumentType.UCC_FINANCING,
        "UCC1": DocumentType.UCC_FINANCING,
        "UCC-1": DocumentType.UCC_FINANCING,
        "FINANCING STATEMENT": DocumentType.UCC_FINANCING,
        # Documentary Stamps (Florida specific)
        "DS": DocumentType.OTHER,
        "DOC STAMPS": DocumentType.OTHER,
        # Easements and Restrictions
        "EASE": DocumentType.EASEMENT,
        "EASEMENT": DocumentType.EASEMENT,
        "GRANT OF EASEMENT": DocumentType.EASEMENT,
        "UTILITY EASEMENT": DocumentType.EASEMENT,
        "ACCESS EASEMENT": DocumentType.EASEMENT,
        "DCR": DocumentType.CC_AND_RS,
        "DECLARATION": DocumentType.CC_AND_RS,
        "DECLARATION OF CONDOMINIUM": DocumentType.CC_AND_RS,
        "DECLARATION OF RESTRICTIONS": DocumentType.CC_AND_RS,
        "RESTRICTIONS": DocumentType.RESTRICTIVE_COVENANT,
        "UNITY OF TITLE": DocumentType.AGREEMENT,
        # Other common documents
        "AFF": DocumentType.AFFIDAVIT,
        "AFFIDAVIT": DocumentType.AFFIDAVIT,
        "AFFIDAVIT OF DOMICILE": DocumentType.AFFIDAVIT,
        "DEATH AFFIDAVIT": DocumentType.AFFIDAVIT,
        "AFFIDAVIT OF CONTINUOUS MARRIAGE": DocumentType.AFFIDAVIT,
        "POA": DocumentType.POWER_OF_ATTORNEY,
        "POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,
        "DURABLE POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,
        "REVOCATION": DocumentType.REVOCATION_OF_POA,
        "REVOCATION OF POA": DocumentType.REVOCATION_OF_POA,
        "LEASE": DocumentType.LEASE,
        "MEMORANDUM OF LEASE": DocumentType.MEMORANDUM,
        "OPTION": DocumentType.OPTION_TO_PURCHASE,
        "CONTRACT": DocumentType.AGREEMENT,
        "AGREEMENT": DocumentType.AGREEMENT,
        "NOTICE": DocumentType.NOTICE,
        # Maps and Plats
        "PLAT": DocumentType.PLAT_MAP,
        "SUBDIVISION PLAT": DocumentType.SUBDIVISION_MAP,
        "REPLAT": DocumentType.PLAT_MAP,
        "CONDOMINIUM PLAT": DocumentType.SUBDIVISION_MAP,
        # Marriage
        "MAR": DocumentType.MARRIAGE_LICENSE,
        "MARRIAGE LICENSE": DocumentType.MARRIAGE_LICENSE,
        "MARRIAGE": DocumentType.MARRIAGE_LICENSE,
        # Death certificates (index only)
        "DC": DocumentType.DEATH_CERTIFICATE,
        "DEATH CERTIFICATE": DocumentType.DEATH_CERTIFICATE,
    }

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the Miami-Dade County recorder scraper."""
        super().__init__(session)
        self._viewstate: Optional[str] = None
        self._eventvalidation: Optional[str] = None

    async def _initialize_session(self):
        """Initialize search session and get ASP.NET tokens."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        status, html = await self._fetch(self.SEARCH_URL)
        if status != 200:
            logger.warning(f"Failed to initialize session: HTTP {status}")
            return

        soup = self._parse_html(html)

        # Get ASP.NET form tokens
        viewstate = soup.find("input", {"name": "__VIEWSTATE"})
        if viewstate:
            self._viewstate = viewstate.get("value")

        eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})
        if eventvalidation:
            self._eventvalidation = eventvalidation.get("value")

        logger.debug("Miami-Dade County session initialized")

    def _parse_miami_dade_document_type(self, raw_type: str) -> DocumentType:
        """Parse Miami-Dade County-specific document type strings."""
        if not raw_type:
            return DocumentType.UNKNOWN

        raw_type = raw_type.upper().strip()

        if raw_type in self.MIAMI_DADE_DOC_TYPES:
            return self.MIAMI_DADE_DOC_TYPES[raw_type]

        return self._parse_document_type(raw_type)

    def _parse_folio(self, folio_str: str) -> Optional[str]:
        """Parse and validate a Miami-Dade County Folio number."""
        if not folio_str:
            return None

        # Clean up
        folio_str = folio_str.strip().replace(" ", "")

        # If already in correct format
        if self.FOLIO_PATTERN.match(folio_str):
            return folio_str

        # Try to format from digits (13 digits)
        digits = re.sub(r"[^\d]", "", folio_str)
        if len(digits) == 13:
            return f"{digits[0:2]}-{digits[2:6]}-{digits[6:9]}-{digits[9:13]}"

        logger.warning(f"Invalid Miami-Dade Folio format: {folio_str}")
        return folio_str

    def _parse_cfn(self, cfn_str: str) -> Optional[str]:
        """Parse CFN (Clerk's File Number)."""
        if not cfn_str:
            return None

        # CFN format varies - clean and return
        cfn = re.sub(r"[^\d]", "", cfn_str.strip())
        return cfn if cfn else None

    def _parse_search_results(self, html: str) -> List[RecordedDocument]:
        """Parse search results HTML into RecordedDocument objects."""
        documents = []
        soup = self._parse_html(html)

        # Find results table
        results_table = (
            soup.find("table", {"id": "gvResults"})
            or soup.find("table", {"class": "results"})
            or soup.find("table", {"class": "GridView"})
        )

        if not results_table:
            no_results = soup.find(
                text=re.compile(r"no\s+(results?|records?)\s+found", re.I)
            )
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
            # Miami-Dade typical layout:
            # CFN | Book/Page | Doc Type | Rec Date | Grantor | Grantee | Folio | Consideration

            cfn = cells[0].get_text(strip=True) if len(cells) > 0 else None
            if not cfn:
                return None

            book_page = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            doc_type_raw = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            rec_date_str = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            grantor_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            grantee_text = cells[5].get_text(strip=True) if len(cells) > 5 else ""
            folio_text = cells[6].get_text(strip=True) if len(cells) > 6 else ""
            consideration_text = cells[7].get_text(strip=True) if len(cells) > 7 else ""

            # Get detail link
            doc_link = cells[0].find("a")
            source_url = None
            if doc_link and doc_link.get("href"):
                source_url = urljoin(self.BASE_URL, doc_link.get("href"))

            # Parse book/page
            book = None
            page = None
            if book_page:
                match = re.match(r"(\d+)\s*/\s*(\d+)", book_page)
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
                    parties.append(
                        DocumentParty(
                            name=self._normalize_name(name),
                            role=PartyRole.GRANTOR,
                            raw_name=name,
                        )
                    )

            for name in self._split_party_names(grantee_text):
                if name:
                    grantees.append(self._normalize_name(name))
                    parties.append(
                        DocumentParty(
                            name=self._normalize_name(name),
                            role=PartyRole.GRANTEE,
                            raw_name=name,
                        )
                    )

            # Parse folio
            legal_descriptions = []
            parcels = []
            if folio_text:
                for folio_part in re.split(r"[,;]", folio_text):
                    folio = self._parse_folio(folio_part.strip())
                    if folio:
                        parcels.append(folio)
                        legal_descriptions.append(
                            LegalDescription(
                                full_description=f"Folio: {folio}",
                                parcel_number=folio,
                                apn=folio,
                            )
                        )

            return RecordedDocument(
                document_number=cfn,
                instrument_number=cfn,
                book=book,
                page=page,
                document_type=self._parse_miami_dade_document_type(doc_type_raw),
                document_type_raw=doc_type_raw,
                recorded_date=self._parse_date(rec_date_str),
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
                    "cfn": cfn,
                    "book_page": book_page,
                    "doc_type_raw": doc_type_raw,
                    "grantor_raw": grantor_text,
                    "grantee_raw": grantee_text,
                    "folio_raw": folio_text,
                },
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
            # Skip common suffixes that aren't names
            if part and part.upper() not in [
                "ET AL",
                "ETAL",
                "ET UX",
                "ETUX",
                "ET VIR",
            ]:
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
        max_results: int = 100,
    ) -> SearchResult:
        """
        Search Miami-Dade County records by party name.

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

        if not self._viewstate:
            await self._initialize_session()

        # Build form data
        form_data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
            "txtLastName": last_name,
            "btnSearch": "Search",
        }

        if first_name:
            form_data["txtFirstName"] = first_name

        if party_type.lower() == "grantor":
            form_data["ddlPartyType"] = "G"
        elif party_type.lower() == "grantee":
            form_data["ddlPartyType"] = "E"
        else:
            form_data["ddlPartyType"] = "A"  # All

        if start_date:
            form_data["txtFromDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            form_data["txtToDate"] = end_date.strftime("%m/%d/%Y")

        # Execute search
        search_url = f"{self.SEARCH_URL}Search.aspx"
        all_documents = []

        try:
            status, html = await self._fetch(search_url, method="POST", data=form_data)

            if status != 200:
                logger.warning(f"Name search returned HTTP {status}")
            else:
                documents = self._parse_search_results(html)

                if document_types:
                    documents = [
                        d for d in documents if d.document_type in document_types
                    ]

                all_documents.extend(documents)

                # Update viewstate for pagination
                soup = self._parse_html(html)
                new_viewstate = soup.find("input", {"name": "__VIEWSTATE"})
                if new_viewstate:
                    self._viewstate = new_viewstate.get("value")

                # Handle pagination
                page = 2
                while len(all_documents) < max_results:
                    next_link = soup.find("a", text=str(page))
                    if not next_link:
                        break

                    form_data["__VIEWSTATE"] = self._viewstate or ""
                    form_data["__EVENTTARGET"] = f"gvResults$ctl01$ctl{page:02d}"

                    status, html = await self._fetch(
                        search_url, method="POST", data=form_data
                    )

                    if status != 200:
                        break

                    documents = self._parse_search_results(html)
                    if not documents:
                        break

                    if document_types:
                        documents = [
                            d for d in documents if d.document_type in document_types
                        ]

                    all_documents.extend(documents)

                    soup = self._parse_html(html)
                    new_viewstate = soup.find("input", {"name": "__VIEWSTATE"})
                    if new_viewstate:
                        self._viewstate = new_viewstate.get("value")

                    page += 1

        except Exception as e:
            logger.error(f"Error during name search: {e}")

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
        Search for a specific document by CFN (Clerk's File Number).

        Args:
            document_number: The CFN

        Returns:
            RecordedDocument if found, None otherwise
        """
        if not self._viewstate:
            await self._initialize_session()

        cfn = self._parse_cfn(document_number)

        form_data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
            "txtCFN": cfn,
            "btnCFNSearch": "Search",
        }

        search_url = f"{self.SEARCH_URL}Search.aspx"

        try:
            status, html = await self._fetch(search_url, method="POST", data=form_data)

            if status != 200:
                logger.warning(f"CFN search returned HTTP {status}")
                return None

            documents = self._parse_search_results(html)

            if documents:
                return await self.get_document_detail(documents[0].document_number)

            return None

        except Exception as e:
            logger.error(f"Error during CFN search: {e}")
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
        Search Miami-Dade County records by Folio number.

        Args:
            parcel_number: The Folio number in format XX-XXXX-XXX-XXXX
            start_date: Start of recording date range
            end_date: End of recording date range
            document_types: Filter by document types
            max_results: Maximum results to return

        Returns:
            SearchResult with matching documents
        """
        import time

        start_time = time.time()

        if not self._viewstate:
            await self._initialize_session()

        # Parse and validate Folio
        folio = self._parse_folio(parcel_number)
        if not folio:
            return SearchResult(
                documents=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(parcel_number=parcel_number),
                search_time_ms=0,
                source_system=self.SYSTEM_NAME,
                warnings=["Invalid Folio format. Use XX-XXXX-XXX-XXXX format."],
            )

        form_data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
            "txtFolio": folio.replace("-", ""),
            "btnFolioSearch": "Search",
        }

        if start_date:
            form_data["txtFromDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            form_data["txtToDate"] = end_date.strftime("%m/%d/%Y")

        search_url = f"{self.SEARCH_URL}Search.aspx"
        all_documents = []

        try:
            status, html = await self._fetch(search_url, method="POST", data=form_data)

            if status != 200:
                logger.warning(f"Folio search returned HTTP {status}")
            else:
                documents = self._parse_search_results(html)

                if document_types:
                    documents = [
                        d for d in documents if d.document_type in document_types
                    ]

                all_documents.extend(documents)

        except Exception as e:
            logger.error(f"Error during Folio search: {e}")

        elapsed_ms = int((time.time() - start_time) * 1000)

        return SearchResult(
            documents=all_documents[:max_results],
            total_count=len(all_documents),
            page_number=1,
            page_size=max_results,
            has_more=len(all_documents) > max_results,
            search_criteria=SearchCriteria(
                parcel_number=folio,
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
        Search Miami-Dade County records by property address.

        Note: Miami-Dade Clerk doesn't directly support address search.
        For address-based searches, first look up the Folio number at
        the Miami-Dade Property Appraiser (miamidade.gov/pa), then
        search by Folio.

        Args:
            address: Street address
            city: City name (Miami, Hialeah, etc.)
            zip_code: ZIP code
            start_date: Start of recording date range
            end_date: End of recording date range
            max_results: Maximum results to return

        Returns:
            SearchResult with matching documents
        """
        # Miami-Dade doesn't support direct address search
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
                "Miami-Dade Clerk doesn't support direct address search.",
                "Look up Folio number at miamidade.gov/pa then search by Folio.",
                "Alternatively, search by owner name.",
            ],
        )

    async def search_by_book_page(
        self, book: str, page: str
    ) -> Optional[RecordedDocument]:
        """
        Search for a document by book and page number.

        Args:
            book: Book (Official Record Book) number
            page: Page number

        Returns:
            RecordedDocument if found, None otherwise
        """
        if not self._viewstate:
            await self._initialize_session()

        form_data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
            "txtBook": book.strip(),
            "txtPage": page.strip(),
            "btnBookPageSearch": "Search",
        }

        search_url = f"{self.SEARCH_URL}Search.aspx"

        try:
            status, html = await self._fetch(search_url, method="POST", data=form_data)

            if status != 200:
                return None

            documents = self._parse_search_results(html)
            if documents:
                return await self.get_document_detail(documents[0].document_number)

            return None

        except Exception as e:
            logger.error(f"Error during book/page search: {e}")
            return None

    async def get_document_detail(
        self, document_number: str
    ) -> Optional[RecordedDocument]:
        """
        Get detailed information for a specific document.

        Args:
            document_number: The CFN (Clerk's File Number)

        Returns:
            RecordedDocument with full details, or None if not found
        """
        cfn = self._parse_cfn(document_number)
        detail_url = f"{self.SEARCH_URL}DocDetail.aspx?CFN={cfn}"

        try:
            status, html = await self._fetch(detail_url)

            if status != 200:
                logger.warning(f"Document detail returned HTTP {status}")
                return None

            soup = self._parse_html(html)

            doc = RecordedDocument(
                document_number=cfn,
                instrument_number=cfn,
                county=self.COUNTY_NAME,
                state=self.STATE_ABBREV,
                fips_code=self.FIPS_CODE,
                source_url=detail_url,
            )

            # Parse document details
            doc = self._parse_detail_page(soup, doc)

            return doc

        except Exception as e:
            logger.error(f"Error getting document detail: {e}")
            return None

    def _parse_detail_page(
        self, soup: BeautifulSoup, doc: RecordedDocument
    ) -> RecordedDocument:
        """Parse the document detail page."""
        # Find detail container
        detail_div = soup.find("div", {"class": "detail"}) or soup.find(
            "div", {"id": "docDetail"}
        )
        if not detail_div:
            detail_div = soup

        # Parse table rows
        for row in detail_div.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower().rstrip(":")
                value = cells[1].get_text(strip=True)
                doc = self._apply_detail_field(doc, label, value)

        # Parse labeled spans
        for label_elem in detail_div.find_all(
            ["span", "label"], class_=re.compile(r"label|field")
        ):
            label = label_elem.get_text(strip=True).lower().rstrip(":")
            value_elem = label_elem.find_next_sibling()
            if value_elem:
                value = value_elem.get_text(strip=True)
                doc = self._apply_detail_field(doc, label, value)

        # Parse parties
        parties_section = soup.find("div", {"id": "parties"}) or soup.find(
            "table", {"class": "parties"}
        )
        if parties_section:
            doc.parties = self._parse_parties(parties_section)
            doc.grantors = doc.get_grantors()
            doc.grantees = doc.get_grantees()

        # Parse Folio numbers
        folio_section = soup.find("div", {"class": "folio"}) or soup.find(
            text=re.compile(r"folio", re.I)
        )
        if folio_section:
            text = (
                folio_section.get_text()
                if hasattr(folio_section, "get_text")
                else str(folio_section)
            )
            folio_matches = re.findall(r"\d{2}-\d{4}-\d{3}-\d{4}", text)
            for folio in folio_matches:
                doc.parcels.append(folio)
                doc.legal_descriptions.append(
                    LegalDescription(
                        full_description=f"Folio: {folio}",
                        parcel_number=folio,
                        apn=folio,
                    )
                )

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

    def _apply_detail_field(
        self, doc: RecordedDocument, label: str, value: str
    ) -> RecordedDocument:
        """Apply a parsed detail field to the document."""
        label = label.lower()

        if "cfn" in label or "clerk" in label and "number" in label:
            if not doc.document_number:
                doc.document_number = value
        elif "book" in label or "orb" in label:
            doc.book = value
        elif "page" in label and "count" not in label:
            doc.page = value
        elif "type" in label:
            doc.document_type_raw = value
            doc.document_type = self._parse_miami_dade_document_type(value)
        elif "recorded" in label or "filed" in label:
            doc.recorded_date = self._parse_date(value)
        elif "consideration" in label or "amount" in label:
            doc.consideration = self._parse_amount(value)
        elif "doc stamp" in label or "documentary" in label:
            doc.documentary_stamps = self._parse_amount(value)

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
                    parties.append(
                        DocumentParty(
                            name=self._normalize_name(name),
                            role=PartyRole.GRANTOR,
                            raw_name=name,
                        )
                    )

        # Look for grantee entries
        for elem in section.find_all(text=re.compile(r"grantee", re.I)):
            parent = elem.find_parent(["tr", "div"])
            if parent:
                text = parent.get_text()
                text = re.sub(r"grantee[s]?:?\s*", "", text, flags=re.I)
                for name in self._split_party_names(text):
                    parties.append(
                        DocumentParty(
                            name=self._normalize_name(name),
                            role=PartyRole.GRANTEE,
                            raw_name=name,
                        )
                    )

        return parties


# Convenience functions for synchronous usage


def search_miami_dade_by_name(
    last_name: str, first_name: Optional[str] = None, **kwargs
) -> SearchResult:
    """Search Miami-Dade County records by name (synchronous)."""

    async def _search():
        async with MiamiDadeCountyRecorder() as recorder:
            return await recorder.search_by_name(last_name, first_name, **kwargs)

    return asyncio.run(_search())


def search_miami_dade_by_folio(folio: str, **kwargs) -> SearchResult:
    """Search Miami-Dade County records by Folio (synchronous)."""

    async def _search():
        async with MiamiDadeCountyRecorder() as recorder:
            return await recorder.search_by_parcel(folio, **kwargs)

    return asyncio.run(_search())


def get_miami_dade_document(cfn: str) -> Optional[RecordedDocument]:
    """Get a Miami-Dade County document by CFN (synchronous)."""

    async def _get():
        async with MiamiDadeCountyRecorder() as recorder:
            return await recorder.get_document_detail(cfn)

    return asyncio.run(_get())
