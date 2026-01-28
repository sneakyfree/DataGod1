"""
DataGod Anomaly Detection Module

Multi-method anomaly detection system for identifying unusual patterns,
outliers, and suspicious data in public records.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class AnomalySeverity(str, Enum):
    """Severity levels for detected anomalies."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """Types of anomalies that can be detected."""
    OUTLIER = "outlier"
    PATTERN_DEVIATION = "pattern_deviation"
    DUPLICATE = "duplicate"
    MISSING_DATA = "missing_data"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    CROSS_FIELD_INCONSISTENCY = "cross_field_inconsistency"
    VALUE_SPIKE = "value_spike"
    FREQUENCY_ANOMALY = "frequency_anomaly"
    RULE_VIOLATION = "rule_violation"


@dataclass
class Anomaly:
    """Represents a detected anomaly."""
    id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    title: str
    description: str
    score: float  # 0-1, higher = more anomalous
    detected_at: datetime
    data_source: str
    record_ids: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    false_positive: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "score": self.score,
            "detected_at": self.detected_at.isoformat(),
            "data_source": self.data_source,
            "record_ids": self.record_ids,
            "metadata": self.metadata,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "false_positive": self.false_positive,
        }


@dataclass
class AnomalyRule:
    """Custom rule for anomaly detection."""
    id: str
    name: str
    description: str
    rule_type: str  # 'threshold', 'pattern', 'comparison'
    field: str
    condition: str  # 'gt', 'lt', 'eq', 'ne', 'contains', 'regex'
    value: Any
    severity: AnomalySeverity
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type,
            "field": self.field,
            "condition": self.condition,
            "value": self.value,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AnomalyConfig:
    """Configuration for anomaly detection."""
    z_score_threshold: float = 3.0
    iqr_multiplier: float = 1.5
    min_data_points: int = 10
    isolation_forest_contamination: float = 0.1
    enable_statistical: bool = True
    enable_ml: bool = True
    enable_rules: bool = True
    lookback_days: int = 30
    batch_size: int = 1000


class AnomalyDetector:
    """
    Multi-method anomaly detection system.
    
    Combines statistical methods, ML-based detection, and custom business rules
    to identify anomalies in public records data.
    """
    
    def __init__(self, config: Optional[AnomalyConfig] = None):
        """Initialize the anomaly detector."""
        self.config = config or AnomalyConfig()
        self.rules: Dict[str, AnomalyRule] = {}
        self._detected_anomalies: Dict[str, Anomaly] = {}
        logger.info("AnomalyDetector initialized with config: %s", self.config)
    
    def detect_all(self, data: pd.DataFrame, data_source: str = "unknown") -> List[Anomaly]:
        """
        Run all enabled detection methods on the data.
        
        Args:
            data: DataFrame containing records to analyze
            data_source: Name of the data source for tracking
            
        Returns:
            List of detected anomalies
        """
        anomalies: List[Anomaly] = []
        
        if len(data) < self.config.min_data_points:
            logger.warning("Insufficient data points (%d) for anomaly detection", len(data))
            return anomalies
        
        try:
            if self.config.enable_statistical:
                anomalies.extend(self.detect_statistical(data, data_source))
            
            if self.config.enable_ml:
                anomalies.extend(self.detect_isolation_forest(data, data_source))
            
            if self.config.enable_rules:
                anomalies.extend(self.detect_rule_based(data, data_source))
            
            # Detect temporal anomalies
            if 'date' in data.columns or 'created_at' in data.columns:
                anomalies.extend(self.detect_temporal_anomalies(data, data_source))
            
            # Detect duplicates
            anomalies.extend(self.detect_duplicates(data, data_source))
            
            # Deduplicate anomalies
            anomalies = self._deduplicate_anomalies(anomalies)
            
            # Store detected anomalies
            for anomaly in anomalies:
                self._detected_anomalies[anomaly.id] = anomaly
            
            logger.info("Detected %d anomalies in data source '%s'", len(anomalies), data_source)
            
        except Exception as e:
            logger.error("Error during anomaly detection: %s", e)
            raise
        
        return anomalies
    
    def detect_statistical(self, data: pd.DataFrame, data_source: str) -> List[Anomaly]:
        """
        Detect anomalies using statistical methods (Z-score and IQR).
        
        Args:
            data: DataFrame to analyze
            data_source: Data source name
            
        Returns:
            List of statistical anomalies
        """
        anomalies: List[Anomaly] = []
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            col_data = data[column].dropna()
            if len(col_data) < self.config.min_data_points:
                continue
            
            # Z-score method
            z_scores = np.abs(stats.zscore(col_data))
            z_outliers = np.where(z_scores > self.config.z_score_threshold)[0]
            
            for idx in z_outliers:
                record_idx = col_data.index[idx]
                value = col_data.iloc[idx]
                z_score = z_scores[idx]
                
                anomaly = Anomaly(
                    id=self._generate_id(f"zscore_{column}_{record_idx}"),
                    anomaly_type=AnomalyType.OUTLIER,
                    severity=self._score_to_severity(z_score / 10),
                    title=f"Statistical Outlier in {column}",
                    description=f"Value {value:.2f} has Z-score of {z_score:.2f}, exceeding threshold of {self.config.z_score_threshold}",
                    score=min(z_score / 10, 1.0),
                    detected_at=datetime.utcnow(),
                    data_source=data_source,
                    record_ids=[int(record_idx)] if isinstance(record_idx, (int, np.integer)) else [],
                    metadata={
                        "column": column,
                        "value": float(value),
                        "z_score": float(z_score),
                        "method": "z_score",
                        "mean": float(col_data.mean()),
                        "std": float(col_data.std()),
                    }
                )
                anomalies.append(anomaly)
            
            # IQR method
            q1 = col_data.quantile(0.25)
            q3 = col_data.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - (self.config.iqr_multiplier * iqr)
            upper_bound = q3 + (self.config.iqr_multiplier * iqr)
            
            iqr_outliers = col_data[(col_data < lower_bound) | (col_data > upper_bound)]
            
            for record_idx, value in iqr_outliers.items():
                # Skip if already caught by Z-score
                existing_ids = {a.record_ids[0] for a in anomalies if a.record_ids}
                if record_idx in existing_ids:
                    continue
                
                deviation = abs(value - col_data.median()) / iqr if iqr > 0 else 0
                
                anomaly = Anomaly(
                    id=self._generate_id(f"iqr_{column}_{record_idx}"),
                    anomaly_type=AnomalyType.OUTLIER,
                    severity=self._score_to_severity(min(deviation / 5, 1.0)),
                    title=f"IQR Outlier in {column}",
                    description=f"Value {value:.2f} is outside IQR bounds [{lower_bound:.2f}, {upper_bound:.2f}]",
                    score=min(deviation / 5, 1.0),
                    detected_at=datetime.utcnow(),
                    data_source=data_source,
                    record_ids=[int(record_idx)] if isinstance(record_idx, (int, np.integer)) else [],
                    metadata={
                        "column": column,
                        "value": float(value),
                        "method": "iqr",
                        "q1": float(q1),
                        "q3": float(q3),
                        "iqr": float(iqr),
                        "lower_bound": float(lower_bound),
                        "upper_bound": float(upper_bound),
                    }
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def detect_isolation_forest(self, data: pd.DataFrame, data_source: str) -> List[Anomaly]:
        """
        Detect anomalies using Isolation Forest algorithm.
        
        Args:
            data: DataFrame to analyze
            data_source: Data source name
            
        Returns:
            List of ML-detected anomalies
        """
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            logger.warning("scikit-learn not available, skipping Isolation Forest detection")
            return []
        
        anomalies: List[Anomaly] = []
        numeric_data = data.select_dtypes(include=[np.number])
        
        if numeric_data.empty or len(numeric_data) < self.config.min_data_points:
            return anomalies
        
        # Fill NaN values with column medians
        numeric_data = numeric_data.fillna(numeric_data.median())
        
        try:
            clf = IsolationForest(
                contamination=self.config.isolation_forest_contamination,
                random_state=42,
                n_estimators=100
            )
            predictions = clf.fit_predict(numeric_data)
            scores = clf.decision_function(numeric_data)
            
            # Find anomalies (predictions == -1)
            anomaly_indices = np.where(predictions == -1)[0]
            
            for idx in anomaly_indices:
                record_idx = data.index[idx]
                score = -scores[idx]  # Convert to positive (higher = more anomalous)
                normalized_score = min(max(score, 0), 1)
                
                anomaly = Anomaly(
                    id=self._generate_id(f"iforest_{record_idx}"),
                    anomaly_type=AnomalyType.PATTERN_DEVIATION,
                    severity=self._score_to_severity(normalized_score),
                    title="ML-Detected Pattern Deviation",
                    description=f"Record shows unusual pattern across multiple fields (isolation score: {score:.3f})",
                    score=normalized_score,
                    detected_at=datetime.utcnow(),
                    data_source=data_source,
                    record_ids=[int(record_idx)] if isinstance(record_idx, (int, np.integer)) else [],
                    metadata={
                        "method": "isolation_forest",
                        "isolation_score": float(score),
                        "contamination": self.config.isolation_forest_contamination,
                        "features_analyzed": list(numeric_data.columns),
                    }
                )
                anomalies.append(anomaly)
                
        except Exception as e:
            logger.error("Isolation Forest detection failed: %s", e)
        
        return anomalies
    
    def detect_rule_based(self, data: pd.DataFrame, data_source: str) -> List[Anomaly]:
        """
        Detect anomalies using custom business rules.
        
        Args:
            data: DataFrame to analyze
            data_source: Data source name
            
        Returns:
            List of rule-based anomalies
        """
        anomalies: List[Anomaly] = []
        
        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            if rule.field not in data.columns:
                continue
            
            try:
                violations = self._evaluate_rule(data, rule)
                
                for idx, row in violations.iterrows():
                    anomaly = Anomaly(
                        id=self._generate_id(f"rule_{rule_id}_{idx}"),
                        anomaly_type=AnomalyType.RULE_VIOLATION,
                        severity=rule.severity,
                        title=f"Rule Violation: {rule.name}",
                        description=f"{rule.description}. Value: {row[rule.field]}",
                        score=0.8,  # Rule violations are generally high confidence
                        detected_at=datetime.utcnow(),
                        data_source=data_source,
                        record_ids=[int(idx)] if isinstance(idx, (int, np.integer)) else [],
                        metadata={
                            "method": "rule_based",
                            "rule_id": rule_id,
                            "rule_name": rule.name,
                            "field": rule.field,
                            "condition": rule.condition,
                            "threshold": rule.value,
                            "actual_value": row[rule.field] if rule.field in row else None,
                        }
                    )
                    anomalies.append(anomaly)
                    
            except Exception as e:
                logger.error("Rule '%s' evaluation failed: %s", rule.name, e)
        
        return anomalies
    
    def detect_temporal_anomalies(self, data: pd.DataFrame, data_source: str) -> List[Anomaly]:
        """
        Detect temporal anomalies (unusual time patterns).
        
        Args:
            data: DataFrame with date column
            data_source: Data source name
            
        Returns:
            List of temporal anomalies
        """
        anomalies: List[Anomaly] = []
        
        date_col = 'date' if 'date' in data.columns else 'created_at'
        if date_col not in data.columns:
            return anomalies
        
        try:
            dates = pd.to_datetime(data[date_col])
            
            # Detect unusual volume spikes
            daily_counts = dates.dt.date.value_counts().sort_index()
            if len(daily_counts) >= self.config.min_data_points:
                mean_count = daily_counts.mean()
                std_count = daily_counts.std()
                
                if std_count > 0:
                    for date, count in daily_counts.items():
                        z_score = (count - mean_count) / std_count
                        if abs(z_score) > self.config.z_score_threshold:
                            anomaly = Anomaly(
                                id=self._generate_id(f"temporal_spike_{date}"),
                                anomaly_type=AnomalyType.VALUE_SPIKE if z_score > 0 else AnomalyType.TEMPORAL_ANOMALY,
                                severity=self._score_to_severity(abs(z_score) / 10),
                                title="Unusual Daily Volume" if z_score > 0 else "Unusually Low Activity",
                                description=f"Date {date}: {count} records vs. average {mean_count:.1f} (Z-score: {z_score:.2f})",
                                score=min(abs(z_score) / 10, 1.0),
                                detected_at=datetime.utcnow(),
                                data_source=data_source,
                                metadata={
                                    "method": "temporal_analysis",
                                    "date": str(date),
                                    "count": int(count),
                                    "mean": float(mean_count),
                                    "std": float(std_count),
                                    "z_score": float(z_score),
                                }
                            )
                            anomalies.append(anomaly)
            
            # Detect gaps in data (missing days)
            if len(daily_counts) > 1:
                date_range = pd.date_range(start=daily_counts.index.min(), end=daily_counts.index.max())
                missing_dates = set(date_range.date) - set(daily_counts.index)
                
                if len(missing_dates) > 0 and len(missing_dates) <= 10:  # Only report if not too many
                    for missing_date in list(missing_dates)[:5]:  # Limit to 5 reports
                        anomaly = Anomaly(
                            id=self._generate_id(f"missing_date_{missing_date}"),
                            anomaly_type=AnomalyType.MISSING_DATA,
                            severity=AnomalySeverity.MEDIUM,
                            title="Missing Date in Data",
                            description=f"No records found for {missing_date}",
                            score=0.6,
                            detected_at=datetime.utcnow(),
                            data_source=data_source,
                            metadata={
                                "method": "temporal_gap_analysis",
                                "missing_date": str(missing_date),
                                "total_missing_dates": len(missing_dates),
                            }
                        )
                        anomalies.append(anomaly)
                        
        except Exception as e:
            logger.error("Temporal anomaly detection failed: %s", e)
        
        return anomalies
    
    def detect_duplicates(self, data: pd.DataFrame, data_source: str) -> List[Anomaly]:
        """
        Detect potential duplicate records.
        
        Args:
            data: DataFrame to analyze
            data_source: Data source name
            
        Returns:
            List of duplicate anomalies
        """
        anomalies: List[Anomaly] = []
        
        # Find exact duplicates
        if len(data) < 2:
            return anomalies
        
        # Exclude ID columns and timestamps
        exclude_cols = ['id', 'created_at', 'updated_at', 'modified_at']
        check_cols = [c for c in data.columns if c.lower() not in exclude_cols]
        
        if not check_cols:
            return anomalies
        
        try:
            duplicates = data[check_cols].duplicated(keep=False)
            duplicate_groups = data[duplicates].groupby(check_cols, dropna=False)
            
            for _, group in duplicate_groups:
                if len(group) > 1:
                    record_ids = [int(idx) for idx in group.index if isinstance(idx, (int, np.integer))]
                    
                    anomaly = Anomaly(
                        id=self._generate_id(f"duplicate_{'_'.join(map(str, record_ids[:3]))}"),
                        anomaly_type=AnomalyType.DUPLICATE,
                        severity=AnomalySeverity.MEDIUM,
                        title=f"Potential Duplicate Records ({len(group)} copies)",
                        description=f"Found {len(group)} records with identical values",
                        score=0.7,
                        detected_at=datetime.utcnow(),
                        data_source=data_source,
                        record_ids=record_ids,
                        metadata={
                            "method": "duplicate_detection",
                            "duplicate_count": len(group),
                            "checked_columns": check_cols,
                        }
                    )
                    anomalies.append(anomaly)
                    
        except Exception as e:
            logger.error("Duplicate detection failed: %s", e)
        
        return anomalies
    
    def add_rule(self, rule: AnomalyRule) -> None:
        """Add a custom detection rule."""
        self.rules[rule.id] = rule
        logger.info("Added anomaly rule: %s", rule.name)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a detection rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info("Removed anomaly rule: %s", rule_id)
            return True
        return False
    
    def get_rules(self) -> List[AnomalyRule]:
        """Get all configured rules."""
        return list(self.rules.values())
    
    def get_anomaly(self, anomaly_id: str) -> Optional[Anomaly]:
        """Get a specific anomaly by ID."""
        return self._detected_anomalies.get(anomaly_id)
    
    def get_all_anomalies(self, include_resolved: bool = False) -> List[Anomaly]:
        """Get all detected anomalies."""
        anomalies = list(self._detected_anomalies.values())
        if not include_resolved:
            anomalies = [a for a in anomalies if not a.resolved]
        return sorted(anomalies, key=lambda x: x.detected_at, reverse=True)
    
    def resolve_anomaly(self, anomaly_id: str, resolved_by: str, false_positive: bool = False) -> bool:
        """Mark an anomaly as resolved."""
        if anomaly_id in self._detected_anomalies:
            anomaly = self._detected_anomalies[anomaly_id]
            anomaly.resolved = True
            anomaly.resolved_at = datetime.utcnow()
            anomaly.resolved_by = resolved_by
            anomaly.false_positive = false_positive
            return True
        return False
    
    def get_anomaly_score(self, record: Dict[str, Any]) -> float:
        """
        Calculate an anomaly score for a single record.
        
        Args:
            record: Record data as dictionary
            
        Returns:
            Anomaly score between 0 and 1
        """
        scores = []
        
        # Check against rules
        for rule in self.rules.values():
            if rule.enabled and rule.field in record:
                if self._check_rule_violation(record[rule.field], rule):
                    scores.append(0.8)
        
        # Return max score or 0
        return max(scores) if scores else 0.0
    
    def _evaluate_rule(self, data: pd.DataFrame, rule: AnomalyRule) -> pd.DataFrame:
        """Evaluate a rule against the data."""
        field_data = data[rule.field]
        
        conditions = {
            'gt': lambda x: x > rule.value,
            'lt': lambda x: x < rule.value,
            'gte': lambda x: x >= rule.value,
            'lte': lambda x: x <= rule.value,
            'eq': lambda x: x == rule.value,
            'ne': lambda x: x != rule.value,
            'contains': lambda x: x.astype(str).str.contains(str(rule.value), case=False, na=False),
            'not_contains': lambda x: ~x.astype(str).str.contains(str(rule.value), case=False, na=False),
        }
        
        if rule.condition in conditions:
            mask = conditions[rule.condition](field_data)
            return data[mask]
        
        return pd.DataFrame()
    
    def _check_rule_violation(self, value: Any, rule: AnomalyRule) -> bool:
        """Check if a single value violates a rule."""
        conditions = {
            'gt': lambda x, v: x > v,
            'lt': lambda x, v: x < v,
            'gte': lambda x, v: x >= v,
            'lte': lambda x, v: x <= v,
            'eq': lambda x, v: x == v,
            'ne': lambda x, v: x != v,
            'contains': lambda x, v: str(v).lower() in str(x).lower(),
        }
        
        if rule.condition in conditions:
            try:
                return conditions[rule.condition](value, rule.value)
            except (TypeError, ValueError):
                return False
        return False
    
    def _score_to_severity(self, score: float) -> AnomalySeverity:
        """Convert numeric score to severity level."""
        if score >= 0.8:
            return AnomalySeverity.CRITICAL
        elif score >= 0.6:
            return AnomalySeverity.HIGH
        elif score >= 0.4:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW
    
    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID for an anomaly."""
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{prefix}_{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    
    def _deduplicate_anomalies(self, anomalies: List[Anomaly]) -> List[Anomaly]:
        """Remove duplicate anomalies based on record IDs and type."""
        seen = set()
        unique = []
        
        for anomaly in anomalies:
            key = (tuple(anomaly.record_ids), anomaly.anomaly_type)
            if key not in seen:
                seen.add(key)
                unique.append(anomaly)
        
        return unique


# Create default detector instance
_default_detector: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create the default anomaly detector instance."""
    global _default_detector
    if _default_detector is None:
        _default_detector = AnomalyDetector()
    return _default_detector
