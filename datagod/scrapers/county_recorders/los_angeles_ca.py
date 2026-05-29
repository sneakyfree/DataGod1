"""
Los Angeles County, California Recorder Scraper

Los Angeles County is the most populous county in the United States (10M+).
The Registrar-Recorder/County Clerk maintains official records including
deeds, mortgages, liens, and other real property documents.

System: LAVOTE/County Recorder Online
URL: https://www.lavote.gov/home/county-clerk/recorder-background
Search URL: https://registrar.lacounty.gov/
FIPS: 06037

Available searches:
- Name search (grantor/grantee)
- Document number search
- APN (Assessor's Parcel Number) search
- Book/Page search
- Address search (via APN lookup)

Note: LA County uses APN format: XXXX-XXX-XXX
Images available online for documents from 1984 to present.
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


class LosAngelesCountyRecorder(CountyRecorderBase):
    """
    Scraper for Los Angeles County, California Registrar-Recorder.

    LA County provides online access to recorded documents through their
    official records search system. Documents from 1984 to present are
    available with images. Earlier documents may require in-person research.
    """

    COUNTY_NAME = "Los Angeles County"
    STATE = "California"
    STATE_ABBREV = "CA"
    FIPS_CODE = "06037"

    BASE_URL = "https://registrar.lacounty.gov/"
    SEARCH_URL = "https://registrar.lacounty.gov/officialrecords/"
    API_URL = "https://registrar.lacounty.gov/api/records/"
    SYSTEM_NAME = "LA County Registrar-Recorder Online"

    REQUEST_DELAY = 2.0  # Respectful rate limiting
    MAX_RETRIES = 3
    TIMEOUT = 45

    REQUIRES_LOGIN = False
    REQUIRES_CAPTCHA = False

    # LA County APN format: XXXX-XXX-XXX (10 digits with dashes)
    APN_PATTERN = re.compile(r"^\d{4}-\d{3}-\d{3}$")

    # California-specific document types
    LA_COUNTY_DOC_TYPES = {
        # Deeds - California uses Grant Deed as standard
        "GD": DocumentType.GRANT_DEED,
        "GRANT DEED": DocumentType.GRANT_DEED,
        "DEED": DocumentType.GRANT_DEED,
        "QCD": DocumentType.QUITCLAIM_DEED,
        "QUITCLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "QUIT CLAIM": DocumentType.QUITCLAIM_DEED,
        "WD": DocumentType.WARRANTY_DEED,
        "WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "TD": DocumentType.TRUSTEES_DEED,
        "TRUSTEE'S DEED": DocumentType.TRUSTEES_DEED,
        "TRUSTEES DEED": DocumentType.TRUSTEES_DEED,
        "TDUS": DocumentType.TRUSTEES_DEED_UPON_SALE,
        "TRUSTEE'S DEED UPON SALE": DocumentType.TRUSTEES_DEED_UPON_SALE,
        "INTERSPOUSAL TRANSFER DEED": DocumentType.QUITCLAIM_DEED,
        "ITD": DocumentType.QUITCLAIM_DEED,
        # Deeds of Trust (California uses DOT instead of Mortgage)
        "DOT": DocumentType.DEED_OF_TRUST,
        "DEED OF TRUST": DocumentType.DEED_OF_TRUST,
        "TRUST DEED": DocumentType.DEED_OF_TRUST,
        "D/T": DocumentType.DEED_OF_TRUST,
        "RECON": DocumentType.MORTGAGE_RELEASE,
        "RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "FULL RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "PARTIAL RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "SUB": DocumentType.SUBORDINATION_AGREEMENT,
        "SUBORDINATION": DocumentType.SUBORDINATION_AGREEMENT,
        "SUBORDINATION AGREEMENT": DocumentType.SUBORDINATION_AGREEMENT,
        "ASGN": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT OF DOT": DocumentType.MORTGAGE_ASSIGNMENT,
        "MOD": DocumentType.MORTGAGE_MODIFICATION,
        "LOAN MODIFICATION": DocumentType.MORTGAGE_MODIFICATION,
        # Liens
        "ML": DocumentType.MECHANICS_LIEN,
        "MECHANIC'S LIEN": DocumentType.MECHANICS_LIEN,
        "MECHANICS LIEN": DocumentType.MECHANICS_LIEN,
        "MLR": DocumentType.MECHANICS_LIEN_RELEASE,
        "RELEASE OF MECHANICS LIEN": DocumentType.MECHANICS_LIEN_RELEASE,
        "AJ": DocumentType.JUDGMENT_LIEN,
        "ABSTRACT OF JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "SATISFACTION OF JUDGMENT": DocumentType.JUDGMENT_SATISFACTION,
        "FTL": DocumentType.TAX_LIEN_FEDERAL,
        "FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "NFTL": DocumentType.TAX_LIEN_FEDERAL,
        "NOTICE OF FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "STL": DocumentType.TAX_LIEN_STATE,
        "STATE TAX LIEN": DocumentType.TAX_LIEN_STATE,
        "FTB LIEN": DocumentType.TAX_LIEN_STATE,
        "CERTIFICATE OF RELEASE FTL": DocumentType.TAX_LIEN_RELEASE,
        # Foreclosure (California non-judicial foreclosure)
        "NOD": DocumentType.NOTICE_OF_DEFAULT,
        "NOTICE OF DEFAULT": DocumentType.NOTICE_OF_DEFAULT,
        "NTS": DocumentType.NOTICE_OF_SALE,
        "NOTICE OF TRUSTEE'S SALE": DocumentType.NOTICE_OF_SALE,
        "NOTICE OF SALE": DocumentType.NOTICE_OF_SALE,
        "CANCELLATION OF NOD": DocumentType.NOTICE,
        "RESCISSION OF NOD": DocumentType.NOTICE,
        "LP": DocumentType.LIS_PENDENS,
        "LIS PENDENS": DocumentType.LIS_PENDENS,
        "NOTICE OF PENDENCY OF ACTION": DocumentType.LIS_PENDENS,
        # UCC
        "UCC1": DocumentType.UCC_FINANCING,
        "UCC-1": DocumentType.UCC_FINANCING,
        "FINANCING STATEMENT": DocumentType.UCC_FINANCING,
        "UCC3": DocumentType.UCC_AMENDMENT,
        "UCC-3": DocumentType.UCC_AMENDMENT,
        # Easements and Restrictions
        "EASE": DocumentType.EASEMENT,
        "EASEMENT": DocumentType.EASEMENT,
        "GRANT OF EASEMENT": DocumentType.EASEMENT,
        "CCR": DocumentType.CC_AND_RS,
        "CC&R": DocumentType.CC_AND_RS,
        "CC&RS": DocumentType.CC_AND_RS,
        "DECLARATION OF CC&RS": DocumentType.CC_AND_RS,
        "COVENANT": DocumentType.RESTRICTIVE_COVENANT,
        # Other common documents
        "AFF": DocumentType.AFFIDAVIT,
        "AFFIDAVIT": DocumentType.AFFIDAVIT,
        "DEATH OF JOINT TENANT": DocumentType.AFFIDAVIT,
        "AFFIDAVIT DEATH OF JOINT TENANT": DocumentType.AFFIDAVIT,
        "POA": DocumentType.POWER_OF_ATTORNEY,
        "POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,
        "FBN": DocumentType.FICTITIOUS_BUSINESS_NAME,
        "FICTITIOUS BUSINESS NAME": DocumentType.FICTITIOUS_BUSINESS_NAME,
        "DBA": DocumentType.FICTITIOUS_BUSINESS_NAME,
        "LEASE": DocumentType.LEASE,
        "MEM": DocumentType.MEMORANDUM,
        "MEMORANDUM": DocumentType.MEMORANDUM,
        "OPTION": DocumentType.OPTION_TO_PURCHASE,
        # Maps
        "PM": DocumentType.PARCEL_MAP,
        "PARCEL MAP": DocumentType.PARCEL_MAP,
        "TR": DocumentType.SUBDIVISION_MAP,
        "TRACT MAP": DocumentType.SUBDIVISION_MAP,
        "SUBDIVISION MAP": DocumentType.SUBDIVISION_MAP,
        "COC": DocumentType.SURVEY,
        "CERTIFICATE OF COMPLIANCE": DocumentType.SURVEY,
    }

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the LA County recorder scraper."""
        super().__init__(session)
        self._session_initialized = False

    async def _initialize_session(self):
        """Initialize a search session."""
        if self._session_initialized:
            return

        if not self.session:
            raise RuntimeError("Session not initialized")

        # Visit the main search page to establish session
        status, _ = await self._fetch(self.SEARCH_URL)
        if status == 200:
            self._session_initialized = True
            logger.debug("LA County session initialized")

    def _parse_la_county_document_type(self, raw_type: str) -> DocumentType:
        """Parse LA County-specific document type strings."""
        if not raw_type:
            return DocumentType.UNKNOWN

        raw_type = raw_type.upper().strip()

        if raw_type in self.LA_COUNTY_DOC_TYPES:
            return self.LA_COUNTY_DOC_TYPES[raw_type]

        return self._parse_document_type(raw_type)

    def _parse_apn(self, apn_str: str) -> Optional[str]:
        """Parse and validate an LA County APN."""
        if not apn_str:
            return None

        # Remove spaces and standardize
        apn_str = apn_str.strip().replace(" ", "")

        # If already in correct format
        if self.APN_PATTERN.match(apn_str):
            return apn_str

        # Try to format from digits only (10 digits)
        digits = re.sub(r"[^\d]", "", apn_str)
        if len(digits) == 10:
            return f"{digits[0:4]}-{digits[4:7]}-{digits[7:10]}"

        logger.warning(f"Invalid LA County APN format: {apn_str}")
        return apn_str

    def _parse_search_results_html(self, html: str) -> List[RecordedDocument]:
        """Parse HTML search results into RecordedDocument objects."""
        documents = []
        soup = self._parse_html(html)

        # Find results container
        results_div = soup.find("div", {"class": "search-results"}) or soup.find(
            "div", {"id": "results"}
        )
        if not results_div:
            results_div = soup

        # Find result rows/cards
        result_items = results_div.find_all(
            "div", {"class": "result-item"}
        ) or results_div.find_all("tr", {"class": "result-row"})

        if not result_items:
            # Try table format
            table = soup.find("table", {"class": "results"})
            if table:
                result_items = table.find_all("tr")[1:]  # Skip header

        for item in result_items:
            try:
                doc = self._parse_result_item(item)
                if doc:
                    documents.append(doc)
            except Exception as e:
                logger.warning(f"Error parsing result item: {e}")
                continue

        return documents

    def _parse_result_item(self, item) -> Optional[RecordedDocument]:
        """Parse a single result item into a RecordedDocument."""
        try:
            # Extract based on structure (div with classes or table row)
            if item.name == "tr":
                return self._parse_table_row(item)
            else:
                return self._parse_result_div(item)
        except Exception as e:
            logger.warning(f"Error parsing result item: {e}")
            return None

    def _parse_table_row(self, row) -> Optional[RecordedDocument]:
        """Parse a table row result."""
        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        # Typical column order:
        # Doc Number | Doc Type | Recorded Date | Grantor | Grantee | APN | Amount
        doc_number = cells[0].get_text(strip=True)
        if not doc_number:
            return None

        doc_type_raw = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        recorded_date_str = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        grantor_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
        grantee_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
        apn_text = cells[5].get_text(strip=True) if len(cells) > 5 else ""
        amount_text = cells[6].get_text(strip=True) if len(cells) > 6 else ""

        # Get link to detail page
        doc_link = cells[0].find("a")
        source_url = (
            urljoin(self.BASE_URL, doc_link.get("href"))
            if doc_link and doc_link.get("href")
            else None
        )

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

        # Parse APN
        legal_descriptions = []
        parcels = []
        if apn_text:
            apn = self._parse_apn(apn_text)
            if apn:
                parcels.append(apn)
                legal_descriptions.append(
                    LegalDescription(
                        full_description=f"APN: {apn}", parcel_number=apn, apn=apn
                    )
                )

        return RecordedDocument(
            document_number=doc_number,
            document_type=self._parse_la_county_document_type(doc_type_raw),
            document_type_raw=doc_type_raw,
            recorded_date=self._parse_date(recorded_date_str),
            parties=parties,
            grantors=grantors,
            grantees=grantees,
            legal_descriptions=legal_descriptions,
            parcels=parcels,
            consideration=self._parse_amount(amount_text),
            county=self.COUNTY_NAME,
            state=self.STATE_ABBREV,
            fips_code=self.FIPS_CODE,
            source_url=source_url,
            raw_data={
                "doc_type_raw": doc_type_raw,
                "grantor_raw": grantor_text,
                "grantee_raw": grantee_text,
                "apn_raw": apn_text,
            },
        )

    def _parse_result_div(self, div) -> Optional[RecordedDocument]:
        """Parse a div-based result item."""
        # Find document number
        doc_num_elem = div.find("span", {"class": "doc-number"}) or div.find(
            class_=re.compile(r"doc.*num")
        )
        doc_number = doc_num_elem.get_text(strip=True) if doc_num_elem else None

        if not doc_number:
            # Try finding by data attribute or link
            link = div.find("a", href=re.compile(r"document|detail"))
            if link:
                doc_number = link.get_text(strip=True)
                if not doc_number:
                    # Try to extract from URL
                    href = link.get("href", "")
                    match = re.search(r"(\d{10,})", href)
                    if match:
                        doc_number = match.group(1)

        if not doc_number:
            return None

        # Extract other fields
        doc_type_elem = div.find("span", {"class": "doc-type"}) or div.find(
            class_=re.compile(r"type")
        )
        doc_type_raw = doc_type_elem.get_text(strip=True) if doc_type_elem else ""

        date_elem = div.find("span", {"class": "recorded-date"}) or div.find(
            class_=re.compile(r"date")
        )
        recorded_date_str = date_elem.get_text(strip=True) if date_elem else ""

        grantor_elem = div.find("span", {"class": "grantor"}) or div.find(
            class_=re.compile(r"grantor")
        )
        grantor_text = grantor_elem.get_text(strip=True) if grantor_elem else ""

        grantee_elem = div.find("span", {"class": "grantee"}) or div.find(
            class_=re.compile(r"grantee")
        )
        grantee_text = grantee_elem.get_text(strip=True) if grantee_elem else ""

        apn_elem = div.find("span", {"class": "apn"}) or div.find(
            class_=re.compile(r"apn|parcel")
        )
        apn_text = apn_elem.get_text(strip=True) if apn_elem else ""

        # Build parties lists
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

        # Parse APN
        legal_descriptions = []
        parcels = []
        if apn_text:
            apn = self._parse_apn(apn_text)
            if apn:
                parcels.append(apn)
                legal_descriptions.append(
                    LegalDescription(
                        full_description=f"APN: {apn}", parcel_number=apn, apn=apn
                    )
                )

        # Get detail link
        link = div.find("a", href=re.compile(r"document|detail"))
        source_url = (
            urljoin(self.BASE_URL, link.get("href"))
            if link and link.get("href")
            else None
        )

        return RecordedDocument(
            document_number=doc_number,
            document_type=self._parse_la_county_document_type(doc_type_raw),
            document_type_raw=doc_type_raw,
            recorded_date=self._parse_date(recorded_date_str),
            parties=parties,
            grantors=grantors,
            grantees=grantees,
            legal_descriptions=legal_descriptions,
            parcels=parcels,
            county=self.COUNTY_NAME,
            state=self.STATE_ABBREV,
            fips_code=self.FIPS_CODE,
            source_url=source_url,
        )

    def _split_party_names(self, text: str) -> List[str]:
        """Split a party names string into individual names."""
        if not text:
            return []

        # Common separators in LA County records
        # Split on semicolon, "AND", or comma (but be careful with "Smith, John")
        names = []

        # First split on semicolon
        parts = text.split(";")

        for part in parts:
            # Then split on " AND " (with spaces)
            subparts = re.split(r"\s+AND\s+", part, flags=re.I)
            for subpart in subparts:
                subpart = subpart.strip()
                if subpart:
                    names.append(subpart)

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
        Search LA County records by party name.

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
            "searchType": "name",
            "lastName": last_name,
        }

        if first_name:
            params["firstName"] = first_name

        if party_type.lower() == "grantor":
            params["nameType"] = "GR"
        elif party_type.lower() == "grantee":
            params["nameType"] = "GE"
        else:
            params["nameType"] = "BOTH"

        if start_date:
            params["fromDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            params["toDate"] = end_date.strftime("%m/%d/%Y")

        # Execute search
        search_url = f"{self.SEARCH_URL}search"
        all_documents = []
        page = 1
        has_more = True

        while has_more and len(all_documents) < max_results:
            params["page"] = page
            params["pageSize"] = min(50, max_results - len(all_documents))

            try:
                status, html = await self._fetch(search_url, method="POST", data=params)

                if status != 200:
                    logger.warning(f"Name search returned HTTP {status}")
                    break

                documents = self._parse_search_results_html(html)

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

        In LA County, document numbers are typically in format YYYYXXXXXXX
        (year + 7 digit sequence).

        Args:
            document_number: The document/instrument number

        Returns:
            RecordedDocument if found, None otherwise
        """
        await self._initialize_session()

        # Clean the document number
        doc_num = re.sub(r"[^\d]", "", document_number.strip())

        params = {
            "searchType": "docnum",
            "documentNumber": doc_num,
        }

        search_url = f"{self.SEARCH_URL}search"

        try:
            status, html = await self._fetch(search_url, method="POST", data=params)

            if status != 200:
                logger.warning(f"Document search returned HTTP {status}")
                return None

            documents = self._parse_search_results_html(html)

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
        max_results: int = 100,
    ) -> SearchResult:
        """
        Search LA County records by APN (Assessor's Parcel Number).

        Args:
            parcel_number: The APN in format XXXX-XXX-XXX
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
                warnings=["Invalid APN format. Use XXXX-XXX-XXX format."],
            )

        params = {
            "searchType": "apn",
            "apn": apn.replace("-", ""),  # Some systems want no dashes
        }

        if start_date:
            params["fromDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            params["toDate"] = end_date.strftime("%m/%d/%Y")

        search_url = f"{self.SEARCH_URL}search"
        all_documents = []
        page = 1
        has_more = True

        while has_more and len(all_documents) < max_results:
            params["page"] = page
            params["pageSize"] = min(50, max_results - len(all_documents))

            try:
                status, html = await self._fetch(search_url, method="POST", data=params)

                if status != 200:
                    logger.warning(f"APN search returned HTTP {status}")
                    break

                documents = self._parse_search_results_html(html)

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
        Search LA County records by property address.

        Note: LA County's address search works by first looking up the APN
        from the Assessor's records, then searching the Recorder's records
        by that APN. Direct address search may have limited results.

        For best results, look up the APN first at:
        https://portal.assessor.lacounty.gov/

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
        import time

        start_time = time.time()

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
            params["fromDate"] = start_date.strftime("%m/%d/%Y")

        if end_date:
            params["toDate"] = end_date.strftime("%m/%d/%Y")

        search_url = f"{self.SEARCH_URL}search"

        try:
            status, html = await self._fetch(search_url, method="POST", data=params)

            if status != 200:
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

            documents = self._parse_search_results_html(html)

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
                    "For complete results, search by APN. Look up APN at portal.assessor.lacounty.gov"
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
        doc_num = re.sub(r"[^\d]", "", document_number.strip())
        detail_url = f"{self.SEARCH_URL}document/{doc_num}"

        try:
            status, html = await self._fetch(detail_url)

            if status != 200:
                logger.warning(f"Document detail returned HTTP {status}")
                return None

            soup = self._parse_html(html)

            doc = RecordedDocument(
                document_number=doc_num,
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
        # Find document info section
        info_section = (
            soup.find("div", {"class": "document-info"})
            or soup.find("table", {"class": "document-details"})
            or soup.find("dl", {"class": "document-info"})
        )

        if info_section:
            # Parse key-value pairs
            if info_section.name == "dl":
                items = list(
                    zip(info_section.find_all("dt"), info_section.find_all("dd"))
                )
                for dt, dd in items:
                    label = dt.get_text(strip=True).lower().rstrip(":")
                    value = dd.get_text(strip=True)
                    doc = self._apply_detail_field(doc, label, value)
            elif info_section.name == "table":
                for row in info_section.find_all("tr"):
                    cells = row.find_all(["th", "td"])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower().rstrip(":")
                        value = cells[1].get_text(strip=True)
                        doc = self._apply_detail_field(doc, label, value)

        # Parse parties
        parties_section = soup.find("div", {"class": "parties"}) or soup.find(
            "table", {"class": "parties"}
        )
        if parties_section:
            doc.parties = self._parse_parties(parties_section)
            doc.grantors = doc.get_grantors()
            doc.grantees = doc.get_grantees()

        # Parse legal descriptions
        legal_section = soup.find("div", {"class": "legal"}) or soup.find(
            "div", {"class": "apn"}
        )
        if legal_section:
            doc.legal_descriptions = self._parse_legal(legal_section)
            doc.parcels = [ld.apn for ld in doc.legal_descriptions if ld.apn]

        # Check for image
        image_link = soup.find("a", {"class": "view-image"}) or soup.find(
            "a", text=re.compile(r"view.*image", re.I)
        )
        if image_link:
            doc.image_available = True
            doc.image_url = urljoin(self.BASE_URL, image_link.get("href", ""))

        # Page count
        page_text = soup.find(text=re.compile(r"pages?:?\s*\d+", re.I))
        if page_text:
            match = re.search(r"(\d+)\s*pages?", str(page_text), re.I)
            if match:
                doc.page_count = int(match.group(1))

        return doc

    def _apply_detail_field(
        self, doc: RecordedDocument, label: str, value: str
    ) -> RecordedDocument:
        """Apply a parsed detail field to the document."""
        label = label.lower()

        if "document" in label and "number" in label:
            if not doc.document_number:
                doc.document_number = value
        elif "instrument" in label:
            doc.instrument_number = value
        elif "type" in label and "document" in label:
            doc.document_type_raw = value
            doc.document_type = self._parse_la_county_document_type(value)
        elif "recorded" in label or "record date" in label:
            doc.recorded_date = self._parse_date(value)
        elif "execution" in label or "executed" in label:
            doc.execution_date = self._parse_date(value)
        elif "consideration" in label or "amount" in label:
            doc.consideration = self._parse_amount(value)
        elif "documentary transfer tax" in label or "doc tax" in label:
            doc.transfer_tax = self._parse_amount(value)
        elif "book" in label:
            doc.book = value
        elif "page" in label and "count" not in label:
            doc.page = value

        return doc

    def _parse_parties(self, section) -> List[DocumentParty]:
        """Parse parties from the detail page."""
        parties = []

        # Find grantor names
        grantor_section = section.find(
            text=re.compile(r"grantor|trustor|mortgagor", re.I)
        )
        if grantor_section:
            parent = grantor_section.find_parent(["tr", "div", "li", "dt"])
            if parent:
                # Get the next sibling or dd element for values
                if parent.name == "dt":
                    value_elem = parent.find_next_sibling("dd")
                else:
                    value_elem = parent
                if value_elem:
                    text = value_elem.get_text()
                    text = re.sub(r"^.*?:\s*", "", text)  # Remove label
                    for name in self._split_party_names(text):
                        parties.append(
                            DocumentParty(
                                name=self._normalize_name(name),
                                role=PartyRole.GRANTOR,
                                raw_name=name,
                            )
                        )

        # Find grantee names
        grantee_section = section.find(
            text=re.compile(r"grantee|trustee|beneficiary|mortgagee", re.I)
        )
        if grantee_section:
            parent = grantee_section.find_parent(["tr", "div", "li", "dt"])
            if parent:
                if parent.name == "dt":
                    value_elem = parent.find_next_sibling("dd")
                else:
                    value_elem = parent
                if value_elem:
                    text = value_elem.get_text()
                    text = re.sub(r"^.*?:\s*", "", text)
                    for name in self._split_party_names(text):
                        parties.append(
                            DocumentParty(
                                name=self._normalize_name(name),
                                role=PartyRole.GRANTEE,
                                raw_name=name,
                            )
                        )

        return parties

    def _parse_legal(self, section) -> List[LegalDescription]:
        """Parse legal descriptions from the detail page."""
        legal_descriptions = []
        text = section.get_text()

        # Find APNs
        apn_matches = re.findall(r"\d{4}[- ]?\d{3}[- ]?\d{3}", text)
        for apn_raw in apn_matches:
            apn = self._parse_apn(apn_raw)
            if apn:
                legal_descriptions.append(
                    LegalDescription(
                        full_description=f"APN: {apn}", parcel_number=apn, apn=apn
                    )
                )

        # Look for tract/lot/unit info (common in subdivisions)
        tract_match = re.search(r"tract\s+(?:no\.?\s*)?(\d+)", text, re.I)
        lot_match = re.search(r"lot\s+(\d+)", text, re.I)
        unit_match = re.search(r"unit\s+(\d+[A-Z]?)", text, re.I)

        if tract_match or lot_match or unit_match:
            if legal_descriptions:
                ld = legal_descriptions[0]
                if tract_match:
                    ld.tract = tract_match.group(1)
                if lot_match:
                    ld.lot = lot_match.group(1)
                if unit_match:
                    ld.unit = unit_match.group(1)
            else:
                legal_descriptions.append(
                    LegalDescription(
                        full_description=text.strip()[:500],
                        tract=tract_match.group(1) if tract_match else None,
                        lot=lot_match.group(1) if lot_match else None,
                        unit=unit_match.group(1) if unit_match else None,
                    )
                )

        return legal_descriptions


# Convenience functions for synchronous usage


def search_la_county_by_name(
    last_name: str, first_name: Optional[str] = None, **kwargs
) -> SearchResult:
    """Search LA County records by name (synchronous)."""

    async def _search():
        async with LosAngelesCountyRecorder() as recorder:
            return await recorder.search_by_name(last_name, first_name, **kwargs)

    return asyncio.run(_search())


def search_la_county_by_apn(apn: str, **kwargs) -> SearchResult:
    """Search LA County records by APN (synchronous)."""

    async def _search():
        async with LosAngelesCountyRecorder() as recorder:
            return await recorder.search_by_parcel(apn, **kwargs)

    return asyncio.run(_search())


def get_la_county_document(document_number: str) -> Optional[RecordedDocument]:
    """Get an LA County document by number (synchronous)."""

    async def _get():
        async with LosAngelesCountyRecorder() as recorder:
            return await recorder.get_document_detail(document_number)

    return asyncio.run(_get())
