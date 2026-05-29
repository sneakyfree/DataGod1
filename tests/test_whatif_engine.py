"""
Tests for What-If / Counterfactual Simulation Engine (Gap P1)
"""

import asyncio

import pytest

from datagod.intelligence.whatif_engine import (
    ParameterCategory,
    ParameterDefinition,
    SimulationDelta,
    SimulationResult,
    WhatIfEngine,
)


class TestParameterDefinition:
    """Test parameter definitions."""

    def test_parameter_has_required_fields(self):
        p = ParameterDefinition(
            id="test_param",
            name="Test Param",
            category=ParameterCategory.PROPERTY,
            description="A test parameter",
            data_type="numeric",
        )
        assert p.id == "test_param"
        assert p.category == ParameterCategory.PROPERTY
        assert p.data_type == "numeric"

    def test_parameter_to_dict(self):
        p = ParameterDefinition(
            id="val",
            name="Value",
            category=ParameterCategory.FINANCIAL,
            description="desc",
            data_type="numeric",
            min_value=0,
            max_value=1000000,
        )
        d = p.to_dict()
        assert d["id"] == "val"
        assert d["min_value"] == 0
        assert d["max_value"] == 1000000
        assert "category" in d

    def test_parameter_with_allowed_values(self):
        p = ParameterDefinition(
            id="status",
            name="Status",
            category=ParameterCategory.PROPERTY,
            description="desc",
            data_type="string",
            allowed_values=["active", "inactive"],
        )
        d = p.to_dict()
        assert d["allowed_values"] == ["active", "inactive"]


class TestParameterCategory:
    """Test parameter category enum."""

    def test_all_categories_exist(self):
        assert ParameterCategory.PROPERTY == "property"
        assert ParameterCategory.FINANCIAL == "financial"
        assert ParameterCategory.LEGAL == "legal"
        assert ParameterCategory.ENTITY == "entity"
        assert ParameterCategory.TIMING == "timing"


class TestWhatIfEngine:
    """Test the WhatIfEngine core class."""

    def setup_method(self):
        self.engine = WhatIfEngine()

    def test_get_parameters_returns_list(self):
        params = self.engine.get_parameters()
        assert isinstance(params, list)
        assert len(params) >= 10  # We defined 10 tunable parameters

    def test_get_parameters_structure(self):
        params = self.engine.get_parameters()
        for p in params:
            assert "id" in p
            assert "name" in p
            assert "category" in p
            assert "description" in p
            assert "data_type" in p

    def test_parameter_ids_unique(self):
        params = self.engine.get_parameters()
        ids = [p["id"] for p in params]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_simulate_returns_result(self):
        baseline = {
            "property": {"value": 300000, "years_owned": 5},
            "lien": {"total_amount": 0},
            "entity": {"type": "individual"},
            "risk": {},
        }
        modifications = {"property_value": 500000}
        result = await self.engine.simulate(baseline, modifications)
        assert isinstance(result, SimulationResult)
        assert result.simulation_id.startswith("sim-")

    @pytest.mark.asyncio
    async def test_simulate_tracks_counts(self):
        baseline = {"property": {}, "lien": {}, "entity": {}, "risk": {}}
        modifications = {"has_tax_lien": True}
        result = await self.engine.simulate(baseline, modifications)
        assert result.baseline_scenario_count >= 0
        assert result.simulated_scenario_count >= 0

    @pytest.mark.asyncio
    async def test_simulate_generates_narrative(self):
        baseline = {"property": {"value": 200000}, "lien": {}, "entity": {}, "risk": {}}
        modifications = {"property_value": 400000}
        result = await self.engine.simulate(baseline, modifications)
        assert len(result.counterfactual_narrative) > 0
        assert "Counterfactual" in result.counterfactual_narrative

    @pytest.mark.asyncio
    async def test_simulate_multiple_modifications(self):
        baseline = {"property": {}, "lien": {}, "entity": {}, "risk": {}}
        modifications = {
            "property_value": 500000,
            "has_tax_lien": True,
            "entity_type": "trust",
        }
        result = await self.engine.simulate(baseline, modifications)
        assert len(result.deltas) == 3

    def test_apply_modifications(self):
        baseline = {"property": {"value": 100}, "lien": {}}
        mods = {"property_value": 999}
        sim = self.engine._apply_modifications(baseline, mods)
        assert sim["property"]["value"] == 999
        # Original unchanged
        assert baseline["property"]["value"] == 100

    def test_to_dict(self):
        result = SimulationResult(
            simulation_id="sim-test",
            baseline_scenario_count=10,
            simulated_scenario_count=12,
            baseline_blocker_count=2,
            simulated_blocker_count=1,
        )
        d = result.to_dict()
        assert d["simulation_id"] == "sim-test"
        assert d["baseline_scenario_count"] == 10


class TestSimulationDelta:
    """Test SimulationDelta dataclass."""

    def test_delta_to_dict(self):
        delta = SimulationDelta(
            parameter_changed="property_value",
            original_value=300000,
            simulated_value=500000,
            scenarios_added=["below_market_value"],
            sensitivity_score=0.75,
        )
        d = delta.to_dict()
        assert d["parameter_changed"] == "property_value"
        assert d["sensitivity_score"] == 0.75
        assert d["scenarios_added"] == ["below_market_value"]
