"""
Alembic migration: Create comments and notifications tables

Revision ID: 2a3b4c5d6e7f
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers
revision = '2a3b4c5d6e7f'
down_revision = None  # Update to your latest migration revision
branch_labels = None
depends_on = None


def upgrade():
    # Comments table
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('record_id', sa.Integer, sa.ForeignKey('records.id'), nullable=True, index=True),
        sa.Column('entity_id', sa.Integer, sa.ForeignKey('entities.id'), nullable=True, index=True),
        sa.Column('parent_id', sa.Integer, sa.ForeignKey('comments.id'), nullable=True, index=True),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
    )

    # Notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('type', sa.String(50), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('read', sa.Boolean, default=False, index=True),
        sa.Column('data', JSON, nullable=True),
        sa.Column('action_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
    )

    # Index for fast "unread notifications for user" query
    op.create_index(
        'ix_notifications_user_unread',
        'notifications',
        ['user_id', 'read'],
        postgresql_where=sa.text("read = false"),
    )


def downgrade():
    op.drop_index('ix_notifications_user_unread', 'notifications')
    op.drop_table('notifications')
    op.drop_table('comments')
