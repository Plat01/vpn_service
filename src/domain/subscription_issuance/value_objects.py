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
