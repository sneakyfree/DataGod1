"""
Snapshot API Routes (DNA Strand Gene 2.3: Immutable Snapshots)

Provides endpoints for creating and retrieving immutable data snapshots
with SQLite DB persistence and SHA-256 integrity verification.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import hashlib
import json
import uuid
import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/snapshots", tags=["snapshots"])

# --- DB-Backed Snapshot Store ---

_SNAPSHOT_DB = os.getenv("SNAPSHOT_DB", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "snapshots.db"
))


def _get_db() -> sqlite3.Connection:
    """Get snapshot DB connection, creating table if needed."""
    conn = sqlite3.connect(_SNAPSHOT_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            data_hash TEXT NOT NULL,
            source TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            data_json TEXT NOT NULL,
            schema_version TEXT DEFAULT '1.0.0',
            model_version TEXT DEFAULT '1.0.0',
            rules_version TEXT DEFAULT '1.0.0'
        )
    """)
    conn.commit()
    return conn


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
    """Compute SHA-256 hash of data for reproducibility."""
    json_bytes = json.dumps(data, sort_keys=True, default=str).encode('utf-8')
    return hashlib.sha256(json_bytes).hexdigest()


def _row_to_snapshot(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert DB row to snapshot dict."""
    return {
        "snapshot_id": row["snapshot_id"],
        "data_hash": row["data_hash"],
        "source": row["source"],
        "description": row["description"],
        "created_at": row["created_at"],
        "data": json.loads(row["data_json"]),
        "schema_version": row["schema_version"],
        "model_version": row["model_version"],
        "rules_version": row["rules_version"],
    }


@router.post("/", response_model=SnapshotResponse)
async def create_snapshot(request: SnapshotCreate):
    """
    Create an immutable snapshot of data.

    Persists to SQLite with SHA-256 hash for integrity verification.
    """
    snapshot_id = f"snap_{uuid.uuid4().hex[:16]}"
    data_hash = compute_data_hash(request.data)
    created_at = datetime.utcnow().isoformat() + "Z"

    db = _get_db()
    try:
        db.execute(
            """INSERT INTO audit_snapshots
               (snapshot_id, data_hash, source, description, created_at, data_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (snapshot_id, data_hash, request.source, request.description,
             created_at, json.dumps(request.data, sort_keys=True, default=str))
        )
        db.commit()
    finally:
        db.close()

    return SnapshotResponse(
        snapshot_id=snapshot_id,
        data_hash=data_hash,
        source=request.source,
        description=request.description,
        created_at=created_at,
        data=request.data,
    )


@router.get("/{snapshot_id}", response_model=SnapshotResponse)
async def get_snapshot(snapshot_id: str):
    """
    Retrieve an immutable snapshot by ID.

    Verifies SHA-256 hash integrity on every read.
    """
    db = _get_db()
    try:
        row = db.execute(
            "SELECT * FROM audit_snapshots WHERE snapshot_id = ?", (snapshot_id,)
        ).fetchone()
    finally:
        db.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")

    snapshot = _row_to_snapshot(row)

    # Verify data integrity on read
    stored_hash = snapshot["data_hash"]
    computed_hash = compute_data_hash(snapshot["data"])
    if stored_hash != computed_hash:
        raise HTTPException(
            status_code=500,
            detail="Data integrity violation: snapshot SHA-256 hash mismatch"
        )

    return SnapshotResponse(**snapshot)


@router.get("/", response_model=List[SnapshotSummary])
async def list_snapshots(
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """List available snapshots."""
    db = _get_db()
    try:
        if source:
            rows = db.execute(
                "SELECT snapshot_id, data_hash, source, description, created_at "
                "FROM audit_snapshots WHERE source = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (source, limit, offset)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT snapshot_id, data_hash, source, description, created_at "
                "FROM audit_snapshots ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
    finally:
        db.close()

    return [
        SnapshotSummary(
            snapshot_id=r["snapshot_id"],
            data_hash=r["data_hash"],
            source=r["source"],
            description=r["description"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/{snapshot_id}/verify")
async def verify_snapshot(snapshot_id: str):
    """
    Verify the integrity of a snapshot.

    Recomputes SHA-256 from stored data and compares to stored hash.
    """
    db = _get_db()
    try:
        row = db.execute(
            "SELECT * FROM audit_snapshots WHERE snapshot_id = ?", (snapshot_id,)
        ).fetchone()
    finally:
        db.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")

    snapshot = _row_to_snapshot(row)
    stored_hash = snapshot["data_hash"]
    computed_hash = compute_data_hash(snapshot["data"])

    return {
        "snapshot_id": snapshot_id,
        "stored_hash": stored_hash,
        "computed_hash": computed_hash,
        "verified": stored_hash == computed_hash,
        "algorithm": "sha256",
        "verified_at": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/compare/{snapshot_before}/{snapshot_after}", response_model=DeltaReport)
async def compare_snapshots(snapshot_before: str, snapshot_after: str):
    """
    Compare two snapshots and return a delta report.
    """
    db = _get_db()
    try:
        row_before = db.execute(
            "SELECT * FROM audit_snapshots WHERE snapshot_id = ?", (snapshot_before,)
        ).fetchone()
        row_after = db.execute(
            "SELECT * FROM audit_snapshots WHERE snapshot_id = ?", (snapshot_after,)
        ).fetchone()
    finally:
        db.close()

    if not row_before:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_before} not found")
    if not row_after:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_after} not found")

    before = json.loads(row_before["data_json"])
    after = json.loads(row_after["data_json"])

    changes = []
    all_keys = set(before.keys()) | set(after.keys())
    for key in sorted(all_keys):
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
