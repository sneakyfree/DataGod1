"""Add users table for authentication

Revision ID: 002_add_users_table
Revises: 001_initial_schema
Create Date: 2024-12-30

This migration adds the users table for authentication and user management.

Tables created:
- users: User accounts with authentication, roles, and subscription tracking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import JSON


# revision identifiers, used by Alembic.
revision = '002_add_users_table'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        # Primary key
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),

        # Authentication fields
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),

        # Profile information
        sa.Column('full_name', sa.String(255), nullable=True),

        # Account status
        sa.Column('disabled', sa.Boolean(), default=False, nullable=False),
        sa.Column('email_verified', sa.Boolean(), default=False, nullable=False),

        # Roles and permissions (stored as JSON array)
        sa.Column('roles', JSON, default=['user'], nullable=False),

        # Email verification
        sa.Column('email_verification_token', sa.String(255), nullable=True),
        sa.Column('email_verification_expires', sa.DateTime(), nullable=True),

        # Password reset
        sa.Column('password_reset_token', sa.String(255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(), nullable=True),

        # Login tracking
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('login_count', sa.Integer(), default=0, nullable=False),
        sa.Column('failed_login_count', sa.Integer(), default=0, nullable=False),
        sa.Column('last_failed_login', sa.DateTime(), nullable=True),

        # Account lockout
        sa.Column('locked_until', sa.DateTime(), nullable=True),

        # Subscription
        sa.Column('subscription_tier', sa.String(50), default='free', nullable=False),
        sa.Column('subscription_expires', sa.DateTime(), nullable=True),

        # Stripe integration
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),

        # API usage tracking
        sa.Column('api_calls_today', sa.Integer(), default=0, nullable=False),
        sa.Column('api_calls_reset_at', sa.DateTime(), nullable=True),
        sa.Column('exports_this_month', sa.Integer(), default=0, nullable=False),
        sa.Column('exports_reset_at', sa.DateTime(), nullable=True),

        # Additional profile data
        sa.Column('profile_data', JSON, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.PrimaryKeyConstraint('id')
    )

    # Create unique constraints
    op.create_index('idx_user_username', 'users', ['username'], unique=True)
    op.create_index('idx_user_email', 'users', ['email'], unique=True)

    # Create other indexes for efficient queries
    op.create_index('idx_user_reset_token', 'users', ['password_reset_token'])
    op.create_index('idx_user_subscription', 'users', ['subscription_tier'])
    op.create_index('idx_user_disabled', 'users', ['disabled'])
    op.create_index('idx_user_email_verified', 'users', ['email_verified'])

    # Create unique indexes for Stripe IDs
    op.create_index('idx_user_stripe_customer', 'users', ['stripe_customer_id'], unique=True)
    op.create_index('idx_user_stripe_subscription', 'users', ['stripe_subscription_id'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_user_stripe_subscription', table_name='users')
    op.drop_index('idx_user_stripe_customer', table_name='users')
    op.drop_index('idx_user_email_verified', table_name='users')
    op.drop_index('idx_user_disabled', table_name='users')
    op.drop_index('idx_user_subscription', table_name='users')
    op.drop_index('idx_user_reset_token', table_name='users')
    op.drop_index('idx_user_email', table_name='users')
    op.drop_index('idx_user_username', table_name='users')

    # Drop table
    op.drop_table('users')
