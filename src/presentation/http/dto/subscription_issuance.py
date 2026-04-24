from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TrafficInfoRequest(BaseModel):
    upload: int = Field(0, ge=0)
    download: int = Field(0, ge=0)
    total: int = Field(0, ge=0)


class InfoBlockRequest(BaseModel):
    color: str = Field(..., pattern="^(red|blue|green)$")
    text: str = Field(..., max_length=200)
    button_text: str = Field(..., max_length=25)
    button_link: str


class ExpireNotificationRequest(BaseModel):
    enabled: bool = True
    button_link: str | None = None


class SubscriptionMetadataRequest(BaseModel):
    profile_title: str | None = Field(None, max_length=25)
    profile_update_interval: int | None = Field(None, ge=1)
    support_url: str | None = None
    profile_web_page_url: str | None = None
    announce: str | None = Field(None, max_length=200)
    traffic_info: TrafficInfoRequest | None = None
    info_block: InfoBlockRequest | None = None
    expire_notification: ExpireNotificationRequest | None = None


class SubscriptionBehaviorRequest(BaseModel):
    autoconnect: bool = False
    autoconnect_type: str = Field("lastused", pattern="^(lastused|lowestdelay)$")
    ping_on_open: bool = False
    fallback_url: str | None = None


class CreateEncryptedSubscriptionRequest(BaseModel):
    tags: list[str] = Field(..., min_length=1)
    ttl_hours: int = Field(..., ge=1, le=8760)
    max_devices: int | None = Field(None, ge=1)
    metadata: SubscriptionMetadataRequest | None = None
    behavior: SubscriptionBehaviorRequest | None = None
    provider_id: str | None = None


class EncryptedSubscriptionResponse(BaseModel):
    id: UUID
    public_id: str
    encrypted_link: str
    expires_at: datetime
    vpn_sources_count: int
    tags_used: list[str]
    created_at: datetime
