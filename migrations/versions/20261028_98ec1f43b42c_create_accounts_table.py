"""create accounts table

Revision ID: 98ec1f43b42c
Revises:
Create Date: 2026-10-28 19:36:19.117709
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "98ec1f43b42c"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("balance", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("balance >= 0", name="ck_accounts_balance_not_negative"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_accounts_name_not_blank"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("accounts")
