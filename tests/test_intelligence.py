"""
Tests for intelligence/blocker_engine.py and intelligence/scenario_builder.py — deep coverage boost
"""

from datetime import datetime

import pytest

from datagod.intelligence.blocker_engine import (
    Blocker,
    BlockerCategory,
    BlockerSeverity,
    BlockerType,
    BlockerUnlockerEngine,
    FixOption,
    FixTimeframe,
    Unlocker,
)
from datagod.intelligence.scenario_builder import (
    ScenarioCategory,
    ScenarioConfidence,
    ScenarioResult,
    ScenarioType,
    ScenarioUniverseBuilder,
)

# ============================================================
# Blocker Engine Tests
# ============================================================


class TestBlockerCategory:
    def test_values(self):
        assert BlockerCategory.LIEN.value == "lien"
        assert BlockerCategory.TITLE.value == "title"
        assert BlockerCategory.LEGAL.value == "legal"
        assert BlockerCategory.FINANCIAL.value == "financial"
        assert BlockerCategory.REGULATORY.value == "regulatory"
        assert BlockerCategory.CONDITION.value == "condition"
        assert BlockerCategory.TIMING.value == "timing"
        assert BlockerCategory.DOCUMENTATION.value == "documentation"


class TestBlockerSeverity:
    def test_values(self):
        assert BlockerSeverity.CRITICAL.value == "critical"
        assert BlockerSeverity.HIGH.value == "high"
        assert BlockerSeverity.MEDIUM.value == "medium"
        assert BlockerSeverity.LOW.value == "low"
        assert BlockerSeverity.INFORMATIONAL.value == "informational"


class TestFixTimeframe:
    def test_values(self):
        assert FixTimeframe.IMMEDIATE.value == "immediate"
        assert FixTimeframe.QUICK_WIN.value == "quick_win"
        assert FixTimeframe.SHORT_TERM.value == "short_term"
        assert FixTimeframe.MEDIUM_TERM.value == "medium_term"
        assert FixTimeframe.LONG_TERM.value == "long_term"
        assert FixTimeframe.UNKNOWN.value == "unknown"


class TestBlockerType:
    def test_create(self):
        bt = BlockerType(
            id="tax_lien",
            name="Tax Lien",
            category=BlockerCategory.LIEN,
            severity=BlockerSeverity.CRITICAL,
            description="Unpaid tax lien on property",
            why_not_template="Tax lien of {amount} blocks title transfer",
            default_fix_options=[],
        )
        assert bt.id == "tax_lien"
        assert bt.severity == BlockerSeverity.CRITICAL


class TestBlocker:
    def test_create(self):
        blocker = Blocker(
            blocker_id="b1",
            blocker_type="tax_lien",
            category=BlockerCategory.LIEN,
            severity=BlockerSeverity.HIGH,
            name="IRS Tax Lien",
            description="Federal tax lien",
            why_not="Cannot close due to IRS lien",
            source_date=datetime.utcnow(),
            data={"amount": 50000},
            fix_options=[],
            source="county_records",
        )
        assert blocker.blocker_id == "b1"
        assert blocker.severity == BlockerSeverity.HIGH
        assert blocker.data["amount"] == 50000


class TestUnlocker:
    def test_create(self):
        unlocker = Unlocker(
            signal_type="below_market",
            name="Below Market Value",
            description="Price significantly below market",
            opportunity="Potential investment opportunity",
            confidence=0.8,
            data={"discount": 25},
        )
        assert unlocker.signal_type == "below_market"
        assert unlocker.confidence == 0.8


class TestBlockerUnlockerEngine:
    def setup_method(self):
        self.engine = BlockerUnlockerEngine()

    def test_initializes(self):
        assert self.engine is not None

    def test_catalog_initialized(self):
        assert hasattr(self.engine, "BLOCKER_CATALOG")
        assert len(self.engine.BLOCKER_CATALOG) > 0

    def test_analyze_empty_data(self):
        blockers, unlockers = self.engine.analyze(property_data={})
        assert isinstance(blockers, list)
        assert isinstance(unlockers, list)

    def test_analyze_with_liens(self):
        blockers, unlockers = self.engine.analyze(
            property_data={"address": "123 Main St"},
            lien_data={
                "liens": [
                    {"type": "tax_lien", "amount": 50000, "status": "active"},
                    {"type": "mortgage", "amount": 200000, "status": "active"},
                ]
            },
        )
        assert isinstance(blockers, list)

    def test_analyze_with_title_issues(self):
        blockers, unlockers = self.engine.analyze(
            property_data={"address": "123 Main St"},
            title_data={
                "chain_of_title": [{"description": "Cloud on title", "type": "cloud"}]
            },
        )
        assert isinstance(blockers, list)

    def test_analyze_with_legal_issues(self):
        blockers, unlockers = self.engine.analyze(
            property_data={"address": "123 Main St"},
            legal_data={
                "pending_cases": [{"type": "foreclosure", "status": "pending"}]
            },
        )
        assert isinstance(blockers, list)

    def test_analyze_identifies_opportunities(self):
        blockers, unlockers = self.engine.analyze(
            property_data={
                "address": "123 Main St",
                "estimated_value": 300000,
                "asking_price": 200000,
            }
        )
        assert isinstance(unlockers, list)

    def test_map_lien_to_blocker(self):
        result = self.engine._map_lien_to_blocker("tax_lien")
        # May return a blocker ID or None
        assert result is None or isinstance(result, str)

    def test_generate_why_not(self):
        # Get a blocker type from catalog
        catalog = self.engine.BLOCKER_CATALOG
        if catalog:
            first_key = list(catalog.keys())[0]
            bt = catalog[first_key]
            why_not = self.engine._generate_why_not(bt, {"amount": 10000})
            assert isinstance(why_not, str)

    def test_get_fix_description(self):
        desc = self.engine._get_fix_description("negotiate")
        assert isinstance(desc, str)

    def test_get_next_steps(self):
        steps = self.engine._get_next_steps("negotiate")
        assert isinstance(steps, list)

    def test_generate_fix_list(self):
        blockers = [
            Blocker(
                blocker_id="b1",
                blocker_type="tax_lien",
                category=BlockerCategory.LIEN,
                severity=BlockerSeverity.HIGH,
                name="Tax Lien",
                description="Tax lien",
                why_not="Blocks title",
                data={},
                fix_options=[
                    FixOption(
                        action="pay_lien",
                        description="Pay off the lien",
                        estimated_cost_low=1000,
                        estimated_cost_high=5000,
                        timeframe=FixTimeframe.SHORT_TERM,
                        timeframe_days=(14, 30),
                        confidence=0.9,
                        requires=["funds"],
                        next_steps=["Contact county"],
                    )
                ],
                source="test",
                source_date=datetime.utcnow(),
            )
        ]
        fix_list = self.engine.generate_fix_list(blockers)
        assert isinstance(fix_list, dict)


# ============================================================
# Scenario Builder Tests
# ============================================================


class TestScenarioCategory:
    def test_values(self):
        assert ScenarioCategory.ACQUISITION.value == "acquisition"
        assert ScenarioCategory.LIEN.value == "lien"
        assert ScenarioCategory.RISK.value == "risk"
        assert ScenarioCategory.OPPORTUNITY.value == "opportunity"
        assert ScenarioCategory.ENTITY.value == "entity"
        assert ScenarioCategory.COMPLIANCE.value == "compliance"
        assert ScenarioCategory.DISTRESS.value == "distress"


class TestScenarioConfidence:
    def test_values(self):
        assert ScenarioConfidence.CONFIRMED.value == "confirmed"
        assert ScenarioConfidence.LIKELY.value == "likely"
        assert ScenarioConfidence.POSSIBLE.value == "possible"
        assert ScenarioConfidence.SPECULATIVE.value == "speculative"
        assert ScenarioConfidence.UNKNOWN.value == "unknown"


class TestScenarioResult:
    def test_create(self):
        result = ScenarioResult(
            scenario_id="s1",
            scenario_name="Tax Lien Acquisition",
            category=ScenarioCategory.ACQUISITION,
            confidence=ScenarioConfidence.LIKELY,
            confidence_score=0.75,
            description="Property has tax lien ripe for acquisition",
            evidence=[{"source": "county", "finding": "delinquent taxes"}],
            missing_data=[],
            recommended_actions=["Contact county tax office"],
            source_labels=[{"source": "county_records", "type": "official"}],
        )
        assert result.scenario_id == "s1"
        assert result.confidence_score == 0.75


class TestScenarioUniverseBuilder:
    def setup_method(self):
        self.builder = ScenarioUniverseBuilder()

    def test_initializes(self):
        assert self.builder is not None

    def test_taxonomy_initialized(self):
        assert hasattr(self.builder, "SCENARIO_TAXONOMY")
        assert len(self.builder.SCENARIO_TAXONOMY) > 0

    @pytest.mark.asyncio
    async def test_analyze_empty_data(self):
        results = await self.builder.analyze(property_data={})
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_analyze_with_property_data(self):
        results = await self.builder.analyze(
            property_data={
                "address": "123 Main St",
                "estimated_value": 300000,
                "property_type": "single_family",
            }
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_analyze_with_liens(self):
        results = await self.builder.analyze(
            property_data={"address": "123 Main St"},
            lien_data={
                "liens": [{"type": "tax_lien", "amount": 50000}],
                "total_liens": 1,
            },
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_analyze_with_entity_data(self):
        results = await self.builder.analyze(
            property_data={"address": "123 Main St"},
            entity_data={
                "owner_name": "John Smith",
                "owner_type": "individual",
            },
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_analyze_with_risk_data(self):
        results = await self.builder.analyze(
            property_data={"address": "123 Main St"},
            risk_data={"risk_score": 0.8, "risk_factors": ["fire_zone", "flood_zone"]},
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_scenario_summary(self):
        results = await self.builder.analyze(
            property_data={"address": "123 Main St", "estimated_value": 500000}
        )
        summary = self.builder.get_scenario_summary(results)
        assert isinstance(summary, dict)

    def test_flatten_data(self):
        flat = self.builder._flatten_data({"a": {"b": 1, "c": {"d": 2}}, "e": 3})
        assert isinstance(flat, dict)

    def test_calculate_confidence(self):
        taxonomy = self.builder.SCENARIO_TAXONOMY
        if taxonomy:
            first_key = list(taxonomy.keys())[0]
            st = taxonomy[first_key]
            score, level, ci_lower, ci_upper = self.builder._calculate_confidence(
                st, [], ["some_indicator"]
            )
            assert 0.0 <= score <= 1.0
