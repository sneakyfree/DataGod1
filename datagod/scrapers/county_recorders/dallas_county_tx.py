"""
Dallas County, Texas Recorder Scraper

Dallas County (2.6M population) maintains recorded documents through
the County Clerk's Office.

System: Custom web application
URL: https://www.dallascounty.org/county-clerk/
FIPS: 48113

Available searches:
- Name search (grantor/grantee)
- Document number search
- Volume/Page search
- Recording date range
- Property ID search

Texas uses Warranty Deeds (General and Special) as standard.
No state transfer tax, but some documents have filing fees.
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


class DallasCountyRecorder(CountyRecorderBase):
    """
    Scraper for Dallas County, Texas County Clerk (Recorder).

    Dallas County provides online access to recorded documents.
    Records are indexed by volume and page or document number.
    """

    COUNTY_NAME = "Dallas County"
    STATE = "Texas"
    STATE_ABBREV = "TX"
    FIPS_CODE = "48113"

    BASE_URL = "https://www.dallascounty.org/county-clerk/"
    SEARCH_URL = "https://www.dallascounty.org/county-clerk/api/records/search"
    DETAIL_URL = "https://www.dallascounty.org/county-clerk/api/records/document"
    SYSTEM_NAME = "Dallas County Clerk Records"

    REQUEST_DELAY = 1.5
    MAX_RETRIES = 3
    TIMEOUT = 45

    REQUIRES_LOGIN = False
    REQUIRES_CAPTCHA = False

    # Document type mappings for Dallas County
    DALLAS_DOC_TYPES = {
        "GENERAL WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "GWD": DocumentType.WARRANTY_DEED,
        "WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "WD": DocumentType.WARRANTY_DEED,
        "SPECIAL WARRANTY DEED": DocumentType.SPECIAL_WARRANTY_DEED,
        "SWD": DocumentType.SPECIAL_WARRANTY_DEED,
        "QUITCLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "QCD": DocumentType.QUITCLAIM_DEED,
        "DEED WITHOUT WARRANTY": DocumentType.QUITCLAIM_DEED,
        "TRUSTEE'S DEED": DocumentType.TRUSTEES_DEED,
        "TRUSTEES DEED": DocumentType.TRUSTEES_DEED,
        "SUBSTITUTE TRUSTEE'S DEED": DocumentType.TRUSTEES_DEED_UPON_SALE,
        "DEED OF TRUST": DocumentType.DEED_OF_TRUST,
        "DOT": DocumentType.DEED_OF_TRUST,
        "TRUST DEED": DocumentType.DEED_OF_TRUST,
        "RELEASE OF LIEN": DocumentType.MORTGAGE_RELEASE,
        "RELEASE": DocumentType.MORTGAGE_RELEASE,
        "RELEASE OF DEED OF TRUST": DocumentType.MORTGAGE_RELEASE,
        "ASSIGNMENT OF DEED OF TRUST": DocumentType.MORTGAGE_ASSIGNMENT,
        "ASSIGNMENT": DocumentType.MORTGAGE_ASSIGNMENT,
        "MODIFICATION": DocumentType.MORTGAGE_MODIFICATION,
        "NOTICE OF DEFAULT": DocumentType.NOTICE_OF_DEFAULT,
        "NOTICE OF SUBSTITUTE TRUSTEE SALE": DocumentType.NOTICE_OF_SALE,
        "NOTICE OF FORECLOSURE SALE": DocumentType.NOTICE_OF_SALE,
        "LIS PENDENS": DocumentType.LIS_PENDENS,
        "MECHANICS LIEN": DocumentType.MECHANICS_LIEN,
        "MECHANIC'S LIEN": DocumentType.MECHANICS_LIEN,
        "MATERIALMAN'S LIEN": DocumentType.MECHANICS_LIEN,
        "ABSTRACT OF JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "JUDGMENT LIEN": DocumentType.JUDGMENT_LIEN,
        "FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "NOTICE OF FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "STATE TAX LIEN": DocumentType.TAX_LIEN_STATE,
        "RELEASE OF TAX LIEN": DocumentType.TAX_LIEN_RELEASE,
        "UCC-1": DocumentType.UCC_FINANCING,
        "UCC FINANCING STATEMENT": DocumentType.UCC_FINANCING,
        "UCC-3": DocumentType.UCC_AMENDMENT,
        "EASEMENT": DocumentType.EASEMENT,
        "RESTRICTION": DocumentType.RESTRICTIVE_COVENANT,
        "RESTRICTIVE COVENANT": DocumentType.RESTRICTIVE_COVENANT,
        "PLAT": DocumentType.PLAT_MAP,
        "AFFIDAVIT": DocumentType.AFFIDAVIT,
        "AFFIDAVIT OF HEIRSHIP": DocumentType.AFFIDAVIT,
        "POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,
        "ASSUMED NAME": DocumentType.FICTITIOUS_BUSINESS_NAME,
        "DBA": DocumentType.FICTITIOUS_BUSINESS_NAME,
    }

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the Dallas County recorder scraper."""
        super().__init__(session)

    def _parse_doc_type(self, raw_type: str) -> DocumentType:
        """Parse document type string to enum."""
        if not raw_type:
            return DocumentType.UNKNOWN
        raw_type = raw_type.upper().strip()
        if raw_type in self.DALLAS_DOC_TYPES:
            return self.DALLAS_DOC_TYPES[raw_type]
        return self._parse_document_type(raw_type)

    async def search_by_name(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        party_type: str = "both",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
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

        try:
            json_response = await self._fetch_json(self.SEARCH_URL, params=params)
        except Exception as e:
            logger.error(f"Dallas County name search failed: {e}")
            return SearchResult(
                documents=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(last_name=last_name, first_name=first_name),
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
        self,
        document_number: str
    ) -> Optional[RecordedDocument]:
        """Search for a specific document by document number."""
        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL,
                params={"docNumber": document_number}
            )
            if json_response.get("document"):
                return self._parse_document_detail(json_response["document"])
        except Exception as e:
            logger.error(f"Dallas County document search failed: {e}")
        return None

    async def search_by_volume_page(
        self,
        volume: str,
        page: str
    ) -> Optional[RecordedDocument]:
        """Search for a document by volume and page."""
        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL,
                params={"volume": volume, "page": page}
            )
            if json_response.get("document"):
                return self._parse_document_detail(json_response["document"])
        except Exception as e:
            logger.error(f"Dallas County volume/page search failed: {e}")
        return None

    async def search_by_property_id(
        self,
        property_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search for documents by property ID."""
        import time
        start_time = time.time()

        params = {
            "propertyId": property_id,
            "limit": min(max_results, 100),
        }
        if start_date:
            params["startDate"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["endDate"] = end_date.strftime("%Y-%m-%d")

        try:
            json_response = await self._fetch_json(self.SEARCH_URL, params=params)
        except Exception as e:
            logger.error(f"Dallas County property search failed: {e}")
            return SearchResult(
                documents=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(parcel_number=property_id),
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
            search_criteria=SearchCriteria(parcel_number=property_id),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_document(self, document_number: str) -> Optional[RecordedDocument]:
        """Get full document details by document number."""
        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL,
                params={"docNumber": document_number, "include": "all"}
            )
            if json_response.get("document"):
                return self._parse_document_detail(json_response["document"])
        except Exception as e:
            logger.error(f"Dallas County document detail failed: {e}")
        return None

    def _parse_document_result(self, data: Dict[str, Any]) -> Optional[RecordedDocument]:
        """Parse a search result into RecordedDocument."""
        doc_number = data.get("documentNumber", data.get("docNumber", ""))
        if not doc_number:
            return None

        parties = []
        grantors = []
        grantees = []

        for grantor in data.get("grantors", []):
            name = grantor if isinstance(grantor, str) else grantor.get("name", "")
            if name:
                grantors.append(self._normalize_name(name))
                parties.append(DocumentParty(
                    name=self._normalize_name(name),
                    role=PartyRole.GRANTOR,
                ))

        for grantee in data.get("grantees", []):
            name = grantee if isinstance(grantee, str) else grantee.get("name", "")
            if name:
                grantees.append(self._normalize_name(name))
                parties.append(DocumentParty(
                    name=self._normalize_name(name),
                    role=PartyRole.GRANTEE,
                ))

        legal_descriptions = []
        for legal in data.get("legalDescriptions", []):
            if isinstance(legal, str):
                legal_descriptions.append(LegalDescription(full_description=legal))
            elif isinstance(legal, dict):
                legal_descriptions.append(LegalDescription(
                    full_description=legal.get("description", ""),
                    lot=legal.get("lot"),
                    block=legal.get("block"),
                    subdivision=legal.get("subdivision"),
                ))

        return RecordedDocument(
            document_number=doc_number,
            book=data.get("volume"),
            page=data.get("page"),
            document_type=self._parse_doc_type(data.get("documentType", "")),
            document_type_raw=data.get("documentType"),
            recorded_date=self._parse_date(data.get("recordedDate")),
            parties=parties,
            grantors=grantors,
            grantees=grantees,
            legal_descriptions=legal_descriptions,
            consideration=self._parse_float(data.get("consideration")),
            county=self.COUNTY_NAME,
            state=self.STATE_ABBREV,
            fips_code=self.FIPS_CODE,
            source_url=f"{self.BASE_URL}records/{doc_number}",
            raw_data=data,
        )

    def _parse_document_detail(self, data: Dict[str, Any]) -> RecordedDocument:
        """Parse full document details."""
        doc = self._parse_document_result(data)
        if not doc:
            doc = RecordedDocument(
                document_number=data.get("documentNumber", ""),
                county=self.COUNTY_NAME,
                state=self.STATE_ABBREV,
            )

        doc.execution_date = self._parse_date(data.get("executionDate"))
        doc.page_count = data.get("pageCount")
        doc.image_available = data.get("imageAvailable", False)
        doc.image_url = data.get("imageUrl")
        doc.case_number = data.get("caseNumber")

        # Add related documents
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

def search_dallas_county_by_name(
    last_name: str,
    first_name: Optional[str] = None,
    max_results: int = 100
) -> SearchResult:
    """Search Dallas County recorded documents by name."""
    async def _search():
        async with DallasCountyRecorder() as recorder:
            return await recorder.search_by_name(
                last_name, first_name=first_name, max_results=max_results
            )
    return asyncio.run(_search())


def search_dallas_county_by_property(
    property_id: str,
    max_results: int = 100
) -> SearchResult:
    """Search Dallas County recorded documents by property ID."""
    async def _search():
        async with DallasCountyRecorder() as recorder:
            return await recorder.search_by_property_id(property_id, max_results=max_results)
    return asyncio.run(_search())


def get_dallas_county_document(document_number: str) -> Optional[RecordedDocument]:
    """Get a specific Dallas County recorded document."""
    async def _get():
        async with DallasCountyRecorder() as recorder:
            return await recorder.get_document(document_number)
    return asyncio.run(_get())
