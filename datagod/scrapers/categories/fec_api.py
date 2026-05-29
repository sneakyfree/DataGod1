"""
FEC (Federal Election Commission) API Integration

Provides access to campaign finance data:
- Candidate information and filings
- Committee registrations
- Individual contributions
- Expenditures
- Independent expenditures

API Documentation: https://api.open.fec.gov/developers/
Rate Limit: 1000 requests per hour with API key
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class CandidateOffice(Enum):
    """Office types for candidates"""

    PRESIDENT = "P"
    SENATE = "S"
    HOUSE = "H"


class CandidateStatus(Enum):
    """Candidate status codes"""

    CANDIDATE = "C"
    FUTURE = "F"
    NOT_YET = "N"
    PRIOR = "P"


class PartyAffiliation(Enum):
    """Major party affiliations"""

    DEMOCRATIC = "DEM"
    REPUBLICAN = "REP"
    LIBERTARIAN = "LIB"
    GREEN = "GRE"
    INDEPENDENT = "IND"
    OTHER = "OTH"


class CommitteeType(Enum):
    """FEC Committee types"""

    PRESIDENTIAL = "P"
    HOUSE = "H"
    SENATE = "S"
    PARTY = "X"
    PAC = "N"  # Non-qualified (PAC)
    SUPER_PAC = "O"  # Independent Expenditure Only
    HYBRID_PAC = "V"
    JOINT = "J"
    LEADERSHIP = "D"


@dataclass
class FECCandidate:
    """Represents an FEC registered candidate"""

    candidate_id: str
    name: str
    party: Optional[str] = None
    office: Optional[CandidateOffice] = None
    state: Optional[str] = None
    district: Optional[str] = None
    incumbent_challenger: Optional[str] = None
    candidate_status: Optional[CandidateStatus] = None
    principal_committees: List[str] = field(default_factory=list)
    cycles: List[int] = field(default_factory=list)
    first_file_date: Optional[date] = None
    last_file_date: Optional[date] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    total_receipts: Optional[float] = None
    total_disbursements: Optional[float] = None
    cash_on_hand: Optional[float] = None
    debts_owed: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "party": self.party,
            "office": self.office.value if self.office else None,
            "state": self.state,
            "district": self.district,
            "incumbent_challenger": self.incumbent_challenger,
            "candidate_status": (
                self.candidate_status.value if self.candidate_status else None
            ),
            "principal_committees": self.principal_committees,
            "cycles": self.cycles,
            "first_file_date": (
                self.first_file_date.isoformat() if self.first_file_date else None
            ),
            "last_file_date": (
                self.last_file_date.isoformat() if self.last_file_date else None
            ),
            "total_receipts": self.total_receipts,
            "total_disbursements": self.total_disbursements,
            "cash_on_hand": self.cash_on_hand,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class FECCommittee:
    """Represents an FEC registered committee"""

    committee_id: str
    name: str
    committee_type: Optional[CommitteeType] = None
    designation: Optional[str] = None
    party: Optional[str] = None
    state: Optional[str] = None
    treasurer_name: Optional[str] = None
    organization_type: Optional[str] = None
    first_file_date: Optional[date] = None
    last_file_date: Optional[date] = None
    cycles: List[int] = field(default_factory=list)
    candidate_ids: List[str] = field(default_factory=list)
    total_receipts: Optional[float] = None
    total_disbursements: Optional[float] = None
    cash_on_hand: Optional[float] = None
    debts_owed: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "committee_id": self.committee_id,
            "name": self.name,
            "committee_type": (
                self.committee_type.value if self.committee_type else None
            ),
            "designation": self.designation,
            "party": self.party,
            "state": self.state,
            "treasurer_name": self.treasurer_name,
            "organization_type": self.organization_type,
            "cycles": self.cycles,
            "candidate_ids": self.candidate_ids,
            "total_receipts": self.total_receipts,
            "total_disbursements": self.total_disbursements,
            "cash_on_hand": self.cash_on_hand,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class FECContribution:
    """Represents an individual contribution"""

    transaction_id: str
    contributor_name: str
    amount: float
    contribution_date: Optional[date] = None
    contributor_city: Optional[str] = None
    contributor_state: Optional[str] = None
    contributor_zip: Optional[str] = None
    contributor_employer: Optional[str] = None
    contributor_occupation: Optional[str] = None
    committee_id: Optional[str] = None
    committee_name: Optional[str] = None
    candidate_id: Optional[str] = None
    candidate_name: Optional[str] = None
    receipt_type: Optional[str] = None
    election_type: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "contributor_name": self.contributor_name,
            "amount": self.amount,
            "contribution_date": (
                self.contribution_date.isoformat() if self.contribution_date else None
            ),
            "contributor_city": self.contributor_city,
            "contributor_state": self.contributor_state,
            "contributor_zip": self.contributor_zip,
            "contributor_employer": self.contributor_employer,
            "contributor_occupation": self.contributor_occupation,
            "committee_id": self.committee_id,
            "committee_name": self.committee_name,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name,
            "fetched_at": self.fetched_at.isoformat(),
        }


class FECApiClient:
    """
    Client for the FEC (Federal Election Commission) API.

    Provides access to campaign finance data including candidates,
    committees, and contributions.

    API Key: Free from https://api.open.fec.gov/developers/
    Rate Limit: 1000 requests/hour
    """

    BASE_URL = "https://api.open.fec.gov/v1"

    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        """
        Initialize FEC API client.

        Args:
            api_key: FEC API key (free from api.open.fec.gov)
            config: Optional configuration dictionary
        """
        self.api_key = api_key
        self.config = config or {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit = self.config.get("rate_limit", 1000)
        self.requests_made = 0
        logger.info("Initialized FEC API Client")

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def _request(
        self, endpoint: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make API request to FEC.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data
        """
        await self._ensure_session()

        url = f"{self.BASE_URL}{endpoint}"
        params = params or {}
        params["api_key"] = self.api_key

        try:
            async with self.session.get(url, params=params) as response:
                self.requests_made += 1

                if response.status == 429:
                    logger.warning("FEC API rate limit exceeded")
                    await asyncio.sleep(60)
                    return await self._request(endpoint, params)

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"FEC API request failed: {e}")
            raise

    async def search_candidates(
        self,
        name: str = None,
        state: str = None,
        office: CandidateOffice = None,
        party: str = None,
        cycle: int = None,
        per_page: int = 20,
    ) -> List[FECCandidate]:
        """
        Search for candidates.

        Args:
            name: Candidate name search
            state: Two-letter state code
            office: Office type (P, S, H)
            party: Party affiliation
            cycle: Election cycle (e.g., 2024)
            per_page: Results per page

        Returns:
            List of FECCandidate objects
        """
        params = {"per_page": per_page, "sort": "-receipts"}

        if name:
            params["q"] = name
        if state:
            params["state"] = state
        if office:
            params["office"] = office.value
        if party:
            params["party"] = party
        if cycle:
            params["cycle"] = cycle

        data = await self._request("/candidates/search/", params)

        candidates = []
        for result in data.get("results", []):
            candidate = FECCandidate(
                candidate_id=result.get("candidate_id", ""),
                name=result.get("name", ""),
                party=result.get("party", result.get("party_full")),
                office=self._parse_office(result.get("office")),
                state=result.get("state"),
                district=result.get("district"),
                incumbent_challenger=result.get("incumbent_challenge"),
                cycles=result.get("cycles", []),
                total_receipts=result.get("receipts"),
                total_disbursements=result.get("disbursements"),
                cash_on_hand=result.get("cash_on_hand_end_period"),
                raw_data=result,
            )
            candidates.append(candidate)

        return candidates

    async def get_candidate(self, candidate_id: str) -> Optional[FECCandidate]:
        """
        Get detailed candidate information.

        Args:
            candidate_id: FEC candidate ID (e.g., P80001571)

        Returns:
            FECCandidate object or None
        """
        data = await self._request(f"/candidate/{candidate_id}/")

        results = data.get("results", [])
        if not results:
            return None

        result = results[0]
        return FECCandidate(
            candidate_id=result.get("candidate_id", ""),
            name=result.get("name", ""),
            party=result.get("party_full"),
            office=self._parse_office(result.get("office")),
            state=result.get("state"),
            district=result.get("district"),
            incumbent_challenger=result.get("incumbent_challenge"),
            candidate_status=self._parse_status(result.get("candidate_status")),
            principal_committees=result.get("principal_committees", []),
            cycles=result.get("cycles", []),
            first_file_date=self._parse_date(result.get("first_file_date")),
            last_file_date=self._parse_date(result.get("last_file_date")),
            address_city=result.get("address_city"),
            address_state=result.get("address_state"),
            address_zip=result.get("address_zip"),
            raw_data=result,
        )

    async def search_committees(
        self,
        name: str = None,
        state: str = None,
        committee_type: CommitteeType = None,
        cycle: int = None,
        per_page: int = 20,
    ) -> List[FECCommittee]:
        """
        Search for committees (PACs, Super PACs, party committees).

        Args:
            name: Committee name search
            state: Two-letter state code
            committee_type: Type of committee
            cycle: Election cycle
            per_page: Results per page

        Returns:
            List of FECCommittee objects
        """
        params = {"per_page": per_page, "sort": "-receipts"}

        if name:
            params["q"] = name
        if state:
            params["state"] = state
        if committee_type:
            params["committee_type"] = committee_type.value
        if cycle:
            params["cycle"] = cycle

        data = await self._request("/committees/", params)

        committees = []
        for result in data.get("results", []):
            committee = FECCommittee(
                committee_id=result.get("committee_id", ""),
                name=result.get("name", ""),
                committee_type=self._parse_committee_type(result.get("committee_type")),
                designation=result.get("designation_full"),
                party=result.get("party_full"),
                state=result.get("state"),
                treasurer_name=result.get("treasurer_name"),
                organization_type=result.get("organization_type_full"),
                cycles=result.get("cycles", []),
                candidate_ids=result.get("candidate_ids", []),
                raw_data=result,
            )
            committees.append(committee)

        return committees

    async def get_contributions(
        self,
        committee_id: str = None,
        contributor_name: str = None,
        contributor_city: str = None,
        contributor_state: str = None,
        contributor_employer: str = None,
        min_amount: float = None,
        max_amount: float = None,
        two_year_transaction_period: int = None,
        per_page: int = 20,
    ) -> List[FECContribution]:
        """
        Search for individual contributions.

        Args:
            committee_id: Receiving committee ID
            contributor_name: Contributor name search
            contributor_city: Contributor city
            contributor_state: Contributor state
            contributor_employer: Employer search
            min_amount: Minimum contribution amount
            max_amount: Maximum contribution amount
            two_year_transaction_period: Election cycle (e.g., 2024)
            per_page: Results per page

        Returns:
            List of FECContribution objects
        """
        params = {"per_page": per_page, "sort": "-contribution_receipt_date"}

        if committee_id:
            params["committee_id"] = committee_id
        if contributor_name:
            params["contributor_name"] = contributor_name
        if contributor_city:
            params["contributor_city"] = contributor_city
        if contributor_state:
            params["contributor_state"] = contributor_state
        if contributor_employer:
            params["contributor_employer"] = contributor_employer
        if min_amount:
            params["min_amount"] = min_amount
        if max_amount:
            params["max_amount"] = max_amount
        if two_year_transaction_period:
            params["two_year_transaction_period"] = two_year_transaction_period

        data = await self._request("/schedules/schedule_a/", params)

        contributions = []
        for result in data.get("results", []):
            contribution = FECContribution(
                transaction_id=result.get("transaction_id", result.get("sub_id", "")),
                contributor_name=result.get("contributor_name", ""),
                amount=result.get("contribution_receipt_amount", 0),
                contribution_date=self._parse_date(
                    result.get("contribution_receipt_date")
                ),
                contributor_city=result.get("contributor_city"),
                contributor_state=result.get("contributor_state"),
                contributor_zip=result.get("contributor_zip"),
                contributor_employer=result.get("contributor_employer"),
                contributor_occupation=result.get("contributor_occupation"),
                committee_id=result.get("committee_id"),
                committee_name=(
                    result.get("committee", {}).get("name")
                    if result.get("committee")
                    else None
                ),
                receipt_type=result.get("receipt_type_full"),
                raw_data=result,
            )
            contributions.append(contribution)

        return contributions

    async def get_candidate_totals(
        self,
        candidate_id: str = None,
        cycle: int = None,
        office: CandidateOffice = None,
        state: str = None,
        per_page: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get aggregate financial totals for candidates.

        Args:
            candidate_id: Specific candidate ID
            cycle: Election cycle
            office: Office type
            state: State code
            per_page: Results per page

        Returns:
            List of financial summary dictionaries
        """
        params = {"per_page": per_page, "sort": "-receipts"}

        if candidate_id:
            params["candidate_id"] = candidate_id
        if cycle:
            params["cycle"] = cycle
        if office:
            params["office"] = office.value
        if state:
            params["state"] = state

        data = await self._request("/candidates/totals/", params)
        return data.get("results", [])

    def _parse_office(self, office_code: str) -> Optional[CandidateOffice]:
        """Parse office code to enum."""
        if not office_code:
            return None
        try:
            return CandidateOffice(office_code)
        except ValueError:
            return None

    def _parse_status(self, status_code: str) -> Optional[CandidateStatus]:
        """Parse status code to enum."""
        if not status_code:
            return None
        try:
            return CandidateStatus(status_code)
        except ValueError:
            return None

    def _parse_committee_type(self, type_code: str) -> Optional[CommitteeType]:
        """Parse committee type code to enum."""
        if not type_code:
            return None
        try:
            return CommitteeType(type_code)
        except ValueError:
            return None

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()


# Synchronous wrapper functions for convenience
def search_fec_candidates(
    api_key: str,
    name: str = None,
    state: str = None,
    office: str = None,
    cycle: int = None,
) -> List[FECCandidate]:
    """
    Synchronous wrapper to search FEC candidates.

    Args:
        api_key: FEC API key
        name: Candidate name
        state: State code
        office: Office type (P, S, H)
        cycle: Election cycle

    Returns:
        List of FECCandidate objects
    """

    async def _search():
        client = FECApiClient(api_key)
        try:
            office_enum = CandidateOffice(office) if office else None
            return await client.search_candidates(
                name=name, state=state, office=office_enum, cycle=cycle
            )
        finally:
            await client.close()

    return asyncio.run(_search())


def search_fec_contributions(
    api_key: str,
    contributor_name: str = None,
    contributor_state: str = None,
    min_amount: float = None,
    cycle: int = None,
) -> List[FECContribution]:
    """
    Synchronous wrapper to search FEC contributions.

    Args:
        api_key: FEC API key
        contributor_name: Contributor name
        contributor_state: State code
        min_amount: Minimum amount
        cycle: Election cycle

    Returns:
        List of FECContribution objects
    """

    async def _search():
        client = FECApiClient(api_key)
        try:
            return await client.get_contributions(
                contributor_name=contributor_name,
                contributor_state=contributor_state,
                min_amount=min_amount,
                two_year_transaction_period=cycle,
            )
        finally:
            await client.close()

    return asyncio.run(_search())
