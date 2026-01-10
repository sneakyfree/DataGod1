"""
Professional Licenses Scraper Module

Provides unified access to professional license records:
- Real estate agents/brokers
- Loan officers (NMLS)
- Attorneys (state bar)
- Contractors
- Healthcare providers

Supports:
- State licensing boards
- NMLS Consumer Access
- State bar associations
- Contractor licensing boards
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class LicenseType(Enum):
    """Types of professional licenses"""
    # Real Estate
    REAL_ESTATE_AGENT = "real_estate_agent"
    REAL_ESTATE_BROKER = "real_estate_broker"
    REAL_ESTATE_APPRAISER = "real_estate_appraiser"

    # Mortgage/Lending
    LOAN_OFFICER = "loan_officer"
    MORTGAGE_BROKER = "mortgage_broker"
    MORTGAGE_LENDER = "mortgage_lender"

    # Legal
    ATTORNEY = "attorney"
    PARALEGAL = "paralegal"
    NOTARY = "notary"

    # Construction
    GENERAL_CONTRACTOR = "general_contractor"
    SPECIALTY_CONTRACTOR = "specialty_contractor"
    ELECTRICIAN = "electrician"
    PLUMBER = "plumber"
    HVAC = "hvac"

    # Healthcare
    PHYSICIAN = "physician"
    NURSE = "nurse"
    DENTIST = "dentist"
    PHARMACIST = "pharmacist"

    # Financial
    CPA = "cpa"
    INSURANCE_AGENT = "insurance_agent"
    INVESTMENT_ADVISOR = "investment_advisor"

    # Other
    OTHER = "other"


class LicenseStatus(Enum):
    """License status values"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    SURRENDERED = "surrendered"
    PENDING = "pending"
    PROBATION = "probation"
    DECEASED = "deceased"
    UNKNOWN = "unknown"


@dataclass
class DisciplinaryAction:
    """Represents a disciplinary action on a license"""
    action_date: date
    action_type: str
    description: Optional[str] = None
    case_number: Optional[str] = None
    effective_date: Optional[date] = None
    end_date: Optional[date] = None
    fine_amount: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'action_date': self.action_date.isoformat(),
            'action_type': self.action_type,
            'description': self.description,
            'case_number': self.case_number,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'fine_amount': self.fine_amount
        }


@dataclass
class Employer:
    """Employer/sponsoring entity information"""
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'phone': self.phone,
            'license_number': self.license_number,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }


@dataclass
class ProfessionalLicense:
    """Represents a professional license record"""
    license_number: str
    license_type: LicenseType
    licensee_name: str
    state: str
    status: LicenseStatus = LicenseStatus.UNKNOWN
    issue_date: Optional[date] = None
    expiration_date: Optional[date] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    employer: Optional[Employer] = None
    specializations: List[str] = field(default_factory=list)
    disciplinary_actions: List[DisciplinaryAction] = field(default_factory=list)
    ce_hours: Optional[int] = None
    nmls_id: Optional[str] = None  # For mortgage professionals
    bar_number: Optional[str] = None  # For attorneys
    npi: Optional[str] = None  # For healthcare providers
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'license_number': self.license_number,
            'license_type': self.license_type.value,
            'licensee_name': self.licensee_name,
            'state': self.state,
            'status': self.status.value,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'address': self.address,
            'city': self.city,
            'zip_code': self.zip_code,
            'phone': self.phone,
            'email': self.email,
            'employer': self.employer.to_dict() if self.employer else None,
            'specializations': self.specializations,
            'disciplinary_actions': [d.to_dict() for d in self.disciplinary_actions],
            'ce_hours': self.ce_hours,
            'nmls_id': self.nmls_id,
            'bar_number': self.bar_number,
            'npi': self.npi,
            'fetched_at': self.fetched_at.isoformat()
        }

    @property
    def is_active(self) -> bool:
        """Check if license is currently active"""
        if self.status != LicenseStatus.ACTIVE:
            return False
        if self.expiration_date and self.expiration_date < date.today():
            return False
        return True

    @property
    def has_disciplinary_history(self) -> bool:
        """Check if licensee has any disciplinary actions"""
        return len(self.disciplinary_actions) > 0


@dataclass
class LicenseSearch:
    """Search parameters for license searches"""
    name: Optional[str] = None
    license_number: Optional[str] = None
    license_type: Optional[LicenseType] = None
    state: Optional[str] = None
    city: Optional[str] = None
    status: Optional[LicenseStatus] = None
    include_inactive: bool = False
    include_disciplined_only: bool = False
    employer_name: Optional[str] = None
    nmls_id: Optional[str] = None
    exact_match: bool = False


class ProfessionalLicensesScraper(ABC):
    """
    Abstract base class for professional license scrapers.

    Provides unified interface for accessing professional license
    records from state licensing boards and national databases.
    """

    def __init__(self, state_code: str = None, config: Dict[str, Any] = None):
        """
        Initialize the professional licenses scraper.

        Args:
            state_code: Two-letter state code (None for national sources)
            config: Optional configuration dictionary
        """
        self.state_code = state_code.upper() if state_code else None
        self.config = config or {}

        logger.info(f"Initialized ProfessionalLicensesScraper for {state_code or 'national'}")

    @abstractmethod
    def search_licenses(self, search: LicenseSearch) -> List[ProfessionalLicense]:
        """
        Search for professional licenses.

        Args:
            search: LicenseSearch parameters

        Returns:
            List of matching ProfessionalLicense objects
        """
        pass

    @abstractmethod
    def get_license_details(self, license_number: str) -> Optional[ProfessionalLicense]:
        """
        Get detailed information for a specific license.

        Args:
            license_number: License number

        Returns:
            ProfessionalLicense with full details or None
        """
        pass

    @abstractmethod
    def verify_license(self, license_number: str, licensee_name: str = None) -> bool:
        """
        Verify if a license is valid and active.

        Args:
            license_number: License number to verify
            licensee_name: Optional name to match

        Returns:
            True if license is valid and active
        """
        pass

    def parse_license_status(self, status_text: str) -> LicenseStatus:
        """
        Parse license status from text.

        Args:
            status_text: Status string

        Returns:
            Parsed LicenseStatus
        """
        status_lower = status_text.lower().strip()

        if any(s in status_lower for s in ['active', 'current', 'valid', 'good standing']):
            return LicenseStatus.ACTIVE
        elif any(s in status_lower for s in ['inactive', 'not active']):
            return LicenseStatus.INACTIVE
        elif 'expired' in status_lower:
            return LicenseStatus.EXPIRED
        elif 'suspended' in status_lower:
            return LicenseStatus.SUSPENDED
        elif 'revoked' in status_lower:
            return LicenseStatus.REVOKED
        elif 'surrendered' in status_lower:
            return LicenseStatus.SURRENDERED
        elif 'pending' in status_lower:
            return LicenseStatus.PENDING
        elif 'probation' in status_lower:
            return LicenseStatus.PROBATION
        elif 'deceased' in status_lower:
            return LicenseStatus.DECEASED

        return LicenseStatus.UNKNOWN

    def classify_license_type(self, license_text: str) -> LicenseType:
        """
        Classify license type from text.

        Args:
            license_text: License type or category text

        Returns:
            Classified LicenseType
        """
        text_lower = license_text.lower()

        # Real Estate
        if 'real estate' in text_lower:
            if 'broker' in text_lower:
                return LicenseType.REAL_ESTATE_BROKER
            elif 'appraiser' in text_lower:
                return LicenseType.REAL_ESTATE_APPRAISER
            return LicenseType.REAL_ESTATE_AGENT

        # Mortgage/Lending
        if any(t in text_lower for t in ['loan officer', 'mlo', 'mortgage loan originator']):
            return LicenseType.LOAN_OFFICER
        if 'mortgage broker' in text_lower:
            return LicenseType.MORTGAGE_BROKER
        if 'mortgage lender' in text_lower:
            return LicenseType.MORTGAGE_LENDER

        # Legal
        if any(t in text_lower for t in ['attorney', 'lawyer', 'counsel']):
            return LicenseType.ATTORNEY
        if 'notary' in text_lower:
            return LicenseType.NOTARY

        # Construction
        if 'general contractor' in text_lower:
            return LicenseType.GENERAL_CONTRACTOR
        if 'electrician' in text_lower:
            return LicenseType.ELECTRICIAN
        if 'plumber' in text_lower:
            return LicenseType.PLUMBER
        if 'hvac' in text_lower or 'heating' in text_lower:
            return LicenseType.HVAC
        if 'contractor' in text_lower:
            return LicenseType.SPECIALTY_CONTRACTOR

        # Healthcare
        if any(t in text_lower for t in ['physician', 'doctor', 'md']):
            return LicenseType.PHYSICIAN
        if 'nurse' in text_lower:
            return LicenseType.NURSE
        if 'dentist' in text_lower:
            return LicenseType.DENTIST
        if 'pharmacist' in text_lower:
            return LicenseType.PHARMACIST

        # Financial
        if 'cpa' in text_lower or 'accountant' in text_lower:
            return LicenseType.CPA
        if 'insurance' in text_lower:
            return LicenseType.INSURANCE_AGENT

        return LicenseType.OTHER

    def normalize_name(self, name: str) -> str:
        """
        Normalize licensee name for matching.

        Args:
            name: Raw name

        Returns:
            Normalized name
        """
        # Remove suffixes
        name = re.sub(r'\b(jr|sr|ii|iii|iv|md|dds|esq|phd|rn|np)\b\.?', '', name, flags=re.IGNORECASE)

        # Remove extra whitespace
        name = ' '.join(name.split())

        return name.strip()

    def parse_date(self, date_str: str) -> Optional[date]:
        """Parse date from various formats."""
        if not date_str:
            return None

        formats = ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y%m%d', '%d-%b-%Y']

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get scraper statistics."""
        return {
            'state': self.state_code,
            'scraper_class': self.__class__.__name__,
        }


class StateLicenseBoardScraper(ProfessionalLicensesScraper):
    """
    Generic state licensing board scraper.
    """

    def __init__(self, state_code: str, license_type: LicenseType, config: Dict[str, Any] = None):
        """
        Initialize state license board scraper.

        Args:
            state_code: Two-letter state code
            license_type: Type of licenses this board handles
            config: State-specific configuration
        """
        super().__init__(state_code=state_code, config=config)
        self.license_type = license_type
        self.base_url = config.get('base_url', '') if config else ''

    def search_licenses(self, search: LicenseSearch) -> List[ProfessionalLicense]:
        """Search for licenses in this state."""
        logger.info(f"Searching {self.license_type.value} licenses in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return []

    def get_license_details(self, license_number: str) -> Optional[ProfessionalLicense]:
        """Get detailed license information."""
        logger.info(f"Getting license details for {license_number} in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return None

    def verify_license(self, license_number: str, licensee_name: str = None) -> bool:
        """Verify license status."""
        license = self.get_license_details(license_number)

        if not license:
            return False

        if licensee_name:
            normalized_input = self.normalize_name(licensee_name)
            normalized_license = self.normalize_name(license.licensee_name)
            if normalized_input.lower() != normalized_license.lower():
                return False

        return license.is_active


class NMLSScraper(ProfessionalLicensesScraper):
    """
    NMLS Consumer Access scraper for mortgage professionals.
    """

    NMLS_BASE_URL = "https://www.nmlsconsumeraccess.org"

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize NMLS scraper."""
        super().__init__(state_code=None, config=config)

    def search_licenses(self, search: LicenseSearch) -> List[ProfessionalLicense]:
        """Search NMLS for mortgage professionals."""
        logger.info(f"Searching NMLS for {search.name or search.nmls_id}")

        # Placeholder - actual implementation would make API calls
        return []

    def get_license_details(self, license_number: str) -> Optional[ProfessionalLicense]:
        """Get NMLS license details."""
        logger.info(f"Getting NMLS details for {license_number}")

        # Placeholder - actual implementation would make API calls
        return None

    def verify_license(self, license_number: str, licensee_name: str = None) -> bool:
        """Verify NMLS license."""
        license = self.get_license_details(license_number)
        return license is not None and license.is_active

    def search_by_nmls_id(self, nmls_id: str) -> Optional[ProfessionalLicense]:
        """
        Search by NMLS ID directly.

        Args:
            nmls_id: NMLS unique identifier

        Returns:
            ProfessionalLicense or None
        """
        search = LicenseSearch(nmls_id=nmls_id)
        results = self.search_licenses(search)
        return results[0] if results else None


def verify_professional_license(
    license_number: str,
    license_type: LicenseType,
    state: str,
    licensee_name: str = None
) -> Dict[str, Any]:
    """
    Convenience function to verify a professional license.

    Args:
        license_number: License number to verify
        license_type: Type of license
        state: State of licensure
        licensee_name: Optional name to verify

    Returns:
        Dictionary with verification results
    """
    result = {
        'license_number': license_number,
        'license_type': license_type.value,
        'state': state,
        'verified': False,
        'status': None,
        'licensee_name': None,
        'expiration_date': None,
        'error': None
    }

    logger.info(f"Verifying {license_type.value} license {license_number} in {state}")

    return result


def search_professional_licenses(
    name: str,
    license_types: List[LicenseType] = None,
    states: List[str] = None,
    include_inactive: bool = False
) -> List[ProfessionalLicense]:
    """
    Convenience function to search licenses across multiple sources.

    Args:
        name: Licensee name to search
        license_types: Types to include
        states: States to search
        include_inactive: Include inactive licenses

    Returns:
        List of matching ProfessionalLicense objects
    """
    results = []

    search = LicenseSearch(
        name=name,
        include_inactive=include_inactive
    )

    logger.info(f"Searching professional licenses for '{name}'")

    return results
