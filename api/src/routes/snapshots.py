"""
Snapshot API Routes (Gap #9: Audit-Grade Reproducibility)

Provides endpoints for creating and retrieving immutable data snapshots.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import hashlib
import json
import uuid

router = APIRouter(prefix="/snapshots", tags=["snapshots"])

# In-memory snapshot store (replace with DB in production)
_snapshots: Dict[str, Dict[str, Any]] = {}


class SnapshotCreate(BaseModel):
    """Request to create a snapshot."""
    data: Dict[str, Any]
    source: str
    description: Optional[str] = None


class SnapshotResponse(BaseModel):
    """Response containing snapshot details."""
    snapshot_id: str
    data_hash: str
    source: str
    description: Optional[str]
    created_at: str
    data: Dict[str, Any]
    schema_version: str = "1.0.0"
    model_version: str = "1.0.0"
    rules_version: str = "1.0.0"


class SnapshotSummary(BaseModel):
    """Summary of a snapshot without full data."""
    snapshot_id: str
    data_hash: str
    source: str
    description: Optional[str]
    created_at: str


class DeltaReport(BaseModel):
    """Report of changes between two snapshots."""
    snapshot_before: str
    snapshot_after: str
    changes: List[Dict[str, Any]]
    change_count: int


def compute_data_hash(data: Dict[str, Any]) -> str:
    """Compute SHA256 hash of data for reproducibility."""
    json_bytes = json.dumps(data, sort_keys=True, default=str).encode('utf-8')
    return hashlib.sha256(json_bytes).hexdigest()


@router.post("/", response_model=SnapshotResponse)
async def create_snapshot(request: SnapshotCreate):
    """
    Create an immutable snapshot of data.
    
    Returns a snapshot_id that can be used to retrieve the exact same data later.
    """
    snapshot_id = f"snap_{uuid.uuid4().hex[:16]}"
    data_hash = compute_data_hash(request.data)
    created_at = datetime.utcnow().isoformat() + "Z"
    
    snapshot = {
        "snapshot_id": snapshot_id,
        "data_hash": data_hash,
        "source": request.source,
        "description": request.description,
        "created_at": created_at,
        "data": request.data,
        "schema_version": "1.0.0",
        "model_version": "1.0.0",
        "rules_version": "1.0.0",
    }
    
    # Store immutably (in production, use append-only DB)
    _snapshots[snapshot_id] = snapshot
    
    return SnapshotResponse(**snapshot)


@router.get("/{snapshot_id}", response_model=SnapshotResponse)
async def get_snapshot(snapshot_id: str):
    """
    Retrieve an immutable snapshot by ID.
    
    The returned data is guaranteed to be identical to the original snapshot.
    """
    if snapshot_id not in _snapshots:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
    
    snapshot = _snapshots[snapshot_id]
    
    # Verify data integrity
    stored_hash = snapshot["data_hash"]
    computed_hash = compute_data_hash(snapshot["data"])
    
    if stored_hash != computed_hash:
        raise HTTPException(
            status_code=500,
            detail="Data integrity violation: snapshot hash mismatch"
        )
    
    return SnapshotResponse(**snapshot)


@router.get("/", response_model=List[SnapshotSummary])
async def list_snapshots(
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """List available snapshots."""
    snapshots = list(_snapshots.values())
    
    # Filter by source if provided
    if source:
        snapshots = [s for s in snapshots if s["source"] == source]
    
    # Sort by created_at descending
    snapshots.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Paginate
    snapshots = snapshots[offset:offset + limit]
    
    return [
        SnapshotSummary(
            snapshot_id=s["snapshot_id"],
            data_hash=s["data_hash"],
            source=s["source"],
            description=s["description"],
            created_at=s["created_at"]
        )
        for s in snapshots
    ]


@router.get("/{snapshot_id}/verify")
async def verify_snapshot(snapshot_id: str):
    """
    Verify the integrity of a snapshot.
    
    Returns verification status and hash comparison.
    """
    if snapshot_id not in _snapshots:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
    
    snapshot = _snapshots[snapshot_id]
    stored_hash = snapshot["data_hash"]
    computed_hash = compute_data_hash(snapshot["data"])
    
    return {
        "snapshot_id": snapshot_id,
        "stored_hash": stored_hash,
        "computed_hash": computed_hash,
        "verified": stored_hash == computed_hash,
        "verified_at": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/compare/{snapshot_before}/{snapshot_after}", response_model=DeltaReport)
async def compare_snapshots(snapshot_before: str, snapshot_after: str):
    """
    Compare two snapshots and return a delta report.
    
    Shows what changed between the two snapshots.
    """
    if snapshot_before not in _snapshots:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_before} not found")
    if snapshot_after not in _snapshots:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_after} not found")
    
    before = _snapshots[snapshot_before]["data"]
    after = _snapshots[snapshot_after]["data"]
    
    changes = []
    
    # Find all keys
    all_keys = set(before.keys()) | set(after.keys())
    
    for key in all_keys:
        old_value = before.get(key)
        new_value = after.get(key)
        
        if old_value != new_value:
            changes.append({
                "field": key,
                "old_value": old_value,
                "new_value": new_value,
                "reason": "data_change"
            })
    
    return DeltaReport(
        snapshot_before=snapshot_before,
        snapshot_after=snapshot_after,
        changes=changes,
        change_count=len(changes)
    )


# Export for API v2 inclusion
snapshots_router = router
