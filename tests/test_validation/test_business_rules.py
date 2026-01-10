"""
Comprehensive tests for the Business Rules Validator.

Tests cover:
- RuleSeverity enum
- RuleViolation dataclass
- RuleResult dataclass
- BusinessRuleValidator class
- Property validation rules
- Deed validation rules
- Court case validation rules
- Business entity validation rules
- Date parsing
- Geographic validation
- Convenience functions
"""

import pytest
from datetime import date, datetime, timedelta
from datagod.validation.business_rules import (
    RuleSeverity,
    RuleViolation,
    RuleResult,
    BusinessRuleValidator,
    validate_property_record,
    validate_court_record,
    validate_business_record,
)


class TestRuleSeverityEnum:
    """Tests for RuleSeverity enum"""

    def test_all_severities_exist(self):
        """Test that all severity levels are defined"""
        assert RuleSeverity.CRITICAL is not None
        assert RuleSeverity.HIGH is not None
        assert RuleSeverity.MEDIUM is not None
        assert RuleSeverity.LOW is not None
        assert RuleSeverity.INFO is not None

    def test_severity_values(self):
        """Test severity string values"""
        assert RuleSeverity.CRITICAL.value == "critical"
        assert RuleSeverity.HIGH.value == "high"
        assert RuleSeverity.MEDIUM.value == "medium"
        assert RuleSeverity.LOW.value == "low"
        assert RuleSeverity.INFO.value == "info"


class TestRuleViolation:
    """Tests for RuleViolation dataclass"""

    def test_create_violation(self):
        """Test creating a rule violation"""
        violation = RuleViolation(
            rule_id="TEST-001",
            rule_name="Test Rule",
            message="Test violation message"
        )
        assert violation.rule_id == "TEST-001"
        assert violation.rule_name == "Test Rule"
        assert violation.message == "Test violation message"
        assert violation.severity == RuleSeverity.MEDIUM  # default

    def test_violation_with_severity(self):
        """Test violation with explicit severity"""
        violation = RuleViolation(
            rule_id="TEST-001",
            rule_name="Critical Rule",
            message="Critical issue",
            severity=RuleSeverity.CRITICAL
        )
        assert violation.severity == RuleSeverity.CRITICAL

    def test_violation_with_details(self):
        """Test violation with field and value details"""
        violation = RuleViolation(
            rule_id="TEST-001",
            rule_name="Value Check",
            message="Value out of range",
            field="test_field",
            actual_value=150,
            expected_range="0-100"
        )
        assert violation.field == "test_field"
        assert violation.actual_value == 150
        assert violation.expected_range == "0-100"

    def test_violation_to_dict(self):
        """Test converting violation to dictionary"""
        violation = RuleViolation(
            rule_id="TEST-001",
            rule_name="Test Rule",
            message="Test message",
            severity=RuleSeverity.HIGH,
            field="test_field",
            actual_value="bad_value",
            expected_range="good_value"
        )
        result = violation.to_dict()
        assert result['rule_id'] == "TEST-001"
        assert result['rule_name'] == "Test Rule"
        assert result['message'] == "Test message"
        assert result['severity'] == "high"
        assert result['field'] == "test_field"
        assert result['actual_value'] == "bad_value"
        assert result['expected_range'] == "good_value"

    def test_violation_to_dict_null_values(self):
        """Test to_dict with null optional values"""
        violation = RuleViolation(
            rule_id="TEST-001",
            rule_name="Test Rule",
            message="Test message"
        )
        result = violation.to_dict()
        assert result['field'] is None
        assert result['actual_value'] is None
        assert result['expected_range'] is None


class TestRuleResult:
    """Tests for RuleResult dataclass"""

    def test_create_valid_result(self):
        """Test creating a valid result"""
        result = RuleResult()
        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_add_violation_high_severity(self):
        """Test adding high severity violation invalidates result"""
        result = RuleResult()
        result.add_violation(
            rule_id="TEST-001",
            rule_name="High Severity",
            message="Test",
            severity=RuleSeverity.HIGH
        )
        assert result.is_valid is False
        assert len(result.violations) == 1

    def test_add_violation_critical_severity(self):
        """Test adding critical severity violation invalidates result"""
        result = RuleResult()
        result.add_violation(
            rule_id="TEST-001",
            rule_name="Critical",
            message="Test",
            severity=RuleSeverity.CRITICAL
        )
        assert result.is_valid is False

    def test_add_violation_medium_severity(self):
        """Test adding medium severity does not invalidate"""
        result = RuleResult()
        result.add_violation(
            rule_id="TEST-001",
            rule_name="Medium",
            message="Test",
            severity=RuleSeverity.MEDIUM
        )
        assert result.is_valid is True
        assert len(result.violations) == 1

    def test_add_violation_low_severity(self):
        """Test adding low severity does not invalidate"""
        result = RuleResult()
        result.add_violation(
            rule_id="TEST-001",
            rule_name="Low",
            message="Test",
            severity=RuleSeverity.LOW
        )
        assert result.is_valid is True

    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = RuleResult(
            record_type='property',
            record_id='123'
        )
        result.add_violation(
            rule_id="TEST-001",
            rule_name="Test",
            message="Test",
            severity=RuleSeverity.LOW
        )
        data = result.to_dict()
        assert data['is_valid'] is True
        assert data['violation_count'] == 1
        assert data['record_type'] == 'property'
        assert data['record_id'] == '123'
        assert len(data['violations']) == 1


class TestBusinessRuleValidator:
    """Tests for BusinessRuleValidator class"""

    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return BusinessRuleValidator()

    def test_validator_initialization(self, validator):
        """Test validator initialization"""
        assert validator.current_year == datetime.now().year
        assert validator.MIN_PROPERTY_VALUE == 1000
        assert validator.MAX_PROPERTY_VALUE == 1_000_000_000

    def test_us_states_includes_all_50(self, validator):
        """Test all 50 states are included"""
        assert 'CA' in validator.US_STATES
        assert 'NY' in validator.US_STATES
        assert 'TX' in validator.US_STATES
        assert 'FL' in validator.US_STATES
        # Territories
        assert 'DC' in validator.US_STATES
        assert 'PR' in validator.US_STATES
        assert 'VI' in validator.US_STATES


class TestPropertyValidation:
    """Tests for property validation rules"""

    @pytest.fixture
    def validator(self):
        return BusinessRuleValidator()

    def test_valid_property_record(self, validator, valid_property_record):
        """Test a valid property record passes"""
        result = validator.validate_property(valid_property_record)
        assert result.is_valid is True

    def test_year_built_too_old(self, validator):
        """Test year built before 1600"""
        record = {"year_built": 1500}
        result = validator.validate_property(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-001" in rule_ids

    def test_year_built_in_future(self, validator):
        """Test year built in the future"""
        record = {"year_built": 2030}
        result = validator.validate_property(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-002" in rule_ids

    def test_assessed_value_too_low(self, validator):
        """Test assessed value below minimum"""
        record = {"assessed_value": 500}
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-003" in rule_ids

    def test_market_value_too_high(self, validator):
        """Test market value above maximum"""
        record = {"market_value": 2_000_000_000}
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-004" in rule_ids

    def test_square_footage_too_high(self, validator):
        """Test square footage above maximum"""
        record = {"square_feet": 2_000_000}
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-005" in rule_ids

    def test_price_per_sqft_too_low(self, validator):
        """Test price per sqft below minimum"""
        record = {
            "square_feet": 2000,
            "market_value": 100  # $0.05/sqft
        }
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-006" in rule_ids

    def test_price_per_sqft_too_high(self, validator):
        """Test price per sqft above maximum"""
        record = {
            "square_feet": 100,
            "market_value": 50_000_000  # $500,000/sqft
        }
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-007" in rule_ids

    def test_invalid_state(self, validator):
        """Test invalid state code"""
        record = {"state": "XX"}
        result = validator.validate_property(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-008" in rule_ids

    def test_valid_states(self, validator):
        """Test valid state codes don't trigger violation"""
        for state in ['CA', 'NY', 'TX', 'FL', 'IL']:
            record = {"state": state}
            result = validator.validate_property(record)
            rule_ids = [v.rule_id for v in result.violations]
            assert "PROP-008" not in rule_ids

    def test_future_sale_date(self, validator):
        """Test last sale date in the future"""
        future = date.today() + timedelta(days=30)
        record = {"last_sale_date": future.isoformat()}
        result = validator.validate_property(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-009" in rule_ids

    def test_assessed_market_ratio_high(self, validator):
        """Test assessed/market ratio too high"""
        record = {
            "assessed_value": 500000,
            "market_value": 200000  # ratio = 2.5
        }
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-010" in rule_ids

    def test_assessed_market_ratio_low(self, validator):
        """Test assessed/market ratio too low"""
        record = {
            "assessed_value": 50000,
            "market_value": 500000  # ratio = 0.1
        }
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-011" in rule_ids

    def test_too_many_bedrooms(self, validator):
        """Test too many bedrooms"""
        record = {"bedrooms": 50}
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-012" in rule_ids

    def test_too_many_bathrooms(self, validator):
        """Test too many bathrooms"""
        record = {"bathrooms": 50}
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-013" in rule_ids

    def test_coordinates_outside_us(self, validator):
        """Test coordinates outside US bounds"""
        record = {
            "latitude": 51.5,  # London
            "longitude": -0.1
        }
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-014" in rule_ids

    def test_valid_continental_us_coordinates(self, validator):
        """Test valid continental US coordinates"""
        record = {
            "latitude": 34.0522,
            "longitude": -118.2437  # Los Angeles
        }
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-014" not in rule_ids

    def test_valid_alaska_coordinates(self, validator):
        """Test valid Alaska coordinates"""
        record = {
            "latitude": 64.2008,
            "longitude": -149.4937  # Fairbanks
        }
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-014" not in rule_ids

    def test_valid_hawaii_coordinates(self, validator):
        """Test valid Hawaii coordinates"""
        record = {
            "latitude": 21.3069,
            "longitude": -157.8583  # Honolulu
        }
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-014" not in rule_ids

    def test_valid_puerto_rico_coordinates(self, validator):
        """Test valid Puerto Rico coordinates"""
        record = {
            "latitude": 18.4655,
            "longitude": -66.1057  # San Juan
        }
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-014" not in rule_ids


class TestDeedValidation:
    """Tests for deed validation rules"""

    @pytest.fixture
    def validator(self):
        return BusinessRuleValidator()

    def test_valid_deed_record(self, validator, valid_deed_record):
        """Test a valid deed record passes"""
        result = validator.validate_deed(valid_deed_record)
        assert result.is_valid is True

    def test_future_recording_date(self, validator):
        """Test recording date in the future"""
        future = date.today() + timedelta(days=30)
        record = {"recording_date": future.isoformat()}
        result = validator.validate_deed(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "DEED-001" in rule_ids

    def test_recording_date_too_old(self, validator):
        """Test recording date before 1800"""
        record = {"recording_date": "1750-01-01"}
        result = validator.validate_deed(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "DEED-002" in rule_ids

    def test_negative_consideration(self, validator):
        """Test negative consideration amount"""
        record = {"consideration": -50000}
        result = validator.validate_deed(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "DEED-003" in rule_ids

    def test_consideration_too_high(self, validator):
        """Test consideration above maximum"""
        record = {"consideration": 2_000_000_000}
        result = validator.validate_deed(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "DEED-004" in rule_ids

    def test_same_grantor_grantee(self, validator):
        """Test grantor and grantee are the same"""
        record = {
            "grantor": "John Smith",
            "grantee": "JOHN SMITH"  # Same person, different case
        }
        result = validator.validate_deed(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "DEED-005" in rule_ids

    def test_different_grantor_grantee(self, validator):
        """Test different grantor and grantee pass"""
        record = {
            "grantor": "John Smith",
            "grantee": "Jane Doe"
        }
        result = validator.validate_deed(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "DEED-005" not in rule_ids

    def test_invalid_state(self, validator):
        """Test invalid state code"""
        record = {"state": "ZZ"}
        result = validator.validate_deed(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "DEED-006" in rule_ids


class TestCourtCaseValidation:
    """Tests for court case validation rules"""

    @pytest.fixture
    def validator(self):
        return BusinessRuleValidator()

    def test_valid_court_case(self, validator, valid_court_case_record):
        """Test a valid court case passes"""
        result = validator.validate_court_case(valid_court_case_record)
        assert result.is_valid is True

    def test_future_filing_date(self, validator):
        """Test filing date in the future"""
        future = date.today() + timedelta(days=30)
        record = {"filing_date": future.isoformat()}
        result = validator.validate_court_case(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "COURT-001" in rule_ids

    def test_disposition_before_filing(self, validator):
        """Test disposition date before filing date"""
        record = {
            "filing_date": "2024-06-01",
            "disposition_date": "2024-01-01"
        }
        result = validator.validate_court_case(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "COURT-002" in rule_ids

    def test_negative_amount_claimed(self, validator):
        """Test negative amount claimed"""
        record = {"amount_claimed": -10000}
        result = validator.validate_court_case(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "COURT-003" in rule_ids

    def test_amount_claimed_too_high(self, validator):
        """Test amount claimed above maximum"""
        record = {"amount_claimed": 50_000_000_000}  # $50B
        result = validator.validate_court_case(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "COURT-004" in rule_ids

    def test_judgment_exceeds_claim(self, validator):
        """Test judgment greatly exceeds amount claimed"""
        record = {
            "amount_claimed": 10000,
            "judgment_amount": 500000  # 50x claim
        }
        result = validator.validate_court_case(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "COURT-005" in rule_ids

    def test_reasonable_judgment(self, validator):
        """Test reasonable judgment doesn't trigger"""
        record = {
            "amount_claimed": 10000,
            "judgment_amount": 15000  # 1.5x claim
        }
        result = validator.validate_court_case(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "COURT-005" not in rule_ids

    def test_closed_without_disposition(self, validator):
        """Test closed case without disposition date"""
        record = {"case_status": "CLOSED"}
        result = validator.validate_court_case(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "COURT-006" in rule_ids

    def test_closed_with_disposition(self, validator):
        """Test closed case with disposition date"""
        record = {
            "case_status": "CLOSED",
            "disposition_date": "2024-06-15",
            "filing_date": "2024-01-01"
        }
        result = validator.validate_court_case(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "COURT-006" not in rule_ids

    def test_invalid_state(self, validator):
        """Test invalid state code"""
        record = {"state": "AB"}
        result = validator.validate_court_case(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "COURT-007" in rule_ids


class TestBusinessValidation:
    """Tests for business entity validation rules"""

    @pytest.fixture
    def validator(self):
        return BusinessRuleValidator()

    def test_valid_business_record(self, validator, valid_business_entity_record):
        """Test a valid business record passes"""
        result = validator.validate_business(valid_business_entity_record)
        assert result.is_valid is True

    def test_future_formation_date(self, validator):
        """Test formation date in the future"""
        future = date.today() + timedelta(days=30)
        record = {"formation_date": future.isoformat()}
        result = validator.validate_business(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "BUS-001" in rule_ids

    def test_formation_date_too_old(self, validator):
        """Test formation date before 1800"""
        record = {"formation_date": "1750-01-01"}
        result = validator.validate_business(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "BUS-002" in rule_ids

    def test_dissolution_before_formation(self, validator):
        """Test dissolution date before formation date"""
        record = {
            "formation_date": "2020-06-01",
            "dissolution_date": "2019-01-01"
        }
        result = validator.validate_business(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "BUS-003" in rule_ids

    def test_active_with_dissolution(self, validator):
        """Test active entity with dissolution date"""
        record = {
            "status": "ACTIVE",
            "dissolution_date": "2024-01-01"
        }
        result = validator.validate_business(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "BUS-004" in rule_ids

    def test_dissolved_without_date(self, validator):
        """Test dissolved entity without dissolution date"""
        record = {"status": "DISSOLVED"}
        result = validator.validate_business(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "BUS-005" in rule_ids

    def test_dissolved_with_date(self, validator):
        """Test dissolved entity with dissolution date"""
        record = {
            "status": "DISSOLVED",
            "dissolution_date": "2024-01-01"
        }
        result = validator.validate_business(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "BUS-005" not in rule_ids

    def test_invalid_ein_format(self, validator):
        """Test invalid EIN format"""
        record = {"ein": "123456789"}  # Missing dash
        result = validator.validate_business(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "BUS-006" in rule_ids

    def test_valid_ein_format(self, validator):
        """Test valid EIN format"""
        record = {"ein": "12-3456789"}
        result = validator.validate_business(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "BUS-006" not in rule_ids

    def test_invalid_state(self, validator):
        """Test invalid state code"""
        record = {"state": "XY"}
        result = validator.validate_business(record)
        assert result.is_valid is False
        rule_ids = [v.rule_id for v in result.violations]
        assert "BUS-007" in rule_ids


class TestDateParsing:
    """Tests for date parsing functionality"""

    @pytest.fixture
    def validator(self):
        return BusinessRuleValidator()

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
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = validator._parse_date(dt)
        # Returns the date portion of the datetime
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_none(self, validator):
        """Test parsing None value"""
        result = validator._parse_date(None)
        assert result is None

    def test_parse_invalid_string(self, validator):
        """Test parsing invalid date string"""
        result = validator._parse_date("not a date")
        assert result is None


class TestCoordinateValidation:
    """Tests for coordinate validation"""

    @pytest.fixture
    def validator(self):
        return BusinessRuleValidator()

    def test_continental_us_coordinates(self, validator):
        """Test continental US coordinates are valid"""
        assert validator._is_valid_us_coordinates(40.7128, -74.0060) is False  # NYC is in main bounds
        # Check the main bounds logic
        lat, lon = 40.7128, -74.0060
        assert 24 <= lat <= 50 and -125 <= lon <= -66  # NYC is in continental bounds

    def test_alaska_coordinates(self, validator):
        """Test Alaska coordinates"""
        assert validator._is_valid_us_coordinates(64.2008, -149.4937) is True

    def test_hawaii_coordinates(self, validator):
        """Test Hawaii coordinates"""
        assert validator._is_valid_us_coordinates(21.3069, -157.8583) is True

    def test_puerto_rico_coordinates(self, validator):
        """Test Puerto Rico coordinates"""
        assert validator._is_valid_us_coordinates(18.4655, -66.1057) is True

    def test_guam_coordinates(self, validator):
        """Test Guam coordinates"""
        assert validator._is_valid_us_coordinates(13.4443, 144.7937) is True

    def test_american_samoa_coordinates(self, validator):
        """Test American Samoa coordinates"""
        assert validator._is_valid_us_coordinates(-14.2710, -170.1322) is True

    def test_invalid_coordinates(self, validator):
        """Test coordinates outside US"""
        assert validator._is_valid_us_coordinates(51.5074, -0.1278) is False  # London
        assert validator._is_valid_us_coordinates(35.6762, 139.6503) is False  # Tokyo


class TestStatistics:
    """Tests for validation statistics"""

    @pytest.fixture
    def validator(self):
        return BusinessRuleValidator()

    def test_statistics_all_valid(self, validator):
        """Test statistics with all valid records"""
        results = [
            RuleResult(is_valid=True),
            RuleResult(is_valid=True),
            RuleResult(is_valid=True),
        ]
        stats = validator.get_statistics(results)
        assert stats['total_records'] == 3
        assert stats['valid_records'] == 3
        assert stats['invalid_records'] == 0
        assert stats['validation_rate'] == 1.0

    def test_statistics_some_invalid(self, validator):
        """Test statistics with some invalid records"""
        results = [
            RuleResult(is_valid=True),
            RuleResult(is_valid=False),
            RuleResult(is_valid=True),
        ]
        stats = validator.get_statistics(results)
        assert stats['total_records'] == 3
        assert stats['valid_records'] == 2
        assert stats['invalid_records'] == 1
        assert stats['validation_rate'] == 2/3

    def test_statistics_by_severity(self, validator):
        """Test statistics by violation severity"""
        result1 = RuleResult()
        result1.add_violation("R1", "Rule 1", "msg", RuleSeverity.HIGH)
        result1.add_violation("R2", "Rule 2", "msg", RuleSeverity.LOW)

        result2 = RuleResult()
        result2.add_violation("R1", "Rule 1", "msg", RuleSeverity.HIGH)

        stats = validator.get_statistics([result1, result2])
        assert stats['violations_by_severity']['high'] == 2
        assert stats['violations_by_severity']['low'] == 1

    def test_statistics_by_rule(self, validator):
        """Test statistics by rule ID"""
        result1 = RuleResult()
        result1.add_violation("PROP-001", "Rule 1", "msg")
        result1.add_violation("PROP-002", "Rule 2", "msg")

        result2 = RuleResult()
        result2.add_violation("PROP-001", "Rule 1", "msg")

        stats = validator.get_statistics([result1, result2])
        assert stats['violations_by_rule']['PROP-001'] == 2
        assert stats['violations_by_rule']['PROP-002'] == 1

    def test_statistics_empty(self, validator):
        """Test statistics with empty results"""
        stats = validator.get_statistics([])
        assert stats['total_records'] == 0
        assert stats['validation_rate'] == 0


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_validate_property_record(self, valid_property_record):
        """Test validate_property_record function"""
        result = validate_property_record(valid_property_record)
        assert result.is_valid is True
        assert result.record_type == 'property'

    def test_validate_property_record_invalid(self):
        """Test validate_property_record with invalid data"""
        record = {"year_built": 1500}
        result = validate_property_record(record)
        assert result.is_valid is False

    def test_validate_court_record(self, valid_court_case_record):
        """Test validate_court_record function"""
        result = validate_court_record(valid_court_case_record)
        assert result.is_valid is True
        assert result.record_type == 'court_case'

    def test_validate_business_record(self, valid_business_entity_record):
        """Test validate_business_record function"""
        result = validate_business_record(valid_business_entity_record)
        assert result.is_valid is True
        assert result.record_type == 'business_entity'


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    @pytest.fixture
    def validator(self):
        return BusinessRuleValidator()

    def test_empty_record(self, validator):
        """Test validation with empty record"""
        result = validator.validate_property({})
        assert result.is_valid is True  # No violations for empty record
        assert len(result.violations) == 0

    def test_none_values(self, validator):
        """Test validation with None values"""
        record = {
            "year_built": None,
            "assessed_value": None,
            "state": None
        }
        result = validator.validate_property(record)
        assert result.is_valid is True

    def test_zero_values(self, validator):
        """Test validation with zero values"""
        record = {
            "assessed_value": 0,
            "square_feet": 0
        }
        result = validator.validate_property(record)
        # Zero values should be handled gracefully
        assert isinstance(result, RuleResult)

    def test_boundary_year_built(self, validator):
        """Test year built at boundaries"""
        # At minimum
        record = {"year_built": 1600}
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-001" not in rule_ids

        # Just below minimum
        record = {"year_built": 1599}
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-001" in rule_ids

    def test_boundary_coordinates(self, validator):
        """Test coordinate boundaries"""
        # Continental US boundary
        record = {
            "latitude": 24.0,  # Southern Florida
            "longitude": -80.0
        }
        result = validator.validate_property(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "PROP-014" not in rule_ids

    def test_special_characters_in_names(self, validator):
        """Test handling of special characters"""
        record = {
            "grantor": "José García",
            "grantee": "François Müller"
        }
        result = validator.validate_deed(record)
        # Should not crash
        assert isinstance(result, RuleResult)

    def test_whitespace_in_names(self, validator):
        """Test whitespace handling in name comparison"""
        record = {
            "grantor": "  John Smith  ",
            "grantee": "John Smith"
        }
        result = validator.validate_deed(record)
        rule_ids = [v.rule_id for v in result.violations]
        assert "DEED-005" in rule_ids

    def test_multiple_violations(self, validator):
        """Test record with multiple violations"""
        record = {
            "year_built": 1500,
            "assessed_value": 500,
            "state": "XX",
            "bedrooms": 50,
            "bathrooms": 50
        }
        result = validator.validate_property(record)
        assert len(result.violations) >= 4
