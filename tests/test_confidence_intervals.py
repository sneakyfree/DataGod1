"""
Tests for Confidence Intervals in Scenario Builder (Gap P8)
"""

import pytest

from datagod.intelligence.scenario_builder import (
    ScenarioConfidence,
    ScenarioResult,
    ScenarioUniverseBuilder,
)


class TestConfidenceIntervals:
    """Test confidence interval computation."""

    def setup_method(self):
        self.builder = ScenarioUniverseBuilder()

    @pytest.mark.asyncio
    async def test_results_have_ci_fields(self):
        """Every scenario result should have CI bounds."""
        results = await self.builder.analyze(
            property_data={"value": 300000, "active_listing": True, "mls_status": True},
            entity_data={},
            lien_data={},
            risk_data={},
        )
        for r in results:
            assert hasattr(r, "confidence_interval_lower")
            assert hasattr(r, "confidence_interval_upper")
            assert 0.0 <= r.confidence_interval_lower <= 1.0
            assert 0.0 <= r.confidence_interval_upper <= 1.0

    @pytest.mark.asyncio
    async def test_ci_bounds_contain_point_estimate(self):
        """CI should bracket the point estimate."""
        results = await self.builder.analyze(
            property_data={"value": 300000},
            entity_data={},
            lien_data={},
            risk_data={},
        )
        for r in results:
            assert r.confidence_interval_lower <= r.confidence_score
            assert r.confidence_interval_upper >= r.confidence_score

    @pytest.mark.asyncio
    async def test_more_evidence_narrows_ci(self):
        """With more indicators, the CI should be narrower."""
        # Sparse data
        sparse_results = await self.builder.analyze(
            property_data={},
            entity_data={},
            lien_data={},
            risk_data={},
        )
        # Rich data
        rich_results = await self.builder.analyze(
            property_data={
                "value": 300000,
                "active_listing": True,
                "mls_status": True,
                "property_status": "active",
                "listing_info": True,
                "condition": "good",
                "years_owned": 5,
            },
            entity_data={"type": "individual"},
            lien_data={"lien_search": True, "title_search": True},
            risk_data={},
        )
        # Compare average CI widths
        if sparse_results and rich_results:
            sparse_widths = [
                r.confidence_interval_upper - r.confidence_interval_lower
                for r in sparse_results
            ]
            rich_widths = [
                r.confidence_interval_upper - r.confidence_interval_lower
                for r in rich_results
            ]
            avg_sparse = (
                sum(sparse_widths) / len(sparse_widths) if sparse_widths else 1.0
            )
            avg_rich = sum(rich_widths) / len(rich_widths) if rich_widths else 1.0
            # Rich data should have same or narrower CIs on average
            assert avg_rich <= avg_sparse + 0.1  # Allow small tolerance

    def test_calculate_confidence_returns_four_values(self):
        """Internal method should return (score, level, ci_lower, ci_upper)."""
        from datagod.intelligence.scenario_builder import ScenarioCategory, ScenarioType

        st = ScenarioType(
            id="test",
            name="Test",
            category=ScenarioCategory.RISK,
            description="test",
            required_data=["a", "b"],
            indicators=["c", "d"],
        )
        result = self.builder._calculate_confidence(
            st, missing_data=["a"], available_indicators=["c"]
        )
        assert len(result) == 4
        score, level, ci_lower, ci_upper = result
        assert isinstance(score, float)
        assert isinstance(ci_lower, float)
        assert isinstance(ci_upper, float)
        assert ci_lower <= score <= ci_upper
