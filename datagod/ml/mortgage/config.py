"""
Configuration for Mortgage Data Gathering Neural Network
"""

from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class MortgageNeuralNetworkConfig:
    """Configuration for the mortgage neural network"""
    
    # Neural network parameters
    learning_rate: float = 0.01
    max_iterations: int = 1000
    tolerance: float = 0.001
    
    # Data processing parameters
    min_data_quality_score: float = 70.0
    max_data_points_per_batch: int = 1000
    
    # Pattern matching parameters
    pattern_match_threshold: float = 0.7
    confidence_threshold: float = 0.8
    
    # Data sources
    supported_sources: List[str] = None
    default_source: str = "generic"
    
    # Validation parameters
    required_fields: List[str] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.supported_sources is None:
            self.supported_sources = [
                "property_records",
                "court_records", 
                "government_api",
                "generic"
            ]
        
        if self.required_fields is None:
            self.required_fields = [
                "property_id",
                "loan_amount",
                "loan_term"
            ]

# Global configuration instance
MORTGAGE_NN_CONFIG = MortgageNeuralNetworkConfig()
