"""add record_count to jurisdictions

Revision ID: 007_record_count
Revises: eef396f77718
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "007_record_count"
down_revision = "eef396f77718"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("jurisdictions") as batch:
        batch.add_column(sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("jurisdictions") as batch:
        batch.drop_column("record_count")
