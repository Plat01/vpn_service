from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.vpn_catalog.dto import (
    BatchCreateVpnSourceDTO,
    CreateVpnSourceDTO,
    UpdateVpnSourceDTO,
    VpnSourceFilterDTO,
)
from src.application.vpn_catalog.use_cases import (
    BatchCreateVpnSourcesUseCase,
    CreateVpnSourceUseCase,
    DeleteVpnSourceUseCase,
    GetAllVpnSourcesUseCase,
    GetVpnSourceByIdUseCase,
    UpdateVpnSourceUseCase,
)
from src.domain.vpn_catalog.repositories import (
    VpnSourceRepository,
    VpnSourceTagRepository,
)
from src.domain.vpn_catalog.validators import VpnUriValidator
from src.infrastructure.db.repositories import (
    SqlAlchemyVpnSourceRepository,
    SqlAlchemyVpnSourceTagRepository,
)
from src.infrastructure.validators import CompositeVpnUriValidator
from src.presentation.http.dependencies import get_current_admin
from src.presentation.http.dto import (
    BatchCreateFailureResponse,
    BatchCreateRequest,
    BatchCreateResponse,
    CreateVpnSourceRequest,
    TagResponse,
    UpdateVpnSourceRequest,
    VpnSourceDetailResponse,
    VpnSourceListItemResponse,
    VpnSourceListResponse,
)
from src.infrastructure.db.database import get_session

router = APIRouter()


def get_vpn_source_repo(
    session: get_session = Depends(get_session),
) -> VpnSourceRepository:
    return SqlAlchemyVpnSourceRepository(session)


def get_tag_repo(session: get_session = Depends(get_session)) -> VpnSourceTagRepository:
    return SqlAlchemyVpnSourceTagRepository(session)


def get_validator() -> VpnUriValidator:
    return CompositeVpnUriValidator()


@router.get("/vpn-sources", response_model=VpnSourceListResponse)
async def list_vpn_sources(
    admin: str = Depends(get_current_admin),
    vpn_source_repo: VpnSourceRepository = Depends(get_vpn_source_repo),
    tags: Annotated[str | None, Query(description="Comma-separated tag slugs")] = None,
    is_active: Annotated[bool | None, Query()] = None,
):
    tag_slugs = tags.split(",") if tags else None

    filter_dto = VpnSourceFilterDTO(tag_slugs=tag_slugs, is_active=is_active)

    use_case = GetAllVpnSourcesUseCase(vpn_source_repo)
    result = await use_case.execute(filter_dto)

    return VpnSourceListResponse(
        items=[
            VpnSourceListItemResponse(
                id=item.id,
                name=item.name,
                uri=item.uri,
                description=item.description,
                is_active=item.is_active,
                tags=[
                    TagResponse(
                        id=tag.id,
                        name=tag.name,
                        slug=tag.slug,
                        created_at=tag.created_at,
                    )
                    for tag in item.tags
                ],
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result
        ]
    )


@router.get("/vpn-sources/{vpn_source_id}", response_model=VpnSourceDetailResponse)
async def get_vpn_source(
    vpn_source_id: UUID,
    admin: str = Depends(get_current_admin),
    vpn_source_repo: VpnSourceRepository = Depends(get_vpn_source_repo),
):
    use_case = GetVpnSourceByIdUseCase(vpn_source_repo)
    result = await use_case.execute(vpn_source_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VpnSource with id {vpn_source_id} not found",
        )

    return VpnSourceDetailResponse(
        id=result.id,
        name=result.name,
        uri=result.uri,
        description=result.description,
        is_active=result.is_active,
        tags=[
            TagResponse(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                created_at=tag.created_at,
            )
            for tag in result.tags
        ],
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post(
    "/vpn-sources",
    response_model=VpnSourceDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vpn_source(
    request: CreateVpnSourceRequest,
    admin: str = Depends(get_current_admin),
    vpn_source_repo: VpnSourceRepository = Depends(get_vpn_source_repo),
    tag_repo: VpnSourceTagRepository = Depends(get_tag_repo),
    validator: VpnUriValidator = Depends(get_validator),
):
    use_case = CreateVpnSourceUseCase(
        vpn_source_repo=vpn_source_repo,
        tag_repo=tag_repo,
        validator=validator,
    )

    dto = CreateVpnSourceDTO(
        name=request.name,
        uri=request.uri,
        description=request.description,
        is_active=request.is_active,
        tags=request.tags,
    )

    try:
        result = await use_case.execute(dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return VpnSourceDetailResponse(
        id=result.id,
        name=result.name,
        uri=result.uri,
        description=result.description,
        is_active=result.is_active,
        tags=[
            TagResponse(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                created_at=tag.created_at,
            )
            for tag in result.tags
        ],
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post(
    "/vpn-sources/batch",
    response_model=BatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def batch_create_vpn_sources(
    request: BatchCreateRequest,
    admin: str = Depends(get_current_admin),
    vpn_source_repo: VpnSourceRepository = Depends(get_vpn_source_repo),
    tag_repo: VpnSourceTagRepository = Depends(get_tag_repo),
    validator: VpnUriValidator = Depends(get_validator),
):
    use_case = BatchCreateVpnSourcesUseCase(
        vpn_source_repo=vpn_source_repo,
        tag_repo=tag_repo,
        validator=validator,
    )

    items = [
        BatchCreateVpnSourceDTO(
            name=item.name,
            uri=item.uri,
            description=item.description,
            is_active=item.is_active,
            tags=item.tags,
        )
        for item in request.items
    ]

    result = await use_case.execute(items)

    return BatchCreateResponse(
        created=[
            VpnSourceDetailResponse(
                id=source.id,
                name=source.name,
                uri=source.uri,
                description=source.description,
                is_active=source.is_active,
                tags=[
                    TagResponse(
                        id=tag.id,
                        name=tag.name,
                        slug=tag.slug,
                        created_at=tag.created_at,
                    )
                    for tag in source.tags
                ],
                created_at=source.created_at,
                updated_at=source.updated_at,
            )
            for source in result.created
        ],
        failed=[
            BatchCreateFailureResponse(
                index=failure.index,
                name=failure.name,
                uri=failure.uri,
                error=failure.error,
            )
            for failure in result.failed
        ],
        total=result.total,
        success_count=result.success_count,
        failed_count=result.failed_count,
    )


@router.patch("/vpn-sources/{vpn_source_id}", response_model=VpnSourceDetailResponse)
async def update_vpn_source(
    vpn_source_id: UUID,
    request: UpdateVpnSourceRequest,
    admin: str = Depends(get_current_admin),
    vpn_source_repo: VpnSourceRepository = Depends(get_vpn_source_repo),
    tag_repo: VpnSourceTagRepository = Depends(get_tag_repo),
    validator: VpnUriValidator = Depends(get_validator),
):
    use_case = UpdateVpnSourceUseCase(
        vpn_source_repo=vpn_source_repo,
        tag_repo=tag_repo,
        validator=validator,
    )

    dto = UpdateVpnSourceDTO(
        name=request.name,
        uri=request.uri,
        description=request.description,
        is_active=request.is_active,
        tags=request.tags,
    )

    try:
        result = await use_case.execute(vpn_source_id, dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return VpnSourceDetailResponse(
        id=result.id,
        name=result.name,
        uri=result.uri,
        description=result.description,
        is_active=result.is_active,
        tags=[
            TagResponse(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                created_at=tag.created_at,
            )
            for tag in result.tags
        ],
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.delete("/vpn-sources/{vpn_source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vpn_source(
    vpn_source_id: UUID,
    admin: str = Depends(get_current_admin),
    vpn_source_repo: VpnSourceRepository = Depends(get_vpn_source_repo),
):
    use_case = DeleteVpnSourceUseCase(vpn_source_repo)

    deleted = await use_case.execute(vpn_source_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VpnSource with id {vpn_source_id} not found",
        )
