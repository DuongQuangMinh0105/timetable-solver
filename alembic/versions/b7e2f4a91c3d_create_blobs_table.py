"""create blobs table

Revision ID: b7e2f4a91c3d
Revises: 14f9553871ec
Create Date: 2026-10-15 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2f4a91c3d"
down_revision: str | Sequence[str] | None = "14f9553871ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "blobs",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("blobs")
