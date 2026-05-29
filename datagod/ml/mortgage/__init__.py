"""
Mortgage Data Gathering Neural Network Package
"""

from .config import MORTGAGE_NN_CONFIG
from .integration import MortgageNeuralNetworkIntegration
from .neural_network import MortgageDataGatheringNeuralNetwork, MortgageDataPoint

__all__ = [
    "MortgageDataGatheringNeuralNetwork",
    "MortgageDataPoint",
    "MORTGAGE_NN_CONFIG",
    "MortgageNeuralNetworkIntegration",
]

# Package metadata
__version__ = "0.1.0"
__author__ = "DataGod Team"
__email__ = "datagod@example.com"
__description__ = "Neural network for gathering mortgage data"
