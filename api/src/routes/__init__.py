"""
API Routes Package (Phase 6.2)

Aggregates all GOAT API routes.
"""

from .agents import router as agents_router
from .anomalies import router as anomalies_router
from .intelligence import router as intelligence_router
from .intake import router as intake_router
from .reports import router as reports_router
from .snapshots import router as snapshots_router
from .whatif import router as whatif_router
from .explainability import router as explainability_router

__all__ = [
    'agents_router',
    'anomalies_router',
    'intelligence_router',
    'intake_router',
    'reports_router',
    'snapshots_router',
    'whatif_router',
    'explainability_router',
]
