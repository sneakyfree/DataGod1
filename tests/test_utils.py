"""
Tests for DataGod utility modules.

Tests cover:
- Data validation
- Data processing
- Data deduplication
- Quality metrics
"""

import json
from datetime import datetime

import pytest


class TestDataValidator:
    """Tests for DataValidator class."""

    def test_validate_jurisdiction_valid(self):
        """Test validation of valid jurisdiction data."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        jurisdiction_data = {"name": "Harris County", "state": "TX"}

        result = validator.validate_jurisdiction(jurisdiction_data)

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "timestamp" in result

    def test_validate_jurisdiction_missing_name(self):
        """Test validation fails when name is missing."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        jurisdiction_data = {"state": "TX"}

        result = validator.validate_jurisdiction(jurisdiction_data)

        assert result["valid"] is False
        assert any("name" in error for error in result["errors"])

    def test_validate_jurisdiction_missing_state(self):
        """Test validation fails when state is missing."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        jurisdiction_data = {"name": "Harris County"}

        result = validator.validate_jurisdiction(jurisdiction_data)

        assert result["valid"] is False
        assert any("state" in error for error in result["errors"])

    def test_validate_jurisdiction_invalid_state_format(self):
        """Test validation fails with invalid state format."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        jurisdiction_data = {
            "name": "Harris County",
            "state": "Texas",  # Should be 2-letter abbreviation
        }

        result = validator.validate_jurisdiction(jurisdiction_data)

        assert result["valid"] is False
        assert any("state" in error.lower() for error in result["errors"])

    def test_validate_jurisdiction_lowercase_state(self):
        """Test validation fails with lowercase state."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        jurisdiction_data = {
            "name": "Harris County",
            "state": "tx",  # Should be uppercase
        }

        result = validator.validate_jurisdiction(jurisdiction_data)

        assert result["valid"] is False

    def test_validate_record_valid(self):
        """Test validation of valid record data."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        record_data = {
            "source_id": "12345",
            "record_type": "property",
            "data": {"address": "123 Main St"},
        }

        result = validator.validate_record(record_data)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_record_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        record_data = {
            "source_id": "12345"
            # Missing record_type and data
        }

        result = validator.validate_record(record_data)

        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_record_invalid_record_type(self):
        """Test validation fails with invalid record type."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        record_data = {
            "source_id": "12345",
            "record_type": "invalid_type",
            "data": {"test": "data"},
        }

        result = validator.validate_record(record_data)

        assert result["valid"] is False
        assert any("record type" in error.lower() for error in result["errors"])

    def test_validate_record_data_not_dict(self):
        """Test validation fails when data is not a dict."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        record_data = {
            "source_id": "12345",
            "record_type": "property",
            "data": "not a dict",
        }

        result = validator.validate_record(record_data)

        assert result["valid"] is False
        assert any("json" in error.lower() for error in result["errors"])

    def test_calculate_quality_metrics(self):
        """Test quality metrics calculation."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        data = {
            "name": "John Doe",
            "address": "123 Main St",
            "city": "Houston",
            "state": "TX",
        }

        metrics = validator.calculate_quality_metrics(data, "test_source")

        assert "completeness" in metrics
        assert "accuracy" in metrics
        assert "consistency" in metrics
        assert "timeliness" in metrics
        assert all(0 <= v <= 1 for v in metrics.values())

    def test_calculate_completeness_full_data(self):
        """Test completeness score with all fields filled."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        data = {"field1": "value1", "field2": "value2", "field3": "value3"}

        completeness = validator._calculate_completeness(data)

        assert completeness == 1.0

    def test_calculate_completeness_partial_data(self):
        """Test completeness score with some fields empty."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()
        data = {"field1": "value1", "field2": None, "field3": ""}

        completeness = validator._calculate_completeness(data)

        # Only field1 is filled, so 1/3
        assert completeness == pytest.approx(1 / 3, 0.01)

    def test_calculate_completeness_empty_data(self):
        """Test completeness score with empty data."""
        from datagod.utils.data_validation import DataValidator

        validator = DataValidator()

        completeness = validator._calculate_completeness({})

        assert completeness == 0.0


class TestDataProcessor:
    """Tests for DataProcessor class."""

    def test_validate_and_clean_removes_nulls(self):
        """Test that null values are removed."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        data = {"name": "John", "address": None, "city": "Houston"}

        result = processor.validate_and_clean(data)

        assert "address" not in result
        assert result["name"] == "John"
        assert result["city"] == "Houston"

    def test_validate_and_clean_converts_string_null(self):
        """Test that string 'null' is converted to None."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        data = {"name": "John", "address": "null"}

        result = processor.validate_and_clean(data)

        assert result["address"] is None

    def test_validate_and_clean_converts_numeric_strings(self):
        """Test that numeric strings are converted to numbers."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        data = {"age": "25", "price": "99.99"}

        result = processor.validate_and_clean(data)

        assert result["age"] == 25
        assert isinstance(result["age"], int)
        assert result["price"] == 99.99
        assert isinstance(result["price"], float)

    def test_deduplicate_records(self):
        """Test deduplication of records."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        records = [
            {"id": 1, "name": "John"},
            {"id": 2, "name": "Jane"},
            {"id": 1, "name": "John"},  # Duplicate
            {"id": 3, "name": "Bob"},
        ]

        result = processor.deduplicate_records(records)

        assert len(result) == 3
        assert {"id": 1, "name": "John"} in result
        assert {"id": 2, "name": "Jane"} in result
        assert {"id": 3, "name": "Bob"} in result

    def test_deduplicate_records_empty_list(self):
        """Test deduplication with empty list."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        result = processor.deduplicate_records([])

        assert result == []

    def test_enrich_data_adds_timestamp(self):
        """Test that enrichment adds timestamp."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        data = {"name": "John"}

        result = processor.enrich_data(data)

        assert "created_at" in result

    def test_enrich_data_adds_confidence_score(self):
        """Test that enrichment adds confidence score."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        data = {"name": "John", "address": "123 Main St"}

        result = processor.enrich_data(data)

        assert "confidence_score" in result
        assert result["confidence_score"] in ["Low", "Medium", "High"]

    def test_enrich_data_adds_hash_value(self):
        """Test that enrichment adds hash value."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        data = {"name": "John"}

        result = processor.enrich_data(data)

        assert "hash_value" in result
        assert len(result["hash_value"]) == 32  # MD5 hash length

    def test_calculate_confidence_score_high(self):
        """Test high confidence score."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        # All fields filled = 100% completeness
        data = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}

        score = processor._calculate_confidence_score(data)

        assert score == "High"

    def test_calculate_confidence_score_medium(self):
        """Test medium confidence score."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        # 8 out of 10 filled = 80% completeness
        data = {
            "a": 1,
            "b": 2,
            "c": 3,
            "d": 4,
            "e": 5,
            "f": 6,
            "g": 7,
            "h": 8,
            "i": None,
            "j": "",
        }

        score = processor._calculate_confidence_score(data)

        assert score == "Medium"

    def test_calculate_confidence_score_low(self):
        """Test low confidence score."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        # 3 out of 10 filled = 30% completeness
        data = {
            "a": 1,
            "b": 2,
            "c": 3,
            "d": None,
            "e": "",
            "f": None,
            "g": "",
            "h": None,
            "i": None,
            "j": "",
        }

        score = processor._calculate_confidence_score(data)

        assert score == "Low"

    def test_calculate_confidence_score_empty(self):
        """Test confidence score with empty data."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        score = processor._calculate_confidence_score({})

        assert score == "Low"

    def test_transform_data(self):
        """Test data transformation with mapping."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "street_address": "123 Main St",
        }
        mapping = {
            "first_name": "given_name",
            "last_name": "family_name",
            "street_address": "address",
        }

        result = processor.transform_data(data, mapping)

        assert result["given_name"] == "John"
        assert result["family_name"] == "Doe"
        assert result["address"] == "123 Main St"
        assert "first_name" not in result

    def test_transform_data_partial_mapping(self):
        """Test transformation with partial mapping."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        data = {"first_name": "John", "last_name": "Doe", "age": 30}
        mapping = {"first_name": "name"}

        result = processor.transform_data(data, mapping)

        assert result["name"] == "John"
        assert "last_name" not in result  # Not in mapping
        assert "age" not in result  # Not in mapping

    def test_validate_data_quality(self):
        """Test data quality validation."""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        data = {
            "name": "John Doe",
            "address": "123 Main St",
            "city": "Houston",
            "state": "TX",
        }

        metrics = processor.validate_data_quality(data)

        assert "completeness" in metrics
        assert "accuracy" in metrics
        assert "consistency" in metrics
        assert "timeliness" in metrics
        assert "overall_score" in metrics
        assert 0 <= metrics["overall_score"] <= 1


class TestValidatorGlobalInstance:
    """Tests for the global validator instance."""

    def test_global_validator_exists(self):
        """Test that global validator instance exists."""
        from datagod.utils.data_validation import DataValidator, validator

        assert validator is not None
        assert isinstance(validator, DataValidator)


class TestProcessorGlobalInstance:
    """Tests for the global processor instance."""

    def test_global_processor_exists(self):
        """Test that global processor instance exists."""
        from datagod.utils.data_processor import DataProcessor, processor

        assert processor is not None
        assert isinstance(processor, DataProcessor)
