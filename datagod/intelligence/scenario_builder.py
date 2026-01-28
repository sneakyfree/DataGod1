"""
Scenario Universe Builder (Phase 3: Intelligence Layer)

Exhaustively enumerates all possible scenarios for a property or entity,
providing ranked opportunities with confidence scoring.

Key Features:
- 50+ scenario types covering acquisitions, liens, risks, opportunities
- Honest uncertainty labeling for data gaps
- Source-labeled findings with timestamps
- Ranked scenarios by relevance and actionability
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import uuid

logger = logging.getLogger(__name__)


class ScenarioCategory(str, Enum):
    """Categories of scenarios."""
    ACQUISITION = "acquisition"
    LIEN = "lien"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    ENTITY = "entity"
    COMPLIANCE = "compliance"
    DISTRESS = "distress"


class ScenarioConfidence(str, Enum):
    """Confidence levels for scenario applicability."""
    CONFIRMED = "confirmed"      # Data clearly supports
    LIKELY = "likely"            # Strong indicators
    POSSIBLE = "possible"        # Some indicators
    SPECULATIVE = "speculative"  # Weak indicators
    UNKNOWN = "unknown"          # Insufficient data


@dataclass
class ScenarioType:
    """Definition of a scenario type."""
    id: str
    name: str
    category: ScenarioCategory
    description: str
    required_data: List[str]
    indicators: List[str]
    risk_level: str = "medium"
    actionable: bool = True


@dataclass
class ScenarioResult:
    """Result of scenario analysis."""
    scenario_id: str
    scenario_name: str
    category: ScenarioCategory
    confidence: ScenarioConfidence
    confidence_score: float  # 0.0 - 1.0
    description: str
    evidence: List[Dict[str, Any]]
    missing_data: List[str]
    recommended_actions: List[str]
    source_labels: List[Dict[str, str]]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ScenarioUniverseBuilder:
    """
    Builds the complete universe of possible scenarios for a property or entity.
    
    Design Philosophy:
    - Exhaustive: Cover all possible scenarios, not just obvious ones
    - Honest: Label unknowns clearly, never invent data
    - Ranked: Order by relevance, confidence, and actionability
    - Sourced: Every finding has a source label
    """
    
    # Comprehensive scenario taxonomy
    SCENARIO_TAXONOMY: Dict[str, ScenarioType] = {}
    
    def __init__(self):
        self._initialize_taxonomy()
        self._analysis_cache: Dict[str, List[ScenarioResult]] = {}
    
    def _initialize_taxonomy(self):
        """Initialize the comprehensive scenario taxonomy."""
        
        # =========================================================================
        # ACQUISITION SCENARIOS
        # =========================================================================
        
        self.SCENARIO_TAXONOMY["traditional_sale"] = ScenarioType(
            id="traditional_sale",
            name="Traditional Market Sale",
            category=ScenarioCategory.ACQUISITION,
            description="Property available through standard market listing",
            required_data=["property_status", "listing_info"],
            indicators=["active_listing", "mls_status"],
            risk_level="low"
        )
        
        self.SCENARIO_TAXONOMY["foreclosure_auction"] = ScenarioType(
            id="foreclosure_auction",
            name="Foreclosure Auction",
            category=ScenarioCategory.ACQUISITION,
            description="Property going to foreclosure auction",
            required_data=["foreclosure_status", "auction_date", "lis_pendens"],
            indicators=["notice_of_default", "auction_scheduled"],
            risk_level="high"
        )
        
        self.SCENARIO_TAXONOMY["tax_sale"] = ScenarioType(
            id="tax_sale",
            name="Tax Sale/Tax Deed",
            category=ScenarioCategory.ACQUISITION,
            description="Property eligible for tax sale due to delinquent taxes",
            required_data=["tax_status", "delinquency_amount", "redemption_period"],
            indicators=["tax_delinquent", "years_delinquent"],
            risk_level="high"
        )
        
        self.SCENARIO_TAXONOMY["reo_acquisition"] = ScenarioType(
            id="reo_acquisition",
            name="REO/Bank-Owned Property",
            category=ScenarioCategory.ACQUISITION,
            description="Property owned by lender after foreclosure",
            required_data=["reo_status", "lender_info"],
            indicators=["bank_owned", "post_foreclosure"],
            risk_level="medium"
        )
        
        self.SCENARIO_TAXONOMY["short_sale"] = ScenarioType(
            id="short_sale",
            name="Short Sale",
            category=ScenarioCategory.ACQUISITION,
            description="Sale for less than mortgage balance with lender approval",
            required_data=["loan_balance", "estimated_value", "lender_approval"],
            indicators=["underwater", "lender_negotiation"],
            risk_level="medium"
        )
        
        self.SCENARIO_TAXONOMY["probate_sale"] = ScenarioType(
            id="probate_sale",
            name="Probate Sale",
            category=ScenarioCategory.ACQUISITION,
            description="Property being sold through probate court",
            required_data=["probate_status", "estate_info"],
            indicators=["death_of_owner", "probate_filing"],
            risk_level="medium"
        )
        
        self.SCENARIO_TAXONOMY["divorce_sale"] = ScenarioType(
            id="divorce_sale",
            name="Divorce/Partition Sale",
            category=ScenarioCategory.ACQUISITION,
            description="Property being sold due to divorce or ownership dispute",
            required_data=["court_records", "ownership_dispute"],
            indicators=["lis_pendens_divorce", "partition_action"],
            risk_level="medium"
        )
        
        self.SCENARIO_TAXONOMY["wholesale_deal"] = ScenarioType(
            id="wholesale_deal",
            name="Wholesale Opportunity",
            category=ScenarioCategory.ACQUISITION,
            description="Property suitable for wholesale assignment",
            required_data=["arv", "repair_cost", "owner_motivation"],
            indicators=["distressed", "motivated_seller"],
            risk_level="low"
        )
        
        # =========================================================================
        # LIEN SCENARIOS
        # =========================================================================
        
        self.SCENARIO_TAXONOMY["clear_title"] = ScenarioType(
            id="clear_title",
            name="Clear Title",
            category=ScenarioCategory.LIEN,
            description="No significant liens or encumbrances",
            required_data=["lien_search", "title_search"],
            indicators=["no_liens", "clean_title"],
            risk_level="low"
        )
        
        self.SCENARIO_TAXONOMY["first_mortgage_only"] = ScenarioType(
            id="first_mortgage_only",
            name="First Mortgage Only",
            category=ScenarioCategory.LIEN,
            description="Standard first mortgage with no subordinate liens",
            required_data=["mortgage_info", "lien_search"],
            indicators=["single_mortgage", "no_subordinate"],
            risk_level="low"
        )
        
        self.SCENARIO_TAXONOMY["multiple_mortgages"] = ScenarioType(
            id="multiple_mortgages",
            name="Multiple Mortgages",
            category=ScenarioCategory.LIEN,
            description="Property has multiple mortgage liens",
            required_data=["mortgage_info", "subordinate_liens"],
            indicators=["second_mortgage", "heloc"],
            risk_level="medium"
        )
        
        self.SCENARIO_TAXONOMY["judgment_lien_present"] = ScenarioType(
            id="judgment_lien_present",
            name="Judgment Lien Present",
            category=ScenarioCategory.LIEN,
            description="Judgment lien recorded against property or owner",
            required_data=["judgment_search", "court_records"],
            indicators=["judgment_filed", "creditor_action"],
            risk_level="high"
        )
        
        self.SCENARIO_TAXONOMY["mechanic_lien_present"] = ScenarioType(
            id="mechanic_lien_present",
            name="Mechanic's Lien Present",
            category=ScenarioCategory.LIEN,
            description="Mechanic's or contractor's lien on property",
            required_data=["lien_search", "contractor_records"],
            indicators=["construction_work", "unpaid_contractor"],
            risk_level="medium"
        )
        
        self.SCENARIO_TAXONOMY["irs_tax_lien"] = ScenarioType(
            id="irs_tax_lien",
            name="IRS Tax Lien",
            category=ScenarioCategory.LIEN,
            description="Federal tax lien filed against owner",
            required_data=["federal_lien_search"],
            indicators=["irs_filing", "federal_tax_debt"],
            risk_level="high"
        )
        
        self.SCENARIO_TAXONOMY["hoa_lien"] = ScenarioType(
            id="hoa_lien",
            name="HOA Lien",
            category=ScenarioCategory.LIEN,
            description="Homeowners association lien for unpaid dues",
            required_data=["hoa_records", "lien_search"],
            indicators=["delinquent_dues", "hoa_filing"],
            risk_level="medium"
        )
        
        # =========================================================================
        # RISK SCENARIOS
        # =========================================================================
        
        self.SCENARIO_TAXONOMY["title_defect"] = ScenarioType(
            id="title_defect",
            name="Title Defect",
            category=ScenarioCategory.RISK,
            description="Defect in title chain that may affect ownership",
            required_data=["title_search", "deed_history"],
            indicators=["gap_in_chain", "improper_conveyance"],
            risk_level="critical"
        )
        
        self.SCENARIO_TAXONOMY["pending_litigation"] = ScenarioType(
            id="pending_litigation",
            name="Pending Litigation",
            category=ScenarioCategory.RISK,
            description="Active lawsuit involving the property",
            required_data=["lis_pendens", "court_records"],
            indicators=["lis_pendens_filed", "lawsuit_pending"],
            risk_level="high"
        )
        
        self.SCENARIO_TAXONOMY["environmental_issue"] = ScenarioType(
            id="environmental_issue",
            name="Environmental Issue",
            category=ScenarioCategory.RISK,
            description="Environmental contamination or concern",
            required_data=["environmental_records", "epa_database"],
            indicators=["contamination", "hazardous_site"],
            risk_level="critical"
        )
        
        self.SCENARIO_TAXONOMY["code_violations"] = ScenarioType(
            id="code_violations",
            name="Code Violations",
            category=ScenarioCategory.RISK,
            description="Outstanding building or zoning code violations",
            required_data=["code_enforcement", "permit_records"],
            indicators=["violation_notice", "unpermitted_work"],
            risk_level="medium"
        )
        
        self.SCENARIO_TAXONOMY["boundary_dispute"] = ScenarioType(
            id="boundary_dispute",
            name="Boundary Dispute",
            category=ScenarioCategory.RISK,
            description="Dispute over property boundaries or encroachment",
            required_data=["survey_records", "court_records"],
            indicators=["encroachment", "boundary_litigation"],
            risk_level="medium"
        )
        
        # =========================================================================
        # OPPORTUNITY SCENARIOS
        # =========================================================================
        
        self.SCENARIO_TAXONOMY["below_market_value"] = ScenarioType(
            id="below_market_value",
            name="Below Market Value",
            category=ScenarioCategory.OPPORTUNITY,
            description="Property priced significantly below market value",
            required_data=["estimated_value", "asking_price", "comparables"],
            indicators=["price_discount", "motivated_seller"],
            risk_level="low"
        )
        
        self.SCENARIO_TAXONOMY["value_add_potential"] = ScenarioType(
            id="value_add_potential",
            name="Value-Add Potential",
            category=ScenarioCategory.OPPORTUNITY,
            description="Property has significant improvement potential",
            required_data=["property_condition", "arv", "repair_estimate"],
            indicators=["deferred_maintenance", "renovation_upside"],
            risk_level="medium"
        )
        
        self.SCENARIO_TAXONOMY["rental_opportunity"] = ScenarioType(
            id="rental_opportunity",
            name="Rental Income Opportunity",
            category=ScenarioCategory.OPPORTUNITY,
            description="Property suitable for rental income",
            required_data=["rental_rates", "vacancy_rates", "property_type"],
            indicators=["positive_cash_flow", "rental_demand"],
            risk_level="low"
        )
        
        self.SCENARIO_TAXONOMY["development_potential"] = ScenarioType(
            id="development_potential",
            name="Development Potential",
            category=ScenarioCategory.OPPORTUNITY,
            description="Land or property with development/redevelopment potential",
            required_data=["zoning", "lot_size", "development_rights"],
            indicators=["underutilized", "rezoning_potential"],
            risk_level="high"
        )
        
        # =========================================================================
        # DISTRESS SCENARIOS
        # =========================================================================
        
        self.SCENARIO_TAXONOMY["pre_foreclosure"] = ScenarioType(
            id="pre_foreclosure",
            name="Pre-Foreclosure",
            category=ScenarioCategory.DISTRESS,
            description="Owner in default but foreclosure not yet completed",
            required_data=["default_notice", "loan_status"],
            indicators=["notice_of_default", "missed_payments"],
            risk_level="medium"
        )
        
        self.SCENARIO_TAXONOMY["owner_bankruptcy"] = ScenarioType(
            id="owner_bankruptcy",
            name="Owner Bankruptcy",
            category=ScenarioCategory.DISTRESS,
            description="Property owner has filed for bankruptcy",
            required_data=["bankruptcy_filing", "court_records"],
            indicators=["chapter_7", "chapter_13", "bankruptcy_stay"],
            risk_level="high"
        )
        
        self.SCENARIO_TAXONOMY["abandoned_property"] = ScenarioType(
            id="abandoned_property",
            name="Abandoned Property",
            category=ScenarioCategory.DISTRESS,
            description="Property appears to be abandoned",
            required_data=["vacancy_indicators", "utility_status"],
            indicators=["vacant", "utilities_off", "mail_accumulation"],
            risk_level="medium"
        )
        
        self.SCENARIO_TAXONOMY["estate_distress"] = ScenarioType(
            id="estate_distress",
            name="Estate/Probate Distress",
            category=ScenarioCategory.DISTRESS,
            description="Property in distressed probate situation",
            required_data=["probate_status", "estate_debts"],
            indicators=["inherited_debt", "estate_taxes"],
            risk_level="medium"
        )
        
        logger.info(f"Initialized {len(self.SCENARIO_TAXONOMY)} scenario types")
    
    async def analyze(
        self,
        property_data: Dict[str, Any],
        entity_data: Optional[Dict[str, Any]] = None,
        lien_data: Optional[Dict[str, Any]] = None,
        risk_data: Optional[Dict[str, Any]] = None
    ) -> List[ScenarioResult]:
        """
        Analyze all available data and generate the scenario universe.
        
        Args:
            property_data: Property information
            entity_data: Owner/entity information
            lien_data: Lien and encumbrance data
            risk_data: Risk assessment data
        
        Returns:
            List of applicable scenarios, ranked by confidence and relevance
        """
        all_data = {
            'property': property_data or {},
            'entity': entity_data or {},
            'liens': lien_data or {},
            'risks': risk_data or {}
        }
        
        scenarios = []
        
        for scenario_id, scenario_type in self.SCENARIO_TAXONOMY.items():
            result = self._evaluate_scenario(scenario_type, all_data)
            if result:
                scenarios.append(result)
        
        # Sort by confidence score (highest first), then by category priority
        category_priority = {
            ScenarioCategory.DISTRESS: 1,
            ScenarioCategory.OPPORTUNITY: 2,
            ScenarioCategory.ACQUISITION: 3,
            ScenarioCategory.RISK: 4,
            ScenarioCategory.LIEN: 5,
            ScenarioCategory.ENTITY: 6,
            ScenarioCategory.COMPLIANCE: 7
        }
        
        scenarios.sort(
            key=lambda s: (-s.confidence_score, category_priority.get(s.category, 99))
        )
        
        return scenarios
    
    def _evaluate_scenario(
        self,
        scenario_type: ScenarioType,
        all_data: Dict[str, Any]
    ) -> Optional[ScenarioResult]:
        """Evaluate if a scenario applies to the given data."""
        
        # Check for required data
        missing_data = []
        available_indicators = []
        evidence = []
        
        # Flatten data for checking
        flat_data = self._flatten_data(all_data)
        
        # Check required data fields
        for required in scenario_type.required_data:
            if required not in flat_data or flat_data[required] is None:
                missing_data.append(required)
        
        # Check for indicators
        for indicator in scenario_type.indicators:
            if indicator in flat_data and flat_data[indicator]:
                available_indicators.append(indicator)
                evidence.append({
                    'indicator': indicator,
                    'value': flat_data[indicator],
                    'source': flat_data.get(f'{indicator}_source', 'unknown')
                })
        
        # Calculate confidence
        confidence_score, confidence_level = self._calculate_confidence(
            scenario_type, missing_data, available_indicators
        )
        
        # Only return scenarios with at least some confidence or that are explicitly unknown
        if confidence_score == 0 and not available_indicators:
            return None
        
        # Generate source labels
        source_labels = []
        for ev in evidence:
            source_labels.append({
                'field': ev['indicator'],
                'source': ev['source'],
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Generate recommended actions
        actions = self._generate_recommended_actions(scenario_type, confidence_level, missing_data)
        
        return ScenarioResult(
            scenario_id=scenario_type.id,
            scenario_name=scenario_type.name,
            category=scenario_type.category,
            confidence=confidence_level,
            confidence_score=confidence_score,
            description=scenario_type.description,
            evidence=evidence,
            missing_data=missing_data,
            recommended_actions=actions,
            source_labels=source_labels
        )
    
    def _flatten_data(self, nested_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested data structure for easier checking."""
        flat = {}
        
        def flatten(obj, prefix=''):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_key = f"{prefix}_{k}" if prefix else k
                    if isinstance(v, dict):
                        flatten(v, new_key)
                    else:
                        flat[new_key] = v
                        flat[k] = v  # Also store without prefix
            elif isinstance(obj, list):
                flat[prefix] = obj
        
        flatten(nested_data)
        return flat
    
    def _calculate_confidence(
        self,
        scenario_type: ScenarioType,
        missing_data: List[str],
        available_indicators: List[str]
    ) -> Tuple[float, ScenarioConfidence]:
        """Calculate confidence score and level for a scenario."""
        
        total_required = len(scenario_type.required_data)
        total_indicators = len(scenario_type.indicators)
        
        # Base score from data availability
        data_score = 0.0
        if total_required > 0:
            available_required = total_required - len(missing_data)
            data_score = available_required / total_required * 0.4
        
        # Indicator score
        indicator_score = 0.0
        if total_indicators > 0:
            indicator_score = len(available_indicators) / total_indicators * 0.6
        
        final_score = data_score + indicator_score
        
        # Determine confidence level
        if final_score >= 0.8:
            level = ScenarioConfidence.CONFIRMED
        elif final_score >= 0.6:
            level = ScenarioConfidence.LIKELY
        elif final_score >= 0.4:
            level = ScenarioConfidence.POSSIBLE
        elif final_score >= 0.2:
            level = ScenarioConfidence.SPECULATIVE
        else:
            level = ScenarioConfidence.UNKNOWN
        
        return round(final_score, 2), level
    
    def _generate_recommended_actions(
        self,
        scenario_type: ScenarioType,
        confidence: ScenarioConfidence,
        missing_data: List[str]
    ) -> List[str]:
        """Generate recommended actions for a scenario."""
        actions = []
        
        # If missing data, recommend obtaining it
        if missing_data:
            actions.append(f"Obtain missing data: {', '.join(missing_data[:3])}")
        
        # Category-specific recommendations
        if scenario_type.category == ScenarioCategory.ACQUISITION:
            if confidence in [ScenarioConfidence.CONFIRMED, ScenarioConfidence.LIKELY]:
                actions.append("Conduct detailed due diligence")
                actions.append("Prepare acquisition strategy")
        
        elif scenario_type.category == ScenarioCategory.RISK:
            if confidence in [ScenarioConfidence.CONFIRMED, ScenarioConfidence.LIKELY]:
                actions.append("Assess risk mitigation options")
                if scenario_type.risk_level in ['high', 'critical']:
                    actions.append("Consult with legal counsel")
        
        elif scenario_type.category == ScenarioCategory.DISTRESS:
            actions.append("Verify distress signals with direct contact")
            actions.append("Assess timeline urgency")
        
        elif scenario_type.category == ScenarioCategory.OPPORTUNITY:
            actions.append("Calculate potential ROI")
            actions.append("Compare with alternative opportunities")
        
        return actions
    
    def get_scenario_summary(self, results: List[ScenarioResult]) -> Dict[str, Any]:
        """Generate a summary of scenario analysis results."""
        
        by_category = {}
        by_confidence = {}
        
        for result in results:
            cat = result.category.value
            conf = result.confidence.value
            
            by_category[cat] = by_category.get(cat, 0) + 1
            by_confidence[conf] = by_confidence.get(conf, 0) + 1
        
        high_confidence = [r for r in results if r.confidence_score >= 0.6]
        top_opportunities = [r for r in results if r.category == ScenarioCategory.OPPORTUNITY and r.confidence_score >= 0.4]
        top_risks = [r for r in results if r.category == ScenarioCategory.RISK and r.confidence_score >= 0.4]
        
        return {
            'total_scenarios': len(results),
            'by_category': by_category,
            'by_confidence': by_confidence,
            'high_confidence_count': len(high_confidence),
            'top_opportunities': [r.scenario_name for r in top_opportunities],
            'top_risks': [r.scenario_name for r in top_risks],
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
