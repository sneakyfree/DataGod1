"""
DataGod Agents Package

Provides the agentic research assistant framework with:
- Orchestrator Agent for task decomposition and routing
- Specialist Agents for domain-specific tasks
- Tool Registry for capability management
- Guardrail Engine for hallucination prevention
- Scraper Tools for real data integration
"""

from .base_agent import BaseSpecialistAgent
from .guardrails import GuardrailEngine, guardrail_engine
from .orchestrator import OrchestratorAgent
from .schemas import AgentAction, AgentOutput, AgentTask, ToolDefinition
from .scraper_tools import ScraperToolsAdapter, register_scraper_tools
from .specialists import (
    ComplianceCheckAgent,
    EntityResolutionAgent,
    LienPriorityAgent,
    PropertyResearchAgent,
    RiskAssessmentAgent,
)
from .tool_registry import ToolRegistry, register_tool, tool_registry

__all__ = [
    # Schemas
    "AgentTask",
    "AgentOutput",
    "AgentAction",
    "ToolDefinition",
    # Orchestrator
    "OrchestratorAgent",
    # Tool Registry
    "ToolRegistry",
    "tool_registry",
    "register_tool",
    # Guardrails
    "GuardrailEngine",
    "guardrail_engine",
    # Base Agent
    "BaseSpecialistAgent",
    # Specialist Agents
    "PropertyResearchAgent",
    "EntityResolutionAgent",
    "LienPriorityAgent",
    "RiskAssessmentAgent",
    "ComplianceCheckAgent",
    # Scraper Tools
    "ScraperToolsAdapter",
    "register_scraper_tools",
]
