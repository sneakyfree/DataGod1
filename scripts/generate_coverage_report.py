#!/usr/bin/env python3
"""
Coverage Report Generator

Generates comprehensive coverage reports for DataGod platform.
Outputs reports in various formats (text, JSON, HTML).

Reports include:
- Overall coverage statistics
- Coverage by state/tier
- Coverage by data category
- Gap analysis
- Progress tracking
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import DatabaseManager


# Data categories
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

# State tiers
STATE_TIERS = {
    1: ['CA', 'TX', 'FL', 'NY'],
    2: ['PA', 'IL', 'OH', 'GA', 'NC', 'MI', 'NJ', 'VA', 'WA', 'AZ',
        'MA', 'TN', 'IN', 'MO', 'MD', 'WI', 'CO', 'MN', 'SC', 'AL', 'LA'],
    4: ['PR', 'GU', 'VI', 'AS', 'MP'],
}


def get_coverage_data(db: DatabaseManager) -> Dict[str, Any]:
    """
    Collect all coverage data from database.
    """
    data = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'summary': db.get_coverage_summary(),
        'by_state': {},
        'by_category': {},
        'by_tier': {1: {}, 2: {}, 3: {}, 4: {}},
        'jurisdictions': []
    }

    # Get jurisdiction details
    try:
        with db.get_session() as session:
            from datagod.models import Jurisdiction

            jurisdictions = session.query(Jurisdiction).filter(
                Jurisdiction.fips_code.isnot(None)
            ).order_by(Jurisdiction.state, Jurisdiction.name).all()

            for j in jurisdictions:
                metadata = j.jurisdiction_metadata or {}
                coverage = metadata.get('coverage', {})

                # Determine tier
                tier = 3  # default
                if j.state in STATE_TIERS.get(1, []):
                    tier = 1
                elif j.state in STATE_TIERS.get(2, []):
                    tier = 2
                elif j.state in STATE_TIERS.get(4, []):
                    tier = 4

                j_data = {
                    'id': j.id,
                    'name': j.name,
                    'state': j.state,
                    'fips_code': j.fips_code,
                    'population': j.population,
                    'tier': tier,
                    'categories_covered': len(coverage),
                    'categories_complete': sum(
                        1 for c in coverage.values()
                        if c.get('status') == 'complete'
                    ),
                    'coverage': coverage
                }

                data['jurisdictions'].append(j_data)

                # Aggregate by state
                if j.state not in data['by_state']:
                    data['by_state'][j.state] = {
                        'total': 0,
                        'with_any_coverage': 0,
                        'complete': 0,
                        'tier': tier,
                        'counties': []
                    }

                data['by_state'][j.state]['total'] += 1
                if coverage:
                    data['by_state'][j.state]['with_any_coverage'] += 1
                if j_data['categories_complete'] == len(DATA_CATEGORIES):
                    data['by_state'][j.state]['complete'] += 1
                data['by_state'][j.state]['counties'].append(j.name)

                # Aggregate by tier
                if 'total' not in data['by_tier'][tier]:
                    data['by_tier'][tier] = {'total': 0, 'with_coverage': 0, 'complete': 0}
                data['by_tier'][tier]['total'] += 1
                if coverage:
                    data['by_tier'][tier]['with_coverage'] += 1

                # Aggregate by category
                for cat in DATA_CATEGORIES:
                    if cat not in data['by_category']:
                        data['by_category'][cat] = {
                            'total': 0,
                            'covered': 0,
                            'complete': 0,
                            'partial': 0,
                            'no_data': 0
                        }

                    data['by_category'][cat]['total'] += 1
                    cat_status = coverage.get(cat, {}).get('status', 'no_data')

                    if cat_status == 'complete':
                        data['by_category'][cat]['complete'] += 1
                        data['by_category'][cat]['covered'] += 1
                    elif cat_status == 'partial':
                        data['by_category'][cat]['partial'] += 1
                        data['by_category'][cat]['covered'] += 1
                    else:
                        data['by_category'][cat]['no_data'] += 1

    except Exception as e:
        data['error'] = str(e)

    return data


def generate_text_report(data: Dict[str, Any]) -> str:
    """
    Generate plain text report.
    """
    lines = []
    lines.append("=" * 70)
    lines.append("DATAGOD COVERAGE REPORT")
    lines.append("=" * 70)
    lines.append(f"Generated: {data['generated_at']}")
    lines.append("")

    # Summary
    summary = data['summary']
    lines.append("-" * 70)
    lines.append("OVERALL SUMMARY")
    lines.append("-" * 70)
    lines.append(f"Total Jurisdictions:     {summary.get('total_jurisdictions', 0):,}")
    lines.append(f"With FIPS Codes:         {summary.get('jurisdictions_with_fips', 0):,}")
    lines.append(f"With Any Coverage:       {summary.get('jurisdictions_with_coverage', 0):,}")
    lines.append(f"Coverage Percentage:     {summary.get('coverage_percentage', 0):.1f}%")
    lines.append("")

    # By Tier
    lines.append("-" * 70)
    lines.append("COVERAGE BY TIER")
    lines.append("-" * 70)
    lines.append(f"{'Tier':<10} {'Total':<10} {'Covered':<10} {'Percentage':<10}")
    lines.append("-" * 40)

    for tier in [1, 2, 3, 4]:
        tier_data = data['by_tier'].get(tier, {})
        total = tier_data.get('total', 0)
        covered = tier_data.get('with_coverage', 0)
        pct = (covered / max(total, 1)) * 100
        tier_names = {1: 'Tier 1 (Critical)', 2: 'Tier 2 (High)',
                      3: 'Tier 3 (Normal)', 4: 'Tier 4 (Territories)'}
        lines.append(f"{tier_names.get(tier, f'Tier {tier}'):<20} {total:<10} {covered:<10} {pct:.1f}%")
    lines.append("")

    # By State (top 10)
    lines.append("-" * 70)
    lines.append("TOP 10 STATES BY COVERAGE")
    lines.append("-" * 70)
    lines.append(f"{'State':<8} {'Total':<10} {'Covered':<10} {'Percentage':<10}")
    lines.append("-" * 38)

    state_coverage = []
    for state, state_data in data['by_state'].items():
        total = state_data['total']
        covered = state_data['with_any_coverage']
        pct = (covered / max(total, 1)) * 100
        state_coverage.append((state, total, covered, pct))

    state_coverage.sort(key=lambda x: -x[3])  # Sort by percentage descending

    for state, total, covered, pct in state_coverage[:10]:
        lines.append(f"{state:<8} {total:<10} {covered:<10} {pct:.1f}%")
    lines.append("")

    # By Category
    lines.append("-" * 70)
    lines.append("COVERAGE BY DATA CATEGORY")
    lines.append("-" * 70)
    lines.append(f"{'Category':<25} {'Covered':<10} {'Complete':<10} {'Partial':<10} {'None':<10}")
    lines.append("-" * 65)

    for cat in DATA_CATEGORIES:
        cat_data = data['by_category'].get(cat, {})
        covered = cat_data.get('covered', 0)
        complete = cat_data.get('complete', 0)
        partial = cat_data.get('partial', 0)
        no_data = cat_data.get('no_data', 0)
        lines.append(f"{cat:<25} {covered:<10} {complete:<10} {partial:<10} {no_data:<10}")
    lines.append("")

    # Gap Analysis
    lines.append("-" * 70)
    lines.append("GAP ANALYSIS - LARGEST GAPS")
    lines.append("-" * 70)

    # Find states with lowest coverage
    low_coverage_states = sorted(state_coverage, key=lambda x: x[3])[:5]
    lines.append("\nStates with Lowest Coverage:")
    for state, total, covered, pct in low_coverage_states:
        lines.append(f"  {state}: {pct:.1f}% ({covered}/{total} jurisdictions)")

    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("=" * 70)

    return "\n".join(lines)


def generate_html_report(data: Dict[str, Any]) -> str:
    """
    Generate HTML report.
    """
    summary = data['summary']

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>DataGod Coverage Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #4CAF50; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #4CAF50; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .progress-bar {{ background: #e0e0e0; border-radius: 4px; height: 20px; overflow: hidden; }}
        .progress-fill {{ background: #4CAF50; height: 100%; transition: width 0.3s; }}
        .timestamp {{ color: #999; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>DataGod Coverage Report</h1>
        <p class="timestamp">Generated: {data['generated_at']}</p>

        <div class="summary">
            <div class="stat-card">
                <div class="stat-value">{summary.get('total_jurisdictions', 0):,}</div>
                <div class="stat-label">Total Jurisdictions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary.get('jurisdictions_with_coverage', 0):,}</div>
                <div class="stat-label">With Coverage</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary.get('coverage_percentage', 0):.1f}%</div>
                <div class="stat-label">Coverage Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(data['by_state'])}</div>
                <div class="stat-label">States/Territories</div>
            </div>
        </div>

        <h2>Coverage by Tier</h2>
        <table>
            <tr><th>Tier</th><th>Total</th><th>Covered</th><th>Progress</th></tr>
"""

    tier_names = {1: 'Tier 1 (Critical)', 2: 'Tier 2 (High)',
                  3: 'Tier 3 (Normal)', 4: 'Tier 4 (Territories)'}

    for tier in [1, 2, 3, 4]:
        tier_data = data['by_tier'].get(tier, {})
        total = tier_data.get('total', 0)
        covered = tier_data.get('with_coverage', 0)
        pct = (covered / max(total, 1)) * 100
        html += f"""
            <tr>
                <td>{tier_names.get(tier, f'Tier {tier}')}</td>
                <td>{total:,}</td>
                <td>{covered:,}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {pct}%"></div>
                    </div>
                    {pct:.1f}%
                </td>
            </tr>
"""

    html += """
        </table>

        <h2>Coverage by Data Category</h2>
        <table>
            <tr><th>Category</th><th>Complete</th><th>Partial</th><th>No Data</th><th>Progress</th></tr>
"""

    for cat in DATA_CATEGORIES:
        cat_data = data['by_category'].get(cat, {})
        total = cat_data.get('total', 0)
        covered = cat_data.get('covered', 0)
        complete = cat_data.get('complete', 0)
        partial = cat_data.get('partial', 0)
        no_data = cat_data.get('no_data', 0)
        pct = (covered / max(total, 1)) * 100

        html += f"""
            <tr>
                <td>{cat.replace('_', ' ').title()}</td>
                <td>{complete:,}</td>
                <td>{partial:,}</td>
                <td>{no_data:,}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {pct}%"></div>
                    </div>
                    {pct:.1f}%
                </td>
            </tr>
"""

    html += """
        </table>

        <h2>Coverage by State</h2>
        <table>
            <tr><th>State</th><th>Tier</th><th>Counties</th><th>Covered</th><th>Progress</th></tr>
"""

    # Sort states by coverage percentage
    state_items = []
    for state, state_data in data['by_state'].items():
        total = state_data['total']
        covered = state_data['with_any_coverage']
        pct = (covered / max(total, 1)) * 100
        state_items.append((state, state_data, total, covered, pct))

    state_items.sort(key=lambda x: -x[4])

    for state, state_data, total, covered, pct in state_items:
        tier = state_data.get('tier', 3)
        html += f"""
            <tr>
                <td>{state}</td>
                <td>Tier {tier}</td>
                <td>{total:,}</td>
                <td>{covered:,}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {pct}%"></div>
                    </div>
                    {pct:.1f}%
                </td>
            </tr>
"""

    html += """
        </table>
    </div>
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description='Generate Coverage Report')
    parser.add_argument(
        '--format',
        choices=['text', 'json', 'html', 'all'],
        default='text',
        help='Output format'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: stdout for text, reports/ for files)'
    )

    args = parser.parse_args()

    # Initialize database
    db = DatabaseManager()

    # Collect data
    print("Collecting coverage data...", file=sys.stderr)
    data = get_coverage_data(db)
    print(f"Found {len(data['jurisdictions'])} jurisdictions", file=sys.stderr)

    # Generate reports
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

    if args.format in ['text', 'all']:
        report = generate_text_report(data)
        if args.output and args.format == 'text':
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"Text report saved to: {args.output}", file=sys.stderr)
        elif args.format == 'all':
            output_path = f"reports/coverage_report_{timestamp}.txt"
            os.makedirs('reports', exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report)
            print(f"Text report saved to: {output_path}", file=sys.stderr)
        else:
            print(report)

    if args.format in ['json', 'all']:
        # Remove jurisdiction details for JSON (too large)
        json_data = {k: v for k, v in data.items() if k != 'jurisdictions'}
        json_data['jurisdiction_count'] = len(data['jurisdictions'])

        if args.output and args.format == 'json':
            with open(args.output, 'w') as f:
                json.dump(json_data, f, indent=2)
            print(f"JSON report saved to: {args.output}", file=sys.stderr)
        elif args.format == 'all':
            output_path = f"reports/coverage_report_{timestamp}.json"
            os.makedirs('reports', exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            print(f"JSON report saved to: {output_path}", file=sys.stderr)
        else:
            print(json.dumps(json_data, indent=2))

    if args.format in ['html', 'all']:
        report = generate_html_report(data)
        if args.output and args.format == 'html':
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"HTML report saved to: {args.output}", file=sys.stderr)
        elif args.format == 'all':
            output_path = f"reports/coverage_report_{timestamp}.html"
            os.makedirs('reports', exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report)
            print(f"HTML report saved to: {output_path}", file=sys.stderr)
        else:
            print(report)

    return 0


if __name__ == '__main__':
    sys.exit(main())
