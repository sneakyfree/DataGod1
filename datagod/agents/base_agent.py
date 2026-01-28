"""
Base Specialist Agent (Phase 2.2: Specialist Agents)

Abstract base class for all specialist agents.
Provides common functionality for tool execution, evidence collection, and output generation.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from .schemas import (
    AgentTask, AgentOutput, AgentAction, EvidenceRef,
    ConfidenceLevel, AgentStatus
)
from .tool_registry import ToolRegistry, tool_registry
from .guardrails import GuardrailEngine, guardrail_engine

logger = logging.getLogger(__name__)


class BaseSpecialistAgent(ABC):
    """
    Abstract base class for specialist agents.
    
    All specialist agents inherit from this class and implement:
    - Their specific processing logic
    - Tool selection for their domain
    - Result formatting
    """
    
    # Subclasses must define these
    AGENT_ID: str = "base_specialist"
    AGENT_NAME: str = "Base Specialist Agent"
    DESCRIPTION: str = "Base class for specialist agents"
    CAPABILITIES: List[str] = []
    
    def __init__(
        self,
        tool_registry: ToolRegistry = None,
        guardrail_engine: GuardrailEngine = None
    ):
        self.tool_registry = tool_registry or globals()['tool_registry']
        self.guardrail_engine = guardrail_engine or globals()['guardrail_engine']
        self._action_log: List[AgentAction] = []
    
    @abstractmethod
    async def process(self, task: AgentTask) -> AgentOutput:
        """
        Process a task and return results.
        
        Subclasses must implement this method with their specific logic.
        """
        pass
    
    async def execute_tool(
        self,
        tool_id: str,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool and return the result.
        
        Handles errors and logging automatically.
        """
        try:
            result = await self.tool_registry.execute(
                tool_id=tool_id,
                agent_id=self.AGENT_ID,
                inputs=inputs
            )
            return result
        except Exception as e:
            logger.error(f"Tool {tool_id} failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_evidence_ref(
        self,
        source: str,
        ref_type: str = "tool_output",
        snippet: str = None,
        url: str = None
    ) -> EvidenceRef:
        """Create an evidence reference for audit trail."""
        return EvidenceRef(
            ref_id=str(uuid.uuid4()),
            ref_type=ref_type,
            source=source,
            snippet=snippet[:200] if snippet else None,
            url=url
        )
    
    def create_output(
        self,
        task: AgentTask,
        result: Dict[str, Any],
        result_type: str,
        confidence: float,
        evidence_refs: List[EvidenceRef] = None,
        warnings: List[str] = None,
        error: str = None
    ) -> AgentOutput:
        """Create a standardized agent output."""
        return AgentOutput(
            task_id=task.task_id,
            agent_id=self.AGENT_ID,
            result=result,
            result_type=result_type,
            confidence=confidence,
            evidence_refs=evidence_refs or [],
            warnings=warnings or [],
            error=error
        )
    
    def log_action(
        self,
        task_id: str,
        action: str,
        inputs: Dict[str, Any] = None,
        outputs: Dict[str, Any] = None,
        success: bool = True,
        error: str = None
    ) -> AgentAction:
        """Log an action for audit trail."""
        action_record = AgentAction(
            task_id=task_id,
            agent_id=self.AGENT_ID,
            action=action,
            inputs=inputs or {},
            outputs=outputs or {},
            success=success,
            error=error,
            completed_at=datetime.utcnow()
        )
        self._action_log.append(action_record)
        return action_record
    
    def get_actions(self, task_id: Optional[str] = None) -> List[AgentAction]:
        """Get logged actions, optionally filtered by task."""
        if task_id:
            return [a for a in self._action_log if a.task_id == task_id]
        return self._action_log.copy()
