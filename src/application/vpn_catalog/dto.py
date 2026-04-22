from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class VpnSourceDTO:
    id: UUID
    name: str
    uri: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tags: list["TagDTO"] = field(default_factory=list)


@dataclass
class VpnSourceListItemDTO:
    id: UUID
    name: str
    uri: str
    description: str | None
    is_active: bool
    tags: list["TagDTO"]
    created_at: datetime
    updated_at: datetime


@dataclass
class CreateVpnSourceDTO:
    name: str
    uri: str
    description: str | None = None
    is_active: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass
class UpdateVpnSourceDTO:
    name: str | None = None
    uri: str | None = None
    description: str | None = None
    is_active: bool | None = None
    tags: list[str] | None = None


@dataclass
class BatchCreateVpnSourceDTO:
    name: str
    uri: str
    description: str | None = None
    is_active: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass
class BatchCreateResultDTO:
    created: list[VpnSourceDTO]
    failed: list["BatchCreateFailureDTO"]
    total: int
    success_count: int
    failed_count: int


@dataclass
class BatchCreateFailureDTO:
    index: int
    name: str
    uri: str
    error: str


@dataclass
class TagDTO:
    id: UUID
    name: str
    slug: str
    created_at: datetime


@dataclass
class CreateTagDTO:
    name: str
    slug: str | None = None


@dataclass
class VpnSourceFilterDTO:
    tag_slugs: list[str] | None = None
    is_active: bool | None = None
