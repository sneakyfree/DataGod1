"""
Agent API Routes (Phase 6.2)

FastAPI routes for GOAT agent capabilities.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class AgentQueryRequest(BaseModel):
    """Request to submit a query to the orchestrator."""
    query: str = Field(..., description="The research query", min_length=3)
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    priority: str = Field(default="normal", description="Priority level")


class AgentQueryResponse(BaseModel):
    """Response from agent query."""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    agents_consulted: List[str] = []
    requires_approval: bool = False
    timestamp: str


class PropertySearchRequest(BaseModel):
    """Request for property search."""
    address: Optional[str] = None
    parcel_id: Optional[str] = None
    county: Optional[str] = None
    state: str = Field(..., min_length=2, max_length=2)


class EntitySearchRequest(BaseModel):
    """Request for entity search."""
    name: str = Field(..., min_length=2)
    entity_type: Optional[str] = None
    state: Optional[str] = None


class LienSearchRequest(BaseModel):
    """Request for lien search."""
    parcel_id: Optional[str] = None
    owner_name: Optional[str] = None
    county: Optional[str] = None
    state: str = Field(..., min_length=2, max_length=2)


class TaskStatusResponse(BaseModel):
    """Response for task status check."""
    task_id: str
    status: str
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =============================================================================
# ROUTES
# =============================================================================

@router.post("/query", response_model=AgentQueryResponse)
async def submit_agent_query(
    request: AgentQueryRequest,
    background_tasks: BackgroundTasks,
    # current_user: User = Depends(get_current_active_user)  # Add auth when wiring
):
    """
    Submit a query to the GOAT orchestrator agent.
    
    The orchestrator will decompose the query, route to specialist agents,
    and synthesize results.
    """
    try:
        from datagod.agents import OrchestratorAgent
        from datagod.agents.scraper_tools import register_scraper_tools
        
        # Ensure scraper tools are registered
        register_scraper_tools()
        
        orchestrator = OrchestratorAgent()
        
        result = await orchestrator.process_query(
            query=request.query,
            context=request.context,
            user_id=1  # Replace with current_user.id when auth is wired
        )
        
        return AgentQueryResponse(
            task_id=result.task_id,
            status="completed",
            result=result.result,
            confidence=result.confidence,
            agents_consulted=result.result.get("agents_consulted", []) if result.result else [],
            requires_approval=result.requires_approval,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Agent query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent query failed: {str(e)}"
        )


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of an agent task.
    
    For long-running tasks, use this to poll for completion.
    """
    # In production, this would check a task queue/store
    return TaskStatusResponse(
        task_id=task_id,
        status="completed",
        progress=1.0
    )


@router.post("/property", response_model=AgentQueryResponse)
async def property_research(request: PropertySearchRequest):
    """
    Run property research using the PropertyResearchAgent.
    
    Searches for property information, ownership, and related records.
    """
    try:
        from datagod.agents.specialists import PropertyResearchAgent
        from datagod.agents.schemas import AgentTask
        from datagod.agents.scraper_tools import register_scraper_tools
        
        register_scraper_tools()
        
        agent = PropertyResearchAgent()
        task = AgentTask(
            query=f"Research property: {request.address or request.parcel_id}",
            context={
                "address": request.address,
                "parcel_id": request.parcel_id,
                "county": request.county,
                "state": request.state
            }
        )
        
        result = await agent.process(task)
        
        return AgentQueryResponse(
            task_id=result.task_id,
            status="completed",
            result=result.result,
            confidence=result.confidence,
            agents_consulted=["property_research"],
            requires_approval=result.requires_approval,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Property research failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Property research failed: {str(e)}"
        )


@router.post("/entity", response_model=AgentQueryResponse)
async def entity_research(request: EntitySearchRequest):
    """
    Run entity research using the EntityResolutionAgent.
    
    Searches for entity/owner information and related properties.
    """
    try:
        from datagod.agents.specialists import EntityResolutionAgent
        from datagod.agents.schemas import AgentTask
        from datagod.agents.scraper_tools import register_scraper_tools
        
        register_scraper_tools()
        
        agent = EntityResolutionAgent()
        task = AgentTask(
            query=f"Research entity: {request.name}",
            context={
                "name": request.name,
                "entity_type": request.entity_type,
                "state": request.state
            }
        )
        
        result = await agent.process(task)
        
        return AgentQueryResponse(
            task_id=result.task_id,
            status="completed",
            result=result.result,
            confidence=result.confidence,
            agents_consulted=["entity_resolution"],
            requires_approval=result.requires_approval,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Entity research failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity research failed: {str(e)}"
        )


@router.post("/lien", response_model=AgentQueryResponse)
async def lien_research(request: LienSearchRequest):
    """
    Run lien research using the LienPriorityAgent.
    
    Searches for liens and calculates priority stack.
    """
    try:
        from datagod.agents.specialists import LienPriorityAgent
        from datagod.agents.schemas import AgentTask
        from datagod.agents.scraper_tools import register_scraper_tools
        
        register_scraper_tools()
        
        agent = LienPriorityAgent()
        task = AgentTask(
            query=f"Find liens for: {request.parcel_id or request.owner_name}",
            context={
                "parcel_id": request.parcel_id,
                "owner_name": request.owner_name,
                "county": request.county,
                "state": request.state
            }
        )
        
        result = await agent.process(task)
        
        return AgentQueryResponse(
            task_id=result.task_id,
            status="completed",
            result=result.result,
            confidence=result.confidence,
            agents_consulted=["lien_priority"],
            requires_approval=result.requires_approval,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Lien research failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lien research failed: {str(e)}"
        )
