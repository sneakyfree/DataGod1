"""
Anomaly Detection API Routes

FastAPI router for anomaly detection endpoints.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

# Import schemas
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datagod.schemas.anomaly_schemas import (
    AnomalyResponse,
    AnomalyListResponse,
    AnomalyRuleResponse,
    AnomalyRuleListResponse,
    AnomalyStatsResponse,
    DetectionResultResponse,
    DetectAnomaliesRequest,
    AnomalyRuleCreate,
    AnomalyRuleUpdate,
    ResolveAnomalyRequest,
    AnomalyConfigUpdate,
    AnomalyConfigResponse,
    AnomalySeverity,
)
from datagod.ml.anomaly_detector import (
    AnomalyDetector,
    AnomalyConfig,
    AnomalyRule,
    get_anomaly_detector,
    AnomalySeverity as DetectorSeverity,
)

try:
    from api.src.db import get_db
    from api.src.api_v2 import get_current_active_user, User, RoleChecker
except ImportError:
    from db import get_db
    from api_v2 import get_current_active_user, User, RoleChecker

import pandas as pd

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.post("/detect", response_model=DetectionResultResponse)
async def detect_anomalies(
    request: DetectAnomaliesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Run anomaly detection on records.
    
    Executes configured detection methods (statistical, ML, rule-based)
    on matching records and returns any detected anomalies.
    """
    start_time = time.time()
    
    try:
        # Build query for records
        from datagod.models import Record, Jurisdiction
        
        query = db.query(Record)
        
        if request.jurisdiction_id:
            query = query.filter(Record.jurisdiction_id == request.jurisdiction_id)
        
        if request.record_type:
            query = query.filter(Record.record_type == request.record_type)
        
        if request.date_from:
            query = query.filter(Record.created_at >= request.date_from)
        
        if request.date_to:
            query = query.filter(Record.created_at <= request.date_to)
        
        # Limit records
        records = query.limit(request.limit).all()
        
        if not records:
            return DetectionResultResponse(
                success=True,
                message="No records found matching criteria",
                anomalies_detected=0,
                detection_time_ms=(time.time() - start_time) * 1000,
                anomalies=[]
            )
        
        # Convert to DataFrame
        record_dicts = []
        for r in records:
            record_dict = {
                'id': r.id,
                'jurisdiction_id': r.jurisdiction_id,
                'record_type': r.record_type,
                'created_at': r.created_at,
            }
            # Add numeric fields if present
            if hasattr(r, 'amount') and r.amount:
                record_dict['amount'] = float(r.amount)
            if hasattr(r, 'data') and r.data:
                # Extract numeric fields from JSON data
                if isinstance(r.data, dict):
                    for k, v in r.data.items():
                        if isinstance(v, (int, float)):
                            record_dict[k] = v
            record_dicts.append(record_dict)
        
        df = pd.DataFrame(record_dicts)
        
        # Configure and run detector
        detector = get_anomaly_detector()
        detector.config.enable_statistical = request.enable_statistical
        detector.config.enable_ml = request.enable_ml
        detector.config.enable_rules = request.enable_rules
        
        data_source = request.data_source or f"query_{datetime.utcnow().isoformat()}"
        anomalies = detector.detect_all(df, data_source)
        
        # Convert to response format
        anomaly_responses = [
            AnomalyResponse(
                id=a.id,
                anomaly_type=a.anomaly_type.value,
                severity=a.severity.value,
                title=a.title,
                description=a.description,
                score=a.score,
                detected_at=a.detected_at,
                data_source=a.data_source,
                record_ids=a.record_ids,
                metadata=a.metadata,
                resolved=a.resolved,
                resolved_at=a.resolved_at,
                resolved_by=a.resolved_by,
                false_positive=a.false_positive,
            )
            for a in anomalies
        ]
        
        return DetectionResultResponse(
            success=True,
            message=f"Detection completed on {len(records)} records",
            anomalies_detected=len(anomalies),
            detection_time_ms=(time.time() - start_time) * 1000,
            anomalies=anomaly_responses
        )
        
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@router.get("", response_model=AnomalyListResponse)
async def list_anomalies(
    include_resolved: bool = Query(False, description="Include resolved anomalies"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    anomaly_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of detected anomalies.
    """
    detector = get_anomaly_detector()
    all_anomalies = detector.get_all_anomalies(include_resolved=include_resolved)
    
    # Apply filters
    if severity:
        all_anomalies = [a for a in all_anomalies if a.severity.value == severity]
    
    if anomaly_type:
        all_anomalies = [a for a in all_anomalies if a.anomaly_type.value == anomaly_type]
    
    # Calculate stats
    unresolved = [a for a in detector.get_all_anomalies(include_resolved=True) if not a.resolved]
    by_severity = {}
    by_type = {}
    
    for a in all_anomalies:
        sev = a.severity.value
        typ = a.anomaly_type.value
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_type[typ] = by_type.get(typ, 0) + 1
    
    # Paginate
    paginated = all_anomalies[offset:offset + limit]
    
    # Convert to response
    anomaly_responses = [
        AnomalyResponse(
            id=a.id,
            anomaly_type=a.anomaly_type.value,
            severity=a.severity.value,
            title=a.title,
            description=a.description,
            score=a.score,
            detected_at=a.detected_at,
            data_source=a.data_source,
            record_ids=a.record_ids,
            metadata=a.metadata,
            resolved=a.resolved,
            resolved_at=a.resolved_at,
            resolved_by=a.resolved_by,
            false_positive=a.false_positive,
        )
        for a in paginated
    ]
    
    return AnomalyListResponse(
        anomalies=anomaly_responses,
        total=len(all_anomalies),
        unresolved_count=len(unresolved),
        by_severity=by_severity,
        by_type=by_type
    )


@router.get("/{anomaly_id}", response_model=AnomalyResponse)
async def get_anomaly(
    anomaly_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific anomaly by ID.
    """
    detector = get_anomaly_detector()
    anomaly = detector.get_anomaly(anomaly_id)
    
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    
    return AnomalyResponse(
        id=anomaly.id,
        anomaly_type=anomaly.anomaly_type.value,
        severity=anomaly.severity.value,
        title=anomaly.title,
        description=anomaly.description,
        score=anomaly.score,
        detected_at=anomaly.detected_at,
        data_source=anomaly.data_source,
        record_ids=anomaly.record_ids,
        metadata=anomaly.metadata,
        resolved=anomaly.resolved,
        resolved_at=anomaly.resolved_at,
        resolved_by=anomaly.resolved_by,
        false_positive=anomaly.false_positive,
    )


@router.post("/{anomaly_id}/resolve")
async def resolve_anomaly(
    anomaly_id: str,
    request: ResolveAnomalyRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark an anomaly as resolved.
    """
    detector = get_anomaly_detector()
    
    success = detector.resolve_anomaly(
        anomaly_id,
        resolved_by=current_user.username,
        false_positive=request.false_positive
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    
    return {"message": "Anomaly resolved", "anomaly_id": anomaly_id}


@router.get("/stats/summary", response_model=AnomalyStatsResponse)
async def get_anomaly_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get anomaly detection statistics.
    """
    detector = get_anomaly_detector()
    all_anomalies = detector.get_all_anomalies(include_resolved=True)
    
    resolved = [a for a in all_anomalies if a.resolved]
    unresolved = [a for a in all_anomalies if not a.resolved]
    false_positives = [a for a in all_anomalies if a.false_positive]
    
    # Last 24 hours
    cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    recent = [a for a in all_anomalies if a.detected_at >= cutoff]
    
    by_severity = {}
    by_type = {}
    for a in all_anomalies:
        sev = a.severity.value
        typ = a.anomaly_type.value
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_type[typ] = by_type.get(typ, 0) + 1
    
    total = len(all_anomalies)
    resolution_rate = len(resolved) / total * 100 if total > 0 else 0
    
    return AnomalyStatsResponse(
        total_detected=total,
        unresolved_count=len(unresolved),
        resolved_count=len(resolved),
        false_positive_count=len(false_positives),
        by_severity=by_severity,
        by_type=by_type,
        detection_rate_24h=len(recent),
        resolution_rate=round(resolution_rate, 2)
    )


# ==================== RULES ENDPOINTS ====================

@router.get("/rules", response_model=AnomalyRuleListResponse)
async def list_rules(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all anomaly detection rules.
    """
    detector = get_anomaly_detector()
    rules = detector.get_rules()
    
    rule_responses = [
        AnomalyRuleResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            rule_type=r.rule_type,
            field=r.field,
            condition=r.condition,
            value=r.value,
            severity=r.severity.value,
            enabled=r.enabled,
            created_at=r.created_at,
        )
        for r in rules
    ]
    
    enabled_count = sum(1 for r in rules if r.enabled)
    
    return AnomalyRuleListResponse(
        rules=rule_responses,
        total=len(rules),
        enabled_count=enabled_count
    )


@router.post("/rules", response_model=AnomalyRuleResponse, dependencies=[Depends(RoleChecker(["admin"]))])
async def create_rule(
    rule_data: AnomalyRuleCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new anomaly detection rule. Admin only.
    """
    import uuid
    
    detector = get_anomaly_detector()
    
    # Map severity
    severity_map = {
        AnomalySeverity.LOW: DetectorSeverity.LOW,
        AnomalySeverity.MEDIUM: DetectorSeverity.MEDIUM,
        AnomalySeverity.HIGH: DetectorSeverity.HIGH,
        AnomalySeverity.CRITICAL: DetectorSeverity.CRITICAL,
    }
    
    rule = AnomalyRule(
        id=str(uuid.uuid4())[:8],
        name=rule_data.name,
        description=rule_data.description,
        rule_type=rule_data.rule_type,
        field=rule_data.field,
        condition=rule_data.condition,
        value=rule_data.value,
        severity=severity_map.get(rule_data.severity, DetectorSeverity.MEDIUM),
        enabled=rule_data.enabled,
    )
    
    detector.add_rule(rule)
    
    return AnomalyRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        field=rule.field,
        condition=rule.condition,
        value=rule.value,
        severity=rule.severity.value,
        enabled=rule.enabled,
        created_at=rule.created_at,
    )


@router.put("/rules/{rule_id}", response_model=AnomalyRuleResponse, dependencies=[Depends(RoleChecker(["admin"]))])
async def update_rule(
    rule_id: str,
    update_data: AnomalyRuleUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an anomaly detection rule. Admin only.
    """
    detector = get_anomaly_detector()
    
    if rule_id not in detector.rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = detector.rules[rule_id]
    
    if update_data.name is not None:
        rule.name = update_data.name
    if update_data.description is not None:
        rule.description = update_data.description
    if update_data.field is not None:
        rule.field = update_data.field
    if update_data.condition is not None:
        rule.condition = update_data.condition
    if update_data.value is not None:
        rule.value = update_data.value
    if update_data.enabled is not None:
        rule.enabled = update_data.enabled
    if update_data.severity is not None:
        severity_map = {
            AnomalySeverity.LOW: DetectorSeverity.LOW,
            AnomalySeverity.MEDIUM: DetectorSeverity.MEDIUM,
            AnomalySeverity.HIGH: DetectorSeverity.HIGH,
            AnomalySeverity.CRITICAL: DetectorSeverity.CRITICAL,
        }
        rule.severity = severity_map.get(update_data.severity, DetectorSeverity.MEDIUM)
    
    return AnomalyRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        field=rule.field,
        condition=rule.condition,
        value=rule.value,
        severity=rule.severity.value,
        enabled=rule.enabled,
        created_at=rule.created_at,
    )


@router.delete("/rules/{rule_id}", dependencies=[Depends(RoleChecker(["admin"]))])
async def delete_rule(
    rule_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an anomaly detection rule. Admin only.
    """
    detector = get_anomaly_detector()
    
    if not detector.remove_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"message": "Rule deleted", "rule_id": rule_id}


# ==================== CONFIG ENDPOINTS ====================

@router.get("/config", response_model=AnomalyConfigResponse)
async def get_config(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current anomaly detection configuration.
    """
    detector = get_anomaly_detector()
    config = detector.config
    
    return AnomalyConfigResponse(
        z_score_threshold=config.z_score_threshold,
        iqr_multiplier=config.iqr_multiplier,
        min_data_points=config.min_data_points,
        isolation_forest_contamination=config.isolation_forest_contamination,
        enable_statistical=config.enable_statistical,
        enable_ml=config.enable_ml,
        enable_rules=config.enable_rules,
        lookback_days=config.lookback_days,
        batch_size=config.batch_size,
    )


@router.patch("/config", response_model=AnomalyConfigResponse, dependencies=[Depends(RoleChecker(["admin"]))])
async def update_config(
    update_data: AnomalyConfigUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update anomaly detection configuration. Admin only.
    """
    detector = get_anomaly_detector()
    config = detector.config
    
    if update_data.z_score_threshold is not None:
        config.z_score_threshold = update_data.z_score_threshold
    if update_data.iqr_multiplier is not None:
        config.iqr_multiplier = update_data.iqr_multiplier
    if update_data.min_data_points is not None:
        config.min_data_points = update_data.min_data_points
    if update_data.isolation_forest_contamination is not None:
        config.isolation_forest_contamination = update_data.isolation_forest_contamination
    if update_data.enable_statistical is not None:
        config.enable_statistical = update_data.enable_statistical
    if update_data.enable_ml is not None:
        config.enable_ml = update_data.enable_ml
    if update_data.enable_rules is not None:
        config.enable_rules = update_data.enable_rules
    if update_data.lookback_days is not None:
        config.lookback_days = update_data.lookback_days
    
    return AnomalyConfigResponse(
        z_score_threshold=config.z_score_threshold,
        iqr_multiplier=config.iqr_multiplier,
        min_data_points=config.min_data_points,
        isolation_forest_contamination=config.isolation_forest_contamination,
        enable_statistical=config.enable_statistical,
        enable_ml=config.enable_ml,
        enable_rules=config.enable_rules,
        lookback_days=config.lookback_days,
        batch_size=config.batch_size,
    )
