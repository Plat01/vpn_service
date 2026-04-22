from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.vpn_source import Base


class SubscriptionIssueModel(Base):
    __tablename__ = "subscription_issues"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    public_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    max_devices: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    tags_used: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    encrypted_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    items: Mapped[list["SubscriptionIssueItemModel"]] = relationship(
        "SubscriptionIssueItemModel",
        back_populates="subscription_issue",
        cascade="all, delete-orphan",
    )


class SubscriptionIssueItemModel(Base):
    __tablename__ = "subscription_issue_items"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    subscription_issue_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscription_issues.id", ondelete="CASCADE"),
        nullable=False,
    )
    vpn_source_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vpn_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    subscription_issue: Mapped["SubscriptionIssueModel"] = relationship(
        "SubscriptionIssueModel",
        back_populates="items",
    )
