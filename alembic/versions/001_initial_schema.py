"""Initial DataGod schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-12-30

This migration creates the initial database schema for the DataGod platform.

Tables created:
- jurisdictions: Geographic jurisdictions (counties, cities, states)
- data_sources: Data sources for each jurisdiction (APIs, scrapers)
- records: Public records (mortgages, deeds, liens, UCC filings)
- entities: People, companies, properties mentioned in records
- relationships: Relationships between entities
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import JSON


# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create jurisdictions table
    op.create_table(
        'jurisdictions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('state', sa.String(2), nullable=True),
        sa.Column('county', sa.String(100), nullable=True),
        sa.Column('type', sa.String(50), nullable=True),
        sa.Column('api_available', sa.Boolean(), default=False),
        sa.Column('scraper_needed', sa.Boolean(), default=True),
        sa.Column('population', sa.Integer(), nullable=True),
        sa.Column('area_sq_miles', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('contact_info', JSON, nullable=True),
        sa.Column('jurisdiction_metadata', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for jurisdictions
    op.create_index('idx_jurisdiction_name', 'jurisdictions', ['name'], unique=True)
    op.create_index('idx_jurisdiction_state', 'jurisdictions', ['state'])
    op.create_index('idx_jurisdiction_county', 'jurisdictions', ['county'])
    op.create_index('idx_jurisdiction_state_county', 'jurisdictions', ['state', 'county'])
    op.create_index('idx_jurisdiction_type', 'jurisdictions', ['type'])
    op.create_index('idx_jurisdiction_api_available', 'jurisdictions', ['api_available'])

    # Create data_sources table
    op.create_table(
        'data_sources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jurisdiction_id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('api_endpoint', sa.String(1000), nullable=True),
        sa.Column('api_key', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('last_scraped', sa.DateTime(), nullable=True),
        sa.Column('next_scheduled_scrape', sa.DateTime(), nullable=True),
        sa.Column('scrape_interval_hours', sa.Integer(), default=24),
        sa.Column('error_count', sa.Integer(), default=0),
        sa.Column('success_count', sa.Integer(), default=0),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config', JSON, nullable=True),
        sa.Column('source_metadata', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['jurisdiction_id'], ['jurisdictions.id'], ondelete='CASCADE')
    )

    # Create indexes for data_sources
    op.create_index('idx_data_source_jurisdiction', 'data_sources', ['jurisdiction_id'])
    op.create_index('idx_data_source_type', 'data_sources', ['source_type'])
    op.create_index('idx_data_source_status', 'data_sources', ['status'])
    op.create_index('idx_data_source_last_scraped', 'data_sources', ['last_scraped'])

    # Create records table
    op.create_table(
        'records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jurisdiction_id', sa.Integer(), nullable=False),
        sa.Column('data_source_id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.String(255), nullable=True),
        sa.Column('record_type', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('loan_amount', sa.Float(), nullable=True),
        sa.Column('sale_amount', sa.Float(), nullable=True),
        sa.Column('date', sa.DateTime(), nullable=True),
        sa.Column('recording_date', sa.DateTime(), nullable=True),
        sa.Column('filing_date', sa.DateTime(), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(2), nullable=True),
        sa.Column('zip_code', sa.String(10), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('grantor', sa.String(255), nullable=True),
        sa.Column('grantee', sa.String(255), nullable=True),
        sa.Column('borrower', sa.String(255), nullable=True),
        sa.Column('lender', sa.String(255), nullable=True),
        sa.Column('document_number', sa.String(100), nullable=True),
        sa.Column('book_page', sa.String(100), nullable=True),
        sa.Column('instrument_number', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('quality_score', sa.Float(), default=1.0),
        sa.Column('confidence_level', sa.Float(), default=1.0),
        sa.Column('url', sa.String(1000), nullable=True),
        sa.Column('document_url', sa.String(1000), nullable=True),
        sa.Column('raw_data', JSON, nullable=True),
        sa.Column('processed_data', JSON, nullable=True),
        sa.Column('entities', JSON, nullable=True),
        sa.Column('relationships', JSON, nullable=True),
        sa.Column('tags', JSON, nullable=True),
        sa.Column('record_metadata', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['jurisdiction_id'], ['jurisdictions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='CASCADE')
    )

    # Create indexes for records
    op.create_index('idx_record_id', 'records', ['record_id'])
    op.create_index('idx_record_jurisdiction', 'records', ['jurisdiction_id'])
    op.create_index('idx_record_data_source', 'records', ['data_source_id'])
    op.create_index('idx_record_type', 'records', ['record_type'])
    op.create_index('idx_record_date', 'records', ['date'])
    op.create_index('idx_record_status', 'records', ['status'])
    op.create_index('idx_record_amount', 'records', ['amount'])
    op.create_index('idx_record_grantor', 'records', ['grantor'])
    op.create_index('idx_record_grantee', 'records', ['grantee'])
    op.create_index('idx_record_address', 'records', ['address'])
    op.create_index('idx_record_city_state', 'records', ['city', 'state'])

    # Create entities table
    op.create_table(
        'entities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('entity_name', sa.String(500), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(2), nullable=True),
        sa.Column('zip_code', sa.String(10), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('business_type', sa.String(100), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('incorporation_date', sa.DateTime(), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('middle_name', sa.String(100), nullable=True),
        sa.Column('property_type', sa.String(50), nullable=True),
        sa.Column('parcel_id', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('verification_date', sa.DateTime(), nullable=True),
        sa.Column('verification_source', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('data', JSON, nullable=True),
        sa.Column('entity_metadata', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for entities
    op.create_index('idx_entity_name', 'entities', ['entity_name'])
    op.create_index('idx_entity_type', 'entities', ['entity_type'])
    op.create_index('idx_entity_name_type', 'entities', ['entity_name', 'entity_type'])
    op.create_index('idx_entity_id', 'entities', ['entity_id'])
    op.create_index('idx_entity_city_state', 'entities', ['city', 'state'])

    # Create relationships table
    op.create_table(
        'relationships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('entity1_id', sa.Integer(), nullable=False),
        sa.Column('entity2_id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(100), nullable=False),
        sa.Column('role1', sa.String(100), nullable=True),
        sa.Column('role2', sa.String(100), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('evidence', JSON, nullable=True),
        sa.Column('confidence_score', sa.Float(), default=1.0),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('relationship_metadata', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['entity1_id'], ['entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity2_id'], ['entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['record_id'], ['records.id'], ondelete='CASCADE')
    )

    # Create indexes for relationships
    op.create_index('idx_relationship_entities', 'relationships', ['entity1_id', 'entity2_id'])
    op.create_index('idx_relationship_record', 'relationships', ['record_id'])
    op.create_index('idx_relationship_type', 'relationships', ['relationship_type'])
    op.create_index('idx_relationship_status', 'relationships', ['status'])


def downgrade() -> None:
    # Drop tables in reverse order (due to foreign key constraints)
    op.drop_table('relationships')
    op.drop_table('entities')
    op.drop_table('records')
    op.drop_table('data_sources')
    op.drop_table('jurisdictions')
