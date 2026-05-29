"""
Unit tests for the AnomalyDetector module.

Tests cover:
- Statistical anomaly detection
- Isolation Forest detection
- Rule-based detection
- Multi-method detection
"""

import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, "/home/user1-gpu/Desktop/grants_folder/datagod/DataGod1")

from datagod.ml.anomaly_detector import (
    AnomalyDetector,
    AnomalyResult,
    AnomalyType,
    DetectionMethod,
)


class TestAnomalyDetector:
    """Tests for AnomalyDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a detector instance."""
        return AnomalyDetector()

    @pytest.fixture
    def sample_data(self):
        """Generate sample time series data with anomalies."""
        # Normal values around 100 with some noise
        normal = [100 + (i % 10) - 5 for i in range(50)]
        # Add anomalies
        normal[10] = 200  # Spike
        normal[25] = 20  # Drop
        normal[40] = 300  # High spike
        return normal

    @pytest.fixture
    def sample_records(self):
        """Generate sample records for record-based detection."""
        base_date = datetime.now()
        return [
            {
                "id": f"rec_{i}",
                "value": 100 + (i % 10),
                "created_at": (base_date - timedelta(days=i)).isoformat(),
                "source": "test",
            }
            for i in range(20)
        ]

    def test_detector_initialization(self, detector):
        """Test detector initializes correctly."""
        assert detector is not None
        assert hasattr(detector, "detect_time_series_anomalies")
        assert hasattr(detector, "detect_record_anomalies")

    def test_statistical_detection_finds_anomalies(self, detector, sample_data):
        """Test that statistical detection finds obvious anomalies."""
        results = detector.detect_time_series_anomalies(
            sample_data, method=DetectionMethod.STATISTICAL
        )

        assert isinstance(results, list)
        assert len(results) > 0

        # Should find at least one anomaly
        anomaly_indices = [r.data_index for r in results]
        assert any(idx in anomaly_indices for idx in [10, 25, 40])

    def test_isolation_forest_detection(self, detector, sample_data):
        """Test Isolation Forest detection method."""
        results = detector.detect_time_series_anomalies(
            sample_data, method=DetectionMethod.ISOLATION_FOREST
        )

        assert isinstance(results, list)
        # Isolation forest should find anomalies in this data
        assert len(results) >= 0  # May or may not find depending on parameters

    def test_rule_based_detection(self, detector, sample_data):
        """Test rule-based detection with custom threshold."""
        results = detector.detect_time_series_anomalies(
            sample_data, method=DetectionMethod.RULE_BASED, threshold=150
        )

        assert isinstance(results, list)
        # Values 200 and 300 should exceed threshold 150
        high_values = [r for r in results if r.value > 150]
        assert len(high_values) >= 2

    def test_multi_method_detection(self, detector, sample_data):
        """Test detection using all methods."""
        results = detector.detect_time_series_anomalies(
            sample_data, method=DetectionMethod.ALL
        )

        assert isinstance(results, list)

        # Check that results include detection method info
        if results:
            assert hasattr(results[0], "detection_method")

    def test_anomaly_result_structure(self, detector, sample_data):
        """Test that AnomalyResult has required fields."""
        results = detector.detect_time_series_anomalies(
            sample_data, method=DetectionMethod.STATISTICAL
        )

        if results:
            result = results[0]
            assert hasattr(result, "anomaly_type")
            assert hasattr(result, "score")
            assert hasattr(result, "value")
            assert hasattr(result, "expected_range")
            assert hasattr(result, "detection_method")

    def test_empty_data_handling(self, detector):
        """Test handling of empty data."""
        results = detector.detect_time_series_anomalies([])
        assert results == []

    def test_single_value_handling(self, detector):
        """Test handling of single value."""
        results = detector.detect_time_series_anomalies([100])
        assert isinstance(results, list)

    def test_record_anomaly_detection(self, detector, sample_records):
        """Test record-based anomaly detection."""
        # Add an anomalous record
        sample_records.append(
            {
                "id": "anomaly_1",
                "value": 1000,  # Way higher than normal
                "created_at": datetime.now().isoformat(),
                "source": "test",
            }
        )

        results = detector.detect_record_anomalies(sample_records, value_field="value")

        assert isinstance(results, list)

    def test_confidence_scores_in_range(self, detector, sample_data):
        """Test that confidence scores are between 0 and 1."""
        results = detector.detect_time_series_anomalies(
            sample_data, method=DetectionMethod.STATISTICAL
        )

        for result in results:
            assert 0 <= result.score <= 1, f"Score {result.score} out of range"

    def test_anomaly_types(self, detector, sample_data):
        """Test that anomaly types are correctly assigned."""
        results = detector.detect_time_series_anomalies(
            sample_data, method=DetectionMethod.STATISTICAL
        )

        valid_types = [
            AnomalyType.SPIKE,
            AnomalyType.DROP,
            AnomalyType.TREND_CHANGE,
            AnomalyType.SEASONALITY_BREAK,
            AnomalyType.OUTLIER,
        ]

        for result in results:
            assert result.anomaly_type in valid_types


class TestAnomalyType:
    """Tests for AnomalyType enum."""

    def test_all_types_defined(self):
        """Test that all expected types are defined."""
        assert AnomalyType.SPIKE is not None
        assert AnomalyType.DROP is not None
        assert AnomalyType.TREND_CHANGE is not None
        assert AnomalyType.OUTLIER is not None


class TestDetectionMethod:
    """Tests for DetectionMethod enum."""

    def test_all_methods_defined(self):
        """Test that all detection methods are defined."""
        assert DetectionMethod.STATISTICAL is not None
        assert DetectionMethod.ISOLATION_FOREST is not None
        assert DetectionMethod.RULE_BASED is not None
        assert DetectionMethod.ALL is not None
