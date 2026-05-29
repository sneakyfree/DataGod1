"""
What-If / Counterfactual Simulation Engine (DNA Strand Gene 3.5 + 4.3)

Enables "What If" analysis by modifying input parameters and comparing
scenario/blocker outcomes against a baseline.

Key Features:
- Parameter sensitivity analysis
- Delta comparison (before vs after)
- Counterfactual reasoning explanations
- Integration with ScenarioUniverseBuilder + BlockerUnlockerEngine
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .blocker_engine import Blocker, BlockerUnlockerEngine, Unlocker
from .scenario_builder import ScenarioResult, ScenarioUniverseBuilder

logger = logging.getLogger(__name__)


class ParameterCategory(str, Enum):
    """Categories of tunable parameters."""

    PROPERTY = "property"
    FINANCIAL = "financial"
    LEGAL = "legal"
    ENTITY = "entity"
    TIMING = "timing"


@dataclass
class ParameterDefinition:
    """A tunable parameter for what-if simulation."""

    id: str
    name: str
    category: ParameterCategory
    description: str
    data_type: str  # "numeric", "boolean", "string", "date"
    default_value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "data_type": self.data_type,
        }
        if self.default_value is not None:
            d["default_value"] = self.default_value
        if self.min_value is not None:
            d["min_value"] = self.min_value
        if self.max_value is not None:
            d["max_value"] = self.max_value
        if self.allowed_values:
            d["allowed_values"] = self.allowed_values
        return d


@dataclass
class SimulationDelta:
    """Difference between baseline and simulated outcomes."""

    parameter_changed: str
    original_value: Any
    simulated_value: Any
    scenarios_added: List[str] = field(default_factory=list)
    scenarios_removed: List[str] = field(default_factory=list)
    scenarios_confidence_changed: List[Dict[str, Any]] = field(default_factory=list)
    blockers_added: List[str] = field(default_factory=list)
    blockers_removed: List[str] = field(default_factory=list)
    sensitivity_score: float = 0.0  # 0-1, how much this parameter affects outcomes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_changed": self.parameter_changed,
            "original_value": self.original_value,
            "simulated_value": self.simulated_value,
            "scenarios_added": self.scenarios_added,
            "scenarios_removed": self.scenarios_removed,
            "scenarios_confidence_changed": self.scenarios_confidence_changed,
            "blockers_added": self.blockers_added,
            "blockers_removed": self.blockers_removed,
            "sensitivity_score": round(self.sensitivity_score, 4),
        }


@dataclass
class SimulationResult:
    """Complete result of a what-if simulation."""

    simulation_id: str
    baseline_scenario_count: int
    simulated_scenario_count: int
    baseline_blocker_count: int
    simulated_blocker_count: int
    deltas: List[SimulationDelta] = field(default_factory=list)
    top_sensitive_parameters: List[str] = field(default_factory=list)
    counterfactual_narrative: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "baseline_scenario_count": self.baseline_scenario_count,
            "simulated_scenario_count": self.simulated_scenario_count,
            "baseline_blocker_count": self.baseline_blocker_count,
            "simulated_blocker_count": self.simulated_blocker_count,
            "deltas": [d.to_dict() for d in self.deltas],
            "top_sensitive_parameters": self.top_sensitive_parameters,
            "counterfactual_narrative": self.counterfactual_narrative,
            "timestamp": self.timestamp.isoformat(),
        }


class WhatIfEngine:
    """
    Counterfactual simulation engine.

    Answers questions like:
    - "What if the property value were $500K instead of $300K?"
    - "What if the tax lien were removed?"
    - "What if the entity type were a trust instead of an individual?"
    """

    TUNABLE_PARAMETERS = [
        ParameterDefinition(
            "property_value",
            "Property Value",
            ParameterCategory.PROPERTY,
            "Assessed or market value of the property",
            "numeric",
            min_value=0,
        ),
        ParameterDefinition(
            "lien_amount",
            "Total Lien Amount",
            ParameterCategory.FINANCIAL,
            "Total outstanding lien amount",
            "numeric",
            min_value=0,
        ),
        ParameterDefinition(
            "has_tax_lien",
            "Tax Lien Present",
            ParameterCategory.LEGAL,
            "Whether a tax lien exists on the property",
            "boolean",
        ),
        ParameterDefinition(
            "has_mechanics_lien",
            "Mechanics Lien Present",
            ParameterCategory.LEGAL,
            "Whether a mechanics lien exists",
            "boolean",
        ),
        ParameterDefinition(
            "has_judgment_lien",
            "Judgment Lien Present",
            ParameterCategory.LEGAL,
            "Whether a judgment lien exists",
            "boolean",
        ),
        ParameterDefinition(
            "entity_type",
            "Entity Type",
            ParameterCategory.ENTITY,
            "Type of owning entity",
            "string",
            allowed_values=["individual", "corporation", "llc", "trust", "partnership"],
        ),
        ParameterDefinition(
            "years_owned",
            "Years Owned",
            ParameterCategory.TIMING,
            "Number of years the current owner has held title",
            "numeric",
            min_value=0,
        ),
        ParameterDefinition(
            "occupancy_status",
            "Occupancy Status",
            ParameterCategory.PROPERTY,
            "Current occupancy state",
            "string",
            allowed_values=["owner_occupied", "tenant_occupied", "vacant", "unknown"],
        ),
        ParameterDefinition(
            "title_clear",
            "Clear Title",
            ParameterCategory.LEGAL,
            "Whether the title is clear of defects",
            "boolean",
        ),
        ParameterDefinition(
            "property_condition",
            "Property Condition",
            ParameterCategory.PROPERTY,
            "Physical condition of the property",
            "string",
            allowed_values=["excellent", "good", "fair", "poor", "distressed"],
        ),
    ]

    def __init__(self):
        self.scenario_builder = ScenarioUniverseBuilder()
        self.blocker_engine = BlockerUnlockerEngine()
        self._sim_counter = 0

    def get_parameters(self) -> List[Dict[str, Any]]:
        """Return all tunable parameters."""
        return [p.to_dict() for p in self.TUNABLE_PARAMETERS]

    async def simulate(
        self,
        baseline_data: Dict[str, Any],
        modifications: Dict[str, Any],
    ) -> SimulationResult:
        """
        Run a what-if simulation.

        Args:
            baseline_data: Current property/entity/lien data
            modifications: Dict of parameter_id -> new_value

        Returns:
            SimulationResult with deltas and sensitivity analysis
        """
        import uuid

        self._sim_counter += 1
        sim_id = f"sim-{uuid.uuid4().hex[:8]}"

        # Split baseline data
        property_data = baseline_data.get("property", {})
        entity_data = baseline_data.get("entity", {})
        lien_data = baseline_data.get("lien", {})
        risk_data = baseline_data.get("risk", {})

        # Run baseline analysis
        baseline_scenarios = await self.scenario_builder.analyze(
            property_data, entity_data, lien_data, risk_data
        )
        baseline_blockers, baseline_unlockers = self.blocker_engine.analyze(
            property_data, lien_data
        )

        # Apply modifications to create simulated data
        sim_data = self._apply_modifications(baseline_data, modifications)
        sim_property = sim_data.get("property", {})
        sim_entity = sim_data.get("entity", {})
        sim_lien = sim_data.get("lien", {})
        sim_risk = sim_data.get("risk", {})

        # Run simulated analysis
        sim_scenarios = await self.scenario_builder.analyze(
            sim_property, sim_entity, sim_lien, sim_risk
        )
        sim_blockers, sim_unlockers = self.blocker_engine.analyze(
            sim_property, sim_lien
        )

        # Compute deltas
        deltas = self._compute_deltas(
            modifications,
            baseline_data,
            baseline_scenarios,
            sim_scenarios,
            baseline_blockers,
            sim_blockers,
        )

        # Rank by sensitivity
        sorted_deltas = sorted(deltas, key=lambda d: d.sensitivity_score, reverse=True)
        top_params = [d.parameter_changed for d in sorted_deltas[:3]]

        # Generate narrative
        narrative = self._generate_narrative(
            modifications,
            deltas,
            baseline_scenarios,
            sim_scenarios,
            baseline_blockers,
            sim_blockers,
        )

        return SimulationResult(
            simulation_id=sim_id,
            baseline_scenario_count=len(baseline_scenarios),
            simulated_scenario_count=len(sim_scenarios),
            baseline_blocker_count=len(baseline_blockers),
            simulated_blocker_count=len(sim_blockers),
            deltas=sorted_deltas,
            top_sensitive_parameters=top_params,
            counterfactual_narrative=narrative,
        )

    def _apply_modifications(
        self, baseline: Dict[str, Any], modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply parameter modifications to create simulated dataset."""
        import copy

        sim = copy.deepcopy(baseline)

        param_mapping = {
            "property_value": ("property", "value"),
            "lien_amount": ("lien", "total_amount"),
            "has_tax_lien": ("lien", "has_tax_lien"),
            "has_mechanics_lien": ("lien", "has_mechanics_lien"),
            "has_judgment_lien": ("lien", "has_judgment_lien"),
            "entity_type": ("entity", "type"),
            "years_owned": ("property", "years_owned"),
            "occupancy_status": ("property", "occupancy_status"),
            "title_clear": ("property", "title_clear"),
            "property_condition": ("property", "condition"),
        }

        for param_id, new_value in modifications.items():
            if param_id in param_mapping:
                section, key = param_mapping[param_id]
                if section not in sim:
                    sim[section] = {}
                sim[section][key] = new_value

        return sim

    def _compute_deltas(
        self,
        modifications: Dict[str, Any],
        baseline_data: Dict[str, Any],
        baseline_scenarios: List[ScenarioResult],
        sim_scenarios: List[ScenarioResult],
        baseline_blockers: List[Blocker],
        sim_blockers: List[Blocker],
    ) -> List[SimulationDelta]:
        """Compute deltas for each modified parameter."""
        baseline_scenario_ids = {s.scenario_id for s in baseline_scenarios}
        sim_scenario_ids = {s.scenario_id for s in sim_scenarios}
        baseline_blocker_ids = {b.blocker_id for b in baseline_blockers}
        sim_blocker_ids = {b.blocker_id for b in sim_blockers}

        # Build confidence maps
        baseline_conf = {s.scenario_id: s.confidence_score for s in baseline_scenarios}
        sim_conf = {s.scenario_id: s.confidence_score for s in sim_scenarios}

        deltas = []
        for param_id, new_value in modifications.items():
            # Get original value
            original = self._get_original_value(param_id, baseline_data)

            added_scenarios = list(sim_scenario_ids - baseline_scenario_ids)
            removed_scenarios = list(baseline_scenario_ids - sim_scenario_ids)

            # Confidence changes for scenarios that exist in both
            conf_changes = []
            for sid in baseline_scenario_ids & sim_scenario_ids:
                if abs(baseline_conf.get(sid, 0) - sim_conf.get(sid, 0)) > 0.01:
                    conf_changes.append(
                        {
                            "scenario_id": sid,
                            "baseline_confidence": baseline_conf[sid],
                            "simulated_confidence": sim_conf[sid],
                            "delta": round(sim_conf[sid] - baseline_conf[sid], 4),
                        }
                    )

            added_blockers = list(sim_blocker_ids - baseline_blocker_ids)
            removed_blockers = list(baseline_blocker_ids - sim_blocker_ids)

            # Sensitivity = normalized count of changes
            total_changes = (
                len(added_scenarios)
                + len(removed_scenarios)
                + len(conf_changes)
                + len(added_blockers)
                + len(removed_blockers)
            )
            total_items = max(len(baseline_scenario_ids) + len(baseline_blocker_ids), 1)
            sensitivity = min(total_changes / total_items, 1.0)

            deltas.append(
                SimulationDelta(
                    parameter_changed=param_id,
                    original_value=original,
                    simulated_value=new_value,
                    scenarios_added=added_scenarios,
                    scenarios_removed=removed_scenarios,
                    scenarios_confidence_changed=conf_changes,
                    blockers_added=added_blockers,
                    blockers_removed=removed_blockers,
                    sensitivity_score=sensitivity,
                )
            )

        return deltas

    def _get_original_value(self, param_id: str, data: Dict[str, Any]) -> Any:
        """Extract original value for a parameter from baseline data."""
        mapping = {
            "property_value": ("property", "value"),
            "lien_amount": ("lien", "total_amount"),
            "has_tax_lien": ("lien", "has_tax_lien"),
            "has_mechanics_lien": ("lien", "has_mechanics_lien"),
            "has_judgment_lien": ("lien", "has_judgment_lien"),
            "entity_type": ("entity", "type"),
            "years_owned": ("property", "years_owned"),
            "occupancy_status": ("property", "occupancy_status"),
            "title_clear": ("property", "title_clear"),
            "property_condition": ("property", "condition"),
        }
        if param_id in mapping:
            section, key = mapping[param_id]
            return data.get(section, {}).get(key)
        return None

    def _generate_narrative(
        self,
        modifications: Dict[str, Any],
        deltas: List[SimulationDelta],
        baseline_scenarios: List,
        sim_scenarios: List,
        baseline_blockers: List,
        sim_blockers: List,
    ) -> str:
        """Generate a plain-English counterfactual narrative."""
        parts = ["**Counterfactual Analysis:**\n"]

        for param_id, new_value in modifications.items():
            parts.append(f"If `{param_id}` were changed to `{new_value}`:")

        scenario_delta = len(sim_scenarios) - len(baseline_scenarios)
        blocker_delta = len(sim_blockers) - len(baseline_blockers)

        if scenario_delta > 0:
            parts.append(f"- {scenario_delta} additional scenario(s) would apply")
        elif scenario_delta < 0:
            parts.append(f"- {abs(scenario_delta)} scenario(s) would no longer apply")
        else:
            parts.append("- No change in applicable scenarios")

        if blocker_delta > 0:
            parts.append(f"- {blocker_delta} new blocker(s) would emerge")
        elif blocker_delta < 0:
            parts.append(f"- {abs(blocker_delta)} blocker(s) would be resolved")
        else:
            parts.append("- No change in blockers")

        # Highlight most sensitive parameter
        if deltas:
            top = max(deltas, key=lambda d: d.sensitivity_score)
            parts.append(
                f"\n**Most sensitive parameter:** `{top.parameter_changed}` "
                f"(sensitivity: {top.sensitivity_score:.0%})"
            )

        return "\n".join(parts)
