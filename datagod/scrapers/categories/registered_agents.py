"""
Registered Agents Scraper
=========================

Comprehensive scraper for registered agent records from Secretary of State
databases. Registered agents receive legal documents on behalf of businesses.

Data Sources:
- Secretary of State business databases
- Corporate filing systems
- Business entity search portals

Public Information:
- Registered agent name (individual or company)
- Agent address (registered office)
- Entities represented
- Agent status
- Appointment/resignation dates

This is valuable for:
- Process serving
- Legal research
- Corporate investigations
- Business due diligence
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
import json
import re
import logging

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of registered agents"""
    INDIVIDUAL = "individual"
    CORPORATION = "corporation"
    LLC = "llc"
    REGISTERED_AGENT_SERVICE = "registered_agent_service"
    LAW_FIRM = "law_firm"
    ATTORNEY = "attorney"
    CPA_FIRM = "cpa_firm"
    COMPANY_OFFICER = "company_officer"
    OTHER = "other"


class AgentStatus(Enum):
    """Agent status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    RESIGNED = "resigned"
    REMOVED = "removed"
    PENDING = "pending"
    SUSPENDED = "suspended"


class EntityType(Enum):
    """Types of entities represented"""
    CORPORATION = "corporation"
    LLC = "llc"
    LP = "limited_partnership"
    LLP = "limited_liability_partnership"
    NONPROFIT = "nonprofit"
    FOREIGN_CORPORATION = "foreign_corporation"
    FOREIGN_LLC = "foreign_llc"
    PROFESSIONAL_CORPORATION = "professional_corporation"
    BENEFIT_CORPORATION = "benefit_corporation"
    SERIES_LLC = "series_llc"
    TRUST = "trust"
    OTHER = "other"


@dataclass
class RepresentedEntity:
    """Entity represented by the registered agent"""
    entity_name: str
    entity_type: EntityType = EntityType.OTHER
    entity_id: Optional[str] = None
    state_of_formation: Optional[str] = None
    status: Optional[str] = None
    appointment_date: Optional[date] = None
    filing_number: Optional[str] = None


@dataclass
class RegisteredAgent:
    """Registered agent record"""
    # Agent identification
    agent_name: str
    agent_type: AgentType = AgentType.INDIVIDUAL

    # Agent address (registered office)
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None

    # Contact (if available)
    phone: Optional[str] = None
    email: Optional[str] = None

    # Agent status
    status: AgentStatus = AgentStatus.ACTIVE
    effective_date: Optional[date] = None
    resignation_date: Optional[date] = None

    # Entities represented
    entities_represented: List[RepresentedEntity] = field(default_factory=list)
    entity_count: int = 0

    # Registration details
    agent_id: Optional[str] = None
    registration_number: Optional[str] = None

    # Source tracking
    source_state: Optional[str] = None
    source_url: Optional[str] = None
    source_system: Optional[str] = None
    retrieved_at: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchCriteria:
    """Search criteria for registered agents"""
    agent_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    entity_name: Optional[str] = None
    agent_type: Optional[AgentType] = None
    status: Optional[AgentStatus] = None


@dataclass
class SearchResult:
    """Search result container"""
    agents: List[RegisteredAgent] = field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 100
    has_more: bool = False
    search_criteria: Optional[SearchCriteria] = None
    search_time_ms: int = 0
    source_system: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class BaseRegisteredAgentAPI:
    """Base class for state registered agent APIs"""

    STATE_CODE: str = ""
    STATE_NAME: str = ""
    BASE_URL: str = ""
    API_URL: str = ""
    SYSTEM_NAME: str = ""

    REQUEST_DELAY: float = 1.0

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; DataGod/1.0; Public Records Research)"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _fetch_json(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Fetch JSON data from URL"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")

        await asyncio.sleep(self.REQUEST_DELAY)

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def _fetch_html(self, url: str, params: Optional[Dict] = None) -> str:
        """Fetch HTML content from URL"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")

        await asyncio.sleep(self.REQUEST_DELAY)

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.text()

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string"""
        if not date_str:
            return None
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y%m%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _classify_agent_type(self, name: str, type_hint: str = "") -> AgentType:
        """Classify agent type from name or hint"""
        combined = f"{name} {type_hint}".lower()

        if any(kw in combined for kw in ["registered agent", "ra service", "agent service"]):
            return AgentType.REGISTERED_AGENT_SERVICE
        elif any(kw in combined for kw in ["law firm", "attorney", "esq", "llp", "pllc"]):
            return AgentType.LAW_FIRM
        elif any(kw in combined for kw in ["cpa", "accounting"]):
            return AgentType.CPA_FIRM
        elif any(kw in combined for kw in ["llc", "limited liability"]):
            return AgentType.LLC
        elif any(kw in combined for kw in ["corp", "inc", "corporation"]):
            return AgentType.CORPORATION

        return AgentType.INDIVIDUAL

    def _classify_entity_type(self, type_str: str) -> EntityType:
        """Classify entity type from string"""
        if not type_str:
            return EntityType.OTHER

        type_lower = type_str.lower()

        if "foreign" in type_lower:
            if "llc" in type_lower:
                return EntityType.FOREIGN_LLC
            return EntityType.FOREIGN_CORPORATION
        elif "llc" in type_lower or "limited liability company" in type_lower:
            if "series" in type_lower:
                return EntityType.SERIES_LLC
            return EntityType.LLC
        elif "llp" in type_lower or "limited liability partnership" in type_lower:
            return EntityType.LLP
        elif "lp" in type_lower or "limited partnership" in type_lower:
            return EntityType.LP
        elif "nonprofit" in type_lower or "non-profit" in type_lower:
            return EntityType.NONPROFIT
        elif "professional" in type_lower:
            return EntityType.PROFESSIONAL_CORPORATION
        elif "benefit" in type_lower:
            return EntityType.BENEFIT_CORPORATION
        elif "corp" in type_lower or "inc" in type_lower:
            return EntityType.CORPORATION
        elif "trust" in type_lower:
            return EntityType.TRUST

        return EntityType.OTHER

    async def search_agents(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        entity_name: Optional[str] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search for registered agents - override in subclass"""
        raise NotImplementedError

    async def get_agent_detail(self, agent_id: str) -> Optional[RegisteredAgent]:
        """Get detailed agent information - override in subclass"""
        raise NotImplementedError

    async def get_entities_by_agent(
        self,
        agent_name: str,
        max_results: int = 500
    ) -> List[RepresentedEntity]:
        """Get all entities represented by an agent"""
        raise NotImplementedError


class DelawareRegisteredAgentAPI(BaseRegisteredAgentAPI):
    """Delaware Division of Corporations registered agent lookup"""

    STATE_CODE = "DE"
    STATE_NAME = "Delaware"
    BASE_URL = "https://icis.corp.delaware.gov"
    API_URL = "https://icis.corp.delaware.gov/eCorp/EntitySearch"
    SYSTEM_NAME = "Delaware Division of Corporations"

    async def search_agents(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        entity_name: Optional[str] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search Delaware registered agents"""
        import time
        start_time = time.time()

        params = {"limit": min(max_results, 100)}

        if name:
            params["agentName"] = name
        if city:
            params["city"] = city
        if entity_name:
            params["entityName"] = entity_name

        try:
            data = await self._fetch_json(f"{self.API_URL}/agents", params=params)
        except Exception as e:
            logger.error(f"Delaware agent search failed: {e}")
            return SearchResult(
                agents=[],
                total_count=0,
                warnings=[str(e)],
            )

        agents = []
        for item in data.get("agents", [])[:max_results]:
            agent = RegisteredAgent(
                agent_name=item.get("name", ""),
                agent_type=self._classify_agent_type(item.get("name", "")),
                address_line1=item.get("address1"),
                address_line2=item.get("address2"),
                city=item.get("city"),
                state="DE",
                zip_code=item.get("zip"),
                status=AgentStatus.ACTIVE if item.get("active") else AgentStatus.INACTIVE,
                entity_count=item.get("entityCount", 0),
                agent_id=item.get("agentId"),
                source_state="DE",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            agents.append(agent)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            agents=agents,
            total_count=data.get("total", len(agents)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                agent_name=name,
                city=city,
                entity_name=entity_name,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class CaliforniaRegisteredAgentAPI(BaseRegisteredAgentAPI):
    """California Secretary of State registered agent lookup"""

    STATE_CODE = "CA"
    STATE_NAME = "California"
    BASE_URL = "https://bizfileonline.sos.ca.gov"
    API_URL = "https://bizfileonline.sos.ca.gov/api/search"
    SYSTEM_NAME = "California Secretary of State"

    async def search_agents(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        entity_name: Optional[str] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search California registered agents"""
        import time
        start_time = time.time()

        params = {"searchType": "AGENT", "rows": min(max_results, 100)}

        if name:
            params["agentName"] = name
        if city:
            params["city"] = city

        try:
            data = await self._fetch_json(self.API_URL, params=params)
        except Exception as e:
            logger.error(f"California agent search failed: {e}")
            return SearchResult(
                agents=[],
                total_count=0,
                warnings=[str(e)],
            )

        agents = []
        for item in data.get("results", [])[:max_results]:
            agent = RegisteredAgent(
                agent_name=item.get("agentName", ""),
                agent_type=self._classify_agent_type(item.get("agentName", ""), item.get("agentType", "")),
                address_line1=item.get("agentAddress"),
                city=item.get("agentCity"),
                state="CA",
                zip_code=item.get("agentZip"),
                status=AgentStatus.ACTIVE if item.get("status") == "ACTIVE" else AgentStatus.INACTIVE,
                entity_count=item.get("entityCount", 0),
                source_state="CA",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            agents.append(agent)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            agents=agents,
            total_count=data.get("totalCount", len(agents)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                agent_name=name,
                city=city,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class TexasRegisteredAgentAPI(BaseRegisteredAgentAPI):
    """Texas Secretary of State registered agent lookup"""

    STATE_CODE = "TX"
    STATE_NAME = "Texas"
    BASE_URL = "https://direct.sos.state.tx.us"
    API_URL = "https://direct.sos.state.tx.us/corp/corp_search"
    SYSTEM_NAME = "Texas Secretary of State"

    async def search_agents(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        entity_name: Optional[str] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search Texas registered agents"""
        import time
        start_time = time.time()

        params = {"searchType": "ra", "numResults": min(max_results, 100)}

        if name:
            params["raName"] = name
        if city:
            params["city"] = city

        try:
            data = await self._fetch_json(f"{self.API_URL}/agent", params=params)
        except Exception as e:
            logger.error(f"Texas agent search failed: {e}")
            return SearchResult(
                agents=[],
                total_count=0,
                warnings=[str(e)],
            )

        agents = []
        for item in data.get("agents", [])[:max_results]:
            agent = RegisteredAgent(
                agent_name=item.get("raName", ""),
                agent_type=self._classify_agent_type(item.get("raName", "")),
                address_line1=item.get("raAddress"),
                city=item.get("raCity"),
                state="TX",
                zip_code=item.get("raZip"),
                status=AgentStatus.ACTIVE,
                entity_count=item.get("entityCount", 0),
                source_state="TX",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            agents.append(agent)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            agents=agents,
            total_count=data.get("total", len(agents)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                agent_name=name,
                city=city,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class FloridaRegisteredAgentAPI(BaseRegisteredAgentAPI):
    """Florida Division of Corporations registered agent lookup"""

    STATE_CODE = "FL"
    STATE_NAME = "Florida"
    BASE_URL = "https://search.sunbiz.org"
    API_URL = "https://search.sunbiz.org/Inquiry"
    SYSTEM_NAME = "Florida Division of Corporations"

    async def search_agents(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        entity_name: Optional[str] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search Florida registered agents"""
        import time
        start_time = time.time()

        params = {"searchType": "RA", "searchNameOrder": ""}

        if name:
            params["searchNameOrder"] = name
        if city:
            params["city"] = city

        try:
            data = await self._fetch_json(f"{self.API_URL}/SearchByRA", params=params)
        except Exception as e:
            logger.error(f"Florida agent search failed: {e}")
            return SearchResult(
                agents=[],
                total_count=0,
                warnings=[str(e)],
            )

        agents = []
        for item in data.get("results", [])[:max_results]:
            agent = RegisteredAgent(
                agent_name=item.get("agentName", ""),
                agent_type=self._classify_agent_type(item.get("agentName", "")),
                address_line1=item.get("agentAddress"),
                city=item.get("agentCity"),
                state="FL",
                zip_code=item.get("agentZip"),
                status=AgentStatus.ACTIVE if item.get("status") == "A" else AgentStatus.INACTIVE,
                entity_count=item.get("entityCount", 0),
                source_state="FL",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            agents.append(agent)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            agents=agents,
            total_count=data.get("total", len(agents)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                agent_name=name,
                city=city,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class NevadaRegisteredAgentAPI(BaseRegisteredAgentAPI):
    """Nevada Secretary of State registered agent lookup"""

    STATE_CODE = "NV"
    STATE_NAME = "Nevada"
    BASE_URL = "https://esos.nv.gov"
    API_URL = "https://esos.nv.gov/EntitySearch/Business"
    SYSTEM_NAME = "Nevada Secretary of State"

    async def search_agents(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        entity_name: Optional[str] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search Nevada registered agents"""
        import time
        start_time = time.time()

        params = {"searchType": "RA"}

        if name:
            params["raName"] = name
        if city:
            params["city"] = city

        try:
            data = await self._fetch_json(f"{self.API_URL}/RASearch", params=params)
        except Exception as e:
            logger.error(f"Nevada agent search failed: {e}")
            return SearchResult(
                agents=[],
                total_count=0,
                warnings=[str(e)],
            )

        agents = []
        for item in data.get("agents", [])[:max_results]:
            agent = RegisteredAgent(
                agent_name=item.get("name", ""),
                agent_type=self._classify_agent_type(item.get("name", ""), item.get("type", "")),
                address_line1=item.get("address"),
                city=item.get("city"),
                state="NV",
                zip_code=item.get("zip"),
                status=AgentStatus.ACTIVE if item.get("status") == "Active" else AgentStatus.INACTIVE,
                entity_count=item.get("entityCount", 0),
                agent_id=item.get("nvId"),
                source_state="NV",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            agents.append(agent)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            agents=agents,
            total_count=data.get("total", len(agents)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                agent_name=name,
                city=city,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


# State registered agent API registry
STATE_AGENT_APIS: Dict[str, type] = {
    "DE": DelawareRegisteredAgentAPI,
    "CA": CaliforniaRegisteredAgentAPI,
    "TX": TexasRegisteredAgentAPI,
    "FL": FloridaRegisteredAgentAPI,
    "NV": NevadaRegisteredAgentAPI,
}


def get_registered_agent_api(state: str) -> Optional[BaseRegisteredAgentAPI]:
    """Get registered agent API for a state"""
    api_class = STATE_AGENT_APIS.get(state.upper())
    if api_class:
        return api_class()
    return None


# Convenience functions

def search_registered_agents(
    state: str,
    name: Optional[str] = None,
    city: Optional[str] = None,
    max_results: int = 100
) -> SearchResult:
    """Search registered agents in a state"""
    async def _search():
        api = get_registered_agent_api(state)
        if not api:
            return SearchResult(
                agents=[],
                total_count=0,
                warnings=[f"No registered agent API available for state: {state}"],
            )
        async with api:
            return await api.search_agents(
                name=name,
                city=city,
                max_results=max_results
            )
    return asyncio.run(_search())


def search_agents_by_entity(
    state: str,
    entity_name: str,
    max_results: int = 100
) -> SearchResult:
    """Search registered agents serving a specific entity"""
    async def _search():
        api = get_registered_agent_api(state)
        if not api:
            return SearchResult(
                agents=[],
                total_count=0,
                warnings=[f"No registered agent API available for state: {state}"],
            )
        async with api:
            return await api.search_agents(
                entity_name=entity_name,
                max_results=max_results
            )
    return asyncio.run(_search())


def search_all_states_agents(
    name: Optional[str] = None,
    city: Optional[str] = None,
    max_results_per_state: int = 50
) -> List[SearchResult]:
    """Search registered agents across all available states"""
    async def _search_all():
        results = []
        for state_code, api_class in STATE_AGENT_APIS.items():
            try:
                async with api_class() as api:
                    result = await api.search_agents(
                        name=name,
                        city=city,
                        max_results=max_results_per_state
                    )
                    results.append(result)
            except Exception as e:
                logger.error(f"Error searching {state_code}: {e}")
                results.append(SearchResult(
                    agents=[],
                    total_count=0,
                    warnings=[f"{state_code}: {str(e)}"],
                ))
        return results
    return asyncio.run(_search_all())
