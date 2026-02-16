"""
DataGod Intelligence Package (Phase 3)

Provides the intelligence layer with:
- Scenario Universe Builder for exhaustive scenario enumeration
- Blocker/Unlocker Engine for actionable fix lists
- What-If / Counterfactual Simulation Engine
"""

from .scenario_builder import (
    ScenarioUniverseBuilder,
    ScenarioCategory,
    ScenarioConfidence,
    ScenarioType,
    ScenarioResult
)

from .blocker_engine import (
    BlockerUnlockerEngine,
    BlockerCategory,
    BlockerSeverity,
    FixTimeframe,
    BlockerType,
    FixOption,
    Blocker,
    Unlocker
)

from .whatif_engine import (
    WhatIfEngine,
    ParameterCategory,
    ParameterDefinition,
    SimulationDelta,
    SimulationResult,
)

__all__ = [
    # Scenario Builder
    'ScenarioUniverseBuilder',
    'ScenarioCategory',
    'ScenarioConfidence',
    'ScenarioType',
    'ScenarioResult',
    # Blocker Engine
    'BlockerUnlockerEngine',
    'BlockerCategory',
    'BlockerSeverity',
    'FixTimeframe',
    'BlockerType',
    'FixOption',
    'Blocker',
    'Unlocker',
    # What-If Engine
    'WhatIfEngine',
    'ParameterCategory',
    'ParameterDefinition',
    'SimulationDelta',
    'SimulationResult',
]
