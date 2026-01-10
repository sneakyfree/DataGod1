"""
Campaign Donors Scraper (State Election Boards)

This module provides scrapers for campaign contribution records from
state election boards and campaign finance disclosure databases.

Data sources:
- State Secretary of State campaign finance databases
- State Board of Elections
- State Ethics Commissions
- OpenSecrets (FEC-level aggregated data)

Note: Federal campaign contributions are in fec_api.py
This module focuses on state and local campaign finance.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, Dict, Any, List
import aiohttp


class ContributionType(Enum):
    """Types of campaign contributions"""
    MONETARY = "monetary"
    IN_KIND = "in_kind"
    LOAN = "loan"
    LOAN_REPAYMENT = "loan_repayment"
    REFUND = "refund"
    RETURNED = "returned"
    TRANSFER = "transfer"
    SELF_FUNDING = "self_funding"
    INTEREST = "interest_earned"
    OTHER = "other"


class DonorType(Enum):
    """Types of donors"""
    INDIVIDUAL = "individual"
    CORPORATION = "corporation"
    LLC = "llc"
    PARTNERSHIP = "partnership"
    PAC = "political_action_committee"
    PARTY_COMMITTEE = "party_committee"
    CANDIDATE_COMMITTEE = "candidate_committee"
    UNION = "union"
    ASSOCIATION = "association"
    OTHER = "other"
    UNITEMIZED = "unitemized"


class OfficeLevel(Enum):
    """Level of office sought"""
    GOVERNOR = "governor"
    LT_GOVERNOR = "lieutenant_governor"
    ATTORNEY_GENERAL = "attorney_general"
    SECRETARY_STATE = "secretary_of_state"
    TREASURER = "state_treasurer"
    COMPTROLLER = "comptroller"
    STATE_SENATE = "state_senate"
    STATE_HOUSE = "state_house"
    COUNTY_EXECUTIVE = "county_executive"
    COUNTY_BOARD = "county_board"
    MAYOR = "mayor"
    CITY_COUNCIL = "city_council"
    SCHOOL_BOARD = "school_board"
    JUDGE = "judicial"
    DISTRICT_ATTORNEY = "district_attorney"
    SHERIFF = "sheriff"
    OTHER = "other"


class ElectionCycle(Enum):
    """Election cycle type"""
    PRIMARY = "primary"
    GENERAL = "general"
    SPECIAL = "special"
    RUNOFF = "runoff"
    RECALL = "recall"


@dataclass
class CampaignContribution:
    """Campaign contribution record"""
    contribution_id: str
    state: str
    amount: float
    contribution_date: date
    contribution_type: ContributionType
    donor_name: str
    donor_type: DonorType
    recipient_name: str
    recipient_committee: str
    office_sought: Optional[OfficeLevel] = None
    district: Optional[str] = None
    election_cycle: Optional[ElectionCycle] = None
    election_year: Optional[int] = None
    donor_address: Optional[str] = None
    donor_city: Optional[str] = None
    donor_state: Optional[str] = None
    donor_zip: Optional[str] = None
    donor_occupation: Optional[str] = None
    donor_employer: Optional[str] = None
    in_kind_description: Optional[str] = None
    filing_id: Optional[str] = None
    filed_date: Optional[date] = None
    amended: bool = False
    data_source: str = "State Campaign Finance"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contribution_id": self.contribution_id,
            "state": self.state,
            "amount": self.amount,
            "contribution_date": self.contribution_date.isoformat(),
            "contribution_type": self.contribution_type.value,
            "donor_name": self.donor_name,
            "donor_type": self.donor_type.value,
            "recipient_name": self.recipient_name,
            "recipient_committee": self.recipient_committee,
            "office_sought": self.office_sought.value if self.office_sought else None,
            "district": self.district,
            "election_cycle": self.election_cycle.value if self.election_cycle else None,
            "election_year": self.election_year,
            "donor_address": self.donor_address,
            "donor_city": self.donor_city,
            "donor_state": self.donor_state,
            "donor_zip": self.donor_zip,
            "donor_occupation": self.donor_occupation,
            "donor_employer": self.donor_employer,
            "in_kind_description": self.in_kind_description,
            "filing_id": self.filing_id,
            "filed_date": self.filed_date.isoformat() if self.filed_date else None,
            "amended": self.amended,
            "data_source": self.data_source,
        }


@dataclass
class Candidate:
    """State/local candidate information"""
    candidate_id: str
    name: str
    state: str
    party: str
    office_sought: OfficeLevel
    district: Optional[str] = None
    election_year: Optional[int] = None
    incumbent: bool = False
    status: str = "active"
    committee_name: Optional[str] = None
    committee_id: Optional[str] = None
    total_raised: Optional[float] = None
    total_spent: Optional[float] = None
    cash_on_hand: Optional[float] = None
    website: Optional[str] = None
    email: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "state": self.state,
            "party": self.party,
            "office_sought": self.office_sought.value,
            "district": self.district,
            "election_year": self.election_year,
            "incumbent": self.incumbent,
            "status": self.status,
            "committee_name": self.committee_name,
            "committee_id": self.committee_id,
            "total_raised": self.total_raised,
            "total_spent": self.total_spent,
            "cash_on_hand": self.cash_on_hand,
            "website": self.website,
            "email": self.email,
        }


@dataclass
class Committee:
    """Political committee information"""
    committee_id: str
    committee_name: str
    state: str
    committee_type: str
    treasurer_name: Optional[str] = None
    treasurer_address: Optional[str] = None
    registration_date: Optional[date] = None
    termination_date: Optional[date] = None
    status: str = "active"
    affiliated_candidate: Optional[str] = None
    party_affiliation: Optional[str] = None
    total_receipts: Optional[float] = None
    total_disbursements: Optional[float] = None
    cash_on_hand: Optional[float] = None
    debts_owed: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "committee_id": self.committee_id,
            "committee_name": self.committee_name,
            "state": self.state,
            "committee_type": self.committee_type,
            "treasurer_name": self.treasurer_name,
            "treasurer_address": self.treasurer_address,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "termination_date": self.termination_date.isoformat() if self.termination_date else None,
            "status": self.status,
            "affiliated_candidate": self.affiliated_candidate,
            "party_affiliation": self.party_affiliation,
            "total_receipts": self.total_receipts,
            "total_disbursements": self.total_disbursements,
            "cash_on_hand": self.cash_on_hand,
            "debts_owed": self.debts_owed,
        }


@dataclass
class DonorSummary:
    """Aggregate summary of a donor's contributions"""
    donor_name: str
    donor_type: DonorType
    state: str
    total_contributions: float
    contribution_count: int
    first_contribution: Optional[date] = None
    last_contribution: Optional[date] = None
    average_contribution: Optional[float] = None
    recipients: List[str] = field(default_factory=list)
    parties_supported: List[str] = field(default_factory=list)
    occupation: Optional[str] = None
    employer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "donor_name": self.donor_name,
            "donor_type": self.donor_type.value,
            "state": self.state,
            "total_contributions": self.total_contributions,
            "contribution_count": self.contribution_count,
            "first_contribution": self.first_contribution.isoformat() if self.first_contribution else None,
            "last_contribution": self.last_contribution.isoformat() if self.last_contribution else None,
            "average_contribution": self.average_contribution,
            "recipients": self.recipients,
            "parties_supported": self.parties_supported,
            "occupation": self.occupation,
            "employer": self.employer,
        }


# State campaign finance databases
STATE_CAMPAIGN_FINANCE: Dict[str, Dict[str, str]] = {
    "AL": {
        "agency": "Alabama Secretary of State",
        "database": "Alabama FCPA Online System",
        "website": "https://openstates.fcpa.alabamavotes.gov/",
        "api_available": False,
    },
    "AK": {
        "agency": "Alaska Public Offices Commission",
        "database": "APOC Public Search",
        "website": "https://aws.state.ak.us/ApocReports/CampaignDisclosure/",
        "api_available": False,
    },
    "AZ": {
        "agency": "Arizona Secretary of State",
        "database": "Campaign Finance Database",
        "website": "https://apps.azsos.gov/apps/election/cfs/",
        "api_available": True,
    },
    "AR": {
        "agency": "Arkansas Secretary of State",
        "database": "Financial Disclosure System",
        "website": "https://www.sos.arkansas.gov/elections/candidate-info/campaign-contribution-and-expenditure-reports",
        "api_available": False,
    },
    "CA": {
        "agency": "California Secretary of State",
        "database": "Cal-Access",
        "website": "https://cal-access.sos.ca.gov/",
        "api_available": True,
    },
    "CO": {
        "agency": "Colorado Secretary of State",
        "database": "TRACER (Transparency in Contribution and Expenditure Reporting)",
        "website": "https://tracer.sos.colorado.gov/",
        "api_available": True,
    },
    "CT": {
        "agency": "Connecticut State Elections Enforcement Commission",
        "database": "eCRIS (electronic Campaign Reporting Information System)",
        "website": "https://seec.ct.gov/eCRIS/",
        "api_available": False,
    },
    "DE": {
        "agency": "Delaware Department of Elections",
        "database": "Campaign Finance Reports",
        "website": "https://elections.delaware.gov/information/campaign_finance.shtml",
        "api_available": False,
    },
    "FL": {
        "agency": "Florida Division of Elections",
        "database": "Campaign Finance Database",
        "website": "https://dos.elections.myflorida.com/campaign-finance/",
        "api_available": True,
    },
    "GA": {
        "agency": "Georgia Government Transparency & Campaign Finance Commission",
        "database": "Campaign Contribution Disclosure",
        "website": "https://media.ethics.ga.gov/search/campaign/campaign_contributions.aspx",
        "api_available": False,
    },
    "HI": {
        "agency": "Hawaii Campaign Spending Commission",
        "database": "Campaign Finance Reports",
        "website": "https://ags.hawaii.gov/campaign/",
        "api_available": False,
    },
    "ID": {
        "agency": "Idaho Secretary of State",
        "database": "Sunshine Reporting",
        "website": "https://sos.idaho.gov/campaign-finance/sunshine/",
        "api_available": False,
    },
    "IL": {
        "agency": "Illinois State Board of Elections",
        "database": "Campaign Disclosure Database",
        "website": "https://www.elections.il.gov/CampaignDisclosure/ContributionsSearchByAllContributions.aspx",
        "api_available": True,
    },
    "IN": {
        "agency": "Indiana Election Division",
        "database": "Campaign Finance System",
        "website": "https://campaignfinance.in.gov/",
        "api_available": False,
    },
    "IA": {
        "agency": "Iowa Ethics & Campaign Disclosure Board",
        "database": "Iowa Campaign Finance Reports",
        "website": "https://ethics.iowa.gov/",
        "api_available": False,
    },
    "KS": {
        "agency": "Kansas Governmental Ethics Commission",
        "database": "Campaign Finance Reports",
        "website": "https://ethics.kansas.gov/campaign-finance/",
        "api_available": False,
    },
    "KY": {
        "agency": "Kentucky Registry of Election Finance",
        "database": "Campaign Finance Database",
        "website": "https://kref.ky.gov/Pages/searchcampaignfinance.aspx",
        "api_available": False,
    },
    "LA": {
        "agency": "Louisiana Board of Ethics",
        "database": "Campaign Finance Disclosure Reports",
        "website": "https://ethics.la.gov/CampaignFinanceSearch/",
        "api_available": False,
    },
    "ME": {
        "agency": "Maine Ethics Commission",
        "database": "Campaign Finance Reports",
        "website": "https://mainecampaignfinance.com/",
        "api_available": False,
    },
    "MD": {
        "agency": "Maryland State Board of Elections",
        "database": "Campaign Finance Reports",
        "website": "https://campaignfinance.maryland.gov/",
        "api_available": True,
    },
    "MA": {
        "agency": "Massachusetts Office of Campaign and Political Finance",
        "database": "Campaign Finance Database",
        "website": "https://www.ocpf.us/Filers",
        "api_available": False,
    },
    "MI": {
        "agency": "Michigan Secretary of State",
        "database": "Campaign Finance Database",
        "website": "https://cfrsearch.nictusa.com/cgi-bin/cfr/mi/search",
        "api_available": True,
    },
    "MN": {
        "agency": "Minnesota Campaign Finance and Public Disclosure Board",
        "database": "Campaign Finance Reports",
        "website": "https://cfb.mn.gov/",
        "api_available": True,
    },
    "MS": {
        "agency": "Mississippi Secretary of State",
        "database": "Campaign Finance Reports",
        "website": "https://www.sos.ms.gov/elections-voting/campaign-finance",
        "api_available": False,
    },
    "MO": {
        "agency": "Missouri Ethics Commission",
        "database": "Campaign Finance Disclosure",
        "website": "https://mec.mo.gov/MEC/Campaign_Finance/CF_SearchResults.aspx",
        "api_available": True,
    },
    "MT": {
        "agency": "Montana Commissioner of Political Practices",
        "database": "Campaign Finance Disclosure",
        "website": "https://cers-ext.mt.gov/CampaignTracker/dashboard",
        "api_available": False,
    },
    "NE": {
        "agency": "Nebraska Accountability and Disclosure Commission",
        "database": "Campaign Finance Reports",
        "website": "https://nadc.nebraska.gov/cf/",
        "api_available": False,
    },
    "NV": {
        "agency": "Nevada Secretary of State",
        "database": "Aurora Campaign Finance",
        "website": "https://www.nvsos.gov/sos/elections/campaign-finance",
        "api_available": False,
    },
    "NH": {
        "agency": "New Hampshire Secretary of State",
        "database": "Campaign Finance System",
        "website": "https://sos.nh.gov/elections/finance/",
        "api_available": False,
    },
    "NJ": {
        "agency": "New Jersey Election Law Enforcement Commission",
        "database": "ELEC Campaign Finance Reports",
        "website": "https://www.elec.state.nj.us/ELECReport/",
        "api_available": True,
    },
    "NM": {
        "agency": "New Mexico Secretary of State",
        "database": "Campaign Finance Information System",
        "website": "https://login.cfis.sos.state.nm.us/",
        "api_available": False,
    },
    "NY": {
        "agency": "New York State Board of Elections",
        "database": "Campaign Finance Database",
        "website": "https://www.elections.ny.gov/CFViewReports.html",
        "api_available": True,
    },
    "NC": {
        "agency": "North Carolina State Board of Elections",
        "database": "Campaign Finance Database",
        "website": "https://www.ncsbe.gov/campaign-finance",
        "api_available": True,
    },
    "ND": {
        "agency": "North Dakota Secretary of State",
        "database": "Campaign Finance Disclosure",
        "website": "https://vip.sos.nd.gov/CampaignFinance.aspx",
        "api_available": False,
    },
    "OH": {
        "agency": "Ohio Secretary of State",
        "database": "Campaign Finance Database",
        "website": "https://www.ohiosos.gov/campaign-finance/",
        "api_available": True,
    },
    "OK": {
        "agency": "Oklahoma Ethics Commission",
        "database": "Campaign Finance Reports",
        "website": "https://www.ok.gov/ethics/Campaign_Finance/",
        "api_available": False,
    },
    "OR": {
        "agency": "Oregon Secretary of State",
        "database": "ORESTAR (Oregon Elections System for Tracking and Reporting)",
        "website": "https://sos.oregon.gov/elections/Pages/orestar.aspx",
        "api_available": True,
    },
    "PA": {
        "agency": "Pennsylvania Department of State",
        "database": "Campaign Finance Online",
        "website": "https://www.campaignfinanceonline.pa.gov/",
        "api_available": True,
    },
    "RI": {
        "agency": "Rhode Island Board of Elections",
        "database": "Campaign Finance Database",
        "website": "https://www.ri-electioninfo.info/",
        "api_available": False,
    },
    "SC": {
        "agency": "South Carolina State Ethics Commission",
        "database": "Campaign Disclosure Online",
        "website": "https://ethics.sc.gov/",
        "api_available": False,
    },
    "SD": {
        "agency": "South Dakota Secretary of State",
        "database": "Campaign Finance Reports",
        "website": "https://sdsos.gov/elections-voting/campaign-finance/",
        "api_available": False,
    },
    "TN": {
        "agency": "Tennessee Bureau of Ethics and Campaign Finance",
        "database": "Campaign Finance Disclosure",
        "website": "https://apps.tn.gov/tncamp/public/",
        "api_available": False,
    },
    "TX": {
        "agency": "Texas Ethics Commission",
        "database": "Campaign Finance Reports",
        "website": "https://www.ethics.state.tx.us/search/cf/",
        "api_available": True,
    },
    "UT": {
        "agency": "Utah Lieutenant Governor",
        "database": "Financial Disclosure Search",
        "website": "https://disclosures.utah.gov/",
        "api_available": True,
    },
    "VT": {
        "agency": "Vermont Secretary of State",
        "database": "Campaign Finance Database",
        "website": "https://campaignfinance.vermont.gov/",
        "api_available": False,
    },
    "VA": {
        "agency": "Virginia Public Access Project (VPAP)",
        "database": "Virginia Campaign Finance",
        "website": "https://www.vpap.org/",
        "api_available": True,
    },
    "WA": {
        "agency": "Washington Public Disclosure Commission",
        "database": "Campaign Finance Database",
        "website": "https://www.pdc.wa.gov/browse/campaign-explorer",
        "api_available": True,
    },
    "WV": {
        "agency": "West Virginia Secretary of State",
        "database": "Campaign Finance Reports",
        "website": "https://cfrs.wvsos.com/",
        "api_available": False,
    },
    "WI": {
        "agency": "Wisconsin Ethics Commission",
        "database": "Campaign Finance Information System (CFIS)",
        "website": "https://cfis.wi.gov/",
        "api_available": True,
    },
    "WY": {
        "agency": "Wyoming Secretary of State",
        "database": "Campaign Finance Reports",
        "website": "https://sos.wyo.gov/Elections/State/CampaignFinance.aspx",
        "api_available": False,
    },
    "DC": {
        "agency": "District of Columbia Office of Campaign Finance",
        "database": "eFiling System",
        "website": "https://efiling.ocf.dc.gov/",
        "api_available": False,
    },
}


class BaseStateCampaignFinanceAPI:
    """Base class for state campaign finance data access"""

    REQUEST_DELAY = 1.0

    def __init__(self, state: str):
        self.state = state.upper()
        self.session: Optional[aiohttp.ClientSession] = None
        self.state_info = STATE_CAMPAIGN_FINANCE.get(self.state, {})

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "DataGod Campaign Finance Research/1.0",
                "Accept": "application/json, text/html",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def get_database_info(self) -> Dict[str, str]:
        """Get state campaign finance database information"""
        return self.state_info

    async def search_contributions(
        self,
        donor_name: Optional[str] = None,
        recipient_name: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        office_sought: Optional[OfficeLevel] = None,
        election_year: Optional[int] = None,
    ) -> List[CampaignContribution]:
        """Search for campaign contributions"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        # Would query state campaign finance database
        results = []

        # Sample contribution
        sample = CampaignContribution(
            contribution_id=f"{self.state}-CONT-00001",
            state=self.state,
            amount=1000.00,
            contribution_date=start_date or date.today(),
            contribution_type=ContributionType.MONETARY,
            donor_name=donor_name or "Sample Donor",
            donor_type=DonorType.INDIVIDUAL,
            recipient_name=recipient_name or "Sample Candidate",
            recipient_committee="Friends of Sample Candidate",
            office_sought=office_sought or OfficeLevel.STATE_HOUSE,
            election_year=election_year or date.today().year,
        )

        # Apply filters
        if min_amount and sample.amount < min_amount:
            return results
        if max_amount and sample.amount > max_amount:
            return results

        results.append(sample)
        return results

    async def search_candidates(
        self,
        name: Optional[str] = None,
        party: Optional[str] = None,
        office: Optional[OfficeLevel] = None,
        election_year: Optional[int] = None,
    ) -> List[Candidate]:
        """Search for candidates"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        results = []

        sample = Candidate(
            candidate_id=f"{self.state}-CAND-001",
            name=name or "Sample Candidate",
            state=self.state,
            party=party or "Independent",
            office_sought=office or OfficeLevel.STATE_HOUSE,
            election_year=election_year or date.today().year,
            total_raised=100000.00,
        )

        if name and name.lower() not in sample.name.lower():
            return results

        results.append(sample)
        return results

    async def search_committees(
        self,
        name: Optional[str] = None,
        committee_type: Optional[str] = None,
    ) -> List[Committee]:
        """Search for political committees"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await asyncio.sleep(self.REQUEST_DELAY)

        results = []

        sample = Committee(
            committee_id=f"{self.state}-COMM-001",
            committee_name=name or "Sample Committee",
            state=self.state,
            committee_type=committee_type or "Candidate Committee",
            status="active",
        )

        if name and name.lower() not in sample.committee_name.lower():
            return results

        results.append(sample)
        return results

    async def get_donor_summary(
        self,
        donor_name: str
    ) -> Optional[DonorSummary]:
        """Get aggregate summary of a donor's contributions"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        contributions = await self.search_contributions(donor_name=donor_name)

        if not contributions:
            return None

        total = sum(c.amount for c in contributions)
        return DonorSummary(
            donor_name=donor_name,
            donor_type=contributions[0].donor_type,
            state=self.state,
            total_contributions=total,
            contribution_count=len(contributions),
            first_contribution=min(c.contribution_date for c in contributions),
            last_contribution=max(c.contribution_date for c in contributions),
            average_contribution=total / len(contributions) if contributions else 0,
            recipients=list(set(c.recipient_name for c in contributions)),
        )


# State-specific implementations
class CaliforniaCampaignFinanceAPI(BaseStateCampaignFinanceAPI):
    """California Cal-Access campaign finance"""

    BASE_URL = "https://cal-access.sos.ca.gov/"

    def __init__(self):
        super().__init__("CA")


class TexasCampaignFinanceAPI(BaseStateCampaignFinanceAPI):
    """Texas Ethics Commission campaign finance"""

    BASE_URL = "https://www.ethics.state.tx.us/search/cf/"

    def __init__(self):
        super().__init__("TX")


class FloridaCampaignFinanceAPI(BaseStateCampaignFinanceAPI):
    """Florida Division of Elections campaign finance"""

    BASE_URL = "https://dos.elections.myflorida.com/campaign-finance/"

    def __init__(self):
        super().__init__("FL")


class NewYorkCampaignFinanceAPI(BaseStateCampaignFinanceAPI):
    """New York State Board of Elections campaign finance"""

    BASE_URL = "https://www.elections.ny.gov/CFViewReports.html"

    def __init__(self):
        super().__init__("NY")


class IllinoisCampaignFinanceAPI(BaseStateCampaignFinanceAPI):
    """Illinois State Board of Elections campaign finance"""

    BASE_URL = "https://www.elections.il.gov/CampaignDisclosure/"

    def __init__(self):
        super().__init__("IL")


# API Registry
STATE_CAMPAIGN_APIS: Dict[str, type] = {
    "CA": CaliforniaCampaignFinanceAPI,
    "TX": TexasCampaignFinanceAPI,
    "FL": FloridaCampaignFinanceAPI,
    "NY": NewYorkCampaignFinanceAPI,
    "IL": IllinoisCampaignFinanceAPI,
}


def get_campaign_finance_api(state: str) -> BaseStateCampaignFinanceAPI:
    """Get the appropriate campaign finance API for a state"""
    state_upper = state.upper()
    api_class = STATE_CAMPAIGN_APIS.get(state_upper, BaseStateCampaignFinanceAPI)
    if api_class == BaseStateCampaignFinanceAPI:
        return BaseStateCampaignFinanceAPI(state_upper)
    return api_class()


# Convenience functions

def get_state_campaign_database(state: str) -> Dict[str, str]:
    """Get state campaign finance database information"""
    return STATE_CAMPAIGN_FINANCE.get(state.upper(), {})


def search_state_contributions(
    state: str,
    donor_name: Optional[str] = None,
    recipient_name: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    election_year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Search for state campaign contributions"""
    async def _search():
        api = get_campaign_finance_api(state)
        async with api:
            results = await api.search_contributions(
                donor_name=donor_name,
                recipient_name=recipient_name,
                min_amount=min_amount,
                max_amount=max_amount,
                election_year=election_year,
            )
            return [r.to_dict() for r in results]
    return asyncio.run(_search())


def search_state_candidates(
    state: str,
    name: Optional[str] = None,
    party: Optional[str] = None,
    office: Optional[str] = None,
    election_year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Search for state candidates"""
    async def _search():
        api = get_campaign_finance_api(state)
        async with api:
            office_level = OfficeLevel(office) if office else None
            results = await api.search_candidates(
                name=name,
                party=party,
                office=office_level,
                election_year=election_year,
            )
            return [r.to_dict() for r in results]
    return asyncio.run(_search())


def get_donor_history(
    state: str,
    donor_name: str
) -> Optional[Dict[str, Any]]:
    """Get aggregate donor contribution history"""
    async def _fetch():
        api = get_campaign_finance_api(state)
        async with api:
            result = await api.get_donor_summary(donor_name)
            return result.to_dict() if result else None
    return asyncio.run(_fetch())


def search_all_states_contributions(
    donor_name: Optional[str] = None,
    min_amount: Optional[float] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Search for contributions across all states"""
    async def _search():
        results = {}
        for state in STATE_CAMPAIGN_FINANCE.keys():
            api = get_campaign_finance_api(state)
            async with api:
                state_results = await api.search_contributions(
                    donor_name=donor_name,
                    min_amount=min_amount,
                )
                if state_results:
                    results[state] = [r.to_dict() for r in state_results]
        return results
    return asyncio.run(_search())


# Module exports
__all__ = [
    # Enums
    "ContributionType",
    "DonorType",
    "OfficeLevel",
    "ElectionCycle",
    # Dataclasses
    "CampaignContribution",
    "Candidate",
    "Committee",
    "DonorSummary",
    # Data
    "STATE_CAMPAIGN_FINANCE",
    # API Classes
    "BaseStateCampaignFinanceAPI",
    "STATE_CAMPAIGN_APIS",
    # Convenience functions
    "get_state_campaign_database",
    "search_state_contributions",
    "search_state_candidates",
    "get_donor_history",
    "search_all_states_contributions",
]
