from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from src.application.vpn_catalog.dto import (
    BatchCreateVpnSourceDTO,
    CreateVpnSourceDTO,
    SyncTextFailureDTO,
    UpdateVpnSourceDTO,
    VpnSourceFilterDTO,
)
from src.application.vpn_catalog.use_cases import (
    BatchCreateVpnSourcesUseCase,
    CreateVpnSourceUseCase,
    DeleteVpnSourceUseCase,
    GetAllVpnSourcesUseCase,
    GetVpnSourceByIdUseCase,
    SyncVpnSourcesTextUseCase,
    UpdateVpnSourceUseCase,
)
from src.domain.vpn_catalog.repositories import (
    VpnSourceImportRepository,
    VpnSourceRepository,
    VpnSourceTagRepository,
)
from src.domain.vpn_catalog.validators import VpnUriValidator
from src.infrastructure.db.repositories import (
    SqlAlchemyVpnSourceImportRepository,
    SqlAlchemyVpnSourceRepository,
    SqlAlchemyVpnSourceTagRepository,
)
from src.infrastructure.parsers import PlainTextUriParser
from src.infrastructure.validators import CompositeVpnUriValidator
from src.presentation.http.dependencies import get_current_admin
from src.presentation.http.dto import (
    BatchCreateFailureResponse,
    BatchCreateRequest,
    BatchCreateResponse,
    CreateVpnSourceRequest,
    SyncTextFailureResponse,
    SyncTextPreviewItem,
    SyncTextResponse,
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


def get_import_repo(
    session: get_session = Depends(get_session),
) -> VpnSourceImportRepository:
    return SqlAlchemyVpnSourceImportRepository(session)


def get_parser() -> PlainTextUriParser:
    return PlainTextUriParser()


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


@router.put(
    "/vpn-sources/sync-text",
    response_model=SyncTextResponse,
    summary="Sync VPN sources from plain text",
)
async def sync_vpn_sources_text(
    text: str = Body(
        ...,
        media_type="text/plain",
        examples={
            "example": {
                "summary": "Example VPN list",
                "value": (
                    "# Main servers\n"
                    "vless://uuid-1@example.com:443?security=reality#Amsterdam-1\n"
                    "vless://uuid-2@example.com:443?security=reality#Amsterdam-2\n"
                    "\n"
                    "# Backup\n"
                    "trojan://password@example.com:443?security=tls#Warsaw-1"
                ),
            },
        },
    ),
    admin: str = Depends(get_current_admin),
    vpn_source_repo: VpnSourceRepository = Depends(get_vpn_source_repo),
    tag_repo: VpnSourceTagRepository = Depends(get_tag_repo),
    validator: VpnUriValidator = Depends(get_validator),
    import_repo: VpnSourceImportRepository = Depends(get_import_repo),
    parser: PlainTextUriParser = Depends(get_parser),
    tags: Annotated[str | None, Query(description="Comma-separated tags")] = None,
    import_group: Annotated[str, Query()] = "default",
    mode: Annotated[Literal["replace", "upsert", "append"], Query()] = "replace",
    dry_run: Annotated[bool, Query()] = True,
    deactivate_missing: Annotated[bool, Query()] = True,
    ignore_invalid: Annotated[bool, Query()] = False,
    name_strategy: Annotated[Literal["fragment", "host", "line_number"], Query()] = "fragment",
):
    tag_list = tags.split(",") if tags else []

    use_case = SyncVpnSourcesTextUseCase(
        vpn_source_repo=vpn_source_repo,
        tag_repo=tag_repo,
        validator=validator,
        import_repo=import_repo,
        parser=parser,
    )

    try:
        result = await use_case.execute(
            text=text,
            mode=mode,
            import_group=import_group,
            tags=tag_list,
            dry_run=dry_run,
            deactivate_missing=deactivate_missing,
            ignore_invalid=ignore_invalid,
            name_strategy=name_strategy,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return SyncTextResponse(
        dry_run=result.dry_run,
        mode=result.mode,
        import_group=result.import_group,
        tags=result.tags,
        parsed_count=result.parsed_count,
        valid_count=result.valid_count,
        invalid_count=result.invalid_count,
        to_create_count=result.to_create_count,
        to_update_count=result.to_update_count,
        to_deactivate_count=result.to_deactivate_count,
        created=[
            SyncTextPreviewItem(
                id=item.id,
                name=item.name,
                uri=item.uri,
                action="create",
                tags=[
                    TagResponse(
                        id=t.id,
                        name=t.name,
                        slug=t.slug,
                        created_at=t.created_at,
                    )
                    for t in item.tags
                ],
            )
            for item in result.created
        ],
        updated=[
            SyncTextPreviewItem(
                id=item.id,
                name=item.name,
                uri=item.uri,
                action="update",
                tags=[
                    TagResponse(
                        id=t.id,
                        name=t.name,
                        slug=t.slug,
                        created_at=t.created_at,
                    )
                    for t in item.tags
                ],
            )
            for item in result.updated
        ],
        deactivated=[
            SyncTextPreviewItem(
                id=item.id,
                name=item.name,
                uri=item.uri,
                action="deactivate",
                tags=[
                    TagResponse(
                        id=t.id,
                        name=t.name,
                        slug=t.slug,
                        created_at=t.created_at,
                    )
                    for t in item.tags
                ],
            )
            for item in result.deactivated
        ],
        failed=[
            SyncTextFailureResponse(
                line=f.line,
                raw=f.raw,
                error=f.error,
            )
            for f in result.failed
        ],
    )
