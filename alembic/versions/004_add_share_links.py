"""Add share_links table for shareable record/entity links

Revision ID: 004_add_share_links
Revises: 003_add_user_features
Create Date: 2025-01-06

This migration adds the share_links table for creating
shareable public links to records and entities.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_share_links'
down_revision = '003_add_user_features'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create share_links table
    op.create_table(
        'share_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # Unique token for public access
        sa.Column('token', sa.String(64), nullable=False),

        # Can share either a record or an entity
        sa.Column('record_id', sa.Integer(), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),

        # Type for quick filtering ('record' or 'entity')
        sa.Column('share_type', sa.String(20), nullable=False),

        # Optional message from sharer
        sa.Column('message', sa.Text(), nullable=True),

        # Expiration and status
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),

        # Analytics
        sa.Column('view_count', sa.Integer(), default=0, nullable=False),
        sa.Column('last_viewed', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['record_id'], ['records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
    )

    # Create indexes for share_links
    op.create_index('idx_share_token', 'share_links', ['token'], unique=True)
    op.create_index('idx_share_user', 'share_links', ['user_id'])
    op.create_index('idx_share_record', 'share_links', ['record_id'])
    op.create_index('idx_share_entity', 'share_links', ['entity_id'])
    op.create_index('idx_share_type', 'share_links', ['share_type'])
    op.create_index('idx_share_active', 'share_links', ['is_active'])
    op.create_index('idx_share_expires', 'share_links', ['expires_at'])


def downgrade() -> None:
    # Drop share_links indexes and table
    op.drop_index('idx_share_expires', table_name='share_links')
    op.drop_index('idx_share_active', table_name='share_links')
    op.drop_index('idx_share_type', table_name='share_links')
    op.drop_index('idx_share_entity', table_name='share_links')
    op.drop_index('idx_share_record', table_name='share_links')
    op.drop_index('idx_share_user', table_name='share_links')
    op.drop_index('idx_share_token', table_name='share_links')
    op.drop_table('share_links')
