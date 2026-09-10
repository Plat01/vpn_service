from datetime import datetime, timezone

from src.infrastructure.subscription.happ_metadata_generator import (
    HappMetadataGenerator,
)
from src.domain.subscription_issuance.value_objects import (
    TrafficInfo,
    InfoBlock,
    ExpireNotification,
    SubscriptionMetadata,
    SubscriptionBehavior,
)


class TestHappMetadataGenerator:
    def test_generate_headers_with_full_metadata(self):
        generator = HappMetadataGenerator()

        traffic = TrafficInfo(upload=0, download=2153701362, total=10737418240)
        info_block = InfoBlock(
            color="blue",
            text="For renewal contact support",
            button_text="Support",
            button_link="https://t.me/bot",
        )
        expire_notification = ExpireNotification(
            enabled=True, button_link="https://t.me/bot"
        )

        metadata = SubscriptionMetadata(
            profile_title="Test VPN",
            profile_update_interval=1,
            support_url="https://t.me/support",
            profile_web_page_url="https://t.me/main",
            announce="Check ping",
            traffic_info=traffic,
            info_block=info_block,
            expire_notification=expire_notification,
        )

        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)

        headers = generator.generate_headers(
            metadata=metadata,
            behavior=None,
            provider_id=None,
            expires_at=expires_at,
            public_id="test-123",
        )

        assert "#profile-title: Test VPN" in headers
        assert "#profile-update-interval: 1" in headers
        assert any(
            "#subscription-userinfo: upload=0; download=2153701362; total=10737418240; expire="
            in h
            for h in headers
        )
        assert "#support-url: https://t.me/support" in headers
        assert "#announce: Check ping" in headers
        assert "#sub-info-color: blue" in headers
        assert "#sub-expire: 1" in headers

    def test_generate_headers_with_russian_announce_base64(self):
        generator = HappMetadataGenerator()

        metadata = SubscriptionMetadata(
            announce="Check ping before connecting",
        )

        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)

        headers = generator.generate_headers(
            metadata=metadata,
            behavior=None,
            provider_id=None,
            expires_at=expires_at,
            public_id="test",
        )

        assert "#announce: Check ping before connecting" in headers

    def test_generate_headers_with_russian_chars_base64(self):
        generator = HappMetadataGenerator()

        metadata = SubscriptionMetadata(
            announce="Проверяйте пинг перед подключением",
        )

        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)

        headers = generator.generate_headers(
            metadata=metadata,
            behavior=None,
            provider_id=None,
            expires_at=expires_at,
            public_id="test",
        )

        assert any("#announce: base64:" in h for h in headers)

    def test_generate_headers_with_behavior(self):
        generator = HappMetadataGenerator()

        behavior = SubscriptionBehavior(
            autoconnect=True,
            autoconnect_type="lowestdelay",
            ping_on_open=True,
            fallback_url="https://backup.example.com/{public_id}",
        )

        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)

        headers = generator.generate_headers(
            metadata=None,
            behavior=behavior,
            provider_id=None,
            expires_at=expires_at,
            public_id="abc-123",
        )

        assert "#subscription-autoconnect: true" in headers
        assert "#subscription-autoconnect-type: lowestdelay" in headers
        assert "#subscription-ping-onopen-enabled: true" in headers
        assert "#fallback-url: https://backup.example.com/abc-123" in headers

    def test_generate_headers_with_provider_id(self):
        generator = HappMetadataGenerator()

        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)

        headers = generator.generate_headers(
            metadata=None,
            behavior=None,
            provider_id="PROVIDER_123",
            expires_at=expires_at,
            public_id="test",
        )

        assert "#providerid PROVIDER_123" in headers

    def test_generate_headers_empty_metadata(self):
        generator = HappMetadataGenerator()

        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)

        headers = generator.generate_headers(
            metadata=None,
            behavior=None,
            provider_id=None,
            expires_at=expires_at,
            public_id="test",
        )

        assert headers == []
