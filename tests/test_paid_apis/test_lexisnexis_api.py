"""
Comprehensive tests for LexisNexis API module.

Tests cover:
- Enums (PermissiblePurpose, RecordType)
- Data classes (PersonRecord, BusinessRecord, CourtRecord, AssetRecord)
- Search classes (PersonSearch, BusinessSearch)
- LexisNexisAPI abstract class and FCRA compliance
- LexisNexisAPIClient implementation
"""

import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from datagod.scrapers.paid.lexisnexis_api import (
    PermissiblePurpose,
    RecordType,
    PersonRecord,
    BusinessRecord,
    CourtRecord,
    AssetRecord,
    PersonSearch,
    BusinessSearch,
    LexisNexisAPI,
    LexisNexisAPIClient,
    create_lexisnexis_client,
)


class TestPermissiblePurposeEnum:
    """Tests for PermissiblePurpose enumeration (FCRA compliance)"""

    def test_all_permissible_purposes_exist(self):
        """Verify all expected permissible purposes are defined"""
        expected_purposes = [
            'CREDIT', 'EMPLOYMENT', 'TENANT_SCREENING',
            'LEGITIMATE_BUSINESS', 'INSURANCE', 'COURT_ORDER',
            'CONSUMER_CONSENT', 'ACCOUNT_REVIEW'
        ]
        for purpose in expected_purposes:
            assert hasattr(PermissiblePurpose, purpose)

    def test_permissible_purpose_values(self):
        """Verify permissible purpose string values"""
        assert PermissiblePurpose.CREDIT.value == "credit"
        assert PermissiblePurpose.EMPLOYMENT.value == "employment"
        assert PermissiblePurpose.TENANT_SCREENING.value == "tenant_screening"
        assert PermissiblePurpose.LEGITIMATE_BUSINESS.value == "legitimate_business"


class TestRecordTypeEnum:
    """Tests for RecordType enumeration"""

    def test_all_record_types_exist(self):
        """Verify all expected record types are defined"""
        expected_types = [
            'PERSON', 'BUSINESS', 'PROPERTY', 'VEHICLE',
            'COURT_CASE', 'BANKRUPTCY', 'LIEN_JUDGMENT', 'UCC',
            'PROFESSIONAL_LICENSE', 'CORPORATION'
        ]
        for record_type in expected_types:
            assert hasattr(RecordType, record_type)

    def test_record_type_values(self):
        """Verify record type string values"""
        assert RecordType.PERSON.value == "person"
        assert RecordType.BUSINESS.value == "business"
        assert RecordType.COURT_CASE.value == "court_case"


class TestPersonRecord:
    """Tests for PersonRecord dataclass"""

    def test_create_minimal_person(self):
        """Test creating person record with required fields"""
        person = PersonRecord(
            lexis_id="L123456",
            first_name="John",
            last_name="Smith"
        )
        assert person.lexis_id == "L123456"
        assert person.first_name == "John"
        assert person.last_name == "Smith"
        assert person.aliases == []

    def test_create_full_person(self):
        """Test creating person record with all fields"""
        person = PersonRecord(
            lexis_id="L123456",
            first_name="John",
            middle_name="Michael",
            last_name="Smith",
            suffix="Jr",
            date_of_birth=date(1985, 6, 15),
            age=39,
            ssn_last_four="1234",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            address_history=[
                {"address": "456 Oak Ave", "city": "Dallas", "state": "TX"}
            ],
            phones=["713-555-1234", "214-555-5678"],
            emails=["john.smith@email.com"],
            aliases=["Johnny Smith", "J. Smith"],
            relatives=[{"name": "Jane Smith", "relationship": "spouse"}],
            associates=[{"name": "Mike Johnson"}],
            employers=[{"employer": "Acme Corp", "title": "Manager"}],
            properties=[{"address": "789 Oak St"}],
            bankruptcies=[],
            match_score=0.95
        )
        assert person.middle_name == "Michael"
        assert person.ssn_last_four == "1234"
        assert len(person.address_history) == 1
        assert len(person.aliases) == 2

    def test_person_to_dict(self):
        """Test converting person record to dictionary"""
        person = PersonRecord(
            lexis_id="L123456",
            first_name="John",
            last_name="Smith",
            date_of_birth=date(1985, 6, 15)
        )
        result = person.to_dict()
        assert result['first_name'] == "John"
        assert result['last_name'] == "Smith"
        assert result['date_of_birth'] == "1985-06-15"
        assert 'fetched_at' in result


class TestBusinessRecord:
    """Tests for BusinessRecord dataclass"""

    def test_create_minimal_business(self):
        """Test creating business record with required fields"""
        business = BusinessRecord(
            lexis_id="B123456",
            business_name="Acme Corporation"
        )
        assert business.lexis_id == "B123456"
        assert business.business_name == "Acme Corporation"
        assert business.officers == []

    def test_create_full_business(self):
        """Test creating business record with all fields"""
        business = BusinessRecord(
            lexis_id="B123456",
            business_name="Acme Corporation",
            dba_names=["Acme Co", "Acme Inc"],
            duns_number="123456789",
            ein="12-3456789",
            business_type="Corporation",
            incorporation_state="TX",
            incorporation_date=date(2010, 1, 15),
            status="Active",
            address="789 Corporate Blvd",
            city="Houston",
            state="TX",
            zip_code="77001",
            phone="713-555-0000",
            website="https://acme.com",
            employee_count=100,
            annual_revenue=10000000.0,
            sic_code="7371",
            sic_description="Computer Services",
            officers=[
                {"name": "John Smith", "title": "CEO"},
                {"name": "Jane Doe", "title": "CFO"}
            ],
            registered_agent="ABC Agent Services",
            ucc_filings=[],
            liens_judgments=[],
            paydex_score=75
        )
        assert business.ein == "12-3456789"
        assert len(business.officers) == 2
        assert business.annual_revenue == 10000000.0

    def test_business_to_dict(self):
        """Test converting business record to dictionary"""
        business = BusinessRecord(
            lexis_id="B123456",
            business_name="Acme Corporation"
        )
        result = business.to_dict()
        assert result['business_name'] == "Acme Corporation"
        assert 'fetched_at' in result


class TestCourtRecord:
    """Tests for CourtRecord dataclass"""

    def test_create_minimal_court(self):
        """Test creating court record with required fields"""
        court = CourtRecord(
            lexis_id="C123456",
            case_number="2024-CV-001234",
            case_type="civil",
            court_name="Harris County District Court",
            court_state="TX"
        )
        assert court.lexis_id == "C123456"
        assert court.case_number == "2024-CV-001234"

    def test_create_full_court(self):
        """Test creating court record with all fields"""
        court = CourtRecord(
            lexis_id="C123456",
            case_number="2024-CV-001234",
            case_type="civil",
            court_name="Harris County District Court",
            court_state="TX",
            court_county="Harris",
            filing_date=date(2024, 1, 15),
            disposition_date=date(2024, 6, 15),
            case_title="Doe v. ABC Corp",
            case_status="Closed",
            disposition="Judgment for Plaintiff",
            plaintiffs=[{"name": "John Doe"}],
            defendants=[{"name": "ABC Corp"}],
            attorneys=[{"name": "Jane Smith", "firm": "Smith & Associates"}],
            judge_name="Hon. Bob Wilson",
            amount_claimed=100000.0,
            amount_awarded=50000.0
        )
        assert court.case_type == "civil"
        assert court.amount_awarded == 50000.0
        assert len(court.plaintiffs) == 1

    def test_court_to_dict(self):
        """Test converting court record to dictionary"""
        court = CourtRecord(
            lexis_id="C123456",
            case_number="2024-CV-001234",
            case_type="civil",
            court_name="Harris County District Court",
            court_state="TX",
            filing_date=date(2024, 1, 15)
        )
        result = court.to_dict()
        assert result['case_number'] == "2024-CV-001234"
        assert result['filing_date'] == "2024-01-15"


class TestAssetRecord:
    """Tests for AssetRecord dataclass"""

    def test_create_minimal_asset(self):
        """Test creating asset record with required fields"""
        asset = AssetRecord(
            lexis_id="A123456",
            asset_type="vehicle",
            owner_name="John Smith"
        )
        assert asset.lexis_id == "A123456"
        assert asset.asset_type == "vehicle"

    def test_create_full_asset(self):
        """Test creating asset record with all fields"""
        asset = AssetRecord(
            lexis_id="A123456",
            asset_type="vehicle",
            owner_name="John Smith",
            owner_lexis_id="L789012",
            vin="1HGCM82633A123456",
            make="Honda",
            model="Accord",
            year=2022,
            license_plate="ABC1234",
            license_state="TX"
        )
        assert asset.vin == "1HGCM82633A123456"
        assert asset.year == 2022

    def test_asset_to_dict(self):
        """Test converting asset record to dictionary"""
        asset = AssetRecord(
            lexis_id="A123456",
            asset_type="vehicle",
            owner_name="John Smith"
        )
        result = asset.to_dict()
        assert result['asset_type'] == "vehicle"
        assert 'fetched_at' in result


class TestPersonSearch:
    """Tests for PersonSearch dataclass"""

    def test_create_minimal_search(self):
        """Test creating person search with defaults"""
        search = PersonSearch()
        assert search.first_name is None
        assert search.permissible_purpose == PermissiblePurpose.LEGITIMATE_BUSINESS

    def test_create_full_search(self):
        """Test creating person search with all fields"""
        search = PersonSearch(
            first_name="John",
            last_name="Smith",
            middle_name="Michael",
            date_of_birth=date(1985, 6, 15),
            ssn="123-45-6789",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            phone="713-555-1234",
            email="john@email.com",
            include_address_history=True,
            include_relatives=True,
            include_associates=True,
            include_properties=True,
            include_court_records=True,
            permissible_purpose=PermissiblePurpose.EMPLOYMENT
        )
        assert search.first_name == "John"
        assert search.include_relatives is True


class TestBusinessSearch:
    """Tests for BusinessSearch dataclass"""

    def test_create_minimal_search(self):
        """Test creating business search with defaults"""
        search = BusinessSearch()
        assert search.business_name is None

    def test_create_full_search(self):
        """Test creating business search with all fields"""
        search = BusinessSearch(
            business_name="Acme",
            dba_name="Acme Corp",
            duns_number="123456789",
            ein="12-3456789",
            city="Houston",
            state="TX",
            zip_code="77001",
            sic_code="7371",
            naics_code="541511",
            include_officers=True,
            include_filings=True,
            include_credit=True
        )
        assert search.ein == "12-3456789"
        assert search.include_officers is True


class TestLexisNexisFCRACompliance:
    """Tests for FCRA compliance in LexisNexis API"""

    def test_validate_permissible_purpose_valid(self):
        """Test valid permissible purpose passes validation"""
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        result = client.validate_permissible_purpose(PermissiblePurpose.CREDIT)
        assert result is True

    def test_validate_permissible_purpose_none_raises(self):
        """Test None permissible purpose raises ValueError"""
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        with pytest.raises(ValueError) as exc_info:
            client.validate_permissible_purpose(None)
        assert "Permissible purpose is required" in str(exc_info.value)

    def test_all_permissible_purposes_valid(self):
        """Test all permissible purposes pass validation"""
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        for purpose in PermissiblePurpose:
            result = client.validate_permissible_purpose(purpose)
            assert result is True


class TestLexisNexisAPIClient:
    """Tests for LexisNexisAPIClient implementation"""

    def test_initialization(self):
        """Test LexisNexisAPIClient initialization"""
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"
        assert client.customer_id == "test_customer"

    def test_initialization_with_config(self):
        """Test LexisNexisAPIClient initialization with config"""
        config = {'timeout': 60}
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer",
            config=config
        )
        assert client.config['timeout'] == 60

    def test_search_person_returns_list(self):
        """Test search_person method returns list"""
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        search = PersonSearch(
            first_name="John",
            last_name="Smith",
            permissible_purpose=PermissiblePurpose.LEGITIMATE_BUSINESS
        )
        results = client.search_person(search)
        assert isinstance(results, list)

    def test_get_person_report_returns_none(self):
        """Test get_person_report method returns None (placeholder)"""
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        result = client.get_person_report("L123456", PermissiblePurpose.CREDIT)
        assert result is None

    def test_search_business_returns_list(self):
        """Test search_business method returns list"""
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        search = BusinessSearch(business_name="Acme")
        results = client.search_business(search)
        assert isinstance(results, list)

    def test_get_business_report_returns_none(self):
        """Test get_business_report method returns None (placeholder)"""
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        result = client.get_business_report("B123456")
        assert result is None

    def test_search_court_records_returns_list(self):
        """Test search_court_records method returns list"""
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        results = client.search_court_records(party_name="John Smith", state="TX")
        assert isinstance(results, list)

    def test_search_assets_returns_list(self):
        """Test search_assets method returns list"""
        client = LexisNexisAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        results = client.search_assets(owner_name="John Smith")
        assert isinstance(results, list)


class TestCreateLexisnexisClientFunction:
    """Tests for create_lexisnexis_client factory function"""

    def test_create_client(self):
        """Test creating LexisNexis client via factory function"""
        client = create_lexisnexis_client(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer"
        )
        assert isinstance(client, LexisNexisAPIClient)
        assert client.api_key == "test_key"

    def test_create_client_with_config(self):
        """Test creating LexisNexis client with config"""
        config = {'timeout': 60}
        client = create_lexisnexis_client(
            api_key="test_key",
            api_secret="test_secret",
            customer_id="test_customer",
            config=config
        )
        assert client.config['timeout'] == 60


class TestLexisNexisImports:
    """Tests for module imports"""

    def test_all_exports_available(self):
        """Test that all expected exports are available"""
        from datagod.scrapers.paid.lexisnexis_api import (
            PermissiblePurpose,
            RecordType,
            PersonRecord,
            BusinessRecord,
            CourtRecord,
            AssetRecord,
            PersonSearch,
            BusinessSearch,
            LexisNexisAPI,
            LexisNexisAPIClient,
            create_lexisnexis_client
        )
        assert all([
            PermissiblePurpose, RecordType, PersonRecord, BusinessRecord,
            CourtRecord, AssetRecord, PersonSearch, BusinessSearch,
            LexisNexisAPI, LexisNexisAPIClient, create_lexisnexis_client
        ])


class TestLexisNexisEdgeCases:
    """Edge case tests for LexisNexis API module"""

    def test_person_with_null_dob(self):
        """Test person record with null date of birth"""
        person = PersonRecord(
            lexis_id="L123456",
            first_name="John",
            last_name="Smith"
        )
        result = person.to_dict()
        assert result['date_of_birth'] is None

    def test_person_with_empty_lists(self):
        """Test person record with empty lists"""
        person = PersonRecord(
            lexis_id="L123456",
            first_name="John",
            last_name="Smith"
        )
        result = person.to_dict()
        assert result['aliases'] == []
        assert result['phones'] == []

    def test_business_with_null_dates(self):
        """Test business record with null dates"""
        business = BusinessRecord(
            lexis_id="B123456",
            business_name="Acme Corp"
        )
        result = business.to_dict()
        # incorporation_date is not in to_dict output, check another null field
        assert result['ein'] is None

    def test_court_with_null_amounts(self):
        """Test court record with null amounts"""
        court = CourtRecord(
            lexis_id="C123456",
            case_number="2024-CV-001234",
            case_type="civil",
            court_name="District Court",
            court_state="TX"
        )
        result = court.to_dict()
        assert result['amount_claimed'] is None
        assert result['amount_awarded'] is None

    def test_asset_vehicle_vs_property(self):
        """Test asset record for vehicle vs property"""
        vehicle = AssetRecord(
            lexis_id="A1",
            asset_type="vehicle",
            owner_name="John Smith",
            vin="1HGCM82633A123456"
        )
        property_asset = AssetRecord(
            lexis_id="A2",
            asset_type="property",
            owner_name="John Smith",
            property_address="123 Main St"
        )
        assert vehicle.vin == "1HGCM82633A123456"
        assert property_asset.property_address == "123 Main St"
