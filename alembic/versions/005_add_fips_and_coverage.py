"""Add FIPS codes and coverage tracking for 100% data coverage goal

Revision ID: 005_add_fips_and_coverage
Revises: 004_add_share_links
Create Date: 2026-01-06

This migration adds:
1. FIPS code columns to jurisdictions table for standardized county identification
2. jurisdiction_coverage table for tracking data coverage by category
3. data_sources table for tracking available data sources per jurisdiction
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_add_fips_and_coverage'
down_revision = '004_add_share_links'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add FIPS columns to jurisdictions table
    op.add_column('jurisdictions', sa.Column('fips_code', sa.String(5), nullable=True))
    op.add_column('jurisdictions', sa.Column('state_fips', sa.String(2), nullable=True))
    op.add_column('jurisdictions', sa.Column('county_fips', sa.String(3), nullable=True))
    op.add_column('jurisdictions', sa.Column('county_seat', sa.String(100), nullable=True))
    op.add_column('jurisdictions', sa.Column('land_area_sq_miles', sa.Float(), nullable=True))
    op.add_column('jurisdictions', sa.Column('priority_tier', sa.Integer(), nullable=True, default=3))

    # Create indexes for FIPS columns
    op.create_index('idx_jurisdiction_fips', 'jurisdictions', ['fips_code'], unique=True)
    op.create_index('idx_jurisdiction_state_fips', 'jurisdictions', ['state_fips'])
    op.create_index('idx_jurisdiction_tier', 'jurisdictions', ['priority_tier'])

    # Create jurisdiction_coverage table for tracking data collection coverage
    op.create_table(
        'jurisdiction_coverage',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jurisdiction_id', sa.Integer(), nullable=False),

        # Data category (court_records, business_filings, property_records, etc.)
        sa.Column('data_category', sa.String(50), nullable=False),

        # Coverage status
        sa.Column('coverage_status', sa.String(20), nullable=False, default='none'),
        # Possible values: 'complete', 'partial', 'none', 'unavailable', 'paywall'

        # Data collection stats
        sa.Column('record_count', sa.Integer(), nullable=True, default=0),
        sa.Column('last_scraped', sa.DateTime(), nullable=True),
        sa.Column('last_successful_scrape', sa.DateTime(), nullable=True),
        sa.Column('scrape_frequency_hours', sa.Integer(), nullable=True, default=168),  # Default: weekly

        # Source information
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(20), nullable=True),  # 'api', 'scraper', 'manual'
        sa.Column('requires_auth', sa.Boolean(), default=False),

        # Quality metrics
        sa.Column('data_quality_score', sa.Float(), nullable=True),  # 0.0 to 1.0
        sa.Column('completeness_score', sa.Float(), nullable=True),  # 0.0 to 1.0

        # Notes and metadata
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('unavailable_reason', sa.String(100), nullable=True),
        # Reasons: 'no_public_access', 'no_digital_records', 'paywall', 'auth_required'

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['jurisdiction_id'], ['jurisdictions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('jurisdiction_id', 'data_category', name='uq_jurisdiction_category')
    )

    # Create indexes for jurisdiction_coverage
    op.create_index('idx_coverage_jurisdiction', 'jurisdiction_coverage', ['jurisdiction_id'])
    op.create_index('idx_coverage_category', 'jurisdiction_coverage', ['data_category'])
    op.create_index('idx_coverage_status', 'jurisdiction_coverage', ['coverage_status'])
    op.create_index('idx_coverage_last_scraped', 'jurisdiction_coverage', ['last_scraped'])

    # Create scraper_runs table for tracking scraper execution history
    op.create_table(
        'scraper_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),

        # What was scraped
        sa.Column('data_source_id', sa.Integer(), nullable=True),
        sa.Column('jurisdiction_id', sa.Integer(), nullable=True),
        sa.Column('data_category', sa.String(50), nullable=False),
        sa.Column('scraper_module', sa.String(100), nullable=True),

        # Run details
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),  # 'running', 'success', 'failed', 'partial'

        # Results
        sa.Column('records_found', sa.Integer(), nullable=True, default=0),
        sa.Column('records_new', sa.Integer(), nullable=True, default=0),
        sa.Column('records_updated', sa.Integer(), nullable=True, default=0),
        sa.Column('records_failed', sa.Integer(), nullable=True, default=0),

        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=True, default=0),

        # Performance
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('requests_made', sa.Integer(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['jurisdiction_id'], ['jurisdictions.id'], ondelete='SET NULL'),
    )

    # Create indexes for scraper_runs
    op.create_index('idx_run_source', 'scraper_runs', ['data_source_id'])
    op.create_index('idx_run_jurisdiction', 'scraper_runs', ['jurisdiction_id'])
    op.create_index('idx_run_category', 'scraper_runs', ['data_category'])
    op.create_index('idx_run_status', 'scraper_runs', ['status'])
    op.create_index('idx_run_started', 'scraper_runs', ['started_at'])


def downgrade() -> None:
    # Drop scraper_runs table and indexes
    op.drop_index('idx_run_started', table_name='scraper_runs')
    op.drop_index('idx_run_status', table_name='scraper_runs')
    op.drop_index('idx_run_category', table_name='scraper_runs')
    op.drop_index('idx_run_jurisdiction', table_name='scraper_runs')
    op.drop_index('idx_run_source', table_name='scraper_runs')
    op.drop_table('scraper_runs')

    op.drop_table('scraper_runs')

    # Drop jurisdiction_coverage table and indexes
    op.drop_index('idx_coverage_last_scraped', table_name='jurisdiction_coverage')
    op.drop_index('idx_coverage_status', table_name='jurisdiction_coverage')
    op.drop_index('idx_coverage_category', table_name='jurisdiction_coverage')
    op.drop_index('idx_coverage_jurisdiction', table_name='jurisdiction_coverage')
    op.drop_table('jurisdiction_coverage')

    # Drop FIPS columns from jurisdictions
    op.drop_index('idx_jurisdiction_tier', table_name='jurisdictions')
    op.drop_index('idx_jurisdiction_state_fips', table_name='jurisdictions')
    op.drop_index('idx_jurisdiction_fips', table_name='jurisdictions')
    op.drop_column('jurisdictions', 'priority_tier')
    op.drop_column('jurisdictions', 'land_area_sq_miles')
    op.drop_column('jurisdictions', 'county_seat')
    op.drop_column('jurisdictions', 'county_fips')
    op.drop_column('jurisdictions', 'state_fips')
    op.drop_column('jurisdictions', 'fips_code')
