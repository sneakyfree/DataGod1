"""
Comprehensive tests for CoreLogic API module.

Tests cover:
- Enums (PropertyType, TransactionType, ForeclosureStatus)
- Data classes (PropertyCharacteristics, TaxAssessment, SaleTransaction,
               MortgageRecord, ForeclosureRecord, AVMResult, PropertySearch)
- CoreLogicAPI abstract class and signature generation
- CoreLogicAPIClient implementation
"""

import hashlib
import hmac
import time
from datetime import date, datetime
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from datagod.scrapers.paid.corelogic_api import (
    AVMResult,
    CoreLogicAPI,
    CoreLogicAPIClient,
    ForeclosureRecord,
    ForeclosureStatus,
    MortgageRecord,
    PropertyCharacteristics,
    PropertySearch,
    PropertyType,
    SaleTransaction,
    TaxAssessment,
    TransactionType,
    create_corelogic_client,
)


class TestPropertyTypeEnum:
    """Tests for PropertyType enumeration"""

    def test_all_property_types_exist(self):
        """Verify all expected property types are defined"""
        expected_types = [
            "SINGLE_FAMILY",
            "CONDO",
            "TOWNHOUSE",
            "MULTI_FAMILY",
            "MOBILE_HOME",
            "VACANT_LAND",
            "COMMERCIAL",
            "INDUSTRIAL",
            "AGRICULTURAL",
            "UNKNOWN",
        ]
        for prop_type in expected_types:
            assert hasattr(PropertyType, prop_type)

    def test_property_type_values(self):
        """Verify property type string values"""
        assert PropertyType.SINGLE_FAMILY.value == "SFR"
        assert PropertyType.CONDO.value == "CONDO"
        assert PropertyType.MULTI_FAMILY.value == "MFR"
        assert PropertyType.VACANT_LAND.value == "LAND"


class TestTransactionTypeEnum:
    """Tests for TransactionType enumeration"""

    def test_all_transaction_types_exist(self):
        """Verify all expected transaction types are defined"""
        expected_types = [
            "SALE",
            "REFINANCE",
            "FORECLOSURE",
            "REO",
            "SHORT_SALE",
            "AUCTION",
            "TRANSFER",
            "UNKNOWN",
        ]
        for trans_type in expected_types:
            assert hasattr(TransactionType, trans_type)

    def test_transaction_type_values(self):
        """Verify transaction type string values"""
        assert TransactionType.SALE.value == "sale"
        assert TransactionType.REFINANCE.value == "refinance"
        assert TransactionType.FORECLOSURE.value == "foreclosure"


class TestForeclosureStatusEnum:
    """Tests for ForeclosureStatus enumeration"""

    def test_all_foreclosure_statuses_exist(self):
        """Verify all expected foreclosure statuses are defined"""
        expected_statuses = [
            "PRE_FORECLOSURE",
            "AUCTION_SCHEDULED",
            "AUCTION_COMPLETED",
            "BANK_OWNED",
            "SOLD",
            "CANCELLED",
            "UNKNOWN",
        ]
        for status in expected_statuses:
            assert hasattr(ForeclosureStatus, status)

    def test_foreclosure_status_values(self):
        """Verify foreclosure status string values"""
        assert ForeclosureStatus.PRE_FORECLOSURE.value == "pre_foreclosure"
        assert ForeclosureStatus.BANK_OWNED.value == "bank_owned"


class TestPropertyCharacteristics:
    """Tests for PropertyCharacteristics dataclass"""

    def test_create_minimal_property(self):
        """Test creating property characteristics with required fields"""
        prop = PropertyCharacteristics(
            property_id="P123456",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            county="Harris",
            apn="1234567890",
        )
        assert prop.property_id == "P123456"
        assert prop.address == "123 Main St"
        assert prop.property_type == PropertyType.UNKNOWN
        assert prop.bedrooms is None
        assert prop.pool is False

    def test_create_full_property(self):
        """Test creating property characteristics with all fields"""
        prop = PropertyCharacteristics(
            property_id="P123456",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            county="Harris",
            apn="1234567890",
            property_type=PropertyType.SINGLE_FAMILY,
            property_use="Residential",
            lot_size_sqft=8500.0,
            lot_size_acres=0.195,
            building_sqft=2500.0,
            living_sqft=2200.0,
            bedrooms=4,
            bathrooms=2.5,
            total_rooms=8,
            year_built=2010,
            stories=2,
            units=1,
            pool=True,
            garage_spaces=2,
            fireplace=True,
            latitude=29.7604,
            longitude=-95.3698,
        )
        assert prop.bedrooms == 4
        assert prop.bathrooms == 2.5
        assert prop.pool is True
        assert prop.latitude == 29.7604

    def test_property_to_dict(self):
        """Test converting property characteristics to dictionary"""
        prop = PropertyCharacteristics(
            property_id="P123456",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            county="Harris",
            apn="1234567890",
            property_type=PropertyType.CONDO,
            bedrooms=2,
        )
        result = prop.to_dict()
        assert result["property_id"] == "P123456"
        assert result["property_type"] == "CONDO"
        assert result["bedrooms"] == 2
        assert "fetched_at" in result


class TestTaxAssessment:
    """Tests for TaxAssessment dataclass"""

    def test_create_minimal_assessment(self):
        """Test creating tax assessment with required fields"""
        assessment = TaxAssessment(property_id="P123456", tax_year=2024)
        assert assessment.property_id == "P123456"
        assert assessment.tax_year == 2024
        assert assessment.tax_delinquent is False

    def test_create_full_assessment(self):
        """Test creating tax assessment with all fields"""
        assessment = TaxAssessment(
            property_id="P123456",
            tax_year=2024,
            assessed_value_total=350000.0,
            assessed_value_land=100000.0,
            assessed_value_improvement=250000.0,
            market_value_total=400000.0,
            tax_amount=7500.0,
            tax_rate=0.0214,
            tax_status="Current",
            tax_delinquent=False,
            exemption_homestead=True,
            exemption_senior=False,
        )
        assert assessment.assessed_value_total == 350000.0
        assert assessment.exemption_homestead is True

    def test_assessment_to_dict(self):
        """Test converting tax assessment to dictionary"""
        assessment = TaxAssessment(
            property_id="P123456", tax_year=2024, tax_amount=7500.0, tax_delinquent=True
        )
        result = assessment.to_dict()
        assert result["property_id"] == "P123456"
        assert result["tax_year"] == 2024
        assert result["tax_delinquent"] is True


class TestSaleTransaction:
    """Tests for SaleTransaction dataclass"""

    def test_create_minimal_transaction(self):
        """Test creating sale transaction with required fields"""
        trans = SaleTransaction(property_id="P123456", transaction_id="T789")
        assert trans.property_id == "P123456"
        assert trans.transaction_type == TransactionType.UNKNOWN
        assert trans.arms_length is True

    def test_create_full_transaction(self):
        """Test creating sale transaction with all fields"""
        trans = SaleTransaction(
            property_id="P123456",
            transaction_id="T789",
            transaction_type=TransactionType.SALE,
            sale_date=date(2024, 6, 15),
            recording_date=date(2024, 6, 20),
            sale_price=450000.0,
            document_number="DOC12345",
            book_page="100/200",
            buyer_names=["John Smith", "Jane Smith"],
            seller_names=["Previous Owner LLC"],
            loan_amount=360000.0,
            lender_name="First National Bank",
            arms_length=True,
            distressed_sale=False,
        )
        assert trans.sale_price == 450000.0
        assert len(trans.buyer_names) == 2
        assert trans.loan_amount == 360000.0

    def test_transaction_to_dict(self):
        """Test converting sale transaction to dictionary"""
        trans = SaleTransaction(
            property_id="P123456",
            transaction_id="T789",
            sale_date=date(2024, 6, 15),
            sale_price=450000.0,
        )
        result = trans.to_dict()
        assert result["property_id"] == "P123456"
        assert result["sale_date"] == "2024-06-15"
        assert result["sale_price"] == 450000.0


class TestMortgageRecord:
    """Tests for MortgageRecord dataclass"""

    def test_create_minimal_mortgage(self):
        """Test creating mortgage record with required fields"""
        mortgage = MortgageRecord(
            property_id="P123456", mortgage_id="M789", loan_amount=360000.0
        )
        assert mortgage.loan_amount == 360000.0
        assert mortgage.lien_position == 1

    def test_create_full_mortgage(self):
        """Test creating mortgage record with all fields"""
        mortgage = MortgageRecord(
            property_id="P123456",
            mortgage_id="M789",
            loan_amount=360000.0,
            loan_type="Conventional",
            interest_rate=6.5,
            interest_rate_type="Fixed",
            loan_term_months=360,
            origination_date=date(2024, 1, 15),
            maturity_date=date(2054, 1, 15),
            borrower_names=["John Smith", "Jane Smith"],
            lender_name="First National Bank",
            lien_position=1,
        )
        assert mortgage.loan_type == "Conventional"
        assert mortgage.interest_rate == 6.5
        assert mortgage.loan_term_months == 360

    def test_mortgage_to_dict(self):
        """Test converting mortgage record to dictionary"""
        mortgage = MortgageRecord(
            property_id="P123456",
            mortgage_id="M789",
            loan_amount=360000.0,
            origination_date=date(2024, 1, 15),
        )
        result = mortgage.to_dict()
        assert result["loan_amount"] == 360000.0
        assert result["origination_date"] == "2024-01-15"


class TestForeclosureRecord:
    """Tests for ForeclosureRecord dataclass"""

    def test_create_minimal_foreclosure(self):
        """Test creating foreclosure record with required fields"""
        foreclosure = ForeclosureRecord(property_id="P123456", foreclosure_id="F789")
        assert foreclosure.status == ForeclosureStatus.UNKNOWN

    def test_create_full_foreclosure(self):
        """Test creating foreclosure record with all fields"""
        foreclosure = ForeclosureRecord(
            property_id="P123456",
            foreclosure_id="F789",
            status=ForeclosureStatus.PRE_FORECLOSURE,
            default_date=date(2024, 1, 15),
            auction_date=date(2024, 6, 15),
            default_amount=15000.0,
            unpaid_balance=350000.0,
            estimated_value=400000.0,
            borrower_names=["John Smith"],
            lender_name="First National Bank",
            original_loan_amount=380000.0,
        )
        assert foreclosure.status == ForeclosureStatus.PRE_FORECLOSURE
        assert foreclosure.default_amount == 15000.0

    def test_foreclosure_to_dict(self):
        """Test converting foreclosure record to dictionary"""
        foreclosure = ForeclosureRecord(
            property_id="P123456",
            foreclosure_id="F789",
            status=ForeclosureStatus.AUCTION_SCHEDULED,
            auction_date=date(2024, 6, 15),
        )
        result = foreclosure.to_dict()
        assert result["status"] == "auction_scheduled"
        assert result["auction_date"] == "2024-06-15"


class TestAVMResult:
    """Tests for AVMResult dataclass"""

    def test_create_minimal_avm(self):
        """Test creating AVM result with required fields"""
        avm = AVMResult(
            property_id="P123456",
            valuation_date=date(2024, 6, 15),
            estimated_value=450000.0,
        )
        assert avm.estimated_value == 450000.0
        assert avm.comparable_count == 0

    def test_create_full_avm(self):
        """Test creating AVM result with all fields"""
        avm = AVMResult(
            property_id="P123456",
            valuation_date=date(2024, 6, 15),
            estimated_value=450000.0,
            value_low=425000.0,
            value_high=475000.0,
            confidence_score=0.85,
            forecast_standard_deviation=12500.0,
            comparable_count=5,
            comparable_properties=["P111", "P222", "P333", "P444", "P555"],
            model_version="3.2.1",
        )
        assert avm.value_low == 425000.0
        assert avm.confidence_score == 0.85
        assert len(avm.comparable_properties) == 5

    def test_avm_to_dict(self):
        """Test converting AVM result to dictionary"""
        avm = AVMResult(
            property_id="P123456",
            valuation_date=date(2024, 6, 15),
            estimated_value=450000.0,
            confidence_score=0.85,
        )
        result = avm.to_dict()
        assert result["estimated_value"] == 450000.0
        assert result["valuation_date"] == "2024-06-15"
        assert result["confidence_score"] == 0.85


class TestPropertySearch:
    """Tests for PropertySearch dataclass"""

    def test_create_empty_search(self):
        """Test creating search with default values"""
        search = PropertySearch()
        assert search.address is None
        assert search.limit == 50
        assert search.offset == 0

    def test_create_address_search(self):
        """Test creating search by address"""
        search = PropertySearch(
            address="123 Main St", city="Houston", state="TX", zip_code="77001"
        )
        assert search.address == "123 Main St"
        assert search.city == "Houston"

    def test_create_filtered_search(self):
        """Test creating search with filters"""
        search = PropertySearch(
            state="TX",
            property_type=PropertyType.SINGLE_FAMILY,
            min_bedrooms=3,
            max_bedrooms=5,
            min_sqft=2000.0,
            max_sqft=4000.0,
            min_year_built=2000,
            min_value=300000.0,
            limit=100,
        )
        assert search.property_type == PropertyType.SINGLE_FAMILY
        assert search.min_bedrooms == 3
        assert search.limit == 100


class TestCoreLogicAPISignature:
    """Tests for CoreLogic API signature generation"""

    def test_generate_signature(self):
        """Test HMAC signature generation"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")

        timestamp = "1704067200000"  # Fixed timestamp for testing
        method = "GET"
        path = "/api/v1/properties"

        expected_message = f"{timestamp}{method}{path}"
        expected_signature = hmac.new(
            "test_secret".encode("utf-8"),
            expected_message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        actual_signature = client._generate_signature(timestamp, method, path)
        assert actual_signature == expected_signature

    def test_generate_signature_with_body(self):
        """Test HMAC signature generation with request body"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")

        timestamp = "1704067200000"
        method = "POST"
        path = "/api/v1/search"
        body = '{"address":"123 Main St"}'

        expected_message = f"{timestamp}{method}{path}{body}"
        expected_signature = hmac.new(
            "test_secret".encode("utf-8"),
            expected_message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        actual_signature = client._generate_signature(timestamp, method, path, body)
        assert actual_signature == expected_signature


class TestCoreLogicAPIClient:
    """Tests for CoreLogicAPIClient implementation"""

    def test_initialization(self):
        """Test CoreLogicAPIClient initialization"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")
        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"

    def test_initialization_with_config(self):
        """Test CoreLogicAPIClient initialization with config"""
        config = {"timeout": 60, "retry_count": 3}
        client = CoreLogicAPIClient(
            api_key="test_key", api_secret="test_secret", config=config
        )
        assert client.config["timeout"] == 60
        assert client.config["retry_count"] == 3

    def test_get_headers(self):
        """Test authenticated headers generation"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")

        with patch("time.time", return_value=1704067200.0):
            headers = client._get_headers("GET", "/api/v1/properties")

        assert headers["X-Api-Key"] == "test_key"
        assert "X-Timestamp" in headers
        assert "X-Signature" in headers
        assert headers["Content-Type"] == "application/json"

    def test_search_properties_returns_list(self):
        """Test search_properties method returns list"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")
        search = PropertySearch(address="123 Main St")
        results = client.search_properties(search)
        assert isinstance(results, list)

    def test_get_property_details_returns_none(self):
        """Test get_property_details method returns None (placeholder)"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")
        result = client.get_property_details("P123456")
        assert result is None

    def test_get_tax_history_returns_list(self):
        """Test get_tax_history method returns list"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")
        results = client.get_tax_history("P123456")
        assert isinstance(results, list)

    def test_get_sales_history_returns_list(self):
        """Test get_sales_history method returns list"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")
        results = client.get_sales_history("P123456")
        assert isinstance(results, list)

    def test_get_mortgage_history_returns_list(self):
        """Test get_mortgage_history method returns list"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")
        results = client.get_mortgage_history("P123456")
        assert isinstance(results, list)

    def test_get_foreclosure_status_returns_none(self):
        """Test get_foreclosure_status method returns None (placeholder)"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")
        result = client.get_foreclosure_status("P123456")
        assert result is None

    def test_get_avm_returns_none(self):
        """Test get_avm method returns None (placeholder)"""
        client = CoreLogicAPIClient(api_key="test_key", api_secret="test_secret")
        result = client.get_avm("P123456")
        assert result is None


class TestCreateCorelogicClientFunction:
    """Tests for create_corelogic_client factory function"""

    def test_create_client(self):
        """Test creating CoreLogic client via factory function"""
        client = create_corelogic_client(api_key="test_key", api_secret="test_secret")
        assert isinstance(client, CoreLogicAPIClient)
        assert client.api_key == "test_key"

    def test_create_client_with_config(self):
        """Test creating CoreLogic client with config"""
        config = {"timeout": 60}
        client = create_corelogic_client(
            api_key="test_key", api_secret="test_secret", config=config
        )
        assert client.config["timeout"] == 60


class TestCoreLogicImports:
    """Tests for module imports"""

    def test_all_exports_available(self):
        """Test that all expected exports are available"""
        from datagod.scrapers.paid.corelogic_api import (
            AVMResult,
            CoreLogicAPI,
            CoreLogicAPIClient,
            ForeclosureRecord,
            ForeclosureStatus,
            MortgageRecord,
            PropertyCharacteristics,
            PropertySearch,
            PropertyType,
            SaleTransaction,
            TaxAssessment,
            TransactionType,
            create_corelogic_client,
        )

        assert all(
            [
                PropertyType,
                TransactionType,
                ForeclosureStatus,
                PropertyCharacteristics,
                TaxAssessment,
                SaleTransaction,
                MortgageRecord,
                ForeclosureRecord,
                AVMResult,
                PropertySearch,
                CoreLogicAPI,
                CoreLogicAPIClient,
                create_corelogic_client,
            ]
        )


class TestCoreLogicEdgeCases:
    """Edge case tests for CoreLogic API module"""

    def test_property_with_null_coordinates(self):
        """Test property to_dict with null coordinates"""
        prop = PropertyCharacteristics(
            property_id="P123456",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            county="Harris",
            apn="1234567890",
        )
        result = prop.to_dict()
        assert result["latitude"] is None
        assert result["longitude"] is None

    def test_transaction_with_empty_names(self):
        """Test transaction with empty buyer/seller names"""
        trans = SaleTransaction(property_id="P123456", transaction_id="T789")
        result = trans.to_dict()
        assert result["buyer_names"] == []
        assert result["seller_names"] == []

    def test_mortgage_with_null_dates(self):
        """Test mortgage to_dict with null dates"""
        mortgage = MortgageRecord(
            property_id="P123456", mortgage_id="M789", loan_amount=360000.0
        )
        result = mortgage.to_dict()
        assert result["origination_date"] is None

    def test_foreclosure_with_null_dates(self):
        """Test foreclosure to_dict with null dates"""
        foreclosure = ForeclosureRecord(property_id="P123456", foreclosure_id="F789")
        result = foreclosure.to_dict()
        assert result["default_date"] is None
        assert result["auction_date"] is None

    def test_avm_with_empty_comparables(self):
        """Test AVM with empty comparable properties"""
        avm = AVMResult(
            property_id="P123456",
            valuation_date=date(2024, 6, 15),
            estimated_value=450000.0,
        )
        assert avm.comparable_properties == []
        assert avm.comparable_count == 0
