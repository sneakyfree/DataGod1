"""
Coverage Monitor
Tracks and reports on data coverage across jurisdictions and data categories.

Provides:
- Real-time coverage statistics
- Gap analysis by state/county
- Data freshness tracking
- Coverage trend reports
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CoverageStatus(Enum):
    """Status of coverage for a jurisdiction/category combination."""

    COMPLETE = "complete"  # 100% coverage, data fresh
    PARTIAL = "partial"  # Some data available
    STALE = "stale"  # Data exists but outdated
    NO_DATA = "no_data"  # No data collected yet
    NO_PUBLIC_ACCESS = "no_access"  # Data not publicly available
    PAYWALL = "paywall"  # Available but requires payment
    AUTH_REQUIRED = "auth_required"  # Requires registration/login


class DataFreshness(Enum):
    """Data freshness categories."""

    REALTIME = "realtime"  # Updated within last hour
    DAILY = "daily"  # Updated within last day
    WEEKLY = "weekly"  # Updated within last week
    MONTHLY = "monthly"  # Updated within last month
    STALE = "stale"  # Over a month old
    NEVER = "never"  # Never collected


@dataclass
class JurisdictionCoverage:
    """Coverage information for a single jurisdiction."""

    fips_code: str
    name: str
    state: str
    level: str  # 'state', 'county', 'city', 'territory'
    population: int = 0
    categories: Dict[str, CoverageStatus] = field(default_factory=dict)
    record_counts: Dict[str, int] = field(default_factory=dict)
    last_updated: Dict[str, Optional[datetime]] = field(default_factory=dict)
    source_urls: Dict[str, str] = field(default_factory=dict)
    notes: Dict[str, str] = field(default_factory=dict)

    def coverage_percentage(self) -> float:
        """Calculate overall coverage percentage."""
        if not self.categories:
            return 0.0
        covered = sum(
            1
            for s in self.categories.values()
            if s in (CoverageStatus.COMPLETE, CoverageStatus.PARTIAL)
        )
        return (covered / len(self.categories)) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fips_code": self.fips_code,
            "name": self.name,
            "state": self.state,
            "level": self.level,
            "population": self.population,
            "coverage_percentage": self.coverage_percentage(),
            "categories": {k: v.value for k, v in self.categories.items()},
            "record_counts": self.record_counts,
            "last_updated": {
                k: v.isoformat() if v else None for k, v in self.last_updated.items()
            },
            "source_urls": self.source_urls,
            "notes": self.notes,
        }


@dataclass
class CategoryCoverage:
    """Coverage information for a data category across all jurisdictions."""

    category: str
    display_name: str
    description: str
    total_jurisdictions: int = 0
    covered_jurisdictions: int = 0
    partial_jurisdictions: int = 0
    no_access_jurisdictions: int = 0
    total_records: int = 0
    freshness: DataFreshness = DataFreshness.NEVER
    federal_sources: List[str] = field(default_factory=list)
    state_sources: Dict[str, str] = field(default_factory=dict)

    def coverage_percentage(self) -> float:
        """Calculate category coverage percentage."""
        if self.total_jurisdictions == 0:
            return 0.0
        return (
            (self.covered_jurisdictions + self.partial_jurisdictions * 0.5)
            / self.total_jurisdictions
        ) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "display_name": self.display_name,
            "description": self.description,
            "total_jurisdictions": self.total_jurisdictions,
            "covered_jurisdictions": self.covered_jurisdictions,
            "partial_jurisdictions": self.partial_jurisdictions,
            "no_access_jurisdictions": self.no_access_jurisdictions,
            "coverage_percentage": self.coverage_percentage(),
            "total_records": self.total_records,
            "freshness": self.freshness.value,
            "federal_sources": self.federal_sources,
            "state_source_count": len(self.state_sources),
        }


class CoverageMonitor:
    """
    Monitor and report on data coverage across jurisdictions and categories.

    Tracks:
    - Geographic coverage (states, counties, territories)
    - Data category coverage (15 categories)
    - Data freshness and update frequency
    - Coverage gaps and their reasons
    """

    # All data categories tracked
    DATA_CATEGORIES = {
        "court_records": "Court Records",
        "business_filings": "Business Filings",
        "professional_licenses": "Professional Licenses",
        "federal_sources": "Federal Sources",
        "news": "News & Media",
        "vital_records": "Vital Records",
        "criminal_records": "Criminal Records",
        "voter_records": "Voter Records",
        "regulatory_records": "Regulatory Records",
        "financial_records": "Financial Records",
        "asset_records": "Asset Records",
        "education_records": "Education Records",
        "employment_records": "Employment Records",
        "health_safety": "Health & Safety Records",
        "transportation": "Transportation Records",
    }

    # Target freshness by category
    FRESHNESS_TARGETS = {
        "court_records": timedelta(days=1),
        "criminal_records": timedelta(days=1),
        "business_filings": timedelta(days=7),
        "vital_records": timedelta(days=30),
        "voter_records": timedelta(days=7),
        "regulatory_records": timedelta(days=7),
        "financial_records": timedelta(days=7),
        "professional_licenses": timedelta(days=30),
        "asset_records": timedelta(days=30),
        "education_records": timedelta(days=30),
        "employment_records": timedelta(days=30),
        "health_safety": timedelta(days=30),
        "transportation": timedelta(days=7),
        "federal_sources": timedelta(days=1),
        "news": timedelta(hours=1),
    }

    # Total US jurisdictions
    TOTAL_COUNTIES = 3143
    TOTAL_STATES = 50
    TOTAL_TERRITORIES = 5  # PR, GU, VI, AS, MP
    TOTAL_DC = 1

    def __init__(self):
        """Initialize the coverage monitor."""
        self.jurisdiction_coverage: Dict[str, JurisdictionCoverage] = {}
        self.category_coverage: Dict[str, CategoryCoverage] = {}
        self.last_full_scan: Optional[datetime] = None

        # Initialize category coverage
        for cat_id, display_name in self.DATA_CATEGORIES.items():
            self.category_coverage[cat_id] = CategoryCoverage(
                category=cat_id,
                display_name=display_name,
                description=self._get_category_description(cat_id),
                total_jurisdictions=self.TOTAL_COUNTIES
                + self.TOTAL_STATES
                + self.TOTAL_TERRITORIES
                + self.TOTAL_DC,
            )

        logger.info("CoverageMonitor initialized")

    def _get_category_description(self, category: str) -> str:
        """Get description for a data category."""
        descriptions = {
            "court_records": "Civil, criminal, family, and probate court cases",
            "business_filings": "Corporate registrations, LLCs, partnerships, UCC filings",
            "professional_licenses": "Real estate, medical, legal, and other professional licenses",
            "federal_sources": "USPTO, SEC, FDIC, Census, BLS, FHFA data",
            "news": "Local and national news articles",
            "vital_records": "Death records, marriages, divorces, burial records",
            "criminal_records": "Sex offenders, inmates, warrants, most wanted",
            "voter_records": "Voter registration, campaign contributions, elections",
            "regulatory_records": "OSHA, SEC, EPA, CPSC violations and inspections",
            "financial_records": "Bankruptcy, nonprofits, tax liens, unclaimed property",
            "asset_records": "Aircraft, vessels, boats, vehicle registrations",
            "education_records": "Schools, colleges, teacher licenses",
            "employment_records": "Government salaries, federal awards, pensions",
            "health_safety": "Healthcare providers, hospitals, nursing homes",
            "transportation": "Vehicle recalls, CDL holders, safety ratings",
        }
        return descriptions.get(category, "")

    def update_jurisdiction_coverage(
        self,
        fips_code: str,
        category: str,
        status: CoverageStatus,
        record_count: int = 0,
        source_url: str = "",
        notes: str = "",
    ) -> None:
        """Update coverage status for a jurisdiction/category combination."""
        if fips_code not in self.jurisdiction_coverage:
            logger.warning(f"Unknown jurisdiction FIPS: {fips_code}")
            return

        jc = self.jurisdiction_coverage[fips_code]
        jc.categories[category] = status
        jc.record_counts[category] = record_count
        jc.last_updated[category] = datetime.now()
        if source_url:
            jc.source_urls[category] = source_url
        if notes:
            jc.notes[category] = notes

        # Update category coverage stats
        self._recalculate_category_coverage(category)

    def _recalculate_category_coverage(self, category: str) -> None:
        """Recalculate coverage statistics for a category."""
        if category not in self.category_coverage:
            return

        cc = self.category_coverage[category]

        complete = 0
        partial = 0
        no_access = 0
        total_records = 0

        for jc in self.jurisdiction_coverage.values():
            status = jc.categories.get(category)
            if status == CoverageStatus.COMPLETE:
                complete += 1
            elif status == CoverageStatus.PARTIAL:
                partial += 1
            elif status == CoverageStatus.NO_PUBLIC_ACCESS:
                no_access += 1

            total_records += jc.record_counts.get(category, 0)

        cc.covered_jurisdictions = complete
        cc.partial_jurisdictions = partial
        cc.no_access_jurisdictions = no_access
        cc.total_records = total_records

        # Determine overall freshness
        cc.freshness = self._calculate_category_freshness(category)

    def _calculate_category_freshness(self, category: str) -> DataFreshness:
        """Calculate overall freshness for a category."""
        now = datetime.now()
        target = self.FRESHNESS_TARGETS.get(category, timedelta(days=30))

        update_times = []
        for jc in self.jurisdiction_coverage.values():
            if category in jc.last_updated and jc.last_updated[category]:
                update_times.append(jc.last_updated[category])

        if not update_times:
            return DataFreshness.NEVER

        # Use median update time
        update_times.sort(reverse=True)
        median_idx = len(update_times) // 2
        median_update = update_times[median_idx]
        age = now - median_update

        if age < timedelta(hours=1):
            return DataFreshness.REALTIME
        elif age < timedelta(days=1):
            return DataFreshness.DAILY
        elif age < timedelta(weeks=1):
            return DataFreshness.WEEKLY
        elif age < timedelta(days=30):
            return DataFreshness.MONTHLY
        else:
            return DataFreshness.STALE

    def get_summary(self) -> Dict[str, Any]:
        """Get overall coverage summary."""
        total_jurisdictions = len(self.jurisdiction_coverage)
        total_categories = len(self.DATA_CATEGORIES)

        # Calculate overall coverage
        total_possible = total_jurisdictions * total_categories
        total_covered = 0
        total_partial = 0

        for jc in self.jurisdiction_coverage.values():
            for status in jc.categories.values():
                if status == CoverageStatus.COMPLETE:
                    total_covered += 1
                elif status == CoverageStatus.PARTIAL:
                    total_partial += 0.5

        overall_coverage = (
            (total_covered + total_partial) / total_possible * 100
            if total_possible > 0
            else 0
        )

        # Category summaries
        category_summaries = []
        for cat_id, cc in sorted(
            self.category_coverage.items(),
            key=lambda x: x[1].coverage_percentage(),
            reverse=True,
        ):
            category_summaries.append(
                {
                    "category": cat_id,
                    "display_name": cc.display_name,
                    "coverage_percentage": cc.coverage_percentage(),
                    "record_count": cc.total_records,
                    "freshness": cc.freshness.value,
                }
            )

        # State summaries
        state_coverage = self._get_state_coverage_summary()

        return {
            "timestamp": datetime.now().isoformat(),
            "overall": {
                "total_jurisdictions": total_jurisdictions,
                "total_categories": total_categories,
                "coverage_percentage": overall_coverage,
                "total_records": sum(
                    cc.total_records for cc in self.category_coverage.values()
                ),
            },
            "targets": {
                "counties": self.TOTAL_COUNTIES,
                "states": self.TOTAL_STATES,
                "territories": self.TOTAL_TERRITORIES,
                "dc": self.TOTAL_DC,
                "total": self.TOTAL_COUNTIES
                + self.TOTAL_STATES
                + self.TOTAL_TERRITORIES
                + self.TOTAL_DC,
            },
            "categories": category_summaries,
            "states": state_coverage,
        }

    def _get_state_coverage_summary(self) -> List[Dict[str, Any]]:
        """Get coverage summary by state."""
        state_stats: Dict[str, Dict[str, Any]] = {}

        for jc in self.jurisdiction_coverage.values():
            state = jc.state
            if state not in state_stats:
                state_stats[state] = {
                    "state": state,
                    "total_jurisdictions": 0,
                    "covered_count": 0,
                    "partial_count": 0,
                    "total_records": 0,
                    "population": 0,
                }

            stats = state_stats[state]
            stats["total_jurisdictions"] += 1
            stats["population"] += jc.population

            # Check if any category is covered
            has_complete = any(
                s == CoverageStatus.COMPLETE for s in jc.categories.values()
            )
            has_partial = any(
                s == CoverageStatus.PARTIAL for s in jc.categories.values()
            )

            if has_complete:
                stats["covered_count"] += 1
            elif has_partial:
                stats["partial_count"] += 1

            stats["total_records"] += sum(jc.record_counts.values())

        # Calculate percentages
        results = []
        for state, stats in state_stats.items():
            total = stats["total_jurisdictions"]
            covered = stats["covered_count"] + stats["partial_count"] * 0.5
            stats["coverage_percentage"] = (covered / total * 100) if total > 0 else 0
            results.append(stats)

        # Sort by coverage percentage descending
        results.sort(key=lambda x: x["coverage_percentage"], reverse=True)
        return results

    def get_gaps(self, min_population: int = 0) -> Dict[str, Any]:
        """
        Get coverage gaps.

        Args:
            min_population: Only include jurisdictions with this minimum population
        """
        gaps_by_category: Dict[str, List[Dict[str, Any]]] = {}
        gaps_by_state: Dict[str, List[Dict[str, Any]]] = {}

        for jc in self.jurisdiction_coverage.values():
            if jc.population < min_population:
                continue

            # Find categories with no coverage
            missing_categories = []
            for cat_id in self.DATA_CATEGORIES:
                status = jc.categories.get(cat_id, CoverageStatus.NO_DATA)
                if status in (CoverageStatus.NO_DATA, CoverageStatus.STALE):
                    missing_categories.append(cat_id)

                    # Add to gaps by category
                    if cat_id not in gaps_by_category:
                        gaps_by_category[cat_id] = []
                    gaps_by_category[cat_id].append(
                        {
                            "fips_code": jc.fips_code,
                            "name": jc.name,
                            "state": jc.state,
                            "population": jc.population,
                            "status": status.value,
                        }
                    )

            if missing_categories:
                # Add to gaps by state
                if jc.state not in gaps_by_state:
                    gaps_by_state[jc.state] = []
                gaps_by_state[jc.state].append(
                    {
                        "fips_code": jc.fips_code,
                        "name": jc.name,
                        "population": jc.population,
                        "missing_categories": missing_categories,
                        "missing_count": len(missing_categories),
                    }
                )

        # Sort gaps by population (prioritize high-population areas)
        for cat_id in gaps_by_category:
            gaps_by_category[cat_id].sort(key=lambda x: x["population"], reverse=True)

        for state in gaps_by_state:
            gaps_by_state[state].sort(key=lambda x: x["population"], reverse=True)

        return {
            "by_category": gaps_by_category,
            "by_state": gaps_by_state,
            "summary": {
                "total_gaps": sum(len(g) for g in gaps_by_category.values()),
                "categories_with_gaps": len(gaps_by_category),
                "states_with_gaps": len(gaps_by_state),
            },
        }

    def get_freshness_report(self) -> Dict[str, Any]:
        """Get data freshness report."""
        now = datetime.now()

        stale_data: List[Dict[str, Any]] = []
        freshness_by_category: Dict[str, Dict[str, int]] = {}

        for cat_id in self.DATA_CATEGORIES:
            freshness_by_category[cat_id] = {
                "realtime": 0,
                "daily": 0,
                "weekly": 0,
                "monthly": 0,
                "stale": 0,
                "never": 0,
            }

        for jc in self.jurisdiction_coverage.values():
            for cat_id, last_update in jc.last_updated.items():
                if last_update is None:
                    freshness_by_category[cat_id]["never"] += 1
                    continue

                age = now - last_update
                target = self.FRESHNESS_TARGETS.get(cat_id, timedelta(days=30))

                if age < timedelta(hours=1):
                    freshness_by_category[cat_id]["realtime"] += 1
                elif age < timedelta(days=1):
                    freshness_by_category[cat_id]["daily"] += 1
                elif age < timedelta(weeks=1):
                    freshness_by_category[cat_id]["weekly"] += 1
                elif age < timedelta(days=30):
                    freshness_by_category[cat_id]["monthly"] += 1
                else:
                    freshness_by_category[cat_id]["stale"] += 1

                    # Add to stale data list if past target
                    if age > target:
                        stale_data.append(
                            {
                                "fips_code": jc.fips_code,
                                "name": jc.name,
                                "state": jc.state,
                                "category": cat_id,
                                "last_updated": last_update.isoformat(),
                                "age_days": age.days,
                                "target_days": target.days,
                            }
                        )

        # Sort stale data by age
        stale_data.sort(key=lambda x: x["age_days"], reverse=True)

        return {
            "timestamp": now.isoformat(),
            "by_category": freshness_by_category,
            "stale_data": stale_data[:100],  # Top 100 most stale
            "total_stale": len(stale_data),
        }

    def generate_report(self, format: str = "json") -> str:
        """
        Generate a comprehensive coverage report.

        Args:
            format: 'json' or 'markdown'
        """
        summary = self.get_summary()
        gaps = self.get_gaps(min_population=10000)  # Focus on larger jurisdictions
        freshness = self.get_freshness_report()

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "gaps": gaps,
            "freshness": freshness,
        }

        if format == "json":
            return json.dumps(report, indent=2, default=str)
        elif format == "markdown":
            return self._format_markdown_report(report)
        else:
            return json.dumps(report, indent=2, default=str)

    def _format_markdown_report(self, report: Dict[str, Any]) -> str:
        """Format report as Markdown."""
        lines = [
            "# DataGod Coverage Report",
            f"Generated: {report['generated_at']}",
            "",
            "## Overall Summary",
            "",
            f"- **Total Jurisdictions:** {report['summary']['overall']['total_jurisdictions']}",
            f"- **Coverage Percentage:** {report['summary']['overall']['coverage_percentage']:.1f}%",
            f"- **Total Records:** {report['summary']['overall']['total_records']:,}",
            "",
            "### Coverage Targets",
            f"- Counties: {report['summary']['targets']['counties']:,}",
            f"- States: {report['summary']['targets']['states']}",
            f"- Territories: {report['summary']['targets']['territories']}",
            f"- DC: {report['summary']['targets']['dc']}",
            "",
            "## Category Coverage",
            "",
            "| Category | Coverage | Records | Freshness |",
            "|----------|----------|---------|-----------|",
        ]

        for cat in report["summary"]["categories"]:
            lines.append(
                f"| {cat['display_name']} | {cat['coverage_percentage']:.1f}% | "
                f"{cat['record_count']:,} | {cat['freshness']} |"
            )

        lines.extend(
            [
                "",
                "## Coverage Gaps",
                "",
                f"- **Total Gaps:** {report['gaps']['summary']['total_gaps']:,}",
                f"- **Categories with Gaps:** {report['gaps']['summary']['categories_with_gaps']}",
                f"- **States with Gaps:** {report['gaps']['summary']['states_with_gaps']}",
                "",
                "## Data Freshness",
                "",
                f"- **Stale Records:** {report['freshness']['total_stale']:,}",
                "",
            ]
        )

        return "\n".join(lines)


# Convenience functions
def get_coverage_monitor() -> CoverageMonitor:
    """Get or create coverage monitor singleton."""
    if not hasattr(get_coverage_monitor, "_instance"):
        get_coverage_monitor._instance = CoverageMonitor()
    return get_coverage_monitor._instance


def generate_coverage_report(format: str = "json") -> str:
    """Generate coverage report."""
    monitor = get_coverage_monitor()
    return monitor.generate_report(format)
