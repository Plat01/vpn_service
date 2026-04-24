from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.subscription_issuance.entities import (
    SubscriptionIssue,
    SubscriptionIssueItem,
)
from src.domain.subscription_issuance.repositories import (
    SubscriptionIssueItemRepository,
    SubscriptionIssueRepository,
)
from src.domain.subscription_issuance.value_objects import (
    ExpireNotification,
    InfoBlock,
    SubscriptionBehavior,
    SubscriptionIssueId,
    SubscriptionIssueItemId,
    SubscriptionMetadata,
    SubscriptionStatus,
    TrafficInfo,
)
from src.domain.vpn_catalog.value_objects import VpnSourceId
from src.infrastructure.db.models import (
    SubscriptionIssueItemModel,
    SubscriptionIssueModel,
)


class SqlAlchemySubscriptionIssueRepository(SubscriptionIssueRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, subscription_issue_id: UUID) -> SubscriptionIssue | None:
        stmt = select(SubscriptionIssueModel).where(
            SubscriptionIssueModel.id == subscription_issue_id
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def get_by_public_id(self, public_id: str) -> SubscriptionIssue | None:
        stmt = select(SubscriptionIssueModel).where(
            SubscriptionIssueModel.public_id == public_id
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def create(self, subscription_issue: SubscriptionIssue) -> SubscriptionIssue:
        model = SubscriptionIssueModel(
            id=subscription_issue.id.value,
            public_id=subscription_issue.public_id,
            status=subscription_issue.status.value,
            expires_at=subscription_issue.expires_at,
            max_devices=subscription_issue.max_devices,
            created_at=subscription_issue.created_at,
            created_by=subscription_issue.created_by,
            tags_used=subscription_issue.tags_used,
            meta_data=self._map_metadata_to_db(subscription_issue.metadata),
            behavior=self._map_behavior_to_db(subscription_issue.behavior),
            provider_id=subscription_issue.provider_id,
            encrypted_link=subscription_issue.encrypted_link,
            revoked_at=subscription_issue.revoked_at,
        )

        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        return self._model_to_entity(model)

    async def update(self, subscription_issue: SubscriptionIssue) -> SubscriptionIssue:
        model = await self._session.get(
            SubscriptionIssueModel, subscription_issue.id.value
        )

        if not model:
            raise ValueError(
                f"SubscriptionIssue with id {subscription_issue.id.value} not found"
            )

        model.status = subscription_issue.status.value
        model.encrypted_link = subscription_issue.encrypted_link
        model.revoked_at = subscription_issue.revoked_at

        await self._session.flush()
        await self._session.refresh(model)

        return self._model_to_entity(model)

    def _model_to_entity(self, model: SubscriptionIssueModel) -> SubscriptionIssue:
        metadata = None
        if model.meta_data:
            metadata = self._map_metadata_from_db(model.meta_data)

        behavior = None
        if model.behavior:
            behavior = self._map_behavior_from_db(model.behavior)

        return SubscriptionIssue(
            id=SubscriptionIssueId(value=model.id),
            public_id=model.public_id,
            status=SubscriptionStatus(model.status),
            expires_at=model.expires_at,
            max_devices=model.max_devices,
            created_at=model.created_at,
            created_by=model.created_by,
            tags_used=model.tags_used or [],
            metadata=metadata,
            behavior=behavior,
            provider_id=model.provider_id,
            encrypted_link=model.encrypted_link,
            revoked_at=model.revoked_at,
        )

    def _map_metadata_from_db(self, data: dict) -> SubscriptionMetadata:
        traffic_info = None
        if "traffic_info" in data:
            traffic_info = TrafficInfo(**data["traffic_info"])

        info_block = None
        if "info_block" in data:
            info_block = InfoBlock(**data["info_block"])

        expire_notification = None
        if "expire_notification" in data:
            expire_notification = ExpireNotification(**data["expire_notification"])

        return SubscriptionMetadata(
            profile_title=data.get("profile_title"),
            profile_update_interval=data.get("profile_update_interval"),
            support_url=data.get("support_url"),
            profile_web_page_url=data.get("profile_web_page_url"),
            announce=data.get("announce"),
            traffic_info=traffic_info,
            info_block=info_block,
            expire_notification=expire_notification,
        )

    def _map_metadata_to_db(self, metadata: SubscriptionMetadata | None) -> dict | None:
        if not metadata:
            return None

        data = {}
        if metadata.profile_title:
            data["profile_title"] = metadata.profile_title
        if metadata.profile_update_interval:
            data["profile_update_interval"] = metadata.profile_update_interval
        if metadata.support_url:
            data["support_url"] = metadata.support_url
        if metadata.profile_web_page_url:
            data["profile_web_page_url"] = metadata.profile_web_page_url
        if metadata.announce:
            data["announce"] = metadata.announce
        if metadata.traffic_info:
            data["traffic_info"] = {
                "upload": metadata.traffic_info.upload,
                "download": metadata.traffic_info.download,
                "total": metadata.traffic_info.total,
            }
        if metadata.info_block:
            data["info_block"] = {
                "color": metadata.info_block.color,
                "text": metadata.info_block.text,
                "button_text": metadata.info_block.button_text,
                "button_link": metadata.info_block.button_link,
            }
        if metadata.expire_notification:
            data["expire_notification"] = {
                "enabled": metadata.expire_notification.enabled,
                "button_link": metadata.expire_notification.button_link,
            }
        return data

    def _map_behavior_from_db(self, data: dict) -> SubscriptionBehavior:
        return SubscriptionBehavior(
            autoconnect=data.get("autoconnect", False),
            autoconnect_type=data.get("autoconnect_type", "lastused"),
            ping_on_open=data.get("ping_on_open", False),
            fallback_url=data.get("fallback_url"),
        )

    def _map_behavior_to_db(self, behavior: SubscriptionBehavior | None) -> dict | None:
        if not behavior:
            return None

        data = {
            "autoconnect": behavior.autoconnect,
            "autoconnect_type": behavior.autoconnect_type,
            "ping_on_open": behavior.ping_on_open,
        }
        if behavior.fallback_url:
            data["fallback_url"] = behavior.fallback_url
        return data


class SqlAlchemySubscriptionIssueItemRepository(SubscriptionIssueItemRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_batch(
        self, items: list[SubscriptionIssueItem]
    ) -> list[SubscriptionIssueItem]:
        models = [
            SubscriptionIssueItemModel(
                id=item.id.value,
                subscription_issue_id=item.subscription_issue_id.value,
                vpn_source_id=item.vpn_source_id.value,
                position=item.position,
                created_at=item.created_at,
            )
            for item in items
        ]

        self._session.add_all(models)
        await self._session.flush()

        for model in models:
            await self._session.refresh(model)

        return [self._model_to_entity(model) for model in models]

    async def get_by_subscription_issue_id(
        self, subscription_issue_id: UUID
    ) -> list[SubscriptionIssueItem]:
        stmt = (
            select(SubscriptionIssueItemModel)
            .where(
                SubscriptionIssueItemModel.subscription_issue_id
                == subscription_issue_id
            )
            .order_by(SubscriptionIssueItemModel.position)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    def _model_to_entity(
        self, model: SubscriptionIssueItemModel
    ) -> SubscriptionIssueItem:
        return SubscriptionIssueItem(
            id=SubscriptionIssueItemId(value=model.id),
            subscription_issue_id=SubscriptionIssueId(
                value=model.subscription_issue_id
            ),
            vpn_source_id=VpnSourceId(value=model.vpn_source_id),
            position=model.position,
            created_at=model.created_at,
        )
