"""
Fairness Monitoring (DNA Strand Gene 2.4)

Implements disparate impact analysis and bias detection
across jurisdictions, entity types, and demographic proxies.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class FairnessMetric(str, Enum):
    """Types of fairness metrics."""
    DISPARATE_IMPACT = "disparate_impact"
    STATISTICAL_PARITY = "statistical_parity"
    EQUAL_OPPORTUNITY = "equal_opportunity"
    PREDICTIVE_PARITY = "predictive_parity"


class FairnessStatus(str, Enum):
    """Pass/fail status for fairness checks."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class FairnessCheck:
    """Result of a single fairness check."""
    metric: FairnessMetric
    protected_attribute: str
    group_a: str
    group_b: str
    group_a_rate: float
    group_b_rate: float
    ratio: float
    threshold: float
    status: FairnessStatus
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric.value,
            "protected_attribute": self.protected_attribute,
            "group_a": self.group_a,
            "group_b": self.group_b,
            "group_a_rate": round(self.group_a_rate, 4),
            "group_b_rate": round(self.group_b_rate, 4),
            "ratio": round(self.ratio, 4),
            "threshold": self.threshold,
            "status": self.status.value,
            "description": self.description,
        }


@dataclass
class FairnessReport:
    """Complete fairness assessment report."""
    report_id: str
    checks: List[FairnessCheck] = field(default_factory=list)
    overall_status: FairnessStatus = FairnessStatus.PASS
    pass_count: int = 0
    warning_count: int = 0
    fail_count: int = 0
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "checks": [c.to_dict() for c in self.checks],
            "overall_status": self.overall_status.value,
            "pass_count": self.pass_count,
            "warning_count": self.warning_count,
            "fail_count": self.fail_count,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat(),
        }


class FairnessMonitor:
    """
    Monitors for bias and disparate impact across platform operations.

    Implements the 4/5ths (80%) rule for disparate impact analysis
    and provides continuous fairness monitoring.
    """

    # Standard disparate impact threshold (4/5ths rule)
    DI_THRESHOLD = 0.80
    WARNING_THRESHOLD = 0.85

    def __init__(self):
        self._history: List[FairnessReport] = []

    def analyze_disparate_impact(
        self,
        outcomes: List[Dict[str, Any]],
        protected_attribute: str,
        outcome_field: str = "approved",
    ) -> FairnessReport:
        """
        Analyze outcomes for disparate impact across a protected attribute.

        Args:
            outcomes: List of outcome records
            protected_attribute: Field name for the protected class
            outcome_field: Field name for the favorable outcome (bool)

        Returns:
            FairnessReport with all pairwise comparisons
        """
        import uuid
        report_id = f"fair-{uuid.uuid4().hex[:8]}"

        # Group outcomes by protected attribute
        groups: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "favorable": 0})
        for outcome in outcomes:
            group = str(outcome.get(protected_attribute, "unknown"))
            groups[group]["total"] += 1
            if outcome.get(outcome_field):
                groups[group]["favorable"] += 1

        # Calculate rates
        rates = {}
        for group, counts in groups.items():
            if counts["total"] > 0:
                rates[group] = counts["favorable"] / counts["total"]
            else:
                rates[group] = 0.0

        # Pairwise disparate impact checks
        checks = []
        group_names = sorted(rates.keys())
        for i, g_a in enumerate(group_names):
            for g_b in group_names[i + 1:]:
                rate_a, rate_b = rates[g_a], rates[g_b]
                # DI ratio: min(rate) / max(rate)
                if max(rate_a, rate_b) > 0:
                    ratio = min(rate_a, rate_b) / max(rate_a, rate_b)
                else:
                    ratio = 1.0

                if ratio < self.DI_THRESHOLD:
                    status = FairnessStatus.FAIL
                elif ratio < self.WARNING_THRESHOLD:
                    status = FairnessStatus.WARNING
                else:
                    status = FairnessStatus.PASS

                checks.append(FairnessCheck(
                    metric=FairnessMetric.DISPARATE_IMPACT,
                    protected_attribute=protected_attribute,
                    group_a=g_a,
                    group_b=g_b,
                    group_a_rate=rate_a,
                    group_b_rate=rate_b,
                    ratio=ratio,
                    threshold=self.DI_THRESHOLD,
                    status=status,
                    description=(
                        f"Disparate impact ratio between '{g_a}' and '{g_b}': "
                        f"{ratio:.2%} ({'PASS' if status == FairnessStatus.PASS else 'FAIL'} "
                        f"at {self.DI_THRESHOLD:.0%} threshold)"
                    ),
                ))

        # Aggregate report
        pass_count = sum(1 for c in checks if c.status == FairnessStatus.PASS)
        warning_count = sum(1 for c in checks if c.status == FairnessStatus.WARNING)
        fail_count = sum(1 for c in checks if c.status == FairnessStatus.FAIL)

        if fail_count > 0:
            overall = FairnessStatus.FAIL
        elif warning_count > 0:
            overall = FairnessStatus.WARNING
        else:
            overall = FairnessStatus.PASS

        recommendations = []
        if fail_count > 0:
            recommendations.append("CRITICAL: Disparate impact violations detected. Review decision criteria for bias.")
            recommendations.append("Consider additional data sources to reduce proxy discrimination.")
        if warning_count > 0:
            recommendations.append("WARNING: Near-threshold ratios detected. Monitor closely for drift.")

        report = FairnessReport(
            report_id=report_id,
            checks=checks,
            overall_status=overall,
            pass_count=pass_count,
            warning_count=warning_count,
            fail_count=fail_count,
            recommendations=recommendations,
        )

        self._history.append(report)
        return report

    def analyze_jurisdiction_bias(
        self,
        records: List[Dict[str, Any]],
        metric_field: str = "anomaly_count",
    ) -> FairnessReport:
        """
        Check for systematic bias across jurisdictions.

        Flags jurisdictions with anomaly detection rates significantly
        higher or lower than the mean.
        """
        import uuid
        import statistics

        report_id = f"fair-jur-{uuid.uuid4().hex[:8]}"

        # Group by jurisdiction
        jur_metrics: Dict[str, List[float]] = defaultdict(list)
        for record in records:
            jur = record.get("jurisdiction", "unknown")
            val = record.get(metric_field, 0)
            jur_metrics[jur].append(float(val))

        # Compute per-jurisdiction averages
        jur_avgs = {j: statistics.mean(vals) for j, vals in jur_metrics.items() if vals}

        if len(jur_avgs) < 2:
            return FairnessReport(report_id=report_id)

        overall_mean = statistics.mean(jur_avgs.values())
        overall_std = statistics.stdev(jur_avgs.values()) if len(jur_avgs) > 1 else 0

        checks = []
        for jur, avg in jur_avgs.items():
            if overall_std > 0:
                z_score = (avg - overall_mean) / overall_std
            else:
                z_score = 0.0

            if abs(z_score) > 2.0:
                status = FairnessStatus.FAIL
            elif abs(z_score) > 1.5:
                status = FairnessStatus.WARNING
            else:
                status = FairnessStatus.PASS

            checks.append(FairnessCheck(
                metric=FairnessMetric.STATISTICAL_PARITY,
                protected_attribute="jurisdiction",
                group_a=jur,
                group_b="population_mean",
                group_a_rate=avg,
                group_b_rate=overall_mean,
                ratio=avg / overall_mean if overall_mean > 0 else 1.0,
                threshold=2.0,
                status=status,
                description=f"Jurisdiction '{jur}': z-score={z_score:.2f}",
            ))

        pass_count = sum(1 for c in checks if c.status == FairnessStatus.PASS)
        warning_count = sum(1 for c in checks if c.status == FairnessStatus.WARNING)
        fail_count = sum(1 for c in checks if c.status == FairnessStatus.FAIL)

        overall = FairnessStatus.FAIL if fail_count else (
            FairnessStatus.WARNING if warning_count else FairnessStatus.PASS
        )

        report = FairnessReport(
            report_id=report_id,
            checks=checks,
            overall_status=overall,
            pass_count=pass_count,
            warning_count=warning_count,
            fail_count=fail_count,
        )
        self._history.append(report)
        return report
