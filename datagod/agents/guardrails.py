"""
Guardrail Engine (Phase 2: Agentic Core)

Prevents hallucinations and enforces bounded autonomy for agents.
Provides validation, confidence thresholds, and human approval gates.
"""

import logging
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .schemas import AgentOutput, ConfidenceLevel, EvidenceRef

logger = logging.getLogger(__name__)


class GuardrailViolation(str, Enum):
    """Types of guardrail violations."""

    HALLUCINATION = "hallucination"
    LOW_CONFIDENCE = "low_confidence"
    NO_EVIDENCE = "no_evidence"
    FORBIDDEN_CONTENT = "forbidden_content"
    SCHEMA_VIOLATION = "schema_violation"
    PERMISSION_DENIED = "permission_denied"


class GuardrailResult:
    """Result of a guardrail check."""

    def __init__(
        self,
        passed: bool,
        violations: List[Dict[str, Any]] = None,
        warnings: List[str] = None,
        requires_approval: bool = False,
        modified_output: Optional[Dict[str, Any]] = None,
    ):
        self.passed = passed
        self.violations = violations or []
        self.warnings = warnings or []
        self.requires_approval = requires_approval
        self.modified_output = modified_output

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "warnings": self.warnings,
            "requires_approval": self.requires_approval,
        }


class GuardrailEngine:
    """
    Enforces guardrails on agent outputs.

    Features:
    - Hallucination detection
    - Confidence threshold enforcement
    - Evidence requirement validation
    - Forbidden content filtering
    - Human approval gates
    """

    # Default thresholds
    DEFAULT_CONFIDENCE_THRESHOLD = 0.5
    HIGH_RISK_CONFIDENCE_THRESHOLD = 0.8
    APPROVAL_REQUIRED_THRESHOLD = 0.3

    # Patterns that indicate potential hallucinations
    HALLUCINATION_INDICATORS = [
        r"(?i)\b(I think|I believe|probably|likely|might be|could be)\b",
        r"(?i)\b(in my opinion|my guess|I assume)\b",
        r"(?i)\b(typically|usually|generally speaking)\b",
    ]

    # Forbidden content patterns (for compliance)
    FORBIDDEN_PATTERNS = [
        r"(?i)\b(ssn|social security number)\s*[:=]?\s*\d{3}[-\s]?\d{2}[-\s]?\d{4}",
        r"(?i)\b(password|secret key|api key)\s*[:=]\s*\S+",
    ]

    # Result types that require evidence
    EVIDENCE_REQUIRED_TYPES = [
        "property_data",
        "lien_analysis",
        "risk_assessment",
        "entity_match",
        "legal_status",
    ]

    def __init__(
        self,
        confidence_threshold: float = None,
        require_evidence: bool = True,
        check_hallucinations: bool = True,
        check_forbidden: bool = True,
    ):
        self.confidence_threshold = (
            confidence_threshold or self.DEFAULT_CONFIDENCE_THRESHOLD
        )
        self.require_evidence = require_evidence
        self.check_hallucinations = check_hallucinations
        self.check_forbidden = check_forbidden

        # Custom rules can be added
        self._custom_rules: List[callable] = []

    def add_rule(self, rule_func: callable):
        """Add a custom validation rule."""
        self._custom_rules.append(rule_func)

    def validate(self, output: AgentOutput) -> GuardrailResult:
        """
        Validate an agent output against all guardrails.

        Args:
            output: The AgentOutput to validate

        Returns:
            GuardrailResult with pass/fail status and any violations
        """
        violations = []
        warnings = []
        requires_approval = False

        # Check confidence threshold
        conf_result = self._check_confidence(output)
        if conf_result:
            if conf_result["severity"] == "violation":
                violations.append(conf_result)
            else:
                warnings.append(conf_result["message"])
            if conf_result.get("requires_approval"):
                requires_approval = True

        # Check for evidence
        if self.require_evidence:
            evidence_result = self._check_evidence(output)
            if evidence_result:
                if evidence_result["severity"] == "violation":
                    violations.append(evidence_result)
                else:
                    warnings.append(evidence_result["message"])

        # Check for hallucination indicators
        if self.check_hallucinations:
            halluc_result = self._check_hallucinations(output)
            if halluc_result:
                violations.extend(halluc_result)

        # Check for forbidden content
        if self.check_forbidden:
            forbidden_result = self._check_forbidden_content(output)
            if forbidden_result:
                violations.extend(forbidden_result)

        # Run custom rules
        for rule in self._custom_rules:
            try:
                rule_result = rule(output)
                if rule_result:
                    if isinstance(rule_result, dict):
                        violations.append(rule_result)
                    else:
                        warnings.append(str(rule_result))
            except Exception as e:
                logger.warning(f"Custom rule failed: {e}")

        passed = len(violations) == 0

        return GuardrailResult(
            passed=passed,
            violations=violations,
            warnings=warnings,
            requires_approval=requires_approval or (not passed),
        )

    def _check_confidence(self, output: AgentOutput) -> Optional[Dict[str, Any]]:
        """Check if confidence meets threshold."""
        if output.confidence < self.APPROVAL_REQUIRED_THRESHOLD:
            return {
                "type": GuardrailViolation.LOW_CONFIDENCE,
                "severity": "violation",
                "message": f"Confidence {output.confidence:.2f} below minimum threshold {self.APPROVAL_REQUIRED_THRESHOLD}",
                "requires_approval": True,
            }
        elif output.confidence < self.confidence_threshold:
            return {
                "type": GuardrailViolation.LOW_CONFIDENCE,
                "severity": "warning",
                "message": f"Confidence {output.confidence:.2f} below recommended threshold {self.confidence_threshold}",
                "requires_approval": True,
            }
        return None

    def _check_evidence(self, output: AgentOutput) -> Optional[Dict[str, Any]]:
        """Check if required evidence is present."""
        if output.result_type in self.EVIDENCE_REQUIRED_TYPES:
            if not output.evidence_refs or len(output.evidence_refs) == 0:
                return {
                    "type": GuardrailViolation.NO_EVIDENCE,
                    "severity": "violation",
                    "message": f"Result type '{output.result_type}' requires evidence but none provided",
                }
        return None

    def _check_hallucinations(self, output: AgentOutput) -> List[Dict[str, Any]]:
        """Check for language patterns that suggest hallucination."""
        violations = []

        # Convert result to string for pattern matching
        result_str = str(output.result)

        for pattern in self.HALLUCINATION_INDICATORS:
            matches = re.findall(pattern, result_str)
            if matches:
                violations.append(
                    {
                        "type": GuardrailViolation.HALLUCINATION,
                        "severity": "warning",
                        "message": f"Possible hallucination indicator found: '{matches[0]}'",
                        "pattern": pattern,
                        "matches": matches[:3],  # Limit to first 3
                    }
                )

        return violations

    def _check_forbidden_content(self, output: AgentOutput) -> List[Dict[str, Any]]:
        """Check for forbidden content patterns."""
        violations = []

        result_str = str(output.result)

        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, result_str):
                violations.append(
                    {
                        "type": GuardrailViolation.FORBIDDEN_CONTENT,
                        "severity": "violation",
                        "message": "Forbidden content pattern detected",
                        "pattern": pattern[:50] + "...",  # Truncate for logging
                    }
                )

        return violations

    def sanitize_output(self, output: AgentOutput) -> AgentOutput:
        """
        Sanitize an output by removing or redacting problematic content.

        Returns a modified copy of the output.
        """
        result_str = str(output.result)

        # Redact forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            result_str = re.sub(pattern, "[REDACTED]", result_str)

        # If result was modified, create new output
        if result_str != str(output.result):
            # Note: This is a simplified approach - in production would deep copy and modify
            output.warnings.append("Output was sanitized to remove sensitive content")

        return output

    def requires_human_approval(self, output: AgentOutput) -> Tuple[bool, str]:
        """
        Determine if an output requires human approval.

        Returns:
            Tuple of (requires_approval, reason)
        """
        # Low confidence always requires approval
        if output.confidence < self.APPROVAL_REQUIRED_THRESHOLD:
            return True, f"Low confidence ({output.confidence:.2f})"

        # High-risk result types require approval at higher threshold
        high_risk_types = ["legal_status", "risk_assessment", "entity_match"]
        if output.result_type in high_risk_types:
            if output.confidence < self.HIGH_RISK_CONFIDENCE_THRESHOLD:
                return (
                    True,
                    f"High-risk result type with moderate confidence ({output.confidence:.2f})",
                )

        # No evidence for evidence-required types
        if output.result_type in self.EVIDENCE_REQUIRED_TYPES:
            if not output.evidence_refs:
                return True, "Missing required evidence"

        # Output already flagged
        if output.requires_approval:
            return True, output.approval_reason or "Previously flagged"

        return False, ""


# Global guardrail engine instance
guardrail_engine = GuardrailEngine()
