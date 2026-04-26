"""merge heads — modules tables

Revision ID: a665766d4da7
Revises: cdec5abcd479, f5a2c3d4e6
Create Date: 2026-04-26 20:26:34.758225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a665766d4da7'
down_revision: Union[str, Sequence[str], None] = ('cdec5abcd479', 'f5a2c3d4e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
