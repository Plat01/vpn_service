from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.subscription_issuance.value_objects import (
    SubscriptionIssueId,
    SubscriptionIssueItemId,
    SubscriptionStatus,
)
from src.domain.vpn_catalog.value_objects import VpnSourceId


@dataclass
class SubscriptionIssue:
    id: SubscriptionIssueId
    public_id: str
    status: SubscriptionStatus
    expires_at: datetime
    max_devices: int | None
    created_at: datetime
    created_by: str
    tags_used: list[str]
    encrypted_link: str | None = None
    revoked_at: datetime | None = None

    def __post_init__(self):
        if not self.public_id or not self.public_id.strip():
            raise ValueError("public_id cannot be empty")
        if not self.created_by or not self.created_by.strip():
            raise ValueError("created_by cannot be empty")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        if self.max_devices is not None and self.max_devices < 1:
            raise ValueError("max_devices must be at least 1 if specified")

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def is_revoked(self) -> bool:
        return self.status == SubscriptionStatus.revoked

    def is_active(self, now: datetime) -> bool:
        return (
            self.status == SubscriptionStatus.active
            and not self.is_expired(now)
            and not self.is_revoked()
        )

    def mark_expired(self) -> None:
        self.status = SubscriptionStatus.expired

    def revoke(self, revoked_at: datetime) -> None:
        self.status = SubscriptionStatus.revoked
        self.revoked_at = revoked_at

    def set_encrypted_link(self, encrypted_link: str) -> None:
        self.encrypted_link = encrypted_link


@dataclass
class SubscriptionIssueItem:
    id: SubscriptionIssueItemId
    subscription_issue_id: SubscriptionIssueId
    vpn_source_id: VpnSourceId
    position: int
    created_at: datetime

    def __post_init__(self):
        if self.position < 0:
            raise ValueError("position must be non-negative")
