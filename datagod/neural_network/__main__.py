"""Main entry point for the neural network module"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datagod.models import Base
from datagod.neural_network.integration import NeuralNetworkIntegration

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main function to demonstrate neural network usage"""

    # Create database engine (adjust connection string as needed)
    engine = create_engine("sqlite:///datagod.db")

    # Create tables
    Base.metadata.create_all(engine)

    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Initialize the neural network integration
        nn_integration = NeuralNetworkIntegration(session)

        # Example usage:
        # 1. Initialize processor
        nn_integration.initialize_processor()

        # 2. Gather data (you would need to have jurisdictions and data sources set up)
        # records_gathered = nn_integration.gather_mortgage_data("Example Jurisdiction")

        # 3. Process data with neural network
        # nn_integration.process_mortgage_data("Example Jurisdiction")

        logger.info("Neural network module initialized successfully")

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
