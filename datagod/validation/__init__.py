"""
Data Validation Framework

Comprehensive validation for property, court, business, and people records.

Modules:
- schema_validator: JSON schema validation for data structures
- business_rules: Domain-specific business rule validation
- cross_source_validator: Cross-source consistency validation
"""

from datagod.validation.business_rules import (
    BusinessRuleValidator,
    RuleViolation,
    validate_business_record,
    validate_court_record,
    validate_property_record,
)
from datagod.validation.cross_source_validator import (
    CrossSourceValidator,
    SourceDiscrepancy,
    reconcile_records,
    validate_cross_source,
)
from datagod.validation.schema_validator import (  # Schema types
    BusinessEntitySchema,
    CourtCaseSchema,
    DeedSchema,
    PersonSchema,
    PropertySchema,
    SchemaValidator,
    ValidationError,
    ValidationResult,
    validate_record,
)

__all__ = [
    # Schema validation
    "SchemaValidator",
    "ValidationResult",
    "ValidationError",
    "validate_record",
    "PropertySchema",
    "DeedSchema",
    "CourtCaseSchema",
    "BusinessEntitySchema",
    "PersonSchema",
    # Business rules
    "BusinessRuleValidator",
    "RuleViolation",
    "validate_property_record",
    "validate_court_record",
    "validate_business_record",
    # Cross-source validation
    "CrossSourceValidator",
    "SourceDiscrepancy",
    "validate_cross_source",
    "reconcile_records",
]
