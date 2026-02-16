"""
Tests for agents/schemas.py and agents/base_agent.py — coverage boost for agent framework
"""

import pytest
from datetime import datetime

from datagod.agents.schemas import (
    AgentPriority,
    AgentStatus,
    ConfidenceLevel,
    AgentTask,
    EvidenceRef,
    AgentOutput,
    AgentAction,
    ToolPermission,
    ToolDefinition,
)


# ============================================================
# Enum Tests
# ============================================================

class TestAgentPriority:
    def test_values(self):
        assert AgentPriority.LOW.value == "low"
        assert AgentPriority.MEDIUM.value == "medium"
        assert AgentPriority.HIGH.value == "high"
        assert AgentPriority.CRITICAL.value == "critical"


class TestAgentStatus:
    def test_values(self):
        assert AgentStatus.PENDING.value == "pending"
        assert AgentStatus.IN_PROGRESS.value == "in_progress"
        assert AgentStatus.AWAITING_APPROVAL.value == "awaiting_approval"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.CANCELLED.value == "cancelled"


class TestConfidenceLevel:
    def test_values(self):
        assert ConfidenceLevel.VERY_LOW.value == "very_low"
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.VERY_HIGH.value == "very_high"


class TestToolPermission:
    def test_values(self):
        assert ToolPermission.READ_ONLY.value == "read_only"
        assert ToolPermission.READ_WRITE.value == "read_write"
        assert ToolPermission.EXECUTE.value == "execute"
        assert ToolPermission.ADMIN.value == "admin"


# ============================================================
# Model Tests
# ============================================================

class TestAgentTask:
    def test_create_minimal(self):
        task = AgentTask(query="Find property records for 123 Main St")
        assert task.query == "Find property records for 123 Main St"
        assert task.task_id is not None
        assert task.status == AgentStatus.PENDING.value

    def test_create_full(self):
        task = AgentTask(
            query="Search liens",
            assigned_agent="lien_specialist",
            priority=AgentPriority.HIGH,
            user_id=42,
            context={"parcel_id": "APN-123"}
        )
        assert task.assigned_agent == "lien_specialist"
        assert task.priority == AgentPriority.HIGH.value
        assert task.user_id == 42
        assert task.context["parcel_id"] == "APN-123"

    def test_defaults(self):
        task = AgentTask(query="test")
        assert task.subtasks == []
        assert task.parent_task_id is None
        assert task.deadline is None
        assert task.session_id is None


class TestEvidenceRef:
    def test_create(self):
        ref = EvidenceRef(
            ref_id="doc_001",
            ref_type="document",
            source="county_records"
        )
        assert ref.ref_id == "doc_001"
        assert ref.ref_type == "document"
        assert ref.source == "county_records"
        assert ref.timestamp is not None

    def test_with_snippet(self):
        ref = EvidenceRef(
            ref_id="api_001",
            ref_type="api_response",
            source="property_api",
            snippet="Owner: John Smith",
            url="https://api.example.com/property/123"
        )
        assert ref.snippet == "Owner: John Smith"
        assert ref.url == "https://api.example.com/property/123"


class TestAgentOutput:
    def test_create(self):
        output = AgentOutput(
            task_id="task_001",
            agent_id="property_specialist",
            result={"owner": "John Smith", "liens": 3},
            result_type="property_data",
            confidence=0.85
        )
        assert output.task_id == "task_001"
        assert output.agent_id == "property_specialist"
        assert output.confidence == 0.85

    def test_confidence_level_very_low(self):
        output = AgentOutput(
            task_id="t1", agent_id="a1",
            result={}, result_type="test",
            confidence=0.2
        )
        assert output.confidence_level == ConfidenceLevel.VERY_LOW.value

    def test_confidence_level_low(self):
        output = AgentOutput(
            task_id="t1", agent_id="a1",
            result={}, result_type="test",
            confidence=0.4
        )
        assert output.confidence_level == ConfidenceLevel.LOW.value

    def test_confidence_level_medium(self):
        output = AgentOutput(
            task_id="t1", agent_id="a1",
            result={}, result_type="test",
            confidence=0.6
        )
        assert output.confidence_level == ConfidenceLevel.MEDIUM.value

    def test_confidence_level_high(self):
        output = AgentOutput(
            task_id="t1", agent_id="a1",
            result={}, result_type="test",
            confidence=0.8
        )
        assert output.confidence_level == ConfidenceLevel.HIGH.value

    def test_confidence_level_very_high(self):
        output = AgentOutput(
            task_id="t1", agent_id="a1",
            result={}, result_type="test",
            confidence=0.95
        )
        assert output.confidence_level == ConfidenceLevel.VERY_HIGH.value

    def test_with_evidence(self):
        evidence = EvidenceRef(
            ref_id="e1", ref_type="doc", source="clerk"
        )
        output = AgentOutput(
            task_id="t1", agent_id="a1",
            result={"found": True}, result_type="search",
            confidence=0.9,
            evidence_refs=[evidence]
        )
        assert len(output.evidence_refs) == 1

    def test_with_warnings(self):
        output = AgentOutput(
            task_id="t1", agent_id="a1",
            result={}, result_type="test",
            confidence=0.5,
            warnings=["Partial data", "Stale cache"]
        )
        assert len(output.warnings) == 2


class TestAgentAction:
    def test_create(self):
        action = AgentAction(
            task_id="task_001",
            agent_id="lien_agent",
            action="query_database"
        )
        assert action.task_id == "task_001"
        assert action.agent_id == "lien_agent"
        assert action.action == "query_database"
        assert action.success is True

    def test_failed_action(self):
        action = AgentAction(
            task_id="task_001",
            agent_id="lien_agent",
            action="call_api",
            success=False,
            error="Timeout"
        )
        assert action.success is False
        assert action.error == "Timeout"


class TestToolDefinition:
    def test_create(self):
        tool = ToolDefinition(
            tool_id="property_search",
            name="Property Search",
            description="Search property records",
            input_schema={"type": "object", "properties": {"address": {"type": "string"}}},
            output_schema={"type": "object"}
        )
        assert tool.tool_id == "property_search"
        assert tool.enabled is True
        assert tool.timeout_seconds == 30
        assert tool.retryable is True
        assert tool.max_retries == 3

    def test_with_permissions(self):
        tool = ToolDefinition(
            tool_id="db_write",
            name="DB Write",
            description="Write to database",
            permission=ToolPermission.READ_WRITE,
            allowed_agents=["admin_agent"],
            input_schema={},
            output_schema={}
        )
        assert tool.permission == ToolPermission.READ_WRITE.value
        assert "admin_agent" in tool.allowed_agents
