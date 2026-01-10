"""
Harris County, Texas County Clerk - Real Property Records Scraper

Harris County is the most populous county in Texas and third most populous
in the United States (4.7M+), containing the city of Houston.

System: Harris County Clerk Official Public Records Search
URL: https://www.cclerk.hctx.net/
FIPS: 48201

Available searches:
- Name search (grantor/grantee)
- Document number/film code search
- Property ID search
- Legal description search (subdivision, lot, block)
- Date range search

Note: Texas uses "Deed of Trust" and Harris County maintains records
dating back to 1836 (though online access is more limited).
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


class HarrisCountyRecorder(CountyRecorderBase):
    """
    Scraper for Harris County, Texas County Clerk - Real Property Records.

    Harris County uses a web-based system for public record searches.
    The system provides access to recorded documents including deeds,
    deeds of trust (mortgages), liens, and other real property documents.
    """

    COUNTY_NAME = "Harris County"
    STATE = "Texas"
    STATE_ABBREV = "TX"
    FIPS_CODE = "48201"

    BASE_URL = "https://www.cclerk.hctx.net/"
    SEARCH_URL = "https://www.cclerk.hctx.net/applications/websearch/RP.aspx"
    SYSTEM_NAME = "Harris County Clerk Real Property Records"

    REQUEST_DELAY = 2.0
    MAX_RETRIES = 3
    TIMEOUT = 45

    REQUIRES_LOGIN = False
    REQUIRES_CAPTCHA = False

    # Harris County property ID format varies
    # Common formats: XXXXXX-XXX-XXXX or account numbers

    # Texas/Harris County specific document types
    HARRIS_COUNTY_DOC_TYPES = {
        # Deeds
        "GWD": DocumentType.WARRANTY_DEED,
        "GENERAL WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "WD": DocumentType.WARRANTY_DEED,
        "SWD": DocumentType.SPECIAL_WARRANTY_DEED,
        "SPECIAL WARRANTY DEED": DocumentType.SPECIAL_WARRANTY_DEED,
        "QCD": DocumentType.QUITCLAIM_DEED,
        "QUITCLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "QUIT CLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "TD": DocumentType.TRUSTEES_DEED,
        "TRUSTEE'S DEED": DocumentType.TRUSTEES_DEED,
        "SUBSTITUTE TRUSTEE'S DEED": DocumentType.TRUSTEES_DEED,
        "DEED": DocumentType.WARRANTY_DEED,
        "DEED WITHOUT WARRANTY": DocumentType.BARGAIN_SALE_DEED,
        "GIFT DEED": DocumentType.GRANT_DEED,
        "CORRECTION DEED": DocumentType.CORRECTION_DEED,

        # Deeds of Trust (Texas equivalent of mortgage)
        "DOT": DocumentType.DEED_OF_TRUST,
        "D/T": DocumentType.DEED_OF_TRUST,
        "DEED OF TRUST": DocumentType.DEED_OF_TRUST,
        "DTR": DocumentType.MORTGAGE_RELEASE,
        "RELEASE OF LIEN": DocumentType.MORTGAGE_RELEASE,
        "RELEASE": DocumentType.MORTGAGE_RELEASE,
        "REL": DocumentType.MORTGAGE_RELEASE,
        "RELEASE OF DEED OF TRUST": DocumentType.MORTGAGE_RELEASE,
        "PARTIAL RELEASE": DocumentType.MORTGAGE_RELEASE,
        "ASSIGNMENT": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASGN": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT OF DEED OF TRUST": DocumentType.MORTGAGE_ASSIGNMENT,
        "TRANSFER OF LIEN": DocumentType.MORTGAGE_ASSIGNMENT,
        "MODIFICATION": DocumentType.MORTGAGE_MODIFICATION,
        "MOD": DocumentType.MORTGAGE_MODIFICATION,
        "LOAN MODIFICATION AGREEMENT": DocumentType.MORTGAGE_MODIFICATION,
        "SUB": DocumentType.SUBORDINATION_AGREEMENT,
        "SUBORDINATION AGREEMENT": DocumentType.SUBORDINATION_AGREEMENT,

        # Texas Home Equity
        "HOME EQUITY DEED OF TRUST": DocumentType.DEED_OF_TRUST,
        "HELOC": DocumentType.DEED_OF_TRUST,

        # Liens
        "MML": DocumentType.MECHANICS_LIEN,
        "MECHANIC'S LIEN": DocumentType.MECHANICS_LIEN,
        "MECHANIC AND MATERIALMAN'S LIEN": DocumentType.MECHANICS_LIEN,
        "M&M LIEN": DocumentType.MECHANICS_LIEN,
        "AFFIDAVIT OF LIEN": DocumentType.MECHANICS_LIEN,
        "RELEASE OF M&M LIEN": DocumentType.MECHANICS_LIEN_RELEASE,
        "AJ": DocumentType.JUDGMENT_LIEN,
        "ABSTRACT OF JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "JUDGMENT LIEN": DocumentType.JUDGMENT_LIEN,
        "RELEASE OF JUDGMENT": DocumentType.JUDGMENT_SATISFACTION,
        "FTL": DocumentType.TAX_LIEN_FEDERAL,
        "FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "NOTICE OF FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "STL": DocumentType.TAX_LIEN_STATE,
        "STATE TAX LIEN": DocumentType.TAX_LIEN_STATE,
        "HOSPITAL LIEN": DocumentType.OTHER,
        "HOA LIEN": DocumentType.HOA_LIEN,
        "ASSESSMENT LIEN": DocumentType.HOA_LIEN,
        "CHILD SUPPORT LIEN": DocumentType.CHILD_SUPPORT_LIEN,

        # Foreclosure (Texas non-judicial)
        "NOS": DocumentType.NOTICE_OF_SALE,
        "NOTICE OF SUBSTITUTE TRUSTEE'S SALE": DocumentType.NOTICE_OF_SALE,
        "NOTICE OF TRUSTEE'S SALE": DocumentType.NOTICE_OF_SALE,
        "NOTICE OF SALE": DocumentType.NOTICE_OF_SALE,
        "APPOINTMENT OF SUBSTITUTE TRUSTEE": DocumentType.NOTICE,
        "LP": DocumentType.LIS_PENDENS,
        "LIS PENDENS": DocumentType.LIS_PENDENS,
        "NOTICE OF LIS PENDENS": DocumentType.LIS_PENDENS,

        # UCC (filed at county level in Texas for fixtures)
        "UCC": DocumentType.UCC_FINANCING,
        "UCC1": DocumentType.UCC_FINANCING,
        "UCC-1": DocumentType.UCC_FINANCING,
        "FINANCING STATEMENT": DocumentType.UCC_FINANCING,
        "FIXTURE FILING": DocumentType.UCC_FINANCING,

        # Easements and Restrictions
        "EASE": DocumentType.EASEMENT,
        "EASEMENT": DocumentType.EASEMENT,
        "GRANT OF EASEMENT": DocumentType.EASEMENT,
        "UTILITY EASEMENT": DocumentType.EASEMENT,
        "PIPELINE EASEMENT": DocumentType.EASEMENT,
        "DCR": DocumentType.CC_AND_RS,
        "DECLARATION OF COVENANTS": DocumentType.CC_AND_RS,
        "RESTRICTIONS": DocumentType.RESTRICTIVE_COVENANT,
        "RESTRICTIVE COVENANT": DocumentType.RESTRICTIVE_COVENANT,
        "DEED RESTRICTION": DocumentType.RESTRICTIVE_COVENANT,

        # Other common Texas documents
        "AFF": DocumentType.AFFIDAVIT,
        "AFFIDAVIT": DocumentType.AFFIDAVIT,
        "AFFIDAVIT OF HEIRSHIP": DocumentType.AFFIDAVIT,
        "AFFIDAVIT OF FACT": DocumentType.AFFIDAVIT,
        "POA": DocumentType.POWER_OF_ATTORNEY,
        "POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,
        "DURABLE POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,
        "REVOCATION OF POA": DocumentType.REVOCATION_OF_POA,
        "CONTRACT OF SALE": DocumentType.AGREEMENT,
        "REAL ESTATE CONTRACT": DocumentType.AGREEMENT,
        "EARNEST MONEY CONTRACT": DocumentType.AGREEMENT,
        "LEASE": DocumentType.LEASE,
        "OIL AND GAS LEASE": DocumentType.LEASE,
        "MINERAL LEASE": DocumentType.LEASE,
        "MEMORANDUM OF LEASE": DocumentType.MEMORANDUM,
        "OPTION": DocumentType.OPTION_TO_PURCHASE,

        # Plats and Maps
        "PLAT": DocumentType.PLAT_MAP,
        "SUBDIVISION PLAT": DocumentType.SUBDIVISION_MAP,
        "REPLAT": DocumentType.PLAT_MAP,
        "AMENDING PLAT": DocumentType.PLAT_MAP,

        # Vital records (filed with County Clerk)
        "MARRIAGE LICENSE": DocumentType.MARRIAGE_LICENSE,
        "MARRIAGE": DocumentType.MARRIAGE_LICENSE,
        "ASSUMED NAME": DocumentType.FICTITIOUS_BUSINESS_NAME,
        "DBA": DocumentType.FICTITIOUS_BUSINESS_NAME,
    }

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the Harris County recorder scraper."""
        super().__init__(session)
        self._viewstate: Optional[str] = None
        self._eventvalidation: Optional[str] = None

    async def _initialize_session(self):
        """Initialize search session and get ASP.NET viewstate tokens."""
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

        logger.debug("Harris County session initialized")

    def _parse_harris_county_document_type(self, raw_type: str) -> DocumentType:
        """Parse Harris County-specific document type strings."""
        if not raw_type:
            return DocumentType.UNKNOWN

        raw_type = raw_type.upper().strip()

        if raw_type in self.HARRIS_COUNTY_DOC_TYPES:
            return self.HARRIS_COUNTY_DOC_TYPES[raw_type]

        return self._parse_document_type(raw_type)

    def _parse_search_results(self, html: str) -> List[RecordedDocument]:
        """Parse search results HTML into RecordedDocument objects."""
        documents = []
        soup = self._parse_html(html)

        # Find the results grid/table
        results_table = soup.find("table", {"id": "gvResults"}) or \
                        soup.find("table", {"class": "results"}) or \
                        soup.find("table", {"class": "GridView"})

        if not results_table:
            # Check for "no results" message
            no_results = soup.find(text=re.compile(r"no\s+records?\s+found", re.I))
            if no_results:
                logger.debug("No results found")
            else:
                logger.debug("Results table not found")
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
            # Harris County typical column layout:
            # Film Code | Doc Type | Rec Date | Grantor | Grantee | Legal | Vol/Page

            film_code = cells[0].get_text(strip=True) if len(cells) > 0 else None
            if not film_code:
                return None

            doc_type_raw = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            rec_date_str = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            grantor_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            grantee_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            legal_text = cells[5].get_text(strip=True) if len(cells) > 5 else ""
            vol_page = cells[6].get_text(strip=True) if len(cells) > 6 else ""

            # Get detail link
            doc_link = cells[0].find("a")
            source_url = None
            if doc_link and doc_link.get("href"):
                source_url = urljoin(self.BASE_URL, doc_link.get("href"))

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

            # Parse legal description
            legal_descriptions = []
            if legal_text:
                ld = self._parse_legal_text(legal_text)
                if ld:
                    legal_descriptions.append(ld)

            # Parse volume/page (book/page equivalent)
            book = None
            page = None
            if vol_page:
                match = re.match(r"(\d+)\s*/\s*(\d+)", vol_page)
                if match:
                    book = match.group(1)
                    page = match.group(2)

            return RecordedDocument(
                document_number=film_code,
                instrument_number=film_code,
                book=book,
                page=page,
                document_type=self._parse_harris_county_document_type(doc_type_raw),
                document_type_raw=doc_type_raw,
                recorded_date=self._parse_date(rec_date_str),
                parties=parties,
                grantors=grantors,
                grantees=grantees,
                legal_descriptions=legal_descriptions,
                county=self.COUNTY_NAME,
                state=self.STATE_ABBREV,
                fips_code=self.FIPS_CODE,
                source_url=source_url,
                raw_data={
                    "film_code": film_code,
                    "doc_type_raw": doc_type_raw,
                    "grantor_raw": grantor_text,
                    "grantee_raw": grantee_text,
                    "legal_raw": legal_text,
                    "vol_page": vol_page,
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
        parts = re.split(r"[;|]|\s+AND\s+|\s+&\s+", text, flags=re.I)
        for part in parts:
            part = part.strip()
            if part:
                names.append(part)

        return names

    def _parse_legal_text(self, text: str) -> Optional[LegalDescription]:
        """Parse legal description text."""
        if not text:
            return None

        # Look for subdivision/lot/block pattern common in Harris County
        lot_match = re.search(r"LOT\s+(\d+[A-Z]?)", text, re.I)
        block_match = re.search(r"BLO?C?K?\s+(\d+[A-Z]?)", text, re.I)
        subdivision_match = re.search(r"^([^,]+)", text)  # Usually first part

        # Look for abstract/survey info (common in rural Harris County)
        abstract_match = re.search(r"ABS(?:TRACT)?\s+(\d+)", text, re.I)
        survey_match = re.search(r"SURVEY\s+([^,]+)", text, re.I)

        # Look for tract number
        tract_match = re.search(r"TRACT\s+(\d+[A-Z]?)", text, re.I)

        subdivision = None
        if subdivision_match:
            sub_text = subdivision_match.group(1).strip()
            # Clean up subdivision name (remove lot/block prefixes if they're at start)
            if not re.match(r"^(LOT|BLOCK|TRACT|ABS)", sub_text, re.I):
                subdivision = sub_text

        return LegalDescription(
            full_description=text,
            lot=lot_match.group(1) if lot_match else None,
            block=block_match.group(1) if block_match else None,
            subdivision=subdivision,
            section=abstract_match.group(1) if abstract_match else None,
            tract=tract_match.group(1) if tract_match else None,
        )

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
        Search Harris County records by party name.

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

        # Build form data for ASP.NET postback
        form_data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
            "txtLastName": last_name,
            "btnSearch": "Search",
        }

        if first_name:
            form_data["txtFirstName"] = first_name

        # Party type selection
        if party_type.lower() == "grantor":
            form_data["rdoPartyType"] = "G"
        elif party_type.lower() == "grantee":
            form_data["rdoPartyType"] = "E"
        else:
            form_data["rdoPartyType"] = "B"  # Both

        if start_date:
            form_data["txtFromDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            form_data["txtToDate"] = end_date.strftime("%m/%d/%Y")

        # Execute search
        all_documents = []

        try:
            status, html = await self._fetch(
                self.SEARCH_URL,
                method="POST",
                data=form_data
            )

            if status != 200:
                logger.warning(f"Name search returned HTTP {status}")
            else:
                documents = self._parse_search_results(html)

                if document_types:
                    documents = [d for d in documents if d.document_type in document_types]

                all_documents.extend(documents)

                # Update viewstate for pagination
                soup = self._parse_html(html)
                new_viewstate = soup.find("input", {"name": "__VIEWSTATE"})
                if new_viewstate:
                    self._viewstate = new_viewstate.get("value")

                # Handle pagination if more results exist
                page = 2
                while len(all_documents) < max_results:
                    # Check for next page link
                    next_link = soup.find("a", text=str(page)) or soup.find("a", {"class": "next"})
                    if not next_link:
                        break

                    # Post for next page
                    form_data["__VIEWSTATE"] = self._viewstate or ""
                    form_data["__EVENTTARGET"] = next_link.get("href", "").replace("javascript:__doPostBack('", "").split("'")[0]

                    status, html = await self._fetch(
                        self.SEARCH_URL,
                        method="POST",
                        data=form_data
                    )

                    if status != 200:
                        break

                    documents = self._parse_search_results(html)
                    if not documents:
                        break

                    if document_types:
                        documents = [d for d in documents if d.document_type in document_types]

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
        Search for a specific document by film code.

        Args:
            document_number: The film code / document number

        Returns:
            RecordedDocument if found, None otherwise
        """
        if not self._viewstate:
            await self._initialize_session()

        form_data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
            "txtFilmCode": document_number.strip(),
            "btnFilmSearch": "Search",
        }

        try:
            status, html = await self._fetch(
                self.SEARCH_URL,
                method="POST",
                data=form_data
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
        Search Harris County records by property ID / account number.

        Note: Harris County uses HCAD (Harris County Appraisal District)
        account numbers. For property searches, consider using the
        subdivision/lot/block search for better results.

        Args:
            parcel_number: The property ID or account number
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

        form_data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
            "txtPropertyID": parcel_number.strip(),
            "btnPropertySearch": "Search",
        }

        if start_date:
            form_data["txtFromDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            form_data["txtToDate"] = end_date.strftime("%m/%d/%Y")

        all_documents = []

        try:
            status, html = await self._fetch(
                self.SEARCH_URL,
                method="POST",
                data=form_data
            )

            if status != 200:
                logger.warning(f"Property search returned HTTP {status}")
            else:
                documents = self._parse_search_results(html)

                if document_types:
                    documents = [d for d in documents if d.document_type in document_types]

                all_documents.extend(documents)

        except Exception as e:
            logger.error(f"Error during property search: {e}")

        elapsed_ms = int((time.time() - start_time) * 1000)

        return SearchResult(
            documents=all_documents[:max_results],
            total_count=len(all_documents),
            page_number=1,
            page_size=max_results,
            has_more=len(all_documents) > max_results,
            search_criteria=SearchCriteria(
                parcel_number=parcel_number,
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
        Search Harris County records by address.

        Note: Harris County Clerk doesn't directly support address search.
        For address-based searches, first look up the property at HCAD
        (hcad.org) to get the account number and legal description,
        then search by those fields.

        This method attempts a name search using the street name as a
        workaround, but results may be limited.

        Args:
            address: Street address
            city: City name
            zip_code: ZIP code
            start_date: Start of recording date range
            end_date: End of recording date range
            max_results: Maximum results to return

        Returns:
            SearchResult with matching documents
        """
        # Extract street name from address as a workaround
        # This is imperfect but may find some results
        street_match = re.search(r"\d+\s+(.+?)(?:\s+(?:ST|AVE|BLVD|DR|RD|LN|CT|CIR|WAY|PL|TER)\.?\s*$|$)", address, re.I)

        if street_match:
            street_name = street_match.group(1).strip()
            return await self.search_by_legal_description(
                subdivision=street_name,
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )

        # If we can't parse the address, return empty results with a warning
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
                "Harris County Clerk doesn't support direct address search.",
                "Look up property at hcad.org for account number and legal description.",
                "Then search by property ID or legal description."
            ]
        )

    async def search_by_legal_description(
        self,
        subdivision: Optional[str] = None,
        lot: Optional[str] = None,
        block: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """
        Search Harris County records by legal description.

        Args:
            subdivision: Subdivision name
            lot: Lot number
            block: Block number
            start_date: Start of recording date range
            end_date: End of recording date range
            max_results: Maximum results to return

        Returns:
            SearchResult with matching documents
        """
        import time
        start_time = time.time()

        if not self._viewstate:
            await self._initialize_session()

        form_data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
            "btnLegalSearch": "Search",
        }

        if subdivision:
            form_data["txtSubdivision"] = subdivision

        if lot:
            form_data["txtLot"] = lot

        if block:
            form_data["txtBlock"] = block

        if start_date:
            form_data["txtFromDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            form_data["txtToDate"] = end_date.strftime("%m/%d/%Y")

        all_documents = []

        try:
            status, html = await self._fetch(
                self.SEARCH_URL,
                method="POST",
                data=form_data
            )

            if status != 200:
                logger.warning(f"Legal description search returned HTTP {status}")
            else:
                all_documents = self._parse_search_results(html)

        except Exception as e:
            logger.error(f"Error during legal description search: {e}")

        elapsed_ms = int((time.time() - start_time) * 1000)

        return SearchResult(
            documents=all_documents[:max_results],
            total_count=len(all_documents),
            page_number=1,
            page_size=max_results,
            has_more=len(all_documents) > max_results,
            search_criteria=SearchCriteria(
                subdivision=subdivision,
                lot=lot,
                block=block,
                start_date=start_date,
                end_date=end_date
            ),
            search_time_ms=elapsed_ms,
            source_system=self.SYSTEM_NAME
        )

    async def get_document_detail(
        self,
        document_number: str
    ) -> Optional[RecordedDocument]:
        """
        Get detailed information for a specific document.

        Args:
            document_number: The film code / document number

        Returns:
            RecordedDocument with full details, or None if not found
        """
        # Harris County detail page URL pattern
        detail_url = f"{self.BASE_URL}applications/websearch/RPDetail.aspx?filmcode={document_number}"

        try:
            status, html = await self._fetch(detail_url)

            if status != 200:
                logger.warning(f"Document detail returned HTTP {status}")
                return None

            soup = self._parse_html(html)

            doc = RecordedDocument(
                document_number=document_number,
                instrument_number=document_number,
                county=self.COUNTY_NAME,
                state=self.STATE_ABBREV,
                fips_code=self.FIPS_CODE,
                source_url=detail_url
            )

            # Parse document details from the page
            doc = self._parse_detail_page(soup, doc)

            return doc

        except Exception as e:
            logger.error(f"Error getting document detail: {e}")
            return None

    def _parse_detail_page(self, soup: BeautifulSoup, doc: RecordedDocument) -> RecordedDocument:
        """Parse the document detail page."""
        # Find document info table or fields
        info_table = soup.find("table", {"class": "detail"}) or soup.find("div", {"class": "document-info"})

        if info_table:
            # Parse table rows or divs
            rows = info_table.find_all("tr") if info_table.name == "table" else []
            for row in rows:
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower().rstrip(":")
                    value = cells[1].get_text(strip=True)
                    doc = self._apply_detail_field(doc, label, value)

        # Also look for labeled spans/divs
        for label_elem in soup.find_all(["label", "span"], class_=re.compile(r"label|field-name")):
            label = label_elem.get_text(strip=True).lower().rstrip(":")
            value_elem = label_elem.find_next_sibling() or label_elem.parent.find(class_=re.compile(r"value|field-value"))
            if value_elem:
                value = value_elem.get_text(strip=True)
                doc = self._apply_detail_field(doc, label, value)

        # Parse parties section
        parties_section = soup.find("div", {"id": "parties"}) or soup.find("table", {"class": "parties"})
        if parties_section:
            doc.parties = self._parse_parties_section(parties_section)
            doc.grantors = doc.get_grantors()
            doc.grantees = doc.get_grantees()

        # Parse legal description
        legal_section = soup.find("div", {"id": "legal"}) or soup.find("td", text=re.compile(r"legal", re.I))
        if legal_section:
            legal_text = legal_section.get_text(strip=True)
            legal_text = re.sub(r"^legal\s*description:?\s*", "", legal_text, flags=re.I)
            if legal_text:
                ld = self._parse_legal_text(legal_text)
                if ld:
                    doc.legal_descriptions = [ld]

        # Check for image availability
        image_link = soup.find("a", text=re.compile(r"view\s*image|document\s*image", re.I))
        if image_link:
            doc.image_available = True
            doc.image_url = urljoin(self.BASE_URL, image_link.get("href", ""))

        # Parse page count if shown
        page_elem = soup.find(text=re.compile(r"pages?:?\s*\d+", re.I))
        if page_elem:
            match = re.search(r"(\d+)\s*pages?", str(page_elem), re.I)
            if match:
                doc.page_count = int(match.group(1))

        return doc

    def _apply_detail_field(self, doc: RecordedDocument, label: str, value: str) -> RecordedDocument:
        """Apply a parsed field to the document."""
        label = label.lower()

        if "film code" in label or "document number" in label:
            if not doc.document_number:
                doc.document_number = value
        elif "instrument" in label:
            doc.instrument_number = value
        elif "type" in label:
            doc.document_type_raw = value
            doc.document_type = self._parse_harris_county_document_type(value)
        elif "recorded" in label or "filed" in label:
            doc.recorded_date = self._parse_date(value)
        elif "execution" in label or "executed" in label:
            doc.execution_date = self._parse_date(value)
        elif "consideration" in label or "amount" in label:
            doc.consideration = self._parse_amount(value)
        elif "volume" in label or "vol" in label:
            doc.book = value
        elif "page" in label and "count" not in label:
            doc.page = value

        return doc

    def _parse_parties_section(self, section) -> List[DocumentParty]:
        """Parse parties from the detail page."""
        parties = []

        # Find grantor entries
        grantor_rows = section.find_all("tr", class_=re.compile(r"grantor"))
        if not grantor_rows:
            grantor_section = section.find(text=re.compile(r"grantor", re.I))
            if grantor_section:
                parent = grantor_section.find_parent("tr") or grantor_section.find_parent("div")
                if parent:
                    text = parent.get_text()
                    text = re.sub(r"grantor[s]?:?\s*", "", text, flags=re.I)
                    for name in self._split_party_names(text):
                        parties.append(DocumentParty(
                            name=self._normalize_name(name),
                            role=PartyRole.GRANTOR,
                            raw_name=name
                        ))

        for row in grantor_rows:
            name = row.get_text(strip=True)
            name = re.sub(r"grantor:?\s*", "", name, flags=re.I)
            if name:
                parties.append(DocumentParty(
                    name=self._normalize_name(name),
                    role=PartyRole.GRANTOR,
                    raw_name=name
                ))

        # Find grantee entries
        grantee_rows = section.find_all("tr", class_=re.compile(r"grantee"))
        if not grantee_rows:
            grantee_section = section.find(text=re.compile(r"grantee", re.I))
            if grantee_section:
                parent = grantee_section.find_parent("tr") or grantee_section.find_parent("div")
                if parent:
                    text = parent.get_text()
                    text = re.sub(r"grantee[s]?:?\s*", "", text, flags=re.I)
                    for name in self._split_party_names(text):
                        parties.append(DocumentParty(
                            name=self._normalize_name(name),
                            role=PartyRole.GRANTEE,
                            raw_name=name
                        ))

        for row in grantee_rows:
            name = row.get_text(strip=True)
            name = re.sub(r"grantee:?\s*", "", name, flags=re.I)
            if name:
                parties.append(DocumentParty(
                    name=self._normalize_name(name),
                    role=PartyRole.GRANTEE,
                    raw_name=name
                ))

        return parties


# Convenience functions for synchronous usage

def search_harris_county_by_name(
    last_name: str,
    first_name: Optional[str] = None,
    **kwargs
) -> SearchResult:
    """Search Harris County records by name (synchronous)."""
    async def _search():
        async with HarrisCountyRecorder() as recorder:
            return await recorder.search_by_name(last_name, first_name, **kwargs)
    return asyncio.run(_search())


def search_harris_county_by_legal(
    subdivision: Optional[str] = None,
    lot: Optional[str] = None,
    block: Optional[str] = None,
    **kwargs
) -> SearchResult:
    """Search Harris County records by legal description (synchronous)."""
    async def _search():
        async with HarrisCountyRecorder() as recorder:
            return await recorder.search_by_legal_description(subdivision, lot, block, **kwargs)
    return asyncio.run(_search())


def get_harris_county_document(
    document_number: str
) -> Optional[RecordedDocument]:
    """Get a Harris County document by film code (synchronous)."""
    async def _get():
        async with HarrisCountyRecorder() as recorder:
            return await recorder.get_document_detail(document_number)
    return asyncio.run(_get())
