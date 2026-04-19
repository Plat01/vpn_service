import base64
import re
from urllib.parse import parse_qs, urlparse

from src.domain.vpn_catalog.validation_errors import (
    ValidationError,
    VpnUriValidationResult,
)
from src.domain.vpn_catalog.validators import VpnUriValidator
from src.domain.vpn_catalog.value_objects import VpnUri


class CompositeVpnUriValidator(VpnUriValidator):
    SUPPORTED_SCHEMES = ["vless", "trojan", "vmess", "ss", "ssr"]

    def __init__(self):
        self._validators = {
            "vless": VlessUriValidator(),
            "trojan": TrojanUriValidator(),
            "vmess": VmessUriValidator(),
            "ss": ShadowsocksUriValidator(),
            "ssr": ShadowsocksRUriValidator(),
        }

    def validate(self, uri: VpnUri) -> VpnUriValidationResult:
        scheme = uri.scheme

        if not scheme:
            return VpnUriValidationResult.failure(
                [
                    ValidationError(
                        "URI must contain a scheme (e.g., vless://, trojan://)"
                    )
                ]
            )

        if scheme not in self.SUPPORTED_SCHEMES:
            return VpnUriValidationResult.failure(
                [
                    ValidationError(
                        f"Unsupported scheme: '{scheme}' is not supported. "
                        f"Supported schemes: {', '.join(self.SUPPORTED_SCHEMES)}"
                    )
                ]
            )

        validator = self._validators.get(scheme)
        if validator:
            return validator.validate(uri)

        return VpnUriValidationResult.failure(
            [ValidationError(f"No validator available for scheme '{scheme}'")]
        )

    def get_supported_schemes(self) -> list[str]:
        return self.SUPPORTED_SCHEMES


class VlessUriValidator(VpnUriValidator):
    def validate(self, uri: VpnUri) -> VpnUriValidationResult:
        errors: list[ValidationError] = []
        uri_str = uri.value

        try:
            parsed = urlparse(uri_str)
        except Exception:
            return VpnUriValidationResult.failure(
                [ValidationError("Invalid URI format")]
            )

        if not parsed.hostname:
            errors.append(ValidationError("Missing required parameter: 'host'"))

        if not parsed.port:
            errors.append(ValidationError("Missing required parameter: 'port'"))

        uuid_pattern = re.compile(
            r"^/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
        )
        uuid_match = uuid_pattern.match(parsed.path)
        if not uuid_match:
            errors.append(
                ValidationError("VLESS requires UUID in path (e.g., /uuid@path)")
            )
        elif uuid_match:
            uuid_str = uuid_match.group(1)
            try:
                import uuid

                uuid.UUID(uuid_str)
            except ValueError:
                errors.append(ValidationError(f"Invalid UUID format: '{uuid_str}'"))

        if errors:
            return VpnUriValidationResult.failure(errors)

        return VpnUriValidationResult.success()

    def get_supported_schemes(self) -> list[str]:
        return ["vless"]


class TrojanUriValidator(VpnUriValidator):
    def validate(self, uri: VpnUri) -> VpnUriValidationResult:
        errors: list[ValidationError] = []
        uri_str = uri.value

        try:
            parsed = urlparse(uri_str)
        except Exception:
            return VpnUriValidationResult.failure(
                [ValidationError("Invalid URI format")]
            )

        if not parsed.hostname:
            errors.append(ValidationError("Missing required parameter: 'host'"))

        if not parsed.port:
            errors.append(ValidationError("Missing required parameter: 'port'"))

        if not parsed.username:
            errors.append(ValidationError("Trojan requires password in userinfo"))

        if errors:
            return VpnUriValidationResult.failure(errors)

        return VpnUriValidationResult.success()

    def get_supported_schemes(self) -> list[str]:
        return ["trojan"]


class VmessUriValidator(VpnUriValidator):
    def validate(self, uri: VpnUri) -> VpnUriValidationResult:
        errors: list[ValidationError] = []
        uri_str = uri.value

        prefix = "vmess://"
        if not uri_str.startswith(prefix):
            return VpnUriValidationResult.failure(
                [ValidationError("VMess URI must start with 'vmess://'")]
            )

        encoded_part = uri_str[len(prefix) :]
        if not encoded_part:
            return VpnUriValidationResult.failure(
                [ValidationError("VMess URI must contain base64-encoded config")]
            )

        try:
            decoded = base64.b64decode(encoded_part).decode("utf-8")
            import json

            config = json.loads(decoded)
        except Exception:
            return VpnUriValidationResult.failure(
                [ValidationError("VMess config must be valid base64-encoded JSON")]
            )

        required_fields = ["add", "port"]
        for field in required_fields:
            if field not in config:
                errors.append(
                    ValidationError(f"VMess config missing required field: '{field}'")
                )

        if "add" in config and not config["add"]:
            errors.append(ValidationError("VMess 'add' (address) cannot be empty"))

        if "port" in config:
            try:
                port = int(config["port"])
                if port < 1 or port > 65535:
                    errors.append(
                        ValidationError(f"VMess port must be between 1 and 65535")
                    )
            except (ValueError, TypeError):
                errors.append(
                    ValidationError(
                        f"VMess port must be a valid number: '{config.get('port')}'"
                    )
                )

        if errors:
            return VpnUriValidationResult.failure(errors)

        return VpnUriValidationResult.success()

    def get_supported_schemes(self) -> list[str]:
        return ["vmess"]


class ShadowsocksUriValidator(VpnUriValidator):
    def validate(self, uri: VpnUri) -> VpnUriValidationResult:
        errors: list[ValidationError] = []
        uri_str = uri.value

        try:
            parsed = urlparse(uri_str)
        except Exception:
            return VpnUriValidationResult.failure(
                [ValidationError("Invalid URI format")]
            )

        if not parsed.hostname:
            errors.append(ValidationError("Missing required parameter: 'host'"))

        if not parsed.port:
            errors.append(ValidationError("Missing required parameter: 'port'"))

        userinfo = parsed.username
        if not userinfo:
            errors.append(
                ValidationError(
                    "Shadowsocks requires method:password in userinfo (base64 encoded)"
                )
            )
        elif userinfo:
            try:
                decoded = base64.urlsafe_b64decode(userinfo + "==").decode("utf-8")
                if ":" not in decoded:
                    errors.append(
                        ValidationError(
                            "Shadowsocks userinfo must be 'method:password' format"
                        )
                    )
            except Exception:
                errors.append(
                    ValidationError("Shadowsocks userinfo must be valid base64")
                )

        if errors:
            return VpnUriValidationResult.failure(errors)

        return VpnUriValidationResult.success()

    def get_supported_schemes(self) -> list[str]:
        return ["ss"]


class ShadowsocksRUriValidator(VpnUriValidator):
    def validate(self, uri: VpnUri) -> VpnUriValidationResult:
        errors: list[ValidationError] = []
        uri_str = uri.value

        try:
            parsed = urlparse(uri_str)
        except Exception:
            return VpnUriValidationResult.failure(
                [ValidationError("Invalid URI format")]
            )

        if not parsed.hostname:
            errors.append(ValidationError("Missing required parameter: 'host'"))

        if not parsed.port:
            errors.append(ValidationError("Missing required parameter: 'port'"))

        userinfo = parsed.username
        if not userinfo:
            errors.append(ValidationError("ShadowsocksR requires encoded userinfo"))

        if errors:
            return VpnUriValidationResult.failure(errors)

        return VpnUriValidationResult.success()

    def get_supported_schemes(self) -> list[str]:
        return ["ssr"]
