"""
Reason Code Engine (DNA Strand Gene 4.4)

Maps blocker types and rule violations to standardized adverse action
reason codes for regulatory compliance.

Supports:
- FCRA (Fair Credit Reporting Act) reason codes
- ECOA (Equal Credit Opportunity Act) reason codes
- Custom DataGod-specific codes for property/lien actions
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReasonCodeStandard(str, Enum):
    """Regulatory standard for reason codes."""

    FCRA = "fcra"
    ECOA = "ecoa"
    DATAGOD = "datagod"  # Internal standard for property/lien actions


class ReasonCodeSeverity(str, Enum):
    """Severity classification."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class ReasonCode:
    """A standardized reason code for an adverse or notable action."""

    code: str
    standard: ReasonCodeStandard
    title: str
    description: str
    regulation_reference: str
    severity: ReasonCodeSeverity
    category: str
    remediation_hint: str = ""
    applicable_blocker_types: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "standard": self.standard.value,
            "title": self.title,
            "description": self.description,
            "regulation_reference": self.regulation_reference,
            "severity": self.severity.value,
            "category": self.category,
            "remediation_hint": self.remediation_hint,
            "applicable_blocker_types": self.applicable_blocker_types,
        }


@dataclass
class ReasonCodeResult:
    """Result of reason code generation for a set of blockers."""

    codes: List[ReasonCode]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    total_codes: int = 0
    critical_count: int = 0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "codes": [c.to_dict() for c in self.codes],
            "generated_at": self.generated_at.isoformat(),
            "total_codes": self.total_codes,
            "critical_count": self.critical_count,
            "summary": self.summary,
        }


class ReasonCodeEngine:
    """
    Maps blockers and rule violations to standard reason codes.

    Provides regulatory-grade traceability from every adverse decision
    back to a specific code with regulation reference.
    """

    def __init__(self):
        self._catalog = self._initialize_catalog()

    def _initialize_catalog(self) -> Dict[str, ReasonCode]:
        """Initialize the comprehensive reason code catalog."""
        catalog = {}

        # --- FCRA-Adjacent Reason Codes ---
        fcra_codes = [
            ReasonCode(
                "FCRA-01",
                ReasonCodeStandard.FCRA,
                "Derogatory Public Record",
                "Public record information indicates adverse legal action",
                "15 U.S.C. § 1681(a)",
                ReasonCodeSeverity.HIGH,
                "legal",
                "Review and dispute inaccurate public records",
                ["judgment_lien", "bankruptcy"],
            ),
            ReasonCode(
                "FCRA-02",
                ReasonCodeStandard.FCRA,
                "Collection Account",
                "Outstanding collection account(s) on record",
                "15 U.S.C. § 1681(a)",
                ReasonCodeSeverity.HIGH,
                "financial",
                "Settle or dispute collection accounts",
                ["collection_action"],
            ),
            ReasonCode(
                "FCRA-03",
                ReasonCodeStandard.FCRA,
                "Tax Lien Filed",
                "Federal, state, or local tax lien filed against property",
                "15 U.S.C. § 1681(a)",
                ReasonCodeSeverity.CRITICAL,
                "tax",
                "Pay outstanding tax liability or negotiate payment plan",
                ["tax_lien", "federal_tax_lien", "state_tax_lien"],
            ),
            ReasonCode(
                "FCRA-04",
                ReasonCodeStandard.FCRA,
                "Judgment Entered",
                "Civil judgment entered against property owner or entity",
                "15 U.S.C. § 1681(a)",
                ReasonCodeSeverity.HIGH,
                "legal",
                "Satisfy judgment or negotiate settlement",
                ["judgment_lien", "civil_judgment"],
            ),
        ]

        # --- ECOA-Adjacent Reason Codes ---
        ecoa_codes = [
            ReasonCode(
                "ECOA-01",
                ReasonCodeStandard.ECOA,
                "Insufficient Collateral",
                "Property value insufficient relative to proposed transaction",
                "12 CFR § 1002.9",
                ReasonCodeSeverity.MEDIUM,
                "property",
                "Obtain updated appraisal or reduce transaction amount",
                ["low_value", "insufficient_equity"],
            ),
            ReasonCode(
                "ECOA-02",
                ReasonCodeStandard.ECOA,
                "Unclear Title",
                "Title defects prevent clear conveyance",
                "12 CFR § 1002.9",
                ReasonCodeSeverity.HIGH,
                "title",
                "Obtain title insurance or resolve title defects",
                ["title_defect", "chain_of_title", "competing_claim"],
            ),
            ReasonCode(
                "ECOA-03",
                ReasonCodeStandard.ECOA,
                "Excessive Existing Liens",
                "Total existing liens exceed acceptable threshold relative to value",
                "12 CFR § 1002.9",
                ReasonCodeSeverity.HIGH,
                "financial",
                "Pay down existing liens or negotiate subordination",
                ["excessive_liens", "over_leveraged"],
            ),
        ]

        # --- DataGod Internal Codes ---
        dg_codes = [
            ReasonCode(
                "DG-001",
                ReasonCodeStandard.DATAGOD,
                "Mechanics Lien Active",
                "Active mechanics lien indicates unpaid construction work",
                "State Lien Law (varies)",
                ReasonCodeSeverity.MEDIUM,
                "lien",
                "Negotiate with contractor or post bond",
                ["mechanics_lien"],
            ),
            ReasonCode(
                "DG-002",
                ReasonCodeStandard.DATAGOD,
                "HOA Lien Delinquent",
                "HOA assessment lien for unpaid dues",
                "CC&Rs / State HOA Statute",
                ReasonCodeSeverity.MEDIUM,
                "lien",
                "Pay outstanding HOA dues and request lien release",
                ["hoa_lien"],
            ),
            ReasonCode(
                "DG-003",
                ReasonCodeStandard.DATAGOD,
                "Environmental Hazard Flag",
                "Environmental contamination or hazard identified at property",
                "CERCLA / State ENV Law",
                ReasonCodeSeverity.CRITICAL,
                "environmental",
                "Obtain Phase I/II environmental assessment",
                ["environmental_hazard", "contamination"],
            ),
            ReasonCode(
                "DG-004",
                ReasonCodeStandard.DATAGOD,
                "Regulatory Non-Compliance",
                "Property or entity fails to meet regulatory requirements",
                "Varies by jurisdiction",
                ReasonCodeSeverity.HIGH,
                "regulatory",
                "Consult legal counsel for compliance plan",
                ["code_violation", "permit_issue", "zoning_violation"],
            ),
            ReasonCode(
                "DG-005",
                ReasonCodeStandard.DATAGOD,
                "Entity Verification Failed",
                "Owning entity could not be verified in public records",
                "State SOS Records",
                ReasonCodeSeverity.MEDIUM,
                "entity",
                "Verify entity registration with Secretary of State",
                ["entity_not_found", "entity_inactive"],
            ),
            ReasonCode(
                "DG-006",
                ReasonCodeStandard.DATAGOD,
                "Data Staleness Warning",
                "Underlying data is older than acceptable freshness threshold",
                "DataGod Data Quality Policy",
                ReasonCodeSeverity.LOW,
                "data_quality",
                "Request fresh data pull from source jurisdictions",
                ["stale_data"],
            ),
            ReasonCode(
                "DG-007",
                ReasonCodeStandard.DATAGOD,
                "Vacant Property Risk",
                "Property appears unoccupied, increasing risk profile",
                "Local Property Maintenance Code",
                ReasonCodeSeverity.LOW,
                "property",
                "Arrange property inspection and secure premises",
                ["vacant_property"],
            ),
            ReasonCode(
                "DG-008",
                ReasonCodeStandard.DATAGOD,
                "Distressed Property Flag",
                "Multiple indicators suggest property is in financial distress",
                "DataGod Risk Engine",
                ReasonCodeSeverity.HIGH,
                "risk",
                "Evaluate acquisition opportunity or risk mitigation",
                ["distress_indicators", "pre_foreclosure"],
            ),
        ]

        for code in fcra_codes + ecoa_codes + dg_codes:
            catalog[code.code] = code
            # Also index by blocker type for fast lookup
            for bt in code.applicable_blocker_types:
                catalog[f"blocker:{bt}"] = code

        return catalog

    def generate_codes(
        self,
        blockers: List[Dict[str, Any]],
        standard_filter: Optional[ReasonCodeStandard] = None,
    ) -> ReasonCodeResult:
        """
        Generate reason codes for a set of blockers.

        Args:
            blockers: List of blocker dicts (from BlockerUnlockerEngine)
            standard_filter: Optional filter to only return codes from a specific standard

        Returns:
            ReasonCodeResult with all applicable codes
        """
        codes = []
        seen_codes = set()

        for blocker in blockers:
            blocker_type = blocker.get("blocker_type", "")
            category = blocker.get("category", "")

            # Look up by blocker type
            key = f"blocker:{blocker_type}"
            if key in self._catalog:
                rc = self._catalog[key]
                if rc.code not in seen_codes:
                    if standard_filter is None or rc.standard == standard_filter:
                        codes.append(rc)
                        seen_codes.add(rc.code)

            # Also check by category keywords
            for code_id, rc in self._catalog.items():
                if not code_id.startswith("blocker:") and rc.code not in seen_codes:
                    if rc.category == category:
                        if standard_filter is None or rc.standard == standard_filter:
                            codes.append(rc)
                            seen_codes.add(rc.code)

        # Sort by severity
        severity_order = {
            ReasonCodeSeverity.CRITICAL: 0,
            ReasonCodeSeverity.HIGH: 1,
            ReasonCodeSeverity.MEDIUM: 2,
            ReasonCodeSeverity.LOW: 3,
            ReasonCodeSeverity.INFORMATIONAL: 4,
        }
        codes.sort(key=lambda c: severity_order.get(c.severity, 5))

        critical_count = sum(
            1 for c in codes if c.severity == ReasonCodeSeverity.CRITICAL
        )

        summary = (
            f"Generated {len(codes)} reason code(s) from {len(blockers)} blocker(s). "
            f"{critical_count} critical item(s) require immediate attention."
        )

        return ReasonCodeResult(
            codes=codes,
            total_codes=len(codes),
            critical_count=critical_count,
            summary=summary,
        )

    def get_code(self, code_id: str) -> Optional[ReasonCode]:
        """Look up a specific reason code by ID."""
        return self._catalog.get(code_id)

    def list_codes(
        self, standard: Optional[ReasonCodeStandard] = None
    ) -> List[ReasonCode]:
        """List all available reason codes, optionally filtered by standard."""
        codes = [
            rc
            for key, rc in self._catalog.items()
            if not key.startswith("blocker:")
            and (standard is None or rc.standard == standard)
        ]
        return codes
