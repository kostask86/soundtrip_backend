"""initial song ontology schema

Revision ID: 20260422_0001
Revises:
Create Date: 2026-04-22

"""

from typing import Sequence, Union

from alembic import op
from scripts.create_db_tables import create_db_tables, drop_db_tables

revision: str = "20260422_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    create_db_tables(bind=op.get_bind())


def downgrade() -> None:
    drop_db_tables(bind=op.get_bind())
