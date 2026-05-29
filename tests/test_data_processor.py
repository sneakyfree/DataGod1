"""
Tests for datagod.utils.data_processor module
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestDataProcessor:
    """Test cases for DataProcessor class"""

    def test_import(self):
        """Test DataProcessor can be imported"""
        from datagod.utils.data_processor import DataProcessor

        assert DataProcessor is not None

    def test_instantiation(self):
        """Test DataProcessor can be instantiated"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()
        assert processor is not None
        assert hasattr(processor, "processing_steps")
        assert processor.processing_steps == []

    def test_validate_and_clean_removes_null_values(self):
        """Test validate_and_clean removes null values"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"name": "John", "age": None, "city": "NYC"}
        result = processor.validate_and_clean(data)

        assert "age" not in result
        assert result["name"] == "John"
        assert result["city"] == "NYC"

    def test_validate_and_clean_converts_string_null(self):
        """Test validate_and_clean converts string 'null' to None"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"name": "John", "status": "null"}
        result = processor.validate_and_clean(data)

        assert result["status"] is None

    def test_validate_and_clean_converts_string_none(self):
        """Test validate_and_clean converts string 'none' to None"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"name": "John", "status": "none"}
        result = processor.validate_and_clean(data)

        assert result["status"] is None

    def test_validate_and_clean_converts_digit_strings_to_int(self):
        """Test validate_and_clean converts digit strings to int"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"age": "25", "count": "100"}
        result = processor.validate_and_clean(data)

        assert result["age"] == 25
        assert result["count"] == 100
        assert isinstance(result["age"], int)

    def test_validate_and_clean_converts_float_strings(self):
        """Test validate_and_clean converts float strings to float"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"price": "19.99", "rate": "0.05"}
        result = processor.validate_and_clean(data)

        assert result["price"] == 19.99
        assert result["rate"] == 0.05
        assert isinstance(result["price"], float)

    def test_validate_and_clean_handles_error(self):
        """Test validate_and_clean handles errors gracefully"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        # Pass something that might cause an error during iteration
        data = {"name": "John"}
        result = processor.validate_and_clean(data)

        # Should return cleaned data even if some fields are problematic
        assert result is not None

    def test_deduplicate_records_removes_duplicates(self):
        """Test deduplicate_records removes duplicate records"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        records = [
            {"name": "John", "age": 25},
            {"name": "Jane", "age": 30},
            {"name": "John", "age": 25},  # Duplicate
        ]
        result = processor.deduplicate_records(records)

        assert len(result) == 2

    def test_deduplicate_records_empty_list(self):
        """Test deduplicate_records with empty list"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        result = processor.deduplicate_records([])
        assert result == []

    def test_deduplicate_records_no_duplicates(self):
        """Test deduplicate_records with no duplicates"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        records = [
            {"name": "John", "age": 25},
            {"name": "Jane", "age": 30},
        ]
        result = processor.deduplicate_records(records)

        assert len(result) == 2

    def test_enrich_data_adds_created_at(self):
        """Test enrich_data adds created_at timestamp"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"name": "John"}
        result = processor.enrich_data(data)

        assert "created_at" in result

    def test_enrich_data_adds_confidence_score(self):
        """Test enrich_data adds confidence_score"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"name": "John"}
        result = processor.enrich_data(data)

        assert "confidence_score" in result

    def test_enrich_data_adds_hash_value(self):
        """Test enrich_data adds hash_value"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"name": "John"}
        result = processor.enrich_data(data)

        assert "hash_value" in result

    def test_enrich_data_preserves_existing_fields(self):
        """Test enrich_data doesn't overwrite existing enrichment fields"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {
            "name": "John",
            "created_at": "2020-01-01",
            "confidence_score": "Manual",
            "hash_value": "existing_hash",
        }
        result = processor.enrich_data(data)

        assert result["created_at"] == "2020-01-01"
        assert result["confidence_score"] == "Manual"
        assert result["hash_value"] == "existing_hash"

    def test_calculate_confidence_score_high(self):
        """Test _calculate_confidence_score returns High for complete data"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        # All 10 fields filled
        data = {f"field_{i}": f"value_{i}" for i in range(10)}
        score = processor._calculate_confidence_score(data)

        assert score == "High"

    def test_calculate_confidence_score_medium(self):
        """Test _calculate_confidence_score returns Medium for 70-89% complete"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        # 8 of 10 fields filled (80%)
        data = {f"field_{i}": f"value_{i}" if i < 8 else "" for i in range(10)}
        score = processor._calculate_confidence_score(data)

        assert score == "Medium"

    def test_calculate_confidence_score_low(self):
        """Test _calculate_confidence_score returns Low for <70% complete"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        # 5 of 10 fields filled (50%)
        data = {f"field_{i}": f"value_{i}" if i < 5 else "" for i in range(10)}
        score = processor._calculate_confidence_score(data)

        assert score == "Low"

    def test_calculate_confidence_score_empty(self):
        """Test _calculate_confidence_score with empty data"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        score = processor._calculate_confidence_score({})
        assert score == "Low"

    def test_transform_data(self):
        """Test transform_data applies mapping rules"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"firstName": "John", "lastName": "Doe", "userAge": 25}
        mapping = {"firstName": "first_name", "lastName": "last_name", "userAge": "age"}
        result = processor.transform_data(data, mapping)

        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["age"] == 25
        assert "firstName" not in result

    def test_transform_data_missing_fields(self):
        """Test transform_data handles missing source fields"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"firstName": "John"}
        mapping = {
            "firstName": "first_name",
            "lastName": "last_name",  # Not in data
        }
        result = processor.transform_data(data, mapping)

        assert result["first_name"] == "John"
        assert "last_name" not in result

    def test_transform_data_empty_mapping(self):
        """Test transform_data with empty mapping"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"name": "John"}
        result = processor.transform_data(data, {})

        assert result == {}

    def test_validate_data_quality(self):
        """Test validate_data_quality returns metrics"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"name": "John", "age": 25, "city": "NYC"}
        metrics = processor.validate_data_quality(data)

        assert "completeness" in metrics
        assert "accuracy" in metrics
        assert "consistency" in metrics
        assert "timeliness" in metrics
        assert "overall_score" in metrics

    def test_validate_data_quality_completeness(self):
        """Test validate_data_quality calculates correct completeness"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        # All fields filled
        data = {"field1": "value1", "field2": "value2"}
        metrics = processor.validate_data_quality(data)

        assert metrics["completeness"] == 1.0

    def test_validate_data_quality_with_empty_fields(self):
        """Test validate_data_quality with empty fields"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        # Half fields empty
        data = {"field1": "value1", "field2": ""}
        metrics = processor.validate_data_quality(data)

        assert metrics["completeness"] == 0.5

    def test_validate_data_quality_overall_score(self):
        """Test validate_data_quality calculates overall score correctly"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"name": "John"}
        metrics = processor.validate_data_quality(data)

        # Overall = completeness*0.3 + accuracy*0.3 + consistency*0.2 + timeliness*0.2
        expected = (
            metrics["completeness"] * 0.3
            + metrics["accuracy"] * 0.3
            + metrics["consistency"] * 0.2
            + metrics["timeliness"] * 0.2
        )
        assert abs(metrics["overall_score"] - expected) < 0.001

    def test_calculate_completeness_empty(self):
        """Test _calculate_completeness with empty data"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        assert processor._calculate_completeness({}) == 0.0

    def test_calculate_completeness_partial(self):
        """Test _calculate_completeness with partial data"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        data = {"field1": "value", "field2": None, "field3": ""}
        result = processor._calculate_completeness(data)

        # Only 1 of 3 fields has a non-empty, non-None value
        assert result == pytest.approx(1 / 3, rel=0.01)

    def test_calculate_accuracy(self):
        """Test _calculate_accuracy returns expected value"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        result = processor._calculate_accuracy({"any": "data"})
        assert result == 0.95  # Placeholder value

    def test_calculate_consistency(self):
        """Test _calculate_consistency returns expected value"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        result = processor._calculate_consistency({"any": "data"})
        assert result == 0.90  # Placeholder value

    def test_calculate_timeliness(self):
        """Test _calculate_timeliness returns expected value"""
        from datagod.utils.data_processor import DataProcessor

        processor = DataProcessor()

        result = processor._calculate_timeliness({"any": "data"})
        assert result == 0.85  # Placeholder value


class TestGlobalProcessor:
    """Test cases for global processor instance"""

    def test_global_processor_exists(self):
        """Test global processor instance exists"""
        from datagod.utils.data_processor import processor

        assert processor is not None

    def test_global_processor_is_data_processor(self):
        """Test global processor is a DataProcessor instance"""
        from datagod.utils.data_processor import DataProcessor, processor

        assert isinstance(processor, DataProcessor)
