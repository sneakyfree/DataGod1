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
- NPI Registry (healthcare)

Free APIs Integrated:
- NMLS Consumer Access (nmlsconsumeraccess.org)
- NPI Registry (npiregistry.cms.hhs.gov)
- State licensing board APIs where available
- ARELLO (arello.org) for real estate
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, quote_plus

logger = logging.getLogger(__name__)

# Try to import aiohttp for async requests
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available, async methods will be limited")


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
    NURSE_PRACTITIONER = "nurse_practitioner"
    DENTIST = "dentist"
    PHARMACIST = "pharmacist"
    PHYSICAL_THERAPIST = "physical_therapist"
    PSYCHOLOGIST = "psychologist"
    CHIROPRACTOR = "chiropractor"
    OPTOMETRIST = "optometrist"
    PODIATRIST = "podiatrist"

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
    DENIED = "denied"
    CANCELLED = "cancelled"
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
            'action_date': self.action_date.isoformat() if self.action_date else None,
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
    nmls_id: Optional[str] = None
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
            'nmls_id': self.nmls_id,
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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    credential: Optional[str] = None
    address: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    employer: Optional[Employer] = None
    organization_name: Optional[str] = None
    specializations: List[str] = field(default_factory=list)
    taxonomy_codes: List[str] = field(default_factory=list)
    disciplinary_actions: List[DisciplinaryAction] = field(default_factory=list)
    ce_hours: Optional[int] = None
    nmls_id: Optional[str] = None  # For mortgage professionals
    bar_number: Optional[str] = None  # For attorneys
    npi: Optional[str] = None  # For healthcare providers
    enumeration_date: Optional[date] = None  # For NPI
    last_updated: Optional[date] = None
    data_source: Optional[str] = None
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'license_number': self.license_number,
            'license_type': self.license_type.value,
            'licensee_name': self.licensee_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'middle_name': self.middle_name,
            'credential': self.credential,
            'state': self.state,
            'status': self.status.value,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'address': self.address,
            'address_line_2': self.address_line_2,
            'city': self.city,
            'zip_code': self.zip_code,
            'county': self.county,
            'phone': self.phone,
            'fax': self.fax,
            'email': self.email,
            'employer': self.employer.to_dict() if self.employer else None,
            'organization_name': self.organization_name,
            'specializations': self.specializations,
            'taxonomy_codes': self.taxonomy_codes,
            'disciplinary_actions': [d.to_dict() for d in self.disciplinary_actions],
            'ce_hours': self.ce_hours,
            'nmls_id': self.nmls_id,
            'bar_number': self.bar_number,
            'npi': self.npi,
            'enumeration_date': self.enumeration_date.isoformat() if self.enumeration_date else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'data_source': self.data_source,
            'source_url': self.source_url,
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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    license_number: Optional[str] = None
    license_type: Optional[LicenseType] = None
    state: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    status: Optional[LicenseStatus] = None
    include_inactive: bool = False
    include_disciplined_only: bool = False
    employer_name: Optional[str] = None
    nmls_id: Optional[str] = None
    npi: Optional[str] = None
    taxonomy_code: Optional[str] = None
    exact_match: bool = False
    limit: int = 50


# =============================================================================
# State Licensing Board Configurations
# =============================================================================

STATE_LICENSE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "CA": {
        "name": "California",
        "boards": {
            "real_estate": {
                "name": "California DRE",
                "url": "https://www2.dre.ca.gov/PublicASP/pplinfo.asp",
                "api_available": False
            },
            "contractors": {
                "name": "CSLB",
                "url": "https://www.cslb.ca.gov/OnlineServices/CheckLicenseII/CheckLicense.aspx",
                "api_available": False
            },
            "medical": {
                "name": "Medical Board of California",
                "url": "https://mbc.ca.gov/breeze/",
                "api_available": False
            }
        }
    },
    "TX": {
        "name": "Texas",
        "boards": {
            "real_estate": {
                "name": "TREC",
                "url": "https://www.trec.texas.gov/apps/license-holder-search/",
                "api_available": False
            },
            "medical": {
                "name": "Texas Medical Board",
                "url": "https://profile.tmb.state.tx.us/",
                "api_available": False
            }
        }
    },
    "FL": {
        "name": "Florida",
        "boards": {
            "real_estate": {
                "name": "FREC",
                "url": "https://www.myfloridalicense.com/wl11.asp",
                "api_url": "https://www.myfloridalicense.com/licensesearch/",
                "api_available": True
            },
            "contractors": {
                "name": "Florida CILB",
                "url": "https://www.myfloridalicense.com/wl11.asp?mode=2&search=Name&SID=&brd=&typ=",
                "api_available": False
            }
        }
    },
    "NY": {
        "name": "New York",
        "boards": {
            "real_estate": {
                "name": "DOS",
                "url": "https://appext20.dos.ny.gov/lcns_public/cos_search",
                "api_available": False
            },
            "medical": {
                "name": "NYSED",
                "url": "http://www.op.nysed.gov/opsearches.htm",
                "api_available": False
            }
        }
    }
}

# Healthcare taxonomy codes for NPI searches
HEALTHCARE_TAXONOMY_CODES: Dict[str, str] = {
    "physician": "207",  # Allopathic & Osteopathic Physicians
    "nurse": "163W",  # Registered Nurse
    "nurse_practitioner": "363L",  # Nurse Practitioner
    "dentist": "122300000X",  # Dentist
    "pharmacist": "183500000X",  # Pharmacist
    "physical_therapist": "225100000X",  # Physical Therapist
    "psychologist": "103T",  # Psychologist
    "chiropractor": "111N",  # Chiropractor
    "optometrist": "152W",  # Optometrist
    "podiatrist": "213E"  # Podiatrist
}


# =============================================================================
# Professional Licenses API (Main Implementation)
# =============================================================================

class ProfessionalLicensesAPI:
    """
    Unified API for professional license searches across multiple sources.

    Integrates:
    - NMLS Consumer Access (mortgage professionals)
    - NPI Registry (healthcare providers)
    - State licensing board APIs where available

    All methods are async-first with synchronous wrappers.
    """

    # API endpoints
    NPI_API_URL = "https://npiregistry.cms.hhs.gov/api/"
    NMLS_BASE_URL = "https://www.nmlsconsumeraccess.org"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Professional Licenses API.

        Args:
            config: Optional configuration dict with API keys/settings
        """
        self.config = config or {}
        self._session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0
        self.last_request_time = None

        logger.info("Initialized ProfessionalLicensesAPI")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "DataGod/1.0 Professional License Verification",
                    "Accept": "application/json"
                }
            )
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _rate_limit(self, delay: float = 1.0):
        """Apply rate limiting between requests."""
        if self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
        self.last_request_time = datetime.now()
        self.request_count += 1

    # =========================================================================
    # NPI Registry (Healthcare Providers)
    # =========================================================================

    async def search_npi(
        self,
        first_name: str = "",
        last_name: str = "",
        organization_name: str = "",
        npi: str = "",
        state: str = "",
        city: str = "",
        zip_code: str = "",
        taxonomy_description: str = "",
        limit: int = 50,
        skip: int = 0
    ) -> List[ProfessionalLicense]:
        """
        Search the NPI Registry for healthcare providers.

        The NPI Registry is a free, public database of all healthcare providers
        who have registered for a National Provider Identifier (NPI).

        Args:
            first_name: Provider's first name
            last_name: Provider's last name
            organization_name: Organization/practice name
            npi: Specific NPI number
            state: Two-letter state code
            city: City name
            zip_code: ZIP code (5 or 9 digit)
            taxonomy_description: Healthcare specialty (e.g., "Family Medicine")
            limit: Maximum results (max 200)
            skip: Number of results to skip

        Returns:
            List of ProfessionalLicense objects
        """
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp required for NPI searches")
            return []

        await self._rate_limit(0.5)  # NPI API is generous with rate limits

        # Build query parameters
        params = {
            "version": "2.1",
            "limit": min(limit, 200)
        }

        if skip > 0:
            params["skip"] = skip
        if npi:
            params["number"] = npi
        if first_name:
            params["first_name"] = first_name
        if last_name:
            params["last_name"] = last_name
        if organization_name:
            params["organization_name"] = organization_name
        if state:
            params["state"] = state.upper()
        if city:
            params["city"] = city
        if zip_code:
            params["postal_code"] = zip_code
        if taxonomy_description:
            params["taxonomy_description"] = taxonomy_description

        try:
            session = await self._get_session()
            async with session.get(self.NPI_API_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"NPI API error: {response.status}")
                    return []

                data = await response.json()
                results = data.get("results", [])

                licenses = []
                for result in results:
                    license = self._parse_npi_result(result)
                    if license:
                        licenses.append(license)

                logger.info(f"NPI search returned {len(licenses)} results")
                return licenses

        except Exception as e:
            logger.error(f"NPI search error: {e}")
            return []

    def _parse_npi_result(self, result: Dict[str, Any]) -> Optional[ProfessionalLicense]:
        """Parse NPI API result into ProfessionalLicense."""
        try:
            npi_number = result.get("number", "")
            basic = result.get("basic", {})

            # Determine if individual or organization
            enumeration_type = basic.get("enumeration_type", "")
            is_individual = enumeration_type == "NPI-1"

            # Get name
            if is_individual:
                first_name = basic.get("first_name", "")
                last_name = basic.get("last_name", "")
                middle_name = basic.get("middle_name")
                licensee_name = f"{first_name} {last_name}".strip()
                credential = basic.get("credential")
                org_name = None
            else:
                first_name = None
                last_name = None
                middle_name = None
                licensee_name = basic.get("organization_name", "")
                credential = None
                org_name = licensee_name

            # Get address (use practice location if available)
            addresses = result.get("addresses", [])
            practice_address = None
            for addr in addresses:
                if addr.get("address_purpose") == "LOCATION":
                    practice_address = addr
                    break
            if not practice_address and addresses:
                practice_address = addresses[0]

            state = ""
            city = ""
            address = ""
            address_2 = ""
            zip_code = ""
            phone = ""
            fax = ""

            if practice_address:
                state = practice_address.get("state", "")
                city = practice_address.get("city", "")
                address = practice_address.get("address_1", "")
                address_2 = practice_address.get("address_2")
                zip_code = practice_address.get("postal_code", "")
                phone = practice_address.get("telephone_number")
                fax = practice_address.get("fax_number")

            # Get taxonomies (specializations)
            taxonomies = result.get("taxonomies", [])
            taxonomy_codes = []
            specializations = []
            license_type = LicenseType.PHYSICIAN  # Default for healthcare

            for tax in taxonomies:
                code = tax.get("code", "")
                desc = tax.get("desc", "")
                if code:
                    taxonomy_codes.append(code)
                if desc:
                    specializations.append(desc)
                    # Classify based on taxonomy
                    if tax.get("primary", False):
                        license_type = self._classify_healthcare_taxonomy(code, desc)

            # Parse dates
            enumeration_date = None
            last_updated = None
            enum_str = basic.get("enumeration_date", "")
            update_str = basic.get("last_updated", "")

            if enum_str:
                try:
                    enumeration_date = datetime.strptime(enum_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            if update_str:
                try:
                    last_updated = datetime.strptime(update_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            # NPI doesn't have status/expiration - assume active if present
            status = LicenseStatus.ACTIVE
            if basic.get("status") == "D":  # Deactivated
                status = LicenseStatus.INACTIVE

            return ProfessionalLicense(
                license_number=npi_number,
                license_type=license_type,
                licensee_name=licensee_name,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                credential=credential,
                state=state,
                status=status,
                address=address,
                address_line_2=address_2,
                city=city,
                zip_code=zip_code,
                phone=phone,
                fax=fax,
                organization_name=org_name,
                specializations=specializations,
                taxonomy_codes=taxonomy_codes,
                npi=npi_number,
                enumeration_date=enumeration_date,
                last_updated=last_updated,
                data_source="NPI Registry",
                source_url=f"https://npiregistry.cms.hhs.gov/provider-view/{npi_number}",
                raw_data=result
            )

        except Exception as e:
            logger.error(f"Error parsing NPI result: {e}")
            return None

    def _classify_healthcare_taxonomy(self, code: str, description: str) -> LicenseType:
        """Classify healthcare license type from taxonomy code/description."""
        desc_lower = description.lower()

        # Check common patterns
        if "nurse practitioner" in desc_lower or code.startswith("363"):
            return LicenseType.NURSE_PRACTITIONER
        elif "registered nurse" in desc_lower or code.startswith("163W"):
            return LicenseType.NURSE
        elif "dentist" in desc_lower or code.startswith("1223"):
            return LicenseType.DENTIST
        elif "pharmacist" in desc_lower or code.startswith("1835"):
            return LicenseType.PHARMACIST
        elif "physical therap" in desc_lower or code.startswith("2251"):
            return LicenseType.PHYSICAL_THERAPIST
        elif "psycholog" in desc_lower or code.startswith("103T"):
            return LicenseType.PSYCHOLOGIST
        elif "chiropract" in desc_lower or code.startswith("111N"):
            return LicenseType.CHIROPRACTOR
        elif "optometr" in desc_lower or code.startswith("152W"):
            return LicenseType.OPTOMETRIST
        elif "podiatr" in desc_lower or code.startswith("213E"):
            return LicenseType.PODIATRIST
        elif any(x in desc_lower for x in ["physician", "doctor", "md", "do"]):
            return LicenseType.PHYSICIAN

        return LicenseType.OTHER

    async def get_npi_details(self, npi: str) -> Optional[ProfessionalLicense]:
        """
        Get detailed information for a specific NPI number.

        Args:
            npi: 10-digit NPI number

        Returns:
            ProfessionalLicense with full details or None
        """
        if not npi or len(npi) != 10:
            logger.error(f"Invalid NPI format: {npi}")
            return None

        results = await self.search_npi(npi=npi, limit=1)
        return results[0] if results else None

    async def verify_npi(self, npi: str, name: str = "") -> Dict[str, Any]:
        """
        Verify a healthcare provider's NPI.

        Args:
            npi: NPI number to verify
            name: Optional name to match

        Returns:
            Verification result dict
        """
        result = {
            "npi": npi,
            "verified": False,
            "active": False,
            "name_match": None,
            "provider_name": None,
            "provider_type": None,
            "state": None,
            "error": None
        }

        license = await self.get_npi_details(npi)

        if not license:
            result["error"] = "NPI not found"
            return result

        result["verified"] = True
        result["active"] = license.status == LicenseStatus.ACTIVE
        result["provider_name"] = license.licensee_name
        result["provider_type"] = license.license_type.value
        result["state"] = license.state

        if name:
            # Fuzzy name matching
            name_lower = name.lower()
            licensee_lower = license.licensee_name.lower()
            result["name_match"] = (
                name_lower in licensee_lower or
                licensee_lower in name_lower
            )

        return result

    # =========================================================================
    # NMLS Consumer Access (Mortgage Professionals)
    # =========================================================================

    async def search_nmls(
        self,
        nmls_id: str = "",
        name: str = "",
        first_name: str = "",
        last_name: str = "",
        state: str = "",
        company_name: str = "",
        company_nmls_id: str = "",
        limit: int = 50
    ) -> List[ProfessionalLicense]:
        """
        Search NMLS Consumer Access for mortgage professionals.

        Note: NMLS doesn't have a public API, so this uses web scraping
        when possible and provides direct URL links.

        Args:
            nmls_id: NMLS unique identifier
            name: Full name to search
            first_name: First name
            last_name: Last name
            state: State where licensed
            company_name: Sponsoring company name
            company_nmls_id: Sponsoring company NMLS ID
            limit: Maximum results

        Returns:
            List of ProfessionalLicense objects
        """
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp required for NMLS searches")
            return []

        await self._rate_limit(2.0)  # Be respectful of NMLS

        # NMLS Consumer Access search URL
        # Unfortunately, NMLS doesn't have a public API - we can only
        # provide direct links and basic validation

        licenses = []

        if nmls_id:
            # Direct lookup by NMLS ID - construct the profile URL
            profile_url = f"{self.NMLS_BASE_URL}/EntityDetails.aspx/COMPANY/{nmls_id}"
            individual_url = f"{self.NMLS_BASE_URL}/EntityDetails.aspx/INDIVIDUAL/{nmls_id}"

            try:
                session = await self._get_session()

                # Try individual first
                async with session.get(individual_url, allow_redirects=True) as response:
                    if response.status == 200:
                        text = await response.text()
                        license = self._parse_nmls_page(text, nmls_id, "INDIVIDUAL")
                        if license:
                            licenses.append(license)

                # If not individual, try company
                if not licenses:
                    async with session.get(profile_url, allow_redirects=True) as response:
                        if response.status == 200:
                            text = await response.text()
                            license = self._parse_nmls_page(text, nmls_id, "COMPANY")
                            if license:
                                licenses.append(license)

            except Exception as e:
                logger.error(f"NMLS lookup error: {e}")

        if not licenses and (name or first_name or last_name):
            # For name searches, we can only provide search URL guidance
            search_name = name or f"{first_name} {last_name}".strip()
            logger.info(f"NMLS name search for '{search_name}' - providing search URL")

            # Create placeholder with search instructions
            license = ProfessionalLicense(
                license_number="SEARCH_REQUIRED",
                license_type=LicenseType.LOAN_OFFICER,
                licensee_name=search_name,
                state=state or "US",
                status=LicenseStatus.UNKNOWN,
                data_source="NMLS Consumer Access",
                source_url=f"{self.NMLS_BASE_URL}/FindAMortgageProfessional.aspx",
                raw_data={
                    "search_instructions": "Visit source_url and search manually",
                    "search_name": search_name,
                    "search_state": state
                }
            )
            licenses.append(license)

        return licenses

    def _parse_nmls_page(
        self,
        html: str,
        nmls_id: str,
        entity_type: str
    ) -> Optional[ProfessionalLicense]:
        """Parse NMLS profile page HTML."""
        try:
            # Look for key indicators that the page contains valid data
            if "Entity not found" in html or "No results" in html:
                return None

            # Extract name (usually in a header or specific div)
            name_match = re.search(
                r'<h\d[^>]*class="[^"]*entity-name[^"]*"[^>]*>([^<]+)</h\d>',
                html, re.IGNORECASE
            )
            if not name_match:
                name_match = re.search(
                    r'<span[^>]*id="[^"]*EntityName[^"]*"[^>]*>([^<]+)</span>',
                    html, re.IGNORECASE
                )

            name = name_match.group(1).strip() if name_match else f"NMLS #{nmls_id}"

            # Determine license type based on entity type
            if entity_type == "INDIVIDUAL":
                license_type = LicenseType.LOAN_OFFICER
            else:
                license_type = LicenseType.MORTGAGE_BROKER

            # Extract status if visible
            status = LicenseStatus.UNKNOWN
            if re.search(r'\bactive\b', html, re.IGNORECASE):
                status = LicenseStatus.ACTIVE
            elif re.search(r'\binactive\b', html, re.IGNORECASE):
                status = LicenseStatus.INACTIVE
            elif re.search(r'\bsurrendered\b', html, re.IGNORECASE):
                status = LicenseStatus.SURRENDERED

            # Extract state licenses
            states = []
            state_matches = re.findall(
                r'<td[^>]*>([A-Z]{2})</td>\s*<td[^>]*>(Active|Inactive|Approved)',
                html, re.IGNORECASE
            )
            for st, st_status in state_matches:
                if st_status.lower() == "active":
                    states.append(st)

            return ProfessionalLicense(
                license_number=nmls_id,
                license_type=license_type,
                licensee_name=name,
                state=", ".join(states) if states else "US",
                status=status,
                nmls_id=nmls_id,
                data_source="NMLS Consumer Access",
                source_url=f"{self.NMLS_BASE_URL}/EntityDetails.aspx/{entity_type}/{nmls_id}",
                raw_data={"entity_type": entity_type, "licensed_states": states}
            )

        except Exception as e:
            logger.error(f"Error parsing NMLS page: {e}")
            return None

    async def verify_nmls(
        self,
        nmls_id: str,
        name: str = "",
        state: str = ""
    ) -> Dict[str, Any]:
        """
        Verify a mortgage professional's NMLS status.

        Args:
            nmls_id: NMLS unique identifier
            name: Optional name to verify
            state: Optional state to check licensure

        Returns:
            Verification result dict
        """
        result = {
            "nmls_id": nmls_id,
            "verified": False,
            "active_states": [],
            "name_match": None,
            "profile_name": None,
            "profile_url": None,
            "error": None
        }

        licenses = await self.search_nmls(nmls_id=nmls_id)

        if not licenses or licenses[0].license_number == "SEARCH_REQUIRED":
            result["error"] = "NMLS ID not found or requires manual verification"
            result["profile_url"] = f"{self.NMLS_BASE_URL}/EntityDetails.aspx/INDIVIDUAL/{nmls_id}"
            return result

        license = licenses[0]
        result["verified"] = True
        result["profile_name"] = license.licensee_name
        result["profile_url"] = license.source_url

        active_states = license.raw_data.get("licensed_states", [])
        result["active_states"] = active_states

        if name:
            name_lower = name.lower()
            licensee_lower = license.licensee_name.lower()
            result["name_match"] = (
                name_lower in licensee_lower or
                licensee_lower in name_lower
            )

        if state and state.upper() not in active_states:
            result["state_licensed"] = False
        elif state:
            result["state_licensed"] = True

        return result

    # =========================================================================
    # State License Board Searches
    # =========================================================================

    async def search_state_licenses(
        self,
        state: str,
        name: str = "",
        license_number: str = "",
        license_type: LicenseType = None,
        include_inactive: bool = False,
        limit: int = 50
    ) -> List[ProfessionalLicense]:
        """
        Search state licensing board for professional licenses.

        Note: Most states don't have public APIs, so this provides
        lookup URLs and guidance for manual verification.

        Args:
            state: Two-letter state code
            name: Licensee name
            license_number: License number
            license_type: Type of license to search
            include_inactive: Include inactive licenses
            limit: Maximum results

        Returns:
            List of ProfessionalLicense objects (may be search guidance)
        """
        state = state.upper()

        if state not in STATE_LICENSE_CONFIGS:
            logger.warning(f"State {state} not configured, using generic search")
            return self._create_generic_state_search(state, name, license_number, license_type)

        config = STATE_LICENSE_CONFIGS[state]
        licenses = []

        # Determine which board to use based on license type
        board_key = None
        if license_type:
            if license_type in [LicenseType.REAL_ESTATE_AGENT, LicenseType.REAL_ESTATE_BROKER]:
                board_key = "real_estate"
            elif license_type in [LicenseType.GENERAL_CONTRACTOR, LicenseType.ELECTRICIAN, LicenseType.PLUMBER]:
                board_key = "contractors"
            elif license_type in [LicenseType.PHYSICIAN, LicenseType.NURSE]:
                board_key = "medical"

        # Search specific board or all boards
        boards_to_search = [board_key] if board_key else list(config.get("boards", {}).keys())

        for board in boards_to_search:
            board_config = config.get("boards", {}).get(board, {})
            if not board_config:
                continue

            # Check if state has API access
            if board_config.get("api_available"):
                # Implement state-specific API calls
                api_results = await self._search_state_api(
                    state, board, board_config, name, license_number, limit
                )
                licenses.extend(api_results)
            else:
                # Provide search guidance
                search_guidance = self._create_state_search_guidance(
                    state, board, board_config, name, license_number, license_type
                )
                licenses.append(search_guidance)

        return licenses[:limit]

    async def _search_state_api(
        self,
        state: str,
        board: str,
        board_config: Dict[str, Any],
        name: str,
        license_number: str,
        limit: int
    ) -> List[ProfessionalLicense]:
        """Search state API where available."""
        licenses = []

        # Florida MyFloridaLicense API
        if state == "FL" and board == "real_estate":
            await self._rate_limit(1.5)
            try:
                session = await self._get_session()

                # Florida license search - simplified API interaction
                params = {}
                if license_number:
                    params["LicenseNumber"] = license_number
                if name:
                    params["Name"] = name

                url = board_config.get("api_url", board_config.get("url"))
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        text = await response.text()
                        # Parse Florida-specific results
                        fl_licenses = self._parse_florida_results(text, state)
                        licenses.extend(fl_licenses)

            except Exception as e:
                logger.error(f"Florida license API error: {e}")

        return licenses

    def _parse_florida_results(self, html: str, state: str) -> List[ProfessionalLicense]:
        """Parse Florida MyFloridaLicense search results."""
        licenses = []

        # Look for license rows in the results table
        pattern = r'<tr[^>]*>\s*<td[^>]*>([^<]+)</td>\s*<td[^>]*>([^<]+)</td>\s*<td[^>]*>([^<]+)</td>'
        matches = re.findall(pattern, html, re.IGNORECASE)

        for match in matches:
            if len(match) >= 3:
                name = match[0].strip()
                license_num = match[1].strip()
                status_text = match[2].strip()

                if name and license_num and "license" not in name.lower():
                    status = LicenseStatus.ACTIVE if "active" in status_text.lower() else LicenseStatus.INACTIVE

                    licenses.append(ProfessionalLicense(
                        license_number=license_num,
                        license_type=LicenseType.REAL_ESTATE_AGENT,
                        licensee_name=name,
                        state=state,
                        status=status,
                        data_source="Florida DBPR",
                        source_url=f"https://www.myfloridalicense.com/wl11.asp?mode=1&search=LicNbr&SID=&brd=&typ=N&LicNbr={license_num}"
                    ))

        return licenses

    def _create_state_search_guidance(
        self,
        state: str,
        board: str,
        board_config: Dict[str, Any],
        name: str,
        license_number: str,
        license_type: LicenseType
    ) -> ProfessionalLicense:
        """Create guidance for manual state license lookup."""
        board_name = board_config.get("name", f"{state} {board.replace('_', ' ').title()}")
        url = board_config.get("url", "")

        return ProfessionalLicense(
            license_number="MANUAL_LOOKUP_REQUIRED",
            license_type=license_type or LicenseType.OTHER,
            licensee_name=name or "Search Required",
            state=state,
            status=LicenseStatus.UNKNOWN,
            data_source=board_name,
            source_url=url,
            raw_data={
                "search_instructions": f"Visit {url} to verify license",
                "board_name": board_name,
                "search_name": name,
                "search_license": license_number,
                "state": state
            }
        )

    def _create_generic_state_search(
        self,
        state: str,
        name: str,
        license_number: str,
        license_type: LicenseType
    ) -> List[ProfessionalLicense]:
        """Create generic search guidance for unconfigured states."""
        # Common search URL patterns
        search_urls = {
            "real_estate": f"https://www.google.com/search?q={state}+real+estate+commission+license+lookup",
            "contractors": f"https://www.google.com/search?q={state}+contractor+license+verification",
            "medical": f"https://www.google.com/search?q={state}+medical+board+license+lookup"
        }

        board_type = "general"
        if license_type:
            if license_type in [LicenseType.REAL_ESTATE_AGENT, LicenseType.REAL_ESTATE_BROKER]:
                board_type = "real_estate"
            elif license_type in [LicenseType.GENERAL_CONTRACTOR, LicenseType.ELECTRICIAN]:
                board_type = "contractors"
            elif license_type in [LicenseType.PHYSICIAN, LicenseType.NURSE]:
                board_type = "medical"

        url = search_urls.get(board_type, search_urls["general"] if "general" in search_urls else "")

        return [ProfessionalLicense(
            license_number="STATE_LOOKUP_REQUIRED",
            license_type=license_type or LicenseType.OTHER,
            licensee_name=name or "Search Required",
            state=state,
            status=LicenseStatus.UNKNOWN,
            data_source=f"{state} Licensing Board",
            source_url=url or f"https://www.google.com/search?q={state}+professional+license+lookup",
            raw_data={
                "search_instructions": "State not configured - use search URL to find licensing board",
                "search_name": name,
                "search_license": license_number
            }
        )]

    # =========================================================================
    # Unified Search Interface
    # =========================================================================

    async def search_licenses(
        self,
        search: LicenseSearch
    ) -> List[ProfessionalLicense]:
        """
        Unified search across all license databases.

        Automatically routes to appropriate source based on license type:
        - Healthcare (NPI)
        - Mortgage (NMLS)
        - Other (State boards)

        Args:
            search: LicenseSearch parameters

        Returns:
            Combined list of ProfessionalLicense objects
        """
        results = []

        # Route based on license type or search parameters
        license_type = search.license_type

        # Healthcare - search NPI
        healthcare_types = [
            LicenseType.PHYSICIAN, LicenseType.NURSE, LicenseType.NURSE_PRACTITIONER,
            LicenseType.DENTIST, LicenseType.PHARMACIST, LicenseType.PHYSICAL_THERAPIST,
            LicenseType.PSYCHOLOGIST, LicenseType.CHIROPRACTOR, LicenseType.OPTOMETRIST,
            LicenseType.PODIATRIST
        ]

        mortgage_types = [
            LicenseType.LOAN_OFFICER, LicenseType.MORTGAGE_BROKER, LicenseType.MORTGAGE_LENDER
        ]

        search_healthcare = license_type in healthcare_types if license_type else search.npi
        search_mortgage = license_type in mortgage_types if license_type else search.nmls_id
        search_state = not search_healthcare and not search_mortgage

        if search.npi:
            # Direct NPI lookup
            npi_result = await self.get_npi_details(search.npi)
            if npi_result:
                results.append(npi_result)
        elif search_healthcare:
            # NPI name search
            npi_results = await self.search_npi(
                first_name=search.first_name or "",
                last_name=search.last_name or "",
                organization_name=search.employer_name or "",
                state=search.state or "",
                city=search.city or "",
                zip_code=search.zip_code or "",
                limit=search.limit
            )
            results.extend(npi_results)

        if search.nmls_id:
            # Direct NMLS lookup
            nmls_results = await self.search_nmls(nmls_id=search.nmls_id)
            results.extend(nmls_results)
        elif search_mortgage:
            # NMLS name search
            nmls_results = await self.search_nmls(
                name=search.name or "",
                first_name=search.first_name or "",
                last_name=search.last_name or "",
                state=search.state or "",
                company_name=search.employer_name or "",
                limit=search.limit
            )
            results.extend(nmls_results)

        if search_state and search.state:
            # State license board search
            state_results = await self.search_state_licenses(
                state=search.state,
                name=search.name or f"{search.first_name or ''} {search.last_name or ''}".strip(),
                license_number=search.license_number or "",
                license_type=license_type,
                include_inactive=search.include_inactive,
                limit=search.limit
            )
            results.extend(state_results)

        # Filter by status if specified
        if search.status and not search.include_inactive:
            results = [r for r in results if r.status == search.status]

        return results[:search.limit]

    async def verify_license(
        self,
        license_number: str,
        license_type: LicenseType,
        state: str = "",
        licensee_name: str = ""
    ) -> Dict[str, Any]:
        """
        Verify a professional license.

        Args:
            license_number: License/NPI/NMLS number
            license_type: Type of license
            state: State of licensure
            licensee_name: Name to verify against

        Returns:
            Verification result dict
        """
        healthcare_types = [
            LicenseType.PHYSICIAN, LicenseType.NURSE, LicenseType.NURSE_PRACTITIONER,
            LicenseType.DENTIST, LicenseType.PHARMACIST
        ]

        mortgage_types = [
            LicenseType.LOAN_OFFICER, LicenseType.MORTGAGE_BROKER, LicenseType.MORTGAGE_LENDER
        ]

        if license_type in healthcare_types:
            return await self.verify_npi(license_number, licensee_name)
        elif license_type in mortgage_types:
            return await self.verify_nmls(license_number, licensee_name, state)
        else:
            # Generic verification - search and validate
            search = LicenseSearch(
                license_number=license_number,
                license_type=license_type,
                state=state,
                name=licensee_name,
                exact_match=True
            )
            results = await self.search_licenses(search)

            if not results:
                return {
                    "license_number": license_number,
                    "verified": False,
                    "error": "License not found"
                }

            license = results[0]
            return {
                "license_number": license_number,
                "verified": True,
                "active": license.is_active,
                "status": license.status.value,
                "licensee_name": license.licensee_name,
                "expiration_date": license.expiration_date.isoformat() if license.expiration_date else None,
                "source": license.data_source
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return {
            "request_count": self.request_count,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "configured_states": list(STATE_LICENSE_CONFIGS.keys()),
            "supported_sources": ["NPI Registry", "NMLS Consumer Access", "State Boards"]
        }


# =============================================================================
# Synchronous Wrappers
# =============================================================================

def search_healthcare_providers(
    first_name: str = "",
    last_name: str = "",
    organization_name: str = "",
    state: str = "",
    specialty: str = "",
    limit: int = 50
) -> List[ProfessionalLicense]:
    """
    Search for healthcare providers in the NPI Registry.

    Synchronous wrapper for ProfessionalLicensesAPI.search_npi()

    Args:
        first_name: Provider's first name
        last_name: Provider's last name
        organization_name: Organization name
        state: Two-letter state code
        specialty: Healthcare specialty
        limit: Maximum results

    Returns:
        List of ProfessionalLicense objects
    """
    api = ProfessionalLicensesAPI()

    async def _search():
        try:
            results = await api.search_npi(
                first_name=first_name,
                last_name=last_name,
                organization_name=organization_name,
                state=state,
                taxonomy_description=specialty,
                limit=limit
            )
            return results
        finally:
            await api.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def verify_npi_number(npi: str, name: str = "") -> Dict[str, Any]:
    """
    Verify a healthcare provider's NPI number.

    Synchronous wrapper for ProfessionalLicensesAPI.verify_npi()

    Args:
        npi: 10-digit NPI number
        name: Optional name to verify

    Returns:
        Verification result dict
    """
    api = ProfessionalLicensesAPI()

    async def _verify():
        try:
            return await api.verify_npi(npi, name)
        finally:
            await api.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _verify())
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(_verify())
    except RuntimeError:
        return asyncio.run(_verify())


def search_mortgage_professionals(
    nmls_id: str = "",
    name: str = "",
    state: str = ""
) -> List[ProfessionalLicense]:
    """
    Search for mortgage professionals in NMLS.

    Synchronous wrapper for ProfessionalLicensesAPI.search_nmls()

    Args:
        nmls_id: NMLS unique identifier
        name: Professional's name
        state: State of licensure

    Returns:
        List of ProfessionalLicense objects
    """
    api = ProfessionalLicensesAPI()

    async def _search():
        try:
            return await api.search_nmls(
                nmls_id=nmls_id,
                name=name,
                state=state
            )
        finally:
            await api.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def verify_nmls_license(nmls_id: str, name: str = "", state: str = "") -> Dict[str, Any]:
    """
    Verify a mortgage professional's NMLS license.

    Synchronous wrapper for ProfessionalLicensesAPI.verify_nmls()

    Args:
        nmls_id: NMLS unique identifier
        name: Optional name to verify
        state: Optional state to check licensure

    Returns:
        Verification result dict
    """
    api = ProfessionalLicensesAPI()

    async def _verify():
        try:
            return await api.verify_nmls(nmls_id, name, state)
        finally:
            await api.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _verify())
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(_verify())
    except RuntimeError:
        return asyncio.run(_verify())


def search_professional_licenses(
    name: str,
    license_types: List[LicenseType] = None,
    states: List[str] = None,
    include_inactive: bool = False
) -> List[ProfessionalLicense]:
    """
    Search for professional licenses across multiple sources.

    Synchronous wrapper for unified license search.

    Args:
        name: Licensee name to search
        license_types: Types to include (None = all)
        states: States to search (None = nationwide)
        include_inactive: Include inactive licenses

    Returns:
        List of matching ProfessionalLicense objects
    """
    api = ProfessionalLicensesAPI()
    all_results = []

    async def _search():
        try:
            # Parse name
            name_parts = name.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[-1] if len(name_parts) > 1 else ""

            # Search each combination
            types_to_search = license_types or [
                LicenseType.PHYSICIAN,
                LicenseType.LOAN_OFFICER
            ]
            states_to_search = states or [""]

            for license_type in types_to_search:
                for state in states_to_search:
                    search = LicenseSearch(
                        name=name,
                        first_name=first_name,
                        last_name=last_name,
                        license_type=license_type,
                        state=state,
                        include_inactive=include_inactive,
                        limit=50
                    )
                    results = await api.search_licenses(search)
                    all_results.extend(results)

            return all_results
        finally:
            await api.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _search())
                return future.result(timeout=120)
        else:
            return loop.run_until_complete(_search())
    except RuntimeError:
        return asyncio.run(_search())


def verify_professional_license(
    license_number: str,
    license_type: LicenseType,
    state: str,
    licensee_name: str = None
) -> Dict[str, Any]:
    """
    Verify a professional license.

    Synchronous wrapper for license verification.

    Args:
        license_number: License/NPI/NMLS number
        license_type: Type of license
        state: State of licensure
        licensee_name: Optional name to verify

    Returns:
        Dictionary with verification results
    """
    api = ProfessionalLicensesAPI()

    async def _verify():
        try:
            return await api.verify_license(
                license_number=license_number,
                license_type=license_type,
                state=state,
                licensee_name=licensee_name or ""
            )
        finally:
            await api.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _verify())
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(_verify())
    except RuntimeError:
        return asyncio.run(_verify())


# =============================================================================
# Legacy Abstract Base Classes (for backward compatibility)
# =============================================================================

class ProfessionalLicensesScraper(ABC):
    """
    Abstract base class for professional license scrapers.

    DEPRECATED: Use ProfessionalLicensesAPI instead.
    Maintained for backward compatibility only.
    """

    def __init__(self, state_code: str = None, config: Dict[str, Any] = None):
        self.state_code = state_code.upper() if state_code else None
        self.config = config or {}
        logger.info(f"Initialized ProfessionalLicensesScraper for {state_code or 'national'}")

    @abstractmethod
    def search_licenses(self, search: LicenseSearch) -> List[ProfessionalLicense]:
        pass

    @abstractmethod
    def get_license_details(self, license_number: str) -> Optional[ProfessionalLicense]:
        pass

    @abstractmethod
    def verify_license(self, license_number: str, licensee_name: str = None) -> bool:
        pass

    def parse_license_status(self, status_text: str) -> LicenseStatus:
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
        text_lower = license_text.lower()
        if 'real estate' in text_lower:
            if 'broker' in text_lower:
                return LicenseType.REAL_ESTATE_BROKER
            elif 'appraiser' in text_lower:
                return LicenseType.REAL_ESTATE_APPRAISER
            return LicenseType.REAL_ESTATE_AGENT
        if any(t in text_lower for t in ['loan officer', 'mlo', 'mortgage loan originator']):
            return LicenseType.LOAN_OFFICER
        if 'mortgage broker' in text_lower:
            return LicenseType.MORTGAGE_BROKER
        if any(t in text_lower for t in ['attorney', 'lawyer', 'counsel']):
            return LicenseType.ATTORNEY
        if 'notary' in text_lower:
            return LicenseType.NOTARY
        if 'general contractor' in text_lower:
            return LicenseType.GENERAL_CONTRACTOR
        if 'electrician' in text_lower:
            return LicenseType.ELECTRICIAN
        if 'plumber' in text_lower:
            return LicenseType.PLUMBER
        if any(t in text_lower for t in ['physician', 'doctor', 'md']):
            return LicenseType.PHYSICIAN
        if 'nurse' in text_lower:
            return LicenseType.NURSE
        if 'dentist' in text_lower:
            return LicenseType.DENTIST
        if 'pharmacist' in text_lower:
            return LicenseType.PHARMACIST
        if 'cpa' in text_lower or 'accountant' in text_lower:
            return LicenseType.CPA
        if 'insurance' in text_lower:
            return LicenseType.INSURANCE_AGENT
        return LicenseType.OTHER

    def normalize_name(self, name: str) -> str:
        name = re.sub(r'\b(jr|sr|ii|iii|iv|md|dds|esq|phd|rn|np)\b\.?', '', name, flags=re.IGNORECASE)
        name = ' '.join(name.split())
        return name.strip()

    def parse_date(self, date_str: str) -> Optional[date]:
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
        return {
            'state': self.state_code,
            'scraper_class': self.__class__.__name__,
        }


class StateLicenseBoardScraper(ProfessionalLicensesScraper):
    """Generic state licensing board scraper - DEPRECATED."""

    def __init__(self, state_code: str, license_type: LicenseType, config: Dict[str, Any] = None):
        super().__init__(state_code=state_code, config=config)
        self.license_type = license_type
        self.base_url = config.get('base_url', '') if config else ''

    def search_licenses(self, search: LicenseSearch) -> List[ProfessionalLicense]:
        logger.warning("StateLicenseBoardScraper.search_licenses is deprecated - use ProfessionalLicensesAPI")
        return []

    def get_license_details(self, license_number: str) -> Optional[ProfessionalLicense]:
        logger.warning("StateLicenseBoardScraper.get_license_details is deprecated - use ProfessionalLicensesAPI")
        return None

    def verify_license(self, license_number: str, licensee_name: str = None) -> bool:
        logger.warning("StateLicenseBoardScraper.verify_license is deprecated - use ProfessionalLicensesAPI")
        return False


class NMLSScraper(ProfessionalLicensesScraper):
    """NMLS Consumer Access scraper - DEPRECATED."""

    NMLS_BASE_URL = "https://www.nmlsconsumeraccess.org"

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(state_code=None, config=config)

    def search_licenses(self, search: LicenseSearch) -> List[ProfessionalLicense]:
        logger.warning("NMLSScraper.search_licenses is deprecated - use ProfessionalLicensesAPI")
        return search_mortgage_professionals(
            nmls_id=search.nmls_id or "",
            name=search.name or ""
        )

    def get_license_details(self, license_number: str) -> Optional[ProfessionalLicense]:
        logger.warning("NMLSScraper.get_license_details is deprecated - use ProfessionalLicensesAPI")
        results = search_mortgage_professionals(nmls_id=license_number)
        return results[0] if results else None

    def verify_license(self, license_number: str, licensee_name: str = None) -> bool:
        result = verify_nmls_license(license_number, licensee_name or "")
        return result.get("verified", False)

    def search_by_nmls_id(self, nmls_id: str) -> Optional[ProfessionalLicense]:
        results = search_mortgage_professionals(nmls_id=nmls_id)
        return results[0] if results else None
