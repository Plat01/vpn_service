from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse

from src.application.subscription_issuance.use_cases import GetSubscriptionConfigUseCase
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
from src.infrastructure.subscription.happ_metadata_generator import (
    HappMetadataGenerator,
)
from src.infrastructure.subscription.url_generator import TextListConfigGenerator
from src.infrastructure.time.provider import SystemTimeProvider
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


def get_metadata_generator() -> HappMetadataGenerator:
    return HappMetadataGenerator()


def get_config_generator(
    metadata_generator: HappMetadataGenerator = Depends(get_metadata_generator),
) -> TextListConfigGenerator:
    return TextListConfigGenerator(metadata_generator)


def get_time_provider() -> SystemTimeProvider:
    return SystemTimeProvider()


@router.get("/subscriptions/{public_id}", response_class=PlainTextResponse)
async def get_subscription_config(
    public_id: str,
    vpn_source_repo: VpnSourceRepository = Depends(get_vpn_source_repo),
    subscription_repo: SubscriptionIssueRepository = Depends(get_subscription_repo),
    item_repo: SubscriptionIssueItemRepository = Depends(get_item_repo),
    config_generator: TextListConfigGenerator = Depends(get_config_generator),
    time_provider: SystemTimeProvider = Depends(get_time_provider),
):
    use_case = GetSubscriptionConfigUseCase(
        subscription_repo=subscription_repo,
        item_repo=item_repo,
        vpn_source_repo=vpn_source_repo,
        time_provider=time_provider,
        config_generator=config_generator,
    )

    try:
        is_active, content = await use_case.execute(public_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=content,
        )

    return PlainTextResponse(content=content, media_type="text/plain")
