import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.main import app
from src.infrastructure.db.models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://vpn_user:vpn_pass@localhost:5432/vpn_test_db"


@pytest.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest.fixture
async def client(async_client):
    return async_client


@pytest.fixture
def auth_headers(admin_credentials):
    import base64

    credentials = base64.b64encode(
        f"{admin_credentials['username']}:{admin_credentials['password']}".encode()
    ).decode()
    return {"Authorization": f"Basic {credentials}"}


class TestVpnSourcesEndpoints:
    @pytest.mark.asyncio
    async def test_list_vpn_sources_empty(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/admin/vpn-sources", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_create_tag(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/admin/vpn-source-tags",
            json={"name": "Europe", "slug": "eu"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Europe"
        assert data["slug"] == "eu"

    @pytest.mark.asyncio
    async def test_create_vpn_source_invalid_uri(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post(
            "/api/v1/admin/vpn-sources",
            json={
                "name": "Test Server",
                "uri": "invalid-uri",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "scheme" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_vpn_source_valid_vless(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post(
            "/api/v1/admin/vpn-sources",
            json={
                "name": "Test VLESS Server",
                "uri": "vless://12345678-1234-1234-1234-123456789abc@example.com:443",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test VLESS Server"
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_vpn_sources_returns_uri(
        self, client: AsyncClient, auth_headers
    ):
        create_response = await client.post(
            "/api/v1/admin/vpn-sources",
            json={
                "name": "Test Server",
                "uri": "vless://12345678-1234-1234-1234-123456789abc@example.com:443",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201

        list_response = await client.get(
            "/api/v1/admin/vpn-sources", headers=auth_headers
        )
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data["items"]) > 0
        item = data["items"][0]
        assert "uri" in item
        assert item["uri"].startswith("vless://")

    @pytest.mark.asyncio
    async def test_get_vpn_source_by_id_returns_uri(
        self, client: AsyncClient, auth_headers
    ):
        create_response = await client.post(
            "/api/v1/admin/vpn-sources",
            json={
                "name": "Test Server",
                "uri": "vless://12345678-1234-1234-1234-123456789abc@example.com:443",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        source_id = create_response.json()["id"]

        detail_response = await client.get(
            f"/api/v1/admin/vpn-sources/{source_id}",
            headers=auth_headers,
        )
        assert detail_response.status_code == 200
        data = detail_response.json()
        assert "uri" in data
        assert data["uri"].startswith("vless://")

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/vpn-sources")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_vpn_source_with_nonexistent_tag(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post(
            "/api/v1/admin/vpn-sources",
            json={
                "name": "Test Server",
                "uri": "vless://12345678-1234-1234-1234-123456789abc@example.com:443",
                "is_active": True,
                "tags": ["nonexistent-tag"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "nonexistent-tag" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_vpn_source_with_valid_tag(
        self, client: AsyncClient, auth_headers
    ):
        tag_response = await client.post(
            "/api/v1/admin/vpn-source-tags",
            json={"name": "Europe", "slug": "eu"},
            headers=auth_headers,
        )
        assert tag_response.status_code == 201

        response = await client.post(
            "/api/v1/admin/vpn-sources",
            json={
                "name": "Test Server",
                "uri": "vless://12345678-1234-1234-1234-123456789abc@example.com:443",
                "is_active": True,
                "tags": ["eu"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["tags"]) == 1
        assert data["tags"][0]["slug"] == "eu"

    @pytest.mark.asyncio
    async def test_update_vpn_source_with_nonexistent_tag(
        self, client: AsyncClient, auth_headers
    ):
        create_response = await client.post(
            "/api/v1/admin/vpn-sources",
            json={
                "name": "Test Server",
                "uri": "vless://12345678-1234-1234-1234-123456789abc@example.com:443",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        source_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/admin/vpn-sources/{source_id}",
            json={"tags": ["nonexistent-tag"]},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "nonexistent-tag" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_batch_create_with_nonexistent_tag(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post(
            "/api/v1/admin/vpn-sources/batch",
            json={
                "items": [
                    {
                        "name": "Server 1",
                        "uri": "vless://12345678-1234-1234-1234-123456789abc@example.com:443",
                        "tags": ["nonexistent-tag"],
                    }
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "nonexistent-tag" in response.json()["detail"]
