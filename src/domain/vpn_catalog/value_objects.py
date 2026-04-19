from dataclasses import dataclass
from uuid import UUID

from src.domain.vpn_catalog.validation_errors import ValidationError


@dataclass(frozen=True)
class VpnSourceId:
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValidationError("VpnSourceId must be a UUID")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class VpnUri:
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValidationError("VpnUri cannot be empty")

    def __str__(self) -> str:
        return self.value

    @property
    def scheme(self) -> str:
        if "://" in self.value:
            return self.value.split("://")[0].lower()
        return ""


@dataclass(frozen=True)
class TagId:
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValidationError("TagId must be a UUID")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class TagSlug:
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValidationError("TagSlug cannot be empty")
        slug = self.value.strip().lower()
        if not slug.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                "TagSlug must contain only alphanumeric characters, hyphens, and underscores"
            )

    def __str__(self) -> str:
        return self.value.strip().lower()
