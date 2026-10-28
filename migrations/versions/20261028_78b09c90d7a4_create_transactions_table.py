"""create transactions table

Revision ID: 78b09c90d7a4
Revises: 98ec1f43b42c
Create Date: 2026-10-28 19:39:03.080524
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "78b09c90d7a4"
down_revision: str | None = "98ec1f43b42c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=6), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("reference_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("type IN ('credit', 'debit')", name="ck_transactions_type"),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "reference_id", name="uq_transactions_account_reference"),
    )
    op.create_index(
        "ix_transactions_account_created_at",
        "transactions",
        ["account_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_account_created_at", table_name="transactions")
    op.drop_table("transactions")
