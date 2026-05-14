"""initial song ontology schema and reference data

Revision ID: 20260422_0001
Revises:
Create Date: 2026-04-22

Creates all tables from SQLAlchemy models, then seeds ontology tables from scripts/ontology_data.json.
"""

from typing import Sequence, Union

from alembic import op
from scripts.create_db_tables import create_db_tables, drop_db_tables
from scripts.seed_ontology_data import clear_ontology_data, seed_ontology_data

revision: str = "20260422_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    create_db_tables(bind=op.get_bind())
    seed_ontology_data(bind=op.get_bind())


def downgrade() -> None:
    clear_ontology_data(bind=op.get_bind())
    drop_db_tables(bind=op.get_bind())
