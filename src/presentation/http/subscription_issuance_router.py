from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.subscription_issuance.dto import CreateEncryptedSubscriptionDTO
from src.application.subscription_issuance.use_cases import (
    CreateEncryptedSubscriptionUseCase,
)
from src.domain.vpn_catalog.repositories import VpnSourceRepository
from src.domain.subscription_issuance.repositories import (
    SubscriptionIssueItemRepository,
    SubscriptionIssueRepository,
)
from src.infrastructure.db.repositories import (
    SqlAlchemySubscriptionIssueItemRepository,
    SqlAlchemySubscriptionIssueRepository,
    SqlAlchemyVpnSourceRepository,
)
from src.infrastructure.happ.crypto_adapter import HappCryptoAdapter
from src.infrastructure.subscription.url_generator import TextListConfigGenerator
from src.infrastructure.time.provider import SystemTimeProvider
from src.presentation.http.dependencies import get_current_admin
from src.presentation.http.dto import (
    CreateEncryptedSubscriptionRequest,
    EncryptedSubscriptionResponse,
)
from src.infrastructure.db.database import get_session

router = APIRouter()


def get_vpn_source_repo(
    session: get_session = Depends(get_session),
) -> VpnSourceRepository:
    return SqlAlchemyVpnSourceRepository(session)


def get_subscription_repo(
    session: get_session = Depends(get_session),
) -> SubscriptionIssueRepository:
    return SqlAlchemySubscriptionIssueRepository(session)


def get_item_repo(
    session: get_session = Depends(get_session),
) -> SubscriptionIssueItemRepository:
    return SqlAlchemySubscriptionIssueItemRepository(session)


def get_crypto_adapter() -> HappCryptoAdapter:
    return HappCryptoAdapter()


def get_config_generator() -> TextListConfigGenerator:
    return TextListConfigGenerator()


def get_time_provider() -> SystemTimeProvider:
    return SystemTimeProvider()


@router.post(
    "/subscriptions/encrypted",
    response_model=EncryptedSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_encrypted_subscription(
    request: CreateEncryptedSubscriptionRequest,
    admin: str = Depends(get_current_admin),
    vpn_source_repo: VpnSourceRepository = Depends(get_vpn_source_repo),
    subscription_repo: SubscriptionIssueRepository = Depends(get_subscription_repo),
    item_repo: SubscriptionIssueItemRepository = Depends(get_item_repo),
    crypto_adapter: HappCryptoAdapter = Depends(get_crypto_adapter),
    config_generator: TextListConfigGenerator = Depends(get_config_generator),
    time_provider: SystemTimeProvider = Depends(get_time_provider),
):
    use_case = CreateEncryptedSubscriptionUseCase(
        vpn_source_repo=vpn_source_repo,
        subscription_repo=subscription_repo,
        item_repo=item_repo,
        crypto_adapter=crypto_adapter,
        config_generator=config_generator,
        time_provider=time_provider,
    )

    dto = CreateEncryptedSubscriptionDTO(
        tags=request.tags,
        ttl_hours=request.ttl_hours,
        created_by=admin,
        max_devices=request.max_devices,
    )

    try:
        result = await use_case.execute(dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return EncryptedSubscriptionResponse(
        id=result.id,
        public_id=result.public_id,
        encrypted_link=result.encrypted_link,
        expires_at=result.expires_at,
        vpn_sources_count=result.vpn_sources_count,
        tags_used=result.tags_used,
        created_at=result.created_at,
    )
