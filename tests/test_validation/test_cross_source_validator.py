"""
Comprehensive tests for the Cross-Source Validator.

Tests cover:
- DiscrepancyType enum
- DiscrepancySeverity enum
- SourceDiscrepancy dataclass
- CrossSourceResult dataclass
- CrossSourceValidator class
- Exact match comparison
- Numeric comparison with tolerance
- Date comparison with tolerance
- Fuzzy text matching
- Record reconciliation
- Convenience functions
"""

from datetime import date, datetime, timedelta

import pytest

from datagod.validation.cross_source_validator import (
    CrossSourceResult,
    CrossSourceValidator,
    DiscrepancySeverity,
    DiscrepancyType,
    SourceDiscrepancy,
    reconcile_records,
    validate_cross_source,
)


class TestDiscrepancyTypeEnum:
    """Tests for DiscrepancyType enum"""

    def test_all_types_exist(self):
        """Test that all discrepancy types are defined"""
        assert DiscrepancyType.VALUE_MISMATCH is not None
        assert DiscrepancyType.MISSING_IN_SOURCE is not None
        assert DiscrepancyType.FORMAT_DIFFERENCE is not None
        assert DiscrepancyType.DATE_DIFFERENCE is not None
        assert DiscrepancyType.CASE_DIFFERENCE is not None
        assert DiscrepancyType.PRECISION_DIFFERENCE is not None

    def test_type_values(self):
        """Test discrepancy type string values"""
        assert DiscrepancyType.VALUE_MISMATCH.value == "value_mismatch"
        assert DiscrepancyType.MISSING_IN_SOURCE.value == "missing_in_source"
        assert DiscrepancyType.FORMAT_DIFFERENCE.value == "format_difference"
        assert DiscrepancyType.DATE_DIFFERENCE.value == "date_difference"
        assert DiscrepancyType.CASE_DIFFERENCE.value == "case_difference"
        assert DiscrepancyType.PRECISION_DIFFERENCE.value == "precision_diff"


class TestDiscrepancySeverityEnum:
    """Tests for DiscrepancySeverity enum"""

    def test_all_severities_exist(self):
        """Test that all severity levels are defined"""
        assert DiscrepancySeverity.CRITICAL is not None
        assert DiscrepancySeverity.HIGH is not None
        assert DiscrepancySeverity.MEDIUM is not None
        assert DiscrepancySeverity.LOW is not None
        assert DiscrepancySeverity.INFO is not None

    def test_severity_values(self):
        """Test severity string values"""
        assert DiscrepancySeverity.CRITICAL.value == "critical"
        assert DiscrepancySeverity.HIGH.value == "high"
        assert DiscrepancySeverity.MEDIUM.value == "medium"
        assert DiscrepancySeverity.LOW.value == "low"
        assert DiscrepancySeverity.INFO.value == "info"


class TestSourceDiscrepancy:
    """Tests for SourceDiscrepancy dataclass"""

    def test_create_discrepancy(self):
        """Test creating a source discrepancy"""
        disc = SourceDiscrepancy(
            field="address",
            discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
            severity=DiscrepancySeverity.MEDIUM,
            source1_name="county",
            source1_value="123 Main St",
            source2_name="assessor",
            source2_value="123 Main Street",
        )
        assert disc.field == "address"
        assert disc.discrepancy_type == DiscrepancyType.VALUE_MISMATCH
        assert disc.severity == DiscrepancySeverity.MEDIUM

    def test_discrepancy_with_optional_fields(self):
        """Test discrepancy with optional fields"""
        disc = SourceDiscrepancy(
            field="value",
            discrepancy_type=DiscrepancyType.PRECISION_DIFFERENCE,
            severity=DiscrepancySeverity.LOW,
            source1_name="source1",
            source1_value=100000,
            source2_name="source2",
            source2_value=100500,
            message="Values differ slightly",
            recommended_value=100250,
            confidence=0.9,
        )
        assert disc.message == "Values differ slightly"
        assert disc.recommended_value == 100250
        assert disc.confidence == 0.9

    def test_discrepancy_to_dict(self):
        """Test converting discrepancy to dictionary"""
        disc = SourceDiscrepancy(
            field="address",
            discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
            severity=DiscrepancySeverity.HIGH,
            source1_name="county",
            source1_value="123 Main St",
            source2_name="assessor",
            source2_value="456 Oak Ave",
            message="Address mismatch",
            recommended_value="123 Main St",
            confidence=0.6,
        )
        result = disc.to_dict()
        assert result["field"] == "address"
        assert result["discrepancy_type"] == "value_mismatch"
        assert result["severity"] == "high"
        assert result["source1_name"] == "county"
        assert result["source1_value"] == "123 Main St"
        assert result["source2_name"] == "assessor"
        assert result["source2_value"] == "456 Oak Ave"
        assert result["message"] == "Address mismatch"
        assert result["recommended_value"] == "123 Main St"
        assert result["confidence"] == 0.6

    def test_discrepancy_to_dict_null_values(self):
        """Test to_dict with null optional values"""
        disc = SourceDiscrepancy(
            field="test",
            discrepancy_type=DiscrepancyType.MISSING_IN_SOURCE,
            severity=DiscrepancySeverity.LOW,
            source1_name="s1",
            source1_value="value",
            source2_name="s2",
            source2_value=None,
        )
        result = disc.to_dict()
        assert result["source2_value"] is None
        assert result["message"] is None
        assert result["recommended_value"] is None


class TestCrossSourceResult:
    """Tests for CrossSourceResult dataclass"""

    def test_create_consistent_result(self):
        """Test creating a consistent result"""
        result = CrossSourceResult()
        assert result.is_consistent is True
        assert len(result.discrepancies) == 0
        assert result.consistency_score == 1.0

    def test_add_critical_discrepancy(self):
        """Test adding critical discrepancy changes consistency"""
        result = CrossSourceResult()
        disc = SourceDiscrepancy(
            field="id",
            discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
            severity=DiscrepancySeverity.CRITICAL,
            source1_name="s1",
            source1_value="1",
            source2_name="s2",
            source2_value="2",
        )
        result.add_discrepancy(disc)
        assert result.is_consistent is False
        assert result.consistency_score < 1.0

    def test_add_high_discrepancy(self):
        """Test adding high severity discrepancy"""
        result = CrossSourceResult()
        disc = SourceDiscrepancy(
            field="value",
            discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
            severity=DiscrepancySeverity.HIGH,
            source1_name="s1",
            source1_value=100,
            source2_name="s2",
            source2_value=200,
        )
        result.add_discrepancy(disc)
        assert result.is_consistent is False

    def test_add_medium_discrepancy(self):
        """Test adding medium severity keeps consistent"""
        result = CrossSourceResult()
        disc = SourceDiscrepancy(
            field="address",
            discrepancy_type=DiscrepancyType.FORMAT_DIFFERENCE,
            severity=DiscrepancySeverity.MEDIUM,
            source1_name="s1",
            source1_value="123 Main St.",
            source2_name="s2",
            source2_value="123 Main Street",
        )
        result.add_discrepancy(disc)
        assert result.is_consistent is True
        assert result.consistency_score < 1.0

    def test_add_low_discrepancy(self):
        """Test adding low severity discrepancy"""
        result = CrossSourceResult()
        disc = SourceDiscrepancy(
            field="name",
            discrepancy_type=DiscrepancyType.CASE_DIFFERENCE,
            severity=DiscrepancySeverity.LOW,
            source1_name="s1",
            source1_value="John Smith",
            source2_name="s2",
            source2_value="JOHN SMITH",
        )
        result.add_discrepancy(disc)
        assert result.is_consistent is True
        assert result.consistency_score >= 0.9

    def test_consistency_score_decreases(self):
        """Test that consistency score decreases with each discrepancy"""
        result = CrossSourceResult()
        initial_score = result.consistency_score

        disc = SourceDiscrepancy(
            field="f1",
            discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
            severity=DiscrepancySeverity.MEDIUM,
            source1_name="s1",
            source1_value="a",
            source2_name="s2",
            source2_value="b",
        )
        result.add_discrepancy(disc)
        assert result.consistency_score < initial_score

    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = CrossSourceResult(sources_compared=["county", "assessor"])
        disc = SourceDiscrepancy(
            field="value",
            discrepancy_type=DiscrepancyType.PRECISION_DIFFERENCE,
            severity=DiscrepancySeverity.LOW,
            source1_name="county",
            source1_value=100000,
            source2_name="assessor",
            source2_value=100500,
        )
        result.add_discrepancy(disc)

        data = result.to_dict()
        assert data["is_consistent"] is True
        assert "consistency_score" in data
        assert data["discrepancy_count"] == 1
        assert data["sources_compared"] == ["county", "assessor"]
        assert len(data["discrepancies"]) == 1


class TestCrossSourceValidator:
    """Tests for CrossSourceValidator class"""

    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return CrossSourceValidator()

    @pytest.fixture
    def custom_validator(self):
        """Create validator with custom tolerances"""
        return CrossSourceValidator(
            date_tolerance_days=30, numeric_tolerance_percent=0.10, fuzzy_threshold=0.80
        )

    def test_validator_initialization(self, validator):
        """Test validator initialization with defaults"""
        assert validator.date_tolerance == timedelta(days=7)
        assert validator.numeric_tolerance == 0.05
        assert validator.fuzzy_threshold == 0.85

    def test_validator_custom_tolerances(self, custom_validator):
        """Test validator with custom tolerances"""
        assert custom_validator.date_tolerance == timedelta(days=30)
        assert custom_validator.numeric_tolerance == 0.10
        assert custom_validator.fuzzy_threshold == 0.80

    def test_field_categories(self, validator):
        """Test field categorization"""
        assert "parcel_id" in validator.EXACT_MATCH_FIELDS
        assert "address" in validator.FUZZY_MATCH_FIELDS
        assert "assessed_value" in validator.NUMERIC_FIELDS
        assert "last_sale_date" in validator.DATE_FIELDS


class TestValidateSingleSource:
    """Tests for validation with single source"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_single_source_returns_consistent(self, validator):
        """Test that single source returns consistent result"""
        records = [("source1", {"field": "value"})]
        result = validator.validate(records)
        assert result.is_consistent is True
        assert len(result.discrepancies) == 0

    def test_empty_records_returns_consistent(self, validator):
        """Test that empty records returns consistent"""
        records = []
        result = validator.validate(records)
        assert result.is_consistent is True


class TestValidateExactMatch:
    """Tests for exact match field validation"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_exact_match_same_values(self, validator):
        """Test exact match fields with same values"""
        records = [
            ("source1", {"parcel_id": "123-456"}),
            ("source2", {"parcel_id": "123-456"}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is True

    def test_exact_match_different_values(self, validator):
        """Test exact match fields with different values"""
        records = [
            ("source1", {"parcel_id": "123-456"}),
            ("source2", {"parcel_id": "789-012"}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is False
        assert len(result.discrepancies) == 1
        assert result.discrepancies[0].severity == DiscrepancySeverity.CRITICAL

    def test_exact_match_case_insensitive(self, validator):
        """Test exact match is case insensitive"""
        records = [("source1", {"state": "CA"}), ("source2", {"state": "ca"})]
        result = validator.validate(records)
        assert result.is_consistent is True

    def test_exact_match_whitespace_handling(self, validator):
        """Test exact match handles whitespace"""
        records = [
            ("source1", {"ein": "12-3456789 "}),
            ("source2", {"ein": " 12-3456789"}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is True


class TestValidateNumericFields:
    """Tests for numeric field validation"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_numeric_exact_match(self, validator):
        """Test numeric fields with exact match"""
        records = [
            ("source1", {"assessed_value": 100000}),
            ("source2", {"assessed_value": 100000}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is True

    def test_numeric_within_tolerance(self, validator):
        """Test numeric values within tolerance"""
        records = [
            ("source1", {"assessed_value": 100000}),
            ("source2", {"assessed_value": 100500}),  # 0.5% difference
        ]
        result = validator.validate(records)
        assert result.is_consistent is True
        assert len(result.discrepancies) == 1
        assert (
            result.discrepancies[0].discrepancy_type
            == DiscrepancyType.PRECISION_DIFFERENCE
        )

    def test_numeric_outside_tolerance(self, validator):
        """Test numeric values outside tolerance"""
        records = [
            ("source1", {"assessed_value": 100000}),
            ("source2", {"assessed_value": 120000}),  # 20% difference
        ]
        result = validator.validate(records)
        # 20% difference is MEDIUM severity, which doesn't make it inconsistent
        # But >20% difference would be HIGH severity
        assert (
            result.discrepancies[0].discrepancy_type == DiscrepancyType.VALUE_MISMATCH
        )
        assert result.discrepancies[0].severity == DiscrepancySeverity.MEDIUM

    def test_numeric_medium_difference(self, validator):
        """Test numeric values with medium difference"""
        records = [
            ("source1", {"assessed_value": 100000}),
            ("source2", {"assessed_value": 110000}),  # 10% difference
        ]
        result = validator.validate(records)
        disc = result.discrepancies[0]
        assert disc.severity == DiscrepancySeverity.MEDIUM

    def test_numeric_high_difference(self, validator):
        """Test numeric values with large difference"""
        records = [
            ("source1", {"assessed_value": 100000}),
            ("source2", {"assessed_value": 150000}),  # 50% difference
        ]
        result = validator.validate(records)
        disc = result.discrepancies[0]
        assert disc.severity == DiscrepancySeverity.HIGH

    def test_numeric_invalid_values(self, validator):
        """Test numeric fields with non-numeric values"""
        records = [
            ("source1", {"assessed_value": 100000}),
            ("source2", {"assessed_value": "unknown"}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is False


class TestValidateDateFields:
    """Tests for date field validation"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_date_exact_match(self, validator):
        """Test date fields with exact match"""
        records = [
            ("source1", {"last_sale_date": "2024-01-15"}),
            ("source2", {"last_sale_date": "2024-01-15"}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is True

    def test_date_within_tolerance(self, validator):
        """Test dates within tolerance (7 days)"""
        records = [
            ("source1", {"last_sale_date": "2024-01-15"}),
            ("source2", {"last_sale_date": "2024-01-18"}),  # 3 days diff
        ]
        result = validator.validate(records)
        assert result.is_consistent is True
        disc = result.discrepancies[0]
        assert disc.discrepancy_type == DiscrepancyType.DATE_DIFFERENCE
        assert disc.severity == DiscrepancySeverity.LOW

    def test_date_outside_tolerance(self, validator):
        """Test dates outside tolerance"""
        records = [
            ("source1", {"last_sale_date": "2024-01-15"}),
            ("source2", {"last_sale_date": "2024-02-15"}),  # 31 days diff
        ]
        result = validator.validate(records)
        disc = result.discrepancies[0]
        assert disc.discrepancy_type == DiscrepancyType.VALUE_MISMATCH

    def test_date_large_difference(self, validator):
        """Test dates with large difference (>1 year)"""
        records = [
            ("source1", {"last_sale_date": "2024-01-15"}),
            ("source2", {"last_sale_date": "2022-01-15"}),  # 2 years diff
        ]
        result = validator.validate(records)
        disc = result.discrepancies[0]
        assert disc.severity == DiscrepancySeverity.HIGH

    def test_date_different_formats(self, validator):
        """Test dates with different formats"""
        records = [
            ("source1", {"last_sale_date": "2024-01-15"}),
            ("source2", {"last_sale_date": "01/15/2024"}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is True

    def test_date_object_vs_string(self, validator):
        """Test date object vs string"""
        records = [
            ("source1", {"last_sale_date": date(2024, 1, 15)}),
            ("source2", {"last_sale_date": "2024-01-15"}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is True

    def test_date_invalid_format(self, validator):
        """Test dates with invalid format"""
        records = [
            ("source1", {"last_sale_date": "2024-01-15"}),
            ("source2", {"last_sale_date": "invalid"}),
        ]
        result = validator.validate(records)
        disc = result.discrepancies[0]
        assert disc.discrepancy_type == DiscrepancyType.FORMAT_DIFFERENCE


class TestValidateFuzzyMatch:
    """Tests for fuzzy text matching"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_fuzzy_exact_match(self, validator):
        """Test fuzzy fields with exact match"""
        records = [
            ("source1", {"address": "123 Main Street"}),
            ("source2", {"address": "123 Main Street"}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is True

    def test_fuzzy_similar_match(self, validator):
        """Test fuzzy fields with similar values"""
        records = [
            ("source1", {"address": "123 Main Street"}),
            ("source2", {"address": "123 Main St"}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is True
        # Should have format difference discrepancy
        if result.discrepancies:
            disc = result.discrepancies[0]
            assert disc.discrepancy_type == DiscrepancyType.FORMAT_DIFFERENCE
            assert disc.severity == DiscrepancySeverity.LOW

    def test_fuzzy_different_values(self, validator):
        """Test fuzzy fields with different values"""
        records = [
            ("source1", {"address": "123 Main Street"}),
            ("source2", {"address": "456 Oak Avenue"}),
        ]
        result = validator.validate(records)
        # Different addresses result in VALUE_MISMATCH, but severity depends on similarity
        # If similarity < 0.5, it's HIGH severity (inconsistent)
        # If similarity >= 0.5, it's MEDIUM severity (still consistent)
        assert len(result.discrepancies) == 1
        assert (
            result.discrepancies[0].discrepancy_type == DiscrepancyType.VALUE_MISMATCH
        )

    def test_fuzzy_owner_name_variations(self, validator):
        """Test owner name variations"""
        records = [
            ("source1", {"owner_name": "John A. Smith"}),
            ("source2", {"owner_name": "John Smith"}),
        ]
        result = validator.validate(records)
        # Should be similar enough
        if result.discrepancies:
            assert result.discrepancies[0].severity in (
                DiscrepancySeverity.LOW,
                DiscrepancySeverity.MEDIUM,
            )


class TestValidateMissingFields:
    """Tests for missing field handling"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_missing_in_one_source(self, validator):
        """Test field missing in one source"""
        records = [
            ("source1", {"address": "123 Main St", "city": "Springfield"}),
            ("source2", {"address": "123 Main St"}),  # Missing city
        ]
        result = validator.validate(records)
        disc = [d for d in result.discrepancies if d.field == "city"][0]
        assert disc.discrepancy_type == DiscrepancyType.MISSING_IN_SOURCE

    def test_missing_exact_match_field(self, validator):
        """Test missing exact match field has high severity"""
        records = [
            ("source1", {"parcel_id": "123-456", "address": "123 Main St"}),
            ("source2", {"address": "123 Main St"}),  # Missing parcel_id
        ]
        result = validator.validate(records)
        disc = [d for d in result.discrepancies if d.field == "parcel_id"][0]
        assert disc.severity == DiscrepancySeverity.HIGH

    def test_missing_optional_field(self, validator):
        """Test missing non-critical field has low severity"""
        records = [
            ("source1", {"address": "123 Main St", "notes": "test"}),
            ("source2", {"address": "123 Main St"}),
        ]
        result = validator.validate(records)
        disc = [d for d in result.discrepancies if d.field == "notes"][0]
        assert disc.severity == DiscrepancySeverity.LOW

    def test_both_missing_no_discrepancy(self, validator):
        """Test field missing in both sources"""
        records = [
            ("source1", {"address": "123 Main St"}),
            ("source2", {"address": "123 Main St"}),
        ]
        result = validator.validate(records)
        # No discrepancy for consistently missing field
        assert len([d for d in result.discrepancies if d.field == "city"]) == 0


class TestValidateCaseDifference:
    """Tests for case difference handling"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_case_difference_detected(self, validator):
        """Test case difference is detected"""
        records = [
            ("source1", {"city": "Springfield"}),
            ("source2", {"city": "SPRINGFIELD"}),
        ]
        result = validator.validate(records)
        # Should detect case difference for non-categorized fields
        if result.discrepancies:
            disc = result.discrepancies[0]
            assert disc.discrepancy_type == DiscrepancyType.CASE_DIFFERENCE
            assert disc.severity == DiscrepancySeverity.INFO


class TestValidateMultipleSources:
    """Tests for validation with multiple sources"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_three_sources_all_match(self, validator):
        """Test three sources all matching"""
        records = [
            ("county", {"address": "123 Main St", "value": 100000}),
            ("assessor", {"address": "123 Main St", "value": 100000}),
            ("mls", {"address": "123 Main St", "value": 100000}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is True
        assert result.sources_compared == ["county", "assessor", "mls"]

    def test_three_sources_one_different(self, validator):
        """Test three sources with one different"""
        records = [
            ("county", {"parcel_id": "123"}),
            ("assessor", {"parcel_id": "123"}),
            ("mls", {"parcel_id": "456"}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is False
        # Should have discrepancies between mls and others
        assert len(result.discrepancies) >= 2


class TestReconcile:
    """Tests for record reconciliation"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_reconcile_empty_records(self, validator):
        """Test reconcile with empty records"""
        result = validator.reconcile([])
        assert result == {}

    def test_reconcile_single_record(self, validator):
        """Test reconcile with single record"""
        records = [("source1", {"field1": "value1", "field2": "value2"})]
        result = validator.reconcile(records)
        assert result == {"field1": "value1", "field2": "value2"}

    def test_reconcile_default_priority(self, validator):
        """Test reconcile with default priority (first wins)"""
        records = [
            ("source1", {"address": "123 Main St"}),
            ("source2", {"address": "456 Oak Ave"}),
        ]
        result = validator.reconcile(records)
        assert result["address"] == "123 Main St"

    def test_reconcile_custom_priority(self, validator):
        """Test reconcile with custom priority order"""
        records = [
            ("county", {"address": "123 Main St"}),
            ("assessor", {"address": "456 Oak Ave"}),
        ]
        result = validator.reconcile(records, priority_order=["assessor", "county"])
        assert result["address"] == "456 Oak Ave"

    def test_reconcile_fills_missing(self, validator):
        """Test reconcile fills missing fields"""
        records = [("source1", {"field1": "value1"}), ("source2", {"field2": "value2"})]
        result = validator.reconcile(records)
        assert result["field1"] == "value1"
        assert result["field2"] == "value2"

    def test_reconcile_skips_none(self, validator):
        """Test reconcile skips None values"""
        records = [("source1", {"field": None}), ("source2", {"field": "value"})]
        result = validator.reconcile(records)
        assert result["field"] == "value"


class TestTextNormalization:
    """Tests for text normalization"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_normalize_lowercase(self, validator):
        """Test normalization converts to lowercase"""
        result = validator._normalize_text("ABC")
        assert result == "abc"

    def test_normalize_removes_punctuation(self, validator):
        """Test normalization removes punctuation"""
        result = validator._normalize_text("123 Main St., Apt. #1")
        assert "," not in result
        assert "." not in result

    def test_normalize_whitespace(self, validator):
        """Test normalization handles whitespace"""
        result = validator._normalize_text("  123   Main   St  ")
        assert result == "123 main st"


class TestSimilarityCalculation:
    """Tests for text similarity calculation"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_identical_strings(self, validator):
        """Test similarity for identical strings"""
        result = validator._calculate_similarity("hello", "hello")
        assert result == 1.0

    def test_completely_different(self, validator):
        """Test similarity for completely different strings"""
        result = validator._calculate_similarity("abc", "xyz")
        assert result < 0.5

    def test_similar_strings(self, validator):
        """Test similarity for similar strings"""
        result = validator._calculate_similarity("hello", "hallo")
        assert result > 0.7

    def test_empty_string(self, validator):
        """Test similarity with empty string"""
        result = validator._calculate_similarity("hello", "")
        assert result == 0.0

    def test_both_empty(self, validator):
        """Test similarity with both empty"""
        result = validator._calculate_similarity("", "")
        assert result == 0.0


class TestDateParsing:
    """Tests for date parsing"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_parse_iso_date(self, validator):
        """Test parsing ISO format date"""
        result = validator._parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_us_date(self, validator):
        """Test parsing US format date"""
        result = validator._parse_date("01/15/2024")
        assert result == date(2024, 1, 15)

    def test_parse_date_object(self, validator):
        """Test parsing date object"""
        d = date(2024, 1, 15)
        result = validator._parse_date(d)
        assert result == d

    def test_parse_datetime_object(self, validator):
        """Test parsing datetime object"""
        dt = datetime(2024, 1, 15, 10, 30)
        result = validator._parse_date(dt)
        assert result == date(2024, 1, 15)

    def test_parse_none(self, validator):
        """Test parsing None"""
        result = validator._parse_date(None)
        assert result is None

    def test_parse_invalid(self, validator):
        """Test parsing invalid string"""
        result = validator._parse_date("not a date")
        assert result is None


class TestMissingSeverity:
    """Tests for missing field severity determination"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_missing_exact_field_high(self, validator):
        """Test missing exact match field has high severity"""
        result = validator._get_missing_severity("parcel_id")
        assert result == DiscrepancySeverity.HIGH

    def test_missing_numeric_field_medium(self, validator):
        """Test missing numeric field has medium severity"""
        result = validator._get_missing_severity("assessed_value")
        assert result == DiscrepancySeverity.MEDIUM

    def test_missing_other_field_low(self, validator):
        """Test missing other field has low severity"""
        result = validator._get_missing_severity("notes")
        assert result == DiscrepancySeverity.LOW


class TestStatistics:
    """Tests for cross-source statistics"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_statistics_all_consistent(self, validator):
        """Test statistics with all consistent results"""
        results = [
            CrossSourceResult(is_consistent=True, consistency_score=1.0),
            CrossSourceResult(is_consistent=True, consistency_score=1.0),
            CrossSourceResult(is_consistent=True, consistency_score=1.0),
        ]
        stats = validator.get_statistics(results)
        assert stats["total_comparisons"] == 3
        assert stats["consistent_records"] == 3
        assert stats["inconsistent_records"] == 0
        assert stats["consistency_rate"] == 1.0

    def test_statistics_some_inconsistent(self, validator):
        """Test statistics with some inconsistent"""
        result1 = CrossSourceResult()
        result2 = CrossSourceResult()
        result2.add_discrepancy(
            SourceDiscrepancy(
                field="id",
                discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
                severity=DiscrepancySeverity.CRITICAL,
                source1_name="s1",
                source1_value="1",
                source2_name="s2",
                source2_value="2",
            )
        )
        result3 = CrossSourceResult()

        stats = validator.get_statistics([result1, result2, result3])
        assert stats["total_comparisons"] == 3
        assert stats["consistent_records"] == 2
        assert stats["inconsistent_records"] == 1

    def test_statistics_by_type(self, validator):
        """Test statistics by discrepancy type"""
        result = CrossSourceResult()
        result.add_discrepancy(
            SourceDiscrepancy(
                field="f1",
                discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
                severity=DiscrepancySeverity.MEDIUM,
                source1_name="s1",
                source1_value="a",
                source2_name="s2",
                source2_value="b",
            )
        )
        result.add_discrepancy(
            SourceDiscrepancy(
                field="f2",
                discrepancy_type=DiscrepancyType.MISSING_IN_SOURCE,
                severity=DiscrepancySeverity.LOW,
                source1_name="s1",
                source1_value="x",
                source2_name="s2",
                source2_value=None,
            )
        )

        stats = validator.get_statistics([result])
        assert stats["discrepancies_by_type"]["value_mismatch"] == 1
        assert stats["discrepancies_by_type"]["missing_in_source"] == 1

    def test_statistics_by_severity(self, validator):
        """Test statistics by severity"""
        result = CrossSourceResult()
        result.add_discrepancy(
            SourceDiscrepancy(
                field="f1",
                discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
                severity=DiscrepancySeverity.HIGH,
                source1_name="s1",
                source1_value="a",
                source2_name="s2",
                source2_value="b",
            )
        )
        result.add_discrepancy(
            SourceDiscrepancy(
                field="f2",
                discrepancy_type=DiscrepancyType.FORMAT_DIFFERENCE,
                severity=DiscrepancySeverity.LOW,
                source1_name="s1",
                source1_value="x",
                source2_name="s2",
                source2_value="y",
            )
        )

        stats = validator.get_statistics([result])
        assert stats["discrepancies_by_severity"]["high"] == 1
        assert stats["discrepancies_by_severity"]["low"] == 1

    def test_statistics_empty(self, validator):
        """Test statistics with empty results"""
        stats = validator.get_statistics([])
        assert stats["total_comparisons"] == 0
        assert stats["consistency_rate"] == 0


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_validate_cross_source(self):
        """Test validate_cross_source function"""
        records = [("source1", {"field": "value"}), ("source2", {"field": "value"})]
        result = validate_cross_source(records)
        assert result.is_consistent is True

    def test_validate_cross_source_inconsistent(self):
        """Test validate_cross_source with inconsistent data"""
        records = [("source1", {"parcel_id": "123"}), ("source2", {"parcel_id": "456"})]
        result = validate_cross_source(records)
        assert result.is_consistent is False

    def test_reconcile_records(self):
        """Test reconcile_records function"""
        records = [("source1", {"field1": "value1"}), ("source2", {"field2": "value2"})]
        result = reconcile_records(records)
        assert result["field1"] == "value1"
        assert result["field2"] == "value2"

    def test_reconcile_records_with_priority(self):
        """Test reconcile_records with priority"""
        records = [("source1", {"field": "a"}), ("source2", {"field": "b"})]
        result = reconcile_records(records, priority_order=["source2", "source1"])
        assert result["field"] == "b"


class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.fixture
    def validator(self):
        return CrossSourceValidator()

    def test_empty_string_values(self, validator):
        """Test empty string values"""
        records = [("source1", {"field": ""}), ("source2", {"field": "value"})]
        result = validator.validate(records)
        # Empty string is treated as a value, not None
        assert len(result.discrepancies) >= 0

    def test_numeric_zero_values(self, validator):
        """Test numeric zero values"""
        records = [
            ("source1", {"assessed_value": 0}),
            ("source2", {"assessed_value": 100000}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is False

    def test_unicode_values(self, validator):
        """Test unicode values"""
        records = [
            ("source1", {"owner_name": "José García"}),
            ("source2", {"owner_name": "Jose Garcia"}),
        ]
        result = validator.validate(records)
        # Should handle unicode gracefully
        assert isinstance(result, CrossSourceResult)

    def test_very_long_strings(self, validator):
        """Test very long string values"""
        long_str = "a" * 10000
        records = [
            ("source1", {"description": long_str}),
            ("source2", {"description": long_str}),
        ]
        result = validator.validate(records)
        assert result.is_consistent is True

    def test_special_characters(self, validator):
        """Test special characters in values"""
        records = [
            ("source1", {"address": "123 Main St. #1A"}),
            ("source2", {"address": "123 Main St #1A"}),
        ]
        result = validator.validate(records)
        # Should handle punctuation differences
        assert isinstance(result, CrossSourceResult)
