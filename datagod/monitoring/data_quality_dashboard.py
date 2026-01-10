"""
Data Quality Dashboard

Provides comprehensive data quality metrics and visualizations.

Features:
- Coverage metrics by state/county
- Data freshness indicators
- Error log viewing
- API quota tracking
- Quality score calculations
"""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class FreshnessStatus(Enum):
    """Data freshness status levels"""
    FRESH = "fresh"           # Updated within 24 hours
    RECENT = "recent"         # Updated within 7 days
    STALE = "stale"           # Updated within 30 days
    OUTDATED = "outdated"     # Not updated in 30+ days
    UNKNOWN = "unknown"       # No update timestamp


class QualityGrade(Enum):
    """Data quality grades"""
    A = "A"  # 90-100%
    B = "B"  # 80-89%
    C = "C"  # 70-79%
    D = "D"  # 60-69%
    F = "F"  # Below 60%


@dataclass
class CoverageMetrics:
    """Coverage metrics for a jurisdiction"""
    jurisdiction_id: str
    jurisdiction_name: str
    total_records: int = 0
    property_records: int = 0
    deed_records: int = 0
    court_records: int = 0
    business_records: int = 0
    license_records: int = 0
    last_updated: Optional[datetime] = None
    data_sources: List[str] = field(default_factory=list)
    coverage_percent: float = 0.0

    @property
    def freshness_status(self) -> FreshnessStatus:
        """Get freshness status based on last update"""
        if not self.last_updated:
            return FreshnessStatus.UNKNOWN

        age = datetime.now() - self.last_updated
        if age < timedelta(hours=24):
            return FreshnessStatus.FRESH
        elif age < timedelta(days=7):
            return FreshnessStatus.RECENT
        elif age < timedelta(days=30):
            return FreshnessStatus.STALE
        else:
            return FreshnessStatus.OUTDATED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'jurisdiction_id': self.jurisdiction_id,
            'jurisdiction_name': self.jurisdiction_name,
            'total_records': self.total_records,
            'property_records': self.property_records,
            'deed_records': self.deed_records,
            'court_records': self.court_records,
            'business_records': self.business_records,
            'license_records': self.license_records,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'data_sources': self.data_sources,
            'coverage_percent': round(self.coverage_percent, 2),
            'freshness_status': self.freshness_status.value,
        }


@dataclass
class QualityScore:
    """Data quality score for a dataset"""
    completeness: float = 0.0  # Percentage of non-null fields
    accuracy: float = 0.0      # Validation pass rate
    consistency: float = 0.0   # Cross-source agreement rate
    timeliness: float = 0.0    # Data freshness score
    uniqueness: float = 0.0    # Deduplication rate

    @property
    def overall_score(self) -> float:
        """Calculate weighted overall score"""
        weights = {
            'completeness': 0.25,
            'accuracy': 0.30,
            'consistency': 0.20,
            'timeliness': 0.15,
            'uniqueness': 0.10,
        }
        return (
            self.completeness * weights['completeness'] +
            self.accuracy * weights['accuracy'] +
            self.consistency * weights['consistency'] +
            self.timeliness * weights['timeliness'] +
            self.uniqueness * weights['uniqueness']
        )

    @property
    def grade(self) -> QualityGrade:
        """Get letter grade based on overall score"""
        score = self.overall_score
        if score >= 90:
            return QualityGrade.A
        elif score >= 80:
            return QualityGrade.B
        elif score >= 70:
            return QualityGrade.C
        elif score >= 60:
            return QualityGrade.D
        else:
            return QualityGrade.F

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'completeness': round(self.completeness, 2),
            'accuracy': round(self.accuracy, 2),
            'consistency': round(self.consistency, 2),
            'timeliness': round(self.timeliness, 2),
            'uniqueness': round(self.uniqueness, 2),
            'overall_score': round(self.overall_score, 2),
            'grade': self.grade.value,
        }


@dataclass
class ErrorLogEntry:
    """An error log entry"""
    timestamp: datetime
    source: str
    error_type: str
    message: str
    jurisdiction: Optional[str] = None
    record_id: Optional[str] = None
    stack_trace: Optional[str] = None
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'error_type': self.error_type,
            'message': self.message,
            'jurisdiction': self.jurisdiction,
            'record_id': self.record_id,
            'stack_trace': self.stack_trace,
            'resolved': self.resolved,
        }


@dataclass
class QuotaStatus:
    """API quota status"""
    api_name: str
    used: int
    limit: int
    reset_at: Optional[datetime] = None

    @property
    def usage_percent(self) -> float:
        """Calculate usage percentage"""
        if self.limit == 0:
            return 0.0
        return (self.used / self.limit) * 100

    @property
    def remaining(self) -> int:
        """Calculate remaining quota"""
        return max(0, self.limit - self.used)

    @property
    def is_critical(self) -> bool:
        """Check if quota is critically low (>90% used)"""
        return self.usage_percent > 90

    @property
    def is_warning(self) -> bool:
        """Check if quota is in warning zone (>75% used)"""
        return self.usage_percent > 75

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'api_name': self.api_name,
            'used': self.used,
            'limit': self.limit,
            'remaining': self.remaining,
            'usage_percent': round(self.usage_percent, 2),
            'reset_at': self.reset_at.isoformat() if self.reset_at else None,
            'is_critical': self.is_critical,
            'is_warning': self.is_warning,
        }


class DataQualityDashboard:
    """
    Central dashboard for data quality metrics.

    Provides:
    - Coverage tracking by jurisdiction
    - Data quality scoring
    - Error logging and viewing
    - API quota monitoring
    - Trend analysis
    """

    # US States and territories
    ALL_STATES = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC', 'PR', 'VI', 'GU', 'AS', 'MP',  # DC and territories
    ]

    def __init__(self, retention_hours: int = 168):  # 1 week default
        """
        Initialize the dashboard.

        Args:
            retention_hours: How long to keep error logs
        """
        self._coverage: Dict[str, CoverageMetrics] = {}
        self._quality_scores: Dict[str, QualityScore] = {}
        self._error_logs: List[ErrorLogEntry] = []
        self._quota_status: Dict[str, QuotaStatus] = {}
        self._retention_hours = retention_hours
        self._historical_coverage: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)

    # ========== Coverage Management ==========

    def update_coverage(self, jurisdiction_id: str, jurisdiction_name: str,
                        record_counts: Dict[str, int],
                        data_sources: List[str] = None,
                        coverage_percent: float = None):
        """
        Update coverage metrics for a jurisdiction.

        Args:
            jurisdiction_id: Jurisdiction identifier (e.g., 'CA', 'CA-LOS_ANGELES')
            jurisdiction_name: Human-readable name
            record_counts: Dict with keys like 'property', 'deed', 'court', etc.
            data_sources: List of data source names
            coverage_percent: Optional explicit coverage percentage
        """
        metrics = CoverageMetrics(
            jurisdiction_id=jurisdiction_id,
            jurisdiction_name=jurisdiction_name,
            property_records=record_counts.get('property', 0),
            deed_records=record_counts.get('deed', 0),
            court_records=record_counts.get('court', 0),
            business_records=record_counts.get('business', 0),
            license_records=record_counts.get('license', 0),
            last_updated=datetime.now(),
            data_sources=data_sources or [],
        )
        metrics.total_records = (
            metrics.property_records +
            metrics.deed_records +
            metrics.court_records +
            metrics.business_records +
            metrics.license_records
        )

        if coverage_percent is not None:
            metrics.coverage_percent = coverage_percent
        else:
            # Calculate coverage based on categories with data
            categories_with_data = sum([
                1 if metrics.property_records > 0 else 0,
                1 if metrics.deed_records > 0 else 0,
                1 if metrics.court_records > 0 else 0,
                1 if metrics.business_records > 0 else 0,
                1 if metrics.license_records > 0 else 0,
            ])
            metrics.coverage_percent = (categories_with_data / 5) * 100

        self._coverage[jurisdiction_id] = metrics
        self._historical_coverage[jurisdiction_id].append(
            (datetime.now(), metrics.coverage_percent)
        )

        logger.debug(f"Updated coverage for {jurisdiction_id}: "
                    f"{metrics.total_records} records, {metrics.coverage_percent}% coverage")

    def get_coverage(self, jurisdiction_id: str) -> Optional[CoverageMetrics]:
        """Get coverage metrics for a jurisdiction"""
        return self._coverage.get(jurisdiction_id)

    def get_all_coverage(self) -> Dict[str, CoverageMetrics]:
        """Get all coverage metrics"""
        return self._coverage.copy()

    def get_state_coverage_summary(self) -> Dict[str, Any]:
        """
        Get coverage summary by state.

        Returns:
            Dict with state codes as keys and summary info as values
        """
        summary = {}
        for state in self.ALL_STATES:
            state_metrics = [
                m for k, m in self._coverage.items()
                if k == state or k.startswith(f"{state}-")
            ]

            if state_metrics:
                total_records = sum(m.total_records for m in state_metrics)
                avg_coverage = sum(m.coverage_percent for m in state_metrics) / len(state_metrics)
                freshness_counts = defaultdict(int)
                for m in state_metrics:
                    freshness_counts[m.freshness_status.value] += 1

                summary[state] = {
                    'county_count': len(state_metrics),
                    'total_records': total_records,
                    'avg_coverage_percent': round(avg_coverage, 2),
                    'freshness': dict(freshness_counts),
                    'has_coverage': True,
                }
            else:
                summary[state] = {
                    'county_count': 0,
                    'total_records': 0,
                    'avg_coverage_percent': 0.0,
                    'freshness': {},
                    'has_coverage': False,
                }

        return summary

    def get_coverage_heatmap_data(self) -> Dict[str, float]:
        """
        Get coverage data formatted for heatmap visualization.

        Returns:
            Dict mapping state codes to coverage percentages
        """
        summary = self.get_state_coverage_summary()
        return {
            state: data['avg_coverage_percent']
            for state, data in summary.items()
        }

    # ========== Quality Scoring ==========

    def update_quality_score(self, dataset_id: str,
                              completeness: float = None,
                              accuracy: float = None,
                              consistency: float = None,
                              timeliness: float = None,
                              uniqueness: float = None):
        """
        Update quality score for a dataset.

        Args:
            dataset_id: Identifier for the dataset
            completeness: Percentage of non-null required fields (0-100)
            accuracy: Validation pass rate (0-100)
            consistency: Cross-source agreement rate (0-100)
            timeliness: Data freshness score (0-100)
            uniqueness: Deduplication rate (0-100)
        """
        existing = self._quality_scores.get(dataset_id, QualityScore())

        self._quality_scores[dataset_id] = QualityScore(
            completeness=completeness if completeness is not None else existing.completeness,
            accuracy=accuracy if accuracy is not None else existing.accuracy,
            consistency=consistency if consistency is not None else existing.consistency,
            timeliness=timeliness if timeliness is not None else existing.timeliness,
            uniqueness=uniqueness if uniqueness is not None else existing.uniqueness,
        )

        logger.debug(f"Updated quality score for {dataset_id}: "
                    f"{self._quality_scores[dataset_id].overall_score}")

    def get_quality_score(self, dataset_id: str) -> Optional[QualityScore]:
        """Get quality score for a dataset"""
        return self._quality_scores.get(dataset_id)

    def get_all_quality_scores(self) -> Dict[str, QualityScore]:
        """Get all quality scores"""
        return self._quality_scores.copy()

    def get_quality_summary(self) -> Dict[str, Any]:
        """
        Get summary of quality scores across all datasets.

        Returns:
            Dict with aggregate statistics
        """
        if not self._quality_scores:
            return {
                'dataset_count': 0,
                'avg_score': 0.0,
                'grade_distribution': {},
                'lowest_scoring': [],
                'highest_scoring': [],
            }

        scores = list(self._quality_scores.values())
        grade_distribution = defaultdict(int)
        for score in scores:
            grade_distribution[score.grade.value] += 1

        sorted_datasets = sorted(
            self._quality_scores.items(),
            key=lambda x: x[1].overall_score
        )

        return {
            'dataset_count': len(scores),
            'avg_score': round(sum(s.overall_score for s in scores) / len(scores), 2),
            'grade_distribution': dict(grade_distribution),
            'lowest_scoring': [
                {'dataset': k, 'score': round(v.overall_score, 2)}
                for k, v in sorted_datasets[:5]
            ],
            'highest_scoring': [
                {'dataset': k, 'score': round(v.overall_score, 2)}
                for k, v in sorted_datasets[-5:][::-1]
            ],
        }

    # ========== Error Logging ==========

    def log_error(self, source: str, error_type: str, message: str,
                  jurisdiction: str = None, record_id: str = None,
                  stack_trace: str = None):
        """
        Log an error.

        Args:
            source: Source of the error (scraper name, service, etc.)
            error_type: Type of error
            message: Error message
            jurisdiction: Optional jurisdiction where error occurred
            record_id: Optional related record ID
            stack_trace: Optional stack trace
        """
        entry = ErrorLogEntry(
            timestamp=datetime.now(),
            source=source,
            error_type=error_type,
            message=message,
            jurisdiction=jurisdiction,
            record_id=record_id,
            stack_trace=stack_trace,
        )
        self._error_logs.append(entry)
        logger.debug(f"Logged error from {source}: {error_type} - {message[:100]}")

    def get_errors(self, source: str = None, error_type: str = None,
                   jurisdiction: str = None, since: datetime = None,
                   include_resolved: bool = False,
                   limit: int = 100) -> List[ErrorLogEntry]:
        """
        Get error log entries with optional filters.

        Args:
            source: Filter by source
            error_type: Filter by error type
            jurisdiction: Filter by jurisdiction
            since: Only include errors after this time
            include_resolved: Include resolved errors
            limit: Maximum entries to return

        Returns:
            List of matching error log entries
        """
        errors = self._error_logs

        if source:
            errors = [e for e in errors if e.source == source]
        if error_type:
            errors = [e for e in errors if e.error_type == error_type]
        if jurisdiction:
            errors = [e for e in errors if e.jurisdiction == jurisdiction]
        if since:
            errors = [e for e in errors if e.timestamp >= since]
        if not include_resolved:
            errors = [e for e in errors if not e.resolved]

        # Sort by timestamp descending (newest first)
        errors = sorted(errors, key=lambda e: e.timestamp, reverse=True)

        return errors[:limit]

    def resolve_error(self, index: int):
        """Mark an error as resolved by index"""
        if 0 <= index < len(self._error_logs):
            self._error_logs[index].resolved = True

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of errors.

        Returns:
            Dict with error statistics
        """
        unresolved = [e for e in self._error_logs if not e.resolved]
        by_source = defaultdict(int)
        by_type = defaultdict(int)
        by_jurisdiction = defaultdict(int)

        for error in unresolved:
            by_source[error.source] += 1
            by_type[error.error_type] += 1
            if error.jurisdiction:
                by_jurisdiction[error.jurisdiction] += 1

        return {
            'total_errors': len(self._error_logs),
            'unresolved_count': len(unresolved),
            'resolved_count': len(self._error_logs) - len(unresolved),
            'by_source': dict(by_source),
            'by_type': dict(by_type),
            'by_jurisdiction': dict(by_jurisdiction),
            'recent_errors': [e.to_dict() for e in self.get_errors(limit=10)],
        }

    def cleanup_old_errors(self):
        """Remove error logs older than retention period"""
        cutoff = datetime.now() - timedelta(hours=self._retention_hours)
        original_count = len(self._error_logs)
        self._error_logs = [e for e in self._error_logs if e.timestamp >= cutoff]
        removed = original_count - len(self._error_logs)
        if removed > 0:
            logger.info(f"Cleaned up {removed} old error logs")

    # ========== Quota Management ==========

    def update_quota(self, api_name: str, used: int, limit: int,
                     reset_at: datetime = None):
        """
        Update API quota status.

        Args:
            api_name: Name of the API
            used: Current usage count
            limit: Usage limit
            reset_at: When the quota resets
        """
        self._quota_status[api_name] = QuotaStatus(
            api_name=api_name,
            used=used,
            limit=limit,
            reset_at=reset_at,
        )

        status = self._quota_status[api_name]
        if status.is_critical:
            logger.warning(f"API quota critical for {api_name}: "
                          f"{status.usage_percent}% used")
        elif status.is_warning:
            logger.info(f"API quota warning for {api_name}: "
                       f"{status.usage_percent}% used")

    def get_quota(self, api_name: str) -> Optional[QuotaStatus]:
        """Get quota status for an API"""
        return self._quota_status.get(api_name)

    def get_all_quotas(self) -> Dict[str, QuotaStatus]:
        """Get all quota statuses"""
        return self._quota_status.copy()

    def get_quota_summary(self) -> Dict[str, Any]:
        """
        Get summary of API quotas.

        Returns:
            Dict with quota statistics
        """
        if not self._quota_status:
            return {
                'api_count': 0,
                'critical_count': 0,
                'warning_count': 0,
                'quotas': [],
            }

        quotas = list(self._quota_status.values())
        critical = [q for q in quotas if q.is_critical]
        warning = [q for q in quotas if q.is_warning and not q.is_critical]

        return {
            'api_count': len(quotas),
            'critical_count': len(critical),
            'warning_count': len(warning),
            'critical_apis': [q.api_name for q in critical],
            'warning_apis': [q.api_name for q in warning],
            'quotas': sorted(
                [q.to_dict() for q in quotas],
                key=lambda x: x['usage_percent'],
                reverse=True
            ),
        }

    # ========== Dashboard Export ==========

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get complete dashboard data for rendering.

        Returns:
            Dict with all dashboard components
        """
        coverage_summary = self.get_state_coverage_summary()
        states_with_coverage = sum(
            1 for s in coverage_summary.values() if s['has_coverage']
        )
        total_records = sum(s['total_records'] for s in coverage_summary.values())

        return {
            'timestamp': datetime.now().isoformat(),
            'overview': {
                'states_covered': states_with_coverage,
                'total_states': len(self.ALL_STATES),
                'coverage_percent': round(
                    (states_with_coverage / len(self.ALL_STATES)) * 100, 2
                ),
                'total_records': total_records,
                'jurisdictions_tracked': len(self._coverage),
            },
            'coverage': {
                'by_state': coverage_summary,
                'heatmap_data': self.get_coverage_heatmap_data(),
            },
            'quality': self.get_quality_summary(),
            'errors': self.get_error_summary(),
            'quotas': self.get_quota_summary(),
        }

    def export_to_json(self, filepath: str = None) -> str:
        """
        Export dashboard data to JSON.

        Args:
            filepath: Optional file path to write to

        Returns:
            JSON string
        """
        data = self.get_dashboard_data()
        json_str = json.dumps(data, indent=2, default=str)

        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
            logger.info(f"Exported dashboard data to {filepath}")

        return json_str

    def reset(self):
        """Reset all dashboard data"""
        self._coverage.clear()
        self._quality_scores.clear()
        self._error_logs.clear()
        self._quota_status.clear()
        self._historical_coverage.clear()
        logger.info("Dashboard data reset")


# Singleton instance
_dashboard_instance: Optional[DataQualityDashboard] = None


def get_dashboard() -> DataQualityDashboard:
    """Get the singleton dashboard instance"""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = DataQualityDashboard()
    return _dashboard_instance


# Convenience functions
def update_coverage(jurisdiction_id: str, jurisdiction_name: str,
                    record_counts: Dict[str, int], **kwargs):
    """Update coverage for a jurisdiction"""
    get_dashboard().update_coverage(jurisdiction_id, jurisdiction_name, record_counts, **kwargs)


def log_data_error(source: str, error_type: str, message: str, **kwargs):
    """Log a data error"""
    get_dashboard().log_error(source, error_type, message, **kwargs)


def get_dashboard_summary() -> Dict[str, Any]:
    """Get dashboard summary data"""
    return get_dashboard().get_dashboard_data()
