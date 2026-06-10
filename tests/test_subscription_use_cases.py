from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.application.subscription_issuance.dto import (
    CreateEncryptedSubscriptionDTO,
    RenewSubscriptionDTO,
)
from src.application.subscription_issuance.use_cases import (
    CreateEncryptedSubscriptionUseCase,
    GetSubscriptionConfigUseCase,
    RenewSubscriptionUseCase,
)
from src.domain.subscription_issuance.entities import SubscriptionIssue
from src.domain.subscription_issuance.value_objects import (
    InfoBlock,
    SubscriptionIssueId,
    SubscriptionMetadata,
    SubscriptionStatus,
    TrafficInfo,
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

        vpn_source_repo = AsyncMock()
        time_provider = MagicMock()
        config_generator = _get_config_generator()

        use_case = GetSubscriptionConfigUseCase(
            subscription_repo=subscription_repo,
            vpn_source_repo=vpn_source_repo,
            time_provider=time_provider,
            config_generator=config_generator,
        )

        with pytest.raises(ValueError, match="Subscription not found"):
            await use_case.execute(str(uuid4()))

    @pytest.mark.asyncio
    async def test_execute_expired_subscription_returns_poison_config(self):
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

        vpn_source_repo = AsyncMock()
        time_provider = MagicMock()
        time_provider.now.return_value = now

        config_generator = _get_config_generator()

        use_case = GetSubscriptionConfigUseCase(
            subscription_repo=subscription_repo,
            vpn_source_repo=vpn_source_repo,
            time_provider=time_provider,
            config_generator=config_generator,
        )

        is_active, content = await use_case.execute(subscription.public_id)

        assert is_active is True
        assert "Подписка истекла" in content
        assert "00000000-0000-0000-0000-000000000000" in content

    @pytest.mark.asyncio
    async def test_execute_expired_subscription_overrides_info_text(self):
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
            metadata=SubscriptionMetadata(
                profile_title="Test",
                profile_update_interval=1,
                support_url="https://t.me/test",
                info_block=InfoBlock(
                    color="blue",
                    text="Original text",
                    button_text="Support",
                    button_link="https://t.me/test",
                ),
            ),
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription
        subscription_repo.update.return_value = subscription

        vpn_source_repo = AsyncMock()
        time_provider = MagicMock()
        time_provider.now.return_value = now

        config_generator = _get_config_generator()

        use_case = GetSubscriptionConfigUseCase(
            subscription_repo=subscription_repo,
            vpn_source_repo=vpn_source_repo,
            time_provider=time_provider,
            config_generator=config_generator,
        )

        is_active, content = await use_case.execute(subscription.public_id)

        assert is_active is True
        assert "Подписка истекла" in content
        assert "00000000-0000-0000-0000-000000000000" in content
        assert "#sub-info-text: Подписка истекла — для продления перейдите в бот нажав на самолетик или обратитесь в поддержку" in content
        assert "Original text" not in content

    @pytest.mark.asyncio
    async def test_execute_revoked_subscription_returns_poison_config(self):
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

        vpn_source_repo = AsyncMock()
        time_provider = MagicMock()
        time_provider.now.return_value = now

        config_generator = _get_config_generator()

        use_case = GetSubscriptionConfigUseCase(
            subscription_repo=subscription_repo,
            vpn_source_repo=vpn_source_repo,
            time_provider=time_provider,
            config_generator=config_generator,
        )

        is_active, content = await use_case.execute(subscription.public_id)

        assert is_active is True
        assert "Подписка отозвана" in content
        assert "00000000-0000-0000-0000-000000000000" in content

    @pytest.mark.asyncio
    async def test_execute_active_subscription_returns_config(self):
        now = datetime.now(timezone.utc)

        vpn_source_1 = VpnSource(
            id=VpnSourceId(value=uuid4()),
            name="Server Alpha",
            uri=VpnUri(value="vless://alpha@example.com:443"),
            is_active=True,
            created_at=now,
            updated_at=now,
            tags=[],
        )
        vpn_source_2 = VpnSource(
            id=VpnSourceId(value=uuid4()),
            name="Server Beta",
            uri=VpnUri(value="vless://beta@example.com:443"),
            is_active=True,
            created_at=now,
            updated_at=now,
            tags=[],
        )

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=now + timedelta(hours=24),
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["main"],
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription

        vpn_source_repo = AsyncMock()
        vpn_source_repo.get_all.return_value = [vpn_source_1, vpn_source_2]

        time_provider = MagicMock()
        time_provider.now.return_value = now

        config_generator = MagicMock()
        config_generator.generate.return_value = "config-content"

        use_case = GetSubscriptionConfigUseCase(
            subscription_repo=subscription_repo,
            vpn_source_repo=vpn_source_repo,
            time_provider=time_provider,
            config_generator=config_generator,
        )

        is_active, content = await use_case.execute(subscription.public_id)

        assert is_active is True
        assert content == "config-content"

        vpn_source_repo.get_all.assert_called_once_with(
            tag_slugs=["main"], is_active=True
        )
        config_generator.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_active_subscription_no_sources(self):
        now = datetime.now(timezone.utc)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=now + timedelta(hours=24),
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["nonexistent"],
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription

        vpn_source_repo = AsyncMock()
        vpn_source_repo.get_all.return_value = []

        time_provider = MagicMock()
        time_provider.now.return_value = now

        config_generator = _get_config_generator()

        use_case = GetSubscriptionConfigUseCase(
            subscription_repo=subscription_repo,
            vpn_source_repo=vpn_source_repo,
            time_provider=time_provider,
            config_generator=config_generator,
        )

        is_active, content = await use_case.execute(subscription.public_id)

        assert is_active is False
        assert content == "No active VPN sources available"


class TestRenewSubscriptionUseCase:
    @pytest.mark.asyncio
    async def test_renew_success_active(self):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=48)
        expires_at = now + timedelta(hours=10)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=created_at,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription
        subscription_repo.update.return_value = subscription

        time_provider = MagicMock()
        time_provider.now.return_value = now

        use_case = RenewSubscriptionUseCase(
            subscription_repo=subscription_repo,
            time_provider=time_provider,
        )

        dto = RenewSubscriptionDTO(
            public_id=subscription.public_id,
            additional_hours=24,
            updated_by="admin",
        )

        result = await use_case.execute(dto)

        assert result.public_id == subscription.public_id
        assert result.vpn_sources_count == 0

        expected_expires = now + timedelta(hours=34)
        assert result.expires_at == expected_expires

        subscription_repo.get_by_public_id.assert_called_once_with(
            subscription.public_id
        )
        subscription_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_renew_success_expired(self):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=48)
        expires_at = now - timedelta(hours=5)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.expired,
            expires_at=expires_at,
            max_devices=None,
            created_at=created_at,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription
        subscription_repo.update.return_value = subscription

        time_provider = MagicMock()
        time_provider.now.return_value = now

        use_case = RenewSubscriptionUseCase(
            subscription_repo=subscription_repo,
            time_provider=time_provider,
        )

        dto = RenewSubscriptionDTO(
            public_id=subscription.public_id,
            additional_hours=24,
            updated_by="admin",
        )

        result = await use_case.execute(dto)

        assert result.vpn_sources_count == 0
        assert result.expires_at == now + timedelta(hours=24)

        # Verify the entity's status was reactivated internally
        assert subscription.status == SubscriptionStatus.active

    @pytest.mark.asyncio
    async def test_renew_revoked_raises(self):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=48)
        expires_at = now + timedelta(hours=10)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.revoked,
            expires_at=expires_at,
            max_devices=None,
            created_at=created_at,
            created_by="admin",
            tags_used=["eu"],
            revoked_at=now,
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription

        time_provider = MagicMock()
        time_provider.now.return_value = now

        use_case = RenewSubscriptionUseCase(
            subscription_repo=subscription_repo,
            time_provider=time_provider,
        )

        dto = RenewSubscriptionDTO(
            public_id=subscription.public_id,
            additional_hours=24,
            updated_by="admin",
        )

        with pytest.raises(ValueError, match="Cannot renew revoked subscription"):
            await use_case.execute(dto)

        subscription_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_renew_not_found_raises(self):
        now = datetime.now(timezone.utc)

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = None

        time_provider = MagicMock()
        time_provider.now.return_value = now

        use_case = RenewSubscriptionUseCase(
            subscription_repo=subscription_repo,
            time_provider=time_provider,
        )

        dto = RenewSubscriptionDTO(
            public_id="nonexistent-public-id",
            additional_hours=24,
            updated_by="admin",
        )

        with pytest.raises(ValueError, match="Subscription not found"):
            await use_case.execute(dto)

        subscription_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_renew_update_max_devices(self):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=48)
        expires_at = now + timedelta(hours=10)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=created_at,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription
        subscription_repo.update.return_value = subscription

        time_provider = MagicMock()
        time_provider.now.return_value = now

        use_case = RenewSubscriptionUseCase(
            subscription_repo=subscription_repo,
            time_provider=time_provider,
        )

        dto = RenewSubscriptionDTO(
            public_id=subscription.public_id,
            additional_hours=24,
            updated_by="admin",
            max_devices=5,
        )

        result = await use_case.execute(dto)

        assert subscription.max_devices == 5
        assert result.vpn_sources_count == 0

    @pytest.mark.asyncio
    async def test_renew_update_traffic_info(self):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=48)
        expires_at = now + timedelta(hours=10)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=created_at,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription
        subscription_repo.update.return_value = subscription

        time_provider = MagicMock()
        time_provider.now.return_value = now

        use_case = RenewSubscriptionUseCase(
            subscription_repo=subscription_repo,
            time_provider=time_provider,
        )

        traffic = TrafficInfo(upload=100, download=200, total=300)
        dto = RenewSubscriptionDTO(
            public_id=subscription.public_id,
            additional_hours=24,
            updated_by="admin",
            traffic_info=traffic,
        )

        result = await use_case.execute(dto)

        assert subscription.metadata is not None
        assert subscription.metadata.traffic_info == traffic
        assert result.vpn_sources_count == 0

    @pytest.mark.asyncio
    async def test_renew_all_params(self):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=48)
        expires_at = now + timedelta(hours=10)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=created_at,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription_repo = AsyncMock()
        subscription_repo.get_by_public_id.return_value = subscription
        subscription_repo.update.return_value = subscription

        time_provider = MagicMock()
        time_provider.now.return_value = now

        use_case = RenewSubscriptionUseCase(
            subscription_repo=subscription_repo,
            time_provider=time_provider,
        )

        traffic = TrafficInfo(upload=500, download=1000, total=1500)
        dto = RenewSubscriptionDTO(
            public_id=subscription.public_id,
            additional_hours=48,
            updated_by="admin",
            max_devices=10,
            traffic_info=traffic,
        )

        result = await use_case.execute(dto)

        assert result.expires_at == now + timedelta(hours=58)
        assert subscription.max_devices == 10
        assert subscription.metadata.traffic_info == traffic
        assert result.vpn_sources_count == 0

        subscription_repo.update.assert_called_once()
