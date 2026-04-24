from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.application.subscription_issuance.dto import CreateEncryptedSubscriptionDTO
from src.application.subscription_issuance.use_cases import (
    CreateEncryptedSubscriptionUseCase,
    GetSubscriptionConfigUseCase,
)
from src.domain.subscription_issuance.entities import SubscriptionIssue
from src.domain.subscription_issuance.value_objects import (
    SubscriptionIssueId,
    SubscriptionStatus,
)
from src.domain.vpn_catalog.entities import VpnSource
from src.domain.vpn_catalog.value_objects import VpnSourceId, VpnUri
from src.infrastructure.subscription.happ_metadata_generator import (
    HappMetadataGenerator,
)
from src.infrastructure.subscription.url_generator import TextListConfigGenerator
from src.infrastructure.time.provider import SystemTimeProvider


def _get_config_generator() -> TextListConfigGenerator:
    metadata_generator = HappMetadataGenerator()
    return TextListConfigGenerator(metadata_generator)


class TestCreateEncryptedSubscriptionUseCase:
    @pytest.mark.asyncio
    async def test_execute_no_vpn_sources_raises(self):
        vpn_source_repo = AsyncMock()
        vpn_source_repo.get_all.return_value = []

        subscription_repo = AsyncMock()
        item_repo = AsyncMock()
        crypto_adapter = AsyncMock()
        time_provider = SystemTimeProvider()
        config_generator = _get_config_generator()

        use_case = CreateEncryptedSubscriptionUseCase(
            vpn_source_repo=vpn_source_repo,
            subscription_repo=subscription_repo,
            item_repo=item_repo,
            crypto_adapter=crypto_adapter,
            config_generator=config_generator,
            time_provider=time_provider,
        )

        dto = CreateEncryptedSubscriptionDTO(
            tags=["eu"],
            ttl_hours=24,
            created_by="admin",
        )

        with pytest.raises(ValueError, match="No active VPN sources found"):
            await use_case.execute(dto)

    @pytest.mark.asyncio
    async def test_execute_success(self):
        now = datetime.now(timezone.utc)
        vpn_source = VpnSource(
            id=VpnSourceId(value=uuid4()),
            name="Test Server",
            uri=VpnUri(value="vless://test@example.com:443"),
            is_active=True,
            created_at=now,
            updated_at=now,
            tags=[],
        )

        vpn_source_repo = AsyncMock()
        vpn_source_repo.get_all.return_value = [vpn_source]

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=now + timedelta(hours=24),
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription_repo = AsyncMock()
        subscription_repo.create.return_value = subscription
        subscription_repo.update.return_value = subscription

        item_repo = AsyncMock()
        item_repo.create_batch.return_value = []

        crypto_adapter = AsyncMock()
        crypto_adapter.encrypt_link.return_value = "happ://crypt5/test123"

        time_provider = MagicMock()
        time_provider.now.return_value = now

        config_generator = _get_config_generator()

        use_case = CreateEncryptedSubscriptionUseCase(
            vpn_source_repo=vpn_source_repo,
            subscription_repo=subscription_repo,
            item_repo=item_repo,
            crypto_adapter=crypto_adapter,
            config_generator=config_generator,
            time_provider=time_provider,
        )

        dto = CreateEncryptedSubscriptionDTO(
            tags=["eu"],
            ttl_hours=24,
            created_by="admin",
        )

        result = await use_case.execute(dto)

        assert result.vpn_sources_count == 1
        assert result.tags_used == ["eu"]
        assert result.encrypted_link == "happ://crypt5/test123"

        vpn_source_repo.get_all.assert_called_once_with(
            tag_slugs=["eu"], is_active=True
        )
        subscription_repo.create.assert_called_once()
        subscription_repo.update.assert_called_once()
        item_repo.create_batch.assert_called_once()
        crypto_adapter.encrypt_link.assert_called_once()


class TestGetSubscriptionConfigUseCase:
    @pytest.mark.asyncio
    async def test_execute_subscription_not_found_raises(self):
        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = None

        item_repo = AsyncMock()
        vpn_source_repo = AsyncMock()
        time_provider = MagicMock()
        config_generator = _get_config_generator()

        use_case = GetSubscriptionConfigUseCase(
            subscription_repo=subscription_repo,
            item_repo=item_repo,
            vpn_source_repo=vpn_source_repo,
            time_provider=time_provider,
            config_generator=config_generator,
        )

        with pytest.raises(ValueError, match="Subscription not found"):
            await use_case.execute(str(uuid4()))

    @pytest.mark.asyncio
    async def test_execute_expired_subscription_returns_false(self):
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(hours=1)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=past_time,
            max_devices=None,
            created_at=now - timedelta(hours=25),
            created_by="admin",
            tags_used=["eu"],
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription
        subscription_repo.update.return_value = subscription

        item_repo = AsyncMock()
        vpn_source_repo = AsyncMock()
        time_provider = MagicMock()
        time_provider.now.return_value = now

        config_generator = _get_config_generator()

        use_case = GetSubscriptionConfigUseCase(
            subscription_repo=subscription_repo,
            item_repo=item_repo,
            vpn_source_repo=vpn_source_repo,
            time_provider=time_provider,
            config_generator=config_generator,
        )

        is_active, content = await use_case.execute(subscription.public_id)

        assert is_active is False
        assert "expired" in content.lower()

    @pytest.mark.asyncio
    async def test_execute_revoked_subscription_returns_false(self):
        now = datetime.now(timezone.utc)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.revoked,
            expires_at=now + timedelta(hours=24),
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
            revoked_at=now,
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription

        item_repo = AsyncMock()
        vpn_source_repo = AsyncMock()
        time_provider = MagicMock()
        time_provider.now.return_value = now

        config_generator = _get_config_generator()

        use_case = GetSubscriptionConfigUseCase(
            subscription_repo=subscription_repo,
            item_repo=item_repo,
            vpn_source_repo=vpn_source_repo,
            time_provider=time_provider,
            config_generator=config_generator,
        )

        is_active, content = await use_case.execute(subscription.public_id)

        assert is_active is False
        assert "revoked" in content.lower()
