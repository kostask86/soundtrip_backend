"""seed ontology reference data

Revision ID: 20260422_0002
Revises: 20260422_0001
Create Date: 2026-04-22
"""

from typing import Sequence, Union

from alembic import op

from scripts.seed_ontology_data import clear_ontology_data, seed_ontology_data

revision: str = "20260422_0002"
down_revision: Union[str, None] = "20260422_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    seed_ontology_data(bind=op.get_bind())


def downgrade() -> None:
    clear_ontology_data(bind=op.get_bind())
