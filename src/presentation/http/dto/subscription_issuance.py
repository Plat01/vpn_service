from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateEncryptedSubscriptionRequest(BaseModel):
    tags: list[str] = Field(..., min_length=1)
    ttl_hours: int = Field(..., ge=1, le=8760)
    max_devices: int | None = Field(None, ge=1)


class EncryptedSubscriptionResponse(BaseModel):
    id: UUID
    public_id: str
    encrypted_link: str
    expires_at: datetime
    vpn_sources_count: int
    tags_used: list[str]
    created_at: datetime
