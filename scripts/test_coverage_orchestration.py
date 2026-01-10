#!/usr/bin/env python3
"""
Test Coverage Orchestration

Verifies that the coverage tracking system works correctly with the
populated jurisdictions database.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import DatabaseManager
from datagod.scrapers.scraper_orchestrator import ScraperOrchestrator, CoverageStatus


def test_coverage_system():
    """Test the coverage tracking system."""
    print("=" * 60)
    print("Testing Coverage Orchestration System")
    print("=" * 60)

    # Initialize database manager
    db = DatabaseManager()

    # Initialize orchestrator with db_manager
    orchestrator = ScraperOrchestrator(db_manager=db)

    # Test 1: Get coverage summary (should be empty initially)
    print("\n--- Test 1: Initial Coverage Summary ---")
    summary = orchestrator.get_coverage_summary()
    print(f"Coverage summary: {summary}")

    # Test 2: Update coverage for a sample county
    print("\n--- Test 2: Update Coverage for Sample Counties ---")

    # Los Angeles County, CA (FIPS: 06037)
    test_counties = [
        ("06037", "Los Angeles County, CA"),
        ("48201", "Harris County, TX"),  # Houston
        ("17031", "Cook County, IL"),     # Chicago
        ("04013", "Maricopa County, AZ"),  # Phoenix
    ]

    data_categories = ["court_records", "business_filings", "property_records"]

    for fips, name in test_counties:
        print(f"\nUpdating coverage for {name} (FIPS: {fips})")

        for category in data_categories:
            orchestrator.update_coverage(
                fips_code=fips,
                data_category=category,
                status=CoverageStatus.COMPLETE,
                record_count=1000,
                source_url=f"https://example.com/{fips}/{category}",
                notes=f"Test coverage entry for {name}"
            )
            print(f"  - {category}: COMPLETE")

    # Test 3: Get coverage summary after updates
    print("\n--- Test 3: Coverage Summary After Updates ---")
    summary = orchestrator.get_coverage_summary()
    print(f"Total jurisdictions: {summary.get('total_jurisdictions', 0)}")
    print(f"Jurisdictions with any coverage: {summary.get('with_coverage', 0)}")
    print(f"Coverage by category: {summary.get('by_category', {})}")

    # Test 4: Get coverage gaps
    print("\n--- Test 4: Coverage Gaps ---")

    # Get gaps for Texas
    tx_gaps = orchestrator.get_coverage_gaps(state="TX")
    print(f"Texas counties without coverage: {len(tx_gaps)} of 254")
    if tx_gaps:
        print(f"  Sample gaps: {[g['name'] for g in tx_gaps[:5]]}")

    # Get gaps for California
    ca_gaps = orchestrator.get_coverage_gaps(state="CA")
    print(f"California counties without coverage: {len(ca_gaps)} of 58")
    if ca_gaps:
        print(f"  Sample gaps: {[g['name'] for g in ca_gaps[:5]]}")

    # Test 5: Verify jurisdiction lookup by FIPS
    print("\n--- Test 5: Jurisdiction Lookup by FIPS ---")

    test_fips = ["06037", "48201", "36061", "12086"]  # LA, Houston, Manhattan, Miami-Dade

    for fips in test_fips:
        jurisdiction = db.get_jurisdiction_by_fips(fips)
        if jurisdiction:
            print(f"FIPS {fips}: {jurisdiction['name']} (pop: {jurisdiction.get('population', 'N/A')})")
        else:
            print(f"FIPS {fips}: Not found")

    # Test 6: List jurisdictions by state
    print("\n--- Test 6: Jurisdictions by State ---")

    state_counts = db.get_jurisdiction_count_by_state()
    for state in ["CA", "TX", "NY", "FL"]:
        jurisdictions = db.list_jurisdictions_by_state(state)
        count = state_counts.get(state, 0)
        print(f"{state}: {count} jurisdictions")
        if jurisdictions:
            print(f"  Sample: {', '.join([j.get('county') or j['name'] for j in jurisdictions[:3]])}")

    print("\n" + "=" * 60)
    print("Coverage Orchestration Tests Complete!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    test_coverage_system()
