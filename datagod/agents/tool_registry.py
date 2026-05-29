"""
Tool Registry (Phase 2: Agentic Core)

Manages the catalog of tools available to agents.
Provides versioning, permissions, and execution control.
"""

import asyncio
import logging
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from .schemas import ToolDefinition, ToolPermission

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when a tool execution fails."""

    pass


class ToolNotFoundError(Exception):
    """Raised when a requested tool doesn't exist."""

    pass


class ToolPermissionError(Exception):
    """Raised when an agent lacks permission to use a tool."""

    pass


class ToolRegistry:
    """
    Central registry for all tools available to agents.

    Features:
    - Versioned tool catalog
    - Permission-based access control
    - Execution with timeout and retry
    - Usage metrics and logging
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}
        self._usage_stats: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def register(
        self,
        tool_id: str,
        name: str,
        description: str,
        handler: Callable,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        permission: ToolPermission = ToolPermission.READ_ONLY,
        allowed_agents: Optional[List[str]] = None,
        **kwargs,
    ) -> ToolDefinition:
        """
        Register a new tool in the registry.

        Args:
            tool_id: Unique identifier for the tool
            name: Human-readable name
            description: What the tool does
            handler: The callable that executes the tool
            input_schema: JSON schema for inputs
            output_schema: JSON schema for outputs
            permission: Permission level required
            allowed_agents: List of agent IDs that can use this tool (None = all)
            **kwargs: Additional ToolDefinition fields

        Returns:
            The registered ToolDefinition
        """
        if tool_id in self._tools:
            logger.warning(f"Overwriting existing tool: {tool_id}")

        tool = ToolDefinition(
            tool_id=tool_id,
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            permission=permission,
            allowed_agents=allowed_agents or [],
            **kwargs,
        )

        self._tools[tool_id] = tool
        self._handlers[tool_id] = handler
        self._usage_stats[tool_id] = {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "total_duration_ms": 0,
            "last_used": None,
        }

        logger.info(f"Registered tool: {tool_id} ({name})")
        return tool

    def unregister(self, tool_id: str) -> bool:
        """Remove a tool from the registry."""
        if tool_id in self._tools:
            del self._tools[tool_id]
            del self._handlers[tool_id]
            logger.info(f"Unregistered tool: {tool_id}")
            return True
        return False

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get a tool definition by ID."""
        return self._tools.get(tool_id)

    def list_tools(
        self,
        category: Optional[str] = None,
        permission: Optional[ToolPermission] = None,
        agent_id: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[ToolDefinition]:
        """
        List tools matching the given criteria.

        Args:
            category: Filter by category
            permission: Filter by permission level
            agent_id: Filter by agent access
            enabled_only: Only return enabled tools

        Returns:
            List of matching ToolDefinitions
        """
        tools = list(self._tools.values())

        if enabled_only:
            tools = [t for t in tools if t.enabled]

        if category:
            tools = [t for t in tools if t.category == category]

        if permission:
            tools = [t for t in tools if t.permission == permission]

        if agent_id:
            tools = [
                t for t in tools if not t.allowed_agents or agent_id in t.allowed_agents
            ]

        return tools

    def can_use(self, tool_id: str, agent_id: str) -> bool:
        """Check if an agent can use a specific tool."""
        tool = self._tools.get(tool_id)
        if not tool:
            return False
        if not tool.enabled:
            return False
        if not tool.allowed_agents:
            return True  # No restrictions
        return agent_id in tool.allowed_agents

    async def execute(
        self, tool_id: str, agent_id: str, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool with the given inputs.

        Args:
            tool_id: The tool to execute
            agent_id: The agent requesting execution
            inputs: Input parameters

        Returns:
            Tool output

        Raises:
            ToolNotFoundError: Tool doesn't exist
            ToolPermissionError: Agent can't use this tool
            ToolExecutionError: Execution failed
        """
        tool = self._tools.get(tool_id)
        if not tool:
            raise ToolNotFoundError(f"Tool not found: {tool_id}")

        if not self.can_use(tool_id, agent_id):
            raise ToolPermissionError(f"Agent {agent_id} cannot use tool {tool_id}")

        handler = self._handlers.get(tool_id)
        if not handler:
            raise ToolExecutionError(f"No handler for tool: {tool_id}")

        # Track execution
        start_time = datetime.utcnow()
        self._usage_stats[tool_id]["calls"] += 1

        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**inputs), timeout=tool.timeout_seconds
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: handler(**inputs)
                    ),
                    timeout=tool.timeout_seconds,
                )

            # Update stats
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._usage_stats[tool_id]["successes"] += 1
            self._usage_stats[tool_id]["total_duration_ms"] += duration_ms
            self._usage_stats[tool_id]["last_used"] = datetime.utcnow()

            logger.info(f"Tool {tool_id} executed successfully ({duration_ms:.2f}ms)")

            return {"success": True, "data": result, "duration_ms": duration_ms}

        except asyncio.TimeoutError:
            self._usage_stats[tool_id]["failures"] += 1
            error_msg = f"Tool {tool_id} timed out after {tool.timeout_seconds}s"
            logger.error(error_msg)
            raise ToolExecutionError(error_msg)

        except Exception as e:
            self._usage_stats[tool_id]["failures"] += 1
            error_msg = f"Tool {tool_id} failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise ToolExecutionError(error_msg)

    def get_stats(self, tool_id: Optional[str] = None) -> Dict[str, Any]:
        """Get usage statistics for tools."""
        if tool_id:
            return self._usage_stats.get(tool_id, {})
        return self._usage_stats

    def initialize_default_tools(self):
        """Register the default set of DataGod tools."""
        if self._initialized:
            return

        # Property Search Tool
        self.register(
            tool_id="property_search",
            name="Property Search",
            description="Search for properties by address, parcel ID, or owner name",
            handler=self._placeholder_handler,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "query_type": {
                        "type": "string",
                        "enum": ["address", "parcel", "owner"],
                    },
                    "jurisdiction": {"type": "string"},
                },
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "total_count": {"type": "integer"},
                },
            },
            permission=ToolPermission.READ_ONLY,
            category="property",
        )

        # Entity Search Tool
        self.register(
            tool_id="entity_search",
            name="Entity Search",
            description="Search for entities (people, companies) across records",
            handler=self._placeholder_handler,
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "entity_type": {
                        "type": "string",
                        "enum": ["person", "company", "any"],
                    },
                },
                "required": ["name"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "entities": {"type": "array"},
                    "match_confidence": {"type": "number"},
                },
            },
            permission=ToolPermission.READ_ONLY,
            category="entity",
        )

        # Lien Search Tool
        self.register(
            tool_id="lien_search",
            name="Lien Search",
            description="Search for liens, encumbrances, and judgments on a property",
            handler=self._placeholder_handler,
            input_schema={
                "type": "object",
                "properties": {
                    "property_id": {"type": "string"},
                    "lien_types": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["property_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "liens": {"type": "array"},
                    "total_amount": {"type": "number"},
                },
            },
            permission=ToolPermission.READ_ONLY,
            category="property",
        )

        # Record Lookup Tool
        self.register(
            tool_id="record_lookup",
            name="Record Lookup",
            description="Get detailed information about a specific record",
            handler=self._placeholder_handler,
            input_schema={
                "type": "object",
                "properties": {
                    "record_id": {"type": "string"},
                },
                "required": ["record_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "record": {"type": "object"},
                    "provenance": {"type": "object"},
                },
            },
            permission=ToolPermission.READ_ONLY,
            category="records",
        )

        # Database Query Tool
        self.register(
            tool_id="database_query",
            name="Database Query",
            description="Execute a structured query against the database",
            handler=self._placeholder_handler,
            input_schema={
                "type": "object",
                "properties": {
                    "table": {"type": "string"},
                    "filters": {"type": "object"},
                    "limit": {"type": "integer", "default": 100},
                },
                "required": ["table"],
            },
            output_schema={
                "type": "object",
                "properties": {"rows": {"type": "array"}, "count": {"type": "integer"}},
            },
            permission=ToolPermission.READ_ONLY,
            category="database",
            allowed_agents=["orchestrator", "property_research", "entity_resolution"],
        )

        self._initialized = True
        logger.info(f"Initialized {len(self._tools)} default tools")

    @staticmethod
    async def _placeholder_handler(**kwargs) -> Dict[str, Any]:
        """Placeholder handler for tools not yet implemented."""
        return {
            "status": "placeholder",
            "message": "Tool handler not yet implemented",
            "inputs": kwargs,
        }


# Global tool registry instance
tool_registry = ToolRegistry()


def register_tool(
    tool_id: str,
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    output_schema: Dict[str, Any],
    **kwargs,
):
    """
    Decorator to register a function as a tool.

    Usage:
        @register_tool(
            tool_id="my_tool",
            name="My Tool",
            description="Does something useful",
            input_schema={"type": "object", "properties": {...}},
            output_schema={"type": "object", "properties": {...}}
        )
        async def my_tool_handler(**inputs):
            ...
    """

    def decorator(func):
        tool_registry.register(
            tool_id=tool_id,
            name=name,
            description=description,
            handler=func,
            input_schema=input_schema,
            output_schema=output_schema,
            **kwargs,
        )
        return func

    return decorator
