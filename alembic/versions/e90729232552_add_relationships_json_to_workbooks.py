"""add relationships_json to workbooks

Revision ID: e90729232552
Revises: c645be70bf3d
Create Date: 2026-03-17 15:24:42.759527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e90729232552'
down_revision: Union[str, None] = 'c645be70bf3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workbooks", sa.Column("relationships_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("workbooks", "relationships_json")
