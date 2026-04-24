import logging
from datetime import timedelta
from uuid import uuid4

from src.application.subscription_issuance.dto import (
    CreateEncryptedSubscriptionDTO,
    SubscriptionIssueResultDTO,
)
from src.config import settings
from src.domain.subscription_issuance.entities import (
    SubscriptionIssue,
    SubscriptionIssueItem,
)
from src.domain.subscription_issuance.repositories import (
    SubscriptionIssueItemRepository,
    SubscriptionIssueRepository,
)
from src.domain.subscription_issuance.value_objects import (
    SubscriptionIssueId,
    SubscriptionIssueItemId,
    SubscriptionStatus,
)
from src.domain.vpn_catalog.repositories import VpnSourceRepository
from src.domain.vpn_catalog.value_objects import VpnSourceId
from src.infrastructure.happ.crypto_adapter import HappCryptoAdapterPort
from src.infrastructure.subscription.url_generator import SubscriptionConfigGenerator
from src.infrastructure.time.provider import TimeProvider

logger = logging.getLogger(__name__)


class CreateEncryptedSubscriptionUseCase:
    def __init__(
        self,
        vpn_source_repo: VpnSourceRepository,
        subscription_repo: SubscriptionIssueRepository,
        item_repo: SubscriptionIssueItemRepository,
        crypto_adapter: HappCryptoAdapterPort,
        config_generator: SubscriptionConfigGenerator,
        time_provider: TimeProvider,
    ):
        self._vpn_source_repo = vpn_source_repo
        self._subscription_repo = subscription_repo
        self._item_repo = item_repo
        self._crypto_adapter = crypto_adapter
        self._config_generator = config_generator
        self._time_provider = time_provider

    async def execute(
        self, dto: CreateEncryptedSubscriptionDTO
    ) -> SubscriptionIssueResultDTO:
        vpn_sources = await self._vpn_source_repo.get_all(
            tag_slugs=dto.tags,
            is_active=True,
        )

        if not vpn_sources:
            raise ValueError(f"No active VPN sources found for tags: {dto.tags}")

        now = self._time_provider.now()
        expires_at = now + timedelta(hours=dto.ttl_hours)

        public_id = str(uuid4())

        subscription_issue = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=public_id,
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=dto.max_devices,
            created_at=now,
            created_by=dto.created_by,
            tags_used=dto.tags,
            metadata=dto.metadata,
            behavior=dto.behavior,
            provider_id=dto.provider_id,
        )

        created_subscription = await self._subscription_repo.create(subscription_issue)

        items = [
            SubscriptionIssueItem(
                id=SubscriptionIssueItemId(value=uuid4()),
                subscription_issue_id=created_subscription.id,
                vpn_source_id=VpnSourceId(value=source.id.value),
                position=index,
                created_at=now,
            )
            for index, source in enumerate(vpn_sources)
        ]

        await self._item_repo.create_batch(items)

        subscription_url = (
            f"{settings.subscription_base_url}/api/v1/subscriptions/{public_id}"
        )

        encrypted_link = await self._crypto_adapter.encrypt_link(subscription_url)

        created_subscription.set_encrypted_link(encrypted_link)
        updated_subscription = await self._subscription_repo.update(
            created_subscription
        )

        logger.info(
            "Subscription created: id=%s, public_id=%s, vpn_sources_count=%d, ttl_hours=%d",
            updated_subscription.id.value,
            public_id[:8] + "...",
            len(vpn_sources),
            dto.ttl_hours,
        )

        return SubscriptionIssueResultDTO(
            id=updated_subscription.id.value,
            public_id=updated_subscription.public_id,
            encrypted_link=updated_subscription.encrypted_link,
            expires_at=updated_subscription.expires_at,
            vpn_sources_count=len(vpn_sources),
            tags_used=updated_subscription.tags_used,
            created_at=updated_subscription.created_at,
        )


class GetSubscriptionConfigUseCase:
    def __init__(
        self,
        subscription_repo: SubscriptionIssueRepository,
        item_repo: SubscriptionIssueItemRepository,
        vpn_source_repo: VpnSourceRepository,
        time_provider: TimeProvider,
        config_generator: SubscriptionConfigGenerator,
    ):
        self._subscription_repo = subscription_repo
        self._item_repo = item_repo
        self._vpn_source_repo = vpn_source_repo
        self._time_provider = time_provider
        self._config_generator = config_generator

    async def execute(self, public_id: str) -> tuple[bool, str]:
        subscription = await self._subscription_repo.get_by_public_id(public_id)

        if not subscription:
            raise ValueError(f"Subscription not found: public_id={public_id[:8]}...")

        now = self._time_provider.now()

        if subscription.is_expired(now):
            if subscription.status != SubscriptionStatus.expired:
                subscription.mark_expired()
                await self._subscription_repo.update(subscription)
            logger.info(
                "Subscription expired: public_id=%s, expires_at=%s",
                public_id[:8] + "...",
                subscription.expires_at.isoformat(),
            )
            return False, "Subscription expired"

        if subscription.is_revoked():
            logger.info(
                "Subscription revoked: public_id=%s",
                public_id[:8] + "...",
            )
            return False, "Subscription revoked"

        items = await self._item_repo.get_by_subscription_issue_id(
            subscription.id.value
        )

        vpn_uris: list[str] = []
        for item in items:
            vpn_source = await self._vpn_source_repo.get_by_id(item.vpn_source_id.value)
            if vpn_source and vpn_source.is_active:
                vpn_uris.append(vpn_source.uri.value)

        if not vpn_uris:
            logger.warning(
                "Subscription has no active VPN sources: public_id=%s",
                public_id[:8] + "...",
            )
            return False, "No active VPN sources available"

        config_content = self._config_generator.generate(
            vpn_uris=vpn_uris,
            metadata=subscription.metadata,
            behavior=subscription.behavior,
            provider_id=subscription.provider_id,
            expires_at=subscription.expires_at,
            public_id=public_id,
        )

        logger.info(
            "Subscription served: public_id=%s, vpn_uris_count=%d",
            public_id[:8] + "...",
            len(vpn_uris),
        )

        return True, config_content
