from datetime import datetime, timezone

from src.infrastructure.subscription.url_generator import TextListConfigGenerator
from src.infrastructure.subscription.happ_metadata_generator import (
    HappMetadataGenerator,
)
from src.domain.subscription_issuance.value_objects import SubscriptionMetadata


class TestTextListConfigGenerator:
    def test_generate_single_uri(self):
        metadata_generator = HappMetadataGenerator()
        generator = TextListConfigGenerator(metadata_generator)
        result = generator.generate(["vless://test@example.com:443"])
        assert result == "vless://test@example.com:443"

    def test_generate_multiple_uris(self):
        metadata_generator = HappMetadataGenerator()
        generator = TextListConfigGenerator(metadata_generator)
        result = generator.generate(
            [
                "vless://test1@example.com:443",
                "vless://test2@example.com:443",
                "trojan://test3@example.com:443",
            ]
        )
        expected = "vless://test1@example.com:443\nvless://test2@example.com:443\ntrojan://test3@example.com:443"
        assert result == expected

    def test_generate_empty_list(self):
        metadata_generator = HappMetadataGenerator()
        generator = TextListConfigGenerator(metadata_generator)
        result = generator.generate([])
        assert result == ""

    def test_generate_preserves_order(self):
        metadata_generator = HappMetadataGenerator()
        generator = TextListConfigGenerator(metadata_generator)
        uris = [
            "vless://first@example.com:443",
            "trojan://second@example.com:443",
            "vmess://third@example.com:443",
        ]
        result = generator.generate(uris)
        lines = result.split("\n")
        assert lines[0] == uris[0]
        assert lines[1] == uris[1]
        assert lines[2] == uris[2]

    def test_generate_with_metadata(self):
        metadata_generator = HappMetadataGenerator()
        config_generator = TextListConfigGenerator(metadata_generator)

        metadata = SubscriptionMetadata(
            profile_title="Test VPN",
            profile_update_interval=1,
        )

        vpn_uris = [
            "vless://uuid@server1:443?security=reality#Server1",
            "vless://uuid@server2:443?security=reality#Server2",
        ]

        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)

        config = config_generator.generate(
            vpn_uris=vpn_uris,
            metadata=metadata,
            behavior=None,
            provider_id=None,
            expires_at=expires_at,
            public_id="test-id",
        )

        assert "#profile-title: Test VPN" in config
        assert "#profile-update-interval: 1" in config
        assert "#subscription-userinfo:" in config
        assert "vless://uuid@server1:443" in config
        assert "vless://uuid@server2:443" in config

    def test_generate_without_metadata(self):
        metadata_generator = HappMetadataGenerator()
        config_generator = TextListConfigGenerator(metadata_generator)

        vpn_uris = ["vless://uuid@server:443"]

        config = config_generator.generate(vpn_uris=vpn_uris)

        assert config == "vless://uuid@server:443"
