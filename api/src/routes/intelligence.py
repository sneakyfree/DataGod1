"""
Intelligence API Routes (Phase 6.2)

FastAPI routes for intelligence layer capabilities.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ScenarioAnalysisRequest(BaseModel):
    """Request for scenario analysis."""
    property_data: Dict[str, Any] = Field(default_factory=dict)
    entity_data: Optional[Dict[str, Any]] = None
    lien_data: Optional[Dict[str, Any]] = None
    risk_data: Optional[Dict[str, Any]] = None


class ScenarioResult(BaseModel):
    """A single scenario result."""
    scenario_id: str
    scenario_name: str
    category: str
    confidence: str
    confidence_score: float
    description: str
    recommended_actions: List[str]


class ScenarioAnalysisResponse(BaseModel):
    """Response from scenario analysis."""
    total_scenarios: int
    high_confidence_count: int
    by_category: Dict[str, int]
    scenarios: List[ScenarioResult]
    summary: Dict[str, Any]
    timestamp: str


class BlockerAnalysisRequest(BaseModel):
    """Request for blocker analysis."""
    property_data: Dict[str, Any] = Field(default_factory=dict)
    lien_data: Optional[Dict[str, Any]] = None
    title_data: Optional[Dict[str, Any]] = None
    legal_data: Optional[Dict[str, Any]] = None


class BlockerResult(BaseModel):
    """A single blocker result."""
    blocker_id: str
    blocker_type: str
    name: str
    severity: str
    why_not: str
    priority_score: float


class FixOption(BaseModel):
    """A fix option for a blocker."""
    action: str
    description: str
    cost_range: Optional[str] = None
    timeframe: str
    confidence: float


class BlockerAnalysisResponse(BaseModel):
    """Response from blocker analysis."""
    total_blockers: int
    critical_count: int
    high_count: int
    blockers: List[BlockerResult]
    fix_list: Dict[str, List[Dict[str, Any]]]
    unlockers: List[Dict[str, Any]]
    timestamp: str


# =============================================================================
# ROUTES
# =============================================================================

@router.post("/scenarios", response_model=ScenarioAnalysisResponse)
async def analyze_scenarios(request: ScenarioAnalysisRequest):
    """
    Run scenario analysis using the ScenarioUniverseBuilder.
    
    Identifies all possible scenarios for a property/entity and ranks
    by confidence and relevance.
    """
    try:
        from datagod.intelligence import ScenarioUniverseBuilder
        
        builder = ScenarioUniverseBuilder()
        
        scenarios = await builder.analyze(
            property_data=request.property_data,
            entity_data=request.entity_data,
            lien_data=request.lien_data,
            risk_data=request.risk_data
        )
        
        summary = builder.get_scenario_summary(scenarios)
        
        # Convert to response format
        scenario_results = [
            ScenarioResult(
                scenario_id=s.scenario_id,
                scenario_name=s.scenario_name,
                category=s.category.value,
                confidence=s.confidence.value,
                confidence_score=s.confidence_score,
                description=s.description,
                recommended_actions=s.recommended_actions
            )
            for s in scenarios[:20]  # Limit to top 20
        ]
        
        return ScenarioAnalysisResponse(
            total_scenarios=len(scenarios),
            high_confidence_count=summary.get("high_confidence_count", 0),
            by_category=summary.get("by_category", {}),
            scenarios=scenario_results,
            summary=summary,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Scenario analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario analysis failed: {str(e)}"
        )


@router.post("/blockers", response_model=BlockerAnalysisResponse)
async def analyze_blockers(request: BlockerAnalysisRequest):
    """
    Run blocker analysis using the BlockerUnlockerEngine.
    
    Identifies all blockers and generates prioritized fix lists.
    """
    try:
        from datagod.intelligence import BlockerUnlockerEngine
        
        engine = BlockerUnlockerEngine()
        
        blockers, unlockers = engine.analyze(
            property_data=request.property_data,
            lien_data=request.lien_data,
            title_data=request.title_data,
            legal_data=request.legal_data
        )
        
        fix_list = engine.generate_fix_list(blockers)
        
        # Count by severity
        critical_count = len([b for b in blockers if b.severity.value == "critical"])
        high_count = len([b for b in blockers if b.severity.value == "high"])
        
        # Convert to response format
        blocker_results = [
            BlockerResult(
                blocker_id=b.blocker_id,
                blocker_type=b.blocker_type,
                name=b.name,
                severity=b.severity.value,
                why_not=b.why_not,
                priority_score=b.priority_score
            )
            for b in blockers
        ]
        
        unlocker_results = [
            {
                "signal_type": u.signal_type,
                "name": u.name,
                "description": u.description,
                "opportunity": u.opportunity,
                "confidence": u.confidence
            }
            for u in unlockers
        ]
        
        return BlockerAnalysisResponse(
            total_blockers=len(blockers),
            critical_count=critical_count,
            high_count=high_count,
            blockers=blocker_results,
            fix_list=fix_list,
            unlockers=unlocker_results,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Blocker analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Blocker analysis failed: {str(e)}"
        )


@router.get("/scenarios/{scenario_id}")
async def get_scenario_details(scenario_id: str):
    """
    Get detailed information about a specific scenario type.
    """
    try:
        from datagod.intelligence import ScenarioUniverseBuilder
        
        builder = ScenarioUniverseBuilder()
        scenario_type = builder.SCENARIO_TAXONOMY.get(scenario_id)
        
        if not scenario_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario type not found: {scenario_id}"
            )
        
        return {
            "id": scenario_type.id,
            "name": scenario_type.name,
            "category": scenario_type.category.value,
            "description": scenario_type.description,
            "required_data": scenario_type.required_data,
            "indicators": scenario_type.indicators,
            "risk_level": scenario_type.risk_level,
            "actionable": scenario_type.actionable
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get scenario details failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/blockers/{blocker_id}")
async def get_blocker_details(blocker_id: str):
    """
    Get detailed information about a specific blocker type.
    """
    try:
        from datagod.intelligence import BlockerUnlockerEngine
        
        engine = BlockerUnlockerEngine()
        blocker_type = engine.BLOCKER_CATALOG.get(blocker_id)
        
        if not blocker_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blocker type not found: {blocker_id}"
            )
        
        return {
            "id": blocker_type.id,
            "name": blocker_type.name,
            "category": blocker_type.category.value,
            "severity": blocker_type.severity.value,
            "description": blocker_type.description,
            "requires_professional": blocker_type.requires_professional,
            "default_fix_options": blocker_type.default_fix_options
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get blocker details failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
