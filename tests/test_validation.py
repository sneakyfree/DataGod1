"""
Tests for Validation modules — coverage for validation/ (0% → 50%+)
"""

from datetime import date, datetime

import pytest

from datagod.validation.business_rules import (
    BusinessRuleValidator,
    RuleResult,
    RuleSeverity,
    RuleViolation,
    validate_business_record,
    validate_court_record,
    validate_property_record,
)
from datagod.validation.schema_validator import (
    BaseSchema,
    CourtCaseSchema,
    DeedSchema,
    FieldSchema,
    FieldType,
    PropertySchema,
    SchemaValidator,
    ValidationError,
    ValidationResult,
    ValidationSeverity,
)

# ============================================================
# Schema Validator Tests
# ============================================================


class TestFieldType:
    def test_enum_values(self):
        assert FieldType.STRING.value == "string"
        assert FieldType.INTEGER.value == "integer"
        assert FieldType.FLOAT.value == "float"
        assert FieldType.BOOLEAN.value == "boolean"
        assert FieldType.DATE.value == "date"


class TestValidationError:
    def test_create(self):
        err = ValidationError(field="name", message="Required")
        assert err.field == "name"
        assert err.message == "Required"
        assert err.severity == ValidationSeverity.ERROR

    def test_to_dict(self):
        err = ValidationError(
            field="age", message="Too low", expected="18", actual="15"
        )
        d = err.to_dict()
        assert d["field"] == "age"
        assert d["expected"] == "18"


class TestValidationResult:
    def test_valid_result(self):
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_add_error(self):
        result = ValidationResult(is_valid=True)
        result.add_error("name", "Required field")
        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_add_warning(self):
        result = ValidationResult(is_valid=True)
        result.add_warning("age", "Unusual value")
        assert len(result.warnings) == 1
        assert result.is_valid is True

    def test_to_dict(self):
        result = ValidationResult(is_valid=True, record_type="property")
        d = result.to_dict()
        assert d["is_valid"] is True
        assert d["record_type"] == "property"


class TestFieldSchema:
    def test_create(self):
        field = FieldSchema("name", FieldType.STRING, required=True, max_length=100)
        assert field.name == "name"
        assert field.required is True
        assert field.max_length == 100


class TestBaseSchema:
    def test_create(self):
        fields = [
            FieldSchema("id", FieldType.STRING, required=True),
            FieldSchema("name", FieldType.STRING, required=False),
        ]
        schema = BaseSchema("test", fields)
        assert schema.schema_name == "test"

    def test_get_field(self):
        fields = [FieldSchema("id", FieldType.STRING, required=True)]
        schema = BaseSchema("test", fields)
        assert schema.get_field("id") is not None
        assert schema.get_field("nonexistent") is None

    def test_get_required_fields(self):
        fields = [
            FieldSchema("id", FieldType.STRING, required=True),
            FieldSchema("name", FieldType.STRING, required=False),
            FieldSchema("email", FieldType.STRING, required=True),
        ]
        schema = BaseSchema("test", fields)
        required = schema.get_required_fields()
        assert "id" in required
        assert "email" in required
        assert "name" not in required


class TestPropertySchema:
    def test_creates_schema(self):
        schema = PropertySchema()
        assert schema.schema_name == "property"
        assert schema.get_field("parcel_id") is not None


class TestDeedSchema:
    def test_creates_schema(self):
        schema = DeedSchema()
        assert schema.schema_name == "deed"
        assert schema.get_field("document_number") is not None


class TestCourtCaseSchema:
    def test_creates_schema(self):
        schema = CourtCaseSchema()
        assert schema.schema_name == "court_case"
        assert schema.get_field("case_number") is not None


class TestSchemaValidator:
    def setup_method(self):
        self.validator = SchemaValidator()

    def test_validate_valid_property(self):
        record = {
            "parcel_id": "ABC-123",
            "address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
            "county": "New York",
        }
        # validate(record, schema_name)
        result = self.validator.validate(record, "property")
        assert isinstance(result, ValidationResult)

    def test_validate_missing_required(self):
        record = {}
        result = self.validator.validate(record, "property")
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_deed(self):
        record = {
            "document_number": "DOC-001",
            "document_type": "WARRANTY_DEED",
            "recording_date": "2024-01-15",
            "county": "Kings",
            "state": "NY",
        }
        result = self.validator.validate(record, "deed")
        assert isinstance(result, ValidationResult)

    def test_validate_court_case(self):
        record = {
            "case_number": "CASE-2024-001",
            "court_name": "Superior Court",
            "case_type": "Civil",
            "filing_date": "2024-03-01",
            "county": "Los Angeles",
            "state": "CA",
        }
        result = self.validator.validate(record, "court_case")
        assert isinstance(result, ValidationResult)


# ============================================================
# Business Rules Tests
# ============================================================


class TestRuleSeverity:
    def test_values(self):
        assert RuleSeverity.CRITICAL.value == "critical"
        assert RuleSeverity.HIGH.value == "high"
        assert RuleSeverity.MEDIUM.value == "medium"
        assert RuleSeverity.LOW.value == "low"


class TestRuleViolation:
    def test_create(self):
        v = RuleViolation(rule_id="R001", rule_name="Test", message="Failed")
        assert v.rule_id == "R001"

    def test_to_dict(self):
        v = RuleViolation(
            rule_id="R001",
            rule_name="Test",
            message="Failed",
            severity=RuleSeverity.HIGH,
        )
        d = v.to_dict()
        assert d["rule_id"] == "R001"


class TestRuleResult:
    def test_valid_by_default(self):
        result = RuleResult()
        assert result.is_valid is True

    def test_add_violation_medium_stays_valid(self):
        # MEDIUM severity does NOT set is_valid=False per actual code
        result = RuleResult()
        result.add_violation(
            "R001", "Test Rule", "Something wrong", severity=RuleSeverity.MEDIUM
        )
        assert len(result.violations) == 1
        assert result.is_valid is True

    def test_add_violation_high_invalidates(self):
        result = RuleResult()
        result.add_violation("R001", "Test Rule", "Serious", severity=RuleSeverity.HIGH)
        assert result.is_valid is False

    def test_add_violation_critical_invalidates(self):
        result = RuleResult()
        result.add_violation(
            "R001", "Test Rule", "Critical", severity=RuleSeverity.CRITICAL
        )
        assert result.is_valid is False

    def test_to_dict(self):
        result = RuleResult(record_type="property", record_id="P001")
        d = result.to_dict()
        assert d["record_type"] == "property"


class TestBusinessRuleValidator:
    def setup_method(self):
        self.validator = BusinessRuleValidator()

    def test_validate_valid_property(self):
        record = {
            "parcel_id": "APN-123",
            "address": "456 Oak Ave",
            "city": "Chicago",
            "state": "IL",
            "assessed_value": 250000,
            "market_value": 280000,
            "year_built": 1990,
        }
        result = self.validator.validate_property(record)
        assert isinstance(result, RuleResult)

    def test_validate_property_negative_value(self):
        record = {
            "parcel_id": "APN-999",
            "assessed_value": -100,
        }
        result = self.validator.validate_property(record)
        assert len(result.violations) > 0

    def test_validate_deed(self):
        record = {
            "document_number": "D-001",
            "document_type": "WARRANTY_DEED",
            "recording_date": "2024-01-15",
            "grantor": "John Smith",
            "grantee": "Jane Doe",
            "consideration": 500000,
        }
        result = self.validator.validate_deed(record)
        assert isinstance(result, RuleResult)

    def test_validate_court_case(self):
        record = {
            "case_number": "2024-CV-001",
            "case_type": "Civil",
            "filing_date": "2024-03-01",
            "plaintiff": "John Doe",
            "defendant": "ABC Corp",
            "amount": 50000,
        }
        result = self.validator.validate_court_case(record)
        assert isinstance(result, RuleResult)

    def test_validate_business(self):
        record = {
            "entity_name": "ABC Corporation",
            "entity_type": "Corporation",
            "state_of_formation": "DE",
            "formation_date": "2020-01-01",
            "status": "Active",
        }
        result = self.validator.validate_business(record)
        assert isinstance(result, RuleResult)

    def test_parse_date_string(self):
        result = self.validator._parse_date("2024-01-15")
        assert result is not None

    def test_parse_date_object(self):
        result = self.validator._parse_date(date(2024, 1, 15))
        assert result is not None

    def test_parse_invalid_date(self):
        result = self.validator._parse_date("not-a-date")
        assert result is None

    def test_valid_alaska_coordinates(self):
        # Alaska: lat 51-72, lon -180 to -129
        assert self.validator._is_valid_us_coordinates(64.0, -150.0) is True

    def test_valid_hawaii_coordinates(self):
        # Hawaii: lat 18-23, lon -161 to -154
        assert self.validator._is_valid_us_coordinates(21.0, -157.0) is True

    def test_invalid_coordinates_paris(self):
        # Paris, France — not US territory
        assert self.validator._is_valid_us_coordinates(48.8566, 2.3522) is False

    def test_get_statistics(self):
        results = [
            self.validator.validate_property({"parcel_id": "A"}),
            self.validator.validate_property(
                {"parcel_id": "B", "assessed_value": 100000}
            ),
        ]
        stats = self.validator.get_statistics(results)
        assert isinstance(stats, dict)


class TestConvenienceFunctions:
    def test_validate_property_record(self):
        result = validate_property_record(
            {"parcel_id": "P001", "assessed_value": 200000}
        )
        assert isinstance(result, RuleResult)

    def test_validate_court_record(self):
        result = validate_court_record({"case_number": "C001"})
        assert isinstance(result, RuleResult)

    def test_validate_business_record(self):
        result = validate_business_record({"entity_name": "Test Corp"})
        assert isinstance(result, RuleResult)
