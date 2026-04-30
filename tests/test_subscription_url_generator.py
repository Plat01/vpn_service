from datetime import datetime, timezone

from src.infrastructure.subscription.url_generator import (
    TextListConfigGenerator,
    VpnSourceInfo,
)
from src.infrastructure.subscription.happ_metadata_generator import (
    HappMetadataGenerator,
)
from src.domain.subscription_issuance.value_objects import SubscriptionMetadata


class TestTextListConfigGenerator:
    def test_generate_single_uri(self):
        metadata_generator = HappMetadataGenerator()
        generator = TextListConfigGenerator(metadata_generator)
        sources = [VpnSourceInfo(name="Test Server", uri="vless://test@example.com:443")]
        result = generator.generate(sources)
        assert result == "vless://test@example.com:443#Test Server"

    def test_generate_multiple_uris(self):
        metadata_generator = HappMetadataGenerator()
        generator = TextListConfigGenerator(metadata_generator)
        sources = [
            VpnSourceInfo(name="Server 1", uri="vless://test1@example.com:443"),
            VpnSourceInfo(name="Server 2", uri="vless://test2@example.com:443"),
            VpnSourceInfo(name="Server 3", uri="trojan://test3@example.com:443"),
        ]
        result = generator.generate(sources)
        expected = (
            "vless://test1@example.com:443#Server 1\n"
            "vless://test2@example.com:443#Server 2\n"
            "trojan://test3@example.com:443#Server 3"
        )
        assert result == expected

    def test_generate_empty_list(self):
        metadata_generator = HappMetadataGenerator()
        generator = TextListConfigGenerator(metadata_generator)
        result = generator.generate([])
        assert result == ""

    def test_generate_preserves_order(self):
        metadata_generator = HappMetadataGenerator()
        generator = TextListConfigGenerator(metadata_generator)
        sources = [
            VpnSourceInfo(name="First", uri="vless://first@example.com:443"),
            VpnSourceInfo(name="Second", uri="trojan://second@example.com:443"),
            VpnSourceInfo(name="Third", uri="vmess://third@example.com:443"),
        ]
        result = generator.generate(sources)
        lines = result.split("\n")
        assert lines[0] == "vless://first@example.com:443#First"
        assert lines[1] == "trojan://second@example.com:443#Second"
        assert lines[2] == "vmess://third@example.com:443#Third"

    def test_generate_with_metadata(self):
        metadata_generator = HappMetadataGenerator()
        config_generator = TextListConfigGenerator(metadata_generator)

        metadata = SubscriptionMetadata(
            profile_title="Test VPN",
            profile_update_interval=1,
        )

        vpn_sources = [
            VpnSourceInfo(name="Server1", uri="vless://uuid@server1:443?security=reality"),
            VpnSourceInfo(name="Server2", uri="vless://uuid@server2:443?security=reality"),
        ]

        expires_at = datetime(2025, 4, 25, 12, 0, 0, tzinfo=timezone.utc)

        config = config_generator.generate(
            vpn_sources=vpn_sources,
            metadata=metadata,
            behavior=None,
            provider_id=None,
            expires_at=expires_at,
            public_id="test-id",
        )

        assert "#profile-title: Test VPN" in config
        assert "#profile-update-interval: 1" in config
        assert "#subscription-userinfo:" in config
        assert "vless://uuid@server1:443?security=reality#Server1" in config
        assert "vless://uuid@server2:443?security=reality#Server2" in config

    def test_generate_without_metadata(self):
        metadata_generator = HappMetadataGenerator()
        config_generator = TextListConfigGenerator(metadata_generator)

        vpn_sources = [VpnSourceInfo(name="Server", uri="vless://uuid@server:443")]

        config = config_generator.generate(vpn_sources=vpn_sources)

        assert config == "vless://uuid@server:443#Server"

    def test_generate_replaces_existing_fragment(self):
        metadata_generator = HappMetadataGenerator()
        generator = TextListConfigGenerator(metadata_generator)
        sources = [
            VpnSourceInfo(
                name="New Name", uri="vless://test@example.com:443?security=reality#Old Name"
            )
        ]
        result = generator.generate(sources)
        assert result == "vless://test@example.com:443?security=reality#New Name"
        assert "#Old Name" not in result
