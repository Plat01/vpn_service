from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class CreateEncryptedSubscriptionDTO:
    tags: list[str]
    ttl_hours: int
    created_by: str
    max_devices: int | None = None


@dataclass
class SubscriptionIssueResultDTO:
    id: UUID
    public_id: str
    encrypted_link: str
    expires_at: datetime
    vpn_sources_count: int
    tags_used: list[str]
    created_at: datetime


@dataclass
class SubscriptionConfigDTO:
    public_id: str
    vpn_uris: list[str]
    expires_at: datetime
    is_active: bool
