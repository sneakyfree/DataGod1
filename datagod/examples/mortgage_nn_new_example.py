#!/usr/bin/env python3
"""
Example usage of the new Mortgage Data Gathering Neural Network
This example demonstrates all features of the new neural network implementation
"""

import logging
from datetime import datetime
from datagod.ml.mortgage_data_gathering_nn import (
    MortgageDataGatheringNeuralNetwork,
    MortgageDataPoint
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Demonstrate the new mortgage neural network usage"""
    
    logger.info("Starting New Mortgage Neural Network Example")
    
    # Initialize the neural network
    nn = MortgageDataGatheringNeuralNetwork()
    
    # Create sample data for demonstration
    sample_property_records = """
    Property ID: PROP-1001
    Borrower: John Smith
    Lender: Bank of America
    Loan Amount: $350,000
    Interest Rate: 4.25%
    Loan Term: 30 years
    Property Address: 123 Main St, Anytown, CA 12345
    Property Value: $400,000
    Loan Date: 2023-05-15
    Status: Active
    Loan Type: Conventional
    """
    
    sample_court_records = """
    Court Order: 123456789
    Judgment Amount: $275,000
    Foreclosure Process
    Property Address: 456 Oak Ave, Somewhere, TX 67890
    Borrower: Jane Doe
    Lender: Chase Bank
    """
    
    sample_government_api = """
    {
        "loan_info": {
            "property_id": "PROP-2001",
            "borrower_name": "Jane Doe",
            "lender_name": "Chase Bank",
            "loan_amount": 450000.0,
            "loan_type": "Conventional",
            "interest_rate": 3.75,
            "loan_term": 30,
            "loan_date": "2023-06-20",
            "status": "active"
        },
        "property_info": {
            "address": "789 Pine St, Elsewhere, NY 54321",
            "property_value": 500000.0
        }
    }
    """
    
    # Test extraction from different sources
    logger.info("=== Testing Property Records Extraction ===")
    extracted_property_data = nn.extract_mortgage_data(sample_property_records, "property_records")
    logger.info(f"Extracted {len(extracted_property_data)} records from property records")
    
    for i, record in enumerate(extracted_property_data):
        logger.info(f"  Record {i+1}:")
        logger.info(f"    Property ID: {record.property_id}")
        logger.info(f"    Borrower: {record.borrower_name}")
        logger.info(f"    Lender: {record.lender_name}")
        logger.info(f"    Loan Amount: ${record.loan_amount:,.2f}")
        logger.info(f"    Interest Rate: {record.interest_rate}%")
        logger.info(f"    Loan Term: {record.loan_term} years")
        logger.info(f"    Property Address: {record.property_address}")
        logger.info(f"    Property Value: ${record.property_value:,.2f}")
        logger.info(f"    Status: {record.status}")
        logger.info(f"    Loan Type: {record.loan_type}")
    
    # Test extraction from court records
    logger.info("\n=== Testing Court Records Extraction ===")
    extracted_court_data = nn.extract_mortgage_data(sample_court_records, "court_records")
    logger.info(f"Extracted {len(extracted_court_data)} records from court records")
    
    for i, record in enumerate(extracted_court_data):
        logger.info(f"  Record {i+1}:")
        logger.info(f"    Property ID: {record.property_id}")
        logger.info(f"    Borrower: {record.borrower_name}")
        logger.info(f"    Lender: {record.lender_name}")
        logger.info(f"    Loan Amount: ${record.loan_amount:,.2f}")
        logger.info(f"    Loan Type: {record.loan_type}")
        logger.info(f"    Property Address: {record.property_address}")
    
    # Test extraction from government API
    logger.info("\n=== Testing Government API Extraction ===")
    extracted_api_data = nn.extract_mortgage_data(sample_government_api, "government_api")
    logger.info(f"Extracted {len(extracted_api_data)} records from government API")
    
    for i, record in enumerate(extracted_api_data):
        logger.info(f"  Record {i+1}:")
        logger.info(f"    Property ID: {record.property_id}")
        logger.info(f"    Borrower: {record.borrower_name}")
        logger.info(f"    Lender: {record.lender_name}")
        logger.info(f"    Loan Amount: ${record.loan_amount:,.2f}")
        logger.info(f"    Loan Type: {record.loan_type}")
        logger.info(f"    Interest Rate: {record.interest_rate}%")
        logger.info(f"    Loan Term: {record.loan_term} years")
        logger.info(f"    Property Address: {record.property_address}")
        logger.info(f"    Property Value: ${record.property_value:,.2f}")
        logger.info(f"    Status: {record.status}")
    
    # Test validation
    logger.info("\n=== Testing Data Validation ===")
    if extracted_property_data:
        valid = nn.validate_mortgage_data(extracted_property_data[0])
        logger.info(f"First property record validation: {'Valid' if valid else 'Invalid'}")
    
    # Test quality scoring
    logger.info("\n=== Testing Data Quality Scoring ===")
    if extracted_property_data:
        quality_score = nn.get_data_quality_score(extracted_property_data[0])
        logger.info(f"Data Quality Score: {quality_score}")
    
    # Test data enhancement
    logger.info("\n=== Testing Data Enhancement ===")
    if extracted_property_data:
        enhanced_data = nn.enhance_data_quality(extracted_property_data)
        logger.info(f"Enhanced {len(enhanced_data)} records")
        if enhanced_data:
            logger.info(f"Enhanced quality score: {enhanced_data[0].quality_score}")
    
    # Test insights generation
    logger.info("\n=== Testing Insights Generation ===")
    if extracted_property_data:
        insights = nn.get_data_insights(extracted_property_data)
        logger.info(f"Data Insights: {insights}")
    
    # Test learning from training data
    logger.info("\n=== Testing Neural Network Training ===")
    
    # Create training data
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
        },
        {
            "property_id": "PROP-2001",
            "borrower_name": "Jane Doe",
            "lender_name": "Chase Bank",
            "loan_amount": 450000.00,
            "loan_type": "Conventional",
            "interest_rate": 3.75,
            "loan_term": 30,
            "loan_date": "2023-06-20",
            "property_address": "789 Pine St, Elsewhere, NY 54321",
            "property_value": 500000.00,
            "status": "active",
            "data_source": "government_api",
            "scraped_at": "2023-06-20T10:00:00Z"
        }
    ]
    
    # Convert to MortgageDataPoint objects for training
    data_points = []
    for data_point in training_data:
        mortgage_point = MortgageDataPoint(
            property_id=data_point["property_id"],
            borrower_name=data_point["borrower_name"],
            lender_name=data_point["lender_name"],
            loan_amount=data_point["loan_amount"],
            loan_type=data_point["loan_type"],
            interest_rate=data_point["interest_rate"],
            loan_term=data_point["loan_term"],
            loan_date=data_point["loan_date"],
            property_address=data_point["property_address"],
            property_value=data_point["property_value"],
            status=data_point["status"],
            data_source=data_point["data_source"],
            scraped_at=data_point["scraped_at"]
        )
        data_points.append(mortgage_point)
    
    # Train the neural network
    nn.learn_patterns(data_points)
    logger.info("Neural network training completed")
    
    logger.info("\nExample completed successfully!")

if __name__ == "__main__":
    main()
