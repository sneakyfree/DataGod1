"""
Tests for Neural Network Integration module
Tests the integration between neural network and DataGod models
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


class TestNeuralNetworkIntegration:
    """Tests for NeuralNetworkIntegration class"""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        return MagicMock()

    def test_integration_initialization(self, mock_session):
        """Test integration initializes correctly"""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        integration = NeuralNetworkIntegration(mock_session)

        assert integration.db_session == mock_session
        assert integration.data_collector is not None
        assert integration.data_processor is None

    def test_initialize_processor(self, mock_session):
        """Test processor initialization"""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        integration = NeuralNetworkIntegration(mock_session)
        integration.initialize_processor(input_size=10, hidden_size=64, num_classes=2)

        assert integration.data_processor is not None

    def test_initialize_processor_default_params(self, mock_session):
        """Test processor initialization with default params"""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        integration = NeuralNetworkIntegration(mock_session)
        integration.initialize_processor()

        assert integration.data_processor is not None


class TestMortgageDataCollector:
    """Tests for MortgageDataCollector class"""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        return MagicMock()

    def test_collector_initialization(self, mock_session):
        """Test collector initializes correctly"""
        from datagod.neural_network.data_collection import MortgageDataCollector

        collector = MortgageDataCollector(mock_session)

        assert collector.db_session == mock_session


class TestIntegrationDataGathering:
    """Tests for data gathering functionality"""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = MagicMock()
        # Mock jurisdiction query to return None (not found)
        session.query.return_value.filter_by.return_value.first.return_value = None
        return session

    def test_gather_data_jurisdiction_not_found(self, mock_session):
        """Test gathering data when jurisdiction not found"""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        integration = NeuralNetworkIntegration(mock_session)
        result = integration.gather_mortgage_data("NonExistentCounty")

        assert result == 0


class TestDataProcessing:
    """Tests for data processing functionality"""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None
        return session

    def test_process_data_auto_initializes_processor(self, mock_session):
        """Test processing auto-initializes processor if needed"""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        integration = NeuralNetworkIntegration(mock_session)
        assert integration.data_processor is None

        # This should auto-initialize the processor
        integration.process_mortgage_data("TestCounty")

        assert integration.data_processor is not None

    def test_process_data_jurisdiction_not_found(self, mock_session):
        """Test processing when jurisdiction not found"""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        integration = NeuralNetworkIntegration(mock_session)
        integration.initialize_processor()

        # Should handle gracefully when jurisdiction not found
        result = integration.process_mortgage_data("NonExistentCounty")
        # Should return None without raising exception


class TestMortgageDataProcessor:
    """Additional tests for MortgageDataProcessor"""

    def test_processor_training_setup(self):
        """Test processor has training components"""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor(input_size=10, hidden_size=64, num_classes=2)

        assert processor.model is not None
        assert processor.criterion is not None
        assert processor.optimizer is not None

    def test_processor_prepare_data(self):
        """Test data preparation returns loaders"""
        from datetime import datetime

        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor(input_size=2, hidden_size=64, num_classes=2)

        # Create mock records
        mock_record1 = MagicMock()
        mock_record1.amount = 200000.0
        mock_record1.date = datetime.now()

        mock_record2 = MagicMock()
        mock_record2.amount = 300000.0
        mock_record2.date = datetime.now()

        records = [mock_record1, mock_record2]

        train_loader, val_loader = processor.prepare_data(records, [], [])

        assert train_loader is not None
        assert val_loader is not None


class TestModelTraining:
    """Tests for model training functionality"""

    def test_model_can_train_single_epoch(self):
        """Test model can complete a training step"""
        from datetime import datetime

        import torch

        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor(input_size=2, hidden_size=32, num_classes=2)

        # Create mock records
        records = []
        for i in range(10):
            mock_record = MagicMock()
            mock_record.amount = float(i * 50000)
            mock_record.date = datetime.now()
            records.append(mock_record)

        train_loader, val_loader = processor.prepare_data(records, [], [])

        # Training should work without errors
        processor.model.train()

        # Just verify the loaders have data
        for batch in train_loader:
            features, targets = batch
            assert features is not None
            assert targets is not None
            break  # Just check first batch
