"""
Tests for Mortgage Data Gathering Neural Network
"""

import pytest
from datetime import datetime


class TestMortgageDataPoint:
    """Tests for MortgageDataPoint dataclass"""

    def test_mortgage_data_point_creation(self):
        """Test creating a MortgageDataPoint"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataPoint

        data_point = MortgageDataPoint(
            property_id="PROP-123",
            borrower_name="John Doe",
            lender_name="First National Bank",
            loan_amount=250000.0,
            loan_type="Conventional",
            interest_rate=4.5,
            loan_term=30,
            loan_date="2024-01-15",
            property_address="123 Main St, Anytown, CA 90210",
            property_value=300000.0,
            status="active",
            data_source="property_records",
            scraped_at=datetime.now().isoformat()
        )

        assert data_point.property_id == "PROP-123"
        assert data_point.borrower_name == "John Doe"
        assert data_point.loan_amount == 250000.0
        assert data_point.interest_rate == 4.5
        assert data_point.loan_term == 30

    def test_mortgage_data_point_with_quality_score(self):
        """Test MortgageDataPoint with quality score"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataPoint

        data_point = MortgageDataPoint(
            property_id="PROP-456",
            borrower_name="Jane Smith",
            lender_name="Community Bank",
            loan_amount=350000.0,
            loan_type="FHA",
            interest_rate=3.75,
            loan_term=15,
            loan_date="2024-02-01",
            property_address="456 Oak Ave, Somewhere, NY 10001",
            property_value=400000.0,
            status="active",
            data_source="court_records",
            scraped_at=datetime.now().isoformat(),
            quality_score=95.5,
            confidence_score=88.0
        )

        assert data_point.quality_score == 95.5
        assert data_point.confidence_score == 88.0


class TestMortgageDataGatheringNeuralNetwork:
    """Tests for MortgageDataGatheringNeuralNetwork class"""

    def test_neural_network_initialization(self):
        """Test neural network initialization"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork

        nn = MortgageDataGatheringNeuralNetwork()

        assert nn is not None
        assert nn.similarity_threshold == 0.7
        assert 'loan_amount' in nn.patterns
        assert 'interest_rate' in nn.patterns

    def test_neural_network_patterns(self):
        """Test that patterns are defined correctly"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork

        nn = MortgageDataGatheringNeuralNetwork()

        # Check that patterns are defined for key fields
        assert len(nn.patterns['loan_amount']) > 0
        assert len(nn.patterns['interest_rate']) > 0
        assert 'loan_term' in nn.patterns
        assert 'property_value' in nn.patterns

    def test_extract_mortgage_data(self):
        """Test mortgage data extraction"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork

        nn = MortgageDataGatheringNeuralNetwork()

        # Test extraction from text
        raw_data = """
        Property: 123 Main Street
        Borrower: John Smith
        Lender: First National Bank
        Loan Amount: $350,000
        Interest Rate: 4.25%
        Loan Type: Conventional
        Term: 30 years
        """

        result = nn.extract_mortgage_data(raw_data, "property_records")

        # Should return list of data points
        assert isinstance(result, list)

    def test_get_data_quality_score(self):
        """Test data quality score calculation"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork, MortgageDataPoint

        nn = MortgageDataGatheringNeuralNetwork()

        data_point = MortgageDataPoint(
            property_id="PROP-789",
            borrower_name="Test User",
            lender_name="Test Bank",
            loan_amount=200000.0,
            loan_type="VA",
            interest_rate=3.25,
            loan_term=30,
            loan_date="2024-03-01",
            property_address="789 Test Blvd, Testville, TX 75001",
            property_value=250000.0,
            status="active",
            data_source="property_records",
            scraped_at=datetime.now().isoformat()
        )

        score = nn.get_data_quality_score(data_point)

        # Score should be a number between 0 and 100
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    def test_validate_mortgage_data(self):
        """Test mortgage data validation"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork, MortgageDataPoint

        nn = MortgageDataGatheringNeuralNetwork()

        valid_record = MortgageDataPoint(
            property_id="PROP-VALID",
            borrower_name="Valid User",
            lender_name="Valid Bank",
            loan_amount=500000.0,
            loan_type="Conventional",
            interest_rate=3.5,
            loan_term=30,
            loan_date="2024-04-01",
            property_address="Valid Address",
            property_value=600000.0,
            status="active",
            data_source="property_records",
            scraped_at=datetime.now().isoformat()
        )

        # validate_mortgage_data takes a single data point and returns bool
        is_valid = nn.validate_mortgage_data(valid_record)

        # Should return True for valid record
        assert is_valid is True

    def test_enhance_data_quality(self):
        """Test data quality enhancement"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork, MortgageDataPoint

        nn = MortgageDataGatheringNeuralNetwork()

        records = [
            MortgageDataPoint(
                property_id="PROP-ENH",
                borrower_name="Test User",
                lender_name="Test Bank",
                loan_amount=300000.0,
                loan_type="FHA",
                interest_rate=4.0,
                loan_term=30,
                loan_date="2024-05-01",
                property_address="456 Enhancement St",
                property_value=350000.0,
                status="active",
                data_source="property_records",
                scraped_at=datetime.now().isoformat()
            )
        ]

        enhanced = nn.enhance_data_quality(records)

        assert isinstance(enhanced, list)
        assert len(enhanced) >= 0

    def test_get_data_insights(self):
        """Test data insights generation"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork, MortgageDataPoint

        nn = MortgageDataGatheringNeuralNetwork()

        records = [
            MortgageDataPoint(
                property_id="PROP-INS-1",
                borrower_name="User One",
                lender_name="Bank One",
                loan_amount=250000.0,
                loan_type="Conventional",
                interest_rate=4.5,
                loan_term=30,
                loan_date="2024-01-15",
                property_address="123 Main St",
                property_value=300000.0,
                status="active",
                data_source="property_records",
                scraped_at=datetime.now().isoformat()
            ),
            MortgageDataPoint(
                property_id="PROP-INS-2",
                borrower_name="User Two",
                lender_name="Bank Two",
                loan_amount=450000.0,
                loan_type="FHA",
                interest_rate=3.75,
                loan_term=15,
                loan_date="2024-02-01",
                property_address="456 Oak Ave",
                property_value=500000.0,
                status="active",
                data_source="court_records",
                scraped_at=datetime.now().isoformat()
            )
        ]

        insights = nn.get_data_insights(records)

        assert isinstance(insights, dict)

    def test_learn_patterns(self):
        """Test pattern learning"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork, MortgageDataPoint

        nn = MortgageDataGatheringNeuralNetwork()

        records = [
            MortgageDataPoint(
                property_id="PROP-LEARN",
                borrower_name="Learner User",
                lender_name="Learning Bank",
                loan_amount=350000.0,
                loan_type="VA",
                interest_rate=3.0,
                loan_term=30,
                loan_date="2024-03-15",
                property_address="789 Learn Blvd",
                property_value=400000.0,
                status="active",
                data_source="property_records",
                scraped_at=datetime.now().isoformat()
            )
        ]

        # Learn patterns should work without errors
        nn.learn_patterns(records)

        # Check that learning patterns are populated
        assert isinstance(nn.learning_patterns, dict)

    def test_process_mortgage_data(self):
        """Test processing mortgage data"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork

        nn = MortgageDataGatheringNeuralNetwork()

        raw_data = """
        Mortgage Record
        Property Address: 123 Main Street, Anytown, CA 90210
        Borrower: John Smith
        Lender: First National Bank
        Loan Amount: $350,000
        Interest Rate: 4.25%
        Loan Type: Conventional
        Term: 30 years
        Recording Date: 2024-01-15
        """

        result = nn.process_mortgage_data(raw_data, "property_records")

        assert isinstance(result, list)


class TestMortgageDataPatternMatching:
    """Tests for pattern matching functionality"""

    def test_loan_type_patterns(self):
        """Test loan type pattern extraction"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork

        nn = MortgageDataGatheringNeuralNetwork()

        # Check that loan_type_patterns exists
        assert hasattr(nn, 'loan_type_patterns')


class TestMortgageDataQuality:
    """Tests for data quality functionality"""

    def test_quality_score_for_complete_record(self):
        """Test quality score for a complete record"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork, MortgageDataPoint

        nn = MortgageDataGatheringNeuralNetwork()

        complete_record = MortgageDataPoint(
            property_id="PROP-COMPLETE",
            borrower_name="Complete User",
            lender_name="Complete Bank",
            loan_amount=500000.0,
            loan_type="Conventional",
            interest_rate=4.0,
            loan_term=30,
            loan_date="2024-06-01",
            property_address="123 Complete St, City, ST 12345",
            property_value=600000.0,
            status="active",
            data_source="verified_source",
            scraped_at=datetime.now().isoformat()
        )

        score = nn.get_data_quality_score(complete_record)

        # Complete records should have high quality score
        assert score >= 70

    def test_quality_score_for_incomplete_record(self):
        """Test quality score for an incomplete record"""
        from datagod.ml.mortgage_data_gathering_nn import MortgageDataGatheringNeuralNetwork, MortgageDataPoint

        nn = MortgageDataGatheringNeuralNetwork()

        # Use "Unknown" values since the scoring logic checks for "Unknown" string specifically
        incomplete_record = MortgageDataPoint(
            property_id="Unknown",  # Missing - 0 points
            borrower_name="Unknown",  # Missing - 0 points
            lender_name="Unknown",  # Missing - 0 points
            loan_amount=0.0,  # Invalid - 0 points
            loan_type="Unknown",  # Missing - 0 points
            interest_rate=0.0,  # Invalid
            loan_term=0,  # Invalid
            loan_date="Unknown",  # Missing - 0 points
            property_address="Unknown",  # Missing - 0 points
            property_value=0.0,  # Invalid
            status="unknown",
            data_source="unknown",
            scraped_at=datetime.now().isoformat()
        )

        score = nn.get_data_quality_score(incomplete_record)

        # Incomplete records with "Unknown" values should have score of 0
        assert score == 0
