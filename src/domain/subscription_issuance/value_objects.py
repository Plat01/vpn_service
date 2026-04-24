from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class SubscriptionStatus(str, Enum):
    active = "active"
    expired = "expired"
    revoked = "revoked"


@dataclass(frozen=True)
class SubscriptionIssueId:
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValueError("SubscriptionIssueId must be a UUID")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class SubscriptionIssueItemId:
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValueError("SubscriptionIssueItemId must be a UUID")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class TrafficInfo:
    upload: int = 0
    download: int = 0
    total: int = 0

    def __post_init__(self):
        if self.upload < 0 or self.download < 0 or self.total < 0:
            raise ValueError("Traffic values must be non-negative")


@dataclass(frozen=True)
class InfoBlock:
    color: str
    text: str
    button_text: str
    button_link: str

    def __post_init__(self):
        if self.color not in ("red", "blue", "green"):
            raise ValueError("color must be red, blue, or green")
        if len(self.text) > 200:
            raise ValueError("text must be max 200 characters")
        if len(self.button_text) > 25:
            raise ValueError("button_text must be max 25 characters")


@dataclass(frozen=True)
class ExpireNotification:
    enabled: bool
    button_link: str | None = None


@dataclass(frozen=True)
class SubscriptionBehavior:
    autoconnect: bool = False
    autoconnect_type: str = "lastused"
    ping_on_open: bool = False
    fallback_url: str | None = None

    def __post_init__(self):
        if self.autoconnect_type not in ("lastused", "lowestdelay"):
            raise ValueError("autoconnect_type must be lastused or lowestdelay")


@dataclass(frozen=True)
class SubscriptionMetadata:
    profile_title: str | None = None
    profile_update_interval: int | None = None
    support_url: str | None = None
    profile_web_page_url: str | None = None
    announce: str | None = None
    traffic_info: TrafficInfo | None = None
    info_block: InfoBlock | None = None
    expire_notification: ExpireNotification | None = None

    def __post_init__(self):
        if self.profile_title and len(self.profile_title) > 25:
            raise ValueError("profile_title must be max 25 characters")
        if self.profile_update_interval and self.profile_update_interval < 1:
            raise ValueError("profile_update_interval must be at least 1")
        if self.announce and len(self.announce) > 200:
            raise ValueError("announce must be max 200 characters")
