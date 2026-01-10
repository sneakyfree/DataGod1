# Mortgage Data Gathering Neural Network

This module implements a neural network approach for gathering and processing mortgage data from various sources.

## Overview

The Mortgage Data Gathering Neural Network is designed to extract, validate, and process mortgage-related information from diverse data sources including property records, court records, and government APIs. It uses pattern matching and rule-based approaches to simulate neural network behavior for data extraction and processing.

## Key Features

- **Multi-source Data Extraction**: Supports property records, court records, and government APIs
- **Data Validation**: Validates extracted data for reasonableness
- **Quality Scoring**: Assigns quality scores to extracted data points
- **Learning Capability**: Can learn from training data to improve future extractions
- **Integration Layer**: Seamlessly integrates with the main application's database and entity relationship models

## Architecture

### Core Components

1. **MortgageDataPoint**: Data class representing a single mortgage record
2. **MortgageDataGatheringNeuralNetwork**: Main neural network implementation for data extraction
3. **MortgageNeuralNetworkIntegration**: Integration layer with database and application logic

## Usage Examples

### Basic Usage

```python
from datagod.ml.mortgage import MortgageDataGatheringNeuralNetwork

# Initialize the neural network
nn = MortgageDataGatheringNeuralNetwork()

# Extract data from different sources
raw_data = """
Property ID: PROP-1001
Borrower: John Smith
Lender: Bank of America
Loan Amount: $350,000
"""

extracted_data = nn.extract_mortgage_data(raw_data, "property_records")
```

### Processing with Quality Scoring

```python
from datagod.ml.mortgage import MortgageDataGatheringNeuralNetwork

nn = MortgageDataGatheringNeuralNetwork()
extracted_data = nn.extract_mortgage_data(raw_data, "property_records")

# Filter by quality score
filtered_data = []
for data_point in extracted_data:
    quality_score = nn.get_data_quality_score(data_point)
    if quality_score >= 70:  # Only keep high quality data
        data_point.quality_score = quality_score
        filtered_data.append(data_point)
```

### Training the Network

```python
from datagod.ml.mortgage import MortgageNeuralNetworkIntegration

integration = MortgageNeuralNetworkIntegration()

# Training data in dictionary format
training_data = [
    {
        "property_id": "PROP-1001",
        "borrower_name": "John Smith",
        "lender_name": "Bank of America",
        "loan_amount": 350000.00,
        "loan_type": "Conventional",
        "interest_rate": 4.25,
        "loan_term": 30,
        "loan_date": "2023-05-15",
        "property_address": "123 Main St, Anytown, CA 12345",
        "property_value": 400000.00,
        "status": "active",
        "data_source": "property_records",
        "scraped_at": "2023-05-15T10:00:00Z"
    }
]

# Train the neural network
integration.train_neural_network(training_data)
```

## Data Sources Supported

1. **Property Records**: Extracts data from property ownership and mortgage records
2. **Court Records**: Processes foreclosure and legal judgment information
3. **Government APIs**: Handles structured data from government sources
4. **Generic Sources**: Pattern matching for unstructured data

## Quality Metrics

The system provides quality scoring for extracted data points:
- **Completeness**: Percentage of required fields filled
- **Consistency**: Internal consistency checks
- **Reasonableness**: Checks against expected ranges

## Integration with Database

The integration layer handles:
- Storing processed data in the database
- Creating entity relationships (borrowers, lenders, properties)
- Generating quality reports
- Managing data validation and filtering

## Configuration

The neural network can be configured through `datagod/ml/mortgage/config.py`:
- `min_data_quality_score`: Minimum quality score for data to be accepted
- `extraction_patterns`: Custom patterns for different data types

## Testing

Run tests with:
```bash
python -m pytest datagod/tests/test_mortgage_nn.py
```

## Example Usage

See `datagod/examples/mortgage_nn_detailed_example.py` for comprehensive usage examples.
