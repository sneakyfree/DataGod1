"""Add user feature tables (saved searches, favorites, activities)

Revision ID: 003_add_user_features
Revises: 002_add_users_table
Create Date: 2025-01-06

This migration adds tables for user engagement features:
- saved_searches: User's saved search queries with notification settings
- user_favorites: User's favorited records and entities
- user_activities: User activity tracking for history and analytics
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import JSON


# revision identifiers, used by Alembic.
revision = '003_add_user_features'
down_revision = '002_add_users_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create saved_searches table
    op.create_table(
        'saved_searches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # Search details
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Search parameters stored as JSON
        sa.Column('search_params', JSON, nullable=False),

        # Usage tracking
        sa.Column('last_run', sa.DateTime(), nullable=True),
        sa.Column('run_count', sa.Integer(), default=0, nullable=False),

        # Notification settings
        sa.Column('notify_on_new_results', sa.Boolean(), default=False, nullable=False),
        sa.Column('notification_frequency', sa.String(50), default='daily', nullable=True),
        sa.Column('last_notification', sa.DateTime(), nullable=True),
        sa.Column('last_result_count', sa.Integer(), default=0, nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create indexes for saved_searches
    op.create_index('idx_saved_search_user', 'saved_searches', ['user_id'])
    op.create_index('idx_saved_search_name', 'saved_searches', ['name'])
    op.create_index('idx_saved_search_notify', 'saved_searches', ['notify_on_new_results'])

    # Create user_favorites table
    op.create_table(
        'user_favorites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # Can favorite either a record or an entity
        sa.Column('record_id', sa.Integer(), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),

        # Type for quick filtering
        sa.Column('favorite_type', sa.String(50), nullable=False),

        # User notes
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', JSON, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['record_id'], ['records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
    )

    # Create indexes for user_favorites
    op.create_index('idx_favorite_user', 'user_favorites', ['user_id'])
    op.create_index('idx_favorite_record', 'user_favorites', ['record_id'])
    op.create_index('idx_favorite_entity', 'user_favorites', ['entity_id'])
    op.create_index('idx_favorite_type', 'user_favorites', ['favorite_type'])
    # Unique constraint to prevent duplicate favorites
    op.create_index('idx_favorite_unique_record', 'user_favorites', ['user_id', 'record_id'], unique=True,
                    postgresql_where=sa.text('record_id IS NOT NULL'))
    op.create_index('idx_favorite_unique_entity', 'user_favorites', ['user_id', 'entity_id'], unique=True,
                    postgresql_where=sa.text('entity_id IS NOT NULL'))

    # Create user_activities table
    op.create_table(
        'user_activities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # Activity details
        sa.Column('activity_type', sa.String(50), nullable=False),

        # Reference to what was accessed
        sa.Column('record_id', sa.Integer(), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('search_id', sa.Integer(), nullable=True),

        # Activity context
        sa.Column('activity_data', JSON, nullable=True),

        # Session info
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['record_id'], ['records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['search_id'], ['saved_searches.id'], ondelete='SET NULL'),
    )

    # Create indexes for user_activities
    op.create_index('idx_activity_user', 'user_activities', ['user_id'])
    op.create_index('idx_activity_type', 'user_activities', ['activity_type'])
    op.create_index('idx_activity_created', 'user_activities', ['created_at'])
    op.create_index('idx_activity_record', 'user_activities', ['record_id'])
    op.create_index('idx_activity_entity', 'user_activities', ['entity_id'])


def downgrade() -> None:
    # Drop user_activities indexes and table
    op.drop_index('idx_activity_entity', table_name='user_activities')
    op.drop_index('idx_activity_record', table_name='user_activities')
    op.drop_index('idx_activity_created', table_name='user_activities')
    op.drop_index('idx_activity_type', table_name='user_activities')
    op.drop_index('idx_activity_user', table_name='user_activities')
    op.drop_table('user_activities')

    # Drop user_favorites indexes and table
    try:
        op.drop_index('idx_favorite_unique_entity', table_name='user_favorites')
    except:
        pass  # Partial index may not exist on all databases
    try:
        op.drop_index('idx_favorite_unique_record', table_name='user_favorites')
    except:
        pass
    op.drop_index('idx_favorite_type', table_name='user_favorites')
    op.drop_index('idx_favorite_entity', table_name='user_favorites')
    op.drop_index('idx_favorite_record', table_name='user_favorites')
    op.drop_index('idx_favorite_user', table_name='user_favorites')
    op.drop_table('user_favorites')

    # Drop saved_searches indexes and table
    op.drop_index('idx_saved_search_notify', table_name='saved_searches')
    op.drop_index('idx_saved_search_name', table_name='saved_searches')
    op.drop_index('idx_saved_search_user', table_name='saved_searches')
    op.drop_table('saved_searches')
