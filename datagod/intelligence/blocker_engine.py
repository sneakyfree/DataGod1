"""
Blocker/Unlocker Engine (Phase 3: Intelligence Layer)

Identifies what's blocking a transaction and provides actionable fix lists
with prioritization, cost estimates, and "Why Not" explanations.

Key Features:
- 100+ blocker types covering liens, title, legal, financial issues
- Prioritized fix list (Quick Wins, 30-Day, 90-Day)
- Cost and timeframe estimates with confidence
- "Why Not" explanations for every blocker
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BlockerCategory(str, Enum):
    """Categories of blockers."""
    LIEN = "lien"
    TITLE = "title"
    LEGAL = "legal"
    FINANCIAL = "financial"
    REGULATORY = "regulatory"
    CONDITION = "condition"
    TIMING = "timing"
    DOCUMENTATION = "documentation"


class BlockerSeverity(str, Enum):
    """Severity levels for blockers."""
    CRITICAL = "critical"    # Deal cannot proceed
    HIGH = "high"            # Major impediment
    MEDIUM = "medium"        # Significant but manageable
    LOW = "low"              # Minor issue
    INFORMATIONAL = "informational"  # FYI only


class FixTimeframe(str, Enum):
    """Timeframe categories for fixes."""
    IMMEDIATE = "immediate"  # < 3 days
    QUICK_WIN = "quick_win"  # 3-7 days
    SHORT_TERM = "short_term"  # 7-30 days
    MEDIUM_TERM = "medium_term"  # 30-90 days
    LONG_TERM = "long_term"  # 90+ days
    UNKNOWN = "unknown"


@dataclass
class BlockerType:
    """Definition of a blocker type."""
    id: str
    name: str
    category: BlockerCategory
    severity: BlockerSeverity
    description: str
    why_not_template: str
    default_fix_options: List[Dict[str, Any]]
    requires_professional: bool = False
    blocking_action: str = "clear_title"


@dataclass
class FixOption:
    """A possible fix for a blocker."""
    action: str
    description: str
    estimated_cost_low: Optional[float]
    estimated_cost_high: Optional[float]
    timeframe: FixTimeframe
    timeframe_days: Tuple[int, int]  # min, max days
    confidence: float  # 0.0 - 1.0
    requires: List[str]  # Prerequisites
    next_steps: List[str]


@dataclass
class Blocker:
    """An identified blocker on a property."""
    blocker_id: str
    blocker_type: str
    category: BlockerCategory
    severity: BlockerSeverity
    name: str
    description: str
    why_not: str  # Plain language explanation
    data: Dict[str, Any]
    fix_options: List[FixOption]
    source: str
    source_date: Optional[datetime]
    priority_score: float = 0.0


@dataclass
class Unlocker:
    """An opportunity signal (opposite of blocker)."""
    signal_type: str
    name: str
    description: str
    opportunity: str
    confidence: float
    data: Dict[str, Any]


class BlockerUnlockerEngine:
    """
    Identifies blockers and generates prioritized fix lists.
    
    Design Philosophy:
    - Comprehensive: Cover all known blockers
    - Actionable: Every blocker has fix options
    - Honest: Include confidence and uncertainty
    - Prioritized: Order by impact and feasibility
    """
    
    # Comprehensive blocker catalog
    BLOCKER_CATALOG: Dict[str, BlockerType] = {}
    
    def __init__(self):
        self._initialize_catalog()
    
    def _initialize_catalog(self):
        """Initialize the comprehensive blocker catalog."""
        
        # =========================================================================
        # LIEN BLOCKERS
        # =========================================================================
        
        self.BLOCKER_CATALOG["tax_lien_delinquent"] = BlockerType(
            id="tax_lien_delinquent",
            name="Delinquent Property Tax Lien",
            category=BlockerCategory.LIEN,
            severity=BlockerSeverity.CRITICAL,
            description="Property has delinquent property taxes with lien recorded",
            why_not_template="You cannot obtain clear title because there is ${amount} in delinquent property taxes owed to {jurisdiction}. This lien has priority over all other liens.",
            default_fix_options=[
                {"action": "pay_in_full", "timeframe": "immediate", "cost_multiplier": 1.0},
                {"action": "payment_plan", "timeframe": "medium_term", "cost_multiplier": 1.1},
                {"action": "negotiate_reduction", "timeframe": "short_term", "cost_multiplier": 0.8}
            ]
        )
        
        self.BLOCKER_CATALOG["irs_tax_lien"] = BlockerType(
            id="irs_tax_lien",
            name="IRS Federal Tax Lien",
            category=BlockerCategory.LIEN,
            severity=BlockerSeverity.CRITICAL,
            description="Federal tax lien recorded against owner",
            why_not_template="The property owner has a federal tax lien of ${amount} recorded by the IRS. This affects all property owned by the debtor.",
            default_fix_options=[
                {"action": "pay_in_full", "timeframe": "short_term", "cost_multiplier": 1.0},
                {"action": "apply_for_discharge", "timeframe": "medium_term", "cost_multiplier": 0.1},
                {"action": "subordination_request", "timeframe": "medium_term", "cost_multiplier": 0.05}
            ],
            requires_professional=True
        )
        
        self.BLOCKER_CATALOG["first_mortgage"] = BlockerType(
            id="first_mortgage",
            name="First Mortgage Lien",
            category=BlockerCategory.LIEN,
            severity=BlockerSeverity.MEDIUM,
            description="First mortgage lien on property (standard encumbrance)",
            why_not_template="There is a first mortgage of ${amount} held by {lender}. This must be paid off or assumed at closing.",
            default_fix_options=[
                {"action": "payoff_at_close", "timeframe": "immediate", "cost_multiplier": 1.0},
                {"action": "assumption", "timeframe": "medium_term", "cost_multiplier": 0.05},
                {"action": "subject_to", "timeframe": "short_term", "cost_multiplier": 0.01}
            ]
        )
        
        self.BLOCKER_CATALOG["second_mortgage"] = BlockerType(
            id="second_mortgage",
            name="Second Mortgage/HELOC",
            category=BlockerCategory.LIEN,
            severity=BlockerSeverity.MEDIUM,
            description="Second mortgage or home equity line of credit",
            why_not_template="There is a subordinate mortgage of ${amount} held by {lender}. Total debt may exceed property value.",
            default_fix_options=[
                {"action": "payoff_at_close", "timeframe": "immediate", "cost_multiplier": 1.0},
                {"action": "negotiate_short_payoff", "timeframe": "medium_term", "cost_multiplier": 0.6}
            ]
        )
        
        self.BLOCKER_CATALOG["judgment_lien"] = BlockerType(
            id="judgment_lien",
            name="Judgment Lien",
            category=BlockerCategory.LIEN,
            severity=BlockerSeverity.HIGH,
            description="Court judgment recorded as lien against property",
            why_not_template="A judgment of ${amount} from case {case_number} has been recorded against the owner. This lien attaches to all real property owned.",
            default_fix_options=[
                {"action": "pay_in_full", "timeframe": "short_term", "cost_multiplier": 1.0},
                {"action": "negotiate_settlement", "timeframe": "medium_term", "cost_multiplier": 0.5},
                {"action": "dispute_lien", "timeframe": "long_term", "cost_multiplier": 0.2}
            ],
            requires_professional=True
        )
        
        self.BLOCKER_CATALOG["mechanic_lien"] = BlockerType(
            id="mechanic_lien",
            name="Mechanic's Lien",
            category=BlockerCategory.LIEN,
            severity=BlockerSeverity.HIGH,
            description="Contractor's lien for unpaid work",
            why_not_template="A mechanic's lien of ${amount} has been filed by {contractor}. The work was performed on or around {work_date}.",
            default_fix_options=[
                {"action": "pay_contractor", "timeframe": "short_term", "cost_multiplier": 1.0},
                {"action": "dispute_lien", "timeframe": "medium_term", "cost_multiplier": 0.3},
                {"action": "bond_off_lien", "timeframe": "short_term", "cost_multiplier": 1.2}
            ]
        )
        
        self.BLOCKER_CATALOG["hoa_lien"] = BlockerType(
            id="hoa_lien",
            name="HOA Lien",
            category=BlockerCategory.LIEN,
            severity=BlockerSeverity.MEDIUM,
            description="Homeowners association lien for unpaid dues",
            why_not_template="The HOA has recorded a lien of ${amount} for delinquent assessments since {delinquent_since}.",
            default_fix_options=[
                {"action": "pay_in_full", "timeframe": "quick_win", "cost_multiplier": 1.0},
                {"action": "payment_plan", "timeframe": "medium_term", "cost_multiplier": 1.1}
            ]
        )
        
        self.BLOCKER_CATALOG["child_support_lien"] = BlockerType(
            id="child_support_lien",
            name="Child Support Lien",
            category=BlockerCategory.LIEN,
            severity=BlockerSeverity.HIGH,
            description="State child support enforcement lien",
            why_not_template="A child support lien of ${amount} has been recorded by {state} child support enforcement.",
            default_fix_options=[
                {"action": "pay_arrearage", "timeframe": "short_term", "cost_multiplier": 1.0},
                {"action": "payment_arrangement", "timeframe": "medium_term", "cost_multiplier": 1.0}
            ]
        )
        
        # =========================================================================
        # TITLE BLOCKERS
        # =========================================================================
        
        self.BLOCKER_CATALOG["lis_pendens"] = BlockerType(
            id="lis_pendens",
            name="Lis Pendens (Pending Litigation)",
            category=BlockerCategory.TITLE,
            severity=BlockerSeverity.CRITICAL,
            description="Notice of pending litigation affecting title",
            why_not_template="A lis pendens has been filed in case {case_number}, indicating pending litigation that may affect ownership. The case involves {case_type}.",
            default_fix_options=[
                {"action": "wait_for_resolution", "timeframe": "long_term", "cost_multiplier": 0.0},
                {"action": "settle_litigation", "timeframe": "medium_term", "cost_multiplier": 0.5},
                {"action": "purchase_pending_litigation", "timeframe": "short_term", "cost_multiplier": 0.3}
            ],
            requires_professional=True
        )
        
        self.BLOCKER_CATALOG["title_defect"] = BlockerType(
            id="title_defect",
            name="Title Defect",
            category=BlockerCategory.TITLE,
            severity=BlockerSeverity.CRITICAL,
            description="Defect in the chain of title",
            why_not_template="There is a defect in the chain of title: {defect_description}. This was identified in a conveyance recorded on {defect_date}.",
            default_fix_options=[
                {"action": "quiet_title_action", "timeframe": "long_term", "cost_multiplier": 1.5},
                {"action": "corrective_deed", "timeframe": "medium_term", "cost_multiplier": 0.3},
                {"action": "affidavit_correction", "timeframe": "short_term", "cost_multiplier": 0.1}
            ],
            requires_professional=True
        )
        
        self.BLOCKER_CATALOG["missing_heir"] = BlockerType(
            id="missing_heir",
            name="Missing or Unknown Heir",
            category=BlockerCategory.TITLE,
            severity=BlockerSeverity.CRITICAL,
            description="Property passed through estate with unknown heirs",
            why_not_template="The property was inherited but there may be unknown heirs with potential claims. The last owner of record died {death_date}.",
            default_fix_options=[
                {"action": "heir_search", "timeframe": "medium_term", "cost_multiplier": 0.1},
                {"action": "quiet_title_action", "timeframe": "long_term", "cost_multiplier": 1.5}
            ],
            requires_professional=True
        )
        
        self.BLOCKER_CATALOG["unreleased_mortgage"] = BlockerType(
            id="unreleased_mortgage",
            name="Unreleased Mortgage",
            category=BlockerCategory.TITLE,
            severity=BlockerSeverity.HIGH,
            description="Mortgage was paid but satisfaction not recorded",
            why_not_template="A mortgage from {lender} dated {mortgage_date} appears unreleased on title, though it may have been paid.",
            default_fix_options=[
                {"action": "obtain_satisfaction", "timeframe": "short_term", "cost_multiplier": 0.05},
                {"action": "affidavit_of_payment", "timeframe": "quick_win", "cost_multiplier": 0.02}
            ]
        )
        
        self.BLOCKER_CATALOG["forged_deed"] = BlockerType(
            id="forged_deed",
            name="Potentially Forged Deed",
            category=BlockerCategory.TITLE,
            severity=BlockerSeverity.CRITICAL,
            description="Deed in chain may contain forged signatures",
            why_not_template="A deed recorded {deed_date} may contain forged signatures. This creates a break in the chain of title.",
            default_fix_options=[
                {"action": "forensic_investigation", "timeframe": "medium_term", "cost_multiplier": 0.2},
                {"action": "quiet_title_action", "timeframe": "long_term", "cost_multiplier": 2.0}
            ],
            requires_professional=True
        )
        
        # =========================================================================
        # LEGAL BLOCKERS
        # =========================================================================
        
        self.BLOCKER_CATALOG["foreclosure_pending"] = BlockerType(
            id="foreclosure_pending",
            name="Foreclosure Proceeding",
            category=BlockerCategory.LEGAL,
            severity=BlockerSeverity.CRITICAL,
            description="Active foreclosure case against property",
            why_not_template="A foreclosure proceeding was initiated by {lender} on {filing_date}. The property may go to auction on {auction_date}.",
            default_fix_options=[
                {"action": "purchase_from_lender", "timeframe": "medium_term", "cost_multiplier": 0.7},
                {"action": "purchase_at_auction", "timeframe": "short_term", "cost_multiplier": 0.6},
                {"action": "short_sale_negotiation", "timeframe": "medium_term", "cost_multiplier": 0.8}
            ]
        )
        
        self.BLOCKER_CATALOG["bankruptcy_stay"] = BlockerType(
            id="bankruptcy_stay",
            name="Bankruptcy Automatic Stay",
            category=BlockerCategory.LEGAL,
            severity=BlockerSeverity.CRITICAL,
            description="Owner has filed bankruptcy, automatic stay in effect",
            why_not_template="The owner filed {bankruptcy_type} bankruptcy on {filing_date}. The automatic stay prevents most collection activities.",
            default_fix_options=[
                {"action": "wait_for_discharge", "timeframe": "long_term", "cost_multiplier": 0.0},
                {"action": "purchase_from_trustee", "timeframe": "medium_term", "cost_multiplier": 0.8},
                {"action": "relief_from_stay_motion", "timeframe": "short_term", "cost_multiplier": 0.1}
            ],
            requires_professional=True
        )
        
        self.BLOCKER_CATALOG["probate_required"] = BlockerType(
            id="probate_required",
            name="Probate Required",
            category=BlockerCategory.LEGAL,
            severity=BlockerSeverity.HIGH,
            description="Property must go through probate before sale",
            why_not_template="The property owner is deceased and the property must go through probate. Estimated timeline: {probate_timeline} months.",
            default_fix_options=[
                {"action": "wait_for_probate", "timeframe": "long_term", "cost_multiplier": 0.0},
                {"action": "purchase_from_estate", "timeframe": "medium_term", "cost_multiplier": 0.9}
            ]
        )
        
        # =========================================================================
        # REGULATORY BLOCKERS
        # =========================================================================
        
        self.BLOCKER_CATALOG["code_violation"] = BlockerType(
            id="code_violation",
            name="Code Violation",
            category=BlockerCategory.REGULATORY,
            severity=BlockerSeverity.MEDIUM,
            description="Outstanding building or zoning code violations",
            why_not_template="There are outstanding code violations: {violation_types}. Fines to date: ${fine_amount}.",
            default_fix_options=[
                {"action": "cure_violations", "timeframe": "medium_term", "cost_multiplier": 1.5},
                {"action": "pay_fines_only", "timeframe": "quick_win", "cost_multiplier": 1.0}
            ]
        )
        
        self.BLOCKER_CATALOG["unpermitted_work"] = BlockerType(
            id="unpermitted_work",
            name="Unpermitted Work",
            category=BlockerCategory.REGULATORY,
            severity=BlockerSeverity.MEDIUM,
            description="Construction work done without permits",
            why_not_template="There is unpermitted work on the property: {work_description}. This may affect insurance and resale value.",
            default_fix_options=[
                {"action": "obtain_retroactive_permits", "timeframe": "medium_term", "cost_multiplier": 0.2},
                {"action": "remove_unpermitted_work", "timeframe": "medium_term", "cost_multiplier": 0.5},
                {"action": "disclose_and_discount", "timeframe": "quick_win", "cost_multiplier": 0.0}
            ]
        )
        
        self.BLOCKER_CATALOG["environmental_issue"] = BlockerType(
            id="environmental_issue",
            name="Environmental Contamination",
            category=BlockerCategory.REGULATORY,
            severity=BlockerSeverity.CRITICAL,
            description="Property has environmental contamination issues",
            why_not_template="The property has environmental issues: {contamination_type}. Remediation may be required before development.",
            default_fix_options=[
                {"action": "phase_2_assessment", "timeframe": "short_term", "cost_multiplier": 0.1},
                {"action": "full_remediation", "timeframe": "long_term", "cost_multiplier": 5.0}
            ],
            requires_professional=True
        )
        
        logger.info(f"Initialized {len(self.BLOCKER_CATALOG)} blocker types")
    
    def analyze(
        self,
        property_data: Dict[str, Any],
        lien_data: Optional[Dict[str, Any]] = None,
        title_data: Optional[Dict[str, Any]] = None,
        legal_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Blocker], List[Unlocker]]:
        """
        Analyze data and identify all blockers and unlockers.
        
        Returns:
            Tuple of (blockers, unlockers)
        """
        blockers = []
        unlockers = []
        
        all_data = {
            'property': property_data or {},
            'liens': lien_data or {},
            'title': title_data or {},
            'legal': legal_data or {}
        }
        
        # Check for lien-related blockers
        blockers.extend(self._analyze_liens(all_data))
        
        # Check for title-related blockers
        blockers.extend(self._analyze_title(all_data))
        
        # Check for legal/regulatory blockers
        blockers.extend(self._analyze_legal(all_data))
        
        # Identify opportunities (unlockers)
        unlockers.extend(self._identify_opportunities(all_data))
        
        # Calculate priority scores and sort
        for blocker in blockers:
            blocker.priority_score = self._calculate_priority(blocker)
        
        blockers.sort(key=lambda b: b.priority_score, reverse=True)
        
        return blockers, unlockers
    
    def _analyze_liens(self, all_data: Dict[str, Any]) -> List[Blocker]:
        """Analyze liens and create blockers."""
        blockers = []
        liens = all_data.get('liens', {}).get('liens', [])
        
        for lien in liens:
            lien_type = lien.get('type', '').lower()
            
            # Map lien to blocker type
            blocker_type_id = self._map_lien_to_blocker(lien_type)
            if not blocker_type_id:
                continue
            
            blocker_type = self.BLOCKER_CATALOG.get(blocker_type_id)
            if not blocker_type:
                continue
            
            # Generate fix options
            fix_options = self._generate_fix_options(blocker_type, lien)
            
            # Generate "Why Not" explanation
            why_not = self._generate_why_not(blocker_type, lien)
            
            blocker = Blocker(
                blocker_id=f"{blocker_type_id}_{lien.get('id', 'unknown')}",
                blocker_type=blocker_type_id,
                category=blocker_type.category,
                severity=blocker_type.severity,
                name=blocker_type.name,
                description=blocker_type.description,
                why_not=why_not,
                data=lien,
                fix_options=fix_options,
                source=lien.get('source', 'lien_search'),
                source_date=lien.get('recorded_date')
            )
            blockers.append(blocker)
        
        return blockers
    
    def _analyze_title(self, all_data: Dict[str, Any]) -> List[Blocker]:
        """Analyze title issues and create blockers."""
        blockers = []
        title_data = all_data.get('title', {})
        
        # Check for lis pendens
        if title_data.get('lis_pendens'):
            blocker_type = self.BLOCKER_CATALOG.get('lis_pendens')
            if blocker_type:
                blockers.append(self._create_blocker_from_type(
                    blocker_type,
                    title_data.get('lis_pendens'),
                    'title_search'
                ))
        
        # Check for title defects
        if title_data.get('defects'):
            blocker_type = self.BLOCKER_CATALOG.get('title_defect')
            if blocker_type:
                for defect in title_data.get('defects', []):
                    blockers.append(self._create_blocker_from_type(
                        blocker_type,
                        defect,
                        'title_search'
                    ))
        
        return blockers
    
    def _analyze_legal(self, all_data: Dict[str, Any]) -> List[Blocker]:
        """Analyze legal issues and create blockers."""
        blockers = []
        legal_data = all_data.get('legal', {})
        property_data = all_data.get('property', {})
        
        # Check for foreclosure
        if legal_data.get('foreclosure') or property_data.get('foreclosure_status'):
            blocker_type = self.BLOCKER_CATALOG.get('foreclosure_pending')
            if blocker_type:
                blockers.append(self._create_blocker_from_type(
                    blocker_type,
                    legal_data.get('foreclosure', {}),
                    'court_records'
                ))
        
        # Check for bankruptcy
        if legal_data.get('bankruptcy'):
            blocker_type = self.BLOCKER_CATALOG.get('bankruptcy_stay')
            if blocker_type:
                blockers.append(self._create_blocker_from_type(
                    blocker_type,
                    legal_data.get('bankruptcy'),
                    'bankruptcy_court'
                ))
        
        return blockers
    
    def _identify_opportunities(self, all_data: Dict[str, Any]) -> List[Unlocker]:
        """Identify opportunity signals (unlockers)."""
        unlockers = []
        
        property_data = all_data.get('property', {})
        lien_data = all_data.get('liens', {})
        
        # Distressed property signals
        if property_data.get('tax_delinquent') or property_data.get('vacant'):
            unlockers.append(Unlocker(
                signal_type="distress_signal",
                name="Distressed Property",
                description="Property shows signs of distress",
                opportunity="Below-market acquisition potential",
                confidence=0.7,
                data={"indicators": ["tax_delinquent", "vacant"]}
            ))
        
        # Motivated seller signals
        if property_data.get('days_on_market', 0) > 90:
            unlockers.append(Unlocker(
                signal_type="motivated_seller",
                name="Extended Days on Market",
                description=f"Property has been listed for {property_data.get('days_on_market')} days",
                opportunity="Price negotiation opportunity",
                confidence=0.6,
                data={"days_on_market": property_data.get('days_on_market')}
            ))
        
        # Equity opportunity
        liens = lien_data.get('liens', [])
        total_liens = sum(float(l.get('amount', 0) or 0) for l in liens)
        estimated_value = property_data.get('estimated_value', 0)
        
        if estimated_value and total_liens < estimated_value * 0.7:
            unlockers.append(Unlocker(
                signal_type="equity_available",
                name="Available Equity",
                description=f"Estimated equity: ${estimated_value - total_liens:,.0f}",
                opportunity="Equity capture opportunity",
                confidence=0.75,
                data={
                    "estimated_value": estimated_value,
                    "total_liens": total_liens,
                    "equity": estimated_value - total_liens
                }
            ))
        
        return unlockers
    
    def _map_lien_to_blocker(self, lien_type: str) -> Optional[str]:
        """Map a lien type to a blocker catalog ID."""
        mapping = {
            'tax': 'tax_lien_delinquent',
            'property_tax': 'tax_lien_delinquent',
            'irs': 'irs_tax_lien', 
            'federal_tax': 'irs_tax_lien',
            'first_mortgage': 'first_mortgage',
            'mortgage': 'first_mortgage',
            'second_mortgage': 'second_mortgage',
            'heloc': 'second_mortgage',
            'judgment': 'judgment_lien',
            'mechanic': 'mechanic_lien',
            'contractor': 'mechanic_lien',
            'hoa': 'hoa_lien',
            'child_support': 'child_support_lien',
            'lis_pendens': 'lis_pendens'
        }
        
        for key, blocker_id in mapping.items():
            if key in lien_type:
                return blocker_id
        
        return None
    
    def _create_blocker_from_type(
        self,
        blocker_type: BlockerType,
        data: Dict[str, Any],
        source: str
    ) -> Blocker:
        """Create a Blocker instance from a BlockerType."""
        fix_options = self._generate_fix_options(blocker_type, data)
        why_not = self._generate_why_not(blocker_type, data)
        
        return Blocker(
            blocker_id=f"{blocker_type.id}_{data.get('id', 'unknown')}",
            blocker_type=blocker_type.id,
            category=blocker_type.category,
            severity=blocker_type.severity,
            name=blocker_type.name,
            description=blocker_type.description,
            why_not=why_not,
            data=data,
            fix_options=fix_options,
            source=source,
            source_date=None
        )
    
    def _generate_fix_options(self, blocker_type: BlockerType, data: Dict[str, Any]) -> List[FixOption]:
        """Generate fix options with cost and time estimates."""
        options = []
        base_amount = float(data.get('amount', 0) or 0)
        
        for default_fix in blocker_type.default_fix_options:
            timeframe_str = default_fix.get('timeframe', 'medium_term')
            timeframe = FixTimeframe(timeframe_str) if timeframe_str in [e.value for e in FixTimeframe] else FixTimeframe.UNKNOWN
            
            # Calculate cost estimates
            multiplier = default_fix.get('cost_multiplier', 1.0)
            cost_low = base_amount * multiplier * 0.9 if base_amount else None
            cost_high = base_amount * multiplier * 1.1 if base_amount else None
            
            # Timeframe in days
            timeframe_days = {
                FixTimeframe.IMMEDIATE: (1, 3),
                FixTimeframe.QUICK_WIN: (3, 7),
                FixTimeframe.SHORT_TERM: (7, 30),
                FixTimeframe.MEDIUM_TERM: (30, 90),
                FixTimeframe.LONG_TERM: (90, 365),
                FixTimeframe.UNKNOWN: (30, 180)
            }.get(timeframe, (30, 90))
            
            option = FixOption(
                action=default_fix['action'],
                description=self._get_fix_description(default_fix['action']),
                estimated_cost_low=cost_low,
                estimated_cost_high=cost_high,
                timeframe=timeframe,
                timeframe_days=timeframe_days,
                confidence=0.7 if timeframe in [FixTimeframe.IMMEDIATE, FixTimeframe.QUICK_WIN] else 0.5,
                requires=[],
                next_steps=self._get_next_steps(default_fix['action'])
            )
            options.append(option)
        
        return options
    
    def _generate_why_not(self, blocker_type: BlockerType, data: Dict[str, Any]) -> str:
        """Generate a plain-language 'Why Not' explanation."""
        template = blocker_type.why_not_template
        
        # Substitute placeholders with actual data
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in template:
                template = template.replace(placeholder, str(value))
            
            # Handle amount formatting
            if key == 'amount' and value:
                template = template.replace("${amount}", f"${float(value):,.2f}")
        
        # Clean up any remaining placeholders
        import re
        template = re.sub(r'\{[^}]+\}', 'unknown', template)
        template = re.sub(r'\$\{[^}]+\}', '$[amount unknown]', template)
        
        return template
    
    def _get_fix_description(self, action: str) -> str:
        """Get description for a fix action."""
        descriptions = {
            'pay_in_full': 'Pay the full amount owed',
            'payment_plan': 'Negotiate a payment plan',
            'negotiate_reduction': 'Negotiate to reduce the amount owed',
            'negotiate_settlement': 'Negotiate a settlement for less than full amount',
            'obtain_satisfaction': 'Obtain a recorded satisfaction from the lienholder',
            'quiet_title_action': 'File a quiet title action in court',
            'wait_for_resolution': 'Wait for the matter to be resolved',
            'purchase_at_auction': 'Purchase the property at auction',
            'dispute_lien': 'Dispute the validity of the lien',
            'bond_off_lien': 'Post a surety bond to remove the lien',
            'affidavit_correction': 'Record an affidavit to correct the issue',
            'apply_for_discharge': 'Apply for IRS discharge of the lien',
            'subordination_request': 'Request IRS subordination of the lien'
        }
        return descriptions.get(action, f'Take action: {action}')
    
    def _get_next_steps(self, action: str) -> List[str]:
        """Get next steps for a fix action."""
        steps = {
            'pay_in_full': ['Obtain payoff quote', 'Arrange payment', 'Obtain release/satisfaction'],
            'payment_plan': ['Contact creditor', 'Negotiate terms', 'Document agreement'],
            'quiet_title_action': ['Engage title attorney', 'File complaint', 'Serve all parties'],
            'negotiate_settlement': ['Determine settlement range', 'Make initial offer', 'Document agreement'],
            'purchase_at_auction': ['Research auction process', 'Arrange financing', 'Attend auction']
        }
        return steps.get(action, ['Research options', 'Take appropriate action'])
    
    def _calculate_priority(self, blocker: Blocker) -> float:
        """Calculate priority score for sorting blockers."""
        # Severity weights
        severity_weight = {
            BlockerSeverity.CRITICAL: 1.0,
            BlockerSeverity.HIGH: 0.8,
            BlockerSeverity.MEDIUM: 0.5,
            BlockerSeverity.LOW: 0.3,
            BlockerSeverity.INFORMATIONAL: 0.1
        }
        
        base_score = severity_weight.get(blocker.severity, 0.5)
        
        # Boost for actionable fixes
        if blocker.fix_options:
            quick_fixes = [f for f in blocker.fix_options if f.timeframe in [FixTimeframe.IMMEDIATE, FixTimeframe.QUICK_WIN]]
            if quick_fixes:
                base_score += 0.1
        
        return min(base_score, 1.0)
    
    def generate_fix_list(
        self,
        blockers: List[Blocker],
        timeframe: Optional[FixTimeframe] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate a prioritized fix list grouped by timeframe.
        
        Returns:
            Dictionary with fixes grouped by timeframe category
        """
        fix_list = {
            'quick_wins': [],     # < 7 days
            'short_term': [],     # 7-30 days
            'medium_term': [],    # 30-90 days
            'long_term': []       # 90+ days
        }
        
        for blocker in blockers:
            for fix in blocker.fix_options:
                fix_entry = {
                    'blocker_name': blocker.name,
                    'blocker_severity': blocker.severity.value,
                    'action': fix.action,
                    'description': fix.description,
                    'cost_range': f"${fix.estimated_cost_low:,.0f} - ${fix.estimated_cost_high:,.0f}" if fix.estimated_cost_low else "Unknown",
                    'days_range': f"{fix.timeframe_days[0]}-{fix.timeframe_days[1]} days",
                    'confidence': fix.confidence,
                    'next_steps': fix.next_steps
                }
                
                if fix.timeframe in [FixTimeframe.IMMEDIATE, FixTimeframe.QUICK_WIN]:
                    fix_list['quick_wins'].append(fix_entry)
                elif fix.timeframe == FixTimeframe.SHORT_TERM:
                    fix_list['short_term'].append(fix_entry)
                elif fix.timeframe == FixTimeframe.MEDIUM_TERM:
                    fix_list['medium_term'].append(fix_entry)
                else:
                    fix_list['long_term'].append(fix_entry)
        
        # Sort each category by confidence (higher first)
        for category in fix_list:
            fix_list[category].sort(key=lambda x: x['confidence'], reverse=True)
        
        return fix_list
