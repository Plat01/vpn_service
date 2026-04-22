from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TagResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    created_at: datetime


class VpnSourceListItemResponse(BaseModel):
    id: UUID
    name: str
    uri: str
    description: str | None
    is_active: bool
    tags: list[TagResponse]
    created_at: datetime
    updated_at: datetime


class VpnSourceDetailResponse(BaseModel):
    id: UUID
    name: str
    uri: str
    description: str | None
    is_active: bool
    tags: list[TagResponse]
    created_at: datetime
    updated_at: datetime


class VpnSourceListResponse(BaseModel):
    items: list[VpnSourceListItemResponse]


class CreateVpnSourceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    uri: str = Field(..., min_length=1)
    description: str | None = Field(None, max_length=1000)
    is_active: bool = Field(True)
    tags: list[str] = Field(default_factory=list)


class UpdateVpnSourceRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    uri: str | None = Field(None, min_length=1)
    description: str | None = Field(None, max_length=1000)
    is_active: bool | None = Field(None)
    tags: list[str] | None = Field(None)


class BatchCreateVpnSourceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    uri: str = Field(..., min_length=1)
    description: str | None = Field(None, max_length=1000)
    is_active: bool = Field(True)
    tags: list[str] = Field(default_factory=list)


class BatchCreateRequest(BaseModel):
    items: list[BatchCreateVpnSourceRequest]


class BatchCreateFailureResponse(BaseModel):
    index: int
    name: str
    uri: str
    error: str


class BatchCreateResponse(BaseModel):
    created: list[VpnSourceDetailResponse]
    failed: list[BatchCreateFailureResponse]
    total: int
    success_count: int
    failed_count: int


class CreateTagRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str | None = Field(None, min_length=1, max_length=100)


class TagListResponse(BaseModel):
    items: list[TagResponse]
