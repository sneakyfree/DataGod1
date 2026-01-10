#!/usr/bin/env python3
"""
DataGod - Public Records Data Platform
Main application entry point

This module provides the main entry point for the DataGod application.
It can be used to start the API server or run database operations.

Usage:
    python main.py              # Start the API server
    python main.py --init       # Initialize the database
    python main.py --seed       # Seed sample data
    python main.py --help       # Show help
"""

import argparse
import logging
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datagod.config.settings import (
    API_HOST, API_PORT, API_WORKERS, API_DEBUG,
    LOG_LEVEL, LOG_FORMAT, ENVIRONMENT
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)


def init_database(reset: bool = False):
    """Initialize the database tables."""
    from db_manager import DatabaseManager

    logger.info("Initializing DataGod database...")
    db = DatabaseManager()

    if reset:
        logger.warning("Resetting database - all data will be lost!")
        db.reset_database()
    else:
        db.init_database()

    logger.info("Database initialization complete.")


def seed_database():
    """Seed the database with sample data."""
    from db_manager import DatabaseManager
    from datetime import datetime

    logger.info("Seeding database with sample data...")
    db = DatabaseManager()

    # Sample jurisdictions
    jurisdictions_data = [
        {
            "name": "Miami-Dade County",
            "state": "FL",
            "county": "Miami-Dade",
            "jurisdiction_type": "county",
            "population": 2716940,
            "api_available": True,
            "description": "Miami-Dade County, Florida"
        },
        {
            "name": "Los Angeles County",
            "state": "CA",
            "county": "Los Angeles",
            "jurisdiction_type": "county",
            "population": 10014009,
            "api_available": True,
            "description": "Los Angeles County, California"
        },
        {
            "name": "Cook County",
            "state": "IL",
            "county": "Cook",
            "jurisdiction_type": "county",
            "population": 5150233,
            "api_available": False,
            "description": "Cook County, Illinois"
        }
    ]

    created_jurisdictions = []
    for j_data in jurisdictions_data:
        jid = db.create_jurisdiction(**j_data)
        if jid:
            created_jurisdictions.append(jid)
            logger.info(f"Created jurisdiction: {j_data['name']} (ID: {jid})")

    # Create data sources for each jurisdiction
    data_sources = []
    for jid in created_jurisdictions:
        ds_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name="Official Records API",
            source_type="api",
            status="active",
            description="Official county records"
        )
        if ds_id:
            data_sources.append(ds_id)
            logger.info(f"Created data source (ID: {ds_id})")

    # Sample records
    if data_sources and created_jurisdictions:
        sample_records = [
            {
                "record_type": "mortgage",
                "title": "Mortgage - 123 Main Street",
                "amount": 450000.00,
                "grantor": "John Smith",
                "grantee": "Wells Fargo Bank",
                "address": "123 Main Street",
                "city": "Miami",
                "state": "FL",
                "date": datetime(2024, 1, 15)
            },
            {
                "record_type": "deed",
                "title": "Warranty Deed - 456 Oak Avenue",
                "amount": 325000.00,
                "grantor": "Jane Doe",
                "grantee": "Robert Johnson",
                "address": "456 Oak Avenue",
                "city": "Los Angeles",
                "state": "CA",
                "date": datetime(2024, 2, 20)
            }
        ]

        for i, record_data in enumerate(sample_records):
            jid = created_jurisdictions[i % len(created_jurisdictions)]
            dsid = data_sources[i % len(data_sources)]

            record_id = db.create_record(
                jurisdiction_id=jid,
                data_source_id=dsid,
                **record_data
            )
            if record_id:
                logger.info(f"Created record: {record_data['title']} (ID: {record_id})")

    # Sample entities
    entities = [
        {"entity_name": "John Smith", "entity_type": "person", "city": "Miami", "state": "FL"},
        {"entity_name": "Jane Doe", "entity_type": "person", "city": "Los Angeles", "state": "CA"},
        {"entity_name": "Wells Fargo Bank", "entity_type": "company", "city": "San Francisco", "state": "CA"}
    ]

    for entity in entities:
        eid = db.create_entity(**entity)
        if eid:
            logger.info(f"Created entity: {entity['entity_name']} (ID: {eid})")

    logger.info("Database seeding complete!")


def show_stats():
    """Display platform statistics."""
    from db_manager import DatabaseManager

    db = DatabaseManager()
    stats = db.get_dashboard_stats()

    print("\n" + "=" * 50)
    print("         DataGod Platform Statistics")
    print("=" * 50)
    print(f"\n  Total Records:      {stats['totalRecords']:,}")
    print(f"  Jurisdictions:      {stats['jurisdictions']:,}")
    print(f"  Data Sources:       {stats['dataSources']:,}")
    print(f"  Active Scrapers:    {stats['activeScrapers']:,}")
    print(f"  Total Entities:     {stats['totalEntities']:,}")
    print("\n" + "=" * 50 + "\n")


def start_server(host: str = None, port: int = None, reload: bool = False, workers: int = None):
    """Start the FastAPI server."""
    host = host or API_HOST
    port = port or API_PORT
    workers = workers or API_WORKERS

    logger.info(f"Starting DataGod API server...")
    logger.info(f"  Environment: {ENVIRONMENT}")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Workers: {workers if not reload else 1}")
    logger.info(f"  Debug/Reload: {reload}")

    try:
        import uvicorn

        uvicorn.run(
            "api.src.api_v2_simple:app",
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1,
            log_level="info" if not API_DEBUG else "debug"
        )
    except ImportError:
        logger.error("uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DataGod - Public Records Data Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                  # Start API server
    python main.py --init           # Initialize database
    python main.py --init --reset   # Reset and reinitialize database
    python main.py --seed           # Seed sample data
    python main.py --stats          # Show statistics
    python main.py --port 8080      # Start on custom port
    python main.py --reload         # Start with auto-reload (development)
        """
    )

    # Server options
    parser.add_argument('--host', default=None, help=f'Host to bind to (default: {API_HOST})')
    parser.add_argument('--port', type=int, default=None, help=f'Port to listen on (default: {API_PORT})')
    parser.add_argument('--workers', type=int, default=None, help=f'Number of workers (default: {API_WORKERS})')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')

    # Database options
    parser.add_argument('--init', action='store_true', help='Initialize the database')
    parser.add_argument('--reset', action='store_true', help='Reset database (use with --init)')
    parser.add_argument('--seed', action='store_true', help='Seed sample data')
    parser.add_argument('--stats', action='store_true', help='Show platform statistics')

    args = parser.parse_args()

    # Handle database operations
    if args.init:
        init_database(reset=args.reset)
        return

    if args.seed:
        seed_database()
        return

    if args.stats:
        show_stats()
        return

    # Default: start server
    start_server(
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        if os.getenv('DEBUG'):
            import traceback
            traceback.print_exc()
        sys.exit(1)
