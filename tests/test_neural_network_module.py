"""
Tests for datagod/neural_network module.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import torch


class TestMortgageDataCollector:
    """Tests for the MortgageDataCollector class."""

    def test_collector_creation(self):
        """Test collector can be created."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()
        collector = MortgageDataCollector(mock_session)
        assert collector is not None
        assert collector.db_session == mock_session

    def test_collect_from_api(self):
        """Test collecting data from API."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()
        collector = MortgageDataCollector(mock_session)

        mock_data_source = MagicMock()
        mock_data_source.api_endpoint = "https://example.com/api"
        mock_data_source.name = "Test API"

        result = collector.collect_from_api(mock_data_source)
        assert isinstance(result, list)

    def test_collect_from_api_exception(self):
        """Test collecting from API with exception."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()
        collector = MortgageDataCollector(mock_session)

        mock_data_source = MagicMock()
        mock_data_source.api_endpoint = None  # Will cause issues
        mock_data_source.name = "Bad API"

        result = collector.collect_from_api(mock_data_source)
        assert isinstance(result, list)

    def test_collect_from_scraper(self):
        """Test collecting data from scraper."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()
        collector = MortgageDataCollector(mock_session)

        mock_data_source = MagicMock()
        mock_data_source.url = "https://example.com"
        mock_data_source.name = "Test Scraper"

        result = collector.collect_from_scraper(mock_data_source)
        assert isinstance(result, list)

    def test_collect_from_scraper_exception(self):
        """Test collecting from scraper with exception."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()
        collector = MortgageDataCollector(mock_session)

        mock_data_source = MagicMock()
        mock_data_source.url = None
        mock_data_source.name = "Bad Scraper"

        result = collector.collect_from_scraper(mock_data_source)
        assert isinstance(result, list)

    def test_collect_from_manual(self):
        """Test collecting data from manual input."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()
        collector = MortgageDataCollector(mock_session)

        mock_data_source = MagicMock()
        mock_data_source.name = "Manual Input"

        result = collector.collect_from_manual(mock_data_source)
        assert isinstance(result, list)

    def test_collect_from_manual_exception(self):
        """Test collecting from manual with exception."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()
        collector = MortgageDataCollector(mock_session)

        mock_data_source = MagicMock()
        mock_data_source.name = None  # Will cause issues

        result = collector.collect_from_manual(mock_data_source)
        assert isinstance(result, list)

    def test_collect_mortgage_data_no_data_sources(self):
        """Test collecting mortgage data with no data sources."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter_by.return_value.all.return_value = []
        mock_session.query.return_value = mock_query

        collector = MortgageDataCollector(mock_session)

        mock_jurisdiction = MagicMock()
        mock_jurisdiction.id = 1

        result = collector.collect_mortgage_data(mock_jurisdiction)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_collect_mortgage_data_with_api_source(self):
        """Test collecting mortgage data with API source."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()

        mock_data_source = MagicMock()
        mock_data_source.source_type = 'api'
        mock_data_source.api_endpoint = "https://example.com/api"
        mock_data_source.name = "API Source"

        mock_query = MagicMock()
        mock_query.filter_by.return_value.all.return_value = [mock_data_source]
        mock_session.query.return_value = mock_query

        collector = MortgageDataCollector(mock_session)

        mock_jurisdiction = MagicMock()
        mock_jurisdiction.id = 1

        result = collector.collect_mortgage_data(mock_jurisdiction)
        assert isinstance(result, list)

    def test_collect_mortgage_data_with_scraper_source(self):
        """Test collecting mortgage data with scraper source."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()

        mock_data_source = MagicMock()
        mock_data_source.source_type = 'scraper'
        mock_data_source.url = "https://example.com"
        mock_data_source.name = "Scraper Source"

        mock_query = MagicMock()
        mock_query.filter_by.return_value.all.return_value = [mock_data_source]
        mock_session.query.return_value = mock_query

        collector = MortgageDataCollector(mock_session)

        mock_jurisdiction = MagicMock()
        mock_jurisdiction.id = 1

        result = collector.collect_mortgage_data(mock_jurisdiction)
        assert isinstance(result, list)

    def test_collect_mortgage_data_with_manual_source(self):
        """Test collecting mortgage data with manual source."""
        from datagod.neural_network.data_collection import MortgageDataCollector

        mock_session = MagicMock()

        mock_data_source = MagicMock()
        mock_data_source.source_type = 'manual'
        mock_data_source.name = "Manual Source"

        mock_query = MagicMock()
        mock_query.filter_by.return_value.all.return_value = [mock_data_source]
        mock_session.query.return_value = mock_query

        collector = MortgageDataCollector(mock_session)

        mock_jurisdiction = MagicMock()
        mock_jurisdiction.id = 1

        result = collector.collect_mortgage_data(mock_jurisdiction)
        assert isinstance(result, list)


class TestNeuralNetworkIntegration:
    """Tests for the NeuralNetworkIntegration class."""

    def test_integration_creation(self):
        """Test integration can be created."""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        mock_session = MagicMock()
        integration = NeuralNetworkIntegration(mock_session)
        assert integration is not None
        assert integration.db_session == mock_session
        assert integration.data_collector is not None
        assert integration.data_processor is None

    def test_initialize_processor(self):
        """Test initializing the processor."""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        mock_session = MagicMock()
        integration = NeuralNetworkIntegration(mock_session)

        integration.initialize_processor(input_size=4, hidden_size=64, num_classes=3)
        assert integration.data_processor is not None

    def test_initialize_processor_default_params(self):
        """Test initializing the processor with default parameters."""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        mock_session = MagicMock()
        integration = NeuralNetworkIntegration(mock_session)

        integration.initialize_processor()
        assert integration.data_processor is not None

    def test_gather_mortgage_data_jurisdiction_not_found(self):
        """Test gathering mortgage data when jurisdiction is not found."""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        integration = NeuralNetworkIntegration(mock_session)

        result = integration.gather_mortgage_data("NonExistentCounty")
        assert result == 0

    def test_gather_mortgage_data_with_jurisdiction(self):
        """Test gathering mortgage data with valid jurisdiction."""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        mock_session = MagicMock()
        mock_jurisdiction = MagicMock()
        mock_jurisdiction.id = 1
        mock_jurisdiction.name = "Test County"

        # First query returns jurisdiction, second returns empty data sources
        def mock_query_side_effect(model):
            query = MagicMock()
            if hasattr(model, '__name__') and model.__name__ == 'Jurisdiction':
                query.filter_by.return_value.first.return_value = mock_jurisdiction
            else:
                query.filter_by.return_value.all.return_value = []
            return query

        mock_session.query.side_effect = mock_query_side_effect

        integration = NeuralNetworkIntegration(mock_session)

        result = integration.gather_mortgage_data("Test County")
        assert result == 0  # No records collected since no data sources

    def test_gather_mortgage_data_exception(self):
        """Test gathering mortgage data with exception."""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        mock_session = MagicMock()
        mock_session.query.side_effect = Exception("Database error")
        mock_session.rollback = MagicMock()

        integration = NeuralNetworkIntegration(mock_session)

        result = integration.gather_mortgage_data("Test County")
        assert result == 0
        mock_session.rollback.assert_called_once()

    def test_process_mortgage_data_no_processor(self):
        """Test processing mortgage data initializes processor if not set."""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        integration = NeuralNetworkIntegration(mock_session)
        assert integration.data_processor is None

        # This should initialize processor and handle missing jurisdiction
        integration.process_mortgage_data("NonExistent")
        assert integration.data_processor is not None

    def test_process_mortgage_data_jurisdiction_not_found(self):
        """Test processing when jurisdiction not found."""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        integration = NeuralNetworkIntegration(mock_session)
        integration.initialize_processor()

        # Should return without error
        result = integration.process_mortgage_data("NonExistent")
        assert result is None

    def test_extract_entities_and_relationships_empty(self):
        """Test extracting entities and relationships from empty records."""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        mock_session = MagicMock()
        integration = NeuralNetworkIntegration(mock_session)

        entities, relationships = integration.extract_entities_and_relationships([])
        assert entities == []
        assert relationships == []

    def test_extract_entities_and_relationships_with_records(self):
        """Test extracting entities and relationships from records."""
        from datagod.neural_network.integration import NeuralNetworkIntegration

        mock_session = MagicMock()
        integration = NeuralNetworkIntegration(mock_session)

        mock_records = [MagicMock(), MagicMock(), MagicMock()]

        entities, relationships = integration.extract_entities_and_relationships(mock_records)
        assert isinstance(entities, list)
        assert isinstance(relationships, list)


class TestMortgageDataDataset:
    """Tests for the MortgageDataDataset class."""

    def test_dataset_creation(self):
        """Test dataset can be created."""
        from datagod.neural_network.model import MortgageDataDataset

        mock_records = []
        mock_entities = []
        mock_relationships = []

        dataset = MortgageDataDataset(mock_records, mock_entities, mock_relationships)
        assert dataset is not None
        assert len(dataset) == 0

    def test_dataset_length(self):
        """Test dataset length."""
        from datagod.neural_network.model import MortgageDataDataset

        mock_records = [MagicMock() for _ in range(5)]
        mock_entities = []
        mock_relationships = []

        dataset = MortgageDataDataset(mock_records, mock_entities, mock_relationships)
        assert len(dataset) == 5

    def test_dataset_getitem(self):
        """Test getting item from dataset."""
        from datagod.neural_network.model import MortgageDataDataset

        mock_record = MagicMock()
        mock_record.amount = 100000.0
        mock_record.date = datetime(2023, 1, 15)

        dataset = MortgageDataDataset([mock_record], [], [])

        features, target = dataset[0]
        assert isinstance(features, torch.Tensor)
        assert isinstance(target, torch.Tensor)
        assert features.shape == (2,)

    def test_dataset_getitem_none_values(self):
        """Test getting item with None values."""
        from datagod.neural_network.model import MortgageDataDataset

        mock_record = MagicMock()
        mock_record.amount = None
        mock_record.date = None

        dataset = MortgageDataDataset([mock_record], [], [])

        features, target = dataset[0]
        assert isinstance(features, torch.Tensor)
        assert features[0].item() == 0.0
        assert features[1].item() == 0.0


class TestMortgageNeuralNetwork:
    """Tests for the MortgageNeuralNetwork class."""

    def test_network_creation(self):
        """Test neural network can be created."""
        from datagod.neural_network.model import MortgageNeuralNetwork

        nn = MortgageNeuralNetwork(input_size=2, hidden_size=64, num_classes=2)
        assert nn is not None

    def test_network_creation_custom_params(self):
        """Test neural network with custom parameters."""
        from datagod.neural_network.model import MortgageNeuralNetwork

        nn = MortgageNeuralNetwork(input_size=10, hidden_size=256, num_classes=5)
        assert nn is not None

    def test_network_forward_pass(self):
        """Test forward pass through network."""
        from datagod.neural_network.model import MortgageNeuralNetwork

        nn = MortgageNeuralNetwork(input_size=2, hidden_size=64, num_classes=2)
        nn.eval()  # Set to eval mode for consistent behavior

        # Create batch of inputs
        input_tensor = torch.randn(4, 2)  # Batch of 4, 2 features each

        output = nn(input_tensor)
        assert output.shape == (4, 2)
        # Output should be between 0 and 1 (sigmoid)
        assert (output >= 0).all() and (output <= 1).all()

    def test_network_forward_pass_single(self):
        """Test forward pass with single sample."""
        from datagod.neural_network.model import MortgageNeuralNetwork

        nn = MortgageNeuralNetwork(input_size=4, hidden_size=32, num_classes=3)
        nn.eval()

        input_tensor = torch.randn(1, 4)
        output = nn(input_tensor)
        assert output.shape == (1, 3)


class TestMortgageDataProcessor:
    """Tests for the MortgageDataProcessor class."""

    def test_processor_creation(self):
        """Test processor can be created."""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor()
        assert processor is not None
        assert processor.model is not None

    def test_processor_creation_custom_params(self):
        """Test processor with custom parameters."""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor(input_size=5, hidden_size=256, num_classes=4)
        assert processor is not None

    def test_processor_prepare_data_empty(self):
        """Test preparing data with empty inputs raises ValueError."""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor()

        # Empty lists raise ValueError due to random sampler needing positive samples
        with pytest.raises(ValueError):
            processor.prepare_data([], [], [])

    def test_processor_prepare_data(self):
        """Test preparing data with records."""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor()

        # Create mock records
        mock_records = []
        for i in range(10):
            record = MagicMock()
            record.amount = float(i * 10000)
            record.date = datetime(2023, 1, i + 1)
            mock_records.append(record)

        train_loader, val_loader = processor.prepare_data(mock_records, [], [])
        assert train_loader is not None
        assert val_loader is not None

    def test_processor_predict(self):
        """Test making predictions."""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor(input_size=2, hidden_size=64, num_classes=2)

        input_tensor = torch.randn(4, 2)
        output = processor.predict(input_tensor)

        assert output.shape == (4, 2)

    def test_processor_validate(self):
        """Test validation."""
        from datagod.neural_network.model import MortgageDataProcessor, MortgageDataDataset
        from torch.utils.data import DataLoader

        processor = MortgageDataProcessor(input_size=2, hidden_size=64, num_classes=1)

        # Create minimal dataset with actual records
        mock_records = []
        for i in range(4):
            record = MagicMock()
            record.amount = float(i * 10000)
            record.date = datetime(2023, 1, i + 1)
            mock_records.append(record)

        dataset = MortgageDataDataset(mock_records, [], [])
        val_loader = DataLoader(dataset, batch_size=2)

        val_loss, val_accuracy = processor.validate(val_loader)
        assert isinstance(val_loss, float)
        assert isinstance(val_accuracy, float)
        assert 0 <= val_accuracy <= 1


class TestMortgageNeuralNetworkTraining:
    """Tests for neural network training functionality."""

    def test_train_single_epoch(self):
        """Test training for a single epoch."""
        from datagod.neural_network.model import MortgageDataProcessor, MortgageDataDataset
        from torch.utils.data import DataLoader

        processor = MortgageDataProcessor(input_size=2, hidden_size=32, num_classes=1)

        # Create minimal dataset
        mock_records = []
        for i in range(8):
            record = MagicMock()
            record.amount = float(i * 10000)
            record.date = datetime(2023, 1, (i % 28) + 1)
            mock_records.append(record)

        dataset = MortgageDataDataset(mock_records, [], [])
        train_loader = DataLoader(dataset, batch_size=2)
        val_loader = DataLoader(dataset, batch_size=2)

        # Train for 1 epoch
        processor.train(train_loader, val_loader, epochs=1)
        # If we get here without error, training worked


class TestMortgageDataProcessorDevice:
    """Tests for device handling in MortgageDataProcessor."""

    def test_processor_device_selection(self):
        """Test that processor selects appropriate device."""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor()
        # Should either be 'cuda' or 'cpu'
        assert processor.device.type in ['cuda', 'cpu']

    def test_model_on_device(self):
        """Test that model is moved to device."""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor()
        # Model parameters should be on the same device
        for param in processor.model.parameters():
            assert param.device.type == processor.device.type
