import pytest

from src.domain.vpn_catalog.value_objects import VpnUri
from src.infrastructure.validators.vpn_uri import (
    CompositeVpnUriValidator,
    VlessUriValidator,
    TrojanUriValidator,
    VmessUriValidator,
    ShadowsocksUriValidator,
    ShadowsocksRUriValidator,
)


class TestCompositeVpnUriValidator:
    def setup_method(self):
        self.validator = CompositeVpnUriValidator()

    def test_get_supported_schemes(self):
        schemes = self.validator.get_supported_schemes()
        assert schemes == ["vless", "trojan", "vmess", "ss", "ssr"]

    def test_invalid_uri_without_scheme(self):
        uri = VpnUri(value="invalid-uri")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("scheme" in e.message for e in result.errors)

    def test_unsupported_scheme(self):
        uri = VpnUri(value="unknown://example.com:443")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("Unsupported scheme" in e.message for e in result.errors)


class TestVlessUriValidator:
    def setup_method(self):
        self.validator = VlessUriValidator()

    def test_valid_vless_uri(self):
        uri = VpnUri(
            value="vless://12345678-1234-1234-1234-123456789abc@example.com:443?encryption=none#test"
        )
        result = self.validator.validate(uri)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_vless_uri_missing_host(self):
        uri = VpnUri(value="vless://12345678-1234-1234-1234-123456789abc@:443")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("host" in e.message for e in result.errors)

    def test_vless_uri_missing_port(self):
        uri = VpnUri(value="vless://12345678-1234-1234-1234-123456789abc@example.com")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("port" in e.message for e in result.errors)

    def test_vless_uri_missing_uuid(self):
        uri = VpnUri(value="vless://example.com:443")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("UUID" in e.message for e in result.errors)

    def test_vless_uri_invalid_uuid(self):
        uri = VpnUri(value="vless://invalid-uuid@example.com:443")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("UUID" in e.message for e in result.errors)


class TestTrojanUriValidator:
    def setup_method(self):
        self.validator = TrojanUriValidator()

    def test_valid_trojan_uri(self):
        uri = VpnUri(value="trojan://password123@example.com:443?security=tls#test")
        result = self.validator.validate(uri)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_trojan_uri_missing_host(self):
        uri = VpnUri(value="trojan://password123@:443")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("host" in e.message for e in result.errors)

    def test_trojan_uri_missing_port(self):
        uri = VpnUri(value="trojan://password123@example.com")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("port" in e.message for e in result.errors)

    def test_trojan_uri_missing_password(self):
        uri = VpnUri(value="trojan://example.com:443")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("password" in e.message for e in result.errors)


class TestVmessUriValidator:
    def setup_method(self):
        self.validator = VmessUriValidator()

    def test_valid_vmess_uri(self):
        import base64
        import json

        config = {
            "add": "example.com",
            "port": 443,
            "id": "12345678-1234-1234-1234-123456789abc",
            "net": "tcp",
        }
        encoded = base64.b64encode(json.dumps(config).encode()).decode()
        uri = VpnUri(value=f"vmess://{encoded}")
        result = self.validator.validate(uri)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_vmess_uri_missing_address(self):
        import base64
        import json

        config = {"port": 443, "id": "12345678-1234-1234-1234-123456789abc"}
        encoded = base64.b64encode(json.dumps(config).encode()).decode()
        uri = VpnUri(value=f"vmess://{encoded}")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any(
            "'add'" in e.message or "address" in e.message for e in result.errors
        )

    def test_vmess_uri_missing_port(self):
        import base64
        import json

        config = {"add": "example.com", "id": "12345678-1234-1234-1234-123456789abc"}
        encoded = base64.b64encode(json.dumps(config).encode()).decode()
        uri = VpnUri(value=f"vmess://{encoded}")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("'port'" in e.message for e in result.errors)

    def test_vmess_uri_invalid_base64(self):
        uri = VpnUri(value="vmess://invalid-base64!!!")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("base64" in e.message for e in result.errors)


class TestShadowsocksUriValidator:
    def setup_method(self):
        self.validator = ShadowsocksUriValidator()

    def test_valid_shadowsocks_uri(self):
        import base64

        userinfo = base64.urlsafe_b64encode("aes-256-gcm:password123".encode()).decode()
        uri = VpnUri(value=f"ss://{userinfo}@example.com:443#test")
        result = self.validator.validate(uri)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_shadowsocks_uri_missing_host(self):
        import base64

        userinfo = base64.urlsafe_b64encode("aes-256-gcm:password123".encode()).decode()
        uri = VpnUri(value=f"ss://{userinfo}@:443")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("host" in e.message for e in result.errors)

    def test_shadowsocks_uri_missing_port(self):
        import base64

        userinfo = base64.urlsafe_b64encode("aes-256-gcm:password123".encode()).decode()
        uri = VpnUri(value=f"ss://{userinfo}@example.com")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("port" in e.message for e in result.errors)


class TestShadowsocksRUriValidator:
    def setup_method(self):
        self.validator = ShadowsocksRUriValidator()

    def test_valid_ssr_uri(self):
        uri = VpnUri(value="ssr://encoded-config@example.com:443")
        result = self.validator.validate(uri)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_ssr_uri_missing_host(self):
        uri = VpnUri(value="ssr://encoded-config@:443")
        result = self.validator.validate(uri)
        assert not result.is_valid
        assert any("host" in e.message for e in result.errors)
