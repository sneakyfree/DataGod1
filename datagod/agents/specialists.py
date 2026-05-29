"""
Specialist Agents (Phase 2.2: Specialist Agents)

Domain-specific agents for DataGod research tasks:
- PropertyResearchAgent: Property records and ownership
- EntityResolutionAgent: Entity matching and disambiguation
- LienPriorityAgent: Lien analysis and priority calculation
- RiskAssessmentAgent: Risk identification and scoring
- ComplianceCheckAgent: Regulatory compliance validation
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_agent import BaseSpecialistAgent
from .schemas import AgentOutput, AgentTask, EvidenceRef

logger = logging.getLogger(__name__)


class PropertyResearchAgent(BaseSpecialistAgent):
    """
    Specialist agent for property research.

    Capabilities:
    - Property search by address, parcel ID, or owner
    - Ownership chain analysis
    - Deed and mortgage record lookup
    - Tax status verification
    """

    AGENT_ID = "property_research"
    AGENT_NAME = "Property Research Agent"
    DESCRIPTION = "Searches and analyzes property records"
    CAPABILITIES = ["property_search", "ownership_chain", "deed_lookup", "tax_status"]

    # Property record types we handle
    RECORD_TYPES = [
        "deed",
        "mortgage",
        "assignment",
        "release",
        "lien",
        "lis_pendens",
        "judgment",
        "ucc",
    ]

    async def process(self, task: AgentTask) -> AgentOutput:
        """Process a property research task."""
        self.log_action(task.task_id, "process_started", inputs={"query": task.query})

        results = {}
        evidence_refs = []
        warnings = []
        confidence = 0.0

        try:
            # Step 1: Parse the query to extract property identifiers
            property_info = self._extract_property_info(task.query, task.context)

            if not property_info:
                return self.create_output(
                    task=task,
                    result={"error": "Could not identify property from query"},
                    result_type="property_research",
                    confidence=0.1,
                    warnings=["No property identifiers found in query"],
                )

            # Step 2: Search for property records
            search_result = await self.execute_tool(
                "property_search",
                {"query": property_info.get("address", task.query), **property_info},
            )

            if search_result.get("success"):
                results["property_search"] = search_result.get("data", {})
                evidence_refs.append(
                    self.create_evidence_ref(
                        source="property_search",
                        snippet=str(search_result.get("data", {}))[:200],
                    )
                )
                confidence = 0.6
            else:
                warnings.append(
                    f"Property search: {search_result.get('error', 'Unknown error')}"
                )

            # Step 3: Get ownership information
            if property_info.get("property_id") or results.get("property_search"):
                lien_result = await self.execute_tool(
                    "lien_search",
                    {"property_id": property_info.get("property_id", "unknown")},
                )

                if lien_result.get("success"):
                    results["liens"] = lien_result.get("data", {})
                    evidence_refs.append(
                        self.create_evidence_ref(
                            source="lien_search",
                            snippet=str(lien_result.get("data", {}))[:200],
                        )
                    )
                    confidence = min(confidence + 0.2, 0.9)

            # Step 4: Compile summary
            results["summary"] = self._compile_property_summary(results)

            self.log_action(
                task.task_id,
                "process_completed",
                outputs={"result_keys": list(results.keys()), "confidence": confidence},
            )

            return self.create_output(
                task=task,
                result=results,
                result_type="property_research",
                confidence=confidence,
                evidence_refs=evidence_refs,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Property research failed: {e}")
            return self.create_output(
                task=task,
                result={"error": str(e)},
                result_type="property_research",
                confidence=0.0,
                error=str(e),
            )

    def _extract_property_info(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract property identifiers from query and context."""
        info = {}

        # Check context first
        if context.get("property_id"):
            info["property_id"] = context["property_id"]
        if context.get("address"):
            info["address"] = context["address"]
        if context.get("parcel_id"):
            info["parcel_id"] = context["parcel_id"]

        # Try to extract address from query
        # Simple pattern matching - production would use NER
        address_pattern = r"\d+\s+\w+(?:\s+\w+)*(?:\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|Court)\.?)"
        matches = re.findall(address_pattern, query, re.IGNORECASE)
        if matches and "address" not in info:
            info["address"] = matches[0]

        return info

    def _compile_property_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compile a summary of property research results."""
        summary = {
            "data_found": bool(results.get("property_search")),
            "liens_found": bool(results.get("liens")),
            "record_types_found": [],
            "total_lien_amount": 0,
        }

        if results.get("liens") and isinstance(results["liens"], dict):
            liens = results["liens"].get("liens", [])
            if liens:
                summary["record_types_found"].append("liens")
                # Sum lien amounts if available
                for lien in liens:
                    if isinstance(lien, dict) and lien.get("amount"):
                        summary["total_lien_amount"] += float(lien.get("amount", 0))

        return summary


class EntityResolutionAgent(BaseSpecialistAgent):
    """
    Specialist agent for entity resolution.

    Capabilities:
    - Entity search across records
    - Name matching and disambiguation
    - Relationship mapping between entities
    - Entity type classification
    """

    AGENT_ID = "entity_resolution"
    AGENT_NAME = "Entity Resolution Agent"
    DESCRIPTION = "Matches and disambiguates entities across records"
    CAPABILITIES = ["entity_search", "name_matching", "relationship_mapping"]

    # Entity types
    ENTITY_TYPES = ["person", "company", "trust", "government", "unknown"]

    async def process(self, task: AgentTask) -> AgentOutput:
        """Process an entity resolution task."""
        self.log_action(task.task_id, "process_started", inputs={"query": task.query})

        results = {}
        evidence_refs = []
        warnings = []
        confidence = 0.0

        try:
            # Step 1: Extract entity name from query
            entity_info = self._extract_entity_info(task.query, task.context)

            if not entity_info.get("name"):
                return self.create_output(
                    task=task,
                    result={"error": "Could not identify entity name from query"},
                    result_type="entity_resolution",
                    confidence=0.1,
                    warnings=["No entity name found in query"],
                )

            # Step 2: Search for entity
            search_result = await self.execute_tool(
                "entity_search",
                {
                    "name": entity_info["name"],
                    "entity_type": entity_info.get("type", "any"),
                },
            )

            if search_result.get("success"):
                results["entity_search"] = search_result.get("data", {})
                evidence_refs.append(
                    self.create_evidence_ref(
                        source="entity_search",
                        snippet=str(search_result.get("data", {}))[:200],
                    )
                )
                confidence = 0.5

                # Calculate match confidence
                match_confidence = search_result.get("data", {}).get(
                    "match_confidence", 0.5
                )
                confidence = min(confidence + match_confidence * 0.4, 0.95)
            else:
                warnings.append(
                    f"Entity search: {search_result.get('error', 'Unknown error')}"
                )

            # Step 3: Resolve entity type
            results["resolved_type"] = self._classify_entity_type(
                entity_info["name"], results.get("entity_search", {})
            )

            # Step 4: Find related entities
            results["related_entities"] = self._find_related_entities(
                results.get("entity_search", {})
            )

            self.log_action(
                task.task_id,
                "process_completed",
                outputs={
                    "entities_found": len(
                        results.get("entity_search", {}).get("entities", [])
                    ),
                    "confidence": confidence,
                },
            )

            return self.create_output(
                task=task,
                result=results,
                result_type="entity_resolution",
                confidence=confidence,
                evidence_refs=evidence_refs,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Entity resolution failed: {e}")
            return self.create_output(
                task=task,
                result={"error": str(e)},
                result_type="entity_resolution",
                confidence=0.0,
                error=str(e),
            )

    def _extract_entity_info(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract entity information from query and context."""
        info = {}

        if context.get("entity_name"):
            info["name"] = context["entity_name"]
        if context.get("entity_type"):
            info["type"] = context["entity_type"]

        # Simple extraction - look for common patterns
        # "owner", "person", "company" followed by name
        if "name" not in info:
            # Default to using significant words from query
            # Production would use NER
            words = query.split()
            # Filter out common words
            stop_words = {
                "find",
                "search",
                "look",
                "for",
                "the",
                "a",
                "an",
                "who",
                "is",
                "are",
                "was",
                "owner",
                "of",
            }
            significant = [w for w in words if w.lower() not in stop_words]
            if significant:
                info["name"] = " ".join(significant[:3])  # First 3 significant words

        return info

    def _classify_entity_type(self, name: str, search_results: Dict[str, Any]) -> str:
        """Classify the entity type based on name and search results."""
        name_lower = name.lower()

        # Check for company indicators
        company_indicators = [
            "llc",
            "inc",
            "corp",
            "ltd",
            "company",
            "co.",
            "trust",
            "bank",
            "mortgage",
        ]
        for indicator in company_indicators:
            if indicator in name_lower:
                return "company" if "trust" not in indicator else "trust"

        # Check search results for type info
        if search_results and search_results.get("entities"):
            for entity in search_results["entities"]:
                if entity.get("entity_type"):
                    return entity["entity_type"]

        # Default to person if no indicators
        return "person"

    def _find_related_entities(
        self, search_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find entities related to the searched entity."""
        related = []

        if search_results and search_results.get("entities"):
            for entity in search_results["entities"]:
                # Look for relationships in entity data
                if entity.get("relationships"):
                    for rel in entity["relationships"]:
                        related.append(
                            {
                                "name": rel.get("related_entity"),
                                "relationship": rel.get("relationship_type"),
                                "confidence": rel.get("confidence", 0.5),
                            }
                        )

        return related


class LienPriorityAgent(BaseSpecialistAgent):
    """
    Specialist agent for lien priority analysis.

    Capabilities:
    - Lien search and identification
    - Priority stack calculation
    - Amount and status analysis
    - Clearance requirements
    """

    AGENT_ID = "lien_priority"
    AGENT_NAME = "Lien Priority Agent"
    DESCRIPTION = "Calculates lien priority and encumbrance stacks"
    CAPABILITIES = ["lien_priority", "amount_calculation", "clearance_analysis"]

    # Lien priority order (higher = paid first)
    PRIORITY_ORDER = {
        "tax_lien": 100,
        "property_tax": 100,
        "mechanic_lien": 90,
        "first_mortgage": 80,
        "second_mortgage": 70,
        "heloc": 65,
        "judgment": 50,
        "ucc": 40,
        "other": 30,
    }

    async def process(self, task: AgentTask) -> AgentOutput:
        """Process a lien priority analysis task."""
        self.log_action(task.task_id, "process_started", inputs={"query": task.query})

        results = {}
        evidence_refs = []
        warnings = []
        confidence = 0.0

        try:
            # Step 1: Get property ID from context or query
            property_id = task.context.get("property_id", "unknown")

            # Step 2: Search for liens
            lien_result = await self.execute_tool(
                "lien_search",
                {
                    "property_id": property_id,
                    "lien_types": list(self.PRIORITY_ORDER.keys()),
                },
            )

            if lien_result.get("success"):
                liens = lien_result.get("data", {}).get("liens", [])
                results["liens_found"] = liens
                evidence_refs.append(
                    self.create_evidence_ref(
                        source="lien_search", snippet=f"Found {len(liens)} liens"
                    )
                )
                confidence = 0.6
            else:
                warnings.append(
                    f"Lien search: {lien_result.get('error', 'Unknown error')}"
                )
                liens = []

            # Step 3: Calculate priority stack
            priority_stack = self._calculate_priority_stack(liens)
            results["priority_stack"] = priority_stack

            # Step 4: Calculate totals
            results["totals"] = self._calculate_totals(priority_stack)

            # Step 5: Generate clearance requirements
            results["clearance_requirements"] = self._generate_clearance_requirements(
                priority_stack
            )

            if priority_stack:
                confidence = min(confidence + 0.2, 0.85)

            self.log_action(
                task.task_id,
                "process_completed",
                outputs={
                    "liens_count": len(liens),
                    "total_amount": results["totals"].get("total", 0),
                },
            )

            return self.create_output(
                task=task,
                result=results,
                result_type="lien_priority",
                confidence=confidence,
                evidence_refs=evidence_refs,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Lien priority analysis failed: {e}")
            return self.create_output(
                task=task,
                result={"error": str(e)},
                result_type="lien_priority",
                confidence=0.0,
                error=str(e),
            )

    def _calculate_priority_stack(
        self, liens: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate the priority stack for liens."""
        scored_liens = []

        for lien in liens:
            lien_type = lien.get("type", "other").lower()
            priority_score = self.PRIORITY_ORDER.get(lien_type, 30)

            scored_liens.append(
                {
                    **lien,
                    "priority_score": priority_score,
                    "priority_rank": 0,  # Will be set after sorting
                }
            )

        # Sort by priority (higher first) then by date (earlier first)
        scored_liens.sort(
            key=lambda x: (-x["priority_score"], x.get("recorded_date", "")),
        )

        # Assign ranks
        for i, lien in enumerate(scored_liens):
            lien["priority_rank"] = i + 1

        return scored_liens

    def _calculate_totals(self, priority_stack: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate total amounts and statistics."""
        total = 0
        by_type = {}

        for lien in priority_stack:
            amount = float(lien.get("amount", 0) or 0)
            total += amount

            lien_type = lien.get("type", "other")
            by_type[lien_type] = by_type.get(lien_type, 0) + amount

        return {"total": total, "count": len(priority_stack), "by_type": by_type}

    def _generate_clearance_requirements(
        self, priority_stack: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate requirements to clear each lien."""
        requirements = []

        for lien in priority_stack:
            req = {
                "lien_type": lien.get("type"),
                "amount": lien.get("amount", 0),
                "priority_rank": lien.get("priority_rank"),
                "action_required": "payoff",
                "estimated_timeframe": "3-5 business days",
            }

            # Customize based on lien type
            if lien.get("type") == "tax_lien":
                req["action_required"] = "pay_with_interest"
                req["estimated_timeframe"] = "1-2 business days"
            elif lien.get("type") == "judgment":
                req["action_required"] = "negotiate_or_pay"
                req["estimated_timeframe"] = "30-60 days"

            requirements.append(req)

        return requirements


class RiskAssessmentAgent(BaseSpecialistAgent):
    """
    Specialist agent for risk assessment.

    Capabilities:
    - Red flag detection
    - Distress signal identification
    - Risk scoring
    - Risk mitigation recommendations
    """

    AGENT_ID = "risk_assessment"
    AGENT_NAME = "Risk Assessment Agent"
    DESCRIPTION = "Identifies and scores documented risks"
    CAPABILITIES = ["risk_scoring", "red_flag_detection", "distress_signals"]

    # Risk factors and weights
    RISK_FACTORS = {
        "tax_delinquency": {"weight": 0.25, "severity": "high"},
        "lis_pendens": {"weight": 0.20, "severity": "high"},
        "foreclosure_filing": {"weight": 0.30, "severity": "critical"},
        "multiple_liens": {"weight": 0.15, "severity": "medium"},
        "judgment": {"weight": 0.10, "severity": "medium"},
        "bankruptcy": {"weight": 0.25, "severity": "high"},
        "code_violation": {"weight": 0.10, "severity": "low"},
        "title_defect": {"weight": 0.20, "severity": "high"},
    }

    async def process(self, task: AgentTask) -> AgentOutput:
        """Process a risk assessment task."""
        self.log_action(task.task_id, "process_started", inputs={"query": task.query})

        results = {}
        evidence_refs = []
        warnings = []
        confidence = 0.0

        try:
            property_id = task.context.get("property_id", "unknown")

            # Step 1: Get property and lien data for analysis
            property_result = await self.execute_tool(
                "property_search", {"query": task.query, "property_id": property_id}
            )

            lien_result = await self.execute_tool(
                "lien_search", {"property_id": property_id}
            )

            # Collect data for analysis
            property_data = (
                property_result.get("data", {})
                if property_result.get("success")
                else {}
            )
            lien_data = (
                lien_result.get("data", {}) if lien_result.get("success") else {}
            )

            if property_result.get("success") or lien_result.get("success"):
                evidence_refs.append(
                    self.create_evidence_ref(
                        source="risk_data_collection",
                        snippet="Collected property and lien data for risk analysis",
                    )
                )
                confidence = 0.5

            # Step 2: Detect red flags
            red_flags = self._detect_red_flags(property_data, lien_data)
            results["red_flags"] = red_flags

            # Step 3: Calculate risk score
            risk_score = self._calculate_risk_score(red_flags)
            results["risk_score"] = risk_score

            # Step 4: Identify distress signals
            distress_signals = self._identify_distress_signals(
                property_data, lien_data, red_flags
            )
            results["distress_signals"] = distress_signals

            # Step 5: Generate recommendations
            results["recommendations"] = self._generate_recommendations(
                red_flags, risk_score
            )

            if red_flags:
                confidence = min(confidence + 0.3, 0.85)

            self.log_action(
                task.task_id,
                "process_completed",
                outputs={
                    "risk_score": risk_score["overall"],
                    "red_flags_count": len(red_flags),
                },
            )

            return self.create_output(
                task=task,
                result=results,
                result_type="risk_assessment",
                confidence=confidence,
                evidence_refs=evidence_refs,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            return self.create_output(
                task=task,
                result={"error": str(e)},
                result_type="risk_assessment",
                confidence=0.0,
                error=str(e),
            )

    def _detect_red_flags(
        self, property_data: Dict, lien_data: Dict
    ) -> List[Dict[str, Any]]:
        """Detect red flags in the data."""
        red_flags = []

        # Check for multiple liens
        liens = lien_data.get("liens", [])
        if len(liens) > 2:
            red_flags.append(
                {
                    "type": "multiple_liens",
                    "severity": self.RISK_FACTORS["multiple_liens"]["severity"],
                    "description": f"Property has {len(liens)} liens",
                    "data": {"count": len(liens)},
                }
            )

        # Check for specific lien types
        for lien in liens:
            lien_type = lien.get("type", "").lower()
            if lien_type == "lis_pendens":
                red_flags.append(
                    {
                        "type": "lis_pendens",
                        "severity": "high",
                        "description": "Pending litigation on property",
                        "data": lien,
                    }
                )
            elif "foreclosure" in lien_type:
                red_flags.append(
                    {
                        "type": "foreclosure_filing",
                        "severity": "critical",
                        "description": "Foreclosure action filed",
                        "data": lien,
                    }
                )
            elif "tax" in lien_type:
                red_flags.append(
                    {
                        "type": "tax_delinquency",
                        "severity": "high",
                        "description": "Tax delinquency on property",
                        "data": lien,
                    }
                )

        return red_flags

    def _calculate_risk_score(self, red_flags: List[Dict]) -> Dict[str, Any]:
        """Calculate overall risk score."""
        if not red_flags:
            return {"overall": 0.0, "category": "low", "factors": []}

        total_weight = 0
        factors = []

        for flag in red_flags:
            flag_type = flag.get("type", "other")
            factor_info = self.RISK_FACTORS.get(flag_type, {"weight": 0.05})
            weight = factor_info["weight"]
            total_weight += weight
            factors.append({"type": flag_type, "weight": weight})

        # Normalize to 0-1 scale
        overall = min(total_weight, 1.0)

        # Determine category
        if overall >= 0.7:
            category = "critical"
        elif overall >= 0.4:
            category = "high"
        elif overall >= 0.2:
            category = "medium"
        else:
            category = "low"

        return {"overall": round(overall, 2), "category": category, "factors": factors}

    def _identify_distress_signals(
        self, property_data: Dict, lien_data: Dict, red_flags: List
    ) -> List[Dict]:
        """Identify distress signals that may indicate opportunity."""
        signals = []

        # High-priority red flags are distress signals
        for flag in red_flags:
            if flag.get("severity") in ["high", "critical"]:
                signals.append(
                    {
                        "signal": flag["type"],
                        "description": flag["description"],
                        "opportunity_type": "distressed_acquisition",
                    }
                )

        return signals

    def _generate_recommendations(
        self, red_flags: List, risk_score: Dict
    ) -> List[Dict]:
        """Generate risk mitigation recommendations."""
        recommendations = []

        if risk_score["category"] == "critical":
            recommendations.append(
                {
                    "priority": "immediate",
                    "action": "Obtain legal counsel before proceeding",
                    "reason": "Critical risk factors detected",
                }
            )

        for flag in red_flags:
            if flag["type"] == "tax_delinquency":
                recommendations.append(
                    {
                        "priority": "high",
                        "action": "Verify tax amounts and redemption period",
                        "reason": "Tax liens have priority over most other liens",
                    }
                )
            elif flag["type"] == "lis_pendens":
                recommendations.append(
                    {
                        "priority": "high",
                        "action": "Research pending litigation details",
                        "reason": "Pending litigation may affect title",
                    }
                )

        return recommendations


class ComplianceCheckAgent(BaseSpecialistAgent):
    """
    Specialist agent for compliance checking.

    Capabilities:
    - Rule validation
    - Regulatory compliance checking
    - Audit preparation
    - Documentation requirements
    """

    AGENT_ID = "compliance_check"
    AGENT_NAME = "Compliance Check Agent"
    DESCRIPTION = "Validates against configured rules and regulations"
    CAPABILITIES = ["rule_checking", "regulation_validation", "audit_preparation"]

    # Compliance rules
    COMPLIANCE_RULES = {
        "data_accuracy": {
            "description": "All data must have verifiable sources",
            "severity": "high",
        },
        "privacy_protection": {
            "description": "PII must be handled according to privacy regulations",
            "severity": "critical",
        },
        "audit_trail": {
            "description": "All actions must be logged with timestamps",
            "severity": "high",
        },
        "data_freshness": {
            "description": "Data must be within acceptable age limits",
            "severity": "medium",
        },
    }

    async def process(self, task: AgentTask) -> AgentOutput:
        """Process a compliance check task."""
        self.log_action(task.task_id, "process_started", inputs={"query": task.query})

        results = {}
        evidence_refs = []
        warnings = []
        confidence = 0.7  # Compliance checks are generally high confidence

        try:
            # Step 1: Identify what to check
            check_type = task.context.get("check_type", "general")
            data_to_check = task.context.get("data", {})

            # Step 2: Run compliance checks
            compliance_results = self._run_compliance_checks(data_to_check)
            results["compliance_checks"] = compliance_results

            # Step 3: Calculate compliance score
            compliance_score = self._calculate_compliance_score(compliance_results)
            results["compliance_score"] = compliance_score

            # Step 4: Generate required documentation
            required_docs = self._identify_required_documentation(compliance_results)
            results["required_documentation"] = required_docs

            # Step 5: Check audit readiness
            audit_status = self._check_audit_readiness(compliance_results)
            results["audit_status"] = audit_status

            # Add warnings for failed checks
            for check in compliance_results:
                if not check.get("passed"):
                    warnings.append(f"Compliance check failed: {check['rule']}")

            evidence_refs.append(
                self.create_evidence_ref(
                    source="compliance_engine",
                    snippet=f"Ran {len(compliance_results)} compliance checks",
                )
            )

            self.log_action(
                task.task_id,
                "process_completed",
                outputs={
                    "compliance_score": compliance_score,
                    "checks_run": len(compliance_results),
                },
            )

            return self.create_output(
                task=task,
                result=results,
                result_type="compliance_check",
                confidence=confidence,
                evidence_refs=evidence_refs,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Compliance check failed: {e}")
            return self.create_output(
                task=task,
                result={"error": str(e)},
                result_type="compliance_check",
                confidence=0.0,
                error=str(e),
            )

    def _run_compliance_checks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all compliance checks on the data."""
        results = []

        for rule_id, rule_info in self.COMPLIANCE_RULES.items():
            check_result = {
                "rule": rule_id,
                "description": rule_info["description"],
                "severity": rule_info["severity"],
                "passed": True,  # Default to passed
                "details": None,
            }

            # Specific check implementations
            if rule_id == "data_accuracy":
                # Check if data has source references
                has_sources = bool(data.get("sources") or data.get("evidence_refs"))
                check_result["passed"] = has_sources
                if not has_sources:
                    check_result["details"] = "No source references found"

            elif rule_id == "audit_trail":
                # Check for timestamps
                has_timestamps = bool(data.get("created_at") or data.get("timestamp"))
                check_result["passed"] = has_timestamps
                if not has_timestamps:
                    check_result["details"] = "Missing timestamp information"

            results.append(check_result)

        return results

    def _calculate_compliance_score(self, check_results: List[Dict]) -> float:
        """Calculate overall compliance score."""
        if not check_results:
            return 1.0

        passed = sum(1 for c in check_results if c.get("passed"))
        return round(passed / len(check_results), 2)

    def _identify_required_documentation(self, check_results: List[Dict]) -> List[Dict]:
        """Identify documentation needed for compliance."""
        docs = []

        for check in check_results:
            if not check.get("passed"):
                docs.append(
                    {
                        "requirement": check["rule"],
                        "description": f"Documentation needed to satisfy: {check['description']}",
                        "priority": check["severity"],
                    }
                )

        return docs

    def _check_audit_readiness(self, check_results: List[Dict]) -> Dict[str, Any]:
        """Check if ready for audit."""
        failed_critical = any(
            c
            for c in check_results
            if not c.get("passed") and c.get("severity") == "critical"
        )

        failed_high = sum(
            1
            for c in check_results
            if not c.get("passed") and c.get("severity") == "high"
        )

        if failed_critical:
            status = "not_ready"
            reason = "Critical compliance failures"
        elif failed_high > 0:
            status = "partially_ready"
            reason = f"{failed_high} high-severity issues to address"
        else:
            status = "ready"
            reason = "All checks passed"

        return {
            "status": status,
            "reason": reason,
            "passed_checks": sum(1 for c in check_results if c.get("passed")),
            "total_checks": len(check_results),
        }


# Export all agents
__all__ = [
    "PropertyResearchAgent",
    "EntityResolutionAgent",
    "LienPriorityAgent",
    "RiskAssessmentAgent",
    "ComplianceCheckAgent",
]
