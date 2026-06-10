from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.domain.subscription_issuance.entities import (
    SubscriptionIssue,
    SubscriptionIssueItem,
)
from src.domain.subscription_issuance.value_objects import (
    SubscriptionIssueId,
    SubscriptionIssueItemId,
    SubscriptionMetadata,
    SubscriptionStatus,
    TrafficInfo,
)
from src.domain.vpn_catalog.value_objects import VpnSourceId


class TestSubscriptionIssueEntity:
    def test_create_subscription_issue_success(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=5,
            created_at=now,
            created_by="admin",
            tags_used=["eu", "premium"],
        )

        assert subscription.status == SubscriptionStatus.active
        assert subscription.max_devices == 5
        assert subscription.tags_used == ["eu", "premium"]
        assert subscription.encrypted_link is None

    def test_create_subscription_issue_empty_public_id_raises(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        with pytest.raises(ValueError, match="public_id cannot be empty"):
            SubscriptionIssue(
                id=SubscriptionIssueId(value=uuid4()),
                public_id="",
                status=SubscriptionStatus.active,
                expires_at=expires_at,
                max_devices=None,
                created_at=now,
                created_by="admin",
                tags_used=["eu"],
            )

    def test_create_subscription_issue_empty_created_by_raises(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        with pytest.raises(ValueError, match="created_by cannot be empty"):
            SubscriptionIssue(
                id=SubscriptionIssueId(value=uuid4()),
                public_id=str(uuid4()),
                status=SubscriptionStatus.active,
                expires_at=expires_at,
                max_devices=None,
                created_at=now,
                created_by="",
                tags_used=["eu"],
            )

    def test_create_subscription_issue_expires_at_before_created_at_raises(self):
        now = datetime.now(timezone.utc)
        expires_at = now - timedelta(hours=1)

        with pytest.raises(ValueError, match="expires_at must be after created_at"):
            SubscriptionIssue(
                id=SubscriptionIssueId(value=uuid4()),
                public_id=str(uuid4()),
                status=SubscriptionStatus.active,
                expires_at=expires_at,
                max_devices=None,
                created_at=now,
                created_by="admin",
                tags_used=["eu"],
            )

    def test_create_subscription_issue_negative_max_devices_raises(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        with pytest.raises(ValueError, match="max_devices must be at least 1"):
            SubscriptionIssue(
                id=SubscriptionIssueId(value=uuid4()),
                public_id=str(uuid4()),
                status=SubscriptionStatus.active,
                expires_at=expires_at,
                max_devices=0,
                created_at=now,
                created_by="admin",
                tags_used=["eu"],
            )

    def test_is_expired_returns_true_when_expired(self):
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(hours=1)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=past_time,
            max_devices=None,
            created_at=now - timedelta(hours=25),
            created_by="admin",
            tags_used=["eu"],
        )

        assert subscription.is_expired(now) is True

    def test_is_expired_returns_false_when_not_expired(self):
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(hours=24)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=future_time,
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
        )

        assert subscription.is_expired(now) is False

    def test_mark_expired_changes_status(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription.mark_expired()

        assert subscription.status == SubscriptionStatus.expired

    def test_revoke_changes_status_and_sets_revoked_at(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)
        revoked_at = now + timedelta(hours=1)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription.revoke(revoked_at)

        assert subscription.status == SubscriptionStatus.revoked
        assert subscription.revoked_at == revoked_at

    def test_is_active_returns_true_for_active_subscription(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
        )

        assert subscription.is_active(now) is True

    def test_is_active_returns_false_for_expired_subscription(self):
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(hours=1)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=past_time,
            max_devices=None,
            created_at=now - timedelta(hours=25),
            created_by="admin",
            tags_used=["eu"],
        )

        assert subscription.is_active(now) is False

    def test_is_active_returns_false_for_revoked_subscription(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.revoked,
            expires_at=expires_at,
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
            revoked_at=now,
        )

        assert subscription.is_active(now) is False

    def test_set_encrypted_link(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription.set_encrypted_link("happ://crypt5/abc123")

        assert subscription.encrypted_link == "happ://crypt5/abc123"

    def test_extend_ttl_active_subscription(self):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=48)
        expires_at = now + timedelta(hours=10)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=created_at,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription.extend_ttl(5, now)

        expected = now + timedelta(hours=15)
        assert subscription.expires_at == expected
        assert subscription.status == SubscriptionStatus.active

    def test_extend_ttl_expired_subscription(self):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=48)
        expires_at = now - timedelta(hours=5)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.expired,
            expires_at=expires_at,
            max_devices=None,
            created_at=created_at,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription.extend_ttl(24, now)

        expected = now + timedelta(hours=24)
        assert subscription.expires_at == expected
        assert subscription.status == SubscriptionStatus.active

    def test_extend_ttl_reactivates_expired(self):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=48)
        expires_at = now - timedelta(hours=5)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.expired,
            expires_at=expires_at,
            max_devices=None,
            created_at=created_at,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription.extend_ttl(24, now)

        assert subscription.status == SubscriptionStatus.active

    def test_extend_ttl_invalid_hours(self):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=48)
        expires_at = now + timedelta(hours=10)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=created_at,
            created_by="admin",
            tags_used=["eu"],
        )

        with pytest.raises(ValueError, match="additional_hours must be at least 1"):
            subscription.extend_ttl(0, now)

    def test_set_max_devices_valid(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription.set_max_devices(5)

        assert subscription.max_devices == 5

    def test_set_max_devices_none(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=3,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
        )

        subscription.set_max_devices(None)

        assert subscription.max_devices is None

    def test_set_max_devices_invalid(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
        )

        with pytest.raises(ValueError, match="max_devices must be at least 1"):
            subscription.set_max_devices(0)

    def test_update_traffic_info_new(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
        )

        assert subscription.metadata is None

        traffic = TrafficInfo(upload=100, download=200, total=300)
        subscription.update_traffic_info(traffic)

        assert subscription.metadata is not None
        assert subscription.metadata.traffic_info == traffic

    def test_update_traffic_info_existing(self):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)
        existing_traffic = TrafficInfo(upload=10, download=20, total=30)

        subscription = SubscriptionIssue(
            id=SubscriptionIssueId(value=uuid4()),
            public_id=str(uuid4()),
            status=SubscriptionStatus.active,
            expires_at=expires_at,
            max_devices=None,
            created_at=now,
            created_by="admin",
            tags_used=["eu"],
            metadata=SubscriptionMetadata(
                profile_title="Test Profile",
                traffic_info=existing_traffic,
            ),
        )

        new_traffic = TrafficInfo(upload=100, download=200, total=300)
        subscription.update_traffic_info(new_traffic)

        assert subscription.metadata.traffic_info == new_traffic
        assert subscription.metadata.profile_title == "Test Profile"


class TestSubscriptionIssueItemEntity:
    def test_create_subscription_issue_item_success(self):
        now = datetime.now(timezone.utc)

        item = SubscriptionIssueItem(
            id=SubscriptionIssueItemId(value=uuid4()),
            subscription_issue_id=SubscriptionIssueId(value=uuid4()),
            vpn_source_id=VpnSourceId(value=uuid4()),
            position=0,
            created_at=now,
        )

        assert item.position == 0

    def test_create_subscription_issue_item_negative_position_raises(self):
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="position must be non-negative"):
            SubscriptionIssueItem(
                id=SubscriptionIssueItemId(value=uuid4()),
                subscription_issue_id=SubscriptionIssueId(value=uuid4()),
                vpn_source_id=VpnSourceId(value=uuid4()),
                position=-1,
                created_at=now,
            )
