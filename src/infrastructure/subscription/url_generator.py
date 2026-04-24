from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.subscription_issuance.value_objects import (
    SubscriptionBehavior,
    SubscriptionMetadata,
)
from src.infrastructure.subscription.happ_metadata_generator import (
    HappMetadataGenerator,
)


class SubscriptionConfigGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        vpn_uris: list[str],
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

    def generate(
        self,
        vpn_uris: list[str],
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

        lines.extend(vpn_uris)

        return "\n".join(lines)
