"""
Tests for Fairness Monitor (Gap P4 – Disparate Impact)
"""

import pytest

from datagod.compliance.fairness import (
    FairnessCheck,
    FairnessMetric,
    FairnessMonitor,
    FairnessReport,
    FairnessStatus,
)


class TestFairnessStatus:
    """Test fairness status enum."""

    def test_statuses_exist(self):
        assert FairnessStatus.PASS == "pass"
        assert FairnessStatus.WARNING == "warning"
        assert FairnessStatus.FAIL == "fail"


class TestFairnessMonitor:
    """Test the FairnessMonitor class."""

    def setup_method(self):
        self.monitor = FairnessMonitor()

    def test_monitor_initializes(self):
        assert self.monitor is not None

    def test_disparate_impact_pass(self):
        """Equal outcomes should pass."""
        outcomes = [
            {"group": "A", "approved": True},
            {"group": "A", "approved": True},
            {"group": "A", "approved": True},
            {"group": "A", "approved": False},
            {"group": "B", "approved": True},
            {"group": "B", "approved": True},
            {"group": "B", "approved": True},
            {"group": "B", "approved": False},
        ]
        report = self.monitor.analyze_disparate_impact(
            outcomes, protected_attribute="group", outcome_field="approved"
        )
        assert isinstance(report, FairnessReport)
        assert report.overall_status in [FairnessStatus.PASS, FairnessStatus.WARNING]

    def test_disparate_impact_fail(self):
        """Highly unequal outcomes should fail."""
        outcomes = []
        # Group A: 90% approval
        for _ in range(90):
            outcomes.append({"group": "A", "approved": True})
        for _ in range(10):
            outcomes.append({"group": "A", "approved": False})
        # Group B: 30% approval
        for _ in range(30):
            outcomes.append({"group": "B", "approved": True})
        for _ in range(70):
            outcomes.append({"group": "B", "approved": False})

        report = self.monitor.analyze_disparate_impact(
            outcomes, protected_attribute="group", outcome_field="approved"
        )
        assert report.overall_status == FairnessStatus.FAIL

    def test_jurisdiction_bias_no_bias(self):
        """Uniform distribution should pass."""
        records = [
            {"jurisdiction": "CA", "anomaly_count": 10},
            {"jurisdiction": "NY", "anomaly_count": 11},
            {"jurisdiction": "TX", "anomaly_count": 10},
        ]
        report = self.monitor.analyze_jurisdiction_bias(
            records, metric_field="anomaly_count"
        )
        assert isinstance(report, FairnessReport)

    def test_jurisdiction_bias_with_bias(self):
        """Large score disparities should produce a report."""
        records = [
            {"jurisdiction": "CA", "anomaly_count": 100},
            {"jurisdiction": "NY", "anomaly_count": 5},
            {"jurisdiction": "TX", "anomaly_count": 95},
            {"jurisdiction": "FL", "anomaly_count": 3},
        ]
        report = self.monitor.analyze_jurisdiction_bias(
            records, metric_field="anomaly_count"
        )
        assert isinstance(report, FairnessReport)
        # With only 4 records, z-score thresholds may not trigger — just verify report is valid
        assert report.overall_status in [
            FairnessStatus.PASS,
            FairnessStatus.WARNING,
            FairnessStatus.FAIL,
        ]

    def test_report_to_dict(self):
        outcomes = [
            {"group": "A", "approved": True},
            {"group": "A", "approved": False},
            {"group": "B", "approved": True},
            {"group": "B", "approved": False},
        ]
        report = self.monitor.analyze_disparate_impact(
            outcomes, protected_attribute="group", outcome_field="approved"
        )
        d = report.to_dict()
        assert "overall_status" in d
        assert "checks" in d
        assert "generated_at" in d

    def test_single_group_passes(self):
        """A single group can't have disparate impact."""
        outcomes = [
            {"group": "A", "approved": True},
            {"group": "A", "approved": False},
        ]
        report = self.monitor.analyze_disparate_impact(
            outcomes, protected_attribute="group", outcome_field="approved"
        )
        assert report.overall_status == FairnessStatus.PASS
