"""Neural network model for mortgage data processing"""

import logging
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

from datagod.models import Entity, Record, Relationship
from datagod.models.entity import Entity
from datagod.models.record import Record
from datagod.models.relationship import Relationship

logger = logging.getLogger(__name__)


class MortgageDataDataset(Dataset):
    """Dataset for mortgage records"""

    def __init__(
        self,
        records: List[Record],
        entities: List[Entity],
        relationships: List[Relationship],
    ):
        self.records = records
        self.entities = entities
        self.relationships = relationships

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        # This is a placeholder implementation
        # In a real implementation, this would convert records to tensors
        # based on features like amount, date, jurisdiction, etc.
        record = self.records[idx]

        # Convert record data to tensor features
        # This is a simplified example - in practice, you'd extract meaningful features
        features = torch.tensor(
            [record.amount or 0.0, record.date.timestamp() if record.date else 0.0],
            dtype=torch.float32,
        )

        # Placeholder for target (would be based on the specific task)
        target = torch.tensor([0.0], dtype=torch.float32)

        return features, target


class MortgageNeuralNetwork(nn.Module):
    """Neural network for processing mortgage data"""

    def __init__(self, input_size: int, hidden_size: int = 128, num_classes: int = 2):
        super(MortgageNeuralNetwork, self).__init__()

        # Define the layers
        self.layer1 = nn.Linear(input_size, hidden_size)
        self.layer2 = nn.Linear(hidden_size, hidden_size)
        self.layer3 = nn.Linear(hidden_size, num_classes)

        # Dropout for regularization
        self.dropout = nn.Dropout(0.2)

        # Batch normalization
        self.bn1 = nn.BatchNorm1d(hidden_size)
        self.bn2 = nn.BatchNorm1d(hidden_size)

    def forward(self, x):
        # Forward pass through the network
        x = self.layer1(x)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout(x)

        x = self.layer2(x)
        x = self.bn2(x)
        x = F.relu(x)
        x = self.dropout(x)

        x = self.layer3(x)

        # Apply sigmoid for binary classification
        # Or use softmax for multi-class classification
        return torch.sigmoid(x)


class MortgageDataProcessor:
    """Main processor for mortgage data using neural network"""

    def __init__(
        self, input_size: int = 2, hidden_size: int = 128, num_classes: int = 2
    ):
        self.model = MortgageNeuralNetwork(input_size, hidden_size, num_classes)
        # Force CPU in test mode to avoid CUDA OOM errors
        if os.environ.get("TESTING") == "1":
            self.device = torch.device("cpu")
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        # Initialize loss function and optimizer
        self.criterion = nn.BCELoss()  # Binary Cross Entropy Loss
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)

        logger.info(f"Using device: {self.device}")

    def prepare_data(
        self,
        records: List[Record],
        entities: List[Entity],
        relationships: List[Relationship],
    ) -> Tuple[DataLoader, DataLoader]:
        """Prepare data for training and validation"""
        # Create dataset
        dataset = MortgageDataDataset(records, entities, relationships)

        # Split into train and validation sets (80/20 split)
        train_size = int(0.8 * len(dataset))
        val_size = len(dataset) - train_size
        train_dataset, val_dataset = torch.utils.data.random_split(
            dataset, [train_size, val_size]
        )

        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

        return train_loader, val_loader

    def train(self, train_loader: DataLoader, val_loader: DataLoader, epochs: int = 10):
        """Train the neural network"""
        self.model.train()

        for epoch in range(epochs):
            running_loss = 0.0
            correct = 0
            total = 0

            for batch_idx, (data, target) in enumerate(train_loader):
                # Move data to device
                data, target = data.to(self.device), target.to(self.device)

                # Zero the gradients
                self.optimizer.zero_grad()

                # Forward pass
                outputs = self.model(data)

                # Calculate loss
                loss = self.criterion(outputs, target)

                # Backward pass
                loss.backward()

                # Update weights
                self.optimizer.step()

                # Statistics
                running_loss += loss.item()
                predicted = (outputs > 0.5).float()
                total += target.size(0)
                correct += (predicted == target).sum().item()

                if batch_idx % 100 == 0:
                    logger.info(
                        f"Epoch [{epoch+1}/{epochs}], Batch [{batch_idx}/{len(train_loader)}], Loss: {loss.item():.4f}"
                    )

            # Validation
            val_loss, val_accuracy = self.validate(val_loader)
            logger.info(
                f"Epoch [{epoch+1}/{epochs}], Train Loss: {running_loss/len(train_loader):.4f}, "
                f"Train Accuracy: {100.*correct/total:.2f}%, Val Loss: {val_loss:.4f}, "
                f"Val Accuracy: {100.*val_accuracy:.2f}%"
            )

    def validate(self, val_loader: DataLoader) -> Tuple[float, float]:
        """Validate the neural network"""
        self.model.eval()
        val_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for data, target in val_loader:
                data, target = data.to(self.device), target.to(self.device)
                outputs = self.model(data)
                loss = self.criterion(outputs, target)
                val_loss += loss.item()

                predicted = (outputs > 0.5).float()
                total += target.size(0)
                correct += (predicted == target).sum().item()

        return val_loss / len(val_loader), correct / total

    def predict(self, data: torch.Tensor) -> torch.Tensor:
        """Make predictions with the neural network"""
        self.model.eval()
        with torch.no_grad():
            data = data.to(self.device)
            outputs = self.model(data)
            return outputs
