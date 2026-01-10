#!/usr/bin/env python3
"""
Simple example usage of the Mortgage Data Gathering Neural Network
"""

import logging
from datagod.ml.mortgage import (
    MortgageDataGatheringNeuralNetwork,
    MortgageDataPoint
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Demonstrate the mortgage neural network usage"""
    
    logger.info("Starting Mortgage Neural Network Example")
    
    # Initialize the neural network
    nn = MortgageDataGatheringNeuralNetwork()
    
    # Create a sample data point
    sample_data_point = MortgageDataPoint(
        property_id="PROP-1001",
        borrower_name="John Smith",
        lender_name="Bank of America",
        loan_amount=350000.00,
        loan_type="Conventional",
        interest_rate=4.25,
        loan_term=30,
        loan_date="2023-05-15",
        property_address="123 Main St, Anytown, CA 12345",
        property_value=400000.00,
        status="active",
        data_source="test",
        scraped_at="2023-05-15T10:00:00Z"
    )
    
    # Validate the data point
    is_valid = nn.validate_mortgage_data(sample_data_point)
    logger.info(f"Data point validation: {'Valid' if is_valid else 'Invalid'}")
    
    # Extract data from sample text
    sample_text = """
    Property ID: PROP-1001
    Loan Amount: $350,000
    Interest Rate: 4.25%
    Loan Term: 30 years
    Property Address: 123 Main St, Anytown, CA 12345
    """
    
    logger.info("Extracting mortgage data...")
    extracted_data = nn.extract_mortgage_data(sample_text, "property_records")
    logger.info(f"Extracted {len(extracted_data)} records")
    
    # Show extracted data
    for record in extracted_data:
        logger.info(f"  - Property ID: {record.property_id}")
        logger.info(f"  - Loan Amount: ${record.loan_amount}")
        logger.info(f"  - Interest Rate: {record.interest_rate}%")
    
    # Test quality scoring
    if extracted_data:
        quality_score = nn.get_data_quality_score(extracted_data[0])
        logger.info(f"Data Quality Score: {quality_score}")
    
    logger.info("Example completed successfully!")

if __name__ == "__main__":
    main()
