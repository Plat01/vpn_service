import logging
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from src.application.vpn_catalog.dto import (
    BatchCreateFailureDTO,
    BatchCreateResultDTO,
    BatchCreateVpnSourceDTO,
    CreateVpnSourceDTO,
    SyncTextFailureDTO,
    SyncTextResultDTO,
    TagDTO,
    UpdateVpnSourceDTO,
    VpnSourceDTO,
    VpnSourceFilterDTO,
    VpnSourceListItemDTO,
)
from src.domain.vpn_catalog.entities import VpnSource, VpnSourceImport, VpnSourceTag
from src.domain.vpn_catalog.repositories import (
    VpnSourceImportRepository,
    VpnSourceRepository,
    VpnSourceTagRepository,
)
from src.domain.vpn_catalog.validators import VpnUriValidator
from src.domain.vpn_catalog.value_objects import VpnSourceId, VpnUri
from src.infrastructure.parsers import PlainTextUriParser, ParsedUriDTO

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


class SyncVpnSourcesTextUseCase:
    def __init__(
        self,
        vpn_source_repo: VpnSourceRepository,
        tag_repo: VpnSourceTagRepository,
        validator: VpnUriValidator,
        import_repo: VpnSourceImportRepository,
        parser: PlainTextUriParser | None = None,
    ):
        self._vpn_source_repo = vpn_source_repo
        self._tag_repo = tag_repo
        self._validator = validator
        self._import_repo = import_repo
        self._parser = parser or PlainTextUriParser()

    async def execute(
        self,
        text: str,
        mode: Literal["replace", "upsert", "append"],
        import_group: str,
        tags: list[str],
        dry_run: bool,
        deactivate_missing: bool,
        ignore_invalid: bool,
        name_strategy: Literal["fragment", "host", "line_number"],
    ) -> SyncTextResultDTO:
        parsed_items = self._parser.parse(text)
        parsed_count = len(parsed_items)

        valid_items: list[ParsedUriDTO] = []
        failed_items: list[SyncTextFailureDTO] = []

        for item in parsed_items:
            vpn_uri = VpnUri(value=item.raw_uri)
            result = self._validator.validate(vpn_uri)
            if not result.is_valid:
                error_messages = "; ".join(e.message for e in result.errors)
                failed_items.append(
                    SyncTextFailureDTO(
                        line=item.line_number,
                        raw=self._parser.mask_uri_for_logging(item.raw_uri),
                        error=error_messages,
                    )
                )
                continue
            valid_items.append(item)

        valid_count = len(valid_items)
        invalid_count = len(failed_items)

        if invalid_count > 0 and not ignore_invalid:
            return SyncTextResultDTO(
                dry_run=dry_run,
                mode=mode,
                import_group=import_group,
                tags=tags,
                parsed_count=parsed_count,
                valid_count=valid_count,
                invalid_count=invalid_count,
                to_create_count=0,
                to_update_count=0,
                to_deactivate_count=0,
                failed=failed_items,
            )

        tag_entities: list[VpnSourceTag] = []
        if tags:
            tag_entities = await self._tag_repo.get_by_slugs(tags)

        existing_sources = await self._vpn_source_repo.get_all_by_import_group(
            import_group, is_active=True
        )
        existing_uris = {s.uri.value for s in existing_sources}
        existing_by_uri = {s.uri.value: s for s in existing_sources}

        to_create: list[VpnSource] = []
        to_update: list[VpnSource] = []
        to_deactivate_ids: list[UUID] = []

        now = datetime.now(timezone.utc)
        seen_uris_in_text: set[str] = set()

        for item in valid_items:
            uri = item.raw_uri
            seen_uris_in_text.add(uri)

            name = self._resolve_name(item, name_strategy)

            if uri in existing_uris:
                existing = existing_by_uri[uri]
                existing.name = name
                existing.updated_at = now
                existing.is_active = True
                existing.tags = tag_entities
                to_update.append(existing)
            else:
                new_source = VpnSource(
                    id=VpnSourceId(value=uuid4()),
                    name=name,
                    uri=VpnUri(value=uri),
                    is_active=True,
                    import_group=import_group,
                    created_at=now,
                    updated_at=now,
                    tags=tag_entities,
                )
                to_create.append(new_source)

        if mode == "replace" and deactivate_missing:
            for source in existing_sources:
                if source.uri.value not in seen_uris_in_text:
                    to_deactivate_ids.append(source.id.value)

        to_create_count = len(to_create)
        to_update_count = len(to_update)
        to_deactivate_count = len(to_deactivate_ids)

        created_dtos: list[VpnSourceDTO] = []
        updated_dtos: list[VpnSourceDTO] = []
        deactivated_dtos: list[VpnSourceDTO] = []

        if not dry_run:
            if to_create:
                created = await self._vpn_source_repo.create_batch(to_create)
                if tags:
                    for source in created:
                        tag_ids = [t.id.value for t in tag_entities]
                        await self._tag_repo.assign_tags_to_source(source.id.value, tag_ids)
                created_dtos = [self._source_to_dto(s) for s in created]

            if to_update:
                updated = await self._vpn_source_repo.update_batch(to_update)
                if tags:
                    for source in updated:
                        tag_ids = [t.id.value for t in tag_entities]
                        await self._tag_repo.assign_tags_to_source(source.id.value, tag_ids)
                updated_dtos = [self._source_to_dto(s) for s in updated]

            if to_deactivate_ids:
                await self._vpn_source_repo.deactivate_batch(to_deactivate_ids)
                deactivated = [s for s in existing_sources if s.id.value in to_deactivate_ids]
                deactivated_dtos = [self._source_to_dto(s) for s in deactivated]

            import_entity = VpnSourceImport(
                id=uuid4(),
                import_group=import_group,
                mode=mode,
                dry_run=dry_run,
                total_count=parsed_count,
                valid_count=valid_count,
                invalid_count=invalid_count,
                created_count=len(created_dtos),
                updated_count=len(updated_dtos),
                deactivated_count=len(deactivated_dtos),
                failed_count=len(failed_items),
                created_at=now,
                error_summary={
                    "failed": [
                        {"line": f.line, "raw": f.raw, "error": f.error}
                        for f in failed_items
                    ]
                } if failed_items else None,
            )
            await self._import_repo.create(import_entity)

            logger.info(
                "Sync completed: group=%s, mode=%s, created=%d, updated=%d, deactivated=%d, failed=%d",
                import_group,
                mode,
                len(created_dtos),
                len(updated_dtos),
                len(deactivated_dtos),
                len(failed_items),
            )

        return SyncTextResultDTO(
            dry_run=dry_run,
            mode=mode,
            import_group=import_group,
            tags=tags,
            parsed_count=parsed_count,
            valid_count=valid_count,
            invalid_count=invalid_count,
            to_create_count=to_create_count,
            to_update_count=to_update_count,
            to_deactivate_count=to_deactivate_count,
            created=created_dtos,
            updated=updated_dtos,
            deactivated=deactivated_dtos,
            failed=failed_items,
        )

    def _resolve_name(
        self, item: ParsedUriDTO, strategy: Literal["fragment", "host", "line_number"]
    ) -> str:
        if strategy == "fragment" and item.name:
            return item.name
        if strategy == "host":
            uri = item.raw_uri
            if "://" in uri:
                after_scheme = uri.split("://", 1)[1]
                if "@" in after_scheme:
                    host_port = after_scheme.split("@", 1)[1]
                    host = host_port.split(":")[0].split("?")[0]
                    return host
            return f"source-{item.line_number}"
        return f"source-{item.line_number}"

    def _source_to_dto(self, source: VpnSource) -> VpnSourceDTO:
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
                    id=t.id.value,
                    name=t.name,
                    slug=t.slug.value,
                    created_at=t.created_at,
                )
                for t in source.tags
            ],
        )
