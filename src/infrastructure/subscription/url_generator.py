from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.subscription_issuance.value_objects import (
    SubscriptionBehavior,
    SubscriptionMetadata,
)
from src.infrastructure.subscription.happ_metadata_generator import (
    HappMetadataGenerator,
)


class VpnSourceInfo:
    def __init__(self, name: str, uri: str):
        self.name = name
        self.uri = uri


class SubscriptionConfigGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        vpn_sources: list[VpnSourceInfo],
        metadata: SubscriptionMetadata | None = None,
        behavior: SubscriptionBehavior | None = None,
        provider_id: str | None = None,
        expires_at: datetime | None = None,
        public_id: str | None = None,
    ) -> str:
        pass


class TextListConfigGenerator(SubscriptionConfigGenerator):
    def __init__(self, metadata_generator: HappMetadataGenerator):
        self._metadata_generator = metadata_generator

    def _add_fragment_to_uri(self, uri: str, name: str) -> str:
        if "#" in uri:
            base_uri = uri.split("#")[0]
        else:
            base_uri = uri
        return f"{base_uri}#{name}"

    def generate(
        self,
        vpn_sources: list[VpnSourceInfo],
        metadata: SubscriptionMetadata | None = None,
        behavior: SubscriptionBehavior | None = None,
        provider_id: str | None = None,
        expires_at: datetime | None = None,
        public_id: str | None = None,
    ) -> str:
        lines = []

        if expires_at and public_id:
            headers = self._metadata_generator.generate_headers(
                metadata=metadata,
                behavior=behavior,
                provider_id=provider_id,
                expires_at=expires_at,
                public_id=public_id,
            )
            lines.extend(headers)

        if lines:
            lines.append("")

        for source in vpn_sources:
            uri_with_name = self._add_fragment_to_uri(source.uri, source.name)
            lines.append(uri_with_name)

        return "\n".join(lines)
