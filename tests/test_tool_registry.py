"""
Tests for Tool Registry — coverage target for agents/tool_registry.py (69% → 85%+)
"""

import pytest
from datagod.agents.tool_registry import (
    ToolRegistry,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
    tool_registry,
    register_tool,
)
from datagod.agents.schemas import ToolPermission


class TestToolRegistryInit:
    def test_creates_empty_registry(self):
        reg = ToolRegistry()
        assert reg is not None

    def test_global_registry_exists(self):
        assert tool_registry is not None


class TestToolRegistration:
    def setup_method(self):
        self.reg = ToolRegistry()

    def test_register_tool(self):
        self.reg.register(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            handler=lambda **kw: {"result": "ok"},
            input_schema={"query": "string"},
            output_schema={"result": "string"},
        )
        tool = self.reg.get_tool("test_tool")
        assert tool is not None
        assert tool.tool_id == "test_tool"

    def test_register_with_permissions(self):
        self.reg.register(
            tool_id="admin_tool",
            name="Admin Tool",
            description="Admin only",
            handler=lambda **kw: {},
            input_schema={},
            output_schema={},
            permission=ToolPermission.ADMIN,
        )
        tool = self.reg.get_tool("admin_tool")
        assert tool.permission == ToolPermission.ADMIN

    def test_register_with_allowed_agents(self):
        self.reg.register(
            tool_id="restricted_tool",
            name="Restricted",
            description="Only for specific agents",
            handler=lambda **kw: {},
            input_schema={},
            output_schema={},
            allowed_agents=["property_research"],
        )
        assert self.reg.can_use("restricted_tool", "property_research")

    def test_unregister(self):
        self.reg.register(
            tool_id="temp_tool",
            name="Temp",
            description="Will be removed",
            handler=lambda **kw: {},
            input_schema={},
            output_schema={},
        )
        assert self.reg.get_tool("temp_tool") is not None
        self.reg.unregister("temp_tool")
        assert self.reg.get_tool("temp_tool") is None

    def test_unregister_nonexistent(self):
        # Should not raise
        self.reg.unregister("ghost_tool")


class TestToolListing:
    def setup_method(self):
        self.reg = ToolRegistry()
        self.reg.register(
            tool_id="tool_a", name="A", description="Alpha",
            handler=lambda **kw: {}, input_schema={}, output_schema={},
            permission=ToolPermission.READ_ONLY,
        )
        self.reg.register(
            tool_id="tool_b", name="B", description="Beta",
            handler=lambda **kw: {}, input_schema={}, output_schema={},
            permission=ToolPermission.READ_WRITE,
        )

    def test_list_all(self):
        tools = self.reg.list_tools()
        assert len(tools) >= 2

    def test_list_by_permission(self):
        read_only = self.reg.list_tools(permission=ToolPermission.READ_ONLY)
        assert all(t.permission == ToolPermission.READ_ONLY for t in read_only)


class TestToolExecution:
    def setup_method(self):
        self.reg = ToolRegistry()

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        async def handler(**kw):
            return {"success": True, "data": kw.get("query", "none")}

        self.reg.register(
            tool_id="search_tool", name="Search", description="Searches",
            handler=handler, input_schema={"query": "string"},
            output_schema={"success": "bool"},
        )
        result = await self.reg.execute("search_tool", "orchestrator", {"query": "test"})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent(self):
        with pytest.raises((ToolNotFoundError, KeyError)):
            await self.reg.execute("nonexistent", "orchestrator", {})

    def test_get_stats(self):
        stats = self.reg.get_stats()
        assert isinstance(stats, dict)


class TestDefaultTools:
    def test_initialize_default_tools(self):
        reg = ToolRegistry()
        reg.initialize_default_tools()
        tools = reg.list_tools()
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_placeholder_handler(self):
        result = await ToolRegistry._placeholder_handler(query="test")
        assert isinstance(result, dict)


class TestRegisterToolDecorator:
    def test_decorator(self):
        @register_tool(
            tool_id="decorated_tool",
            name="Decorated Tool",
            description="Created via decorator",
            input_schema={"x": "int"},
            output_schema={"result": "int"},
        )
        async def my_handler(**inputs):
            return {"result": inputs.get("x", 0) * 2}

        # The decorator should have registered the tool in the global registry
        tool = tool_registry.get_tool("decorated_tool")
        assert tool is not None
