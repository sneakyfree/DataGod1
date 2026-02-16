"""merge_heads

Revision ID: eef396f77718
Revises: 006_add_provenance_audit, be5527f6a835
Create Date: 2026-02-09 18:29:23.968592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eef396f77718'
down_revision: Union[str, Sequence[str], None] = ('006_add_provenance_audit', 'be5527f6a835')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
