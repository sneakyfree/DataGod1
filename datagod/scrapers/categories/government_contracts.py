"""
Government Contracts Category Scraper

Collects public government contract records including:
- Federal contracts (USASpending, FPDS)
- State and local contracts
- Grants and awards
- Procurement data
- Contract modifications
- Subcontract data
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContractType(Enum):
    """Types of government contracts."""

    DEFINITIVE = "definitive"
    IDV = "idv"  # Indefinite Delivery Vehicle
    BPA = "bpa"  # Blanket Purchase Agreement
    BOA = "boa"  # Basic Ordering Agreement
    GRANT = "grant"
    COOPERATIVE_AGREEMENT = "cooperative_agreement"
    LOAN = "loan"
    DIRECT_PAYMENT = "direct_payment"
    PURCHASE_ORDER = "purchase_order"
    TASK_ORDER = "task_order"


class AwardStatus(Enum):
    """Award/contract status."""

    ACTIVE = "active"
    CLOSED = "closed"
    TERMINATED = "terminated"
    PENDING = "pending"
    MODIFIED = "modified"


class CompetitionType(Enum):
    """Competition type for awards."""

    FULL_OPEN = "full_open"
    FULL_OPEN_SMALL_BUSINESS = "full_open_small_business"
    COMPETITIVE_8A = "competitive_8a"
    NOT_COMPETED = "not_competed"
    NOT_AVAILABLE = "not_available"
    SOLE_SOURCE = "sole_source"
    LIMITED_SOURCES = "limited_sources"


@dataclass
class ContractRecord:
    """Government contract record data structure."""

    contract_id: str
    contract_type: ContractType
    awarding_agency: str
    awarding_sub_agency: Optional[str] = None
    recipient_name: str = ""
    recipient_duns: Optional[str] = None
    recipient_uei: Optional[str] = None
    recipient_address: Optional[str] = None
    recipient_city: Optional[str] = None
    recipient_state: Optional[str] = None
    recipient_zip: Optional[str] = None
    award_amount: float = 0.0
    obligated_amount: float = 0.0
    potential_amount: Optional[float] = None
    award_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    description: Optional[str] = None
    naics_code: Optional[str] = None
    naics_description: Optional[str] = None
    psc_code: Optional[str] = None  # Product Service Code
    competition_type: CompetitionType = CompetitionType.NOT_AVAILABLE
    status: AwardStatus = AwardStatus.ACTIVE
    place_of_performance_city: Optional[str] = None
    place_of_performance_state: Optional[str] = None
    place_of_performance_zip: Optional[str] = None
    small_business: bool = False
    women_owned: bool = False
    veteran_owned: bool = False
    minority_owned: bool = False
    disadvantaged: bool = False
    modifications: List[Dict[str, Any]] = field(default_factory=list)
    subcontracts: List[Dict[str, Any]] = field(default_factory=list)
    source_url: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "contract_id": self.contract_id,
            "contract_type": self.contract_type.value,
            "awarding_agency": self.awarding_agency,
            "awarding_sub_agency": self.awarding_sub_agency,
            "recipient_name": self.recipient_name,
            "recipient_duns": self.recipient_duns,
            "recipient_uei": self.recipient_uei,
            "recipient_address": self.recipient_address,
            "recipient_city": self.recipient_city,
            "recipient_state": self.recipient_state,
            "recipient_zip": self.recipient_zip,
            "award_amount": self.award_amount,
            "obligated_amount": self.obligated_amount,
            "potential_amount": self.potential_amount,
            "award_date": self.award_date.isoformat() if self.award_date else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "description": self.description,
            "naics_code": self.naics_code,
            "naics_description": self.naics_description,
            "psc_code": self.psc_code,
            "competition_type": self.competition_type.value,
            "status": self.status.value,
            "place_of_performance_city": self.place_of_performance_city,
            "place_of_performance_state": self.place_of_performance_state,
            "place_of_performance_zip": self.place_of_performance_zip,
            "small_business": self.small_business,
            "women_owned": self.women_owned,
            "veteran_owned": self.veteran_owned,
            "minority_owned": self.minority_owned,
            "disadvantaged": self.disadvantaged,
            "modifications_count": len(self.modifications),
            "subcontracts_count": len(self.subcontracts),
            "source_url": self.source_url,
        }


# Federal contract data sources
FEDERAL_CONTRACT_SOURCES = {
    "usaspending": {
        "name": "USASpending.gov",
        "base_url": "https://www.usaspending.gov/",
        "api_url": "https://api.usaspending.gov/api/v2/",
        "description": "Primary source for federal spending data",
    },
    "fpds": {
        "name": "FPDS",
        "base_url": "https://www.fpds.gov/",
        "api_url": "https://www.fpds.gov/ezsearch/search.do",
        "description": "Federal Procurement Data System",
    },
    "sam": {
        "name": "SAM.gov",
        "base_url": "https://sam.gov/",
        "api_url": "https://api.sam.gov/",
        "description": "System for Award Management - entity data",
    },
    "grants": {
        "name": "Grants.gov",
        "base_url": "https://www.grants.gov/",
        "api_url": "https://www.grants.gov/grantsws/",
        "description": "Federal grants data",
    },
    "sbir": {
        "name": "SBIR/STTR",
        "base_url": "https://www.sbir.gov/",
        "description": "Small Business Innovation Research awards",
    },
    "usaid": {
        "name": "USAID",
        "base_url": "https://explorer.usaid.gov/",
        "description": "Foreign assistance data",
    },
}

# State procurement portals
STATE_PROCUREMENT_SOURCES: Dict[str, Dict[str, str]] = {
    "CA": {
        "portal": "https://caleprocure.ca.gov/",
        "name": "Cal eProcure",
    },
    "TX": {
        "portal": "https://www.txsmartbuy.com/",
        "name": "Texas SmartBuy",
    },
    "NY": {
        "portal": "https://ogs.ny.gov/procurement",
        "name": "NY OGS Procurement",
    },
    "FL": {
        "portal": "https://www.dms.myflorida.com/business_operations/state_purchasing",
        "name": "Florida MyFloridaMarketPlace",
    },
    "PA": {
        "portal": "https://www.dgs.pa.gov/",
        "name": "PA Department of General Services",
    },
    "IL": {
        "portal": "https://www.illinois.gov/cms/procurement/",
        "name": "Illinois BidBuy",
    },
    "OH": {
        "portal": "https://procure.ohio.gov/",
        "name": "Ohio Procurement",
    },
    "GA": {
        "portal": "https://doas.ga.gov/state-purchasing",
        "name": "Georgia Procurement",
    },
    "NC": {
        "portal": "https://ncadmin.nc.gov/government-agencies/procurement",
        "name": "NC E-Procurement",
    },
    "MI": {
        "portal": "https://www.michigan.gov/dtmb/procurement",
        "name": "Michigan SIGMA",
    },
    "NJ": {
        "portal": "https://www.state.nj.us/treasury/purchase/",
        "name": "NJ Division of Purchase",
    },
    "VA": {
        "portal": "https://eva.virginia.gov/",
        "name": "Virginia eVA",
    },
    "WA": {
        "portal": "https://des.wa.gov/services/contracting-purchasing",
        "name": "Washington WEBS",
    },
    "AZ": {
        "portal": "https://spo.az.gov/",
        "name": "Arizona SPO",
    },
    "MA": {
        "portal": "https://www.mass.gov/topics/procurement",
        "name": "COMMBUYS",
    },
}


class GovernmentContractsScraper:
    """
    Scraper for government contract records.

    Features:
    - Federal contract searches via USASpending
    - FPDS procurement data
    - State procurement portals
    - Grant and award data
    - Contractor lookup
    """

    CATEGORY = "government_contracts"
    DISPLAY_NAME = "Government Contracts"

    def __init__(self):
        """Initialize the government contracts scraper."""
        self.federal_sources = FEDERAL_CONTRACT_SOURCES
        self.state_sources = STATE_PROCUREMENT_SOURCES
        self.records: List[ContractRecord] = []
        logger.info("GovernmentContractsScraper initialized")

    def search_federal_contracts(
        self,
        recipient_name: str = "",
        awarding_agency: str = "",
        naics_code: str = "",
        state: str = "",
        min_amount: float = None,
        max_amount: float = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> List[ContractRecord]:
        """
        Search federal contracts via USASpending API.

        Args:
            recipient_name: Recipient/contractor name
            awarding_agency: Awarding agency filter
            naics_code: NAICS code filter
            state: State filter
            min_amount: Minimum award amount
            max_amount: Maximum award amount
            start_date: Award start date
            end_date: Award end date

        Returns:
            List of contract records
        """
        logger.info(f"Searching federal contracts")
        contracts = []

        # Would implement actual USASpending API call
        return contracts

    def get_contract_by_id(self, contract_id: str) -> Optional[ContractRecord]:
        """
        Get contract details by ID.

        Args:
            contract_id: Contract/award ID

        Returns:
            Contract record if found
        """
        logger.info(f"Getting contract {contract_id}")
        # Would implement actual contract lookup
        return None

    def search_grants(
        self,
        recipient_name: str = "",
        awarding_agency: str = "",
        cfda_number: str = "",
        state: str = "",
        min_amount: float = None,
        max_amount: float = None,
    ) -> List[ContractRecord]:
        """
        Search federal grants.

        Args:
            recipient_name: Recipient name
            awarding_agency: Awarding agency
            cfda_number: CFDA program number
            state: State filter
            min_amount: Minimum amount
            max_amount: Maximum amount

        Returns:
            List of grant records
        """
        logger.info(f"Searching federal grants")
        grants = []

        # Would implement actual grants search
        return grants

    def get_contractor_profile(
        self, uei: str = "", duns: str = "", name: str = ""
    ) -> Dict[str, Any]:
        """
        Get contractor profile from SAM.gov.

        Args:
            uei: Unique Entity ID
            duns: DUNS number (legacy)
            name: Company name

        Returns:
            Contractor profile data
        """
        logger.info(f"Getting contractor profile")
        # Would implement actual SAM.gov lookup
        return {}

    def search_subcontracts(
        self, prime_contract_id: str = "", subcontractor_name: str = "", state: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Search subcontract data.

        Args:
            prime_contract_id: Prime contract ID
            subcontractor_name: Subcontractor name
            state: State filter

        Returns:
            List of subcontract records
        """
        logger.info(f"Searching subcontracts")
        subcontracts = []

        # Would implement actual subcontract search
        return subcontracts

    def get_agency_spending(
        self, agency: str, fiscal_year: int = None
    ) -> Dict[str, Any]:
        """
        Get spending summary for an agency.

        Args:
            agency: Agency name or code
            fiscal_year: Fiscal year

        Returns:
            Agency spending summary
        """
        year = fiscal_year or datetime.now().year
        logger.info(f"Getting spending for {agency} FY{year}")
        # Would implement actual agency spending lookup
        return {}

    def search_state_contracts(
        self,
        state: str,
        vendor_name: str = "",
        contract_type: str = "",
        agency: str = "",
    ) -> List[ContractRecord]:
        """
        Search state procurement contracts.

        Args:
            state: State code
            vendor_name: Vendor name
            contract_type: Contract type filter
            agency: State agency filter

        Returns:
            List of state contract records
        """
        if state.upper() not in self.state_sources:
            logger.warning(f"No procurement source for state {state}")
            return []

        logger.info(f"Searching {state} state contracts")
        contracts = []

        # Would implement actual state procurement search
        return contracts

    def get_small_business_awards(
        self, state: str = "", business_type: str = "", fiscal_year: int = None
    ) -> List[ContractRecord]:
        """
        Get small business contract awards.

        Args:
            state: State filter
            business_type: Business type (women-owned, veteran, etc.)
            fiscal_year: Fiscal year

        Returns:
            List of small business awards
        """
        logger.info(f"Getting small business awards")
        awards = []

        # Would implement actual small business search
        return awards

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        return {
            "category": self.CATEGORY,
            "display_name": self.DISPLAY_NAME,
            "federal_sources": len(self.federal_sources),
            "federal_source_names": list(self.federal_sources.keys()),
            "states_with_procurement": len(self.state_sources),
            "states": list(self.state_sources.keys()),
            "contract_types": [t.value for t in ContractType],
            "competition_types": [t.value for t in CompetitionType],
        }


# Module-level convenience functions
def get_contracts_scraper() -> GovernmentContractsScraper:
    """Get government contracts scraper instance."""
    return GovernmentContractsScraper()


def search_contracts(
    recipient_name: str = "", state: str = "", **kwargs
) -> List[Dict[str, Any]]:
    """Search federal contracts."""
    scraper = get_contracts_scraper()
    records = scraper.search_federal_contracts(
        recipient_name=recipient_name, state=state, **kwargs
    )
    return [r.to_dict() for r in records]


def get_available_sources() -> Dict[str, Any]:
    """Get all available contract sources."""
    return {
        "federal_sources": FEDERAL_CONTRACT_SOURCES,
        "state_sources": STATE_PROCUREMENT_SOURCES,
    }
