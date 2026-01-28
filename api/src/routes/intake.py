"""
Intake Wizard API Routes (Phase 6.2)

FastAPI routes for guided intake wizard.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["intake"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class StartSessionRequest(BaseModel):
    """Request to start an intake session."""
    schema_id: str = Field(..., description="ID of the intake schema to use")


class StartSessionResponse(BaseModel):
    """Response from starting a session."""
    session_id: str
    schema_name: str
    total_stages: int
    current_stage: int
    fields: List[Dict[str, Any]]
    groups: List[Dict[str, Any]]


class SubmitStageRequest(BaseModel):
    """Request to submit stage data."""
    data: Dict[str, Any] = Field(..., description="Field values for this stage")


class SubmitStageResponse(BaseModel):
    """Response from submitting a stage."""
    session_id: str
    current_stage: int
    validations: List[Dict[str, Any]]
    contradictions: List[Dict[str, Any]]
    verification_tasks: List[Dict[str, Any]]
    can_proceed: bool
    next_stage: Optional[int] = None
    next_fields: Optional[List[Dict[str, Any]]] = None
    complete: bool = False
    final_data: Optional[Dict[str, Any]] = None


class SessionSummaryResponse(BaseModel):
    """Session summary response."""
    session_id: str
    schema_id: str
    data: Dict[str, Any]
    uncertain_fields: List[str]
    verification_tasks: List[Dict[str, Any]]
    contradictions: List[Dict[str, Any]]
    complete: bool


class ResolveContradictionRequest(BaseModel):
    """Request to resolve a contradiction."""
    contradiction_index: int
    resolution: Dict[str, Any]


# Session storage (in production, use Redis or database)
_sessions: Dict[str, Any] = {}


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/schemas")
async def list_schemas():
    """
    List available intake schemas.
    """
    try:
        from datagod.ux import GuidedIntakeWizard
        
        wizard = GuidedIntakeWizard()
        
        schemas = [
            {
                "id": schema.schema_id,
                "name": schema.name,
                "description": schema.description,
                "stages": len(schema.progressive_stages)
            }
            for schema in wizard.SCHEMAS.values()
        ]
        
        return {"schemas": schemas}
        
    except Exception as e:
        logger.error(f"List schemas failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/start", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest):
    """
    Start a new intake session.
    
    Returns the first stage fields to display.
    """
    try:
        from datagod.ux import GuidedIntakeWizard
        
        wizard = GuidedIntakeWizard()
        session = wizard.start_session(request.schema_id)
        
        # Store wizard instance for this session
        _sessions[session["session_id"]] = wizard
        
        return StartSessionResponse(
            session_id=session["session_id"],
            schema_name=session["schema_name"],
            total_stages=session["total_stages"],
            current_stage=session["current_stage"],
            fields=session["fields"],
            groups=session["groups"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Start session failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{session_id}/submit", response_model=SubmitStageResponse)
async def submit_stage(session_id: str, request: SubmitStageRequest):
    """
    Submit data for the current stage.
    
    Validates data, checks for contradictions, and returns next stage if applicable.
    """
    try:
        wizard = _sessions.get(session_id)
        if not wizard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )
        
        result = wizard.submit_stage(session_id, request.data)
        
        return SubmitStageResponse(
            session_id=result["session_id"],
            current_stage=result["current_stage"],
            validations=result["validations"],
            contradictions=result["contradictions"],
            verification_tasks=result["verification_tasks"],
            can_proceed=result["can_proceed"],
            next_stage=result.get("next_stage"),
            next_fields=result.get("next_fields"),
            complete=result.get("complete", False),
            final_data=result.get("final_data")
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Submit stage failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(session_id: str):
    """
    Get summary of an intake session.
    """
    try:
        wizard = _sessions.get(session_id)
        if not wizard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )
        
        summary = wizard.get_summary(session_id)
        
        return SessionSummaryResponse(
            session_id=summary["session_id"],
            schema_id=summary["schema_id"],
            data=summary["data"],
            uncertain_fields=summary["uncertain_fields"],
            verification_tasks=summary["verification_tasks"],
            contradictions=summary["contradictions"],
            complete=summary["complete"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get summary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{session_id}/resolve")
async def resolve_contradiction(session_id: str, request: ResolveContradictionRequest):
    """
    Resolve a detected contradiction.
    """
    try:
        wizard = _sessions.get(session_id)
        if not wizard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )
        
        result = wizard.resolve_contradiction(
            session_id,
            request.contradiction_index,
            request.resolution
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resolve contradiction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
