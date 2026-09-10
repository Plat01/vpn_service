"""add import_group to vpn_sources and vpn_source_imports table

Revision ID: 004
Revises: 003
Create Date: 2026-04-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vpn_sources",
        sa.Column("import_group", sa.String(100), nullable=True, default="default"),
    )
    op.create_index(
        "idx_vpn_sources_import_group",
        "vpn_sources",
        ["import_group"],
    )

    op.create_table(
        "vpn_source_imports",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("import_group", sa.String(100), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, default=True),
        sa.Column("total_count", sa.Integer(), nullable=False, default=0),
        sa.Column("valid_count", sa.Integer(), nullable=False, default=0),
        sa.Column("invalid_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_count", sa.Integer(), nullable=False, default=0),
        sa.Column("updated_count", sa.Integer(), nullable=False, default=0),
        sa.Column("deactivated_count", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_count", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("error_summary", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_vpn_source_imports_import_group",
        "vpn_source_imports",
        ["import_group"],
    )
    op.create_index(
        "idx_vpn_source_imports_created_at",
        "vpn_source_imports",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_vpn_source_imports_created_at", "vpn_source_imports")
    op.drop_index("idx_vpn_source_imports_import_group", "vpn_source_imports")
    op.drop_table("vpn_source_imports")

    op.drop_index("idx_vpn_sources_import_group", "vpn_sources")
    op.drop_column("vpn_sources", "import_group")