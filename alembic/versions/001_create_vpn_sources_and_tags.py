"""Create vpn_sources and vpn_source_tags tables

Revision ID: 001
Revises:
Create Date: 2026-04-20 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vpn_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("uri", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_vpn_sources_is_active", "vpn_sources", ["is_active"])

    op.create_table(
        "vpn_source_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_vpn_source_tags_slug"),
    )
    op.create_index(
        "idx_vpn_source_tags_slug", "vpn_source_tags", ["slug"], unique=True
    )

    op.create_table(
        "vpn_source_tag_associations",
        sa.Column(
            "vpn_source_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["vpn_source_id"],
            ["vpn_sources.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["vpn_source_tags.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("vpn_source_id", "tag_id"),
    )
    op.create_index(
        "idx_vpn_source_tag_assoc_source",
        "vpn_source_tag_associations",
        ["vpn_source_id"],
    )
    op.create_index(
        "idx_vpn_source_tag_assoc_tag",
        "vpn_source_tag_associations",
        ["tag_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_vpn_source_tag_assoc_tag", "vpn_source_tag_associations")
    op.drop_index("idx_vpn_source_tag_assoc_source", "vpn_source_tag_associations")
    op.drop_table("vpn_source_tag_associations")

    op.drop_index("idx_vpn_source_tags_slug", "vpn_source_tags")
    op.drop_table("vpn_source_tags")

    op.drop_index("idx_vpn_sources_is_active", "vpn_sources")
    op.drop_table("vpn_sources")
