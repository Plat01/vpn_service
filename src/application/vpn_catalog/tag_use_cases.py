from datetime import datetime, timezone
from uuid import uuid4

from src.application.vpn_catalog.dto import CreateTagDTO, TagDTO
from src.domain.vpn_catalog.entities import VpnSourceTag
from src.domain.vpn_catalog.repositories import VpnSourceTagRepository
from src.domain.vpn_catalog.value_objects import TagId, TagSlug


class GetAllTagsUseCase:
    def __init__(self, tag_repo: VpnSourceTagRepository):
        self._tag_repo = tag_repo

    async def execute(self) -> list[TagDTO]:
        tags = await self._tag_repo.get_all()

        return [
            TagDTO(
                id=tag.id.value,
                name=tag.name,
                slug=tag.slug.value,
                created_at=tag.created_at,
            )
            for tag in tags
        ]


class CreateTagUseCase:
    def __init__(self, tag_repo: VpnSourceTagRepository):
        self._tag_repo = tag_repo

    async def execute(self, dto: CreateTagDTO) -> TagDTO:
        slug = dto.slug or dto.name.lower().replace(" ", "-").replace("_", "-")

        existing = await self._tag_repo.get_by_slug(slug)
        if existing:
            raise ValueError(f"Tag with slug '{slug}' already exists")

        tag = VpnSourceTag(
            id=TagId(value=uuid4()),
            name=dto.name,
            slug=TagSlug(value=slug),
            created_at=datetime.now(timezone.utc),
        )

        created = await self._tag_repo.create(tag)

        return TagDTO(
            id=created.id.value,
            name=created.name,
            slug=created.slug.value,
            created_at=created.created_at,
        )
