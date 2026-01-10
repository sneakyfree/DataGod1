#!/usr/bin/env python3
"""
DataGod - Mortgage Data Gathering Neural Network
Main application entry point
"""

import logging
import sys
from typing import Dict, Any
from datagod.db_manager import init_db
from datagod.models.jurisdiction import Jurisdiction
from datagod.models.data_source import DataSource
from datagod.models.record import Record
from datagod.utils.data_validation import validator
from datagod.utils.data_processor import processor
from datagod.scrapers.property_scraper import PropertyScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('datagod.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def setup_database():
    """Initialize database"""
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def create_sample_jurisdiction():
    """Create a sample jurisdiction for testing"""
    from datagod.db_manager import get_db_session
    
    session = get_db_session()
    try:
        # Check if jurisdiction already exists
        jurisdiction = session.query(Jurisdiction).filter_by(name="Sample County").first()
        
        if not jurisdiction:
            jurisdiction = Jurisdiction(
                name="Sample County",
                state="CA",
                county="Sample County",
                type="County",
                api_available=False,
                scraper_needed=True,
                description="Sample jurisdiction for testing"
            )
            session.add(jurisdiction)
            session.commit()
            logger.info("Sample jurisdiction created")
        else:
            logger.info("Sample jurisdiction already exists")
            
    except Exception as e:
        logger.error(f"Failed to create sample jurisdiction: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

def create_sample_data_source():
    """Create a sample data source for testing"""
    from datagod.db_manager import get_db_session
    
    session = get_db_session()
    try:
        # Get jurisdiction
        jurisdiction = session.query(Jurisdiction).filter_by(name="Sample County").first()
        if not jurisdiction:
            logger.error("No jurisdiction found for data source")
            return
            
        # Check if data source already exists
        data_source = session.query(DataSource).filter_by(source_name="Sample Property Source").first()
        
        if not data_source:
            data_source = DataSource(
                jurisdiction_id=jurisdiction.id,
                source_name="Sample Property Source",
                source_type="scraper",
                status="active",
                description="Sample property data source for testing"
            )
            session.add(data_source)
            session.commit()
            logger.info("Sample data source created")
        else:
            logger.info("Sample data source already exists")
            
    except Exception as e:
        logger.error(f"Failed to create sample data source: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

def run_data_collection():
    """Run the main data collection process"""
    logger.info("Starting data collection process...")
    
    # Initialize database
    setup_database()
    
    # Create sample data for testing
    create_sample_jurisdiction()
    create_sample_data_source()
    
    # Test scraping
    logger.info("Testing property scraping...")
    scraper = PropertyScraper(base_url="https://example-property-data.com")
    property_data = scraper.scrape()
    
    if property_data:
        logger.info(f"Scraped {len(property_data)} property records")
        
        # Validate data
        for record in property_data:
            validation_result = validator.validate_record(record)
            if not validation_result['valid']:
                logger.warning(f"Validation errors: {validation_result['errors']}")
            else:
                logger.info("Record validation passed")
                
        # Process data
        processed_data = []
        for record in property_data:
            enriched_data = processor.enrich_data(record)
            processed_data.append(enriched_data)
        
        logger.info(f"Processed {len(processed_data)} records")
        logger.info("Data collection process completed successfully")
    else:
        logger.warning("No data was scraped")

def main():
    """Main entry point"""
    try:
        run_data_collection()
        logger.info("DataGod application completed successfully")
    except Exception as e:
        logger.error(f"DataGod application failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
