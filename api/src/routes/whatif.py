"""
What-If Simulation API Routes (DNA Strand Gene 3.5 + 4.3)

Endpoints for counterfactual reasoning and parameter sensitivity analysis.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/whatif", tags=["what-if"])


class SimulateRequest(BaseModel):
    """Request to run a what-if simulation."""

    baseline_data: Dict[str, Any] = Field(
        ..., description="Current property/entity/lien data"
    )
    modifications: Dict[str, Any] = Field(
        ..., description="Parameter changes to simulate (param_id -> new_value)"
    )


class SimulateResponse(BaseModel):
    """What-if simulation result."""

    simulation_id: str
    baseline_scenario_count: int
    simulated_scenario_count: int
    baseline_blocker_count: int
    simulated_blocker_count: int
    deltas: List[Dict[str, Any]]
    top_sensitive_parameters: List[str]
    counterfactual_narrative: str


@router.get("/parameters")
async def list_parameters():
    """List all tunable parameters for what-if simulation."""
    from datagod.intelligence.whatif_engine import WhatIfEngine

    engine = WhatIfEngine()
    return {
        "parameters": engine.get_parameters(),
        "total": len(engine.TUNABLE_PARAMETERS),
    }


@router.post("/simulate", response_model=SimulateResponse)
async def run_simulation(request: SimulateRequest):
    """
    Run a what-if simulation.

    Modifies specified parameters and compares scenario/blocker outcomes
    against the baseline to reveal sensitivity and counterfactual insights.
    """
    from datagod.intelligence.whatif_engine import WhatIfEngine

    engine = WhatIfEngine()

    try:
        result = await engine.simulate(
            baseline_data=request.baseline_data,
            modifications=request.modifications,
        )
        return SimulateResponse(**result.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")
