from fastapi import APIRouter, Depends, HTTPException, status

from src.application.subscription_issuance.dto import CreateEncryptedSubscriptionDTO
from src.application.subscription_issuance.use_cases import (
    CreateEncryptedSubscriptionUseCase,
)
from src.domain.subscription_issuance.value_objects import (
    ExpireNotification,
    InfoBlock,
    SubscriptionBehavior,
    SubscriptionMetadata,
    TrafficInfo,
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
from src.infrastructure.subscription.happ_metadata_generator import (
    HappMetadataGenerator,
)
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


def get_metadata_generator() -> HappMetadataGenerator:
    return HappMetadataGenerator()


def get_config_generator(
    metadata_generator: HappMetadataGenerator = Depends(get_metadata_generator),
) -> TextListConfigGenerator:
    return TextListConfigGenerator(metadata_generator)


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

    metadata = None
    if request.metadata:
        traffic_info = None
        if request.metadata.traffic_info:
            traffic_info = TrafficInfo(
                upload=request.metadata.traffic_info.upload,
                download=request.metadata.traffic_info.download,
                total=request.metadata.traffic_info.total,
            )

        info_block = None
        if request.metadata.info_block:
            info_block = InfoBlock(
                color=request.metadata.info_block.color,
                text=request.metadata.info_block.text,
                button_text=request.metadata.info_block.button_text,
                button_link=request.metadata.info_block.button_link,
            )

        expire_notification = None
        if request.metadata.expire_notification:
            expire_notification = ExpireNotification(
                enabled=request.metadata.expire_notification.enabled,
                button_link=request.metadata.expire_notification.button_link,
            )

        metadata = SubscriptionMetadata(
            profile_title=request.metadata.profile_title,
            profile_update_interval=request.metadata.profile_update_interval,
            support_url=request.metadata.support_url,
            profile_web_page_url=request.metadata.profile_web_page_url,
            announce=request.metadata.announce,
            traffic_info=traffic_info,
            info_block=info_block,
            expire_notification=expire_notification,
        )

    behavior = None
    if request.behavior:
        behavior = SubscriptionBehavior(
            autoconnect=request.behavior.autoconnect,
            autoconnect_type=request.behavior.autoconnect_type,
            ping_on_open=request.behavior.ping_on_open,
            fallback_url=request.behavior.fallback_url,
        )

    dto = CreateEncryptedSubscriptionDTO(
        tags=request.tags,
        ttl_hours=request.ttl_hours,
        created_by=admin,
        max_devices=request.max_devices,
        metadata=metadata,
        behavior=behavior,
        provider_id=request.provider_id,
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
