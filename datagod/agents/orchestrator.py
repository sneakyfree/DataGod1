"""
Orchestrator Agent (Phase 2: Agentic Core)

Central coordinator for all agent tasks.
Handles task decomposition, agent routing, result synthesis, and confidence assessment.
"""

import asyncio
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .guardrails import GuardrailEngine, guardrail_engine
from .schemas import (
    AgentAction,
    AgentOutput,
    AgentPriority,
    AgentStatus,
    AgentTask,
    ConfidenceLevel,
    EvidenceRef,
)
from .tool_registry import ToolRegistry, tool_registry

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Central orchestrator for the DataGod agent system.

    Responsibilities:
    - Task decomposition: Break complex queries into subtasks
    - Agent routing: Assign subtasks to specialist agents
    - Result synthesis: Combine specialist outputs into coherent response
    - Confidence assessment: Aggregate confidence and evidence
    - Human approval gates: Escalate low-confidence decisions
    """

    AGENT_ID = "orchestrator"

    # Specialist agent registry
    SPECIALIST_AGENTS = {
        "property_research": {
            "name": "Property Research Agent",
            "description": "Searches and analyzes property records",
            "capabilities": ["property_search", "lien_search", "ownership_chain"],
            "priority_keywords": ["property", "address", "parcel", "deed", "mortgage"],
        },
        "entity_resolution": {
            "name": "Entity Resolution Agent",
            "description": "Matches and disambiguates entities across records",
            "capabilities": ["entity_search", "name_matching", "relationship_mapping"],
            "priority_keywords": ["owner", "person", "company", "entity", "who"],
        },
        "lien_priority": {
            "name": "Lien Priority Agent",
            "description": "Calculates lien priority and encumbrance stacks",
            "capabilities": [
                "lien_priority",
                "amount_calculation",
                "clearance_analysis",
            ],
            "priority_keywords": [
                "lien",
                "priority",
                "encumbrance",
                "judgment",
                "clear",
            ],
        },
        "risk_assessment": {
            "name": "Risk Assessment Agent",
            "description": "Identifies and scores documented risks",
            "capabilities": ["risk_scoring", "red_flag_detection", "distress_signals"],
            "priority_keywords": [
                "risk",
                "red flag",
                "distress",
                "foreclosure",
                "delinquent",
            ],
        },
        "compliance_check": {
            "name": "Compliance Check Agent",
            "description": "Validates against configured rules and regulations",
            "capabilities": [
                "rule_checking",
                "regulation_validation",
                "audit_preparation",
            ],
            "priority_keywords": ["compliance", "regulation", "rule", "audit", "valid"],
        },
    }

    def __init__(
        self,
        tool_registry: ToolRegistry = None,
        guardrail_engine: GuardrailEngine = None,
    ):
        self.tool_registry = tool_registry or globals()["tool_registry"]
        self.guardrail_engine = guardrail_engine or globals()["guardrail_engine"]

        # Task tracking (in-memory for fast access)
        self._active_tasks: Dict[str, AgentTask] = {}
        self._task_outputs: Dict[str, List[AgentOutput]] = {}
        self._action_log: List[AgentAction] = []

        # HITL persistence (SQLite for durability)
        self._hitl_db = os.environ.get(
            "HITL_DB",
            os.path.join(os.path.dirname(__file__), "..", "..", "hitl_queue.db"),
        )
        self._init_hitl_db()

        # Initialize tool registry
        self.tool_registry.initialize_default_tools()

    def _init_hitl_db(self):
        """Initialize the HITL persistence database."""
        try:
            conn = sqlite3.connect(self._hitl_db)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hitl_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    inputs TEXT DEFAULT '{}',
                    outputs TEXT DEFAULT '{}',
                    success INTEGER DEFAULT 1,
                    error TEXT,
                    created_at TEXT NOT NULL
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hitl_approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    approved INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    approval_reason TEXT,
                    decided_at TEXT NOT NULL
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_actions_task
                ON hitl_actions(task_id)
            """
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"HITL DB init failed (will use in-memory only): {e}")
            self._hitl_db = None

    def _persist_action(self, action_record: "AgentAction"):
        """Persist an action to the HITL database."""
        if not self._hitl_db:
            return
        try:
            conn = sqlite3.connect(self._hitl_db)
            conn.execute(
                "INSERT INTO hitl_actions (task_id, agent_id, action, inputs, outputs, success, error, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    action_record.task_id,
                    action_record.agent_id,
                    action_record.action,
                    json.dumps(action_record.inputs, default=str),
                    json.dumps(action_record.outputs, default=str),
                    1 if action_record.success else 0,
                    action_record.error,
                    (
                        action_record.completed_at.isoformat()
                        if action_record.completed_at
                        else datetime.utcnow().isoformat()
                    ),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to persist action: {e}")

    def _persist_approval(
        self, task_id: str, approved: bool, user_id: int, reason: str = None
    ):
        """Persist an approval decision to the HITL database."""
        if not self._hitl_db:
            return
        try:
            conn = sqlite3.connect(self._hitl_db)
            conn.execute(
                "INSERT OR REPLACE INTO hitl_approvals (task_id, approved, user_id, approval_reason, decided_at) VALUES (?, ?, ?, ?, ?)",
                (
                    task_id,
                    1 if approved else 0,
                    user_id,
                    reason,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to persist approval: {e}")

    async def process_query(
        self,
        query: str,
        context: Dict[str, Any] = None,
        user_id: Optional[int] = None,
        priority: AgentPriority = AgentPriority.MEDIUM,
    ) -> AgentOutput:
        """
        Process a user query through the agent system.

        This is the main entry point for all agent interactions.

        Args:
            query: The user's query or request
            context: Additional context (property_id, entity_name, etc.)
            user_id: ID of the requesting user
            priority: Task priority level

        Returns:
            AgentOutput with the synthesized result
        """
        # Create root task
        root_task = AgentTask(
            query=query,
            context=context or {},
            user_id=user_id,
            priority=priority,
            assigned_agent=self.AGENT_ID,
        )

        logger.info(f"Processing query: {query[:100]}... (task: {root_task.task_id})")

        # Log action
        self._log_action(
            task_id=root_task.task_id,
            action="task_received",
            inputs={"query": query, "context": context},
        )

        try:
            # Step 1: Decompose task
            subtasks = await self._decompose_task(root_task)
            root_task.subtasks = [t.task_id for t in subtasks]
            root_task.status = AgentStatus.IN_PROGRESS
            self._active_tasks[root_task.task_id] = root_task

            # Step 2: Execute subtasks (could be parallel or sequential)
            subtask_outputs = await self._execute_subtasks(subtasks)

            # Step 3: Synthesize results
            synthesis = await self._synthesize_results(root_task, subtask_outputs)

            # Step 4: Validate through guardrails
            guardrail_result = self.guardrail_engine.validate(synthesis)

            if not guardrail_result.passed:
                synthesis.warnings.extend(
                    [v.get("message", "") for v in guardrail_result.violations]
                )
                synthesis.requires_approval = True
                synthesis.approval_reason = "Guardrail violations detected"

            if guardrail_result.requires_approval:
                synthesis.requires_approval = True
                if not synthesis.approval_reason:
                    synthesis.approval_reason = "Low confidence or missing evidence"

            # Step 5: Finalize
            root_task.status = (
                AgentStatus.COMPLETED
                if guardrail_result.passed
                else AgentStatus.AWAITING_APPROVAL
            )

            self._log_action(
                task_id=root_task.task_id,
                action="task_completed",
                outputs={
                    "result": synthesis.result,
                    "confidence": synthesis.confidence,
                },
            )

            return synthesis

        except Exception as e:
            logger.error(f"Task {root_task.task_id} failed: {e}")
            root_task.status = AgentStatus.FAILED

            return AgentOutput(
                task_id=root_task.task_id,
                agent_id=self.AGENT_ID,
                result={"error": str(e)},
                result_type="error",
                confidence=0.0,
                error=str(e),
            )

    async def _decompose_task(self, task: AgentTask) -> List[AgentTask]:
        """
        Decompose a complex task into subtasks for specialist agents.

        Uses keyword matching and query analysis to determine
        which specialists are needed.
        """
        subtasks = []
        query_lower = task.query.lower()

        # Analyze query to determine relevant specialists
        relevant_agents = []

        for agent_id, agent_info in self.SPECIALIST_AGENTS.items():
            score = 0
            for keyword in agent_info["priority_keywords"]:
                if keyword in query_lower:
                    score += 1

            if score > 0:
                relevant_agents.append((agent_id, score))

        # Sort by relevance score
        relevant_agents.sort(key=lambda x: x[1], reverse=True)

        # If no specific agents matched, default to property research
        if not relevant_agents:
            relevant_agents = [("property_research", 1)]

        # Create subtasks for top agents (max 3 to avoid over-parallelization)
        for agent_id, score in relevant_agents[:3]:
            subtask = AgentTask(
                query=task.query,
                context=task.context,
                user_id=task.user_id,
                priority=task.priority,
                parent_task_id=task.task_id,
                assigned_agent=agent_id,
            )
            subtasks.append(subtask)
            self._active_tasks[subtask.task_id] = subtask

        self._log_action(
            task_id=task.task_id,
            action="task_decomposed",
            outputs={
                "subtask_count": len(subtasks),
                "agents": [a for a, _ in relevant_agents[:3]],
            },
        )

        return subtasks

    async def _execute_subtasks(self, subtasks: List[AgentTask]) -> List[AgentOutput]:
        """
        Execute subtasks, potentially in parallel.
        """
        outputs = []

        # For now, execute sequentially (can be parallelized later)
        for subtask in subtasks:
            subtask.status = AgentStatus.IN_PROGRESS

            try:
                output = await self._execute_specialist(subtask)
                outputs.append(output)
                subtask.status = AgentStatus.COMPLETED

            except Exception as e:
                logger.error(f"Subtask {subtask.task_id} failed: {e}")
                subtask.status = AgentStatus.FAILED

                # Create error output
                outputs.append(
                    AgentOutput(
                        task_id=subtask.task_id,
                        agent_id=subtask.assigned_agent or "unknown",
                        result={"error": str(e)},
                        result_type="error",
                        confidence=0.0,
                        error=str(e),
                    )
                )

        return outputs

    async def _execute_specialist(self, task: AgentTask) -> AgentOutput:
        """
        Execute a task through a specialist agent.

        In the full implementation, this would delegate to actual
        specialist agent classes. For now, it uses the tool registry
        to execute relevant tools.
        """
        agent_id = task.assigned_agent
        agent_info = self.SPECIALIST_AGENTS.get(agent_id, {})

        self._log_action(
            task_id=task.task_id,
            action="specialist_invoked",
            inputs={"agent": agent_id, "query": task.query},
        )

        # Get tools available to this agent
        available_tools = self.tool_registry.list_tools(agent_id=agent_id)

        # Simple tool selection based on agent capabilities
        results = []
        evidence_refs = []

        for capability in agent_info.get("capabilities", []):
            # Find a tool matching this capability
            matching_tools = [t for t in available_tools if capability in t.tool_id]

            if matching_tools:
                tool = matching_tools[0]
                try:
                    # Execute tool
                    tool_result = await self.tool_registry.execute(
                        tool_id=tool.tool_id,
                        agent_id=agent_id,
                        inputs={"query": task.query, **task.context},
                    )

                    if tool_result.get("success"):
                        results.append(tool_result.get("data", {}))

                        # Add evidence reference
                        evidence_refs.append(
                            EvidenceRef(
                                ref_id=str(uuid.uuid4()),
                                ref_type="tool_output",
                                source=tool.tool_id,
                                snippet=str(tool_result.get("data", {}))[:200],
                            )
                        )

                except Exception as e:
                    logger.warning(f"Tool {tool.tool_id} failed: {e}")

        # Calculate confidence based on results
        if results:
            confidence = 0.7  # Base confidence when we have results
        else:
            confidence = 0.3  # Low confidence when no tools returned data

        return AgentOutput(
            task_id=task.task_id,
            agent_id=agent_id,
            result={
                "agent": agent_id,
                "agent_name": agent_info.get("name", agent_id),
                "data": results,
                "query": task.query,
            },
            result_type=f"{agent_id}_output",
            confidence=confidence,
            evidence_refs=evidence_refs,
        )

    async def _synthesize_results(
        self, root_task: AgentTask, subtask_outputs: List[AgentOutput]
    ) -> AgentOutput:
        """
        Synthesize outputs from multiple specialists into a coherent response.
        """
        # Collect all results
        combined_data = {}
        all_evidence = []
        all_warnings = []
        min_confidence = 1.0

        for output in subtask_outputs:
            if output.error:
                all_warnings.append(f"{output.agent_id}: {output.error}")
                continue

            combined_data[output.agent_id] = output.result
            all_evidence.extend(output.evidence_refs)
            all_warnings.extend(output.warnings)
            min_confidence = min(min_confidence, output.confidence)

        # Calculate overall confidence (use minimum as conservative estimate)
        overall_confidence = min_confidence if combined_data else 0.2

        # Determine if approval is needed
        requires_approval, approval_reason = (
            self.guardrail_engine.requires_human_approval(
                AgentOutput(
                    task_id=root_task.task_id,
                    agent_id=self.AGENT_ID,
                    result=combined_data,
                    result_type="synthesized_response",
                    confidence=overall_confidence,
                    evidence_refs=all_evidence,
                )
            )
        )

        synthesis = AgentOutput(
            task_id=root_task.task_id,
            agent_id=self.AGENT_ID,
            result={
                "query": root_task.query,
                "response": combined_data,
                "agents_consulted": list(combined_data.keys()),
                "synthesis_timestamp": datetime.utcnow().isoformat(),
            },
            result_type="synthesized_response",
            confidence=overall_confidence,
            evidence_refs=all_evidence,
            warnings=all_warnings,
            requires_approval=requires_approval,
            approval_reason=approval_reason if requires_approval else None,
        )

        # Store for later retrieval
        self._task_outputs[root_task.task_id] = subtask_outputs + [synthesis]

        return synthesis

    def _log_action(
        self,
        task_id: str,
        action: str,
        inputs: Dict[str, Any] = None,
        outputs: Dict[str, Any] = None,
        success: bool = True,
        error: str = None,
    ):
        """Log an agent action for audit trail."""
        action_record = AgentAction(
            task_id=task_id,
            agent_id=self.AGENT_ID,
            action=action,
            inputs=inputs or {},
            outputs=outputs or {},
            success=success,
            error=error,
            completed_at=datetime.utcnow(),
        )
        self._action_log.append(action_record)

        # Persist to HITL database for audit-grade traceability
        self._persist_action(action_record)
        logger.debug(f"Action logged: {action} for task {task_id}")

    def get_task_status(self, task_id: str) -> Optional[AgentTask]:
        """Get the current status of a task."""
        return self._active_tasks.get(task_id)

    def get_action_log(self, task_id: Optional[str] = None) -> List[AgentAction]:
        """Get action log, optionally filtered by task."""
        if task_id:
            return [a for a in self._action_log if a.task_id == task_id]
        return self._action_log.copy()

    def approve_output(self, task_id: str, user_id: int, approved: bool = True) -> bool:
        """
        Approve or reject an output awaiting human approval.
        """
        outputs = self._task_outputs.get(task_id, [])
        if not outputs:
            return False

        # Find the synthesis output
        for output in outputs:
            if output.requires_approval:
                if approved:
                    output.approved_by = user_id
                    output.approved_at = datetime.utcnow()
                    output.requires_approval = False

                    # Update task status
                    task = self._active_tasks.get(task_id)
                    if task:
                        task.status = AgentStatus.COMPLETED
                else:
                    task = self._active_tasks.get(task_id)
                    if task:
                        task.status = AgentStatus.CANCELLED

                self._log_action(
                    task_id=task_id,
                    action="approval_decision",
                    inputs={"approved": approved, "user_id": user_id},
                )

                # Persist approval decision
                self._persist_approval(task_id, approved, user_id)

                return True

        return False
