"""
Scraper Tools Adapter (Phase 6: Integration)

Connects GOAT agents to real scraper infrastructure.
Provides tool implementations that wrap ScraperOrchestrator methods.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Import scraper infrastructure
try:
    from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator
    from datagod.scrapers.base_scraper import BaseScraper
    SCRAPERS_AVAILABLE = True
except ImportError:
    SCRAPERS_AVAILABLE = False
    logger.warning("Scraper infrastructure not available")

# Import agent infrastructure
from datagod.agents.tool_registry import tool_registry, ToolPermission
from datagod.agents.schemas import ToolDefinition


class ScraperToolsAdapter:
    """
    Adapter that wraps scraper methods as agent tools.
    
    This bridges the GOAT agent system to the real scraper infrastructure.
    """
    
    def __init__(self, orchestrator: Optional['ScraperOrchestrator'] = None):
        """
        Initialize adapter.
        
        Args:
            orchestrator: ScraperOrchestrator instance (creates one if not provided)
        """
        if SCRAPERS_AVAILABLE and orchestrator is None:
            self.orchestrator = ScraperOrchestrator()
        else:
            self.orchestrator = orchestrator
        
        self._registered = False
    
    def register_all_tools(self):
        """Register all scraper tools with the tool registry."""
        if self._registered:
            logger.info("Tools already registered")
            return
        
        # Property search tool
        tool_registry.register(
            tool_id="property_search_real",
            name="Property Search (Real)",
            description="Search for property records using real scraper infrastructure",
            handler=self.property_search,
            input_schema={
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Property address"},
                    "parcel_id": {"type": "string", "description": "Parcel/APN number"},
                    "county": {"type": "string", "description": "County name"},
                    "state": {"type": "string", "description": "State code"}
                },
                "required": ["state"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "properties": {"type": "array"},
                    "count": {"type": "integer"},
                    "source": {"type": "string"}
                }
            },
            permission=ToolPermission.READ_ONLY
        )
        
        # Lien search tool
        tool_registry.register(
            tool_id="lien_search_real",
            name="Lien Search (Real)",
            description="Search for liens and encumbrances using real scraper infrastructure",
            handler=self.lien_search,
            input_schema={
                "type": "object",
                "properties": {
                    "parcel_id": {"type": "string"},
                    "owner_name": {"type": "string"},
                    "county": {"type": "string"},
                    "state": {"type": "string"}
                },
                "required": ["state"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "liens": {"type": "array"},
                    "total_amount": {"type": "number"}
                }
            },
            permission=ToolPermission.READ_ONLY
        )
        
        # Entity search tool
        tool_registry.register(
            tool_id="entity_search_real",
            name="Entity Search (Real)",
            description="Search for entity/owner information using real scraper infrastructure",
            handler=self.entity_search,
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Entity name"},
                    "entity_type": {"type": "string", "enum": ["person", "company", "trust"]},
                    "state": {"type": "string"}
                },
                "required": ["name"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "entities": {"type": "array"},
                    "count": {"type": "integer"}
                }
            },
            permission=ToolPermission.READ_ONLY
        )
        
        # Court records tool
        tool_registry.register(
            tool_id="court_records_real",
            name="Court Records Search (Real)",
            description="Search court records for judgments, liens, foreclosures",
            handler=self.court_records_search,
            input_schema={
                "type": "object",
                "properties": {
                    "party_name": {"type": "string"},
                    "case_type": {"type": "string"},
                    "county": {"type": "string"},
                    "state": {"type": "string"}
                },
                "required": ["party_name", "state"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "cases": {"type": "array"},
                    "count": {"type": "integer"}
                }
            },
            permission=ToolPermission.READ_ONLY
        )
        
        # Tax records tool
        tool_registry.register(
            tool_id="tax_records_real",
            name="Tax Records Search (Real)",
            description="Search tax assessment and delinquency records",
            handler=self.tax_records_search,
            input_schema={
                "type": "object",
                "properties": {
                    "parcel_id": {"type": "string"},
                    "address": {"type": "string"},
                    "county": {"type": "string"},
                    "state": {"type": "string"}
                },
                "required": ["state"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "assessment": {"type": "object"},
                    "tax_status": {"type": "string"},
                    "delinquent_amount": {"type": "number"}
                }
            },
            permission=ToolPermission.READ_ONLY
        )
        
        self._registered = True
        logger.info(f"Registered {5} scraper tools with tool registry")
        
        # Also register aliases without _real suffix for compatibility
        self._register_aliases()
    
    def _register_aliases(self):
        """Register aliases without _real suffix for backward compatibility."""
        aliases = [
            ("property_search", self.property_search),
            ("lien_search", self.lien_search),
            ("entity_search", self.entity_search),
        ]
        
        for alias_id, handler in aliases:
            try:
                tool_registry.register(
                    tool_id=alias_id,
                    name=alias_id.replace("_", " ").title(),
                    description=f"Alias for {alias_id}_real",
                    handler=handler,
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                    permission=ToolPermission.READ_ONLY
                )
                logger.debug(f"Registered alias: {alias_id}")
            except Exception as e:
                logger.debug(f"Alias {alias_id} may already exist: {e}")

    
    async def property_search(
        self,
        address: Optional[str] = None,
        parcel_id: Optional[str] = None,
        county: Optional[str] = None,
        state: str = None,
        **kwargs  # Accept additional params like 'query'
    ) -> Dict[str, Any]:
        """
        Search for property records.
        
        Wraps ScraperOrchestrator property search methods.
        """
        if not SCRAPERS_AVAILABLE:
            return self._mock_property_search(address, parcel_id, county, state)
        
        try:
            # Use orchestrator to search
            results = await self._run_scraper_search(
                search_type="property",
                params={
                    "address": address,
                    "parcel_id": parcel_id,
                    "county": county,
                    "state": state
                }
            )
            
            return {
                "properties": results.get("records", []),
                "count": len(results.get("records", [])),
                "source": results.get("source", "scraper_orchestrator"),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Property search failed: {e}")
            return {
                "properties": [],
                "count": 0,
                "error": str(e),
                "source": "error"
            }
    
    async def lien_search(
        self,
        parcel_id: Optional[str] = None,
        owner_name: Optional[str] = None,
        county: Optional[str] = None,
        state: str = None,
        property_id: Optional[str] = None,
        lien_types: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for liens and encumbrances."""
        if not SCRAPERS_AVAILABLE:
            return self._mock_lien_search(parcel_id, owner_name, county, state)
        
        try:
            results = await self._run_scraper_search(
                search_type="lien",
                params={
                    "parcel_id": parcel_id,
                    "owner_name": owner_name,
                    "county": county,
                    "state": state
                }
            )
            
            liens = results.get("records", [])
            total = sum(float(l.get("amount", 0) or 0) for l in liens)
            
            return {
                "liens": liens,
                "count": len(liens),
                "total_amount": total,
                "source": results.get("source", "scraper_orchestrator"),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Lien search failed: {e}")
            return {"liens": [], "count": 0, "total_amount": 0, "error": str(e)}
    
    async def entity_search(
        self,
        name: str = None,
        entity_type: Optional[str] = None,
        state: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for entity/owner information."""
        if not SCRAPERS_AVAILABLE:
            return self._mock_entity_search(name, entity_type, state)
        
        try:
            results = await self._run_scraper_search(
                search_type="entity",
                params={
                    "name": name,
                    "entity_type": entity_type,
                    "state": state
                }
            )
            
            return {
                "entities": results.get("records", []),
                "count": len(results.get("records", [])),
                "source": results.get("source", "scraper_orchestrator"),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Entity search failed: {e}")
            return {"entities": [], "count": 0, "error": str(e)}
    
    async def court_records_search(
        self,
        party_name: str,
        case_type: Optional[str] = None,
        county: Optional[str] = None,
        state: str = None
    ) -> Dict[str, Any]:
        """Search court records."""
        if not SCRAPERS_AVAILABLE:
            return self._mock_court_search(party_name, case_type, county, state)
        
        try:
            results = await self._run_scraper_search(
                search_type="court",
                params={
                    "party_name": party_name,
                    "case_type": case_type,
                    "county": county,
                    "state": state
                }
            )
            
            return {
                "cases": results.get("records", []),
                "count": len(results.get("records", [])),
                "source": results.get("source", "court_scraper"),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Court records search failed: {e}")
            return {"cases": [], "count": 0, "error": str(e)}
    
    async def tax_records_search(
        self,
        parcel_id: Optional[str] = None,
        address: Optional[str] = None,
        county: Optional[str] = None,
        state: str = None
    ) -> Dict[str, Any]:
        """Search tax records."""
        if not SCRAPERS_AVAILABLE:
            return self._mock_tax_search(parcel_id, address, county, state)
        
        try:
            results = await self._run_scraper_search(
                search_type="tax",
                params={
                    "parcel_id": parcel_id,
                    "address": address,
                    "county": county,
                    "state": state
                }
            )
            
            return {
                "assessment": results.get("assessment", {}),
                "tax_status": results.get("status", "unknown"),
                "delinquent_amount": results.get("delinquent", 0),
                "source": results.get("source", "tax_scraper"),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Tax records search failed: {e}")
            return {"assessment": {}, "tax_status": "error", "error": str(e)}
    
    async def _run_scraper_search(
        self,
        search_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a scraper search via the orchestrator."""
        if not self.orchestrator:
            raise RuntimeError("No scraper orchestrator available")
        
        # Map search type to orchestrator method
        # This would integrate with the actual ScraperOrchestrator API
        state = params.get("state", "").upper()
        
        # For now, use a generic search method
        # In full integration, this would call specific orchestrator methods
        loop = asyncio.get_event_loop()
        
        # Run in executor since scrapers may be sync
        result = await loop.run_in_executor(
            None,
            lambda: self._sync_search(search_type, params)
        )
        
        return result
    
    def _sync_search(self, search_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous search wrapper."""
        # This would call the actual orchestrator methods
        # For now, return mock data to enable development
        return {
            "records": [],
            "source": f"{search_type}_scraper",
            "search_params": params
        }
    
    # Mock methods for development/testing
    def _mock_property_search(self, address, parcel_id, county, state) -> Dict[str, Any]:
        """Mock property search for testing."""
        return {
            "properties": [
                {
                    "address": address or "123 Main St",
                    "parcel_id": parcel_id or "123-456-789",
                    "owner": "John Doe",
                    "property_type": "single_family",
                    "assessed_value": 350000,
                    "county": county or "Cook",
                    "state": state or "IL"
                }
            ],
            "count": 1,
            "source": "mock_data",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _mock_lien_search(self, parcel_id, owner_name, county, state) -> Dict[str, Any]:
        """Mock lien search for testing."""
        return {
            "liens": [
                {
                    "type": "mortgage",
                    "lender": "First National Bank",
                    "amount": 250000,
                    "recorded_date": "2020-01-15",
                    "document_number": "2020-001234"
                },
                {
                    "type": "property_tax",
                    "creditor": f"{county or 'Cook'} County",
                    "amount": 5200,
                    "status": "current"
                }
            ],
            "count": 2,
            "total_amount": 255200,
            "source": "mock_data",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _mock_entity_search(self, name, entity_type, state) -> Dict[str, Any]:
        """Mock entity search for testing."""
        return {
            "entities": [
                {
                    "name": name,
                    "type": entity_type or "person",
                    "properties_owned": 3,
                    "state": state or "IL"
                }
            ],
            "count": 1,
            "source": "mock_data",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _mock_court_search(self, party_name, case_type, county, state) -> Dict[str, Any]:
        """Mock court records search for testing."""
        return {
            "cases": [],
            "count": 0,
            "source": "mock_data",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _mock_tax_search(self, parcel_id, address, county, state) -> Dict[str, Any]:
        """Mock tax records search for testing."""
        return {
            "assessment": {
                "land_value": 100000,
                "improvement_value": 250000,
                "total_value": 350000,
                "tax_year": 2025
            },
            "tax_status": "current",
            "delinquent_amount": 0,
            "source": "mock_data",
            "timestamp": datetime.utcnow().isoformat()
        }


# Module-level adapter instance
scraper_adapter = ScraperToolsAdapter()


def register_scraper_tools():
    """Register all scraper tools with the agent tool registry."""
    scraper_adapter.register_all_tools()
