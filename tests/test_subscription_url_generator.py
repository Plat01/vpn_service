import pytest

from src.infrastructure.subscription.url_generator import TextListConfigGenerator


class TestTextListConfigGenerator:
    def test_generate_single_uri(self):
        generator = TextListConfigGenerator()
        result = generator.generate(["vless://test@example.com:443"])
        assert result == "vless://test@example.com:443"

    def test_generate_multiple_uris(self):
        generator = TextListConfigGenerator()
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
        generator = TextListConfigGenerator()
        result = generator.generate([])
        assert result == ""

    def test_generate_preserves_order(self):
        generator = TextListConfigGenerator()
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
