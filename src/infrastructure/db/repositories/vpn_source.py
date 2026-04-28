from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.vpn_catalog.entities import VpnSource, VpnSourceTag
from src.domain.vpn_catalog.repositories import VpnSourceRepository
from src.domain.vpn_catalog.value_objects import TagId, TagSlug, VpnSourceId, VpnUri
from src.infrastructure.db.models import (
    VpnSourceModel,
    VpnSourceTagModel,
)


class SqlAlchemyVpnSourceRepository(VpnSourceRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_all(
        self,
        tag_slugs: list[str] | None = None,
        is_active: bool | None = None,
    ) -> list[VpnSource]:
        stmt = select(VpnSourceModel).options(selectinload(VpnSourceModel.tags))

        if is_active is not None:
            stmt = stmt.where(VpnSourceModel.is_active == is_active)

        if tag_slugs:
            stmt = stmt.join(VpnSourceModel.tags).where(
                VpnSourceTagModel.slug.in_(tag_slugs)
            )

        result = await self._session.execute(stmt)
        models = result.scalars().unique().all()

        return [self._model_to_entity(model) for model in models]

    async def get_by_id(self, vpn_source_id: UUID) -> VpnSource | None:
        stmt = (
            select(VpnSourceModel)
            .where(VpnSourceModel.id == vpn_source_id)
            .options(selectinload(VpnSourceModel.tags))
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def create(self, vpn_source: VpnSource) -> VpnSource:
        model = VpnSourceModel(
            id=vpn_source.id.value,
            name=vpn_source.name,
            uri=vpn_source.uri.value,
            description=vpn_source.description,
            is_active=vpn_source.is_active,
            import_group=vpn_source.import_group,
            created_at=vpn_source.created_at,
            updated_at=vpn_source.updated_at,
        )

        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model, ["tags"])

        return self._model_to_entity(model)

    async def update(self, vpn_source: VpnSource) -> VpnSource:
        stmt = (
            update(VpnSourceModel)
            .where(VpnSourceModel.id == vpn_source.id.value)
            .values(
                name=vpn_source.name,
                uri=vpn_source.uri.value,
                description=vpn_source.description,
                is_active=vpn_source.is_active,
                updated_at=datetime.now(timezone.utc),
            )
        )

        await self._session.execute(stmt)
        await self._session.flush()

        stmt = (
            select(VpnSourceModel)
            .where(VpnSourceModel.id == vpn_source.id.value)
            .options(selectinload(VpnSourceModel.tags))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one()

        return self._model_to_entity(model)

    async def delete(self, vpn_source_id: UUID) -> bool:
        stmt = delete(VpnSourceModel).where(VpnSourceModel.id == vpn_source_id)

        result = await self._session.execute(stmt)
        await self._session.flush()

        return result.rowcount > 0

    async def create_batch(self, vpn_sources: list[VpnSource]) -> list[VpnSource]:
        models = [
            VpnSourceModel(
                id=source.id.value,
                name=source.name,
                uri=source.uri.value,
                description=source.description,
                is_active=source.is_active,
                import_group=source.import_group,
                created_at=source.created_at,
                updated_at=source.updated_at,
            )
            for source in vpn_sources
        ]

        self._session.add_all(models)
        await self._session.flush()

        for model in models:
            await self._session.refresh(model, ["tags"])

        return [self._model_to_entity(model) for model in models]

    async def get_by_uri(
        self, uri: str, import_group: str | None = None
    ) -> VpnSource | None:
        stmt = select(VpnSourceModel).where(VpnSourceModel.uri == uri)
        if import_group:
            stmt = stmt.where(VpnSourceModel.import_group == import_group)
        stmt = stmt.options(selectinload(VpnSourceModel.tags))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def get_all_by_import_group(
        self, import_group: str, is_active: bool | None = None
    ) -> list[VpnSource]:
        stmt = select(VpnSourceModel).where(
            VpnSourceModel.import_group == import_group
        )
        if is_active is not None:
            stmt = stmt.where(VpnSourceModel.is_active == is_active)
        stmt = stmt.options(selectinload(VpnSourceModel.tags))
        result = await self._session.execute(stmt)
        models = result.scalars().unique().all()
        return [self._model_to_entity(m) for m in models]

    async def deactivate_batch(self, vpn_source_ids: list[UUID]) -> int:
        stmt = (
            update(VpnSourceModel)
            .where(VpnSourceModel.id.in_(vpn_source_ids))
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def update_batch(self, vpn_sources: list[VpnSource]) -> list[VpnSource]:
        updated_models = []
        for source in vpn_sources:
            stmt = (
                update(VpnSourceModel)
                .where(VpnSourceModel.id == source.id.value)
                .values(
                    name=source.name,
                    uri=source.uri.value,
                    description=source.description,
                    is_active=source.is_active,
                    import_group=source.import_group,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await self._session.execute(stmt)

        await self._session.flush()

        ids = [s.id.value for s in vpn_sources]
        stmt = (
            select(VpnSourceModel)
            .where(VpnSourceModel.id.in_(ids))
            .options(selectinload(VpnSourceModel.tags))
        )
        result = await self._session.execute(stmt)
        models = result.scalars().unique().all()
        return [self._model_to_entity(m) for m in models]

    def _model_to_entity(self, model: VpnSourceModel) -> VpnSource:
        tags = [
            VpnSourceTag(
                id=TagId(value=tag_model.id),
                name=tag_model.name,
                slug=TagSlug(value=tag_model.slug),
                created_at=tag_model.created_at,
            )
            for tag_model in model.tags
        ]

        return VpnSource(
            id=VpnSourceId(value=model.id),
            name=model.name,
            uri=VpnUri(value=model.uri),
            description=model.description,
            is_active=model.is_active,
            import_group=model.import_group or "default",
            created_at=model.created_at,
            updated_at=model.updated_at,
            tags=tags,
        )
