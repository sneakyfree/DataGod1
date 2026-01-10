"""
Court Records Scraper Module

Provides unified access to court records across jurisdictions:
- Case search (civil, criminal, family, probate)
- Party search (plaintiff, defendant, petitioner)
- Judgment and lien search
- Court document retrieval

Supports:
- State court portals
- PACER (federal courts)
- County clerk sites
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class CaseType(Enum):
    """Types of court cases"""
    CIVIL = "civil"
    CRIMINAL = "criminal"
    FAMILY = "family"
    PROBATE = "probate"
    BANKRUPTCY = "bankruptcy"
    SMALL_CLAIMS = "small_claims"
    TAX = "tax"
    TRAFFIC = "traffic"
    JUVENILE = "juvenile"
    APPELLATE = "appellate"
    UNKNOWN = "unknown"


class CaseStatus(Enum):
    """Case status values"""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    DISMISSED = "dismissed"
    SETTLED = "settled"
    APPEALED = "appealed"
    ON_HOLD = "on_hold"
    UNKNOWN = "unknown"


class PartyType(Enum):
    """Types of case parties"""
    PLAINTIFF = "plaintiff"
    DEFENDANT = "defendant"
    PETITIONER = "petitioner"
    RESPONDENT = "respondent"
    APPELLANT = "appellant"
    APPELLEE = "appellee"
    CREDITOR = "creditor"
    DEBTOR = "debtor"
    WITNESS = "witness"
    ATTORNEY = "attorney"
    JUDGE = "judge"
    OTHER = "other"


@dataclass
class CaseParty:
    """Represents a party in a court case"""
    name: str
    party_type: PartyType
    party_id: Optional[str] = None
    address: Optional[str] = None
    attorney_name: Optional[str] = None
    attorney_firm: Optional[str] = None
    is_business: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'party_type': self.party_type.value,
            'party_id': self.party_id,
            'address': self.address,
            'attorney_name': self.attorney_name,
            'attorney_firm': self.attorney_firm,
            'is_business': self.is_business
        }


@dataclass
class CourtCase:
    """Represents a court case record"""
    case_number: str
    case_type: CaseType
    court_name: str
    filing_date: Optional[date] = None
    case_title: Optional[str] = None
    status: CaseStatus = CaseStatus.UNKNOWN
    judge_name: Optional[str] = None
    parties: List[CaseParty] = field(default_factory=list)
    jurisdiction: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    disposition: Optional[str] = None
    disposition_date: Optional[date] = None
    amount_claimed: Optional[float] = None
    amount_awarded: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'case_number': self.case_number,
            'case_type': self.case_type.value,
            'court_name': self.court_name,
            'filing_date': self.filing_date.isoformat() if self.filing_date else None,
            'case_title': self.case_title,
            'status': self.status.value,
            'judge_name': self.judge_name,
            'parties': [p.to_dict() for p in self.parties],
            'jurisdiction': self.jurisdiction,
            'county': self.county,
            'state': self.state,
            'disposition': self.disposition,
            'disposition_date': self.disposition_date.isoformat() if self.disposition_date else None,
            'amount_claimed': self.amount_claimed,
            'amount_awarded': self.amount_awarded,
            'fetched_at': self.fetched_at.isoformat()
        }

    @property
    def plaintiffs(self) -> List[CaseParty]:
        """Get all plaintiffs/petitioners"""
        return [p for p in self.parties if p.party_type in (PartyType.PLAINTIFF, PartyType.PETITIONER)]

    @property
    def defendants(self) -> List[CaseParty]:
        """Get all defendants/respondents"""
        return [p for p in self.parties if p.party_type in (PartyType.DEFENDANT, PartyType.RESPONDENT)]


@dataclass
class CaseSearch:
    """Search parameters for court cases"""
    case_number: Optional[str] = None
    party_name: Optional[str] = None
    case_type: Optional[CaseType] = None
    court_name: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[CaseStatus] = None
    include_closed: bool = True


@dataclass
class PartySearch:
    """Search parameters for party-based searches"""
    name: str
    party_type: Optional[PartyType] = None
    state: Optional[str] = None
    county: Optional[str] = None
    case_type: Optional[CaseType] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    exact_match: bool = False


class CourtRecordsScraper(ABC):
    """
    Abstract base class for court records scrapers.

    Provides unified interface for accessing court records across
    different court systems and jurisdictions.
    """

    # Case type keywords for classification
    CIVIL_KEYWORDS = ['civil', 'contract', 'tort', 'personal injury', 'negligence', 'breach']
    CRIMINAL_KEYWORDS = ['criminal', 'felony', 'misdemeanor', 'dui', 'dwi', 'theft', 'assault']
    FAMILY_KEYWORDS = ['family', 'divorce', 'custody', 'child support', 'adoption', 'paternity']
    PROBATE_KEYWORDS = ['probate', 'estate', 'will', 'trust', 'guardianship', 'conservatorship']

    def __init__(self, jurisdiction: str, config: Dict[str, Any] = None):
        """
        Initialize the court records scraper.

        Args:
            jurisdiction: Court jurisdiction identifier
            config: Optional configuration dictionary
        """
        self.jurisdiction = jurisdiction
        self.config = config or {}
        self._session = None

        logger.info(f"Initialized CourtRecordsScraper for {jurisdiction}")

    @abstractmethod
    def search_cases(self, search: CaseSearch) -> List[CourtCase]:
        """
        Search for court cases matching criteria.

        Args:
            search: CaseSearch parameters

        Returns:
            List of matching CourtCase objects
        """
        pass

    @abstractmethod
    def search_by_party(self, search: PartySearch) -> List[CourtCase]:
        """
        Search for cases by party name.

        Args:
            search: PartySearch parameters

        Returns:
            List of CourtCase objects involving the party
        """
        pass

    @abstractmethod
    def get_case_details(self, case_number: str) -> Optional[CourtCase]:
        """
        Get detailed information for a specific case.

        Args:
            case_number: Case number/identifier

        Returns:
            CourtCase with full details or None if not found
        """
        pass

    def classify_case_type(self, text: str) -> CaseType:
        """
        Classify case type based on text content.

        Args:
            text: Case title, description, or type string

        Returns:
            Classified CaseType
        """
        text_lower = text.lower()

        if any(kw in text_lower for kw in self.CRIMINAL_KEYWORDS):
            return CaseType.CRIMINAL
        elif any(kw in text_lower for kw in self.FAMILY_KEYWORDS):
            return CaseType.FAMILY
        elif any(kw in text_lower for kw in self.PROBATE_KEYWORDS):
            return CaseType.PROBATE
        elif any(kw in text_lower for kw in self.CIVIL_KEYWORDS):
            return CaseType.CIVIL
        elif 'bankruptcy' in text_lower:
            return CaseType.BANKRUPTCY
        elif 'small claim' in text_lower:
            return CaseType.SMALL_CLAIMS
        elif 'tax' in text_lower:
            return CaseType.TAX
        elif 'traffic' in text_lower:
            return CaseType.TRAFFIC
        elif 'juvenile' in text_lower:
            return CaseType.JUVENILE
        elif 'appeal' in text_lower:
            return CaseType.APPELLATE

        return CaseType.UNKNOWN

    def parse_case_status(self, status_text: str) -> CaseStatus:
        """
        Parse case status from text.

        Args:
            status_text: Status string

        Returns:
            Parsed CaseStatus
        """
        status_lower = status_text.lower().strip()

        if any(s in status_lower for s in ['open', 'active', 'pending trial']):
            return CaseStatus.OPEN
        elif any(s in status_lower for s in ['closed', 'disposed', 'final']):
            return CaseStatus.CLOSED
        elif any(s in status_lower for s in ['pending', 'awaiting']):
            return CaseStatus.PENDING
        elif 'dismiss' in status_lower:
            return CaseStatus.DISMISSED
        elif 'settle' in status_lower:
            return CaseStatus.SETTLED
        elif 'appeal' in status_lower:
            return CaseStatus.APPEALED
        elif any(s in status_lower for s in ['hold', 'stayed', 'abated']):
            return CaseStatus.ON_HOLD

        return CaseStatus.UNKNOWN

    def parse_party_type(self, party_text: str) -> PartyType:
        """
        Parse party type from text.

        Args:
            party_text: Party type string

        Returns:
            Parsed PartyType
        """
        party_lower = party_text.lower().strip()

        if 'plaintiff' in party_lower:
            return PartyType.PLAINTIFF
        elif 'defendant' in party_lower:
            return PartyType.DEFENDANT
        elif 'petitioner' in party_lower:
            return PartyType.PETITIONER
        elif 'respondent' in party_lower:
            return PartyType.RESPONDENT
        elif 'appellant' in party_lower:
            return PartyType.APPELLANT
        elif 'appellee' in party_lower:
            return PartyType.APPELLEE
        elif 'creditor' in party_lower:
            return PartyType.CREDITOR
        elif 'debtor' in party_lower:
            return PartyType.DEBTOR
        elif 'attorney' in party_lower or 'counsel' in party_lower:
            return PartyType.ATTORNEY
        elif 'judge' in party_lower:
            return PartyType.JUDGE
        elif 'witness' in party_lower:
            return PartyType.WITNESS

        return PartyType.OTHER

    def normalize_case_number(self, case_number: str) -> str:
        """
        Normalize case number format.

        Args:
            case_number: Raw case number string

        Returns:
            Normalized case number
        """
        # Remove extra whitespace
        normalized = ' '.join(case_number.split())

        # Standardize common separators
        normalized = normalized.replace(' - ', '-').replace(' / ', '/')

        return normalized.upper()

    def parse_amount(self, amount_str: str) -> Optional[float]:
        """
        Parse monetary amount from string.

        Args:
            amount_str: Amount string (e.g., "$1,234.56")

        Returns:
            Float amount or None if parsing fails
        """
        if not amount_str:
            return None

        try:
            # Remove currency symbols, commas, and whitespace
            cleaned = re.sub(r'[\$,\s]', '', amount_str)
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date from various formats.

        Args:
            date_str: Date string

        Returns:
            Parsed date or None
        """
        if not date_str:
            return None

        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m-%d-%Y',
            '%Y%m%d',
            '%d-%b-%Y',
            '%B %d, %Y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get scraper statistics."""
        return {
            'jurisdiction': self.jurisdiction,
            'scraper_class': self.__class__.__name__,
        }


class StateCourtScraper(CourtRecordsScraper):
    """
    Generic state court scraper that can be configured for different states.
    """

    def __init__(self, state_code: str, config: Dict[str, Any] = None):
        """
        Initialize state court scraper.

        Args:
            state_code: Two-letter state code
            config: State-specific configuration
        """
        super().__init__(jurisdiction=state_code, config=config)
        self.state_code = state_code.upper()
        self.base_url = config.get('base_url', '') if config else ''
        self.court_api = config.get('court_api', '') if config else ''

    def search_cases(self, search: CaseSearch) -> List[CourtCase]:
        """Search for court cases in this state."""
        # Implementation would vary by state
        logger.info(f"Searching cases in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return []

    def search_by_party(self, search: PartySearch) -> List[CourtCase]:
        """Search for cases by party name."""
        logger.info(f"Searching by party '{search.name}' in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return []

    def get_case_details(self, case_number: str) -> Optional[CourtCase]:
        """Get detailed case information."""
        logger.info(f"Getting case details for {case_number} in {self.state_code}")

        # Placeholder - actual implementation would make API calls
        return None


def search_court_records(
    party_name: str,
    states: List[str] = None,
    case_types: List[CaseType] = None,
    date_from: date = None,
    date_to: date = None
) -> List[CourtCase]:
    """
    Convenience function to search court records across multiple jurisdictions.

    Args:
        party_name: Name to search for
        states: List of state codes to search (None = all available)
        case_types: Types of cases to include
        date_from: Start date filter
        date_to: End date filter

    Returns:
        List of matching CourtCase objects
    """
    results = []

    # Create search parameters
    search = PartySearch(
        name=party_name,
        date_from=date_from,
        date_to=date_to
    )

    # Would iterate through configured state scrapers
    logger.info(f"Searching court records for '{party_name}'")

    return results
