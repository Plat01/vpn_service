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


@dataclass
class SyncTextFailureDTO:
    line: int
    raw: str
    error: str


@dataclass
class SyncTextResultDTO:
    dry_run: bool
    mode: str
    import_group: str
    tags: list[str]
    parsed_count: int
    valid_count: int
    invalid_count: int
    to_create_count: int
    to_update_count: int
    to_deactivate_count: int
    created: list[VpnSourceDTO] = field(default_factory=list)
    updated: list[VpnSourceDTO] = field(default_factory=list)
    deactivated: list[VpnSourceDTO] = field(default_factory=list)
    failed: list[SyncTextFailureDTO] = field(default_factory=list)
