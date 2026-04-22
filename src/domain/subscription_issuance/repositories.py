from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.subscription_issuance.entities import (
    SubscriptionIssue,
    SubscriptionIssueItem,
)


class SubscriptionIssueRepository(ABC):
    @abstractmethod
    async def get_by_id(self, subscription_issue_id: UUID) -> SubscriptionIssue | None:
        pass

    @abstractmethod
    async def get_by_public_id(self, public_id: str) -> SubscriptionIssue | None:
        pass

    @abstractmethod
    async def create(self, subscription_issue: SubscriptionIssue) -> SubscriptionIssue:
        pass

    @abstractmethod
    async def update(self, subscription_issue: SubscriptionIssue) -> SubscriptionIssue:
        pass


class SubscriptionIssueItemRepository(ABC):
    @abstractmethod
    async def create_batch(
        self, items: list[SubscriptionIssueItem]
    ) -> list[SubscriptionIssueItem]:
        pass

    @abstractmethod
    async def get_by_subscription_issue_id(
        self, subscription_issue_id: UUID
    ) -> list[SubscriptionIssueItem]:
        pass
