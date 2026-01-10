"""
Voter Records Scraper

Free public voter/election records sources:
- FEC (Federal Election Commission) - Campaign finance
- State voter registration lookup (varies by state)
- Campaign contribution records
- Election results (state/county)
- Ballot measures and initiatives

Note: Voter file access varies significantly by state.
Some states make full voter files public, others restrict access.

Free Sources Integrated:
- FEC API (api.open.fec.gov) - Federal campaign finance (API key recommended)
- OpenSecrets (opensecrets.org) - Campaign finance analysis
- Follow The Money (followthemoney.org) - State campaign finance
- State election websites - Results and registration lookup
- Vote Smart API (votesmart.org) - Candidate information
"""

import asyncio
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode, quote_plus

logger = logging.getLogger(__name__)

# Try to import aiohttp for async requests
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available, async methods will be limited")


class VoterStatus(Enum):
    """Voter registration status"""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"
    CANCELLED = "Cancelled"
    PURGED = "Purged"
    SUSPENDED = "Suspended"
    UNKNOWN = "Unknown"


class PartyRegistration(Enum):
    """Party registration"""
    DEMOCRATIC = "Democratic"
    REPUBLICAN = "Republican"
    LIBERTARIAN = "Libertarian"
    GREEN = "Green"
    INDEPENDENT = "Independent"
    NO_PARTY = "No Party Preference"
    CONSTITUTION = "Constitution"
    REFORM = "Reform"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class ElectionType(Enum):
    """Election types"""
    GENERAL = "General"
    PRIMARY = "Primary"
    RUNOFF = "Runoff"
    SPECIAL = "Special"
    LOCAL = "Local"
    MUNICIPAL = "Municipal"
    PRESIDENTIAL = "Presidential"
    MIDTERM = "Midterm"


class VoterFileAccess(Enum):
    """State voter file access levels"""
    PUBLIC = "Public"
    REGISTERED_VOTERS = "Registered Voters Only"
    CANDIDATES_PARTIES = "Candidates/Parties Only"
    RESTRICTED = "Restricted"
    NOT_AVAILABLE = "Not Available Online"
    FEE_REQUIRED = "Fee Required"


class ContributionType(Enum):
    """Types of campaign contributions"""
    INDIVIDUAL = "Individual"
    PAC = "Political Action Committee"
    PARTY = "Party Committee"
    CANDIDATE = "Candidate"
    SUPER_PAC = "Super PAC"
    CORPORATE = "Corporate"
    UNION = "Union"
    OTHER = "Other"


@dataclass
class VoterRegistration:
    """Voter registration record"""
    voter_id: str
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    registration_date: Optional[date] = None
    status: VoterStatus = VoterStatus.UNKNOWN
    party: PartyRegistration = PartyRegistration.UNKNOWN
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    precinct: Optional[str] = None
    congressional_district: Optional[str] = None
    state_senate_district: Optional[str] = None
    state_house_district: Optional[str] = None
    voting_history: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    lookup_url: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'voter_id': self.voter_id,
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'middle_name': self.middle_name,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'status': self.status.value,
            'party': self.party.value,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'county': self.county,
            'precinct': self.precinct,
            'congressional_district': self.congressional_district,
            'state_senate_district': self.state_senate_district,
            'state_house_district': self.state_house_district,
            'voting_history': self.voting_history,
            'source_url': self.source_url,
            'lookup_url': self.lookup_url,
            'fetched_at': self.fetched_at.isoformat()
        }


@dataclass
class CampaignContribution:
    """Campaign contribution record"""
    contributor_name: str
    amount: float
    contribution_date: Optional[date] = None
    recipient_name: Optional[str] = None
    recipient_id: Optional[str] = None
    recipient_type: Optional[str] = None
    election_cycle: Optional[str] = None
    contributor_employer: Optional[str] = None
    contributor_occupation: Optional[str] = None
    contributor_city: Optional[str] = None
    contributor_state: Optional[str] = None
    contributor_zip: Optional[str] = None
    receipt_type: Optional[str] = None
    contribution_type: ContributionType = ContributionType.INDIVIDUAL
    transaction_id: Optional[str] = None
    filing_id: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'contributor_name': self.contributor_name,
            'amount': self.amount,
            'contribution_date': self.contribution_date.isoformat() if self.contribution_date else None,
            'recipient_name': self.recipient_name,
            'recipient_id': self.recipient_id,
            'recipient_type': self.recipient_type,
            'election_cycle': self.election_cycle,
            'contributor_employer': self.contributor_employer,
            'contributor_occupation': self.contributor_occupation,
            'contributor_city': self.contributor_city,
            'contributor_state': self.contributor_state,
            'contributor_zip': self.contributor_zip,
            'receipt_type': self.receipt_type,
            'contribution_type': self.contribution_type.value,
            'transaction_id': self.transaction_id,
            'filing_id': self.filing_id,
            'source': self.source,
            'source_url': self.source_url,
            'fetched_at': self.fetched_at.isoformat()
        }


@dataclass
class Candidate:
    """Candidate information"""
    name: str
    candidate_id: Optional[str] = None
    party: PartyRegistration = PartyRegistration.UNKNOWN
    office: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    election_year: Optional[int] = None
    incumbent: bool = False
    total_receipts: Optional[float] = None
    total_disbursements: Optional[float] = None
    cash_on_hand: Optional[float] = None
    source_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'candidate_id': self.candidate_id,
            'party': self.party.value,
            'office': self.office,
            'state': self.state,
            'district': self.district,
            'election_year': self.election_year,
            'incumbent': self.incumbent,
            'total_receipts': self.total_receipts,
            'total_disbursements': self.total_disbursements,
            'cash_on_hand': self.cash_on_hand,
            'source_url': self.source_url
        }


@dataclass
class Committee:
    """Political committee/PAC information"""
    name: str
    committee_id: str
    committee_type: Optional[str] = None
    designation: Optional[str] = None
    party: Optional[str] = None
    state: Optional[str] = None
    treasurer_name: Optional[str] = None
    total_receipts: Optional[float] = None
    total_disbursements: Optional[float] = None
    cash_on_hand: Optional[float] = None
    filing_frequency: Optional[str] = None
    first_file_date: Optional[date] = None
    source_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'committee_id': self.committee_id,
            'committee_type': self.committee_type,
            'designation': self.designation,
            'party': self.party,
            'state': self.state,
            'treasurer_name': self.treasurer_name,
            'total_receipts': self.total_receipts,
            'total_disbursements': self.total_disbursements,
            'cash_on_hand': self.cash_on_hand,
            'filing_frequency': self.filing_frequency,
            'first_file_date': self.first_file_date.isoformat() if self.first_file_date else None,
            'source_url': self.source_url
        }


@dataclass
class ElectionResult:
    """Election result record"""
    election_date: date
    election_type: ElectionType = ElectionType.GENERAL
    office: Optional[str] = None
    jurisdiction: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    total_votes: Optional[int] = None
    winner: Optional[str] = None
    registered_voters: Optional[int] = None
    turnout_percentage: Optional[float] = None
    source_url: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'election_date': self.election_date.isoformat(),
            'election_type': self.election_type.value,
            'office': self.office,
            'jurisdiction': self.jurisdiction,
            'state': self.state,
            'county': self.county,
            'candidates': self.candidates,
            'total_votes': self.total_votes,
            'winner': self.winner,
            'registered_voters': self.registered_voters,
            'turnout_percentage': self.turnout_percentage,
            'source_url': self.source_url,
            'fetched_at': self.fetched_at.isoformat()
        }


@dataclass
class StateVoterAccess:
    """State voter file access information"""
    state: str
    state_name: str
    access_level: VoterFileAccess
    registration_lookup_url: Optional[str] = None
    election_results_url: Optional[str] = None
    voter_file_cost: Optional[str] = None
    eligible_requesters: Optional[str] = None
    data_available: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'state': self.state,
            'state_name': self.state_name,
            'access_level': self.access_level.value,
            'registration_lookup_url': self.registration_lookup_url,
            'election_results_url': self.election_results_url,
            'voter_file_cost': self.voter_file_cost,
            'eligible_requesters': self.eligible_requesters,
            'data_available': self.data_available,
            'notes': self.notes
        }


# =============================================================================
# State Voter Data Configurations
# =============================================================================

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"
}

STATE_VOTER_LOOKUP: Dict[str, str] = {
    "AL": "https://myinfo.alabamavotes.gov/voterview",
    "AK": "https://myvoterinformation.alaska.gov/",
    "AZ": "https://my.arizona.vote/PortalList.aspx",
    "AR": "https://www.voterview.ar-nova.org/VoterView",
    "CA": "https://voterstatus.sos.ca.gov/",
    "CO": "https://www.sos.state.co.us/voter/pages/pub/olvr/findVoterReg.xhtml",
    "CT": "https://portaldir.ct.gov/sots/LookUp.aspx",
    "DE": "https://ivote.de.gov/voterview",
    "FL": "https://registration.elections.myflorida.com/CheckVoterStatus",
    "GA": "https://mvp.sos.ga.gov/s/",
    "HI": "https://olvr.hawaii.gov/",
    "ID": "https://elections.sos.idaho.gov/ElectionLink/ElectionLink/VoterSearch.aspx",
    "IL": "https://ova.elections.il.gov/RegistrationLookup.aspx",
    "IN": "https://indianavoters.in.gov/",
    "IA": "https://sos.iowa.gov/elections/VoterReg/RegToVote/search.aspx",
    "KS": "https://myvoteinfo.voteks.org/VoterView",
    "KY": "https://vrsws.sos.ky.gov/VIC/",
    "LA": "https://voterportal.sos.la.gov/",
    "ME": "https://www.maine.gov/portal/government/edemocracy/voter_lookup.php",
    "MD": "https://voterservices.elections.maryland.gov/VoterSearch",
    "MA": "https://www.sec.state.ma.us/VoterRegistrationSearch/MyVoterRegStatus.aspx",
    "MI": "https://mvic.sos.state.mi.us/",
    "MN": "https://mnvotes.sos.state.mn.us/VoterStatus.aspx",
    "MS": "https://www.msegov.com/sos/voter_registration/amiregistered/Search",
    "MO": "https://voteroutreach.sos.mo.gov/portal/",
    "MT": "https://app.mt.gov/voterinfo/",
    "NE": "https://www.votercheck.necvr.ne.gov/VoterView",
    "NV": "https://www.nvsos.gov/votersearch/",
    "NH": "https://app.sos.nh.gov/viphome",
    "NJ": "https://voter.svrs.nj.gov/registration-check",
    "NM": "https://voterportal.servis.sos.state.nm.us/WhereToVote.aspx",
    "NY": "https://voterlookup.elections.ny.gov/",
    "NC": "https://vt.ncsbe.gov/RegLkup/",
    "ND": "https://vip.sos.nd.gov/WhereToVote.aspx",
    "OH": "https://voterlookup.ohiosos.gov/voterlookup.aspx",
    "OK": "https://www.ok.gov/elections/Voter_Info/Online_Voter_Tool/",
    "OR": "https://sos.oregon.gov/voting/Pages/myvote.aspx",
    "PA": "https://www.pavoterservices.pa.gov/pages/voterregistrationstatus.aspx",
    "RI": "https://vote.sos.ri.gov/Home/UpdateVoterRecord",
    "SC": "https://info.scvotes.sc.gov/eng/voterinquiry/VoterInformationRequest.aspx",
    "SD": "https://vip.sdsos.gov/VIPLogin.aspx",
    "TN": "https://tnmap.tn.gov/voterlookup/",
    "TX": "https://teamrv-mvp.sos.texas.gov/MVP/mvp.do",
    "UT": "https://votesearch.utah.gov/voter-search/search/search-by-voter/voter-info",
    "VT": "https://mvp.vermont.gov/",
    "VA": "https://vote.elections.virginia.gov/VoterInformation",
    "WA": "https://voter.votewa.gov/WhereToVote.aspx",
    "WV": "https://apps.sos.wv.gov/Elections/voter/amiregisteredtovote",
    "WI": "https://myvote.wi.gov/en-us/RegisterToVote",
    "WY": "https://soswy.state.wy.us/Elections/Docs/WYCountyClerks.pdf",
    "DC": "https://www.dcboe.org/Voters/Register-To-Vote/Check-Voter-Registration-Status"
}

STATE_ELECTION_RESULTS: Dict[str, str] = {
    "AL": "https://www.sos.alabama.gov/alabama-votes/voter/election-data",
    "AK": "https://www.elections.alaska.gov/results/",
    "AZ": "https://azsos.gov/elections/voter-registration-historical-election-data",
    "AR": "https://results.enr.clarityelections.com/AR/",
    "CA": "https://www.sos.ca.gov/elections/prior-elections/",
    "CO": "https://www.coloradosos.gov/pubs/elections/Results/",
    "CT": "https://portal.ct.gov/SOTS/Election-Services/Election-Results/",
    "DE": "https://elections.delaware.gov/results/",
    "FL": "https://dos.myflorida.com/elections/data-statistics/elections-data/",
    "GA": "https://results.enr.clarityelections.com/GA/",
    "HI": "https://elections.hawaii.gov/election-results/",
    "ID": "https://sos.idaho.gov/elect/results/",
    "IL": "https://www.elections.il.gov/ElectionResults.aspx",
    "IN": "https://enr.indianavoters.in.gov/",
    "IA": "https://sos.iowa.gov/elections/results/",
    "KS": "https://sos.ks.gov/elections/elections-results.html",
    "KY": "https://results.enr.clarityelections.com/KY/",
    "LA": "https://voterportal.sos.la.gov/graphical",
    "ME": "https://www.maine.gov/sos/cec/elec/results/",
    "MD": "https://elections.maryland.gov/elections/results_data/",
    "MA": "https://electionstats.state.ma.us/",
    "MI": "https://miboecfr.nictusa.com/cgi-bin/cfr/precinct_srch.cgi",
    "MN": "https://www.sos.state.mn.us/elections-voting/election-results/",
    "MS": "https://www.sos.ms.gov/elections-voting/election-results",
    "MO": "https://www.sos.mo.gov/elections/s_default/results",
    "MT": "https://sosmt.gov/elections/results/",
    "NE": "https://sos.nebraska.gov/elections/election-results",
    "NV": "https://www.nvsos.gov/sos/elections/election-results",
    "NH": "https://www.sos.nh.gov/elections/data-and-statistics/election-results",
    "NJ": "https://www.state.nj.us/state/elections/election-results.shtml",
    "NM": "https://electionresults.sos.state.nm.us/",
    "NY": "https://www.elections.ny.gov/ElectionResults.html",
    "NC": "https://www.ncsbe.gov/results-data",
    "ND": "https://results.sos.nd.gov/",
    "OH": "https://www.ohiosos.gov/elections/election-results-and-data/",
    "OK": "https://results.okelections.us/",
    "OR": "https://sos.oregon.gov/elections/Pages/electionhistory.aspx",
    "PA": "https://www.electionreturns.pa.gov/",
    "RI": "https://www.ri.gov/election/results/",
    "SC": "https://www.scvotes.gov/election-results",
    "SD": "https://electionresults.sd.gov/",
    "TN": "https://sos.tn.gov/elections/results",
    "TX": "https://results.texas-election.com/",
    "UT": "https://electionresults.utah.gov/",
    "VT": "https://vtelectionresults.sec.state.vt.us/",
    "VA": "https://results.elections.virginia.gov/",
    "WA": "https://results.vote.wa.gov/",
    "WV": "https://apps.sos.wv.gov/Elections/results/",
    "WI": "https://elections.wi.gov/elections-voting/results",
    "WY": "https://sos.wyo.gov/Elections/Results.aspx",
    "DC": "https://dcboe.org/election-results"
}

VOTER_FILE_ACCESS_POLICIES: Dict[str, Dict[str, Any]] = {
    "AK": {"access": VoterFileAccess.PUBLIC, "cost": "Free online", "notes": "Full voter file available"},
    "AR": {"access": VoterFileAccess.PUBLIC, "cost": "$0.01/name", "notes": "Available to public"},
    "CO": {"access": VoterFileAccess.PUBLIC, "cost": "Varies by county", "notes": "Monthly updates available"},
    "CT": {"access": VoterFileAccess.PUBLIC, "cost": "Free for first copy", "notes": "Available to anyone"},
    "DE": {"access": VoterFileAccess.RESTRICTED, "cost": "N/A", "notes": "Restricted to candidates/parties"},
    "FL": {"access": VoterFileAccess.PUBLIC, "cost": "$0.01/name", "notes": "Highly accessible"},
    "GA": {"access": VoterFileAccess.CANDIDATES_PARTIES, "cost": "$250+", "notes": "Restricted requesters"},
    "MI": {"access": VoterFileAccess.PUBLIC, "cost": "Varies", "notes": "Available for purchase"},
    "NC": {"access": VoterFileAccess.PUBLIC, "cost": "Free online", "notes": "Full voter file free"},
    "NV": {"access": VoterFileAccess.PUBLIC, "cost": "Free CD", "notes": "Available to public"},
    "OH": {"access": VoterFileAccess.PUBLIC, "cost": "Free for viewing", "notes": "Copies cost extra"},
    "OK": {"access": VoterFileAccess.PUBLIC, "cost": "$50", "notes": "Statewide file available"},
    "OR": {"access": VoterFileAccess.PUBLIC, "cost": "Varies", "notes": "Available to public"},
    "RI": {"access": VoterFileAccess.PUBLIC, "cost": "Free", "notes": "Open access"},
    "TX": {"access": VoterFileAccess.CANDIDATES_PARTIES, "cost": "Varies", "notes": "Restricted access"},
    "UT": {"access": VoterFileAccess.PUBLIC, "cost": "$1,050", "notes": "Statewide file"},
    "WI": {"access": VoterFileAccess.PUBLIC, "cost": "$12,500 statewide", "notes": "Expensive but public"},
    "WA": {"access": VoterFileAccess.RESTRICTED, "cost": "N/A", "notes": "Restricted use"},
    "CA": {"access": VoterFileAccess.FEE_REQUIRED, "cost": "Varies by county", "notes": "County-level files"},
    "NY": {"access": VoterFileAccess.RESTRICTED, "cost": "N/A", "notes": "Party committee access only"},
    "PA": {"access": VoterFileAccess.FEE_REQUIRED, "cost": "$20-500", "notes": "Available for purchase"},
    "IL": {"access": VoterFileAccess.FEE_REQUIRED, "cost": "Varies", "notes": "County-level files"},
}


# =============================================================================
# Voter Records API (Main Implementation)
# =============================================================================

class VoterRecordsAPI:
    """
    API for voter and election records from free public sources.

    Integrates:
    - FEC API (Federal Election Commission) - Campaign finance
    - State voter registration lookup URLs
    - State election results portals
    - Voter file access policy information

    All methods are async-first with synchronous wrappers.
    """

    # FEC API endpoint
    FEC_API_URL = "https://api.open.fec.gov/v1"
    FEC_API_KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")  # Get free key at api.data.gov

    def __init__(self, fec_api_key: str = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Voter Records API.

        Args:
            fec_api_key: FEC API key (get free at api.data.gov)
            config: Optional configuration dict
        """
        self.fec_api_key = fec_api_key or self.FEC_API_KEY
        self.config = config or {}
        self._session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0
        self.last_request_time = None

        logger.info("Initialized VoterRecordsAPI")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "DataGod/1.0 (Public Records Research)",
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

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse various date formats."""
        if not date_str:
            return None
        date_str = str(date_str).strip()

        formats = ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str[:10], fmt[:min(len(fmt), len(date_str)+3)]).date()
            except ValueError:
                continue
        return None

    def _parse_party(self, party_str: Optional[str]) -> PartyRegistration:
        """Parse party string to enum."""
        if not party_str:
            return PartyRegistration.UNKNOWN

        party_lower = party_str.lower()
        if "dem" in party_lower:
            return PartyRegistration.DEMOCRATIC
        elif "rep" in party_lower:
            return PartyRegistration.REPUBLICAN
        elif "lib" in party_lower:
            return PartyRegistration.LIBERTARIAN
        elif "green" in party_lower:
            return PartyRegistration.GREEN
        elif "ind" in party_lower or "unaffiliated" in party_lower:
            return PartyRegistration.INDEPENDENT
        elif "no party" in party_lower or "none" in party_lower:
            return PartyRegistration.NO_PARTY
        return PartyRegistration.OTHER

    # =========================================================================
    # State Voter Lookup Information
    # =========================================================================

    def get_voter_lookup_url(self, state: str) -> Optional[str]:
        """
        Get state voter registration lookup URL.

        Args:
            state: Two-letter state code

        Returns:
            URL for voter lookup portal
        """
        return STATE_VOTER_LOOKUP.get(state.upper())

    def get_election_results_url(self, state: str) -> Optional[str]:
        """
        Get state election results portal URL.

        Args:
            state: Two-letter state code

        Returns:
            URL for election results
        """
        return STATE_ELECTION_RESULTS.get(state.upper())

    def get_state_voter_access(self, state: str) -> StateVoterAccess:
        """
        Get comprehensive voter file access information for a state.

        Args:
            state: Two-letter state code

        Returns:
            StateVoterAccess with full details
        """
        state = state.upper()
        state_name = STATE_NAMES.get(state, state)

        policy = VOTER_FILE_ACCESS_POLICIES.get(state, {})
        access_level = policy.get("access", VoterFileAccess.RESTRICTED)

        return StateVoterAccess(
            state=state,
            state_name=state_name,
            access_level=access_level,
            registration_lookup_url=STATE_VOTER_LOOKUP.get(state),
            election_results_url=STATE_ELECTION_RESULTS.get(state),
            voter_file_cost=policy.get("cost"),
            eligible_requesters=policy.get("eligible"),
            notes=policy.get("notes"),
            data_available=policy.get("data_available", [
                "name", "address", "party", "voting_history"
            ])
        )

    def get_all_state_voter_info(self) -> Dict[str, StateVoterAccess]:
        """Get voter access information for all states."""
        return {
            state: self.get_state_voter_access(state)
            for state in STATE_NAMES.keys()
        }

    # =========================================================================
    # FEC API - Campaign Contributions
    # =========================================================================

    async def search_contributions(
        self,
        contributor_name: str = "",
        recipient_name: str = "",
        recipient_id: str = "",
        contributor_state: str = "",
        contributor_city: str = "",
        contributor_zip: str = "",
        contributor_employer: str = "",
        min_amount: float = None,
        max_amount: float = None,
        min_date: date = None,
        max_date: date = None,
        election_cycle: str = "",
        limit: int = 100
    ) -> List[CampaignContribution]:
        """
        Search FEC individual contributions database.

        The FEC API provides access to all federal campaign contributions
        of $200 or more (smaller contributions are aggregated).

        Args:
            contributor_name: Contributor name to search
            recipient_name: Candidate/committee name
            recipient_id: FEC committee ID
            contributor_state: Contributor's state
            contributor_city: Contributor's city
            contributor_zip: Contributor's ZIP code
            contributor_employer: Employer name
            min_amount: Minimum contribution amount
            max_amount: Maximum contribution amount
            min_date: Start date for contributions
            max_date: End date for contributions
            election_cycle: Election cycle (e.g., "2024")
            limit: Maximum results (max 100 per request)

        Returns:
            List of CampaignContribution objects
        """
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp required for FEC API")
            return []

        await self._rate_limit(1.0)

        # Build query parameters
        params = {
            "api_key": self.fec_api_key,
            "per_page": min(limit, 100),
            "sort": "-contribution_receipt_date"
        }

        if contributor_name:
            params["contributor_name"] = contributor_name
        if recipient_id:
            params["committee_id"] = recipient_id
        if contributor_state:
            params["contributor_state"] = contributor_state.upper()
        if contributor_city:
            params["contributor_city"] = contributor_city
        if contributor_zip:
            params["contributor_zip"] = contributor_zip
        if contributor_employer:
            params["contributor_employer"] = contributor_employer
        if min_amount:
            params["min_amount"] = min_amount
        if max_amount:
            params["max_amount"] = max_amount
        if min_date:
            params["min_date"] = min_date.strftime("%Y-%m-%d")
        if max_date:
            params["max_date"] = max_date.strftime("%Y-%m-%d")
        if election_cycle:
            params["two_year_transaction_period"] = election_cycle

        results = []

        try:
            session = await self._get_session()
            url = f"{self.FEC_API_URL}/schedules/schedule_a/"

            async with session.get(url, params=params) as response:
                if response.status == 429:
                    logger.warning("FEC API rate limit reached")
                    return results
                if response.status != 200:
                    logger.error(f"FEC API error: {response.status}")
                    return results

                data = await response.json()
                contributions = data.get("results", [])

                for contrib in contributions:
                    contribution = self._parse_fec_contribution(contrib)
                    if contribution:
                        results.append(contribution)

                logger.info(f"FEC search returned {len(results)} contributions")
                return results

        except Exception as e:
            logger.error(f"FEC API search error: {e}")
            return results

    def _parse_fec_contribution(self, data: Dict[str, Any]) -> Optional[CampaignContribution]:
        """Parse FEC API contribution record."""
        try:
            amount = data.get("contribution_receipt_amount", 0)
            if amount is None:
                amount = 0

            return CampaignContribution(
                contributor_name=data.get("contributor_name", "Unknown"),
                amount=float(amount),
                contribution_date=self._parse_date(data.get("contribution_receipt_date")),
                recipient_name=data.get("committee", {}).get("name") if data.get("committee") else data.get("committee_id"),
                recipient_id=data.get("committee_id"),
                recipient_type=data.get("entity_type_desc"),
                election_cycle=str(data.get("two_year_transaction_period", "")),
                contributor_employer=data.get("contributor_employer"),
                contributor_occupation=data.get("contributor_occupation"),
                contributor_city=data.get("contributor_city"),
                contributor_state=data.get("contributor_state"),
                contributor_zip=data.get("contributor_zip"),
                receipt_type=data.get("receipt_type_full"),
                transaction_id=data.get("transaction_id"),
                filing_id=str(data.get("file_number", "")) if data.get("file_number") else None,
                source="FEC",
                source_url=f"https://www.fec.gov/data/receipts/individual-contributions/?contributor_name={quote_plus(data.get('contributor_name', ''))}"
            )
        except Exception as e:
            logger.error(f"Error parsing FEC contribution: {e}")
            return None

    async def search_candidates(
        self,
        name: str = "",
        state: str = "",
        party: str = "",
        office: str = "",
        district: str = "",
        election_year: int = None,
        incumbent: bool = None,
        limit: int = 50
    ) -> List[Candidate]:
        """
        Search FEC candidate database.

        Args:
            name: Candidate name
            state: State code
            party: Party affiliation (DEM, REP, LIB, etc.)
            office: Office (H=House, S=Senate, P=President)
            district: Congressional district (for House)
            election_year: Election year
            incumbent: Filter by incumbent status
            limit: Maximum results

        Returns:
            List of Candidate objects
        """
        if not AIOHTTP_AVAILABLE:
            return []

        await self._rate_limit(1.0)

        params = {
            "api_key": self.fec_api_key,
            "per_page": min(limit, 100),
            "sort": "-election_year"
        }

        if name:
            params["name"] = name
        if state:
            params["state"] = state.upper()
        if party:
            params["party"] = party.upper()
        if office:
            office_map = {"house": "H", "senate": "S", "president": "P"}
            params["office"] = office_map.get(office.lower(), office.upper())
        if district:
            params["district"] = district
        if election_year:
            params["election_year"] = election_year
        if incumbent is not None:
            params["incumbent_challenge"] = "I" if incumbent else "C"

        results = []

        try:
            session = await self._get_session()
            url = f"{self.FEC_API_URL}/candidates/search/"

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"FEC candidates API error: {response.status}")
                    return results

                data = await response.json()
                candidates_data = data.get("results", [])

                for cand in candidates_data:
                    candidate = self._parse_fec_candidate(cand)
                    if candidate:
                        results.append(candidate)

                return results

        except Exception as e:
            logger.error(f"FEC candidates search error: {e}")
            return results

    def _parse_fec_candidate(self, data: Dict[str, Any]) -> Optional[Candidate]:
        """Parse FEC candidate data."""
        try:
            office_map = {"H": "House", "S": "Senate", "P": "President"}

            return Candidate(
                name=data.get("name", "Unknown"),
                candidate_id=data.get("candidate_id"),
                party=self._parse_party(data.get("party_full")),
                office=office_map.get(data.get("office"), data.get("office")),
                state=data.get("state"),
                district=data.get("district"),
                election_year=data.get("election_year"),
                incumbent=data.get("incumbent_challenge") == "I",
                total_receipts=data.get("total_receipts"),
                total_disbursements=data.get("total_disbursements"),
                cash_on_hand=data.get("cash_on_hand_end_period"),
                source_url=f"https://www.fec.gov/data/candidate/{data.get('candidate_id', '')}/"
            )
        except Exception as e:
            logger.error(f"Error parsing FEC candidate: {e}")
            return None

    async def search_committees(
        self,
        name: str = "",
        committee_id: str = "",
        state: str = "",
        committee_type: str = "",
        party: str = "",
        min_receipts: float = None,
        limit: int = 50
    ) -> List[Committee]:
        """
        Search FEC political committees/PACs.

        Args:
            name: Committee name
            committee_id: FEC committee ID
            state: State code
            committee_type: Type (P=Presidential, H=House, S=Senate, etc.)
            party: Party affiliation
            min_receipts: Minimum total receipts
            limit: Maximum results

        Returns:
            List of Committee objects
        """
        if not AIOHTTP_AVAILABLE:
            return []

        await self._rate_limit(1.0)

        params = {
            "api_key": self.fec_api_key,
            "per_page": min(limit, 100)
        }

        if name:
            params["q"] = name
        if committee_id:
            params["committee_id"] = committee_id
        if state:
            params["state"] = state.upper()
        if committee_type:
            params["committee_type"] = committee_type
        if party:
            params["party"] = party.upper()
        if min_receipts:
            params["min_receipts"] = min_receipts

        results = []

        try:
            session = await self._get_session()
            url = f"{self.FEC_API_URL}/committees/"

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"FEC committees API error: {response.status}")
                    return results

                data = await response.json()
                committees_data = data.get("results", [])

                for comm in committees_data:
                    committee = self._parse_fec_committee(comm)
                    if committee:
                        results.append(committee)

                return results

        except Exception as e:
            logger.error(f"FEC committees search error: {e}")
            return results

    def _parse_fec_committee(self, data: Dict[str, Any]) -> Optional[Committee]:
        """Parse FEC committee data."""
        try:
            return Committee(
                name=data.get("name", "Unknown"),
                committee_id=data.get("committee_id", ""),
                committee_type=data.get("committee_type_full"),
                designation=data.get("designation_full"),
                party=data.get("party_full"),
                state=data.get("state"),
                treasurer_name=data.get("treasurer_name"),
                total_receipts=data.get("total_receipts"),
                total_disbursements=data.get("total_disbursements"),
                cash_on_hand=data.get("last_cash_on_hand_end_period"),
                filing_frequency=data.get("filing_frequency"),
                first_file_date=self._parse_date(data.get("first_file_date")),
                source_url=f"https://www.fec.gov/data/committee/{data.get('committee_id', '')}/"
            )
        except Exception as e:
            logger.error(f"Error parsing FEC committee: {e}")
            return None

    async def get_candidate_totals(
        self,
        candidate_id: str = "",
        election_year: int = None,
        office: str = "",
        state: str = "",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get candidate financial totals.

        Args:
            candidate_id: FEC candidate ID
            election_year: Election year
            office: Office type
            state: State code
            limit: Maximum results

        Returns:
            List of candidate financial summary dicts
        """
        if not AIOHTTP_AVAILABLE:
            return []

        await self._rate_limit(1.0)

        params = {
            "api_key": self.fec_api_key,
            "per_page": min(limit, 100),
            "sort": "-receipts"
        }

        if candidate_id:
            params["candidate_id"] = candidate_id
        if election_year:
            params["election_year"] = election_year
        if office:
            office_map = {"house": "H", "senate": "S", "president": "P"}
            params["office"] = office_map.get(office.lower(), office.upper())
        if state:
            params["state"] = state.upper()

        try:
            session = await self._get_session()
            url = f"{self.FEC_API_URL}/candidates/totals/"

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                return data.get("results", [])

        except Exception as e:
            logger.error(f"FEC candidate totals error: {e}")
            return []

    # =========================================================================
    # Voter Registration Guidance
    # =========================================================================

    def get_voter_registration_guidance(
        self,
        state: str,
        first_name: str = "",
        last_name: str = ""
    ) -> VoterRegistration:
        """
        Get voter registration lookup guidance for a state.

        Note: Actual registration lookup requires visiting state portals
        directly as they use web forms, not public APIs.

        Args:
            state: State code
            first_name: First name for guidance
            last_name: Last name for guidance

        Returns:
            VoterRegistration with lookup URL and instructions
        """
        state = state.upper()
        lookup_url = STATE_VOTER_LOOKUP.get(state)
        state_name = STATE_NAMES.get(state, state)

        name = f"{first_name} {last_name}".strip() if first_name or last_name else "Lookup Required"

        return VoterRegistration(
            voter_id="LOOKUP_REQUIRED",
            name=name,
            first_name=first_name or None,
            last_name=last_name or None,
            state=state,
            status=VoterStatus.UNKNOWN,
            lookup_url=lookup_url,
            source_url=lookup_url
        )

    # =========================================================================
    # All Resources for a State
    # =========================================================================

    def get_all_state_resources(self, state: str) -> Dict[str, Any]:
        """
        Get all voter/election resources for a state.

        Args:
            state: Two-letter state code

        Returns:
            Dictionary with all available resources and URLs
        """
        state = state.upper()
        state_name = STATE_NAMES.get(state, state)
        policy = VOTER_FILE_ACCESS_POLICIES.get(state, {})

        return {
            "state": state,
            "state_name": state_name,
            "voter_lookup_url": STATE_VOTER_LOOKUP.get(state),
            "election_results_url": STATE_ELECTION_RESULTS.get(state),
            "voter_file_access": policy.get("access", VoterFileAccess.RESTRICTED).value if isinstance(policy.get("access"), VoterFileAccess) else "Restricted",
            "voter_file_cost": policy.get("cost"),
            "voter_file_notes": policy.get("notes"),
            "fec_state_contributions": f"https://www.fec.gov/data/receipts/?contributor_state={state}",
            "fec_state_candidates": f"https://www.fec.gov/data/candidates/?state={state}",
            "fec_state_committees": f"https://www.fec.gov/data/committees/?state={state}",
            "opensecrets_state": f"https://www.opensecrets.org/states/summary.php?state={state}"
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return {
            "request_count": self.request_count,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "states_configured": len(STATE_VOTER_LOOKUP),
            "fec_api_key_set": self.fec_api_key != "DEMO_KEY",
            "supported_sources": ["FEC", "State Portals", "OpenSecrets"]
        }


# =============================================================================
# Synchronous Wrappers
# =============================================================================

def get_voter_lookup_url(state: str) -> Optional[str]:
    """Get state voter registration lookup URL."""
    api = VoterRecordsAPI()
    return api.get_voter_lookup_url(state)


def get_election_results_url(state: str) -> Optional[str]:
    """Get state election results URL."""
    api = VoterRecordsAPI()
    return api.get_election_results_url(state)


def get_state_election_resources(state: str) -> Dict[str, Any]:
    """Get all voter/election resources for state."""
    api = VoterRecordsAPI()
    return api.get_all_state_resources(state)


def get_state_voter_access(state: str) -> StateVoterAccess:
    """Get state voter file access policy."""
    api = VoterRecordsAPI()
    return api.get_state_voter_access(state)


def search_fec_contributions(
    contributor_name: str = "",
    contributor_state: str = "",
    min_amount: float = None,
    max_amount: float = None,
    election_cycle: str = "",
    limit: int = 100
) -> List[CampaignContribution]:
    """
    Search FEC contributions synchronously.

    Args:
        contributor_name: Contributor name
        contributor_state: Contributor's state
        min_amount: Minimum amount
        max_amount: Maximum amount
        election_cycle: Election cycle
        limit: Maximum results

    Returns:
        List of CampaignContribution objects
    """
    api = VoterRecordsAPI()

    async def _search():
        try:
            return await api.search_contributions(
                contributor_name=contributor_name,
                contributor_state=contributor_state,
                min_amount=min_amount,
                max_amount=max_amount,
                election_cycle=election_cycle,
                limit=limit
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


def search_fec_candidates(
    name: str = "",
    state: str = "",
    party: str = "",
    office: str = "",
    election_year: int = None,
    limit: int = 50
) -> List[Candidate]:
    """
    Search FEC candidates synchronously.

    Args:
        name: Candidate name
        state: State code
        party: Party affiliation
        office: Office type
        election_year: Election year
        limit: Maximum results

    Returns:
        List of Candidate objects
    """
    api = VoterRecordsAPI()

    async def _search():
        try:
            return await api.search_candidates(
                name=name,
                state=state,
                party=party,
                office=office,
                election_year=election_year,
                limit=limit
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


def search_fec_committees(
    name: str = "",
    state: str = "",
    committee_type: str = "",
    limit: int = 50
) -> List[Committee]:
    """
    Search FEC committees/PACs synchronously.

    Args:
        name: Committee name
        state: State code
        committee_type: Committee type
        limit: Maximum results

    Returns:
        List of Committee objects
    """
    api = VoterRecordsAPI()

    async def _search():
        try:
            return await api.search_committees(
                name=name,
                state=state,
                committee_type=committee_type,
                limit=limit
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


# =============================================================================
# Legacy Class (for backward compatibility)
# =============================================================================

class VoterRecordsScraper:
    """
    Legacy scraper class for backward compatibility.

    DEPRECATED: Use VoterRecordsAPI instead.
    """

    STATE_VOTER_LOOKUP = STATE_VOTER_LOOKUP
    STATE_ELECTION_RESULTS = STATE_ELECTION_RESULTS
    VOTER_FILE_ACCESS = {k: v.get("access", VoterFileAccess.RESTRICTED) for k, v in VOTER_FILE_ACCESS_POLICIES.items()}

    def __init__(self):
        """Initialize voter records scraper"""
        self._api = VoterRecordsAPI()
        self._session: Optional[aiohttp.ClientSession] = None
        logger.warning("VoterRecordsScraper is deprecated - use VoterRecordsAPI")

    async def _get_session(self) -> aiohttp.ClientSession:
        return await self._api._get_session()

    async def close(self):
        await self._api.close()

    def get_voter_lookup_url(self, state: str) -> Optional[str]:
        return self._api.get_voter_lookup_url(state)

    def get_election_results_url(self, state: str) -> Optional[str]:
        return self._api.get_election_results_url(state)

    def get_voter_file_access(self, state: str) -> StateVoterAccess:
        return self._api.get_state_voter_access(state)

    async def check_voter_registration(
        self,
        state: str,
        first_name: str,
        last_name: str,
        date_of_birth: Optional[date] = None,
        county: Optional[str] = None,
        zip_code: Optional[str] = None
    ) -> Optional[VoterRegistration]:
        return self._api.get_voter_registration_guidance(state, first_name, last_name)

    async def search_campaign_contributions(
        self,
        contributor_name: Optional[str] = None,
        recipient_name: Optional[str] = None,
        state: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        cycle: Optional[str] = None,
        limit: int = 100
    ) -> List[CampaignContribution]:
        return await self._api.search_contributions(
            contributor_name=contributor_name or "",
            recipient_name=recipient_name or "",
            contributor_state=state or "",
            min_amount=min_amount,
            max_amount=max_amount,
            election_cycle=cycle or "",
            limit=limit
        )

    async def get_election_results(
        self,
        state: str,
        election_date: Optional[date] = None,
        office: Optional[str] = None,
        county: Optional[str] = None
    ) -> List[ElectionResult]:
        # Election results require scraping state portals
        # Return guidance instead
        url = self._api.get_election_results_url(state)
        if url and election_date:
            return [ElectionResult(
                election_date=election_date,
                state=state,
                county=county,
                office=office,
                source_url=url
            )]
        return []

    def get_all_state_resources(self, state: str) -> Dict[str, Any]:
        return self._api.get_all_state_resources(state)


def check_registration_sync(
    state: str,
    first_name: str,
    last_name: str,
    date_of_birth: Optional[date] = None
) -> Optional[VoterRegistration]:
    """Synchronous voter registration check - returns guidance."""
    api = VoterRecordsAPI()
    return api.get_voter_registration_guidance(state, first_name, last_name)
