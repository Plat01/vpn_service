"""Create subscription_issues and subscription_issue_items tables

Revision ID: 002
Revises: 001
Create Date: 2026-04-22 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscription_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_devices", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column(
            "tags_used",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("encrypted_link", sa.Text, nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_subscription_issues_public_id"),
    )
    op.create_index(
        "idx_subscription_issues_public_id",
        "subscription_issues",
        ["public_id"],
        unique=True,
    )
    op.create_index("idx_subscription_issues_status", "subscription_issues", ["status"])
    op.create_index(
        "idx_subscription_issues_expires_at", "subscription_issues", ["expires_at"]
    )

    op.create_table(
        "subscription_issue_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "subscription_issue_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("vpn_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["subscription_issue_id"],
            ["subscription_issues.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vpn_source_id"],
            ["vpn_sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_subscription_issue_items_subscription_issue_id",
        "subscription_issue_items",
        ["subscription_issue_id"],
    )
    op.create_index(
        "idx_subscription_issue_items_vpn_source_id",
        "subscription_issue_items",
        ["vpn_source_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_subscription_issue_items_vpn_source_id", "subscription_issue_items"
    )
    op.drop_index(
        "idx_subscription_issue_items_subscription_issue_id", "subscription_issue_items"
    )
    op.drop_table("subscription_issue_items")

    op.drop_index("idx_subscription_issues_expires_at", "subscription_issues")
    op.drop_index("idx_subscription_issues_status", "subscription_issues")
    op.drop_index("idx_subscription_issues_public_id", "subscription_issues")
    op.drop_table("subscription_issues")
