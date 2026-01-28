"""Add provenance, audit log, and schema version tables

Revision ID: 006_add_provenance_audit
Revises: 005_add_fips_and_coverage
Create Date: 2026-01-18

Phase 1.2 of GOAT DataGod DNA Strand Master Plan:
- Add provenance columns to records table for audit-grade data tracking
- Create audit_log table with WORM (Write-Once-Read-Many) constraints
- Create schema_version table for migration checksums and version pinning
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '006_add_provenance_audit'
down_revision = '005_add_fips_and_coverage'
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # 1. ADD PROVENANCE COLUMNS TO RECORDS TABLE
    # =========================================================================
    # These columns enable audit-grade data tracking as per DNA Strand Master Plan
    
    op.add_column('records', sa.Column(
        'source_system', 
        sa.String(100), 
        nullable=True,
        comment='Canonical source system identifier (e.g., county-recorders-la, usda-fsa)'
    ))
    
    op.add_column('records', sa.Column(
        'collected_at',
        sa.DateTime,
        nullable=True,
        comment='Timestamp when data was actually collected from source'
    ))
    
    op.add_column('records', sa.Column(
        'query_hash',
        sa.String(64),
        nullable=True,
        comment='SHA-256 hash of the query/request that produced this record'
    ))
    
    op.add_column('records', sa.Column(
        'source_snapshot_id',
        sa.String(100),
        nullable=True,
        comment='Reference to point-in-time snapshot for reproducibility'
    ))
    
    op.add_column('records', sa.Column(
        'data_version',
        sa.Integer,
        nullable=False,
        server_default='1',
        comment='Version counter for tracking record changes'
    ))
    
    # Add indexes for provenance queries
    op.create_index('idx_record_source_system', 'records', ['source_system'])
    op.create_index('idx_record_collected_at', 'records', ['collected_at'])
    op.create_index('idx_record_query_hash', 'records', ['query_hash'])
    
    # =========================================================================
    # 2. CREATE AUDIT_LOG TABLE (WORM - Write Once Read Many)
    # =========================================================================
    # Immutable audit trail for compliance and reproducibility
    
    op.create_table(
        'audit_log',
        # Primary key
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        
        # Event identification
        sa.Column('event_id', sa.String(36), nullable=False, unique=True, index=True,
                  comment='UUID for this audit event'),
        sa.Column('event_type', sa.String(50), nullable=False, index=True,
                  comment='Type: record_created, record_updated, search_executed, export_generated, etc.'),
        sa.Column('event_timestamp', sa.DateTime, nullable=False, default=datetime.utcnow, index=True,
                  comment='When the event occurred (immutable)'),
        
        # Actor information
        sa.Column('actor_id', sa.Integer, nullable=True, index=True,
                  comment='User ID who performed the action (null for system actions)'),
        sa.Column('actor_type', sa.String(20), nullable=False, default='user',
                  comment='user, system, scraper, api_client'),
        sa.Column('actor_ip', sa.String(45), nullable=True,
                  comment='IP address of the actor (IPv6 compatible)'),
        sa.Column('actor_user_agent', sa.String(500), nullable=True,
                  comment='User agent string for web requests'),
        
        # Target of the action
        sa.Column('target_type', sa.String(50), nullable=True, index=True,
                  comment='record, entity, user, search, export, etc.'),
        sa.Column('target_id', sa.String(100), nullable=True, index=True,
                  comment='ID of the target object'),
        
        # Action details
        sa.Column('action', sa.String(100), nullable=False, index=True,
                  comment='Specific action: create, update, delete, view, search, export'),
        sa.Column('action_data', sa.JSON, nullable=True,
                  comment='JSON blob of action-specific data (search params, old/new values, etc.)'),
        
        # Provenance
        sa.Column('request_id', sa.String(36), nullable=True, index=True,
                  comment='Request correlation ID for tracing'),
        sa.Column('session_id', sa.String(64), nullable=True,
                  comment='Session ID if applicable'),
        
        # Response/Result
        sa.Column('response_hash', sa.String(64), nullable=True,
                  comment='SHA-256 hash of the response data for reproducibility'),
        sa.Column('success', sa.Boolean, nullable=False, default=True,
                  comment='Whether the action succeeded'),
        sa.Column('error_message', sa.Text, nullable=True,
                  comment='Error message if action failed'),
        
        # Integrity
        sa.Column('checksum', sa.String(64), nullable=False,
                  comment='SHA-256 checksum of this log entry for tamper detection'),
        sa.Column('previous_checksum', sa.String(64), nullable=True,
                  comment='Checksum of previous entry (blockchain-style chain)'),
                  
        # Note: No updated_at column - WORM means write-once
    )
    
    # Create composite indexes for common queries
    op.create_index('idx_audit_actor_time', 'audit_log', ['actor_id', 'event_timestamp'])
    op.create_index('idx_audit_target_time', 'audit_log', ['target_type', 'target_id', 'event_timestamp'])
    op.create_index('idx_audit_event_type_time', 'audit_log', ['event_type', 'event_timestamp'])
    
    # =========================================================================
    # 3. CREATE SCHEMA_VERSION TABLE
    # =========================================================================
    # Track schema migrations with checksums for version pinning
    
    op.create_table(
        'schema_version',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        
        # Version identification
        sa.Column('version_id', sa.String(50), nullable=False, unique=True, index=True,
                  comment='Alembic revision ID'),
        sa.Column('version_name', sa.String(255), nullable=True,
                  comment='Human-readable migration name'),
        sa.Column('version_number', sa.Integer, nullable=False,
                  comment='Sequential version number'),
        
        # Migration metadata
        sa.Column('applied_at', sa.DateTime, nullable=False, default=datetime.utcnow,
                  comment='When this migration was applied'),
        sa.Column('applied_by', sa.String(100), nullable=True,
                  comment='User/system that applied the migration'),
        
        # Checksums for integrity
        sa.Column('migration_checksum', sa.String(64), nullable=False,
                  comment='SHA-256 hash of the migration file'),
        sa.Column('schema_checksum', sa.String(64), nullable=True,
                  comment='SHA-256 hash of schema state after migration'),
        
        # Rollback tracking
        sa.Column('is_current', sa.Boolean, nullable=False, default=True,
                  comment='Whether this is the current active version'),
        sa.Column('rollback_possible', sa.Boolean, nullable=False, default=True,
                  comment='Whether this migration can be safely rolled back'),
        
        # Notes
        sa.Column('notes', sa.Text, nullable=True,
                  comment='Migration notes or warnings'),
    )
    
    # =========================================================================
    # 4. CREATE DATA_SNAPSHOT TABLE
    # =========================================================================
    # Store point-in-time snapshots for reproducibility
    
    op.create_table(
        'data_snapshot',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        
        # Snapshot identification  
        sa.Column('snapshot_id', sa.String(36), nullable=False, unique=True, index=True,
                  comment='UUID for this snapshot'),
        sa.Column('snapshot_type', sa.String(50), nullable=False, index=True,
                  comment='Type: record, search_result, export, jurisdiction_state'),
        
        # Timing
        sa.Column('created_at', sa.DateTime, nullable=False, default=datetime.utcnow, index=True),
        sa.Column('expires_at', sa.DateTime, nullable=True,
                  comment='When this snapshot can be garbage collected'),
        
        # Target
        sa.Column('target_type', sa.String(50), nullable=True),
        sa.Column('target_id', sa.String(100), nullable=True),
        
        # Snapshot data
        sa.Column('data', sa.JSON, nullable=False,
                  comment='The actual snapshot data'),
        sa.Column('data_checksum', sa.String(64), nullable=False,
                  comment='SHA-256 of the data for integrity verification'),
        
        # Context
        sa.Column('query_params', sa.JSON, nullable=True,
                  comment='Query parameters that produced this snapshot'),
        sa.Column('schema_version', sa.String(50), nullable=True,
                  comment='Schema version at time of snapshot'),
        sa.Column('model_version', sa.String(50), nullable=True,
                  comment='ML model version if applicable'),
        
        # Creator
        sa.Column('created_by_user_id', sa.Integer, nullable=True),
        sa.Column('created_by_request_id', sa.String(36), nullable=True),
    )
    
    op.create_index('idx_snapshot_type_target', 'data_snapshot', ['snapshot_type', 'target_type', 'target_id'])
    op.create_index('idx_snapshot_expires', 'data_snapshot', ['expires_at'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('data_snapshot')
    op.drop_table('schema_version')
    op.drop_table('audit_log')
    
    # Drop indexes first
    op.drop_index('idx_record_query_hash', 'records')
    op.drop_index('idx_record_collected_at', 'records')
    op.drop_index('idx_record_source_system', 'records')
    
    # Remove provenance columns from records
    op.drop_column('records', 'data_version')
    op.drop_column('records', 'source_snapshot_id')
    op.drop_column('records', 'query_hash')
    op.drop_column('records', 'collected_at')
    op.drop_column('records', 'source_system')
