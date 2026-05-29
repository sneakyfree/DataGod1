#!/usr/bin/env python3
"""
Example usage of the Mortgage Data Gathering Neural Network
"""

import logging

from datagod.ml.mortgage import (
    MortgageDataGatheringNeuralNetwork,
    MortgageDataScraper,
    MortgageNeuralNetworkIntegration,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Demonstrate the mortgage neural network usage"""

    logger.info("Starting Mortgage Neural Network Example")

    # Initialize the neural network
    nn = MortgageDataGatheringNeuralNetwork()

    # Sample raw data (simulating what might be scraped from a source)
    sample_data = """
    Property ID: PROP-1001
    Borrower: John Smith
    Lender: Bank of America
    Loan Amount: $350,000
    Interest Rate: 4.25%
    Loan Term: 30 years
    Loan Date: 2023-05-15
    Property Address: 123 Main St, Anytown, CA 12345
    Property Value: $400,000
    Status: Active
    """

    # Extract mortgage data
    logger.info("Extracting mortgage data...")
    extracted_data = nn.extract_mortgage_data(sample_data, "property_records")

    logger.info(f"Extracted {len(extracted_data)} data points")

    # Show the extracted data
    for data_point in extracted_data:
        logger.info(f"Property ID: {data_point.property_id}")
        logger.info(f"Loan Amount: ${data_point.loan_amount:,.2f}")
        logger.info(f"Interest Rate: {data_point.interest_rate}%")
        logger.info(f"Loan Term: {data_point.loan_term} years")
        logger.info(f"Property Address: {data_point.property_address}")
        logger.info("---")

    # Test quality scoring
    if extracted_data:
        quality_score = nn.get_data_quality_score(extracted_data[0])
        logger.info(f"Data Quality Score: {quality_score}")

    # Test validation
    is_valid = nn.validate_mortgage_data(extracted_data[0]) if extracted_data else False
    logger.info(f"Data Valid: {is_valid}")

    # Test the scraper integration
    logger.info("Testing scraper integration...")
    scraper = MortgageDataScraper("https://example.com")

    # Test processing with the integration layer
    integration = MortgageNeuralNetworkIntegration()

    # Process data through the integration layer
    processed_data = integration.process_mortgage_data(sample_data, "property_records")
    logger.info(f"Processed {len(processed_data)} records through integration layer")

    logger.info("Mortgage Neural Network Example Completed")


if __name__ == "__main__":
    main()
