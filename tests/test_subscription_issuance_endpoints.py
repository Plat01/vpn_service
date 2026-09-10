import base64
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    credentials = base64.b64encode("admin:change_me_in_production".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


class TestSubscriptionIssuanceEndpoints:
    @pytest.mark.asyncio
    async def test_create_subscription_unauthorized(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/admin/subscriptions/encrypted",
            json={"tags": ["eu"], "ttl_hours": 24},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_subscription_empty_tags(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post(
            "/api/v1/admin/subscriptions/encrypted",
            json={"tags": [], "ttl_hours": 24},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_subscription_invalid_ttl(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post(
            "/api/v1/admin/subscriptions/encrypted",
            json={"tags": ["eu"], "ttl_hours": 0},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_subscription_ttl_too_large(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post(
            "/api/v1/admin/subscriptions/encrypted",
            json={"tags": ["eu"], "ttl_hours": 10000},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_subscription_invalid_max_devices(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post(
            "/api/v1/admin/subscriptions/encrypted",
            json={"tags": ["eu"], "ttl_hours": 24, "max_devices": 0},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_subscription_not_found(self, client: AsyncClient):
        fake_public_id = str(uuid4())
        response = await client.get(f"/api/v1/subscriptions/{fake_public_id}")
        assert response.status_code == 404


class TestSubscriptionIssuanceWithMocks:
    @pytest.mark.asyncio
    async def test_create_subscription_no_vpn_sources_found(
        self, client: AsyncClient, auth_headers
    ):
        with patch(
            "src.infrastructure.db.repositories.vpn_source.SqlAlchemyVpnSourceRepository.get_all",
            new_callable=AsyncMock,
        ) as mock_get_all:
            mock_get_all.return_value = []

            response = await client.post(
                "/api/v1/admin/subscriptions/encrypted",
                json={"tags": ["nonexistent"], "ttl_hours": 24},
                headers=auth_headers,
            )

            assert response.status_code == 400
            assert "No active VPN sources found" in response.json()["detail"]
