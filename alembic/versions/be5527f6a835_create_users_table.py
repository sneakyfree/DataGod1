"""create_users_table

Revision ID: be5527f6a835
Revises: 005_add_fips_and_coverage
Create Date: 2026-01-12 09:30:52.196605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be5527f6a835'
down_revision: Union[str, Sequence[str], None] = '005_add_fips_and_coverage'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
