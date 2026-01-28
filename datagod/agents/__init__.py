"""
DataGod Agents Package

Provides the agentic research assistant framework with:
- Orchestrator Agent for task decomposition and routing
- Specialist Agents for domain-specific tasks
- Tool Registry for capability management
- Guardrail Engine for hallucination prevention
- Scraper Tools for real data integration
"""

from .schemas import AgentTask, AgentOutput, AgentAction, ToolDefinition
from .orchestrator import OrchestratorAgent
from .tool_registry import ToolRegistry, tool_registry, register_tool
from .guardrails import GuardrailEngine, guardrail_engine
from .base_agent import BaseSpecialistAgent
from .specialists import (
    PropertyResearchAgent,
    EntityResolutionAgent,
    LienPriorityAgent,
    RiskAssessmentAgent,
    ComplianceCheckAgent
)
from .scraper_tools import ScraperToolsAdapter, register_scraper_tools

__all__ = [
    # Schemas
    'AgentTask',
    'AgentOutput',
    'AgentAction',
    'ToolDefinition',
    # Orchestrator
    'OrchestratorAgent',
    # Tool Registry
    'ToolRegistry',
    'tool_registry',
    'register_tool',
    # Guardrails
    'GuardrailEngine',
    'guardrail_engine',
    # Base Agent
    'BaseSpecialistAgent',
    # Specialist Agents
    'PropertyResearchAgent',
    'EntityResolutionAgent',
    'LienPriorityAgent',
    'RiskAssessmentAgent',
    'ComplianceCheckAgent',
    # Scraper Tools
    'ScraperToolsAdapter',
    'register_scraper_tools',
]
