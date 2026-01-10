#!/usr/bin/env python3
"""
Populate Jurisdictions from FIPS Data

This script loads all 3,143 US counties from the FIPS data files
into the database jurisdictions table.

Usage:
    python scripts/populate_jurisdictions.py [--dry-run] [--state STATE]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_fips_data() -> dict:
    """Load FIPS county data from JSON file."""
    fips_file = project_root / 'datagod' / 'data' / 'fips' / 'us_counties_complete.json'

    if not fips_file.exists():
        raise FileNotFoundError(f"FIPS data file not found: {fips_file}")

    with open(fips_file, 'r') as f:
        data = json.load(f)

    logger.info(f"Loaded FIPS data: {data['metadata']['total_counties']} counties")
    return data


def load_states_data() -> dict:
    """Load states data from JSON file."""
    states_file = project_root / 'datagod' / 'data' / 'fips' / 'us_states.json'

    if not states_file.exists():
        logger.warning(f"States file not found: {states_file}")
        return {}

    with open(states_file, 'r') as f:
        data = json.load(f)

    return data


def populate_jurisdictions(
    db_manager: DatabaseManager,
    fips_data: dict,
    states_filter: str = None,
    dry_run: bool = False
) -> dict:
    """
    Populate jurisdictions from FIPS data.

    Args:
        db_manager: Database manager instance
        fips_data: FIPS county data
        states_filter: Optional state code to filter by
        dry_run: If True, don't actually insert data

    Returns:
        Dict with statistics
    """
    stats = {
        'total_counties': 0,
        'created': 0,
        'skipped': 0,
        'errors': 0,
        'by_state': {}
    }

    counties = fips_data.get('counties', {})

    # Filter states if specified
    if states_filter:
        states_filter = states_filter.upper()
        if states_filter not in counties:
            logger.error(f"State '{states_filter}' not found in FIPS data")
            return stats
        counties = {states_filter: counties[states_filter]}

    # Process each state
    for state_code, state_counties in counties.items():
        state_stats = {'created': 0, 'skipped': 0, 'errors': 0}

        logger.info(f"Processing {state_code}: {len(state_counties)} counties")

        jurisdictions_data = []

        for county in state_counties:
            stats['total_counties'] += 1

            jurisdiction = {
                'name': county['name'],
                'state': state_code,
                'fips_code': county['fips'],
                'seat': county.get('seat'),
                'population': county.get('population'),
                'type': 'county'
            }

            jurisdictions_data.append(jurisdiction)

        if dry_run:
            state_stats['created'] = len(jurisdictions_data)
            logger.info(f"  [DRY RUN] Would create {len(jurisdictions_data)} jurisdictions")
        else:
            # Bulk insert
            result = db_manager.bulk_create_jurisdictions(jurisdictions_data)
            state_stats['created'] = result['created']
            state_stats['skipped'] = result['skipped']
            state_stats['errors'] = result['errors']
            logger.info(f"  Created: {result['created']}, Skipped: {result['skipped']}, Errors: {result['errors']}")

        stats['created'] += state_stats['created']
        stats['skipped'] += state_stats['skipped']
        stats['errors'] += state_stats['errors']
        stats['by_state'][state_code] = state_stats

    return stats


def add_states_as_jurisdictions(
    db_manager: DatabaseManager,
    states_data: dict,
    dry_run: bool = False
) -> dict:
    """
    Add states themselves as jurisdictions.

    Args:
        db_manager: Database manager instance
        states_data: States data with FIPS codes
        dry_run: If True, don't actually insert data

    Returns:
        Dict with statistics
    """
    stats = {'created': 0, 'skipped': 0, 'errors': 0}

    states = states_data.get('states', [])

    if not states:
        logger.warning("No states data available")
        return stats

    logger.info(f"Adding {len(states)} states as jurisdictions")

    jurisdictions_data = []

    for state in states:
        # Create 5-digit FIPS with zeros for county portion
        fips_code = f"{state['fips']}000"

        jurisdiction = {
            'name': state['name'],
            'state': state['code'],
            'fips_code': fips_code,
            'population': state.get('population'),
            'type': 'state'
        }
        jurisdictions_data.append(jurisdiction)

    if dry_run:
        stats['created'] = len(jurisdictions_data)
        logger.info(f"[DRY RUN] Would create {len(jurisdictions_data)} state jurisdictions")
    else:
        result = db_manager.bulk_create_jurisdictions(jurisdictions_data)
        stats = result
        logger.info(f"States - Created: {result['created']}, Skipped: {result['skipped']}, Errors: {result['errors']}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Populate jurisdictions from FIPS data'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--state',
        type=str,
        help='Process only specific state (e.g., CA, TX)'
    )
    parser.add_argument(
        '--include-states',
        action='store_true',
        help='Also add states as jurisdictions'
    )
    parser.add_argument(
        '--database-url',
        type=str,
        help='Database URL (optional, uses default if not specified)'
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("DataGod Jurisdiction Population Script")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    # Load FIPS data
    try:
        fips_data = load_fips_data()
        states_data = load_states_data()
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        sys.exit(1)

    # Initialize database
    try:
        db_manager = DatabaseManager(args.database_url) if args.database_url else DatabaseManager()
        db_manager.init_database()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Populate counties
    logger.info("\n--- Populating Counties ---")
    county_stats = populate_jurisdictions(
        db_manager,
        fips_data,
        states_filter=args.state,
        dry_run=args.dry_run
    )

    # Optionally add states
    state_stats = {'created': 0, 'skipped': 0, 'errors': 0}
    if args.include_states and not args.state:
        logger.info("\n--- Adding States ---")
        state_stats = add_states_as_jurisdictions(
            db_manager,
            states_data,
            dry_run=args.dry_run
        )

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total counties processed: {county_stats['total_counties']}")
    logger.info(f"Counties created: {county_stats['created']}")
    logger.info(f"Counties skipped (already exist): {county_stats['skipped']}")
    logger.info(f"Counties with errors: {county_stats['errors']}")

    if args.include_states:
        logger.info(f"States created: {state_stats['created']}")

    # Verify by checking database
    if not args.dry_run:
        summary = db_manager.get_coverage_summary()
        logger.info("\n--- Database Status ---")
        logger.info(f"Total jurisdictions in DB: {summary.get('total_jurisdictions', 0)}")
        logger.info(f"Jurisdictions with FIPS: {summary.get('jurisdictions_with_fips', 0)}")

        by_state = summary.get('by_state', {})
        if by_state:
            logger.info(f"States with data: {len(by_state)}")
            # Show top 5 by count
            sorted_states = sorted(by_state.items(), key=lambda x: x[1], reverse=True)[:5]
            for state, count in sorted_states:
                logger.info(f"  {state}: {count} jurisdictions")

    logger.info("\nDone!")


if __name__ == '__main__':
    main()
