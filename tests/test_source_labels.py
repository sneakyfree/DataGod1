"""
Tests for Source Labels (Gap P7 – Audit-Grade Provenance)
"""

import pytest

from datagod.compliance.source_labels import (
    LabeledValue,
    SourceConfidence,
    label_data,
    label_estimated,
    label_stated,
    label_unknown,
    label_verified,
)


class TestSourceConfidence:
    """Test source confidence enum."""

    def test_all_levels_exist(self):
        assert SourceConfidence.VERIFIED == "verified"
        assert SourceConfidence.STATED == "stated"
        assert SourceConfidence.ESTIMATED == "estimated"
        assert SourceConfidence.UNKNOWN == "unknown"

    def test_inferred_level(self):
        assert SourceConfidence.INFERRED == "inferred"


class TestLabeledValue:
    """Test LabeledValue model."""

    def test_create_labeled_value(self):
        lv = LabeledValue(
            value=250000,
            label=SourceConfidence.VERIFIED,
            source="county_assessor",
        )
        assert lv.value == 250000
        assert lv.label == SourceConfidence.VERIFIED
        assert lv.source == "county_assessor"

    def test_labeled_value_default_confidence_score(self):
        lv = LabeledValue(
            value="John Doe",
            label=SourceConfidence.STATED,
            source="self_reported",
        )
        assert lv.confidence_score >= 0

    def test_labeled_value_to_dict(self):
        lv = LabeledValue(
            value=100,
            label=SourceConfidence.ESTIMATED,
            source="algorithm",
        )
        d = lv.to_dict()
        assert d["value"] == 100
        assert d["label"] == "estimated"
        assert d["source"] == "algorithm"

    def test_is_trustworthy_verified(self):
        lv = LabeledValue(value=1, label=SourceConfidence.VERIFIED)
        assert lv.is_trustworthy is True

    def test_is_trustworthy_stated(self):
        lv = LabeledValue(value=1, label=SourceConfidence.STATED)
        assert lv.is_trustworthy is True

    def test_is_not_trustworthy_unknown(self):
        lv = LabeledValue(value=1, label=SourceConfidence.UNKNOWN)
        assert lv.is_trustworthy is False


class TestConvenienceFunctions:
    """Test convenience labeling functions."""

    def test_label_verified(self):
        lv = label_verified(500000, "county_records")
        assert lv.label == SourceConfidence.VERIFIED
        assert lv.value == 500000

    def test_label_stated(self):
        lv = label_stated("John Doe", "borrower_application")
        assert lv.label == SourceConfidence.STATED

    def test_label_estimated(self):
        lv = label_estimated(475000, "avm_model")
        assert lv.label == SourceConfidence.ESTIMATED

    def test_label_unknown(self):
        lv = label_unknown(None)
        assert lv.label == SourceConfidence.UNKNOWN
        assert lv.value is None

    def test_label_data_generic(self):
        lv = label_data(42, SourceConfidence.VERIFIED, "test_source")
        assert lv.label == SourceConfidence.VERIFIED
        assert lv.value == 42
