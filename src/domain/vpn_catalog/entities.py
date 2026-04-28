from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.vpn_catalog.value_objects import TagId, TagSlug, VpnSourceId, VpnUri


@dataclass
class VpnSourceTag:
    id: TagId
    name: str
    slug: TagSlug
    created_at: datetime

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Tag name cannot be empty")


@dataclass
class VpnSource:
    id: VpnSourceId
    name: str
    uri: VpnUri
    is_active: bool
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    tags: list[VpnSourceTag] = field(default_factory=list)
    import_group: str = "default"

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("VpnSource name cannot be empty")
        if not self.import_group or len(self.import_group) > 100:
            raise ValueError("ImportGroup must be 1-100 chars")

    def update(
        self,
        name: str | None = None,
        uri: VpnUri | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        if name is not None:
            if not name.strip():
                raise ValueError("VpnSource name cannot be empty")
            self.name = name
        if uri is not None:
            self.uri = uri
        if description is not None:
            self.description = description
        if is_active is not None:
            self.is_active = is_active

    def assign_tags(self, tags: list[VpnSourceTag]) -> None:
        self.tags = tags


@dataclass
class VpnSourceTagAssociation:
    vpn_source_id: VpnSourceId
    tag_id: TagId


@dataclass
class VpnSourceImport:
    id: UUID
    import_group: str
    mode: str
    dry_run: bool
    total_count: int
    valid_count: int
    invalid_count: int
    created_count: int
    updated_count: int
    deactivated_count: int
    failed_count: int
    created_at: datetime
    error_summary: dict | None = None

    def __post_init__(self):
        if self.mode not in ("replace", "upsert", "append"):
            raise ValueError(f"Invalid mode: {self.mode}")
        if not self.import_group or len(self.import_group) > 100:
            raise ValueError("ImportGroup must be 1-100 chars")
