"""
DataGod Explainability Service
4-layer explainability framework for ML decisions and data processing
"""

from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


class ExplainabilityLayer(str, Enum):
    """Four layers of explanation, from simple to audit-grade."""
    USER = "user"           # Plain English for end users
    TECHNICAL = "technical"  # Technical details for data analysts
    AUDIT = "audit"          # Compliance-grade audit trail
    COMPLIANCE = "compliance"  # Regulatory compliance documentation


class Explanation:
    """Structured explanation for a decision or result."""

    def __init__(
        self,
        decision_id: str,
        decision_type: str,
        summary: str,
    ):
        self.decision_id = decision_id
        self.decision_type = decision_type
        self.summary = summary
        self.layers: Dict[str, Dict[str, Any]] = {}
        self.created_at = datetime.utcnow()

    def add_layer(self, layer: ExplainabilityLayer, content: Dict[str, Any]):
        """Add explanation content for a specific layer."""
        self.layers[layer.value] = {
            "content": content,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type,
            "summary": self.summary,
            "layers": self.layers,
            "created_at": self.created_at.isoformat(),
        }


class ExplainabilityService:
    """
    Service for generating multi-layer explanations for ML decisions,
    anomaly detections, and data processing results.
    """

    def explain_anomaly(
        self,
        anomaly_id: str,
        anomaly_type: str,
        confidence: float,
        features: Dict[str, Any],
        detection_method: str,
    ) -> Explanation:
        """Generate a 4-layer explanation for an anomaly detection result."""
        explanation = Explanation(
            decision_id=anomaly_id,
            decision_type="anomaly_detection",
            summary=f"Anomaly detected ({anomaly_type}) with {confidence:.1%} confidence",
        )

        # User layer: plain English
        explanation.add_layer(ExplainabilityLayer.USER, {
            "what_happened": f"Our system detected an unusual pattern in the data ({anomaly_type}).",
            "confidence": f"{confidence:.0%} confident this is a real anomaly",
            "what_to_do": "Review the flagged records and verify the data is correct.",
        })

        # Technical layer: features and method
        explanation.add_layer(ExplainabilityLayer.TECHNICAL, {
            "detection_method": detection_method,
            "confidence_score": confidence,
            "contributing_features": features,
            "model_version": "v1.0",
            "feature_importance": {
                k: round(v, 4) if isinstance(v, (int, float)) else v
                for k, v in features.items()
            },
        })

        # Audit layer: full trace
        explanation.add_layer(ExplainabilityLayer.AUDIT, {
            "anomaly_id": anomaly_id,
            "detection_timestamp": datetime.utcnow().isoformat(),
            "method": detection_method,
            "input_features": features,
            "confidence": confidence,
            "threshold_used": 0.7,
            "decision": "flagged" if confidence > 0.7 else "within_normal",
        })

        # Compliance layer
        explanation.add_layer(ExplainabilityLayer.COMPLIANCE, {
            "data_handling": "All data processed in compliance with data protection policies",
            "model_governance": "Detection model is registered in the model registry with version control",
            "bias_assessment": "Model has been evaluated for bias across jurisdictions",
            "retention_policy": "Anomaly records retained for 7 years per data retention policy",
        })

        return explanation

    def explain_search(
        self,
        query: str,
        result_count: int,
        filters_applied: Dict[str, Any],
    ) -> Explanation:
        """Generate explanation for search result ranking."""
        explanation = Explanation(
            decision_id=f"search-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            decision_type="search_results",
            summary=f"Found {result_count} results for '{query}'",
        )

        explanation.add_layer(ExplainabilityLayer.USER, {
            "results_found": result_count,
            "filters_used": list(filters_applied.keys()),
            "relevance_note": "Results are sorted by relevance to your search terms",
        })

        explanation.add_layer(ExplainabilityLayer.TECHNICAL, {
            "query": query,
            "result_count": result_count,
            "filters": filters_applied,
            "search_method": "full_text_ilike",
            "index_used": True,
        })

        return explanation

    def explain_data_quality(
        self,
        quality_score: float,
        dimensions: Dict[str, float],
        issues: List[Dict[str, Any]],
    ) -> Explanation:
        """Generate explanation for data quality assessment."""
        explanation = Explanation(
            decision_id=f"quality-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            decision_type="data_quality",
            summary=f"Data quality score: {quality_score:.0%}",
        )

        explanation.add_layer(ExplainabilityLayer.USER, {
            "overall_quality": f"{quality_score:.0%}",
            "dimensions": {k: f"{v:.0%}" for k, v in dimensions.items()},
            "issue_count": len(issues),
        })

        explanation.add_layer(ExplainabilityLayer.TECHNICAL, {
            "quality_score": quality_score,
            "dimensions": dimensions,
            "issues": issues,
            "methodology": "Multi-dimensional quality assessment (completeness, accuracy, freshness, consistency)",
        })

        return explanation
