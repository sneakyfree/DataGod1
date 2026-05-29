"""
Anomaly Detection Pydantic Schemas

Request/response models for the anomaly detection API.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """Types of anomalies."""

    OUTLIER = "outlier"
    PATTERN_DEVIATION = "pattern_deviation"
    DUPLICATE = "duplicate"
    MISSING_DATA = "missing_data"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    CROSS_FIELD_INCONSISTENCY = "cross_field_inconsistency"
    VALUE_SPIKE = "value_spike"
    FREQUENCY_ANOMALY = "frequency_anomaly"
    RULE_VIOLATION = "rule_violation"


# Response Models


class AnomalyResponse(BaseModel):
    """Single anomaly response."""

    id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    title: str
    description: str
    score: float = Field(..., ge=0, le=1)
    detected_at: datetime
    data_source: str
    record_ids: List[int] = []
    metadata: Dict[str, Any] = {}
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    false_positive: bool = False

    class Config:
        from_attributes = True


class AnomalyListResponse(BaseModel):
    """List of anomalies response."""

    anomalies: List[AnomalyResponse]
    total: int
    unresolved_count: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]


class AnomalyRuleResponse(BaseModel):
    """Anomaly rule response."""

    id: str
    name: str
    description: str
    rule_type: str
    field: str
    condition: str
    value: Any
    severity: AnomalySeverity
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AnomalyRuleListResponse(BaseModel):
    """List of rules response."""

    rules: List[AnomalyRuleResponse]
    total: int
    enabled_count: int


class AnomalyStatsResponse(BaseModel):
    """Anomaly statistics response."""

    total_detected: int
    unresolved_count: int
    resolved_count: int
    false_positive_count: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    detection_rate_24h: float
    resolution_rate: float


class DetectionResultResponse(BaseModel):
    """Result of running detection."""

    success: bool
    message: str
    anomalies_detected: int
    detection_time_ms: float
    anomalies: List[AnomalyResponse] = []


# Request Models


class DetectAnomaliesRequest(BaseModel):
    """Request to run anomaly detection."""

    data_source: Optional[str] = None
    jurisdiction_id: Optional[int] = None
    record_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    enable_statistical: bool = True
    enable_ml: bool = True
    enable_rules: bool = True
    limit: int = Field(default=1000, ge=1, le=10000)


class AnomalyRuleCreate(BaseModel):
    """Create a new anomaly rule."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=1000)
    rule_type: str = Field(..., pattern="^(threshold|pattern|comparison)$")
    field: str = Field(..., min_length=1)
    condition: str = Field(
        ..., pattern="^(gt|lt|gte|lte|eq|ne|contains|not_contains|regex)$"
    )
    value: Any
    severity: AnomalySeverity = AnomalySeverity.MEDIUM
    enabled: bool = True


class AnomalyRuleUpdate(BaseModel):
    """Update an anomaly rule."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    field: Optional[str] = None
    condition: Optional[str] = None
    value: Optional[Any] = None
    severity: Optional[AnomalySeverity] = None
    enabled: Optional[bool] = None


class ResolveAnomalyRequest(BaseModel):
    """Resolve an anomaly."""

    false_positive: bool = False
    notes: Optional[str] = None


class AnomalyConfigUpdate(BaseModel):
    """Update detection configuration."""

    z_score_threshold: Optional[float] = Field(None, ge=1.0, le=10.0)
    iqr_multiplier: Optional[float] = Field(None, ge=1.0, le=5.0)
    min_data_points: Optional[int] = Field(None, ge=5, le=100)
    isolation_forest_contamination: Optional[float] = Field(None, ge=0.01, le=0.5)
    enable_statistical: Optional[bool] = None
    enable_ml: Optional[bool] = None
    enable_rules: Optional[bool] = None
    lookback_days: Optional[int] = Field(None, ge=1, le=365)


class AnomalyConfigResponse(BaseModel):
    """Current detection configuration."""

    z_score_threshold: float
    iqr_multiplier: float
    min_data_points: int
    isolation_forest_contamination: float
    enable_statistical: bool
    enable_ml: bool
    enable_rules: bool
    lookback_days: int
    batch_size: int
