"""
Schema Validator

JSON schema-based validation for data structures.

Features:
- Configurable schemas for different record types
- Required field validation
- Data type validation
- Field length constraints
- Format validation (dates, addresses, identifiers)
"""

import re
import logging
from datetime import date, datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum

logger = logging.getLogger(__name__)


class FieldType(Enum):
    """Supported field data types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    LIST = "list"
    DICT = "dict"
    ANY = "any"


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"      # Must be fixed, record is invalid
    WARNING = "warning"  # Should be fixed, record is usable
    INFO = "info"        # Informational, no action required


@dataclass
class ValidationError:
    """Represents a single validation error"""
    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    expected: Optional[Any] = None
    actual: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'field': self.field,
            'message': self.message,
            'severity': self.severity.value,
            'expected': str(self.expected) if self.expected else None,
            'actual': str(self.actual) if self.actual else None,
        }


@dataclass
class ValidationResult:
    """Result of validation operation"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    record_type: Optional[str] = None
    record_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
            'record_type': self.record_type,
            'record_id': self.record_id,
        }

    def add_error(self, field: str, message: str,
                  expected: Any = None, actual: Any = None):
        """Add an error to the result"""
        self.errors.append(ValidationError(
            field=field,
            message=message,
            severity=ValidationSeverity.ERROR,
            expected=expected,
            actual=actual
        ))
        self.is_valid = False

    def add_warning(self, field: str, message: str,
                    expected: Any = None, actual: Any = None):
        """Add a warning to the result"""
        self.warnings.append(ValidationError(
            field=field,
            message=message,
            severity=ValidationSeverity.WARNING,
            expected=expected,
            actual=actual
        ))


@dataclass
class FieldSchema:
    """Schema definition for a single field"""
    name: str
    field_type: FieldType
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    custom_validator: Optional[Callable[[Any], bool]] = None
    error_message: Optional[str] = None


class BaseSchema:
    """Base class for record schemas"""

    def __init__(self, schema_name: str, fields: List[FieldSchema]):
        self.schema_name = schema_name
        self.fields = {f.name: f for f in fields}

    def get_field(self, name: str) -> Optional[FieldSchema]:
        """Get field schema by name"""
        return self.fields.get(name)

    def get_required_fields(self) -> List[str]:
        """Get list of required field names"""
        return [name for name, f in self.fields.items() if f.required]


class PropertySchema(BaseSchema):
    """Schema for property records"""

    def __init__(self):
        fields = [
            FieldSchema("parcel_id", FieldType.STRING, required=True,
                       min_length=1, max_length=50),
            FieldSchema("address", FieldType.STRING, required=True,
                       min_length=5, max_length=200),
            FieldSchema("city", FieldType.STRING, required=True,
                       min_length=1, max_length=100),
            FieldSchema("state", FieldType.STRING, required=True,
                       min_length=2, max_length=2,
                       pattern=r'^[A-Z]{2}$'),
            FieldSchema("zip_code", FieldType.STRING, required=True,
                       pattern=r'^\d{5}(-\d{4})?$'),
            FieldSchema("county", FieldType.STRING, required=False,
                       max_length=100),
            FieldSchema("property_type", FieldType.STRING, required=False,
                       allowed_values=['SFR', 'CONDO', 'TOWNHOUSE', 'MULTI_FAMILY',
                                      'COMMERCIAL', 'LAND', 'INDUSTRIAL', 'UNKNOWN']),
            FieldSchema("bedrooms", FieldType.INTEGER, required=False,
                       min_value=0, max_value=50),
            FieldSchema("bathrooms", FieldType.FLOAT, required=False,
                       min_value=0, max_value=50),
            FieldSchema("square_feet", FieldType.FLOAT, required=False,
                       min_value=0, max_value=1000000),
            FieldSchema("lot_size", FieldType.FLOAT, required=False,
                       min_value=0),
            FieldSchema("year_built", FieldType.INTEGER, required=False,
                       min_value=1600, max_value=2100),
            FieldSchema("assessed_value", FieldType.FLOAT, required=False,
                       min_value=0),
            FieldSchema("market_value", FieldType.FLOAT, required=False,
                       min_value=0),
            FieldSchema("owner_name", FieldType.STRING, required=False,
                       max_length=200),
            FieldSchema("last_sale_date", FieldType.DATE, required=False),
            FieldSchema("last_sale_price", FieldType.FLOAT, required=False,
                       min_value=0),
            FieldSchema("latitude", FieldType.FLOAT, required=False,
                       min_value=-90, max_value=90),
            FieldSchema("longitude", FieldType.FLOAT, required=False,
                       min_value=-180, max_value=180),
        ]
        super().__init__("property", fields)


class DeedSchema(BaseSchema):
    """Schema for deed/document records"""

    def __init__(self):
        fields = [
            FieldSchema("document_number", FieldType.STRING, required=True,
                       min_length=1, max_length=50),
            FieldSchema("document_type", FieldType.STRING, required=True,
                       allowed_values=['DEED', 'MORTGAGE', 'LIEN', 'RELEASE',
                                      'ASSIGNMENT', 'EASEMENT', 'NOTICE', 'OTHER']),
            FieldSchema("recording_date", FieldType.DATE, required=True),
            FieldSchema("grantor", FieldType.STRING, required=False,
                       max_length=500),
            FieldSchema("grantee", FieldType.STRING, required=False,
                       max_length=500),
            FieldSchema("consideration", FieldType.FLOAT, required=False,
                       min_value=0),
            FieldSchema("parcel_id", FieldType.STRING, required=False,
                       max_length=50),
            FieldSchema("legal_description", FieldType.STRING, required=False,
                       max_length=2000),
            FieldSchema("book", FieldType.STRING, required=False,
                       max_length=20),
            FieldSchema("page", FieldType.STRING, required=False,
                       max_length=20),
            FieldSchema("county", FieldType.STRING, required=True,
                       max_length=100),
            FieldSchema("state", FieldType.STRING, required=True,
                       min_length=2, max_length=2),
        ]
        super().__init__("deed", fields)


class CourtCaseSchema(BaseSchema):
    """Schema for court case records"""

    def __init__(self):
        fields = [
            FieldSchema("case_number", FieldType.STRING, required=True,
                       min_length=1, max_length=50),
            FieldSchema("case_type", FieldType.STRING, required=True,
                       allowed_values=['CIVIL', 'CRIMINAL', 'FAMILY', 'PROBATE',
                                      'BANKRUPTCY', 'SMALL_CLAIMS', 'TAX',
                                      'TRAFFIC', 'JUVENILE', 'APPELLATE', 'UNKNOWN']),
            FieldSchema("court_name", FieldType.STRING, required=True,
                       max_length=200),
            FieldSchema("filing_date", FieldType.DATE, required=True),
            FieldSchema("case_status", FieldType.STRING, required=False,
                       allowed_values=['OPEN', 'CLOSED', 'PENDING', 'DISMISSED',
                                      'SETTLED', 'APPEALED', 'ON_HOLD', 'UNKNOWN']),
            FieldSchema("case_title", FieldType.STRING, required=False,
                       max_length=500),
            FieldSchema("plaintiff", FieldType.STRING, required=False,
                       max_length=500),
            FieldSchema("defendant", FieldType.STRING, required=False,
                       max_length=500),
            FieldSchema("judge", FieldType.STRING, required=False,
                       max_length=200),
            FieldSchema("amount_claimed", FieldType.FLOAT, required=False,
                       min_value=0),
            FieldSchema("judgment_amount", FieldType.FLOAT, required=False,
                       min_value=0),
            FieldSchema("disposition_date", FieldType.DATE, required=False),
            FieldSchema("county", FieldType.STRING, required=False,
                       max_length=100),
            FieldSchema("state", FieldType.STRING, required=True,
                       min_length=2, max_length=2),
        ]
        super().__init__("court_case", fields)


class BusinessEntitySchema(BaseSchema):
    """Schema for business entity records"""

    def __init__(self):
        fields = [
            FieldSchema("entity_id", FieldType.STRING, required=True,
                       min_length=1, max_length=50),
            FieldSchema("entity_name", FieldType.STRING, required=True,
                       min_length=1, max_length=300),
            FieldSchema("entity_type", FieldType.STRING, required=True,
                       allowed_values=['LLC', 'CORPORATION', 'LLP', 'LP',
                                      'PARTNERSHIP', 'SOLE_PROPRIETORSHIP',
                                      'NONPROFIT', 'TRUST', 'PROFESSIONAL_CORP',
                                      'BENEFIT_CORP', 'UNKNOWN']),
            FieldSchema("status", FieldType.STRING, required=False,
                       allowed_values=['ACTIVE', 'INACTIVE', 'DISSOLVED',
                                      'SUSPENDED', 'MERGED', 'CONVERTED',
                                      'REVOKED', 'WITHDRAWN', 'FORFEITED',
                                      'PENDING', 'UNKNOWN']),
            FieldSchema("formation_date", FieldType.DATE, required=False),
            FieldSchema("dissolution_date", FieldType.DATE, required=False),
            FieldSchema("state", FieldType.STRING, required=True,
                       min_length=2, max_length=2),
            FieldSchema("ein", FieldType.STRING, required=False,
                       pattern=r'^\d{2}-\d{7}$'),
            FieldSchema("registered_agent", FieldType.STRING, required=False,
                       max_length=300),
            FieldSchema("registered_address", FieldType.STRING, required=False,
                       max_length=500),
            FieldSchema("principal_address", FieldType.STRING, required=False,
                       max_length=500),
        ]
        super().__init__("business_entity", fields)


class PersonSchema(BaseSchema):
    """Schema for person records"""

    def __init__(self):
        fields = [
            FieldSchema("person_id", FieldType.STRING, required=True,
                       min_length=1, max_length=50),
            FieldSchema("first_name", FieldType.STRING, required=True,
                       min_length=1, max_length=100),
            FieldSchema("last_name", FieldType.STRING, required=True,
                       min_length=1, max_length=100),
            FieldSchema("middle_name", FieldType.STRING, required=False,
                       max_length=100),
            FieldSchema("suffix", FieldType.STRING, required=False,
                       allowed_values=['JR', 'SR', 'II', 'III', 'IV', 'V']),
            FieldSchema("date_of_birth", FieldType.DATE, required=False),
            FieldSchema("ssn_last4", FieldType.STRING, required=False,
                       pattern=r'^\d{4}$'),
            FieldSchema("address", FieldType.STRING, required=False,
                       max_length=500),
            FieldSchema("city", FieldType.STRING, required=False,
                       max_length=100),
            FieldSchema("state", FieldType.STRING, required=False,
                       min_length=2, max_length=2),
            FieldSchema("zip_code", FieldType.STRING, required=False,
                       pattern=r'^\d{5}(-\d{4})?$'),
            FieldSchema("phone", FieldType.STRING, required=False,
                       pattern=r'^\+?1?\d{10,14}$'),
            FieldSchema("email", FieldType.STRING, required=False,
                       pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
        ]
        super().__init__("person", fields)


class SchemaValidator:
    """
    Validates records against defined schemas.

    Features:
    - Schema-based validation
    - Type checking
    - Format validation
    - Custom validators
    """

    # Date format patterns
    DATE_PATTERNS = [
        r'^\d{4}-\d{2}-\d{2}$',           # ISO format: 2024-01-15
        r'^\d{2}/\d{2}/\d{4}$',           # US format: 01/15/2024
        r'^\d{1,2}/\d{1,2}/\d{4}$',       # Flexible US: 1/15/2024
    ]

    # Pre-built schemas
    SCHEMAS = {
        'property': PropertySchema(),
        'deed': DeedSchema(),
        'court_case': CourtCaseSchema(),
        'business_entity': BusinessEntitySchema(),
        'person': PersonSchema(),
    }

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the validator.

        Args:
            strict_mode: If True, unknown fields cause warnings
        """
        self.strict_mode = strict_mode

    def validate(self, record: Dict[str, Any],
                 schema: Union[str, BaseSchema]) -> ValidationResult:
        """
        Validate a record against a schema.

        Args:
            record: The record to validate
            schema: Schema name or BaseSchema instance

        Returns:
            ValidationResult with errors and warnings
        """
        # Get schema
        if isinstance(schema, str):
            if schema not in self.SCHEMAS:
                raise ValueError(f"Unknown schema: {schema}")
            schema_obj = self.SCHEMAS[schema]
        else:
            schema_obj = schema

        result = ValidationResult(
            is_valid=True,
            record_type=schema_obj.schema_name,
            record_id=record.get('record_id') or record.get('id')
        )

        # Check required fields
        for field_name in schema_obj.get_required_fields():
            if field_name not in record or record[field_name] is None:
                result.add_error(
                    field=field_name,
                    message=f"Required field '{field_name}' is missing or null"
                )

        # Validate each field in the record
        for field_name, value in record.items():
            if value is None:
                continue

            field_schema = schema_obj.get_field(field_name)

            if field_schema is None:
                if self.strict_mode:
                    result.add_warning(
                        field=field_name,
                        message=f"Unknown field '{field_name}' not in schema"
                    )
                continue

            # Validate field
            self._validate_field(result, field_name, value, field_schema)

        return result

    def _validate_field(self, result: ValidationResult, field_name: str,
                        value: Any, schema: FieldSchema):
        """Validate a single field against its schema"""

        # Type validation
        if not self._check_type(value, schema.field_type):
            result.add_error(
                field=field_name,
                message=f"Invalid type for '{field_name}'",
                expected=schema.field_type.value,
                actual=type(value).__name__
            )
            return

        # String validations
        if schema.field_type == FieldType.STRING and isinstance(value, str):
            # Length constraints
            if schema.min_length and len(value) < schema.min_length:
                result.add_error(
                    field=field_name,
                    message=f"'{field_name}' is too short",
                    expected=f"min length {schema.min_length}",
                    actual=f"length {len(value)}"
                )

            if schema.max_length and len(value) > schema.max_length:
                result.add_error(
                    field=field_name,
                    message=f"'{field_name}' is too long",
                    expected=f"max length {schema.max_length}",
                    actual=f"length {len(value)}"
                )

            # Pattern validation
            if schema.pattern and not re.match(schema.pattern, value):
                result.add_error(
                    field=field_name,
                    message=f"'{field_name}' does not match required pattern",
                    expected=schema.pattern,
                    actual=value
                )

        # Numeric validations
        if schema.field_type in (FieldType.INTEGER, FieldType.FLOAT):
            if schema.min_value is not None and value < schema.min_value:
                result.add_error(
                    field=field_name,
                    message=f"'{field_name}' is below minimum",
                    expected=f"min {schema.min_value}",
                    actual=value
                )

            if schema.max_value is not None and value > schema.max_value:
                result.add_error(
                    field=field_name,
                    message=f"'{field_name}' is above maximum",
                    expected=f"max {schema.max_value}",
                    actual=value
                )

        # Allowed values validation
        if schema.allowed_values:
            if value not in schema.allowed_values and str(value).upper() not in schema.allowed_values:
                result.add_error(
                    field=field_name,
                    message=f"'{field_name}' has invalid value",
                    expected=schema.allowed_values,
                    actual=value
                )

        # Custom validator
        if schema.custom_validator:
            try:
                if not schema.custom_validator(value):
                    result.add_error(
                        field=field_name,
                        message=schema.error_message or f"'{field_name}' failed custom validation",
                        actual=value
                    )
            except Exception as e:
                result.add_error(
                    field=field_name,
                    message=f"Custom validation error: {str(e)}",
                    actual=value
                )

    def _check_type(self, value: Any, expected_type: FieldType) -> bool:
        """Check if value matches expected type"""
        if expected_type == FieldType.ANY:
            return True

        if expected_type == FieldType.STRING:
            return isinstance(value, str)

        if expected_type == FieldType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)

        if expected_type == FieldType.FLOAT:
            return isinstance(value, (int, float)) and not isinstance(value, bool)

        if expected_type == FieldType.BOOLEAN:
            return isinstance(value, bool)

        if expected_type == FieldType.DATE:
            if isinstance(value, date) and not isinstance(value, datetime):
                return True
            if isinstance(value, str):
                return any(re.match(p, value) for p in self.DATE_PATTERNS)
            return False

        if expected_type == FieldType.DATETIME:
            if isinstance(value, datetime):
                return True
            if isinstance(value, str):
                # ISO datetime format
                return bool(re.match(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', value))
            return False

        if expected_type == FieldType.LIST:
            return isinstance(value, list)

        if expected_type == FieldType.DICT:
            return isinstance(value, dict)

        return False

    def validate_batch(self, records: List[Dict[str, Any]],
                       schema: Union[str, BaseSchema]) -> List[ValidationResult]:
        """
        Validate multiple records.

        Args:
            records: List of records to validate
            schema: Schema to validate against

        Returns:
            List of ValidationResults
        """
        return [self.validate(record, schema) for record in records]

    def get_statistics(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Get validation statistics from results"""
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid

        # Count errors by field
        error_by_field: Dict[str, int] = {}
        for result in results:
            for error in result.errors:
                error_by_field[error.field] = error_by_field.get(error.field, 0) + 1

        return {
            'total_records': total,
            'valid_records': valid,
            'invalid_records': invalid,
            'validation_rate': valid / total if total > 0 else 0,
            'total_errors': sum(len(r.errors) for r in results),
            'total_warnings': sum(len(r.warnings) for r in results),
            'errors_by_field': error_by_field,
        }


# Convenience functions
def validate_record(record: Dict[str, Any], schema: str) -> ValidationResult:
    """Validate a single record using default validator"""
    validator = SchemaValidator()
    return validator.validate(record, schema)
