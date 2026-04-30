"""drop removed song metadata columns

Revision ID: 20260430_0003
Revises: 20260422_0002
Create Date: 2026-04-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260430_0003"
down_revision: Union[str, None] = "20260422_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("songs") as batch_op:
        batch_op.drop_column("mb_recording_mbid")
        batch_op.drop_column("mb_release_mbid")
        batch_op.drop_column("mb_release_group_mbid")
        batch_op.drop_column("lyrics_language")


def downgrade() -> None:
    with op.batch_alter_table("songs") as batch_op:
        batch_op.add_column(sa.Column("lyrics_language", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("mb_release_group_mbid", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("mb_release_mbid", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("mb_recording_mbid", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_songs_mb_release_group_mbid", ["mb_release_group_mbid"], unique=False)
        batch_op.create_index("ix_songs_mb_release_mbid", ["mb_release_mbid"], unique=False)
        batch_op.create_index("ix_songs_mb_recording_mbid", ["mb_recording_mbid"], unique=False)
