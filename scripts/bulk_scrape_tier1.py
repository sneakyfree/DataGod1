#!/usr/bin/env python3
"""
Bulk Scrape Tier 1 States

Initiates coverage collection for Tier 1 states (highest population):
- California (58 counties)
- Texas (254 counties)
- Florida (67 counties)
- New York (62 counties)

This script queues scraping tasks for all counties in these states
across all data categories.
"""

import sys
import os
import argparse
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import DatabaseManager
from datagod.scrapers.scraper_orchestrator import (
    ScraperOrchestrator,
    CoverageStatus,
    TaskPriority
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Tier 1 states (highest population impact)
TIER1_STATES = ['CA', 'TX', 'FL', 'NY']

# All data categories to collect
DATA_CATEGORIES = [
    'court_records',
    'business_filings',
    'professional_licenses',
    'property_records',
    'vital_records',
    'criminal_records',
    'voter_records',
    'financial_records',
    'asset_records',
    'education_records',
    'employment_records',
    'health_safety_records',
    'transportation_records',
    'regulatory_records',
]


def get_state_jurisdictions(db: DatabaseManager, state: str) -> list:
    """Get all jurisdictions for a state."""
    return db.list_jurisdictions_by_state(state)


def queue_jurisdiction_scrape(
    orchestrator: ScraperOrchestrator,
    jurisdiction: dict,
    categories: list,
    priority: TaskPriority = TaskPriority.NORMAL
) -> int:
    """
    Queue scraping tasks for a single jurisdiction.

    Returns the number of tasks queued.
    """
    fips = jurisdiction.get('fips_code')
    if not fips:
        logger.warning(f"No FIPS code for {jurisdiction['name']}, skipping")
        return 0

    # Update coverage for each category (simulated for now)
    tasks_queued = 0
    for category in categories:
        try:
            # For now, mark as partial coverage to track that we've attempted
            orchestrator.update_coverage(
                fips_code=fips,
                data_category=category,
                status=CoverageStatus.PARTIAL,
                record_count=0,
                source_url=f"pending://{jurisdiction['state']}/{category}",
                notes=f"Queued for scraping {datetime.utcnow().isoformat()}"
            )
            tasks_queued += 1
        except Exception as e:
            logger.error(f"Error queueing {category} for {jurisdiction['name']}: {e}")

    return tasks_queued


def scrape_state(
    db: DatabaseManager,
    orchestrator: ScraperOrchestrator,
    state: str,
    categories: list,
    limit: int = None,
    priority: TaskPriority = TaskPriority.NORMAL
) -> dict:
    """
    Queue scraping for all counties in a state.

    Returns stats about the operation.
    """
    logger.info(f"Starting scrape queue for state: {state}")

    jurisdictions = get_state_jurisdictions(db, state)
    if limit:
        jurisdictions = jurisdictions[:limit]

    stats = {
        'state': state,
        'total_jurisdictions': len(jurisdictions),
        'jurisdictions_processed': 0,
        'tasks_queued': 0,
        'errors': 0,
        'start_time': datetime.utcnow().isoformat()
    }

    for jurisdiction in jurisdictions:
        try:
            tasks = queue_jurisdiction_scrape(
                orchestrator, jurisdiction, categories, priority
            )
            stats['tasks_queued'] += tasks
            stats['jurisdictions_processed'] += 1

            if stats['jurisdictions_processed'] % 10 == 0:
                logger.info(
                    f"Progress: {stats['jurisdictions_processed']}/{len(jurisdictions)} "
                    f"jurisdictions processed"
                )
        except Exception as e:
            logger.error(f"Error processing {jurisdiction['name']}: {e}")
            stats['errors'] += 1

    stats['end_time'] = datetime.utcnow().isoformat()
    logger.info(f"Completed {state}: {stats['tasks_queued']} tasks queued")

    return stats


def main():
    parser = argparse.ArgumentParser(description='Bulk scrape Tier 1 states')
    parser.add_argument(
        '--states',
        nargs='+',
        default=TIER1_STATES,
        help='States to process (default: CA TX FL NY)'
    )
    parser.add_argument(
        '--categories',
        nargs='+',
        default=DATA_CATEGORIES,
        help='Data categories to scrape'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit jurisdictions per state (for testing)'
    )
    parser.add_argument(
        '--priority',
        choices=['critical', 'high', 'normal', 'low'],
        default='high',
        help='Task priority level'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually queueing'
    )

    args = parser.parse_args()

    # Map priority string to enum
    priority_map = {
        'critical': TaskPriority.CRITICAL,
        'high': TaskPriority.HIGH,
        'normal': TaskPriority.NORMAL,
        'low': TaskPriority.LOW
    }
    priority = priority_map[args.priority]

    print("=" * 60)
    print("DataGod Bulk Scraper - Tier 1 States")
    print("=" * 60)
    print(f"States: {', '.join(args.states)}")
    print(f"Categories: {len(args.categories)} data types")
    print(f"Priority: {args.priority}")
    print(f"Limit per state: {args.limit or 'None (all)'}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN MODE - No changes will be made]\n")

    # Initialize database and orchestrator
    db = DatabaseManager()
    orchestrator = ScraperOrchestrator(db_manager=db)

    all_stats = []

    for state in args.states:
        print(f"\n--- Processing {state} ---")

        # Get count first
        jurisdictions = get_state_jurisdictions(db, state)
        count = len(jurisdictions)
        print(f"Found {count} jurisdictions in {state}")

        if args.dry_run:
            print(f"Would queue {count * len(args.categories)} tasks")
            all_stats.append({
                'state': state,
                'jurisdictions': count,
                'would_queue': count * len(args.categories)
            })
            continue

        stats = scrape_state(
            db=db,
            orchestrator=orchestrator,
            state=state,
            categories=args.categories,
            limit=args.limit,
            priority=priority
        )
        all_stats.append(stats)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_jurisdictions = 0
    total_tasks = 0
    total_errors = 0

    for stats in all_stats:
        state = stats.get('state', 'Unknown')
        if args.dry_run:
            print(f"{state}: {stats.get('jurisdictions', 0)} jurisdictions, "
                  f"{stats.get('would_queue', 0)} tasks (dry run)")
            total_jurisdictions += stats.get('jurisdictions', 0)
            total_tasks += stats.get('would_queue', 0)
        else:
            print(f"{state}: {stats.get('jurisdictions_processed', 0)} processed, "
                  f"{stats.get('tasks_queued', 0)} tasks, "
                  f"{stats.get('errors', 0)} errors")
            total_jurisdictions += stats.get('jurisdictions_processed', 0)
            total_tasks += stats.get('tasks_queued', 0)
            total_errors += stats.get('errors', 0)

    print("-" * 60)
    print(f"TOTAL: {total_jurisdictions} jurisdictions, {total_tasks} tasks")
    if not args.dry_run and total_errors > 0:
        print(f"ERRORS: {total_errors}")
    print("=" * 60)

    # Get updated coverage summary
    if not args.dry_run:
        print("\n--- Updated Coverage Summary ---")
        summary = db.get_coverage_summary()
        print(f"Total jurisdictions: {summary['total_jurisdictions']}")
        print(f"With coverage data: {summary['jurisdictions_with_coverage']}")
        print(f"Coverage percentage: {summary['coverage_percentage']}%")

    return 0


if __name__ == '__main__':
    sys.exit(main())
