"""
King County, Washington Recorder Scraper

King County (2.3M population) maintains recorded documents through
the King County Recorder's Office with online access via the
Records and Licensing Services Division.

System: King County eRecording / Accela
URL: https://recordsearch.kingcounty.gov/
FIPS: 53033

Available searches:
- Name search (grantor/grantee)
- Document number search
- Recording number search
- Recording date range
- Parcel/tax account number

Washington uses primarily Warranty Deeds and Statutory Warranty Deeds.
Washington has a Real Estate Excise Tax (REET) instead of documentary stamps.
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


class KingCountyRecorder(CountyRecorderBase):
    """
    Scraper for King County, Washington Recorder's Office.

    King County provides online access to recorded documents through
    their eRecording system. Records are indexed by recording number
    or instrument number. Washington uses REET instead of transfer tax.
    """

    COUNTY_NAME = "King County"
    STATE = "Washington"
    STATE_ABBREV = "WA"
    FIPS_CODE = "53033"

    BASE_URL = "https://recordsearch.kingcounty.gov/"
    SEARCH_URL = "https://recordsearch.kingcounty.gov/LandmarkWeb/search/index"
    API_URL = "https://recordsearch.kingcounty.gov/api/search"
    DETAIL_URL = "https://recordsearch.kingcounty.gov/api/document"
    SYSTEM_NAME = "King County Landmark Web"

    REQUEST_DELAY = 1.5
    MAX_RETRIES = 3
    TIMEOUT = 45

    REQUIRES_LOGIN = False
    REQUIRES_CAPTCHA = False

    # Document type mappings for King County / Washington
    KING_DOC_TYPES = {
        "STATUTORY WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "SWD": DocumentType.WARRANTY_DEED,
        "WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "WD": DocumentType.WARRANTY_DEED,
        "BARGAIN AND SALE DEED": DocumentType.BARGAIN_SALE_DEED,
        "BSD": DocumentType.BARGAIN_SALE_DEED,
        "QUITCLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "QCD": DocumentType.QUITCLAIM_DEED,
        "QUIT CLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "TRUSTEE'S DEED": DocumentType.TRUSTEES_DEED,
        "TRUSTEES DEED": DocumentType.TRUSTEES_DEED,
        "TD": DocumentType.TRUSTEES_DEED,
        "PERSONAL REPRESENTATIVE'S DEED": DocumentType.TRUSTEES_DEED,
        "EXECUTOR'S DEED": DocumentType.TRUSTEES_DEED,
        "ADMINISTRATOR'S DEED": DocumentType.TRUSTEES_DEED,
        "DEED OF TRUST": DocumentType.DEED_OF_TRUST,
        "DOT": DocumentType.DEED_OF_TRUST,
        "TRUST DEED": DocumentType.DEED_OF_TRUST,
        "SHORT FORM DEED OF TRUST": DocumentType.DEED_OF_TRUST,
        "RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "FULL RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "PARTIAL RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "DEED OF RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "RELEASE OF LIEN": DocumentType.MORTGAGE_RELEASE,
        "ASSIGNMENT OF DEED OF TRUST": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT": DocumentType.MORTGAGE_ASSIGNMENT,
        "MODIFICATION OF DEED OF TRUST": DocumentType.MORTGAGE_MODIFICATION,
        "MODIFICATION": DocumentType.MORTGAGE_MODIFICATION,
        "LOAN MODIFICATION AGREEMENT": DocumentType.MORTGAGE_MODIFICATION,
        "NOTICE OF TRUSTEE'S SALE": DocumentType.NOTICE_OF_SALE,
        "NOTICE OF TRUSTEE SALE": DocumentType.NOTICE_OF_SALE,
        "NOTICE OF DEFAULT": DocumentType.NOTICE_OF_DEFAULT,
        "TRUSTEE'S DEED UPON SALE": DocumentType.TRUSTEES_DEED_UPON_SALE,
        "LIS PENDENS": DocumentType.LIS_PENDENS,
        "MECHANICS LIEN": DocumentType.MECHANICS_LIEN,
        "MECHANIC'S LIEN": DocumentType.MECHANICS_LIEN,
        "CONSTRUCTION LIEN": DocumentType.MECHANICS_LIEN,
        "MATERIALMAN'S LIEN": DocumentType.MECHANICS_LIEN,
        "CLAIM OF LIEN": DocumentType.MECHANICS_LIEN,
        "ABSTRACT OF JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "NOTICE OF FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "STATE TAX LIEN": DocumentType.TAX_LIEN_STATE,
        "STATE TAX WARRANT": DocumentType.TAX_LIEN_STATE,
        "RELEASE OF FEDERAL TAX LIEN": DocumentType.TAX_LIEN_RELEASE,
        "RELEASE OF STATE TAX LIEN": DocumentType.TAX_LIEN_RELEASE,
        "UCC-1": DocumentType.UCC_FINANCING,
        "UCC FINANCING STATEMENT": DocumentType.UCC_FINANCING,
        "UCC-3": DocumentType.UCC_AMENDMENT,
        "UCC AMENDMENT": DocumentType.UCC_AMENDMENT,
        "EASEMENT": DocumentType.EASEMENT,
        "ACCESS EASEMENT": DocumentType.EASEMENT,
        "UTILITY EASEMENT": DocumentType.EASEMENT,
        "COVENANT": DocumentType.RESTRICTIVE_COVENANT,
        "RESTRICTIVE COVENANT": DocumentType.RESTRICTIVE_COVENANT,
        "CC&R": DocumentType.CC_AND_RS,
        "DECLARATION": DocumentType.CC_AND_RS,
        "DECLARATION OF COVENANTS": DocumentType.CC_AND_RS,
        "PLAT": DocumentType.PLAT_MAP,
        "SHORT PLAT": DocumentType.PLAT_MAP,
        "BINDING SITE PLAN": DocumentType.PLAT_MAP,
        "SURVEY": DocumentType.SURVEY,
        "BOUNDARY LINE ADJUSTMENT": DocumentType.SURVEY,
        "AFFIDAVIT": DocumentType.AFFIDAVIT,
        "AFFIDAVIT OF REAL PROPERTY": DocumentType.AFFIDAVIT,
        "POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,
        "POA": DocumentType.POWER_OF_ATTORNEY,
        "REVOCATION OF POWER OF ATTORNEY": DocumentType.REVOCATION_OF_POA,
        "MARRIAGE LICENSE": DocumentType.MARRIAGE_LICENSE,
        "CERTIFICATE OF MARRIAGE": DocumentType.MARRIAGE_CERTIFICATE,
        "DD-214": DocumentType.DD214,
        "DD214": DocumentType.DD214,
        "MILITARY DISCHARGE": DocumentType.MILITARY_DISCHARGE,
    }

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the King County recorder scraper."""
        super().__init__(session)

    def _parse_doc_type(self, raw_type: str) -> DocumentType:
        """Parse document type string to enum."""
        if not raw_type:
            return DocumentType.UNKNOWN
        raw_type = raw_type.upper().strip()
        if raw_type in self.KING_DOC_TYPES:
            return self.KING_DOC_TYPES[raw_type]
        return self._parse_document_type(raw_type)

    async def search_by_name(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        party_type: str = "both",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        document_types: Optional[List[DocumentType]] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """Search for documents by party name."""
        import time

        start_time = time.time()

        params = {
            "lastName": last_name,
            "limit": min(max_results, 100),
            "partyType": party_type,
        }
        if first_name:
            params["firstName"] = first_name
        if start_date:
            params["startDate"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["endDate"] = end_date.strftime("%Y-%m-%d")
        if document_types:
            params["docTypes"] = ",".join([dt.value for dt in document_types])

        try:
            json_response = await self._fetch_json(
                f"{self.API_URL}/name", params=params
            )
        except Exception as e:
            logger.error(f"King County name search failed: {e}")
            return SearchResult(
                documents=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(
                    last_name=last_name, first_name=first_name
                ),
                warnings=[str(e)],
            )

        documents = []
        for item in json_response.get("results", [])[:max_results]:
            doc = self._parse_document_result(item)
            if doc:
                documents.append(doc)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            documents=documents,
            total_count=json_response.get("total", len(documents)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=SearchCriteria(last_name=last_name, first_name=first_name),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def search_by_document_number(
        self, document_number: str
    ) -> Optional[RecordedDocument]:
        """Search for a specific document by recording number."""
        try:
            json_response = await self._fetch_json(
                f"{self.DETAIL_URL}/{document_number}"
            )
            if json_response.get("document"):
                return self._parse_document_detail(json_response["document"])
        except Exception as e:
            logger.error(f"King County document search failed: {e}")
        return None

    async def search_by_parcel(
        self,
        parcel_number: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        document_types: Optional[List[DocumentType]] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """Search for documents by parcel number (tax account number)."""
        import time

        start_time = time.time()

        # King County uses 10-digit parcel numbers
        # Format: XXXXXXXXXX (no separators)
        clean_parcel = re.sub(r"[^0-9]", "", parcel_number)

        params = {
            "parcelNumber": clean_parcel,
            "limit": min(max_results, 100),
        }
        if start_date:
            params["startDate"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["endDate"] = end_date.strftime("%Y-%m-%d")
        if document_types:
            params["docTypes"] = ",".join([dt.value for dt in document_types])

        try:
            json_response = await self._fetch_json(
                f"{self.API_URL}/parcel", params=params
            )
        except Exception as e:
            logger.error(f"King County parcel search failed: {e}")
            return SearchResult(
                documents=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(parcel_number=parcel_number),
                warnings=[str(e)],
            )

        documents = []
        for item in json_response.get("results", [])[:max_results]:
            doc = self._parse_document_result(item)
            if doc:
                documents.append(doc)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            documents=documents,
            total_count=json_response.get("total", len(documents)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=SearchCriteria(parcel_number=parcel_number),
            search_time_ms=search_time,
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
        """Search for documents by property address."""
        import time

        start_time = time.time()

        params = {
            "address": address,
            "limit": min(max_results, 100),
        }
        if city:
            params["city"] = city
        if zip_code:
            params["zip"] = zip_code
        if start_date:
            params["startDate"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["endDate"] = end_date.strftime("%Y-%m-%d")

        try:
            json_response = await self._fetch_json(
                f"{self.API_URL}/address", params=params
            )
        except Exception as e:
            logger.error(f"King County address search failed: {e}")
            return SearchResult(
                documents=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(property_address=address),
                warnings=[str(e)],
            )

        documents = []
        for item in json_response.get("results", [])[:max_results]:
            doc = self._parse_document_result(item)
            if doc:
                documents.append(doc)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            documents=documents,
            total_count=json_response.get("total", len(documents)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=SearchCriteria(property_address=address),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_document_detail(
        self, document_number: str
    ) -> Optional[RecordedDocument]:
        """Get full document details by recording number."""
        try:
            json_response = await self._fetch_json(
                f"{self.DETAIL_URL}/{document_number}", params={"include": "all"}
            )
            if json_response.get("document"):
                return self._parse_document_detail(json_response["document"])
        except Exception as e:
            logger.error(f"King County document detail failed: {e}")
        return None

    def _parse_document_result(
        self, data: Dict[str, Any]
    ) -> Optional[RecordedDocument]:
        """Parse a search result into RecordedDocument."""
        rec_number = data.get("recordingNumber", data.get("instrumentNumber", ""))
        if not rec_number:
            return None

        parties = []
        grantors = []
        grantees = []

        for grantor in data.get("grantors", []):
            name = grantor if isinstance(grantor, str) else grantor.get("name", "")
            if name:
                grantors.append(self._normalize_name(name))
                parties.append(
                    DocumentParty(
                        name=self._normalize_name(name),
                        role=PartyRole.GRANTOR,
                    )
                )

        for grantee in data.get("grantees", []):
            name = grantee if isinstance(grantee, str) else grantee.get("name", "")
            if name:
                grantees.append(self._normalize_name(name))
                parties.append(
                    DocumentParty(
                        name=self._normalize_name(name),
                        role=PartyRole.GRANTEE,
                    )
                )

        legal_descriptions = []
        for legal in data.get("legalDescriptions", []):
            if isinstance(legal, str):
                legal_descriptions.append(LegalDescription(full_description=legal))
            elif isinstance(legal, dict):
                legal_descriptions.append(
                    LegalDescription(
                        full_description=legal.get("description", ""),
                        parcel_number=legal.get("parcelNumber"),
                        lot=legal.get("lot"),
                        block=legal.get("block"),
                        subdivision=legal.get("subdivision"),
                        section=legal.get("section"),
                        township=legal.get("township"),
                        range=legal.get("range"),
                    )
                )

        parcels = data.get("parcelNumbers", [])
        if isinstance(parcels, str):
            parcels = [parcels]

        # Washington REET (Real Estate Excise Tax) instead of transfer tax
        reet_amount = self._parse_float(data.get("reet", data.get("exciseTax")))

        return RecordedDocument(
            document_number=rec_number,
            instrument_number=data.get("instrumentNumber"),
            book=data.get("volume"),
            page=data.get("page"),
            document_type=self._parse_doc_type(data.get("documentType", "")),
            document_type_raw=data.get("documentType"),
            recorded_date=self._parse_date(data.get("recordedDate")),
            parties=parties,
            grantors=grantors,
            grantees=grantees,
            legal_descriptions=legal_descriptions,
            parcels=parcels,
            consideration=self._parse_float(
                data.get("consideration", data.get("salePrice"))
            ),
            transfer_tax=reet_amount,
            county=self.COUNTY_NAME,
            state=self.STATE_ABBREV,
            fips_code=self.FIPS_CODE,
            source_url=f"{self.BASE_URL}document/{rec_number}",
            raw_data=data,
        )

    def _parse_document_detail(self, data: Dict[str, Any]) -> RecordedDocument:
        """Parse full document details."""
        doc = self._parse_document_result(data)
        if not doc:
            doc = RecordedDocument(
                document_number=data.get("recordingNumber", ""),
                county=self.COUNTY_NAME,
                state=self.STATE_ABBREV,
            )

        doc.execution_date = self._parse_date(data.get("executionDate"))
        doc.page_count = data.get("pageCount")
        doc.image_available = data.get("imageAvailable", False)
        doc.image_url = data.get("imageUrl")
        doc.case_number = data.get("caseNumber")

        # Property addresses
        addresses = data.get("propertyAddresses", [])
        if addresses:
            doc.property_addresses = (
                addresses if isinstance(addresses, list) else [addresses]
            )

        # Related documents
        for ref in data.get("references", []):
            if ref:
                doc.related_documents.append(str(ref))

        return doc

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse a date string to date object."""
        if not date_str:
            return None
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"]:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse a float value."""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                value = value.replace("$", "").replace(",", "")
            return float(value)
        except (ValueError, TypeError):
            return None


# Synchronous convenience functions


def search_king_county_by_name(
    last_name: str, first_name: Optional[str] = None, max_results: int = 100
) -> SearchResult:
    """Search King County recorded documents by name."""

    async def _search():
        async with KingCountyRecorder() as recorder:
            return await recorder.search_by_name(
                last_name, first_name=first_name, max_results=max_results
            )

    return asyncio.run(_search())


def search_king_county_by_parcel(
    parcel_number: str, max_results: int = 100
) -> SearchResult:
    """Search King County recorded documents by parcel number."""

    async def _search():
        async with KingCountyRecorder() as recorder:
            return await recorder.search_by_parcel(
                parcel_number, max_results=max_results
            )

    return asyncio.run(_search())


def search_king_county_by_address(
    address: str, city: Optional[str] = None, max_results: int = 100
) -> SearchResult:
    """Search King County recorded documents by address."""

    async def _search():
        async with KingCountyRecorder() as recorder:
            return await recorder.search_by_address(
                address, city=city, max_results=max_results
            )

    return asyncio.run(_search())


def get_king_county_document(document_number: str) -> Optional[RecordedDocument]:
    """Get a specific King County recorded document."""

    async def _get():
        async with KingCountyRecorder() as recorder:
            return await recorder.get_document_detail(document_number)

    return asyncio.run(_get())
