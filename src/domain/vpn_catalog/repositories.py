from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.vpn_catalog.entities import VpnSource, VpnSourceImport, VpnSourceTag


class VpnSourceRepository(ABC):
    @abstractmethod
    async def get_all(
        self,
        tag_slugs: list[str] | None = None,
        is_active: bool | None = None,
    ) -> list[VpnSource]:
        pass

    @abstractmethod
    async def get_by_id(self, vpn_source_id: UUID) -> VpnSource | None:
        pass

    @abstractmethod
    async def get_by_uri(
        self, uri: str, import_group: str | None = None
    ) -> VpnSource | None:
        pass

    @abstractmethod
    async def get_all_by_import_group(
        self, import_group: str, is_active: bool | None = None
    ) -> list[VpnSource]:
        pass

    @abstractmethod
    async def create(self, vpn_source: VpnSource) -> VpnSource:
        pass

    @abstractmethod
    async def update(self, vpn_source: VpnSource) -> VpnSource:
        pass

    @abstractmethod
    async def delete(self, vpn_source_id: UUID) -> bool:
        pass

    @abstractmethod
    async def create_batch(self, vpn_sources: list[VpnSource]) -> list[VpnSource]:
        pass

    @abstractmethod
    async def deactivate_batch(self, vpn_source_ids: list[UUID]) -> int:
        pass

    @abstractmethod
    async def update_batch(self, vpn_sources: list[VpnSource]) -> list[VpnSource]:
        pass


class VpnSourceImportRepository(ABC):
    @abstractmethod
    async def create(self, import_: VpnSourceImport) -> VpnSourceImport:
        pass

    @abstractmethod
    async def get_by_id(self, import_id: UUID) -> VpnSourceImport | None:
        pass

    @abstractmethod
    async def get_recent(
        self, import_group: str | None = None, limit: int = 50
    ) -> list[VpnSourceImport]:
        pass


class VpnSourceTagRepository(ABC):
    @abstractmethod
    async def get_all(self) -> list[VpnSourceTag]:
        pass

    @abstractmethod
    async def get_by_id(self, tag_id: UUID) -> VpnSourceTag | None:
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> VpnSourceTag | None:
        pass

    @abstractmethod
    async def get_by_slugs(self, slugs: list[str]) -> list[VpnSourceTag]:
        pass

    @abstractmethod
    async def create(self, tag: VpnSourceTag) -> VpnSourceTag:
        pass

    @abstractmethod
    async def create_or_get(self, name: str, slug: str) -> VpnSourceTag:
        pass

    @abstractmethod
    async def assign_tags_to_source(
        self, vpn_source_id: UUID, tag_ids: list[UUID]
    ) -> None:
        pass

    @abstractmethod
    async def get_tags_for_source(self, vpn_source_id: UUID) -> list[VpnSourceTag]:
        pass
