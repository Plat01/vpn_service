
from fastapi import APIRouter, Depends, HTTPException, status

from src.application.vpn_catalog.dto import CreateTagDTO
from src.application.vpn_catalog.tag_use_cases import (
    CreateTagUseCase,
    GetAllTagsUseCase,
)
from src.domain.vpn_catalog.repositories import VpnSourceTagRepository
from src.infrastructure.db.repositories import SqlAlchemyVpnSourceTagRepository
from src.presentation.http.dependencies import get_current_admin
from src.presentation.http.dto import CreateTagRequest, TagListResponse, TagResponse
from src.infrastructure.db.database import get_session

router = APIRouter()


def get_tag_repo(session: get_session = Depends(get_session)) -> VpnSourceTagRepository:
    return SqlAlchemyVpnSourceTagRepository(session)


@router.get("/vpn-source-tags", response_model=TagListResponse)
async def list_tags(
    admin: str = Depends(get_current_admin),
    tag_repo: VpnSourceTagRepository = Depends(get_tag_repo),
):
    use_case = GetAllTagsUseCase(tag_repo)
    result = await use_case.execute()

    return TagListResponse(
        items=[
            TagResponse(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                created_at=tag.created_at,
            )
            for tag in result
        ]
    )


@router.post(
    "/vpn-source-tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED
)
async def create_tag(
    request: CreateTagRequest,
    admin: str = Depends(get_current_admin),
    tag_repo: VpnSourceTagRepository = Depends(get_tag_repo),
):
    use_case = CreateTagUseCase(tag_repo)

    dto = CreateTagDTO(name=request.name, slug=request.slug)

    try:
        result = await use_case.execute(dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return TagResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        created_at=result.created_at,
    )
