"""
LexisNexis API Integration

LexisNexis provides comprehensive people search, business reports,
court records, and public records data.

This module provides access to:
- People search (comprehensive background)
- Business reports (Dun & Bradstreet data)
- Court records (civil, criminal, bankruptcy)
- Asset searches (property, vehicles, aircraft)
- News archives
- Professional licenses

Pricing: ~$10,000+/year (enterprise pricing, volume-based)
API Documentation: Requires enterprise agreement for access.

Note: LexisNexis requires strict compliance with FCRA, GLBA, and DPPA
regulations. Usage is restricted to permissible purposes.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PermissiblePurpose(Enum):
    """FCRA permissible purposes for data access"""

    CREDIT = "credit"  # Credit decisions
    EMPLOYMENT = "employment"  # Employment screening
    INSURANCE = "insurance"  # Insurance underwriting
    TENANT_SCREENING = "tenant_screening"  # Rental applications
    LEGITIMATE_BUSINESS = "legitimate_business"  # Business transactions
    COURT_ORDER = "court_order"  # Court-ordered disclosure
    CONSUMER_CONSENT = "consumer_consent"  # Written consumer consent
    ACCOUNT_REVIEW = "account_review"  # Existing account review


class RecordType(Enum):
    """Types of records available"""

    PERSON = "person"
    BUSINESS = "business"
    PROPERTY = "property"
    VEHICLE = "vehicle"
    COURT_CASE = "court_case"
    BANKRUPTCY = "bankruptcy"
    LIEN_JUDGMENT = "lien_judgment"
    UCC = "ucc"
    PROFESSIONAL_LICENSE = "professional_license"
    CORPORATION = "corporation"


@dataclass
class PersonRecord:
    """Person search result from LexisNexis"""

    lexis_id: str

    # Name
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    suffix: Optional[str] = None
    aliases: List[str] = field(default_factory=list)

    # Demographics
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    deceased: bool = False
    date_of_death: Optional[date] = None

    # SSN (masked for compliance)
    ssn_last_four: Optional[str] = None

    # Current address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None

    # Address history
    address_history: List[Dict[str, Any]] = field(default_factory=list)

    # Phone numbers
    phones: List[str] = field(default_factory=list)

    # Email addresses
    emails: List[str] = field(default_factory=list)

    # Relatives/associates
    relatives: List[Dict[str, Any]] = field(default_factory=list)
    associates: List[Dict[str, Any]] = field(default_factory=list)

    # Employment history
    employers: List[Dict[str, Any]] = field(default_factory=list)

    # Properties owned
    properties: List[Dict[str, Any]] = field(default_factory=list)

    # Vehicles registered
    vehicles: List[Dict[str, Any]] = field(default_factory=list)

    # Professional licenses
    licenses: List[Dict[str, Any]] = field(default_factory=list)

    # Bankruptcies
    bankruptcies: List[Dict[str, Any]] = field(default_factory=list)

    # Liens and judgments
    liens_judgments: List[Dict[str, Any]] = field(default_factory=list)

    # Criminal records (if permissible)
    criminal_records: List[Dict[str, Any]] = field(default_factory=list)

    # Confidence score
    match_score: Optional[float] = None

    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lexis_id": self.lexis_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "middle_name": self.middle_name,
            "aliases": self.aliases,
            "date_of_birth": (
                self.date_of_birth.isoformat() if self.date_of_birth else None
            ),
            "age": self.age,
            "deceased": self.deceased,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "phones": self.phones,
            "emails": self.emails,
            "address_history_count": len(self.address_history),
            "relatives_count": len(self.relatives),
            "properties_count": len(self.properties),
            "bankruptcies_count": len(self.bankruptcies),
            "liens_judgments_count": len(self.liens_judgments),
            "match_score": self.match_score,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class BusinessRecord:
    """Business report from LexisNexis"""

    lexis_id: str
    business_name: str

    # DBA names
    dba_names: List[str] = field(default_factory=list)

    # Identifiers
    duns_number: Optional[str] = None
    ein: Optional[str] = None

    # Business type
    business_type: Optional[str] = None
    incorporation_state: Optional[str] = None
    incorporation_date: Optional[date] = None

    # Status
    status: Optional[str] = None

    # Address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    # Contact
    phone: Optional[str] = None
    website: Optional[str] = None

    # Size
    employee_count: Optional[int] = None
    employee_count_range: Optional[str] = None
    annual_revenue: Optional[float] = None
    annual_revenue_range: Optional[str] = None

    # Industry
    sic_code: Optional[str] = None
    sic_description: Optional[str] = None
    naics_code: Optional[str] = None
    naics_description: Optional[str] = None

    # Officers/principals
    officers: List[Dict[str, Any]] = field(default_factory=list)

    # Registered agent
    registered_agent: Optional[str] = None
    registered_agent_address: Optional[str] = None

    # Parent/subsidiaries
    parent_company: Optional[Dict[str, Any]] = None
    subsidiaries: List[Dict[str, Any]] = field(default_factory=list)

    # Filings
    ucc_filings: List[Dict[str, Any]] = field(default_factory=list)
    liens_judgments: List[Dict[str, Any]] = field(default_factory=list)
    bankruptcies: List[Dict[str, Any]] = field(default_factory=list)

    # Credit indicators (if available)
    paydex_score: Optional[int] = None
    credit_risk_class: Optional[str] = None

    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lexis_id": self.lexis_id,
            "business_name": self.business_name,
            "dba_names": self.dba_names,
            "duns_number": self.duns_number,
            "ein": self.ein,
            "business_type": self.business_type,
            "status": self.status,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "employee_count": self.employee_count,
            "annual_revenue": self.annual_revenue,
            "sic_code": self.sic_code,
            "sic_description": self.sic_description,
            "officers_count": len(self.officers),
            "ucc_filings_count": len(self.ucc_filings),
            "liens_judgments_count": len(self.liens_judgments),
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class CourtRecord:
    """Court record from LexisNexis"""

    lexis_id: str
    case_number: str
    case_type: str  # civil, criminal, bankruptcy, etc.

    # Court info
    court_name: str
    court_state: str
    court_county: Optional[str] = None

    # Dates
    filing_date: Optional[date] = None
    disposition_date: Optional[date] = None

    # Case details
    case_title: Optional[str] = None
    case_status: Optional[str] = None
    disposition: Optional[str] = None

    # Parties
    plaintiffs: List[Dict[str, Any]] = field(default_factory=list)
    defendants: List[Dict[str, Any]] = field(default_factory=list)
    other_parties: List[Dict[str, Any]] = field(default_factory=list)

    # Attorneys
    attorneys: List[Dict[str, Any]] = field(default_factory=list)

    # Judge
    judge_name: Optional[str] = None

    # Financial
    amount_claimed: Optional[float] = None
    amount_awarded: Optional[float] = None

    # Documents
    docket_entries: List[Dict[str, Any]] = field(default_factory=list)

    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lexis_id": self.lexis_id,
            "case_number": self.case_number,
            "case_type": self.case_type,
            "court_name": self.court_name,
            "court_state": self.court_state,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "case_title": self.case_title,
            "case_status": self.case_status,
            "disposition": self.disposition,
            "plaintiffs_count": len(self.plaintiffs),
            "defendants_count": len(self.defendants),
            "amount_claimed": self.amount_claimed,
            "amount_awarded": self.amount_awarded,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class AssetRecord:
    """Asset (property, vehicle, aircraft) record"""

    lexis_id: str
    asset_type: str  # property, vehicle, aircraft, watercraft

    # Owner
    owner_name: str
    owner_lexis_id: Optional[str] = None

    # Property-specific
    property_address: Optional[str] = None
    property_city: Optional[str] = None
    property_state: Optional[str] = None
    property_type: Optional[str] = None
    assessed_value: Optional[float] = None
    sale_price: Optional[float] = None
    sale_date: Optional[date] = None

    # Vehicle-specific
    vin: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    license_plate: Optional[str] = None
    license_state: Optional[str] = None

    # Aircraft-specific
    tail_number: Optional[str] = None
    aircraft_type: Optional[str] = None
    manufacturer: Optional[str] = None

    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lexis_id": self.lexis_id,
            "asset_type": self.asset_type,
            "owner_name": self.owner_name,
            "property_address": self.property_address,
            "property_state": self.property_state,
            "assessed_value": self.assessed_value,
            "vin": self.vin,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "tail_number": self.tail_number,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class PersonSearch:
    """Search parameters for person lookup"""

    # Name
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None

    # Identifiers
    ssn: Optional[str] = None  # Full or last 4
    date_of_birth: Optional[date] = None

    # Address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    # Phone/email
    phone: Optional[str] = None
    email: Optional[str] = None

    # Options
    include_address_history: bool = True
    include_relatives: bool = False
    include_associates: bool = False
    include_properties: bool = False
    include_vehicles: bool = False
    include_court_records: bool = False
    include_bankruptcies: bool = False

    # Permissible purpose (REQUIRED)
    permissible_purpose: PermissiblePurpose = PermissiblePurpose.LEGITIMATE_BUSINESS


@dataclass
class BusinessSearch:
    """Search parameters for business lookup"""

    # Name
    business_name: Optional[str] = None
    dba_name: Optional[str] = None

    # Identifiers
    duns_number: Optional[str] = None
    ein: Optional[str] = None

    # Location
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    # Industry
    sic_code: Optional[str] = None
    naics_code: Optional[str] = None

    # Options
    include_officers: bool = True
    include_filings: bool = True
    include_credit: bool = False


class LexisNexisAPI(ABC):
    """
    Abstract base class for LexisNexis API integration.

    LexisNexis provides comprehensive public records data including:
    - People search (SSN trace, address history, relatives)
    - Business reports (D&B data, officers, filings)
    - Court records (civil, criminal, bankruptcy)
    - Asset searches (property, vehicles, aircraft)
    - Professional licenses
    - News archives

    IMPORTANT: Usage requires compliance with FCRA, GLBA, DPPA.
    All searches must have a valid permissible purpose.

    API requires enterprise agreement for credentials.
    """

    BASE_URL = "https://risk.lexisnexis.com/api/v1"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        customer_id: str,
        config: Dict[str, Any] = None,
    ):
        """
        Initialize LexisNexis API client.

        Args:
            api_key: LexisNexis API key
            api_secret: LexisNexis API secret
            customer_id: LexisNexis customer ID
            config: Optional configuration dictionary
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.customer_id = customer_id
        self.config = config or {}
        self._access_token = None
        self._token_expires = None

        logger.info("Initialized LexisNexisAPI")

    @abstractmethod
    def search_person(self, search: PersonSearch) -> List[PersonRecord]:
        """
        Search for a person.

        COMPLIANCE NOTE: Requires valid permissible purpose.
        Results may be limited based on access level.

        Args:
            search: PersonSearch parameters

        Returns:
            List of PersonRecord objects
        """
        pass

    @abstractmethod
    def get_person_report(
        self, lexis_id: str, purpose: PermissiblePurpose
    ) -> Optional[PersonRecord]:
        """
        Get comprehensive person report.

        Args:
            lexis_id: LexisNexis person ID
            purpose: Permissible purpose for the lookup

        Returns:
            PersonRecord with full details or None
        """
        pass

    @abstractmethod
    def search_business(self, search: BusinessSearch) -> List[BusinessRecord]:
        """
        Search for a business.

        Args:
            search: BusinessSearch parameters

        Returns:
            List of BusinessRecord objects
        """
        pass

    @abstractmethod
    def get_business_report(self, lexis_id: str) -> Optional[BusinessRecord]:
        """
        Get comprehensive business report.

        Args:
            lexis_id: LexisNexis business ID

        Returns:
            BusinessRecord with full details or None
        """
        pass

    @abstractmethod
    def search_court_records(
        self,
        party_name: str,
        state: str = None,
        case_type: str = None,
        date_from: date = None,
        date_to: date = None,
    ) -> List[CourtRecord]:
        """
        Search court records by party name.

        Args:
            party_name: Name of party to search
            state: State filter
            case_type: Case type filter
            date_from: Start date filter
            date_to: End date filter

        Returns:
            List of CourtRecord objects
        """
        pass

    @abstractmethod
    def get_court_case(self, lexis_id: str) -> Optional[CourtRecord]:
        """
        Get court case details.

        Args:
            lexis_id: LexisNexis court case ID

        Returns:
            CourtRecord or None
        """
        pass

    @abstractmethod
    def search_assets(
        self, owner_name: str, asset_type: str = None, state: str = None
    ) -> List[AssetRecord]:
        """
        Search for assets by owner name.

        Args:
            owner_name: Owner name to search
            asset_type: Type filter (property, vehicle, aircraft)
            state: State filter

        Returns:
            List of AssetRecord objects
        """
        pass

    @abstractmethod
    def search_bankruptcies(
        self,
        party_name: str,
        state: str = None,
        date_from: date = None,
        date_to: date = None,
    ) -> List[CourtRecord]:
        """
        Search bankruptcy records.

        Args:
            party_name: Debtor name to search
            state: State filter
            date_from: Start date filter
            date_to: End date filter

        Returns:
            List of CourtRecord objects (bankruptcy type)
        """
        pass

    @abstractmethod
    def search_liens_judgments(
        self,
        party_name: str,
        state: str = None,
        date_from: date = None,
        date_to: date = None,
    ) -> List[Dict[str, Any]]:
        """
        Search liens and judgments.

        Args:
            party_name: Party name to search
            state: State filter
            date_from: Start date filter
            date_to: End date filter

        Returns:
            List of lien/judgment records
        """
        pass

    def validate_permissible_purpose(self, purpose: PermissiblePurpose) -> bool:
        """
        Validate that a permissible purpose is provided.

        All person searches require a valid FCRA permissible purpose.
        """
        if purpose is None:
            raise ValueError("Permissible purpose is required for person searches")
        return True


class LexisNexisAPIClient(LexisNexisAPI):
    """
    Concrete implementation of LexisNexis API client.

    Note: This is a placeholder implementation. Actual API calls
    require valid LexisNexis enterprise credentials.
    """

    def search_person(self, search: PersonSearch) -> List[PersonRecord]:
        """Search for a person."""
        self.validate_permissible_purpose(search.permissible_purpose)
        logger.info(
            f"Searching LexisNexis person: {search.first_name} {search.last_name}"
        )
        return []

    def get_person_report(
        self, lexis_id: str, purpose: PermissiblePurpose
    ) -> Optional[PersonRecord]:
        """Get comprehensive person report."""
        self.validate_permissible_purpose(purpose)
        logger.info(f"Getting LexisNexis person report: {lexis_id}")
        return None

    def search_business(self, search: BusinessSearch) -> List[BusinessRecord]:
        """Search for a business."""
        logger.info(f"Searching LexisNexis business: {search.business_name}")
        return []

    def get_business_report(self, lexis_id: str) -> Optional[BusinessRecord]:
        """Get comprehensive business report."""
        logger.info(f"Getting LexisNexis business report: {lexis_id}")
        return None

    def search_court_records(
        self,
        party_name: str,
        state: str = None,
        case_type: str = None,
        date_from: date = None,
        date_to: date = None,
    ) -> List[CourtRecord]:
        """Search court records by party name."""
        logger.info(f"Searching LexisNexis court records: {party_name}")
        return []

    def get_court_case(self, lexis_id: str) -> Optional[CourtRecord]:
        """Get court case details."""
        logger.info(f"Getting LexisNexis court case: {lexis_id}")
        return None

    def search_assets(
        self, owner_name: str, asset_type: str = None, state: str = None
    ) -> List[AssetRecord]:
        """Search for assets by owner name."""
        logger.info(f"Searching LexisNexis assets: {owner_name}")
        return []

    def search_bankruptcies(
        self,
        party_name: str,
        state: str = None,
        date_from: date = None,
        date_to: date = None,
    ) -> List[CourtRecord]:
        """Search bankruptcy records."""
        logger.info(f"Searching LexisNexis bankruptcies: {party_name}")
        return []

    def search_liens_judgments(
        self,
        party_name: str,
        state: str = None,
        date_from: date = None,
        date_to: date = None,
    ) -> List[Dict[str, Any]]:
        """Search liens and judgments."""
        logger.info(f"Searching LexisNexis liens/judgments: {party_name}")
        return []


# Factory function
def create_lexisnexis_client(
    api_key: str, api_secret: str, customer_id: str, config: Dict[str, Any] = None
) -> LexisNexisAPIClient:
    """Create a LexisNexis API client instance."""
    return LexisNexisAPIClient(
        api_key=api_key, api_secret=api_secret, customer_id=customer_id, config=config
    )
