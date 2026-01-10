"""
Comprehensive tests for the Schema Validator.

Tests cover:
- FieldType enum
- ValidationSeverity enum
- ValidationError dataclass
- ValidationResult dataclass
- FieldSchema dataclass
- BaseSchema class
- Specific schema classes (Property, Deed, CourtCase, BusinessEntity, Person)
- SchemaValidator class
- Type validation
- Required field validation
- Pattern matching
- Length constraints
- Value constraints
- Batch validation
"""

import pytest
from datetime import date, datetime
from datagod.validation.schema_validator import (
    FieldType,
    ValidationSeverity,
    ValidationError,
    ValidationResult,
    FieldSchema,
    BaseSchema,
    PropertySchema,
    DeedSchema,
    CourtCaseSchema,
    BusinessEntitySchema,
    PersonSchema,
    SchemaValidator,
    validate_record,
)


class TestFieldTypeEnum:
    """Tests for FieldType enum"""

    def test_all_field_types_exist(self):
        """Test that all expected field types are defined"""
        assert FieldType.STRING is not None
        assert FieldType.INTEGER is not None
        assert FieldType.FLOAT is not None
        assert FieldType.BOOLEAN is not None
        assert FieldType.DATE is not None
        assert FieldType.DATETIME is not None
        assert FieldType.LIST is not None
        assert FieldType.DICT is not None
        assert FieldType.ANY is not None

    def test_field_type_values(self):
        """Test that field types have correct string values"""
        assert FieldType.STRING.value == "string"
        assert FieldType.INTEGER.value == "integer"
        assert FieldType.FLOAT.value == "float"
        assert FieldType.BOOLEAN.value == "boolean"
        assert FieldType.DATE.value == "date"
        assert FieldType.DATETIME.value == "datetime"


class TestValidationSeverityEnum:
    """Tests for ValidationSeverity enum"""

    def test_all_severities_exist(self):
        """Test that all severity levels are defined"""
        assert ValidationSeverity.ERROR is not None
        assert ValidationSeverity.WARNING is not None
        assert ValidationSeverity.INFO is not None

    def test_severity_values(self):
        """Test severity string values"""
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"


class TestValidationError:
    """Tests for ValidationError dataclass"""

    def test_create_validation_error(self):
        """Test creating a validation error"""
        error = ValidationError(
            field="name",
            message="Field is required",
            severity=ValidationSeverity.ERROR
        )
        assert error.field == "name"
        assert error.message == "Field is required"
        assert error.severity == ValidationSeverity.ERROR

    def test_validation_error_with_expected_actual(self):
        """Test validation error with expected and actual values"""
        error = ValidationError(
            field="age",
            message="Value out of range",
            severity=ValidationSeverity.ERROR,
            expected="18-100",
            actual=150
        )
        assert error.expected == "18-100"
        assert error.actual == 150

    def test_validation_error_to_dict(self):
        """Test converting validation error to dictionary"""
        error = ValidationError(
            field="email",
            message="Invalid format",
            severity=ValidationSeverity.ERROR,
            expected="valid email",
            actual="notanemail"
        )
        result = error.to_dict()
        assert result['field'] == "email"
        assert result['message'] == "Invalid format"
        assert result['severity'] == "error"
        assert result['expected'] == "valid email"
        assert result['actual'] == "notanemail"

    def test_validation_error_to_dict_null_values(self):
        """Test to_dict with null expected/actual"""
        error = ValidationError(
            field="test",
            message="Test error"
        )
        result = error.to_dict()
        assert result['expected'] is None
        assert result['actual'] is None


class TestValidationResult:
    """Tests for ValidationResult dataclass"""

    def test_create_valid_result(self):
        """Test creating a valid result"""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_create_invalid_result(self):
        """Test creating an invalid result"""
        error = ValidationError(field="test", message="Error")
        result = ValidationResult(is_valid=False, errors=[error])
        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_add_error(self):
        """Test adding an error to result"""
        result = ValidationResult(is_valid=True)
        result.add_error("field1", "Error message", expected="foo", actual="bar")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "field1"

    def test_add_warning(self):
        """Test adding a warning to result"""
        result = ValidationResult(is_valid=True)
        result.add_warning("field1", "Warning message")
        assert result.is_valid is True  # Warnings don't invalidate
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == ValidationSeverity.WARNING

    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = ValidationResult(
            is_valid=True,
            record_type="property",
            record_id="123"
        )
        result.add_warning("field1", "Minor issue")

        data = result.to_dict()
        assert data['is_valid'] is True
        assert data['error_count'] == 0
        assert data['warning_count'] == 1
        assert data['record_type'] == "property"
        assert data['record_id'] == "123"


class TestFieldSchema:
    """Tests for FieldSchema dataclass"""

    def test_create_basic_field_schema(self):
        """Test creating a basic field schema"""
        schema = FieldSchema(
            name="test_field",
            field_type=FieldType.STRING,
            required=True
        )
        assert schema.name == "test_field"
        assert schema.field_type == FieldType.STRING
        assert schema.required is True

    def test_field_schema_with_constraints(self):
        """Test field schema with length constraints"""
        schema = FieldSchema(
            name="name",
            field_type=FieldType.STRING,
            min_length=1,
            max_length=100
        )
        assert schema.min_length == 1
        assert schema.max_length == 100

    def test_field_schema_with_pattern(self):
        """Test field schema with regex pattern"""
        schema = FieldSchema(
            name="zip_code",
            field_type=FieldType.STRING,
            pattern=r'^\d{5}$'
        )
        assert schema.pattern == r'^\d{5}$'

    def test_field_schema_with_allowed_values(self):
        """Test field schema with allowed values"""
        schema = FieldSchema(
            name="status",
            field_type=FieldType.STRING,
            allowed_values=['ACTIVE', 'INACTIVE', 'PENDING']
        )
        assert 'ACTIVE' in schema.allowed_values
        assert len(schema.allowed_values) == 3

    def test_field_schema_with_value_constraints(self):
        """Test field schema with numeric constraints"""
        schema = FieldSchema(
            name="age",
            field_type=FieldType.INTEGER,
            min_value=0,
            max_value=150
        )
        assert schema.min_value == 0
        assert schema.max_value == 150

    def test_field_schema_with_custom_validator(self):
        """Test field schema with custom validator"""
        def is_even(value):
            return value % 2 == 0

        schema = FieldSchema(
            name="even_number",
            field_type=FieldType.INTEGER,
            custom_validator=is_even,
            error_message="Must be an even number"
        )
        assert schema.custom_validator is not None
        assert schema.error_message == "Must be an even number"


class TestBaseSchema:
    """Tests for BaseSchema class"""

    def test_create_base_schema(self):
        """Test creating a base schema"""
        fields = [
            FieldSchema("id", FieldType.STRING, required=True),
            FieldSchema("name", FieldType.STRING, required=True),
            FieldSchema("optional", FieldType.STRING, required=False),
        ]
        schema = BaseSchema("test_schema", fields)
        assert schema.schema_name == "test_schema"
        assert len(schema.fields) == 3

    def test_get_field(self):
        """Test getting a field from schema"""
        fields = [
            FieldSchema("id", FieldType.STRING, required=True),
        ]
        schema = BaseSchema("test", fields)
        field = schema.get_field("id")
        assert field is not None
        assert field.name == "id"

    def test_get_nonexistent_field(self):
        """Test getting a field that doesn't exist"""
        schema = BaseSchema("test", [])
        field = schema.get_field("nonexistent")
        assert field is None

    def test_get_required_fields(self):
        """Test getting list of required fields"""
        fields = [
            FieldSchema("id", FieldType.STRING, required=True),
            FieldSchema("name", FieldType.STRING, required=True),
            FieldSchema("optional", FieldType.STRING, required=False),
        ]
        schema = BaseSchema("test", fields)
        required = schema.get_required_fields()
        assert len(required) == 2
        assert "id" in required
        assert "name" in required
        assert "optional" not in required


class TestPropertySchema:
    """Tests for PropertySchema"""

    def test_property_schema_creation(self):
        """Test creating property schema"""
        schema = PropertySchema()
        assert schema.schema_name == "property"

    def test_property_required_fields(self):
        """Test property schema required fields"""
        schema = PropertySchema()
        required = schema.get_required_fields()
        assert "parcel_id" in required
        assert "address" in required
        assert "city" in required
        assert "state" in required
        assert "zip_code" in required

    def test_property_optional_fields_exist(self):
        """Test that optional fields are defined"""
        schema = PropertySchema()
        assert schema.get_field("bedrooms") is not None
        assert schema.get_field("bathrooms") is not None
        assert schema.get_field("square_feet") is not None
        assert schema.get_field("year_built") is not None

    def test_property_state_field_pattern(self):
        """Test state field has pattern constraint"""
        schema = PropertySchema()
        state_field = schema.get_field("state")
        assert state_field.pattern == r'^[A-Z]{2}$'

    def test_property_type_allowed_values(self):
        """Test property_type has allowed values"""
        schema = PropertySchema()
        prop_type = schema.get_field("property_type")
        assert 'SFR' in prop_type.allowed_values
        assert 'CONDO' in prop_type.allowed_values


class TestDeedSchema:
    """Tests for DeedSchema"""

    def test_deed_schema_creation(self):
        """Test creating deed schema"""
        schema = DeedSchema()
        assert schema.schema_name == "deed"

    def test_deed_required_fields(self):
        """Test deed schema required fields"""
        schema = DeedSchema()
        required = schema.get_required_fields()
        assert "document_number" in required
        assert "document_type" in required
        assert "recording_date" in required
        assert "county" in required
        assert "state" in required

    def test_deed_document_type_allowed_values(self):
        """Test document_type has allowed values"""
        schema = DeedSchema()
        doc_type = schema.get_field("document_type")
        assert 'DEED' in doc_type.allowed_values
        assert 'MORTGAGE' in doc_type.allowed_values
        assert 'LIEN' in doc_type.allowed_values


class TestCourtCaseSchema:
    """Tests for CourtCaseSchema"""

    def test_court_case_schema_creation(self):
        """Test creating court case schema"""
        schema = CourtCaseSchema()
        assert schema.schema_name == "court_case"

    def test_court_case_required_fields(self):
        """Test court case required fields"""
        schema = CourtCaseSchema()
        required = schema.get_required_fields()
        assert "case_number" in required
        assert "case_type" in required
        assert "court_name" in required
        assert "filing_date" in required
        assert "state" in required

    def test_court_case_type_allowed_values(self):
        """Test case_type allowed values"""
        schema = CourtCaseSchema()
        case_type = schema.get_field("case_type")
        assert 'CIVIL' in case_type.allowed_values
        assert 'CRIMINAL' in case_type.allowed_values
        assert 'FAMILY' in case_type.allowed_values


class TestBusinessEntitySchema:
    """Tests for BusinessEntitySchema"""

    def test_business_schema_creation(self):
        """Test creating business entity schema"""
        schema = BusinessEntitySchema()
        assert schema.schema_name == "business_entity"

    def test_business_required_fields(self):
        """Test business entity required fields"""
        schema = BusinessEntitySchema()
        required = schema.get_required_fields()
        assert "entity_id" in required
        assert "entity_name" in required
        assert "entity_type" in required
        assert "state" in required

    def test_business_ein_pattern(self):
        """Test EIN field pattern"""
        schema = BusinessEntitySchema()
        ein_field = schema.get_field("ein")
        assert ein_field.pattern == r'^\d{2}-\d{7}$'


class TestPersonSchema:
    """Tests for PersonSchema"""

    def test_person_schema_creation(self):
        """Test creating person schema"""
        schema = PersonSchema()
        assert schema.schema_name == "person"

    def test_person_required_fields(self):
        """Test person required fields"""
        schema = PersonSchema()
        required = schema.get_required_fields()
        assert "person_id" in required
        assert "first_name" in required
        assert "last_name" in required

    def test_person_email_pattern(self):
        """Test email field pattern"""
        schema = PersonSchema()
        email_field = schema.get_field("email")
        assert email_field.pattern is not None


class TestSchemaValidator:
    """Tests for SchemaValidator class"""

    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return SchemaValidator()

    @pytest.fixture
    def non_strict_validator(self):
        """Create non-strict validator"""
        return SchemaValidator(strict_mode=False)

    def test_validator_initialization(self):
        """Test validator initialization"""
        validator = SchemaValidator()
        assert validator.strict_mode is True

    def test_validator_non_strict_mode(self):
        """Test non-strict mode initialization"""
        validator = SchemaValidator(strict_mode=False)
        assert validator.strict_mode is False

    def test_validate_valid_property(self, validator, valid_property_record):
        """Test validating a valid property record"""
        result = validator.validate(valid_property_record, "property")
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_valid_deed(self, validator, valid_deed_record):
        """Test validating a valid deed record"""
        result = validator.validate(valid_deed_record, "deed")
        assert result.is_valid is True

    def test_validate_valid_court_case(self, validator, valid_court_case_record):
        """Test validating a valid court case record"""
        result = validator.validate(valid_court_case_record, "court_case")
        assert result.is_valid is True

    def test_validate_valid_business(self, validator, valid_business_entity_record):
        """Test validating a valid business entity record"""
        result = validator.validate(valid_business_entity_record, "business_entity")
        assert result.is_valid is True

    def test_validate_valid_person(self, validator, valid_person_record):
        """Test validating a valid person record"""
        result = validator.validate(valid_person_record, "person")
        assert result.is_valid is True

    def test_validate_unknown_schema(self, validator):
        """Test validation with unknown schema"""
        with pytest.raises(ValueError) as exc_info:
            validator.validate({}, "unknown_schema")
        assert "Unknown schema" in str(exc_info.value)

    def test_validate_schema_object(self, validator):
        """Test validation with schema object instead of string"""
        schema = PropertySchema()
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210"
        }
        result = validator.validate(record, schema)
        assert result.is_valid is True

    def test_validate_missing_required_field(self, validator):
        """Test validation with missing required field"""
        record = {
            "parcel_id": "123",
            # Missing address, city, state, zip_code
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False
        assert len(result.errors) >= 4  # At least 4 required fields missing

    def test_validate_null_required_field(self, validator):
        """Test validation with null required field"""
        record = {
            "parcel_id": "123",
            "address": None,  # Required but null
            "city": "Test",
            "state": "CA",
            "zip_code": "90210"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "address" in error_fields


class TestSchemaValidatorTypeValidation:
    """Tests for type validation"""

    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    def test_string_type_valid(self, validator):
        """Test valid string type"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_string_type_invalid(self, validator):
        """Test invalid string type (number instead of string)"""
        record = {
            "parcel_id": 123,  # Should be string
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "parcel_id" in error_fields

    def test_integer_type_valid(self, validator):
        """Test valid integer type"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "bedrooms": 3
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_integer_type_invalid(self, validator):
        """Test invalid integer type (string instead of int)"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "bedrooms": "three"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False

    def test_float_type_accepts_int(self, validator):
        """Test that float type accepts integers"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "bathrooms": 2  # Int should be accepted for float field
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_date_type_iso_format(self, validator):
        """Test date type with ISO format"""
        record = {
            "document_number": "123",
            "document_type": "DEED",
            "recording_date": "2024-01-15",
            "county": "Test",
            "state": "CA"
        }
        result = validator.validate(record, "deed")
        assert result.is_valid is True

    def test_date_type_us_format(self, validator):
        """Test date type with US format"""
        record = {
            "document_number": "123",
            "document_type": "DEED",
            "recording_date": "01/15/2024",
            "county": "Test",
            "state": "CA"
        }
        result = validator.validate(record, "deed")
        assert result.is_valid is True

    def test_date_type_object(self, validator):
        """Test date type with date object"""
        record = {
            "document_number": "123",
            "document_type": "DEED",
            "recording_date": date(2024, 1, 15),
            "county": "Test",
            "state": "CA"
        }
        result = validator.validate(record, "deed")
        assert result.is_valid is True

    def test_boolean_type_not_int(self, validator):
        """Test that boolean type doesn't accept int"""
        fields = [FieldSchema("flag", FieldType.BOOLEAN, required=True)]
        schema = BaseSchema("test", fields)

        record = {"flag": 1}
        result = validator.validate(record, schema)
        assert result.is_valid is False


class TestSchemaValidatorLengthConstraints:
    """Tests for length constraint validation"""

    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    def test_min_length_valid(self, validator):
        """Test valid min length"""
        record = {
            "parcel_id": "123",
            "address": "123 Main Street",  # >= 5 chars
            "city": "Test",
            "state": "CA",
            "zip_code": "90210"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_min_length_invalid(self, validator):
        """Test invalid min length"""
        record = {
            "parcel_id": "123",
            "address": "A",  # Too short (< 5 chars)
            "city": "Test",
            "state": "CA",
            "zip_code": "90210"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "address" in error_fields

    def test_max_length_invalid(self, validator):
        """Test invalid max length"""
        record = {
            "parcel_id": "A" * 100,  # Too long (> 50 chars)
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False


class TestSchemaValidatorPatternValidation:
    """Tests for pattern validation"""

    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    def test_state_pattern_valid(self, validator):
        """Test valid state pattern"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",  # Valid 2-letter uppercase
            "zip_code": "90210"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_state_pattern_invalid_lowercase(self, validator):
        """Test invalid state pattern (lowercase)"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "ca",  # Lowercase invalid
            "zip_code": "90210"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False

    def test_state_pattern_invalid_length(self, validator):
        """Test invalid state pattern (too long)"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CAL",  # Too long
            "zip_code": "90210"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False

    def test_zip_pattern_valid_5digit(self, validator):
        """Test valid 5-digit zip code"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_zip_pattern_valid_9digit(self, validator):
        """Test valid 9-digit zip code"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210-1234"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_zip_pattern_invalid(self, validator):
        """Test invalid zip code pattern"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "9021"  # Too short
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False

    def test_ein_pattern_valid(self, validator):
        """Test valid EIN pattern"""
        record = {
            "entity_id": "123",
            "entity_name": "Test Corp",
            "entity_type": "CORPORATION",
            "state": "CA",
            "ein": "12-3456789"
        }
        result = validator.validate(record, "business_entity")
        assert result.is_valid is True

    def test_ein_pattern_invalid(self, validator):
        """Test invalid EIN pattern"""
        record = {
            "entity_id": "123",
            "entity_name": "Test Corp",
            "entity_type": "CORPORATION",
            "state": "CA",
            "ein": "123456789"  # Missing dash
        }
        result = validator.validate(record, "business_entity")
        assert result.is_valid is False


class TestSchemaValidatorValueConstraints:
    """Tests for value constraint validation"""

    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    def test_min_value_valid(self, validator):
        """Test valid min value"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "bedrooms": 3
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_min_value_invalid(self, validator):
        """Test invalid min value"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "bedrooms": -1
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False

    def test_max_value_invalid(self, validator):
        """Test invalid max value"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "bedrooms": 100
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False

    def test_year_built_range_valid(self, validator):
        """Test valid year_built range"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "year_built": 2020
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_year_built_range_invalid_old(self, validator):
        """Test invalid year_built (too old)"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "year_built": 1500
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False

    def test_latitude_range_valid(self, validator):
        """Test valid latitude range"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "latitude": 34.0522
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_latitude_range_invalid(self, validator):
        """Test invalid latitude range"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "latitude": 100.0  # Invalid: > 90
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False


class TestSchemaValidatorAllowedValues:
    """Tests for allowed values validation"""

    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    def test_allowed_value_valid(self, validator):
        """Test valid allowed value"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "property_type": "SFR"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True

    def test_allowed_value_invalid(self, validator):
        """Test invalid allowed value"""
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "property_type": "CASTLE"  # Not in allowed values
        }
        result = validator.validate(record, "property")
        assert result.is_valid is False

    def test_case_status_valid(self, validator):
        """Test valid case status"""
        record = {
            "case_number": "123",
            "case_type": "CIVIL",
            "court_name": "Test Court",
            "filing_date": "2024-01-15",
            "state": "CA",
            "case_status": "OPEN"
        }
        result = validator.validate(record, "court_case")
        assert result.is_valid is True


class TestSchemaValidatorUnknownFields:
    """Tests for unknown field handling"""

    def test_strict_mode_warns_unknown_fields(self):
        """Test strict mode warns about unknown fields"""
        validator = SchemaValidator(strict_mode=True)
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "unknown_field": "value"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True  # Unknown fields don't invalidate
        assert len(result.warnings) > 0
        warning_fields = [w.field for w in result.warnings]
        assert "unknown_field" in warning_fields

    def test_non_strict_mode_ignores_unknown_fields(self):
        """Test non-strict mode ignores unknown fields"""
        validator = SchemaValidator(strict_mode=False)
        record = {
            "parcel_id": "123",
            "address": "123 Main St",
            "city": "Test",
            "state": "CA",
            "zip_code": "90210",
            "unknown_field": "value"
        }
        result = validator.validate(record, "property")
        assert result.is_valid is True
        assert len(result.warnings) == 0


class TestSchemaValidatorCustomValidation:
    """Tests for custom validator support"""

    def test_custom_validator_pass(self):
        """Test custom validator that passes"""
        def is_valid_ssn(value):
            return len(value) == 4 and value.isdigit()

        fields = [
            FieldSchema("ssn", FieldType.STRING, custom_validator=is_valid_ssn)
        ]
        schema = BaseSchema("test", fields)
        validator = SchemaValidator()

        result = validator.validate({"ssn": "1234"}, schema)
        assert result.is_valid is True

    def test_custom_validator_fail(self):
        """Test custom validator that fails"""
        def is_valid_ssn(value):
            return len(value) == 4 and value.isdigit()

        fields = [
            FieldSchema("ssn", FieldType.STRING, custom_validator=is_valid_ssn)
        ]
        schema = BaseSchema("test", fields)
        validator = SchemaValidator()

        result = validator.validate({"ssn": "123"}, schema)
        assert result.is_valid is False

    def test_custom_validator_exception(self):
        """Test custom validator that raises exception"""
        def bad_validator(value):
            raise ValueError("Test error")

        fields = [
            FieldSchema("test", FieldType.STRING, custom_validator=bad_validator)
        ]
        schema = BaseSchema("test", fields)
        validator = SchemaValidator()

        result = validator.validate({"test": "value"}, schema)
        assert result.is_valid is False
        assert "validation error" in result.errors[0].message.lower()


class TestSchemaValidatorBatch:
    """Tests for batch validation"""

    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    def test_validate_batch_all_valid(self, validator, sample_records_batch):
        """Test batch validation with all valid records"""
        results = validator.validate_batch(sample_records_batch, "property")
        assert len(results) == 3
        assert all(r.is_valid for r in results)

    def test_validate_batch_some_invalid(self, validator):
        """Test batch validation with some invalid records"""
        records = [
            {"parcel_id": "1", "address": "123 Main St", "city": "A", "state": "CA", "zip_code": "90210"},
            {"parcel_id": "2"},  # Missing required fields
            {"parcel_id": "3", "address": "456 Oak Ave", "city": "B", "state": "CA", "zip_code": "90210"},
        ]
        results = validator.validate_batch(records, "property")
        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is False
        assert results[2].is_valid is True

    def test_validate_batch_empty(self, validator):
        """Test batch validation with empty list"""
        results = validator.validate_batch([], "property")
        assert len(results) == 0


class TestSchemaValidatorStatistics:
    """Tests for validation statistics"""

    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    def test_get_statistics_all_valid(self, validator, sample_records_batch):
        """Test statistics with all valid records"""
        results = validator.validate_batch(sample_records_batch, "property")
        stats = validator.get_statistics(results)

        assert stats['total_records'] == 3
        assert stats['valid_records'] == 3
        assert stats['invalid_records'] == 0
        assert stats['validation_rate'] == 1.0

    def test_get_statistics_some_invalid(self, validator):
        """Test statistics with some invalid records"""
        records = [
            {"parcel_id": "1", "address": "123 Main St", "city": "A", "state": "CA", "zip_code": "90210"},
            {"parcel_id": "2"},  # Invalid
            {"parcel_id": "3", "address": "456 Oak Ave", "city": "B", "state": "CA", "zip_code": "90210"},
        ]
        results = validator.validate_batch(records, "property")
        stats = validator.get_statistics(results)

        assert stats['total_records'] == 3
        assert stats['valid_records'] == 2
        assert stats['invalid_records'] == 1
        assert stats['validation_rate'] == 2/3

    def test_get_statistics_errors_by_field(self, validator):
        """Test error counting by field"""
        records = [
            {"parcel_id": "1"},  # Missing multiple fields
            {"parcel_id": "2"},  # Missing multiple fields
        ]
        results = validator.validate_batch(records, "property")
        stats = validator.get_statistics(results)

        assert 'address' in stats['errors_by_field']
        assert stats['errors_by_field']['address'] == 2

    def test_get_statistics_empty(self, validator):
        """Test statistics with empty results"""
        stats = validator.get_statistics([])
        assert stats['total_records'] == 0
        assert stats['validation_rate'] == 0


class TestValidateRecordFunction:
    """Tests for validate_record convenience function"""

    def test_validate_record_valid(self, valid_property_record):
        """Test validate_record with valid record"""
        result = validate_record(valid_property_record, "property")
        assert result.is_valid is True

    def test_validate_record_invalid(self):
        """Test validate_record with invalid record"""
        record = {"parcel_id": "123"}
        result = validate_record(record, "property")
        assert result.is_valid is False

    def test_validate_record_unknown_schema(self):
        """Test validate_record with unknown schema"""
        with pytest.raises(ValueError):
            validate_record({}, "unknown")
