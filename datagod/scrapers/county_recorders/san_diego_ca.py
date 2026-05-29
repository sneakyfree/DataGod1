"""
San Diego County, California Recorder Scraper

San Diego County (3.3M population) maintains recorded documents through
the Assessor/Recorder/County Clerk (ARCC) office.

System: Custom web application
URL: https://arcc.sdcounty.ca.gov/
FIPS: 06073

Available searches:
- Name search (grantor/grantee)
- Document number search
- APN (Assessor's Parcel Number) search
- Book/Page search
- Recording date range

California uses Grant Deeds as the standard deed type.
Transfer tax is $1.10 per $1,000 of sale price.
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


class SanDiegoCountyRecorder(CountyRecorderBase):
    """
    Scraper for San Diego County, California Recorder.

    San Diego County uses the ARCC (Assessor/Recorder/County Clerk) system.
    Records are available online from 1970 to present.
    """

    COUNTY_NAME = "San Diego County"
    STATE = "California"
    STATE_ABBREV = "CA"
    FIPS_CODE = "06073"

    BASE_URL = "https://arcc.sdcounty.ca.gov/"
    SEARCH_URL = "https://arcc.sdcounty.ca.gov/services/recorder/search"
    DETAIL_URL = "https://arcc.sdcounty.ca.gov/services/recorder/document"
    SYSTEM_NAME = "San Diego County ARCC"

    REQUEST_DELAY = 1.5
    MAX_RETRIES = 3
    TIMEOUT = 45

    REQUIRES_LOGIN = False
    REQUIRES_CAPTCHA = False

    # San Diego County APN format: XXX-XXX-XX-XX
    APN_PATTERN = re.compile(r"^\d{3}-\d{3}-\d{2}-\d{2}[A-Z]?$")

    # Document type mappings for San Diego County
    SD_DOC_TYPES = {
        "GRANT DEED": DocumentType.GRANT_DEED,
        "GD": DocumentType.GRANT_DEED,
        "DEED": DocumentType.GRANT_DEED,
        "WARRANTY DEED": DocumentType.WARRANTY_DEED,
        "WD": DocumentType.WARRANTY_DEED,
        "QUITCLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "QCD": DocumentType.QUITCLAIM_DEED,
        "QUIT CLAIM DEED": DocumentType.QUITCLAIM_DEED,
        "TRUSTEE'S DEED": DocumentType.TRUSTEES_DEED,
        "TRUSTEES DEED": DocumentType.TRUSTEES_DEED,
        "TDUS": DocumentType.TRUSTEES_DEED_UPON_SALE,
        "DEED OF TRUST": DocumentType.DEED_OF_TRUST,
        "DOT": DocumentType.DEED_OF_TRUST,
        "TRUST DEED": DocumentType.DEED_OF_TRUST,
        "RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "FULL RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "PARTIAL RECONVEYANCE": DocumentType.MORTGAGE_RELEASE,
        "SUBSTITUTION": DocumentType.MORTGAGE_MODIFICATION,
        "ASSIGNMENT": DocumentType.MORTGAGE_ASSIGNMENT,
        "NOTICE OF DEFAULT": DocumentType.NOTICE_OF_DEFAULT,
        "NOD": DocumentType.NOTICE_OF_DEFAULT,
        "NOTICE OF SALE": DocumentType.NOTICE_OF_SALE,
        "NOS": DocumentType.NOTICE_OF_SALE,
        "LIS PENDENS": DocumentType.LIS_PENDENS,
        "LP": DocumentType.LIS_PENDENS,
        "MECHANICS LIEN": DocumentType.MECHANICS_LIEN,
        "ML": DocumentType.MECHANICS_LIEN,
        "JUDGMENT LIEN": DocumentType.JUDGMENT_LIEN,
        "ABSTRACT OF JUDGMENT": DocumentType.JUDGMENT_LIEN,
        "FEDERAL TAX LIEN": DocumentType.TAX_LIEN_FEDERAL,
        "FTL": DocumentType.TAX_LIEN_FEDERAL,
        "STATE TAX LIEN": DocumentType.TAX_LIEN_STATE,
        "STL": DocumentType.TAX_LIEN_STATE,
        "RELEASE": DocumentType.TAX_LIEN_RELEASE,
        "UCC-1": DocumentType.UCC_FINANCING,
        "UCC FINANCING": DocumentType.UCC_FINANCING,
        "EASEMENT": DocumentType.EASEMENT,
        "CC&R": DocumentType.CC_AND_RS,
        "CC&RS": DocumentType.CC_AND_RS,
        "DECLARATION": DocumentType.DECLARATION,
        "AFFIDAVIT": DocumentType.AFFIDAVIT,
        "POWER OF ATTORNEY": DocumentType.POWER_OF_ATTORNEY,
        "POA": DocumentType.POWER_OF_ATTORNEY,
    }

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the San Diego County recorder scraper."""
        super().__init__(session)

    def _format_apn(self, apn: str) -> str:
        """Format an APN with dashes if not already formatted."""
        clean = apn.replace("-", "").replace(" ", "").replace(".", "").strip()
        suffix = ""
        if clean and clean[-1].isalpha():
            suffix = clean[-1].upper()
            clean = clean[:-1]
        if len(clean) == 10:
            return f"{clean[:3]}-{clean[3:6]}-{clean[6:8]}-{clean[8:10]}{suffix}"
        return apn

    def _parse_doc_type(self, raw_type: str) -> DocumentType:
        """Parse document type string to enum."""
        if not raw_type:
            return DocumentType.UNKNOWN
        raw_type = raw_type.upper().strip()
        if raw_type in self.SD_DOC_TYPES:
            return self.SD_DOC_TYPES[raw_type]
        return self._parse_document_type(raw_type)

    async def search_by_name(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        party_type: str = "both",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
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

        try:
            json_response = await self._fetch_json(self.SEARCH_URL, params=params)
        except Exception as e:
            logger.error(f"San Diego name search failed: {e}")
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
        """Search for a specific document by document number."""
        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL, params={"docNumber": document_number}
            )
            if json_response.get("document"):
                return self._parse_document_detail(json_response["document"])
        except Exception as e:
            logger.error(f"San Diego document search failed: {e}")
        return None

    async def search_by_apn(
        self,
        apn: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """Search for documents by Assessor's Parcel Number."""
        import time

        start_time = time.time()

        formatted_apn = self._format_apn(apn)

        params = {
            "apn": formatted_apn,
            "limit": min(max_results, 100),
        }
        if start_date:
            params["startDate"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["endDate"] = end_date.strftime("%Y-%m-%d")

        try:
            json_response = await self._fetch_json(self.SEARCH_URL, params=params)
        except Exception as e:
            logger.error(f"San Diego APN search failed: {e}")
            return SearchResult(
                documents=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=SearchCriteria(apn=apn),
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
            search_criteria=SearchCriteria(apn=apn),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def search_by_parcel(
        self,
        parcel_number: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        document_types: Optional[List[DocumentType]] = None,
        max_results: int = 100,
    ) -> SearchResult:
        """Search for documents by parcel/APN number."""
        return await self.search_by_apn(
            parcel_number,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
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
            json_response = await self._fetch_json(self.SEARCH_URL, params=params)
        except Exception as e:
            logger.error(f"San Diego address search failed: {e}")
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
        """Get full document details by document number."""
        try:
            json_response = await self._fetch_json(
                self.DETAIL_URL, params={"docNumber": document_number, "include": "all"}
            )
            if json_response.get("document"):
                return self._parse_document_detail(json_response["document"])
        except Exception as e:
            logger.error(f"San Diego document detail failed: {e}")
        return None

    def _parse_document_result(
        self, data: Dict[str, Any]
    ) -> Optional[RecordedDocument]:
        """Parse a search result into RecordedDocument."""
        doc_number = data.get("documentNumber", data.get("docNumber", ""))
        if not doc_number:
            return None

        # Parse parties
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

        # Parse legal descriptions
        legal_descriptions = []
        for apn in data.get("parcels", data.get("apns", [])):
            legal_descriptions.append(
                LegalDescription(
                    full_description="",
                    apn=self._format_apn(apn) if apn else None,
                )
            )

        return RecordedDocument(
            document_number=doc_number,
            document_type=self._parse_doc_type(data.get("documentType", "")),
            document_type_raw=data.get("documentType"),
            recorded_date=self._parse_date(data.get("recordedDate")),
            parties=parties,
            grantors=grantors,
            grantees=grantees,
            legal_descriptions=legal_descriptions,
            parcels=data.get("parcels", data.get("apns", [])),
            consideration=self._parse_float(data.get("consideration")),
            transfer_tax=self._parse_float(data.get("transferTax")),
            county=self.COUNTY_NAME,
            state=self.STATE_ABBREV,
            fips_code=self.FIPS_CODE,
            source_url=f"{self.BASE_URL}document/{doc_number}",
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

        # Add additional details
        doc.book = data.get("book")
        doc.page = data.get("page")
        doc.execution_date = self._parse_date(data.get("executionDate"))
        doc.page_count = data.get("pageCount")
        doc.image_available = data.get("imageAvailable", False)
        doc.image_url = data.get("imageUrl")

        # Parse full legal description
        if data.get("legalDescription"):
            doc.legal_descriptions.append(
                LegalDescription(
                    full_description=data.get("legalDescription", ""),
                    subdivision=data.get("subdivision"),
                    lot=data.get("lot"),
                    block=data.get("block"),
                )
            )

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


def search_san_diego_by_name(
    last_name: str, first_name: Optional[str] = None, max_results: int = 100
) -> SearchResult:
    """Search San Diego County recorded documents by name."""

    async def _search():
        async with SanDiegoCountyRecorder() as recorder:
            return await recorder.search_by_name(
                last_name, first_name=first_name, max_results=max_results
            )

    return asyncio.run(_search())


def search_san_diego_by_apn(apn: str, max_results: int = 100) -> SearchResult:
    """Search San Diego County recorded documents by APN."""

    async def _search():
        async with SanDiegoCountyRecorder() as recorder:
            return await recorder.search_by_apn(apn, max_results=max_results)

    return asyncio.run(_search())


def search_san_diego_by_address(
    address: str, city: Optional[str] = None, max_results: int = 100
) -> SearchResult:
    """Search San Diego County recorded documents by address."""

    async def _search():
        async with SanDiegoCountyRecorder() as recorder:
            return await recorder.search_by_address(
                address, city=city, max_results=max_results
            )

    return asyncio.run(_search())


def get_san_diego_document(document_number: str) -> Optional[RecordedDocument]:
    """Get a specific San Diego County recorded document."""

    async def _get():
        async with SanDiegoCountyRecorder() as recorder:
            return await recorder.get_document_detail(document_number)

    return asyncio.run(_get())
