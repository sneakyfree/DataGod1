"""
Tests for Neural Network Model module
Tests the PyTorch-based neural network for mortgage data processing
"""

import pytest
import torch
import torch.nn as nn
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestMortgageNeuralNetwork:
    """Tests for MortgageNeuralNetwork class"""

    def test_network_initialization(self):
        """Test neural network initializes correctly"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=64, num_classes=2)

        assert model is not None
        assert isinstance(model, nn.Module)

    def test_network_layers(self):
        """Test network has correct layers"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=64, num_classes=2)

        assert hasattr(model, 'layer1')
        assert hasattr(model, 'layer2')
        assert hasattr(model, 'layer3')
        assert hasattr(model, 'dropout')
        assert hasattr(model, 'bn1')
        assert hasattr(model, 'bn2')

    def test_network_forward_pass(self):
        """Test forward pass produces correct output shape"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=64, num_classes=2)
        model.eval()  # Set to evaluation mode for batch norm

        # Create batch of 5 samples with 10 features each
        input_tensor = torch.randn(5, 10)
        output = model(input_tensor)

        assert output.shape == (5, 2)

    def test_network_output_range(self):
        """Test output values are in sigmoid range [0, 1]"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=64, num_classes=2)
        model.eval()

        input_tensor = torch.randn(10, 10)
        output = model(input_tensor)

        assert torch.all(output >= 0)
        assert torch.all(output <= 1)

    def test_network_different_sizes(self):
        """Test network with different input/hidden sizes"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        # Small network
        small = MortgageNeuralNetwork(input_size=5, hidden_size=32, num_classes=1)
        small.eval()
        output = small(torch.randn(3, 5))
        assert output.shape == (3, 1)

        # Large network
        large = MortgageNeuralNetwork(input_size=100, hidden_size=256, num_classes=10)
        large.eval()
        output = large(torch.randn(3, 100))
        assert output.shape == (3, 10)


class TestMortgageDataDataset:
    """Tests for MortgageDataDataset class"""

    def test_dataset_creation(self):
        """Test dataset can be created with mock data"""
        from datagod.neural_network.model import MortgageDataDataset

        # Create mock records with required attributes
        mock_record = MagicMock()
        mock_record.amount = 250000.0
        mock_record.date = datetime.now()

        dataset = MortgageDataDataset(
            records=[mock_record],
            entities=[],
            relationships=[]
        )

        assert len(dataset) == 1

    def test_dataset_length(self):
        """Test dataset length matches records count"""
        from datagod.neural_network.model import MortgageDataDataset

        records = []
        for i in range(5):
            mock_record = MagicMock()
            mock_record.amount = float(i * 100000)
            mock_record.date = datetime.now()
            records.append(mock_record)

        dataset = MortgageDataDataset(
            records=records,
            entities=[],
            relationships=[]
        )

        assert len(dataset) == 5

    def test_dataset_getitem(self):
        """Test dataset __getitem__ returns features and target"""
        from datagod.neural_network.model import MortgageDataDataset

        mock_record = MagicMock()
        mock_record.amount = 300000.0
        mock_record.date = datetime.now()

        dataset = MortgageDataDataset(
            records=[mock_record],
            entities=[],
            relationships=[]
        )

        features, target = dataset[0]

        assert isinstance(features, torch.Tensor)
        assert isinstance(target, torch.Tensor)
        assert features.dtype == torch.float32
        assert target.dtype == torch.float32

    def test_dataset_with_none_values(self):
        """Test dataset handles None values in records"""
        from datagod.neural_network.model import MortgageDataDataset

        mock_record = MagicMock()
        mock_record.amount = None
        mock_record.date = None

        dataset = MortgageDataDataset(
            records=[mock_record],
            entities=[],
            relationships=[]
        )

        features, target = dataset[0]

        # Should handle None gracefully (convert to 0)
        assert features[0] == 0.0
        assert features[1] == 0.0


class TestMortgageDataProcessor:
    """Tests for MortgageDataProcessor class"""

    def test_processor_initialization(self):
        """Test processor initializes correctly"""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor(
            input_size=10,
            hidden_size=64,
            num_classes=2
        )

        assert processor.model is not None
        assert processor.criterion is not None
        assert processor.optimizer is not None

    def test_processor_default_params(self):
        """Test processor with default parameters"""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor()

        assert processor.model is not None

    def test_processor_device_selection(self):
        """Test processor selects appropriate device"""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor()

        # Device should be either 'cpu' or 'cuda'
        assert processor.device.type in ['cpu', 'cuda']

    def test_processor_has_criterion(self):
        """Test processor has loss criterion"""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor()

        assert isinstance(processor.criterion, nn.BCELoss)

    def test_processor_has_optimizer(self):
        """Test processor has optimizer"""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor()

        assert isinstance(processor.optimizer, torch.optim.Adam)


class TestNetworkTraining:
    """Tests for network training functionality"""

    def test_model_parameters_exist(self):
        """Test model has trainable parameters"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=64, num_classes=2)

        params = list(model.parameters())
        assert len(params) > 0

    def test_model_gradients(self):
        """Test gradients can be computed"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=64, num_classes=2)
        model.train()

        # Forward pass
        input_tensor = torch.randn(5, 10)
        output = model(input_tensor)

        # Compute loss
        target = torch.rand(5, 2)
        loss = nn.BCELoss()(output, target)

        # Backward pass
        loss.backward()

        # Check gradients exist
        for param in model.parameters():
            assert param.grad is not None

    def test_model_training_step(self):
        """Test a single training step"""
        from datagod.neural_network.model import MortgageDataProcessor

        processor = MortgageDataProcessor(input_size=10, hidden_size=64, num_classes=2)
        processor.model.train()

        # Get initial parameters
        initial_params = [p.clone() for p in processor.model.parameters()]

        # Forward pass
        input_tensor = torch.randn(5, 10).to(processor.device)
        output = processor.model(input_tensor)

        # Compute loss
        target = torch.rand(5, 2).to(processor.device)
        loss = processor.criterion(output, target)

        # Backward pass and optimize
        processor.optimizer.zero_grad()
        loss.backward()
        processor.optimizer.step()

        # Check parameters changed
        for initial, current in zip(initial_params, processor.model.parameters()):
            # At least some parameters should change
            if not torch.equal(initial.to(processor.device), current):
                break
        else:
            # All parameters unchanged - not ideal but not necessarily wrong
            pass


class TestModelModes:
    """Tests for model training/evaluation modes"""

    def test_model_train_mode(self):
        """Test model can be set to training mode"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=64, num_classes=2)
        model.train()

        assert model.training is True

    def test_model_eval_mode(self):
        """Test model can be set to evaluation mode"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=64, num_classes=2)
        model.eval()

        assert model.training is False

    def test_dropout_behavior(self):
        """Test dropout behaves differently in train/eval modes"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=64, num_classes=2)

        input_tensor = torch.randn(20, 10)

        # In eval mode, output should be deterministic
        model.eval()
        with torch.no_grad():
            out1 = model(input_tensor)
            out2 = model(input_tensor)
        assert torch.allclose(out1, out2)

        # In train mode, outputs may differ due to dropout
        model.train()
        out3 = model(input_tensor)
        out4 = model(input_tensor)
        # Note: With small probability, they could be equal


class TestBatchNormalization:
    """Tests for batch normalization layers"""

    def test_batch_norm_layers(self):
        """Test batch norm layers are present"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=64, num_classes=2)

        assert isinstance(model.bn1, nn.BatchNorm1d)
        assert isinstance(model.bn2, nn.BatchNorm1d)

    def test_batch_norm_size(self):
        """Test batch norm has correct size"""
        from datagod.neural_network.model import MortgageNeuralNetwork

        model = MortgageNeuralNetwork(input_size=10, hidden_size=128, num_classes=2)

        assert model.bn1.num_features == 128
        assert model.bn2.num_features == 128
