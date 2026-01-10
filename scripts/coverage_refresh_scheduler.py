#!/usr/bin/env python3
"""
Coverage Refresh Scheduler

Automated script for maintaining data freshness across all jurisdictions.
Implements the refresh cadence from the master plan:

| Data Type           | Refresh Frequency |
|---------------------|-------------------|
| Court filings       | Daily             |
| Business filings    | Weekly            |
| Property records    | Monthly           |
| Inmate/offender     | Daily             |
| Campaign finance    | Weekly            |
| Vital records       | Monthly           |
| Professional licenses| Weekly           |
| Regulatory records  | Weekly            |

Usage:
    python scripts/coverage_refresh_scheduler.py --mode check
    python scripts/coverage_refresh_scheduler.py --mode refresh --category court_records
    python scripts/coverage_refresh_scheduler.py --mode schedule --daemon
"""

import sys
import os
import argparse
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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


# Refresh cadence configuration (in days)
REFRESH_CADENCE = {
    'court_records': 1,         # Daily
    'criminal_records': 1,      # Daily (inmates, offenders)
    'business_filings': 7,      # Weekly
    'voter_records': 7,         # Weekly (campaign finance)
    'professional_licenses': 7, # Weekly
    'regulatory_records': 7,    # Weekly
    'property_records': 30,     # Monthly
    'vital_records': 30,        # Monthly
    'financial_records': 7,     # Weekly
    'asset_records': 30,        # Monthly
    'education_records': 30,    # Monthly
    'employment_records': 30,   # Monthly
    'health_safety_records': 7, # Weekly
    'transportation_records': 7,# Weekly
}

# Priority based on population tiers
TIER_PRIORITY = {
    1: TaskPriority.CRITICAL,  # CA, TX, FL, NY
    2: TaskPriority.HIGH,      # PA, IL, OH, GA, NC, MI, etc.
    3: TaskPriority.NORMAL,    # Remaining states
    4: TaskPriority.LOW,       # Territories
}

# State tiers for prioritization
STATE_TIERS = {
    'CA': 1, 'TX': 1, 'FL': 1, 'NY': 1,
    'PA': 2, 'IL': 2, 'OH': 2, 'GA': 2, 'NC': 2, 'MI': 2,
    'NJ': 2, 'VA': 2, 'WA': 2, 'AZ': 2, 'MA': 2, 'TN': 2,
    'IN': 2, 'MO': 2, 'MD': 2, 'WI': 2, 'CO': 2, 'MN': 2,
    'SC': 2, 'AL': 2, 'LA': 2,
    # Tier 3: All other states (default)
    'PR': 4, 'GU': 4, 'VI': 4, 'AS': 4, 'MP': 4,  # Territories
}


def get_stale_jurisdictions(
    db: DatabaseManager,
    category: str,
    max_age_days: int = None
) -> List[Dict]:
    """
    Find jurisdictions with stale or missing coverage for a category.

    Args:
        db: Database manager
        category: Data category to check
        max_age_days: Override for staleness threshold

    Returns:
        List of jurisdictions needing refresh
    """
    if max_age_days is None:
        max_age_days = REFRESH_CADENCE.get(category, 7)

    stale_threshold = datetime.utcnow() - timedelta(days=max_age_days)
    stale_jurisdictions = []

    try:
        # Get all jurisdictions with FIPS codes
        with db.get_session() as session:
            from datagod.models import Jurisdiction

            jurisdictions = session.query(Jurisdiction).filter(
                Jurisdiction.fips_code.isnot(None)
            ).all()

            for j in jurisdictions:
                metadata = j.jurisdiction_metadata or {}
                coverage = metadata.get('coverage', {})
                cat_coverage = coverage.get(category, {})

                needs_refresh = False
                reason = ''

                if not cat_coverage:
                    needs_refresh = True
                    reason = 'no_coverage'
                elif cat_coverage.get('status') == 'error':
                    needs_refresh = True
                    reason = 'error_status'
                elif cat_coverage.get('last_scraped'):
                    try:
                        last_scraped = datetime.fromisoformat(
                            cat_coverage['last_scraped'].replace('Z', '+00:00')
                        )
                        if last_scraped.replace(tzinfo=None) < stale_threshold:
                            needs_refresh = True
                            reason = 'stale'
                    except (ValueError, TypeError):
                        needs_refresh = True
                        reason = 'invalid_date'
                else:
                    needs_refresh = True
                    reason = 'no_timestamp'

                if needs_refresh:
                    stale_jurisdictions.append({
                        'id': j.id,
                        'name': j.name,
                        'state': j.state,
                        'fips_code': j.fips_code,
                        'population': j.population,
                        'reason': reason,
                        'last_scraped': cat_coverage.get('last_scraped'),
                        'tier': STATE_TIERS.get(j.state, 3)
                    })

            # Sort by tier then population
            stale_jurisdictions.sort(
                key=lambda x: (x['tier'], -(x['population'] or 0))
            )

    except Exception as e:
        logger.error(f"Error finding stale jurisdictions: {e}")

    return stale_jurisdictions


def check_refresh_status(db: DatabaseManager) -> Dict:
    """
    Check refresh status across all categories.

    Returns summary of what needs refreshing.
    """
    summary = {
        'timestamp': datetime.utcnow().isoformat(),
        'categories': {},
        'total_stale': 0,
        'total_jurisdictions': 0
    }

    # Get total jurisdiction count
    coverage_summary = db.get_coverage_summary()
    summary['total_jurisdictions'] = coverage_summary.get('total_jurisdictions', 0)

    for category, cadence_days in REFRESH_CADENCE.items():
        stale = get_stale_jurisdictions(db, category, cadence_days)

        summary['categories'][category] = {
            'cadence_days': cadence_days,
            'stale_count': len(stale),
            'stale_percentage': round(
                len(stale) / max(summary['total_jurisdictions'], 1) * 100, 1
            ),
            'by_tier': {
                1: len([j for j in stale if j['tier'] == 1]),
                2: len([j for j in stale if j['tier'] == 2]),
                3: len([j for j in stale if j['tier'] == 3]),
                4: len([j for j in stale if j['tier'] == 4]),
            }
        }
        summary['total_stale'] += len(stale)

    return summary


def refresh_category(
    db: DatabaseManager,
    orchestrator: ScraperOrchestrator,
    category: str,
    limit: int = None,
    tier: int = None,
    dry_run: bool = False
) -> Dict:
    """
    Refresh coverage for a specific category.

    Args:
        db: Database manager
        orchestrator: Scraper orchestrator
        category: Category to refresh
        limit: Max jurisdictions to process
        tier: Only process specific tier
        dry_run: Don't actually queue tasks

    Returns:
        Stats about the refresh operation
    """
    cadence_days = REFRESH_CADENCE.get(category, 7)
    stale = get_stale_jurisdictions(db, category, cadence_days)

    if tier:
        stale = [j for j in stale if j['tier'] == tier]

    if limit:
        stale = stale[:limit]

    stats = {
        'category': category,
        'cadence_days': cadence_days,
        'jurisdictions_found': len(stale),
        'jurisdictions_processed': 0,
        'tasks_queued': 0,
        'errors': 0,
        'dry_run': dry_run,
        'start_time': datetime.utcnow().isoformat()
    }

    for j in stale:
        try:
            priority = TIER_PRIORITY.get(j['tier'], TaskPriority.NORMAL)

            if dry_run:
                logger.info(f"[DRY RUN] Would queue {category} for {j['name']} (priority: {priority.name})")
            else:
                orchestrator.update_coverage(
                    fips_code=j['fips_code'],
                    data_category=category,
                    status=CoverageStatus.PARTIAL,
                    record_count=0,
                    source_url=f"refresh://{j['state']}/{category}",
                    notes=f"Queued for refresh {datetime.utcnow().isoformat()}"
                )

            stats['jurisdictions_processed'] += 1
            stats['tasks_queued'] += 1

        except Exception as e:
            logger.error(f"Error processing {j['name']}: {e}")
            stats['errors'] += 1

    stats['end_time'] = datetime.utcnow().isoformat()
    return stats


def run_scheduled_refresh(
    db: DatabaseManager,
    orchestrator: ScraperOrchestrator,
    dry_run: bool = False
):
    """
    Run scheduled refresh based on cadence configuration.

    Checks each category and refreshes those due for update.
    """
    logger.info("Starting scheduled refresh cycle")

    # Determine which categories need refresh today
    today_categories = []

    for category, cadence_days in REFRESH_CADENCE.items():
        if cadence_days == 1:
            # Daily - always refresh
            today_categories.append(category)
        elif cadence_days == 7:
            # Weekly - refresh on Sunday
            if datetime.utcnow().weekday() == 6:
                today_categories.append(category)
        elif cadence_days == 30:
            # Monthly - refresh on 1st of month
            if datetime.utcnow().day == 1:
                today_categories.append(category)

    if not today_categories:
        logger.info("No categories scheduled for refresh today")
        return

    logger.info(f"Categories scheduled for refresh: {', '.join(today_categories)}")

    all_stats = []
    for category in today_categories:
        stats = refresh_category(
            db=db,
            orchestrator=orchestrator,
            category=category,
            dry_run=dry_run
        )
        all_stats.append(stats)
        logger.info(f"Completed {category}: {stats['tasks_queued']} tasks queued")

    return all_stats


def main():
    parser = argparse.ArgumentParser(description='Coverage Refresh Scheduler')
    parser.add_argument(
        '--mode',
        choices=['check', 'refresh', 'schedule'],
        default='check',
        help='Operation mode'
    )
    parser.add_argument(
        '--category',
        choices=list(REFRESH_CADENCE.keys()),
        help='Specific category to refresh (for refresh mode)'
    )
    parser.add_argument(
        '--tier',
        type=int,
        choices=[1, 2, 3, 4],
        help='Only process specific tier'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit jurisdictions to process'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as daemon (for schedule mode)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("DataGod Coverage Refresh Scheduler")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    db = DatabaseManager()
    orchestrator = ScraperOrchestrator(db_manager=db)

    if args.mode == 'check':
        print("\n--- Checking Refresh Status ---\n")
        summary = check_refresh_status(db)

        print(f"Total Jurisdictions: {summary['total_jurisdictions']}")
        print(f"Total Stale: {summary['total_stale']}")
        print("\nBy Category:")
        print("-" * 60)

        for category, info in sorted(summary['categories'].items()):
            print(f"\n{category}:")
            print(f"  Cadence: Every {info['cadence_days']} day(s)")
            print(f"  Stale: {info['stale_count']} ({info['stale_percentage']}%)")
            print(f"  By Tier: T1={info['by_tier'][1]}, T2={info['by_tier'][2]}, "
                  f"T3={info['by_tier'][3]}, T4={info['by_tier'][4]}")

    elif args.mode == 'refresh':
        if not args.category:
            print("ERROR: --category required for refresh mode")
            return 1

        print(f"\n--- Refreshing {args.category} ---\n")

        stats = refresh_category(
            db=db,
            orchestrator=orchestrator,
            category=args.category,
            limit=args.limit,
            tier=args.tier,
            dry_run=args.dry_run
        )

        print(f"Category: {stats['category']}")
        print(f"Cadence: Every {stats['cadence_days']} days")
        print(f"Jurisdictions found: {stats['jurisdictions_found']}")
        print(f"Jurisdictions processed: {stats['jurisdictions_processed']}")
        print(f"Tasks queued: {stats['tasks_queued']}")
        print(f"Errors: {stats['errors']}")

        if args.dry_run:
            print("\n[DRY RUN - No changes made]")

    elif args.mode == 'schedule':
        print("\n--- Running Scheduled Refresh ---\n")

        if args.daemon:
            print("Running in daemon mode (Ctrl+C to stop)")
            while True:
                try:
                    run_scheduled_refresh(db, orchestrator, args.dry_run)
                    # Sleep until next check (every hour)
                    logger.info("Sleeping for 1 hour...")
                    time.sleep(3600)
                except KeyboardInterrupt:
                    print("\nShutdown requested")
                    break
        else:
            run_scheduled_refresh(db, orchestrator, args.dry_run)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
