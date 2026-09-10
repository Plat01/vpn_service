"""Add metadata, behavior, provider_id columns to subscription_issues

Revision ID: 003
Revises: 002
Create Date: 2026-04-25 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscription_issues",
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "subscription_issues",
        sa.Column("behavior", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "subscription_issues",
        sa.Column("provider_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscription_issues", "provider_id")
    op.drop_column("subscription_issues", "behavior")
    op.drop_column("subscription_issues", "metadata")
