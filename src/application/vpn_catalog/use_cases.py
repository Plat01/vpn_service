import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.application.vpn_catalog.dto import (
    BatchCreateFailureDTO,
    BatchCreateResultDTO,
    BatchCreateVpnSourceDTO,
    CreateVpnSourceDTO,
    CreateTagDTO,
    TagDTO,
    UpdateVpnSourceDTO,
    VpnSourceDTO,
    VpnSourceFilterDTO,
    VpnSourceListItemDTO,
)
from src.domain.vpn_catalog.entities import VpnSource, VpnSourceTag
from src.domain.vpn_catalog.repositories import (
    VpnSourceRepository,
    VpnSourceTagRepository,
)
from src.domain.vpn_catalog.validation_errors import ValidationError
from src.domain.vpn_catalog.validators import VpnUriValidator
from src.domain.vpn_catalog.value_objects import TagId, TagSlug, VpnSourceId, VpnUri

logger = logging.getLogger(__name__)


class GetAllVpnSourcesUseCase:
    def __init__(
        self,
        vpn_source_repo: VpnSourceRepository,
    ):
        self._vpn_source_repo = vpn_source_repo

    async def execute(
        self, filter: VpnSourceFilterDTO | None = None
    ) -> list[VpnSourceListItemDTO]:
        tag_slugs = filter.tag_slugs if filter else None
        is_active = filter.is_active if filter else None

        vpn_sources = await self._vpn_source_repo.get_all(
            tag_slugs=tag_slugs,
            is_active=is_active,
        )

        return [
            VpnSourceListItemDTO(
                id=source.id.value,
                name=source.name,
                uri=source.uri.value,
                description=source.description,
                is_active=source.is_active,
                tags=[
                    TagDTO(
                        id=tag.id.value,
                        name=tag.name,
                        slug=tag.slug.value,
                        created_at=tag.created_at,
                    )
                    for tag in source.tags
                ],
                created_at=source.created_at,
                updated_at=source.updated_at,
            )
            for source in vpn_sources
        ]


class GetVpnSourceByIdUseCase:
    def __init__(
        self,
        vpn_source_repo: VpnSourceRepository,
    ):
        self._vpn_source_repo = vpn_source_repo

    async def execute(self, vpn_source_id: UUID) -> VpnSourceDTO | None:
        source = await self._vpn_source_repo.get_by_id(vpn_source_id)

        if not source:
            return None

        return VpnSourceDTO(
            id=source.id.value,
            name=source.name,
            uri=source.uri.value,
            description=source.description,
            is_active=source.is_active,
            created_at=source.created_at,
            updated_at=source.updated_at,
            tags=[
                TagDTO(
                    id=tag.id.value,
                    name=tag.name,
                    slug=tag.slug.value,
                    created_at=tag.created_at,
                )
                for tag in source.tags
            ],
        )


class CreateVpnSourceUseCase:
    def __init__(
        self,
        vpn_source_repo: VpnSourceRepository,
        tag_repo: VpnSourceTagRepository,
        validator: VpnUriValidator,
    ):
        self._vpn_source_repo = vpn_source_repo
        self._tag_repo = tag_repo
        self._validator = validator

    async def execute(self, dto: CreateVpnSourceDTO) -> VpnSourceDTO:
        vpn_uri = VpnUri(value=dto.uri)

        result = self._validator.validate(vpn_uri)
        if not result.is_valid:
            error_messages = "; ".join(e.message for e in result.errors)
            raise ValueError(error_messages)

        tags: list[VpnSourceTag] = []
        if dto.tags:
            tags = await self._tag_repo.get_by_slugs(dto.tags)

        now = datetime.now(timezone.utc)
        vpn_source = VpnSource(
            id=VpnSourceId(value=uuid4()),
            name=dto.name,
            uri=vpn_uri,
            description=dto.description,
            is_active=dto.is_active,
            created_at=now,
            updated_at=now,
            tags=tags,
        )

        created = await self._vpn_source_repo.create(vpn_source)

        if dto.tags:
            tag_ids = [tag.id.value for tag in tags]
            await self._tag_repo.assign_tags_to_source(created.id.value, tag_ids)

        logger.info(
            "VpnSource created: id=%s, name=%s, is_active=%s",
            created.id.value,
            created.name,
            created.is_active,
        )

        return VpnSourceDTO(
            id=created.id.value,
            name=created.name,
            uri=created.uri.value,
            description=created.description,
            is_active=created.is_active,
            created_at=created.created_at,
            updated_at=created.updated_at,
            tags=[
                TagDTO(
                    id=tag.id.value,
                    name=tag.name,
                    slug=tag.slug.value,
                    created_at=tag.created_at,
                )
                for tag in created.tags
            ],
        )


class BatchCreateVpnSourcesUseCase:
    def __init__(
        self,
        vpn_source_repo: VpnSourceRepository,
        tag_repo: VpnSourceTagRepository,
        validator: VpnUriValidator,
    ):
        self._vpn_source_repo = vpn_source_repo
        self._tag_repo = tag_repo
        self._validator = validator

    async def execute(
        self, items: list[BatchCreateVpnSourceDTO]
    ) -> BatchCreateResultDTO:
        created_sources: list[VpnSource] = []
        failed_items: list[BatchCreateFailureDTO] = []

        valid_sources_to_create: list[VpnSource] = []

        for index, item in enumerate(items):
            vpn_uri = VpnUri(value=item.uri)

            result = self._validator.validate(vpn_uri)
            if not result.is_valid:
                error_messages = "; ".join(e.message for e in result.errors)
                failed_items.append(
                    BatchCreateFailureDTO(
                        index=index,
                        name=item.name,
                        uri=item.uri,
                        error=error_messages,
                    )
                )
                continue

            tags: list[VpnSourceTag] = []
            if item.tags:
                tags = await self._tag_repo.get_by_slugs(item.tags)

            now = datetime.now(timezone.utc)
            vpn_source = VpnSource(
                id=VpnSourceId(value=uuid4()),
                name=item.name,
                uri=vpn_uri,
                description=item.description,
                is_active=item.is_active,
                created_at=now,
                updated_at=now,
                tags=tags,
            )

            valid_sources_to_create.append(vpn_source)

        if valid_sources_to_create:
            created_sources = await self._vpn_source_repo.create_batch(
                valid_sources_to_create
            )

            for source in created_sources:
                if source.tags:
                    tag_ids = [tag.id.value for tag in source.tags]
                    await self._tag_repo.assign_tags_to_source(source.id.value, tag_ids)

        created_dtos = [
            VpnSourceDTO(
                id=source.id.value,
                name=source.name,
                uri=source.uri.value,
                description=source.description,
                is_active=source.is_active,
                created_at=source.created_at,
                updated_at=source.updated_at,
                tags=[
                    TagDTO(
                        id=tag.id.value,
                        name=tag.name,
                        slug=tag.slug.value,
                        created_at=tag.created_at,
                    )
                    for tag in source.tags
                ],
            )
            for source in created_sources
        ]

        logger.info(
            "Batch VpnSource creation: total=%d, success=%d, failed=%d",
            len(items),
            len(created_sources),
            len(failed_items),
        )

        return BatchCreateResultDTO(
            created=created_dtos,
            failed=failed_items,
            total=len(items),
            success_count=len(created_sources),
            failed_count=len(failed_items),
        )


class UpdateVpnSourceUseCase:
    def __init__(
        self,
        vpn_source_repo: VpnSourceRepository,
        tag_repo: VpnSourceTagRepository,
        validator: VpnUriValidator,
    ):
        self._vpn_source_repo = vpn_source_repo
        self._tag_repo = tag_repo
        self._validator = validator

    async def execute(
        self, vpn_source_id: UUID, dto: UpdateVpnSourceDTO
    ) -> VpnSourceDTO:
        source = await self._vpn_source_repo.get_by_id(vpn_source_id)

        if not source:
            raise ValueError(f"VpnSource with id {vpn_source_id} not found")

        if dto.uri is not None:
            vpn_uri = VpnUri(value=dto.uri)
            result = self._validator.validate(vpn_uri)
            if not result.is_valid:
                error_messages = "; ".join(e.message for e in result.errors)
                raise ValueError(error_messages)
            source.update(uri=vpn_uri)

        source.update(
            name=dto.name,
            description=dto.description,
            is_active=dto.is_active,
        )

        if dto.tags is not None:
            tags = await self._tag_repo.get_by_slugs(dto.tags)
            source.assign_tags(tags)

        source.updated_at = datetime.now(timezone.utc)

        updated = await self._vpn_source_repo.update(source)

        if dto.tags is not None:
            tag_ids = [tag.id.value for tag in source.tags]
            await self._tag_repo.assign_tags_to_source(updated.id.value, tag_ids)

        logger.info(
            "VpnSource updated: id=%s, name=%s, is_active=%s",
            updated.id.value,
            updated.name,
            updated.is_active,
        )

        return VpnSourceDTO(
            id=updated.id.value,
            name=updated.name,
            uri=updated.uri.value,
            description=updated.description,
            is_active=updated.is_active,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            tags=[
                TagDTO(
                    id=tag.id.value,
                    name=tag.name,
                    slug=tag.slug.value,
                    created_at=tag.created_at,
                )
                for tag in updated.tags
            ],
        )


class DeleteVpnSourceUseCase:
    def __init__(
        self,
        vpn_source_repo: VpnSourceRepository,
    ):
        self._vpn_source_repo = vpn_source_repo

    async def execute(self, vpn_source_id: UUID) -> bool:
        deleted = await self._vpn_source_repo.delete(vpn_source_id)

        if deleted:
            logger.info("VpnSource deleted: id=%s", vpn_source_id)

        return deleted
