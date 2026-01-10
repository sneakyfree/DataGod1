#!/usr/bin/env python3
"""
Sync Coverage Data to Data Quality Dashboard

Bridges the coverage data stored in the database with the
in-memory DataQualityDashboard for monitoring and visualization.
"""

import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import DatabaseManager
from datagod.monitoring.data_quality_dashboard import (
    DataQualityDashboard,
    CoverageMetrics,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_coverage_to_dashboard(db: DatabaseManager, dashboard: DataQualityDashboard):
    """
    Sync jurisdiction coverage from database to dashboard.
    """
    logger.info("Syncing coverage data to dashboard...")

    # Get all jurisdictions with coverage
    try:
        with db.get_session() as session:
            from datagod.models import Jurisdiction

            jurisdictions = session.query(Jurisdiction).filter(
                Jurisdiction.fips_code.isnot(None)
            ).all()

            synced = 0
            for j in jurisdictions:
                # Extract coverage data from metadata
                metadata = j.jurisdiction_metadata or {}
                coverage_data = metadata.get('coverage', {})

                if not coverage_data:
                    continue

                # Build record counts dict by category
                record_counts = {}
                categories_covered = 0

                for category, cat_data in coverage_data.items():
                    if isinstance(cat_data, dict):
                        count = cat_data.get('record_count', 0)
                        # Map to dashboard expected keys
                        if 'property' in category:
                            record_counts['property'] = record_counts.get('property', 0) + count
                        elif 'court' in category:
                            record_counts['court'] = record_counts.get('court', 0) + count
                        elif 'business' in category:
                            record_counts['business'] = record_counts.get('business', 0) + count
                        elif 'license' in category:
                            record_counts['license'] = record_counts.get('license', 0) + count
                        else:
                            record_counts['other'] = record_counts.get('other', 0) + count

                        if cat_data.get('status') in ['partial', 'complete']:
                            categories_covered += 1

                # Update dashboard using correct method signature
                # Use state-based ID format: STATE or STATE-COUNTY_NAME
                coverage_pct = (categories_covered / 14) * 100 if categories_covered > 0 else 0
                county_name = j.name.replace(' ', '_').upper()
                jurisdiction_id = f"{j.state}-{county_name}" if j.name else j.state

                dashboard.update_coverage(
                    jurisdiction_id=jurisdiction_id,
                    jurisdiction_name=j.name,
                    record_counts=record_counts,
                    data_sources=[j.state],
                    coverage_percent=coverage_pct
                )
                synced += 1

            logger.info(f"Synced {synced} jurisdictions to dashboard")
            return synced

    except Exception as e:
        logger.error(f"Error syncing coverage: {e}")
        import traceback
        traceback.print_exc()
        return 0


def create_quality_scores(db: DatabaseManager, dashboard: DataQualityDashboard):
    """
    Create quality scores based on coverage data.
    """
    logger.info("Creating quality scores...")

    # Get state list from dashboard
    states = DataQualityDashboard.ALL_STATES

    scores_created = 0
    for state in states:
        # Get jurisdictions for this state
        jurisdictions = db.list_jurisdictions_by_state(state)
        total = len(jurisdictions)

        if total == 0:
            continue

        # Count covered jurisdictions
        covered = 0
        for j in jurisdictions:
            metadata = j.get('jurisdiction_metadata', {}) or {}
            if metadata.get('coverage'):
                covered += 1

        # Calculate score components
        coverage_pct = (covered / total) * 100 if total > 0 else 0

        # Update quality score using correct method signature
        dashboard.update_quality_score(
            dataset_id=f"state_{state}",
            completeness=coverage_pct,
            accuracy=95.0,  # Default accuracy
            consistency=90.0,  # Default consistency
            timeliness=85.0,  # Default timeliness
        )
        scores_created += 1

    logger.info(f"Created {scores_created} quality scores")
    return scores_created


def main():
    print("=" * 60)
    print("DataGod Coverage to Dashboard Sync")
    print("=" * 60)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print()

    # Initialize
    db = DatabaseManager()
    dashboard = DataQualityDashboard()

    # Sync coverage
    synced = sync_coverage_to_dashboard(db, dashboard)
    print(f"Jurisdictions synced: {synced}")

    # Create quality scores
    scores = create_quality_scores(db, dashboard)
    print(f"Quality scores created: {scores}")

    # Get dashboard summary
    print("\n--- Dashboard Summary ---")
    data = dashboard.get_dashboard_data()

    overview = data.get('overview', {})
    print(f"States with coverage: {overview.get('states_covered', 0)}/{overview.get('total_states', 0)}")
    print(f"Jurisdictions tracked: {overview.get('jurisdictions_tracked', 0)}")
    print(f"Coverage percentage: {overview.get('coverage_percent', 0):.1f}%")
    print(f"Total records: {overview.get('total_records', 0)}")

    quality = data.get('quality', {})
    print(f"Quality datasets scored: {quality.get('total_datasets', 0)}")
    print(f"Average quality score: {quality.get('average_score', 0):.1f}")

    # State coverage summary
    state_summary = dashboard.get_state_coverage_summary()
    states_with_data = sum(1 for s in state_summary.values() if s.get('has_coverage'))
    print(f"\nStates with coverage data: {states_with_data}")

    # Show top states by coverage
    states_with_counties = {k: v for k, v in state_summary.items() if v.get('has_coverage')}
    if states_with_counties:
        print("\nTop 10 States by Jurisdiction Count:")
        sorted_states = sorted(
            states_with_counties.items(),
            key=lambda x: x[1].get('county_count', 0),
            reverse=True
        )[:10]
        for state, info in sorted_states:
            print(f"  {state}: {info.get('county_count', 0)} counties, {info.get('avg_coverage_percent', 0):.1f}% avg coverage")

    print("\n" + "=" * 60)
    print("Sync complete!")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
