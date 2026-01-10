#!/usr/bin/env python3
"""
DataGod CLI - Command Line Interface for the DataGod Public Records Platform

Usage:
    python cli.py [command] [options]

Commands:
    init        Initialize the database
    serve       Start the API server
    scrape      Run scrapers
    search      Search records
    stats       Show platform statistics
    seed        Seed sample data for testing
    export      Export data to file
"""

import sys
import os
import argparse
import json
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def init_database(args):
    """Initialize the database and create all tables."""
    print("Initializing DataGod database...")

    from db_manager import DatabaseManager

    db = DatabaseManager()

    if args.reset:
        confirm = input("WARNING: This will DELETE all existing data. Are you sure? (yes/no): ")
        if confirm.lower() == 'yes':
            db.reset_database()
            print("Database reset complete.")
        else:
            print("Operation cancelled.")
            return
    else:
        if db.init_database():
            print("Database initialized successfully.")
        else:
            print("Failed to initialize database.")
            sys.exit(1)


def serve_api(args):
    """Start the FastAPI server."""
    print(f"Starting DataGod API server on {args.host}:{args.port}...")

    try:
        import uvicorn
        uvicorn.run(
            "api.src.api_v2_simple:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1
        )
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


def run_scraper(args):
    """Run a scraper for a specific jurisdiction or all jurisdictions."""
    from db_manager import DatabaseManager

    db = DatabaseManager()

    # State to scraper class mapping
    STATE_SCRAPERS = {
        'FL': ('datagod.scrapers.florida_api', 'FloridaPropertyAppraiserAPI'),
        'CA': ('datagod.scrapers.california_api', 'CaliforniaPropertyAPI'),
        'TX': ('datagod.scrapers.texas_api', 'TexasPropertyAPI'),
        'NY': ('datagod.scrapers.newyork_api', 'NewYorkPropertyAPI'),
        'IL': ('datagod.scrapers.illinois_api', 'IllinoisPropertyAPI'),
        'PA': ('datagod.scrapers.pennsylvania_api', 'PennsylvaniaPropertyAPI'),
        'AZ': ('datagod.scrapers.arizona_api', 'ArizonaPropertyAPI'),
        'GA': ('datagod.scrapers.georgia_api', 'GeorgiaPropertyAPI'),
        'OH': ('datagod.scrapers.ohio_api', 'OhioPropertyAPI'),
        'WA': ('datagod.scrapers.washington_api', 'WashingtonPropertyAPI'),
        'CO': ('datagod.scrapers.colorado_api', 'ColoradoPropertyAPI'),
        'NC': ('datagod.scrapers.northcarolina_api', 'NorthCarolinaPropertyAPI'),
        'VA': ('datagod.scrapers.virginia_api', 'VirginiaPropertyAPI'),
        'NJ': ('datagod.scrapers.newjersey_api', 'NewJerseyPropertyAPI'),
    }

    def get_scraper_for_state(state: str):
        """Get the appropriate scraper class for a state."""
        scraper_info = STATE_SCRAPERS.get(state)
        if not scraper_info:
            return None
        try:
            import importlib
            module_path, class_name = scraper_info
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            print(f"  Warning: Could not load scraper for {state}: {e}")
            return None

    def scrape_jurisdiction(jurisdiction: dict, dry_run: bool = False):
        """Scrape a single jurisdiction."""
        jid = jurisdiction['id']
        name = jurisdiction['name']
        state = jurisdiction.get('state', '')

        if dry_run:
            print(f"  [DRY RUN] Would scrape: {name} ({state})")
            return {'status': 'dry_run', 'jurisdiction': name}

        scraper_class = get_scraper_for_state(state)
        if not scraper_class:
            print(f"  [SKIP] No scraper available for state: {state}")
            return {'status': 'skipped', 'reason': 'no_scraper', 'jurisdiction': name}

        try:
            print(f"  [START] Scraping {name} ({state})...")

            # Get data source for this jurisdiction
            data_sources = db.list_data_sources(jurisdiction_id=jid, limit=1)
            if not data_sources:
                ds_id = db.create_data_source(
                    jurisdiction_id=jid,
                    source_name=f"{name} Property Records",
                    source_type="api",
                    status="active"
                )
            else:
                ds_id = data_sources[0]['id']

            # Initialize scraper
            config = {
                'jurisdiction_id': jid,
                'jurisdiction_name': name,
                'data_source_id': ds_id,
            }

            scraper = scraper_class(jurisdiction_id=jid, config=config)

            # Perform search
            limit = getattr(args, 'limit', 100) or 100
            records = scraper.search_records({'limit': limit})

            if records:
                saved_count = 0
                for record in records:
                    record_id = db.create_record(
                        jurisdiction_id=jid,
                        data_source_id=ds_id,
                        record_type=record.get('record_type', 'property'),
                        title=record.get('title', 'Property Record'),
                        description=record.get('description'),
                        amount=record.get('amount'),
                        address=record.get('address'),
                        city=record.get('city'),
                        state=state,
                        grantor=record.get('grantor'),
                        grantee=record.get('grantee'),
                        date=record.get('date'),
                        raw_data=record
                    )
                    if record_id:
                        saved_count += 1

                print(f"  [DONE] {name}: Saved {saved_count}/{len(records)} records")
                return {
                    'status': 'success',
                    'jurisdiction': name,
                    'records_found': len(records),
                    'records_saved': saved_count
                }
            else:
                print(f"  [DONE] {name}: No records found")
                return {'status': 'success', 'jurisdiction': name, 'records_found': 0}

        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
            return {'status': 'error', 'jurisdiction': name, 'error': str(e)}

    # Process based on arguments
    results = []
    dry_run = getattr(args, 'dry_run', False)

    if args.all:
        jurisdictions = db.list_jurisdictions(limit=1000)
        print(f"Found {len(jurisdictions)} jurisdictions to process")
        print("-" * 60)

        for jurisdiction in jurisdictions:
            result = scrape_jurisdiction(jurisdiction, dry_run=dry_run)
            results.append(result)

    elif args.jurisdiction_id:
        jurisdiction = db.get_jurisdiction(args.jurisdiction_id)
        if jurisdiction:
            result = scrape_jurisdiction(jurisdiction, dry_run=dry_run)
            results.append(result)
        else:
            print(f"Jurisdiction {args.jurisdiction_id} not found.")
            sys.exit(1)

    elif getattr(args, 'state', None):
        jurisdictions = db.list_jurisdictions(state=args.state, limit=100)
        print(f"Found {len(jurisdictions)} jurisdictions in {args.state}")
        print("-" * 60)

        for jurisdiction in jurisdictions:
            result = scrape_jurisdiction(jurisdiction, dry_run=dry_run)
            results.append(result)

    else:
        print("Please specify --jurisdiction-id, --state, or --all")
        print("Use --dry-run to preview without scraping")
        sys.exit(1)

    # Print summary
    if results:
        print("\n" + "=" * 60)
        print("SCRAPING SUMMARY")
        print("=" * 60)
        success = sum(1 for r in results if r.get('status') == 'success')
        errors = sum(1 for r in results if r.get('status') == 'error')
        skipped = sum(1 for r in results if r.get('status') == 'skipped')
        dry_runs = sum(1 for r in results if r.get('status') == 'dry_run')
        total_records = sum(r.get('records_saved', 0) for r in results)

        print(f"  Total jurisdictions: {len(results)}")
        print(f"  Successful: {success}")
        print(f"  Errors: {errors}")
        print(f"  Skipped: {skipped}")
        if dry_runs:
            print(f"  Dry runs: {dry_runs}")
        print(f"  Total records saved: {total_records}")
        print("=" * 60)


def search_records(args):
    """Search records in the database."""
    from db_manager import DatabaseManager

    db = DatabaseManager()

    results = db.search_records(
        query=args.query,
        record_type=args.type,
        jurisdiction_id=args.jurisdiction_id,
        limit=args.limit
    )

    if not results:
        print("No records found.")
        return

    print(f"\nFound {len(results)} records:\n")
    print("-" * 80)

    for record in results:
        print(f"ID: {record['id']}")
        print(f"Title: {record['title']}")
        print(f"Type: {record['record_type']}")
        if record['amount']:
            print(f"Amount: ${record['amount']:,.2f}")
        if record['date']:
            print(f"Date: {record['date']}")
        if record['grantor']:
            print(f"Grantor: {record['grantor']}")
        if record['grantee']:
            print(f"Grantee: {record['grantee']}")
        print("-" * 80)


def show_stats(args):
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
    print("\n" + "=" * 50)

    if stats['recentRecords']:
        print("\nRecent Records:")
        print("-" * 50)
        for record in stats['recentRecords'][:5]:
            print(f"  - {record['title'][:50]}...")


def seed_data(args):
    """Seed the database with sample data for testing."""
    print("Seeding database with sample data...")

    from db_manager import DatabaseManager

    db = DatabaseManager()

    # Sample jurisdictions
    jurisdictions = [
        {
            "name": "Miami-Dade County",
            "state": "FL",
            "county": "Miami-Dade",
            "jurisdiction_type": "county",
            "population": 2716940,
            "api_available": True,
            "description": "Miami-Dade County, Florida - largest county in Florida"
        },
        {
            "name": "Los Angeles County",
            "state": "CA",
            "county": "Los Angeles",
            "jurisdiction_type": "county",
            "population": 10014009,
            "api_available": True,
            "description": "Los Angeles County, California - most populous county in the US"
        },
        {
            "name": "Cook County",
            "state": "IL",
            "county": "Cook",
            "jurisdiction_type": "county",
            "population": 5150233,
            "api_available": False,
            "description": "Cook County, Illinois - includes Chicago"
        },
        {
            "name": "Harris County",
            "state": "TX",
            "county": "Harris",
            "jurisdiction_type": "county",
            "population": 4731145,
            "api_available": True,
            "description": "Harris County, Texas - includes Houston"
        },
        {
            "name": "Maricopa County",
            "state": "AZ",
            "county": "Maricopa",
            "jurisdiction_type": "county",
            "population": 4485414,
            "api_available": False,
            "description": "Maricopa County, Arizona - includes Phoenix"
        }
    ]

    created_jurisdictions = []
    for j in jurisdictions:
        jid = db.create_jurisdiction(**j)
        if jid:
            created_jurisdictions.append(jid)
            print(f"  Created jurisdiction: {j['name']} (ID: {jid})")

    if not created_jurisdictions:
        print("No jurisdictions created (may already exist)")
        return

    # Sample data sources
    data_sources = []
    for jid in created_jurisdictions:
        # Create API data source
        ds_id = db.create_data_source(
            jurisdiction_id=jid,
            source_name=f"Official Records API",
            source_type="api",
            status="active",
            description="Official county records API endpoint"
        )
        if ds_id:
            data_sources.append(ds_id)
            print(f"  Created data source (ID: {ds_id})")

    # Sample records
    sample_records = [
        {
            "record_type": "mortgage",
            "title": "Mortgage - 123 Main Street",
            "amount": 450000.00,
            "grantor": "John Smith",
            "grantee": "Wells Fargo Bank",
            "borrower": "John Smith",
            "lender": "Wells Fargo Bank",
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
        },
        {
            "record_type": "lien",
            "title": "Tax Lien - 789 Pine Road",
            "amount": 15000.00,
            "grantor": "IRS",
            "grantee": "Michael Williams",
            "address": "789 Pine Road",
            "city": "Chicago",
            "state": "IL",
            "date": datetime(2024, 3, 10)
        },
        {
            "record_type": "ucc",
            "title": "UCC Filing - ABC Corporation",
            "amount": 1000000.00,
            "grantor": "ABC Corporation",
            "grantee": "First National Bank",
            "city": "Houston",
            "state": "TX",
            "date": datetime(2024, 4, 5)
        }
    ]

    if data_sources:
        for i, record_data in enumerate(sample_records):
            # Assign to a jurisdiction and data source
            jid = created_jurisdictions[i % len(created_jurisdictions)]
            dsid = data_sources[i % len(data_sources)]

            record_id = db.create_record(
                jurisdiction_id=jid,
                data_source_id=dsid,
                **record_data
            )
            if record_id:
                print(f"  Created record: {record_data['title'][:40]}... (ID: {record_id})")

    # Sample entities
    entities = [
        {"entity_name": "John Smith", "entity_type": "person", "city": "Miami", "state": "FL"},
        {"entity_name": "Jane Doe", "entity_type": "person", "city": "Los Angeles", "state": "CA"},
        {"entity_name": "ABC Corporation", "entity_type": "company", "city": "Houston", "state": "TX"},
        {"entity_name": "Wells Fargo Bank", "entity_type": "company", "city": "San Francisco", "state": "CA"},
        {"entity_name": "First National Bank", "entity_type": "company", "city": "New York", "state": "NY"}
    ]

    for entity in entities:
        eid = db.create_entity(**entity)
        if eid:
            print(f"  Created entity: {entity['entity_name']} (ID: {eid})")

    print("\nSample data seeding complete!")
    print("\nRun 'python cli.py stats' to see the current database statistics.")


def export_data(args):
    """Export records to a file."""
    from db_manager import DatabaseManager
    import csv

    db = DatabaseManager()

    print(f"Exporting records to {args.output}...")

    records = db.search_records(
        query=args.query,
        record_type=args.type,
        limit=args.limit or 10000
    )

    if not records:
        print("No records to export.")
        return

    if args.format == 'json':
        with open(args.output, 'w') as f:
            json.dump(records, f, indent=2, default=str)
    elif args.format == 'csv':
        if records:
            with open(args.output, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)

    print(f"Exported {len(records)} records to {args.output}")


def list_jurisdictions(args):
    """List all jurisdictions in the database."""
    from db_manager import DatabaseManager

    db = DatabaseManager()

    jurisdictions = db.list_jurisdictions(
        state=args.state,
        limit=args.limit
    )

    if not jurisdictions:
        print("No jurisdictions found.")
        return

    print(f"\n{'ID':<6} {'Name':<30} {'State':<6} {'Type':<10} {'API':<5}")
    print("-" * 60)

    for j in jurisdictions:
        api = "Yes" if j['api_available'] else "No"
        print(f"{j['id']:<6} {j['name'][:28]:<30} {j['state'] or 'N/A':<6} {j['type'] or 'N/A':<10} {api:<5}")


def add_jurisdiction(args):
    """Add a new jurisdiction to the database."""
    from db_manager import DatabaseManager

    db = DatabaseManager()

    jid = db.create_jurisdiction(
        name=args.name,
        state=args.state,
        county=args.county,
        jurisdiction_type=args.type,
        api_available=args.api_available,
        description=args.description
    )

    if jid:
        print(f"Created jurisdiction '{args.name}' with ID: {jid}")
    else:
        print(f"Failed to create jurisdiction (may already exist)")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DataGod CLI - Public Records Data Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python cli.py init                    # Initialize database
    python cli.py init --reset            # Reset database (deletes all data)
    python cli.py serve                   # Start API server
    python cli.py serve --port 8080       # Start on custom port
    python cli.py stats                   # Show statistics
    python cli.py seed                    # Seed sample data
    python cli.py search "mortgage"       # Search records
    python cli.py list-jurisdictions      # List all jurisdictions
    python cli.py export -o data.json     # Export to JSON
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # init command
    init_parser = subparsers.add_parser('init', help='Initialize the database')
    init_parser.add_argument('--reset', action='store_true', help='Reset database (deletes all data)')

    # serve command
    serve_parser = subparsers.add_parser('serve', help='Start the API server')
    serve_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    serve_parser.add_argument('--port', type=int, default=8000, help='Port to listen on (default: 8000)')
    serve_parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    serve_parser.add_argument('--workers', type=int, default=4, help='Number of worker processes (default: 4)')

    # scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Run scrapers')
    scrape_parser.add_argument('--jurisdiction-id', type=int, help='Specific jurisdiction ID to scrape')
    scrape_parser.add_argument('--state', help='Scrape all jurisdictions in a state (e.g., FL, CA)')
    scrape_parser.add_argument('--all', action='store_true', help='Scrape all jurisdictions')
    scrape_parser.add_argument('--dry-run', action='store_true', help='Preview without actually scraping')
    scrape_parser.add_argument('--limit', type=int, default=100, help='Maximum records per jurisdiction (default: 100)')

    # search command
    search_parser = subparsers.add_parser('search', help='Search records')
    search_parser.add_argument('query', nargs='?', help='Search query')
    search_parser.add_argument('--type', help='Record type filter')
    search_parser.add_argument('--jurisdiction-id', type=int, help='Jurisdiction ID filter')
    search_parser.add_argument('--limit', type=int, default=20, help='Maximum results (default: 20)')

    # stats command
    stats_parser = subparsers.add_parser('stats', help='Show platform statistics')

    # seed command
    seed_parser = subparsers.add_parser('seed', help='Seed sample data for testing')

    # export command
    export_parser = subparsers.add_parser('export', help='Export data to file')
    export_parser.add_argument('-o', '--output', required=True, help='Output file path')
    export_parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Export format')
    export_parser.add_argument('--query', help='Filter query')
    export_parser.add_argument('--type', help='Record type filter')
    export_parser.add_argument('--limit', type=int, help='Maximum records to export')

    # list-jurisdictions command
    list_j_parser = subparsers.add_parser('list-jurisdictions', help='List jurisdictions')
    list_j_parser.add_argument('--state', help='Filter by state')
    list_j_parser.add_argument('--limit', type=int, default=50, help='Maximum results')

    # add-jurisdiction command
    add_j_parser = subparsers.add_parser('add-jurisdiction', help='Add a new jurisdiction')
    add_j_parser.add_argument('name', help='Jurisdiction name')
    add_j_parser.add_argument('--state', required=True, help='State code (e.g., FL, CA)')
    add_j_parser.add_argument('--county', help='County name')
    add_j_parser.add_argument('--type', default='county', help='Jurisdiction type')
    add_j_parser.add_argument('--api-available', action='store_true', help='Has API available')
    add_j_parser.add_argument('--description', help='Description')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Route to appropriate handler
    commands = {
        'init': init_database,
        'serve': serve_api,
        'scrape': run_scraper,
        'search': search_records,
        'stats': show_stats,
        'seed': seed_data,
        'export': export_data,
        'list-jurisdictions': list_jurisdictions,
        'add-jurisdiction': add_jurisdiction
    }

    if args.command in commands:
        try:
            commands[args.command](args)
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            if os.getenv('DEBUG'):
                import traceback
                traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
