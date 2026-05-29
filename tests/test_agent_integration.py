"""
Agent Integration Tests (Phase 6.1)

End-to-end tests for agent-scraper integration.
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestScraperToolsAdapter:
    """Tests for the scraper tools adapter."""

    def test_adapter_initialization(self):
        """Test adapter can be initialized."""
        from datagod.agents.scraper_tools import ScraperToolsAdapter

        adapter = ScraperToolsAdapter()
        assert adapter is not None

    def test_register_all_tools(self):
        """Test all tools are registered."""
        from datagod.agents.scraper_tools import ScraperToolsAdapter
        from datagod.agents.tool_registry import ToolRegistry

        registry = ToolRegistry()
        adapter = ScraperToolsAdapter()
        adapter.register_all_tools()

        # Check tools are in global registry
        from datagod.agents.tool_registry import tool_registry

        tools = tool_registry.list_tools()
        tool_ids = [t.tool_id for t in tools]

        assert "property_search_real" in tool_ids
        assert "lien_search_real" in tool_ids
        assert "entity_search_real" in tool_ids

    @pytest.mark.asyncio
    async def test_property_search_mock(self):
        """Test property search with mock data."""
        from datagod.agents.scraper_tools import ScraperToolsAdapter

        adapter = ScraperToolsAdapter()
        result = await adapter.property_search(address="123 Main St", state="IL")

        assert "properties" in result
        assert result["count"] >= 0
        assert "source" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_lien_search_mock(self):
        """Test lien search with mock data."""
        from datagod.agents.scraper_tools import ScraperToolsAdapter

        adapter = ScraperToolsAdapter()
        result = await adapter.lien_search(parcel_id="123-456-789", state="IL")

        assert "liens" in result
        assert "total_amount" in result
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_entity_search_mock(self):
        """Test entity search with mock data."""
        from datagod.agents.scraper_tools import ScraperToolsAdapter

        adapter = ScraperToolsAdapter()
        result = await adapter.entity_search(name="John Doe", entity_type="person")

        assert "entities" in result
        assert result["count"] >= 0


class TestAgentScraperIntegration:
    """Tests for agent-to-scraper integration."""

    @pytest.mark.asyncio
    async def test_property_agent_uses_scraper(self):
        """Test PropertyResearchAgent can use scraper tools."""
        from datagod.agents.schemas import AgentTask
        from datagod.agents.scraper_tools import register_scraper_tools
        from datagod.agents.specialists import PropertyResearchAgent

        # Register scraper tools
        register_scraper_tools()

        agent = PropertyResearchAgent()
        task = AgentTask(
            query="Find property at 123 Main St, Chicago, IL",
            context={"state": "IL", "city": "Chicago"},
        )

        result = await agent.process(task)

        assert result is not None
        assert result.task_id == task.task_id
        assert result.agent_id == "property_research"
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_lien_agent_uses_scraper(self):
        """Test LienPriorityAgent can use scraper tools."""
        from datagod.agents.schemas import AgentTask
        from datagod.agents.scraper_tools import register_scraper_tools
        from datagod.agents.specialists import LienPriorityAgent

        register_scraper_tools()

        agent = LienPriorityAgent()
        task = AgentTask(
            query="Find all liens on parcel 123-456-789",
            context={"parcel_id": "123-456-789", "state": "IL"},
        )

        result = await agent.process(task)

        assert result is not None
        assert result.agent_id == "lien_priority"

    @pytest.mark.asyncio
    async def test_orchestrator_routes_to_specialists(self):
        """Test OrchestratorAgent correctly routes to specialists."""
        from datagod.agents.orchestrator import OrchestratorAgent
        from datagod.agents.scraper_tools import register_scraper_tools

        register_scraper_tools()

        orchestrator = OrchestratorAgent()

        result = await orchestrator.process_query(
            query="Find liens on 123 Main St and assess risk",
            context={"state": "IL"},
            user_id=1,
        )

        assert result is not None
        assert "result" in result or hasattr(result, "result")


class TestIntelligenceIntegration:
    """Tests for intelligence layer integration."""

    @pytest.mark.asyncio
    async def test_scenario_builder_with_real_data(self):
        """Test ScenarioUniverseBuilder with real-ish data."""
        from datagod.intelligence import ScenarioUniverseBuilder

        builder = ScenarioUniverseBuilder()

        scenarios = await builder.analyze(
            property_data={
                "address": "123 Main St",
                "property_type": "single_family",
                "tax_delinquent": True,
                "vacant": True,
            },
            lien_data={
                "liens": [
                    {"type": "property_tax", "amount": 5000},
                    {"type": "mortgage", "amount": 200000},
                ]
            },
        )

        assert len(scenarios) > 0
        # Should identify distress scenarios
        scenario_ids = [s.scenario_id for s in scenarios]
        # With tax delinquent and vacant, should find distress signals

    def test_blocker_engine_with_real_data(self):
        """Test BlockerUnlockerEngine with real-ish data."""
        from datagod.intelligence import BlockerUnlockerEngine

        engine = BlockerUnlockerEngine()

        blockers, unlockers = engine.analyze(
            property_data={
                "address": "123 Main St",
                "tax_delinquent": True,
                "estimated_value": 300000,
            },
            lien_data={
                "liens": [
                    {"type": "property_tax", "amount": 5000, "id": "1"},
                    {"type": "judgment", "amount": 15000, "id": "2"},
                ]
            },
        )

        assert len(blockers) > 0
        # Should have tax lien blocker
        blocker_types = [b.blocker_type for b in blockers]


class TestUXIntegration:
    """Tests for UX components integration."""

    def test_intake_wizard_session(self):
        """Test intake wizard session flow."""
        from datagod.ux import GuidedIntakeWizard

        wizard = GuidedIntakeWizard()

        # Start session
        session = wizard.start_session("property_research")
        assert "session_id" in session
        assert session["current_stage"] == 1
        assert len(session["fields"]) > 0

        # Submit first stage
        result = wizard.submit_stage(
            session["session_id"],
            {
                "property_address": "123 Main St, Chicago, IL",
                "property_type": "single_family",
            },
        )

        assert "validations" in result
        # May have next stage

    def test_report_generator_all_views(self):
        """Test report generator produces all views."""
        from datagod.ux import MultiViewReportGenerator, ReportView

        generator = MultiViewReportGenerator()

        data = {
            "property": {"address": "123 Main St"},
            "liens": {"liens": [{"type": "mortgage", "amount": 200000}]},
            "risk_assessment": {"risk_score": {"overall": 0.3, "category": "low"}},
        }

        reports = generator.generate_all_views(data, title="Test Report")

        assert ReportView.CONSUMER in reports
        assert ReportView.OPERATOR in reports
        assert ReportView.ANALYST in reports
        assert ReportView.AUDIT in reports

        # Audit view should have metadata
        audit = reports[ReportView.AUDIT]
        assert "metadata" in audit


class TestSecurityIntegration:
    """Tests for security integration."""

    def test_rate_limiter(self):
        """Test rate limiter works."""
        from datagod.security import RateLimitConfig, RateLimiter

        config = RateLimitConfig(requests_per_minute=5, burst_limit=2)
        limiter = RateLimiter(config)

        # First requests should be allowed
        for i in range(2):
            result = limiter.check(f"user_1")
            assert result["allowed"] == True

        # Burst limit should kick in
        result = limiter.check("user_1")
        assert result["allowed"] == False

    def test_pii_redaction(self):
        """Test PII redaction works."""
        from datagod.security import PIIRedactor

        redactor = PIIRedactor()

        text = "Contact John at 555-123-4567 or john@email.com"
        redacted = redactor.redact(text)

        assert "555-123-4567" not in redacted
        assert "john@email.com" not in redacted


class TestPerformanceIntegration:
    """Tests for performance utilities integration."""

    def test_cache_manager(self):
        """Test cache manager works."""
        from datagod.performance import CacheManager

        cache = CacheManager(max_size=10, default_ttl=60)

        # Set and get
        cache.set("test_key", {"data": "value"})
        result = cache.get("test_key")

        assert result == {"data": "value"}

        # Stats
        stats = cache.get_stats()
        assert stats["hits"] == 1

    @pytest.mark.asyncio
    async def test_batch_processor(self):
        """Test batch processor works."""
        from datagod.performance import AsyncBatchProcessor

        processor = AsyncBatchProcessor(batch_size=3, max_concurrent=2)

        async def double(x):
            return x * 2

        items = [1, 2, 3, 4, 5]
        result = await processor.process(items, double)

        assert result.success_count == 5
        assert result.failure_count == 0
        assert result.successful == [2, 4, 6, 8, 10]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
