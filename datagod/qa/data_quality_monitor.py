"""
DataGod Data Quality Monitoring Module

Comprehensive data quality tracking and reporting for public records data.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class QualityDimension(str, Enum):
    """Data quality dimensions."""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"


class QualityStatus(str, Enum):
    """Quality status levels."""
    EXCELLENT = "excellent"  # >= 95%
    GOOD = "good"           # >= 80%
    FAIR = "fair"           # >= 60%
    POOR = "poor"           # < 60%


@dataclass
class QualityMetric:
    """Individual quality metric result."""
    dimension: QualityDimension
    score: float  # 0-100
    status: QualityStatus
    issues_found: int
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "status": self.status.value,
            "issues_found": self.issues_found,
            "details": self.details,
            "recommendations": self.recommendations,
        }


@dataclass  
class QualityIssue:
    """Represents a data quality issue."""
    issue_id: str
    dimension: QualityDimension
    severity: str  # 'critical', 'high', 'medium', 'low'
    table: str
    column: Optional[str]
    description: str
    affected_records: int
    example_values: List[Any] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "dimension": self.dimension.value,
            "severity": self.severity,
            "table": self.table,
            "column": self.column,
            "description": self.description,
            "affected_records": self.affected_records,
            "example_values": self.example_values[:5],
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class QualityReport:
    """Complete data quality report."""
    report_id: str
    generated_at: datetime
    overall_score: float
    overall_status: QualityStatus
    metrics: Dict[QualityDimension, QualityMetric]
    issues: List[QualityIssue]
    trends: Dict[str, List[float]]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "overall_score": self.overall_score,
            "overall_status": self.overall_status.value,
            "metrics": {k.value: v.to_dict() for k, v in self.metrics.items()},
            "issues": [i.to_dict() for i in self.issues],
            "trends": self.trends,
            "recommendations": self.recommendations,
        }


@dataclass
class ConsistencyRule:
    """Rule for cross-field consistency checks."""
    name: str
    description: str
    field1: str
    field2: str
    rule_type: str  # 'equal', 'greater', 'less', 'sum', 'custom'
    expected_value: Optional[Any] = None


@dataclass
class QualityConfig:
    """Configuration for quality monitoring."""
    required_fields: List[str] = field(default_factory=lambda: [
        'id', 'jurisdiction_id', 'record_type', 'created_at'
    ])
    timeliness_sla_hours: int = 24
    freshness_threshold_days: int = 7
    duplicate_check_fields: List[str] = field(default_factory=list)
    value_ranges: Dict[str, tuple] = field(default_factory=dict)
    format_patterns: Dict[str, str] = field(default_factory=dict)


class DataQualityMonitor:
    """
    Comprehensive data quality tracking and monitoring.
    
    Calculates quality metrics across multiple dimensions:
    - Completeness: Non-null required fields
    - Accuracy: Data correctness (spot-checks)
    - Consistency: Cross-field rule adherence
    - Timeliness: Data freshness
    - Validity: Format and range validation
    - Uniqueness: Duplicate detection
    """
    
    DIMENSIONS = list(QualityDimension)
    
    def __init__(self, config: Optional[QualityConfig] = None):
        """Initialize the quality monitor."""
        self.config = config or QualityConfig()
        self.consistency_rules: List[ConsistencyRule] = []
        self._issue_history: List[QualityIssue] = []
        self._score_history: Dict[str, List[Tuple[datetime, float]]] = {}
        logger.info("DataQualityMonitor initialized")
    
    def generate_report(self, data: pd.DataFrame, table_name: str = "records") -> QualityReport:
        """
        Generate a comprehensive quality report.
        
        Args:
            data: DataFrame to analyze
            table_name: Name of the table/dataset
            
        Returns:
            Complete quality report
        """
        report_id = self._generate_id(f"report_{table_name}")
        generated_at = datetime.utcnow()
        issues: List[QualityIssue] = []
        metrics: Dict[QualityDimension, QualityMetric] = {}
        
        # Calculate each dimension
        metrics[QualityDimension.COMPLETENESS] = self.calculate_completeness(data, table_name)
        issues.extend(self._get_completeness_issues(data, table_name))
        
        metrics[QualityDimension.ACCURACY] = self.calculate_accuracy(data, table_name)
        
        metrics[QualityDimension.CONSISTENCY] = self.calculate_consistency(data, table_name)
        issues.extend(self._get_consistency_issues(data, table_name))
        
        metrics[QualityDimension.TIMELINESS] = self.calculate_timeliness(data, table_name)
        
        metrics[QualityDimension.VALIDITY] = self.calculate_validity(data, table_name)
        issues.extend(self._get_validity_issues(data, table_name))
        
        metrics[QualityDimension.UNIQUENESS] = self.calculate_uniqueness(data, table_name)
        issues.extend(self._get_uniqueness_issues(data, table_name))
        
        # Calculate overall score (weighted average)
        weights = {
            QualityDimension.COMPLETENESS: 0.25,
            QualityDimension.ACCURACY: 0.20,
            QualityDimension.CONSISTENCY: 0.15,
            QualityDimension.TIMELINESS: 0.15,
            QualityDimension.VALIDITY: 0.15,
            QualityDimension.UNIQUENESS: 0.10,
        }
        
        overall_score = sum(
            metrics[dim].score * weights.get(dim, 0.1)
            for dim in metrics
        )
        overall_status = self._score_to_status(overall_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, issues)
        
        # Get trend data
        trends = self._get_trends(table_name)
        
        # Store score history
        self._update_score_history(table_name, overall_score)
        
        # Store issues
        self._issue_history.extend(issues)
        
        return QualityReport(
            report_id=report_id,
            generated_at=generated_at,
            overall_score=round(overall_score, 2),
            overall_status=overall_status,
            metrics=metrics,
            issues=issues,
            trends=trends,
            recommendations=recommendations,
        )
    
    def calculate_completeness(self, data: pd.DataFrame, table_name: str = "records") -> QualityMetric:
        """
        Calculate completeness score.
        
        Measures the percentage of non-null values in required fields.
        """
        if len(data) == 0:
            return QualityMetric(
                dimension=QualityDimension.COMPLETENESS,
                score=0.0,
                status=QualityStatus.POOR,
                issues_found=0,
                details={"message": "No data to analyze"},
            )
        
        required_fields = [f for f in self.config.required_fields if f in data.columns]
        
        if not required_fields:
            return QualityMetric(
                dimension=QualityDimension.COMPLETENESS,
                score=100.0,
                status=QualityStatus.EXCELLENT,
                issues_found=0,
                details={"message": "No required fields configured"},
            )
        
        total_cells = len(data) * len(required_fields)
        null_cells = data[required_fields].isnull().sum().sum()
        completeness = ((total_cells - null_cells) / total_cells) * 100
        
        # Get per-field completeness
        field_completeness = {}
        issues_found = 0
        for field in required_fields:
            null_count = data[field].isnull().sum()
            field_pct = ((len(data) - null_count) / len(data)) * 100
            field_completeness[field] = round(field_pct, 2)
            if null_count > 0:
                issues_found += 1
        
        recommendations = []
        for field, pct in field_completeness.items():
            if pct < 90:
                recommendations.append(f"Field '{field}' has only {pct}% completeness - review data ingestion")
        
        return QualityMetric(
            dimension=QualityDimension.COMPLETENESS,
            score=round(completeness, 2),
            status=self._score_to_status(completeness),
            issues_found=issues_found,
            details={
                "total_records": len(data),
                "required_fields": required_fields,
                "field_completeness": field_completeness,
                "null_cells": int(null_cells),
            },
            recommendations=recommendations,
        )
    
    def calculate_accuracy(self, data: pd.DataFrame, table_name: str = "records", sample_size: int = 100) -> QualityMetric:
        """
        Calculate accuracy score.
        
        Performs spot-check validation against known patterns and ranges.
        """
        if len(data) == 0:
            return QualityMetric(
                dimension=QualityDimension.ACCURACY,
                score=0.0,
                status=QualityStatus.POOR,
                issues_found=0,
            )
        
        # Sample data for spot-checking
        sample = data.sample(n=min(sample_size, len(data)), random_state=42)
        
        accuracy_checks = []
        issues_found = 0
        
        # Check date validity
        date_cols = [c for c in data.columns if 'date' in c.lower() or c in ['created_at', 'updated_at']]
        for col in date_cols:
            if col in sample.columns:
                try:
                    dates = pd.to_datetime(sample[col], errors='coerce')
                    valid_dates = dates.notna() & (dates >= pd.Timestamp('1900-01-01')) & (dates <= pd.Timestamp.now() + pd.Timedelta(days=365))
                    accuracy = valid_dates.mean() * 100
                    accuracy_checks.append(accuracy)
                    if accuracy < 95:
                        issues_found += 1
                except Exception:
                    pass
        
        # Check numeric ranges
        for col, (min_val, max_val) in self.config.value_ranges.items():
            if col in sample.columns:
                values = pd.to_numeric(sample[col], errors='coerce')
                in_range = (values >= min_val) & (values <= max_val)
                accuracy = in_range.mean() * 100
                accuracy_checks.append(accuracy)
                if accuracy < 95:
                    issues_found += 1
        
        # If no specific checks, use a baseline
        if not accuracy_checks:
            accuracy_checks = [95.0]  # Assume good accuracy without specific validation
        
        overall_accuracy = np.mean(accuracy_checks)
        
        return QualityMetric(
            dimension=QualityDimension.ACCURACY,
            score=round(overall_accuracy, 2),
            status=self._score_to_status(overall_accuracy),
            issues_found=issues_found,
            details={
                "sample_size": len(sample),
                "checks_performed": len(accuracy_checks),
                "date_columns_checked": date_cols,
            },
        )
    
    def calculate_consistency(self, data: pd.DataFrame, table_name: str = "records") -> QualityMetric:
        """
        Calculate consistency score.
        
        Checks cross-field relationships and business rules.
        """
        if len(data) == 0:
            return QualityMetric(
                dimension=QualityDimension.CONSISTENCY,
                score=0.0,
                status=QualityStatus.POOR,
                issues_found=0,
            )
        
        consistency_scores = []
        issues_found = 0
        rule_results = {}
        
        for rule in self.consistency_rules:
            if rule.field1 in data.columns and rule.field2 in data.columns:
                if rule.rule_type == 'equal':
                    consistent = (data[rule.field1] == data[rule.field2]).mean() * 100
                elif rule.rule_type == 'greater':
                    consistent = (data[rule.field1] > data[rule.field2]).mean() * 100
                elif rule.rule_type == 'less':
                    consistent = (data[rule.field1] < data[rule.field2]).mean() * 100
                else:
                    consistent = 100.0
                
                consistency_scores.append(consistent)
                rule_results[rule.name] = round(consistent, 2)
                
                if consistent < 95:
                    issues_found += 1
        
        # Check for internal consistency (e.g., dates in order)
        if 'created_at' in data.columns and 'updated_at' in data.columns:
            dates_valid = (pd.to_datetime(data['updated_at'], errors='coerce') >= 
                          pd.to_datetime(data['created_at'], errors='coerce'))
            consistency = dates_valid.mean() * 100
            consistency_scores.append(consistency)
            rule_results['created_before_updated'] = round(consistency, 2)
            if consistency < 95:
                issues_found += 1
        
        overall_consistency = np.mean(consistency_scores) if consistency_scores else 100.0
        
        return QualityMetric(
            dimension=QualityDimension.CONSISTENCY,
            score=round(overall_consistency, 2),
            status=self._score_to_status(overall_consistency),
            issues_found=issues_found,
            details={
                "rules_checked": len(self.consistency_rules),
                "rule_results": rule_results,
            },
        )
    
    def calculate_timeliness(self, data: pd.DataFrame, table_name: str = "records") -> QualityMetric:
        """
        Calculate timeliness score.
        
        Measures data freshness based on SLA requirements.
        """
        if len(data) == 0:
            return QualityMetric(
                dimension=QualityDimension.TIMELINESS,
                score=0.0,
                status=QualityStatus.POOR,
                issues_found=0,
            )
        
        # Find the most recent timestamp column
        date_cols = ['updated_at', 'created_at', 'modified_at', 'date']
        timestamp_col = None
        
        for col in date_cols:
            if col in data.columns:
                timestamp_col = col
                break
        
        if not timestamp_col:
            return QualityMetric(
                dimension=QualityDimension.TIMELINESS,
                score=50.0,  # Unknown
                status=QualityStatus.FAIR,
                issues_found=0,
                details={"message": "No timestamp column found"},
            )
        
        now = datetime.utcnow()
        sla = timedelta(hours=self.config.timeliness_sla_hours)
        freshness_threshold = timedelta(days=self.config.freshness_threshold_days)
        
        # Parse timestamps
        timestamps = pd.to_datetime(data[timestamp_col], errors='coerce')
        valid_timestamps = timestamps.dropna()
        
        if len(valid_timestamps) == 0:
            return QualityMetric(
                dimension=QualityDimension.TIMELINESS,
                score=0.0,
                status=QualityStatus.POOR,
                issues_found=1,
                details={"message": "No valid timestamps"},
            )
        
        # Calculate freshness
        latest = valid_timestamps.max()
        oldest = valid_timestamps.min()
        age = now - latest
        
        # Recent data percentage (within freshness threshold)
        recent_threshold = now - freshness_threshold
        recent_pct = (valid_timestamps >= recent_threshold).mean() * 100
        
        # Timeliness score based on most recent data
        if age <= sla:
            timeliness = 100.0
        elif age <= freshness_threshold:
            timeliness = max(0, 100 - (age.days / self.config.freshness_threshold_days * 50))
        else:
            timeliness = max(0, 50 - (age.days - self.config.freshness_threshold_days))
        
        issues_found = 0 if timeliness >= 80 else 1
        
        recommendations = []
        if timeliness < 80:
            recommendations.append(f"Data is {age.days} days old - consider refreshing")
        
        return QualityMetric(
            dimension=QualityDimension.TIMELINESS,
            score=round(timeliness, 2),
            status=self._score_to_status(timeliness),
            issues_found=issues_found,
            details={
                "latest_record": latest.isoformat() if pd.notna(latest) else None,
                "oldest_record": oldest.isoformat() if pd.notna(oldest) else None,
                "age_days": age.days,
                "recent_records_pct": round(recent_pct, 2),
                "sla_hours": self.config.timeliness_sla_hours,
            },
            recommendations=recommendations,
        )
    
    def calculate_validity(self, data: pd.DataFrame, table_name: str = "records") -> QualityMetric:
        """
        Calculate validity score.
        
        Checks data format and value validity.
        """
        if len(data) == 0:
            return QualityMetric(
                dimension=QualityDimension.VALIDITY,
                score=0.0,
                status=QualityStatus.POOR,
                issues_found=0,
            )
        
        validity_checks = []
        issues_found = 0
        format_results = {}
        
        # Check format patterns
        import re
        for col, pattern in self.config.format_patterns.items():
            if col in data.columns:
                matches = data[col].astype(str).str.match(pattern, na=False)
                validity = matches.mean() * 100
                validity_checks.append(validity)
                format_results[col] = round(validity, 2)
                if validity < 95:
                    issues_found += 1
        
        # Check common patterns
        # Email validation
        email_cols = [c for c in data.columns if 'email' in c.lower()]
        for col in email_cols:
            email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
            matches = data[col].astype(str).str.match(email_pattern, na=True)
            validity = matches.mean() * 100
            validity_checks.append(validity)
            format_results[f"{col}_email_format"] = round(validity, 2)
            if validity < 95:
                issues_found += 1
        
        # ZIP code validation
        zip_cols = [c for c in data.columns if 'zip' in c.lower() or 'postal' in c.lower()]
        for col in zip_cols:
            zip_pattern = r'^\d{5}(-\d{4})?$'
            non_null = data[col].dropna()
            if len(non_null) > 0:
                matches = non_null.astype(str).str.match(zip_pattern)
                validity = matches.mean() * 100
                validity_checks.append(validity)
                format_results[f"{col}_zip_format"] = round(validity, 2)
                if validity < 95:
                    issues_found += 1
        
        # State code validation
        state_cols = [c for c in data.columns if c.lower() == 'state']
        valid_states = set([
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
        ])
        for col in state_cols:
            valid = data[col].isin(valid_states)
            validity = valid.mean() * 100
            validity_checks.append(validity)
            format_results[f"{col}_state_valid"] = round(validity, 2)
            if validity < 95:
                issues_found += 1
        
        overall_validity = np.mean(validity_checks) if validity_checks else 95.0
        
        return QualityMetric(
            dimension=QualityDimension.VALIDITY,
            score=round(overall_validity, 2),
            status=self._score_to_status(overall_validity),
            issues_found=issues_found,
            details={
                "format_checks": len(validity_checks),
                "format_results": format_results,
            },
        )
    
    def calculate_uniqueness(self, data: pd.DataFrame, table_name: str = "records") -> QualityMetric:
        """
        Calculate uniqueness score.
        
        Detects and measures duplicate records.
        """
        if len(data) == 0:
            return QualityMetric(
                dimension=QualityDimension.UNIQUENESS,
                score=0.0,
                status=QualityStatus.POOR,
                issues_found=0,
            )
        
        # Use configured duplicate check fields or all columns
        check_cols = self.config.duplicate_check_fields or [
            c for c in data.columns 
            if c.lower() not in ['id', 'created_at', 'updated_at', 'modified_at']
        ]
        check_cols = [c for c in check_cols if c in data.columns]
        
        if not check_cols:
            return QualityMetric(
                dimension=QualityDimension.UNIQUENESS,
                score=100.0,
                status=QualityStatus.EXCELLENT,
                issues_found=0,
                details={"message": "No columns to check for duplicates"},
            )
        
        # Count duplicates
        duplicates = data.duplicated(subset=check_cols, keep=False)
        duplicate_count = duplicates.sum()
        duplicate_groups = data[duplicates].groupby(check_cols).size()
        
        uniqueness = ((len(data) - duplicate_count) / len(data)) * 100
        issues_found = 1 if duplicate_count > 0 else 0
        
        recommendations = []
        if duplicate_count > 0:
            recommendations.append(f"Found {duplicate_count} duplicate records - consider deduplication")
        
        return QualityMetric(
            dimension=QualityDimension.UNIQUENESS,
            score=round(uniqueness, 2),
            status=self._score_to_status(uniqueness),
            issues_found=issues_found,
            details={
                "total_records": len(data),
                "duplicate_records": int(duplicate_count),
                "duplicate_groups": len(duplicate_groups) if duplicate_count > 0 else 0,
                "columns_checked": check_cols,
            },
            recommendations=recommendations,
        )
    
    def add_consistency_rule(self, rule: ConsistencyRule) -> None:
        """Add a consistency validation rule."""
        self.consistency_rules.append(rule)
        logger.info("Added consistency rule: %s", rule.name)
    
    def get_issues(self, severity: Optional[str] = None) -> List[QualityIssue]:
        """Get all detected quality issues."""
        issues = self._issue_history
        if severity:
            issues = [i for i in issues if i.severity == severity]
        return sorted(issues, key=lambda x: x.detected_at, reverse=True)
    
    # Private methods
    
    def _get_completeness_issues(self, data: pd.DataFrame, table_name: str) -> List[QualityIssue]:
        """Get completeness-related issues."""
        issues = []
        required_fields = [f for f in self.config.required_fields if f in data.columns]
        
        for field in required_fields:
            null_count = data[field].isnull().sum()
            null_pct = (null_count / len(data)) * 100 if len(data) > 0 else 0
            
            if null_pct > 5:
                severity = 'critical' if null_pct > 20 else 'high' if null_pct > 10 else 'medium'
                issues.append(QualityIssue(
                    issue_id=self._generate_id(f"completeness_{table_name}_{field}"),
                    dimension=QualityDimension.COMPLETENESS,
                    severity=severity,
                    table=table_name,
                    column=field,
                    description=f"Field '{field}' has {null_pct:.1f}% missing values",
                    affected_records=int(null_count),
                ))
        
        return issues
    
    def _get_consistency_issues(self, data: pd.DataFrame, table_name: str) -> List[QualityIssue]:
        """Get consistency-related issues."""
        issues = []
        
        for rule in self.consistency_rules:
            if rule.field1 in data.columns and rule.field2 in data.columns:
                if rule.rule_type == 'equal':
                    inconsistent = data[data[rule.field1] != data[rule.field2]]
                elif rule.rule_type == 'greater':
                    inconsistent = data[data[rule.field1] <= data[rule.field2]]
                else:
                    continue
                
                if len(inconsistent) > 0:
                    pct = (len(inconsistent) / len(data)) * 100
                    severity = 'high' if pct > 10 else 'medium' if pct > 5 else 'low'
                    
                    issues.append(QualityIssue(
                        issue_id=self._generate_id(f"consistency_{rule.name}"),
                        dimension=QualityDimension.CONSISTENCY,
                        severity=severity,
                        table=table_name,
                        column=f"{rule.field1}, {rule.field2}",
                        description=f"Rule '{rule.name}' violated: {rule.description}",
                        affected_records=len(inconsistent),
                    ))
        
        return issues
    
    def _get_validity_issues(self, data: pd.DataFrame, table_name: str) -> List[QualityIssue]:
        """Get validity-related issues."""
        issues = []
        import re
        
        for col, pattern in self.config.format_patterns.items():
            if col in data.columns:
                invalid = ~data[col].astype(str).str.match(pattern, na=True)
                invalid_count = invalid.sum()
                
                if invalid_count > 0:
                    pct = (invalid_count / len(data)) * 100
                    severity = 'high' if pct > 10 else 'medium' if pct > 5 else 'low'
                    
                    issues.append(QualityIssue(
                        issue_id=self._generate_id(f"validity_{col}"),
                        dimension=QualityDimension.VALIDITY,
                        severity=severity,
                        table=table_name,
                        column=col,
                        description=f"Field '{col}' has {invalid_count} values not matching expected format",
                        affected_records=int(invalid_count),
                        example_values=data[invalid][col].head(5).tolist(),
                    ))
        
        return issues
    
    def _get_uniqueness_issues(self, data: pd.DataFrame, table_name: str) -> List[QualityIssue]:
        """Get uniqueness-related issues."""
        issues = []
        
        check_cols = self.config.duplicate_check_fields or [
            c for c in data.columns 
            if c.lower() not in ['id', 'created_at', 'updated_at']
        ]
        check_cols = [c for c in check_cols if c in data.columns]
        
        if check_cols and len(data) > 0:
            duplicates = data.duplicated(subset=check_cols, keep=False)
            duplicate_count = duplicates.sum()
            
            if duplicate_count > 0:
                pct = (duplicate_count / len(data)) * 100
                severity = 'high' if pct > 10 else 'medium' if pct > 5 else 'low'
                
                issues.append(QualityIssue(
                    issue_id=self._generate_id(f"uniqueness_{table_name}"),
                    dimension=QualityDimension.UNIQUENESS,
                    severity=severity,
                    table=table_name,
                    column=None,
                    description=f"Found {duplicate_count} duplicate records ({pct:.1f}% of total)",
                    affected_records=int(duplicate_count),
                ))
        
        return issues
    
    def _score_to_status(self, score: float) -> QualityStatus:
        """Convert score to status."""
        if score >= 95:
            return QualityStatus.EXCELLENT
        elif score >= 80:
            return QualityStatus.GOOD
        elif score >= 60:
            return QualityStatus.FAIR
        return QualityStatus.POOR
    
    def _generate_recommendations(
        self,
        metrics: Dict[QualityDimension, QualityMetric],
        issues: List[QualityIssue]
    ) -> List[str]:
        """Generate overall recommendations."""
        recommendations = []
        
        # Priority-based recommendations
        for dim in [QualityDimension.COMPLETENESS, QualityDimension.ACCURACY, 
                    QualityDimension.TIMELINESS, QualityDimension.UNIQUENESS]:
            if dim in metrics and metrics[dim].score < 80:
                recommendations.extend(metrics[dim].recommendations)
        
        # Issue-based recommendations
        critical_issues = [i for i in issues if i.severity == 'critical']
        if critical_issues:
            recommendations.append(f"Address {len(critical_issues)} critical quality issues immediately")
        
        high_issues = [i for i in issues if i.severity == 'high']
        if high_issues:
            recommendations.append(f"Review and fix {len(high_issues)} high-priority quality issues")
        
        return recommendations[:10]  # Limit to top 10
    
    def _get_trends(self, table_name: str) -> Dict[str, List[float]]:
        """Get historical score trends."""
        trends = {}
        history_key = f"{table_name}_overall"
        
        if history_key in self._score_history:
            history = self._score_history[history_key][-30:]  # Last 30 entries
            trends["overall"] = [score for _, score in history]
        
        return trends
    
    def _update_score_history(self, table_name: str, score: float) -> None:
        """Update score history for trends."""
        history_key = f"{table_name}_overall"
        
        if history_key not in self._score_history:
            self._score_history[history_key] = []
        
        self._score_history[history_key].append((datetime.utcnow(), score))
        
        # Keep only last 100 entries
        if len(self._score_history[history_key]) > 100:
            self._score_history[history_key] = self._score_history[history_key][-100:]
    
    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID."""
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{prefix}_{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]


# Create default monitor instance
_default_monitor: Optional[DataQualityMonitor] = None


def get_quality_monitor() -> DataQualityMonitor:
    """Get or create the default quality monitor instance."""
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = DataQualityMonitor()
    return _default_monitor
