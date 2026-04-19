from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.vpn_catalog.entities import VpnSourceTag
from src.domain.vpn_catalog.repositories import VpnSourceTagRepository
from src.domain.vpn_catalog.value_objects import TagId, TagSlug
from src.infrastructure.db.models import (
    VpnSourceTagAssociationModel,
    VpnSourceTagModel,
)


class SqlAlchemyVpnSourceTagRepository(VpnSourceTagRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_all(self) -> list[VpnSourceTag]:
        stmt = select(VpnSourceTagModel).order_by(VpnSourceTagModel.name)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def get_by_id(self, tag_id: UUID) -> VpnSourceTag | None:
        stmt = select(VpnSourceTagModel).where(VpnSourceTagModel.id == tag_id)

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def get_by_slug(self, slug: str) -> VpnSourceTag | None:
        stmt = select(VpnSourceTagModel).where(VpnSourceTagModel.slug == slug)

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def get_by_slugs(self, slugs: list[str]) -> list[VpnSourceTag]:
        stmt = select(VpnSourceTagModel).where(VpnSourceTagModel.slug.in_(slugs))

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def create(self, tag: VpnSourceTag) -> VpnSourceTag:
        model = VpnSourceTagModel(
            id=tag.id.value,
            name=tag.name,
            slug=tag.slug.value,
            created_at=tag.created_at,
        )

        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        return self._model_to_entity(model)

    async def create_or_get(self, name: str, slug: str) -> VpnSourceTag:
        existing = await self.get_by_slug(slug)

        if existing:
            return existing

        tag = VpnSourceTag(
            id=TagId(value=uuid4()),
            name=name,
            slug=TagSlug(value=slug),
            created_at=datetime.now(timezone.utc),
        )

        return await self.create(tag)

    async def assign_tags_to_source(
        self, vpn_source_id: UUID, tag_ids: list[UUID]
    ) -> None:
        stmt = delete(VpnSourceTagAssociationModel).where(
            VpnSourceTagAssociationModel.vpn_source_id == vpn_source_id
        )
        await self._session.execute(stmt)

        if tag_ids:
            stmt = insert(VpnSourceTagAssociationModel).values(
                [
                    {"vpn_source_id": vpn_source_id, "tag_id": tag_id}
                    for tag_id in tag_ids
                ]
            )
            await self._session.execute(stmt)

        await self._session.flush()

    async def get_tags_for_source(self, vpn_source_id: UUID) -> list[VpnSourceTag]:
        stmt = (
            select(VpnSourceTagModel)
            .join(VpnSourceTagAssociationModel)
            .where(VpnSourceTagAssociationModel.vpn_source_id == vpn_source_id)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    def _model_to_entity(self, model: VpnSourceTagModel) -> VpnSourceTag:
        return VpnSourceTag(
            id=TagId(value=model.id),
            name=model.name,
            slug=TagSlug(value=model.slug),
            created_at=model.created_at,
        )
