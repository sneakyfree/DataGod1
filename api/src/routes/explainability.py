"""
Explainability API Routes (DNA Strand Gene 4.1/4.5)

Exposes on-demand 4-layer explanations for anomalies, search results,
and data quality assessments.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/explainability", tags=["explainability"])


class AnomalyExplainRequest(BaseModel):
    """Request to explain an anomaly detection."""
    anomaly_id: str
    anomaly_type: str
    confidence: float = Field(..., ge=0, le=1)
    features: Dict[str, Any]
    detection_method: str = "isolation_forest"


class SearchExplainRequest(BaseModel):
    """Request to explain search results."""
    query: str
    result_count: int
    filters_applied: Dict[str, Any] = {}


class QualityExplainRequest(BaseModel):
    """Request to explain data quality score."""
    quality_score: float = Field(..., ge=0, le=1)
    dimensions: Dict[str, float]
    issues: List[Dict[str, Any]] = []


class ExplainResponse(BaseModel):
    """Structured 4-layer explanation response."""
    decision_id: str
    decision_type: str
    summary: str
    layers: Dict[str, Any]
    created_at: str


@router.post("/anomaly", response_model=ExplainResponse)
async def explain_anomaly(request: AnomalyExplainRequest):
    """Generate 4-layer explanation for an anomaly detection result."""
    from datagod.services.explainability import ExplainabilityService
    svc = ExplainabilityService()
    explanation = svc.explain_anomaly(
        anomaly_id=request.anomaly_id,
        anomaly_type=request.anomaly_type,
        confidence=request.confidence,
        features=request.features,
        detection_method=request.detection_method,
    )
    return ExplainResponse(**explanation.to_dict())


@router.post("/search", response_model=ExplainResponse)
async def explain_search(request: SearchExplainRequest):
    """Generate explanation for search result ranking."""
    from datagod.services.explainability import ExplainabilityService
    svc = ExplainabilityService()
    explanation = svc.explain_search(
        query=request.query,
        result_count=request.result_count,
        filters_applied=request.filters_applied,
    )
    return ExplainResponse(**explanation.to_dict())


@router.post("/quality", response_model=ExplainResponse)
async def explain_quality(request: QualityExplainRequest):
    """Generate explanation for data quality assessment."""
    from datagod.services.explainability import ExplainabilityService
    svc = ExplainabilityService()
    explanation = svc.explain_data_quality(
        quality_score=request.quality_score,
        dimensions=request.dimensions,
        issues=request.issues,
    )
    return ExplainResponse(**explanation.to_dict())


@router.get("/layers")
async def list_layers():
    """Describe the 4 explainability layers."""
    return {
        "layers": [
            {"id": "user", "name": "User Layer", "description": "Plain-English explanation for end users"},
            {"id": "technical", "name": "Technical Layer", "description": "Technical details for data analysts"},
            {"id": "audit", "name": "Audit Layer", "description": "Full decision trace for compliance auditing"},
            {"id": "compliance", "name": "Compliance Layer", "description": "Regulatory documentation and references"},
        ]
    }
