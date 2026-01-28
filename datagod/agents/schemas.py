"""
Agent Schemas (Phase 2: Agentic Core)

Pydantic models for agent task management, outputs, and actions.
These schemas ensure type safety and validation across the agent framework.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import uuid


class AgentPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfidenceLevel(str, Enum):
    """Confidence level categories."""
    VERY_LOW = "very_low"      # < 0.3
    LOW = "low"                 # 0.3 - 0.5
    MEDIUM = "medium"           # 0.5 - 0.7
    HIGH = "high"               # 0.7 - 0.9
    VERY_HIGH = "very_high"    # > 0.9


class AgentTask(BaseModel):
    """
    Represents a task assigned to an agent.
    
    Every agent interaction starts with an AgentTask that defines
    what needs to be done, who should do it, and when.
    """
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Task definition
    query: str = Field(..., description="The user's original query or task description")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for the task")
    
    # Routing
    assigned_agent: Optional[str] = Field(None, description="Which specialist agent should handle this")
    subtasks: List[str] = Field(default_factory=list, description="IDs of decomposed subtasks")
    parent_task_id: Optional[str] = Field(None, description="Parent task if this is a subtask")
    
    # Priority and timing
    priority: AgentPriority = Field(default=AgentPriority.MEDIUM)
    deadline: Optional[datetime] = Field(None, description="Optional deadline for completion")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Status tracking
    status: AgentStatus = Field(default=AgentStatus.PENDING)
    
    # User context
    user_id: Optional[int] = Field(None, description="User who initiated the task")
    session_id: Optional[str] = Field(None, description="Session for task grouping")
    
    class Config:
        use_enum_values = True


class EvidenceRef(BaseModel):
    """Reference to evidence supporting an agent's output."""
    ref_id: str = Field(..., description="Document or record ID")
    ref_type: str = Field(..., description="Type: document, record, api_response, etc.")
    source: str = Field(..., description="Source system or data source name")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    snippet: Optional[str] = Field(None, description="Relevant excerpt from the source")
    url: Optional[str] = Field(None, description="URL to source if applicable")


class AgentOutput(BaseModel):
    """
    Represents the output from an agent task.
    
    Every agent must produce an AgentOutput that includes:
    - The result data
    - Confidence level
    - Evidence references
    - Whether human approval is needed
    """
    task_id: str = Field(..., description="ID of the task this output is for")
    agent_id: str = Field(..., description="ID of the agent that produced this output")
    
    # Result
    result: Dict[str, Any] = Field(..., description="The structured output data")
    result_type: str = Field(..., description="Type of result: property_data, entity_match, risk_assessment, etc.")
    
    # Confidence and evidence
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    confidence_level: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    
    # Approval
    requires_approval: bool = Field(default=False, description="Whether human approval is needed")
    approval_reason: Optional[str] = Field(None, description="Why approval is required")
    approved_by: Optional[int] = Field(None, description="User ID who approved")
    approved_at: Optional[datetime] = Field(None)
    
    # Execution metadata
    execution_time_ms: Optional[float] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list)
    
    @validator('confidence_level', pre=True, always=True)
    def set_confidence_level(cls, v, values):
        """Auto-calculate confidence level from score."""
        confidence = values.get('confidence', 0.5)
        if confidence < 0.3:
            return ConfidenceLevel.VERY_LOW
        elif confidence < 0.5:
            return ConfidenceLevel.LOW
        elif confidence < 0.7:
            return ConfidenceLevel.MEDIUM
        elif confidence < 0.9:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.VERY_HIGH
    
    class Config:
        use_enum_values = True


class AgentAction(BaseModel):
    """
    Records an action taken by an agent for audit logging.
    
    Every action an agent takes is logged with full provenance
    for compliance and debugging.
    """
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = Field(..., description="Task this action belongs to")
    agent_id: str = Field(..., description="Agent that took the action")
    
    # Action details
    action: str = Field(..., description="Action type: query_database, call_api, calculate, etc.")
    action_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Inputs and outputs
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    
    # Results
    success: bool = Field(default=True)
    error: Optional[str] = Field(None)
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    duration_ms: Optional[float] = Field(None)
    
    # Approval tracking
    requires_approval: bool = Field(default=False)
    approved_by: Optional[int] = Field(None)
    
    class Config:
        use_enum_values = True


class ToolPermission(str, Enum):
    """Tool permission levels."""
    READ_ONLY = "read_only"       # Can only read data
    READ_WRITE = "read_write"     # Can read and modify data
    EXECUTE = "execute"           # Can execute actions
    ADMIN = "admin"               # Full access


class ToolDefinition(BaseModel):
    """
    Defines a tool available to agents.
    
    Tools are versioned, have explicit permissions, and are
    registered in the Tool Registry.
    """
    tool_id: str = Field(..., description="Unique tool identifier")
    name: str = Field(..., description="Human-readable tool name")
    description: str = Field(..., description="What the tool does")
    version: str = Field(default="1.0.0")
    
    # Permissions
    permission: ToolPermission = Field(default=ToolPermission.READ_ONLY)
    allowed_agents: List[str] = Field(default_factory=list, description="Which agents can use this tool")
    
    # Interface
    input_schema: Dict[str, Any] = Field(..., description="JSON schema for tool inputs")
    output_schema: Dict[str, Any] = Field(..., description="JSON schema for tool outputs")
    
    # Execution
    handler: Optional[str] = Field(None, description="Python path to handler function")
    timeout_seconds: int = Field(default=30)
    retryable: bool = Field(default=True)
    max_retries: int = Field(default=3)
    
    # Metadata
    category: str = Field(default="general")
    tags: List[str] = Field(default_factory=list)
    enabled: bool = Field(default=True)
    
    class Config:
        use_enum_values = True
