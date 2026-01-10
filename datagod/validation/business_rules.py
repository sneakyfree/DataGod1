"""
Business Rules Validator

Domain-specific validation rules for property, court, and business records.

Features:
- Date range validations
- Cross-field consistency checks
- Geographic validations
- Financial reasonableness checks
"""

import re
import logging
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class RuleSeverity(Enum):
    """Severity levels for rule violations"""
    CRITICAL = "critical"    # Data is invalid
    HIGH = "high"            # Likely data error
    MEDIUM = "medium"        # Possible issue
    LOW = "low"              # Minor concern
    INFO = "info"            # Informational only


@dataclass
class RuleViolation:
    """Represents a business rule violation"""
    rule_id: str
    rule_name: str
    message: str
    severity: RuleSeverity = RuleSeverity.MEDIUM
    field: Optional[str] = None
    actual_value: Optional[Any] = None
    expected_range: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'message': self.message,
            'severity': self.severity.value,
            'field': self.field,
            'actual_value': str(self.actual_value) if self.actual_value else None,
            'expected_range': self.expected_range,
        }


@dataclass
class RuleResult:
    """Result of business rule validation"""
    is_valid: bool = True
    violations: List[RuleViolation] = field(default_factory=list)
    record_type: Optional[str] = None
    record_id: Optional[str] = None

    def add_violation(self, rule_id: str, rule_name: str, message: str,
                      severity: RuleSeverity = RuleSeverity.MEDIUM,
                      field: str = None, actual_value: Any = None,
                      expected_range: str = None):
        """Add a violation"""
        self.violations.append(RuleViolation(
            rule_id=rule_id,
            rule_name=rule_name,
            message=message,
            severity=severity,
            field=field,
            actual_value=actual_value,
            expected_range=expected_range
        ))
        if severity in (RuleSeverity.CRITICAL, RuleSeverity.HIGH):
            self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'violation_count': len(self.violations),
            'violations': [v.to_dict() for v in self.violations],
            'record_type': self.record_type,
            'record_id': self.record_id,
        }


class BusinessRuleValidator:
    """
    Validates records against domain-specific business rules.

    Features:
    - Property valuation reasonableness
    - Date consistency checks
    - Geographic validation
    - Financial calculations
    """

    # US State codes
    US_STATES = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC', 'PR', 'VI', 'GU', 'AS', 'MP'
    }

    # Reasonable value ranges
    MIN_PROPERTY_VALUE = 1000
    MAX_PROPERTY_VALUE = 1_000_000_000
    MIN_YEAR_BUILT = 1600
    MAX_SQFT = 1_000_000
    MIN_PRICE_PER_SQFT = 1
    MAX_PRICE_PER_SQFT = 10_000

    def __init__(self):
        """Initialize the validator"""
        self.current_year = datetime.now().year

    def validate_property(self, record: Dict[str, Any]) -> RuleResult:
        """
        Validate property record against business rules.

        Args:
            record: Property record dictionary

        Returns:
            RuleResult with violations
        """
        result = RuleResult(
            record_type='property',
            record_id=record.get('parcel_id') or record.get('id')
        )

        # Rule: Year built must be reasonable
        year_built = record.get('year_built')
        if year_built:
            if year_built < self.MIN_YEAR_BUILT:
                result.add_violation(
                    rule_id="PROP-001",
                    rule_name="Year Built Too Old",
                    message=f"Year built {year_built} is before {self.MIN_YEAR_BUILT}",
                    severity=RuleSeverity.HIGH,
                    field="year_built",
                    actual_value=year_built,
                    expected_range=f"{self.MIN_YEAR_BUILT}-{self.current_year}"
                )
            elif year_built > self.current_year:
                result.add_violation(
                    rule_id="PROP-002",
                    rule_name="Year Built In Future",
                    message=f"Year built {year_built} is in the future",
                    severity=RuleSeverity.HIGH,
                    field="year_built",
                    actual_value=year_built
                )

        # Rule: Property value must be reasonable
        for value_field in ['assessed_value', 'market_value', 'last_sale_price']:
            value = record.get(value_field)
            if value:
                if value < self.MIN_PROPERTY_VALUE:
                    result.add_violation(
                        rule_id="PROP-003",
                        rule_name="Value Too Low",
                        message=f"{value_field} of ${value:,.0f} is unusually low",
                        severity=RuleSeverity.MEDIUM,
                        field=value_field,
                        actual_value=value,
                        expected_range=f">${self.MIN_PROPERTY_VALUE:,}"
                    )
                elif value > self.MAX_PROPERTY_VALUE:
                    result.add_violation(
                        rule_id="PROP-004",
                        rule_name="Value Too High",
                        message=f"{value_field} of ${value:,.0f} is unusually high",
                        severity=RuleSeverity.MEDIUM,
                        field=value_field,
                        actual_value=value
                    )

        # Rule: Square footage must be reasonable
        sqft = record.get('square_feet') or record.get('building_sqft')
        if sqft:
            if sqft > self.MAX_SQFT:
                result.add_violation(
                    rule_id="PROP-005",
                    rule_name="Square Footage Too High",
                    message=f"Square footage of {sqft:,.0f} is unusually high",
                    severity=RuleSeverity.MEDIUM,
                    field="square_feet",
                    actual_value=sqft
                )

        # Rule: Price per square foot should be reasonable
        if sqft and sqft > 0:
            for value_field in ['market_value', 'last_sale_price']:
                value = record.get(value_field)
                if value:
                    price_per_sqft = value / sqft
                    if price_per_sqft < self.MIN_PRICE_PER_SQFT:
                        result.add_violation(
                            rule_id="PROP-006",
                            rule_name="Price Per SqFt Too Low",
                            message=f"Price per sqft (${price_per_sqft:,.2f}) is unusually low",
                            severity=RuleSeverity.LOW,
                            field=value_field,
                            actual_value=price_per_sqft
                        )
                    elif price_per_sqft > self.MAX_PRICE_PER_SQFT:
                        result.add_violation(
                            rule_id="PROP-007",
                            rule_name="Price Per SqFt Too High",
                            message=f"Price per sqft (${price_per_sqft:,.2f}) is unusually high",
                            severity=RuleSeverity.MEDIUM,
                            field=value_field,
                            actual_value=price_per_sqft
                        )

        # Rule: State must be valid
        state = record.get('state')
        if state and state.upper() not in self.US_STATES:
            result.add_violation(
                rule_id="PROP-008",
                rule_name="Invalid State",
                message=f"State '{state}' is not a valid US state code",
                severity=RuleSeverity.HIGH,
                field="state",
                actual_value=state
            )

        # Rule: Last sale date should not be in the future
        last_sale_date = self._parse_date(record.get('last_sale_date'))
        if last_sale_date and last_sale_date > date.today():
            result.add_violation(
                rule_id="PROP-009",
                rule_name="Future Sale Date",
                message="Last sale date is in the future",
                severity=RuleSeverity.HIGH,
                field="last_sale_date",
                actual_value=record.get('last_sale_date')
            )

        # Rule: Assessed vs Market value ratio
        assessed = record.get('assessed_value')
        market = record.get('market_value')
        if assessed and market and market > 0:
            ratio = assessed / market
            if ratio > 1.5:
                result.add_violation(
                    rule_id="PROP-010",
                    rule_name="Assessment Ratio High",
                    message=f"Assessed value is {ratio:.1f}x market value",
                    severity=RuleSeverity.LOW,
                    actual_value=ratio,
                    expected_range="0.5-1.5"
                )
            elif ratio < 0.3:
                result.add_violation(
                    rule_id="PROP-011",
                    rule_name="Assessment Ratio Low",
                    message=f"Assessed value is only {ratio:.1%} of market value",
                    severity=RuleSeverity.LOW,
                    actual_value=ratio
                )

        # Rule: Bedrooms and bathrooms should be reasonable
        bedrooms = record.get('bedrooms')
        bathrooms = record.get('bathrooms')
        if bedrooms and bedrooms > 20:
            result.add_violation(
                rule_id="PROP-012",
                rule_name="Bedrooms Too High",
                message=f"{bedrooms} bedrooms is unusually high",
                severity=RuleSeverity.MEDIUM,
                field="bedrooms",
                actual_value=bedrooms
            )
        if bathrooms and bathrooms > 20:
            result.add_violation(
                rule_id="PROP-013",
                rule_name="Bathrooms Too High",
                message=f"{bathrooms} bathrooms is unusually high",
                severity=RuleSeverity.MEDIUM,
                field="bathrooms",
                actual_value=bathrooms
            )

        # Rule: Coordinates should be in US bounds
        lat = record.get('latitude')
        lon = record.get('longitude')
        if lat and lon:
            # Continental US approximate bounds
            if not (24 <= lat <= 50 and -125 <= lon <= -66):
                # Check for Alaska, Hawaii, territories
                if not self._is_valid_us_coordinates(lat, lon):
                    result.add_violation(
                        rule_id="PROP-014",
                        rule_name="Coordinates Outside US",
                        message=f"Coordinates ({lat}, {lon}) are outside US bounds",
                        severity=RuleSeverity.MEDIUM,
                        actual_value=f"({lat}, {lon})"
                    )

        return result

    def validate_deed(self, record: Dict[str, Any]) -> RuleResult:
        """
        Validate deed/document record against business rules.

        Args:
            record: Deed record dictionary

        Returns:
            RuleResult with violations
        """
        result = RuleResult(
            record_type='deed',
            record_id=record.get('document_number') or record.get('id')
        )

        # Rule: Recording date should not be in the future
        recording_date = self._parse_date(record.get('recording_date'))
        if recording_date and recording_date > date.today():
            result.add_violation(
                rule_id="DEED-001",
                rule_name="Future Recording Date",
                message="Recording date is in the future",
                severity=RuleSeverity.CRITICAL,
                field="recording_date",
                actual_value=record.get('recording_date')
            )

        # Rule: Recording date should not be too old
        if recording_date and recording_date < date(1800, 1, 1):
            result.add_violation(
                rule_id="DEED-002",
                rule_name="Recording Date Too Old",
                message="Recording date is before 1800",
                severity=RuleSeverity.HIGH,
                field="recording_date",
                actual_value=record.get('recording_date')
            )

        # Rule: Consideration amount should be reasonable
        consideration = record.get('consideration')
        if consideration:
            if consideration < 0:
                result.add_violation(
                    rule_id="DEED-003",
                    rule_name="Negative Consideration",
                    message="Consideration amount is negative",
                    severity=RuleSeverity.CRITICAL,
                    field="consideration",
                    actual_value=consideration
                )
            elif consideration > self.MAX_PROPERTY_VALUE:
                result.add_violation(
                    rule_id="DEED-004",
                    rule_name="Consideration Too High",
                    message=f"Consideration of ${consideration:,.0f} is unusually high",
                    severity=RuleSeverity.MEDIUM,
                    field="consideration",
                    actual_value=consideration
                )

        # Rule: Grantor and grantee should be different
        grantor = record.get('grantor', '').strip().lower()
        grantee = record.get('grantee', '').strip().lower()
        if grantor and grantee and grantor == grantee:
            result.add_violation(
                rule_id="DEED-005",
                rule_name="Same Grantor Grantee",
                message="Grantor and grantee are the same",
                severity=RuleSeverity.MEDIUM,
                actual_value=grantor
            )

        # Rule: State must be valid
        state = record.get('state')
        if state and state.upper() not in self.US_STATES:
            result.add_violation(
                rule_id="DEED-006",
                rule_name="Invalid State",
                message=f"State '{state}' is not a valid US state code",
                severity=RuleSeverity.HIGH,
                field="state",
                actual_value=state
            )

        return result

    def validate_court_case(self, record: Dict[str, Any]) -> RuleResult:
        """
        Validate court case record against business rules.

        Args:
            record: Court case record dictionary

        Returns:
            RuleResult with violations
        """
        result = RuleResult(
            record_type='court_case',
            record_id=record.get('case_number') or record.get('id')
        )

        # Rule: Filing date should not be in the future
        filing_date = self._parse_date(record.get('filing_date'))
        if filing_date and filing_date > date.today():
            result.add_violation(
                rule_id="COURT-001",
                rule_name="Future Filing Date",
                message="Filing date is in the future",
                severity=RuleSeverity.CRITICAL,
                field="filing_date",
                actual_value=record.get('filing_date')
            )

        # Rule: Disposition date should be after filing date
        disposition_date = self._parse_date(record.get('disposition_date'))
        if filing_date and disposition_date:
            if disposition_date < filing_date:
                result.add_violation(
                    rule_id="COURT-002",
                    rule_name="Disposition Before Filing",
                    message="Disposition date is before filing date",
                    severity=RuleSeverity.HIGH,
                    field="disposition_date",
                    actual_value=f"Filed: {filing_date}, Disposed: {disposition_date}"
                )

        # Rule: Amount claimed should be reasonable
        amount_claimed = record.get('amount_claimed')
        if amount_claimed:
            if amount_claimed < 0:
                result.add_violation(
                    rule_id="COURT-003",
                    rule_name="Negative Amount Claimed",
                    message="Amount claimed is negative",
                    severity=RuleSeverity.HIGH,
                    field="amount_claimed",
                    actual_value=amount_claimed
                )
            elif amount_claimed > 10_000_000_000:  # $10B
                result.add_violation(
                    rule_id="COURT-004",
                    rule_name="Amount Claimed Too High",
                    message=f"Amount claimed of ${amount_claimed:,.0f} is unusually high",
                    severity=RuleSeverity.MEDIUM,
                    field="amount_claimed",
                    actual_value=amount_claimed
                )

        # Rule: Judgment should not exceed amount claimed (if both present)
        judgment_amount = record.get('judgment_amount')
        if amount_claimed and judgment_amount:
            if judgment_amount > amount_claimed * 10:
                result.add_violation(
                    rule_id="COURT-005",
                    rule_name="Judgment Exceeds Claim",
                    message="Judgment amount greatly exceeds amount claimed",
                    severity=RuleSeverity.LOW,
                    actual_value=f"Claimed: ${amount_claimed:,.0f}, Judgment: ${judgment_amount:,.0f}"
                )

        # Rule: Case status should match dates
        case_status = record.get('case_status')
        if case_status == 'CLOSED' and not disposition_date:
            result.add_violation(
                rule_id="COURT-006",
                rule_name="Closed Without Disposition",
                message="Case is closed but has no disposition date",
                severity=RuleSeverity.LOW,
                field="case_status"
            )

        # Rule: State must be valid
        state = record.get('state')
        if state and state.upper() not in self.US_STATES:
            result.add_violation(
                rule_id="COURT-007",
                rule_name="Invalid State",
                message=f"State '{state}' is not a valid US state code",
                severity=RuleSeverity.HIGH,
                field="state",
                actual_value=state
            )

        return result

    def validate_business(self, record: Dict[str, Any]) -> RuleResult:
        """
        Validate business entity record against business rules.

        Args:
            record: Business entity record dictionary

        Returns:
            RuleResult with violations
        """
        result = RuleResult(
            record_type='business_entity',
            record_id=record.get('entity_id') or record.get('id')
        )

        # Rule: Formation date should not be in the future
        formation_date = self._parse_date(record.get('formation_date'))
        if formation_date and formation_date > date.today():
            result.add_violation(
                rule_id="BUS-001",
                rule_name="Future Formation Date",
                message="Formation date is in the future",
                severity=RuleSeverity.CRITICAL,
                field="formation_date",
                actual_value=record.get('formation_date')
            )

        # Rule: Formation date should not be too old
        if formation_date and formation_date < date(1800, 1, 1):
            result.add_violation(
                rule_id="BUS-002",
                rule_name="Formation Date Too Old",
                message="Formation date is before 1800",
                severity=RuleSeverity.MEDIUM,
                field="formation_date",
                actual_value=record.get('formation_date')
            )

        # Rule: Dissolution date should be after formation date
        dissolution_date = self._parse_date(record.get('dissolution_date'))
        if formation_date and dissolution_date:
            if dissolution_date < formation_date:
                result.add_violation(
                    rule_id="BUS-003",
                    rule_name="Dissolution Before Formation",
                    message="Dissolution date is before formation date",
                    severity=RuleSeverity.HIGH,
                    field="dissolution_date",
                    actual_value=f"Formed: {formation_date}, Dissolved: {dissolution_date}"
                )

        # Rule: Active status should not have dissolution date
        status = record.get('status')
        if status == 'ACTIVE' and dissolution_date:
            result.add_violation(
                rule_id="BUS-004",
                rule_name="Active With Dissolution",
                message="Entity is active but has a dissolution date",
                severity=RuleSeverity.MEDIUM,
                field="status"
            )

        # Rule: Dissolved status should have dissolution date
        if status == 'DISSOLVED' and not dissolution_date:
            result.add_violation(
                rule_id="BUS-005",
                rule_name="Dissolved Without Date",
                message="Entity is dissolved but has no dissolution date",
                severity=RuleSeverity.LOW,
                field="status"
            )

        # Rule: EIN format validation
        ein = record.get('ein')
        if ein and not re.match(r'^\d{2}-\d{7}$', ein):
            result.add_violation(
                rule_id="BUS-006",
                rule_name="Invalid EIN Format",
                message=f"EIN '{ein}' is not in valid format (XX-XXXXXXX)",
                severity=RuleSeverity.HIGH,
                field="ein",
                actual_value=ein
            )

        # Rule: State must be valid
        state = record.get('state')
        if state and state.upper() not in self.US_STATES:
            result.add_violation(
                rule_id="BUS-007",
                rule_name="Invalid State",
                message=f"State '{state}' is not a valid US state code",
                severity=RuleSeverity.HIGH,
                field="state",
                actual_value=state
            )

        return result

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse a date value"""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y']:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None

    def _is_valid_us_coordinates(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within US territories"""
        # Alaska
        if 51 <= lat <= 72 and -180 <= lon <= -129:
            return True
        # Hawaii
        if 18 <= lat <= 23 and -161 <= lon <= -154:
            return True
        # Puerto Rico / Virgin Islands
        if 17 <= lat <= 19 and -68 <= lon <= -64:
            return True
        # Guam
        if 13 <= lat <= 14 and 144 <= lon <= 145:
            return True
        # American Samoa
        if -15 <= lat <= -11 and -172 <= lon <= -168:
            return True
        return False

    def get_statistics(self, results: List[RuleResult]) -> Dict[str, Any]:
        """Get validation statistics from results"""
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)

        # Count violations by severity
        by_severity: Dict[str, int] = {}
        by_rule: Dict[str, int] = {}
        for result in results:
            for violation in result.violations:
                sev = violation.severity.value
                by_severity[sev] = by_severity.get(sev, 0) + 1
                by_rule[violation.rule_id] = by_rule.get(violation.rule_id, 0) + 1

        return {
            'total_records': total,
            'valid_records': valid,
            'invalid_records': total - valid,
            'validation_rate': valid / total if total > 0 else 0,
            'total_violations': sum(len(r.violations) for r in results),
            'violations_by_severity': by_severity,
            'violations_by_rule': by_rule,
        }


# Convenience functions
def validate_property_record(record: Dict[str, Any]) -> RuleResult:
    """Validate a property record using default validator"""
    validator = BusinessRuleValidator()
    return validator.validate_property(record)


def validate_court_record(record: Dict[str, Any]) -> RuleResult:
    """Validate a court case record using default validator"""
    validator = BusinessRuleValidator()
    return validator.validate_court_case(record)


def validate_business_record(record: Dict[str, Any]) -> RuleResult:
    """Validate a business entity record using default validator"""
    validator = BusinessRuleValidator()
    return validator.validate_business(record)
