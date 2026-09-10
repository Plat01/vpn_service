import base64
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.config import settings


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    credentials = base64.b64encode(
        f"{settings.admin_username}:{settings.admin_password}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "text/plain",
    }


class TestSyncTextEndpoint:
    @pytest.mark.asyncio
    async def test_sync_text_unauthorized(self, client: AsyncClient):
        response = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content="vless://12345678-1234-1234-1234-123456789012@example.com:443",
            headers={"Content-Type": "text/plain"},
            params={"dry_run": True},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sync_text_dry_run_no_changes(
        self, client: AsyncClient, auth_headers
    ):
        text = "# Comment\nvless://12345678-1234-1234-1234-123456789abc@example.com:443?security=reality#Server1"
        response = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text,
            headers=auth_headers,
            params={
                "dry_run": True,
                "import_group": "test-group",
                "mode": "replace",
                "name_strategy": "fragment",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True
        assert data["parsed_count"] == 1
        assert data["valid_count"] == 1
        assert data["invalid_count"] == 0
        assert data["to_create_count"] == 1

    @pytest.mark.asyncio
    async def test_sync_text_invalid_uri_returns_failed(
        self, client: AsyncClient, auth_headers
    ):
        text = "invalid-uri-format\nvless://12345678-1234-1234-1234-123456789abc@example.com:443#Valid"
        response = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text,
            headers=auth_headers,
            params={
                "dry_run": True,
                "ignore_invalid": True,
                "name_strategy": "fragment",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["parsed_count"] == 2
        assert data["valid_count"] == 1
        assert data["invalid_count"] == 1
        assert len(data["failed"]) == 1
        assert data["failed"][0]["line"] == 1

    @pytest.mark.asyncio
    async def test_sync_text_comments_and_empty_lines_ignored(
        self, client: AsyncClient, auth_headers
    ):
        text = """
# This is a comment

vless://12345678-1234-1234-1234-123456789abc@example.com:443#Server1

# Another comment
vless://abcd1234-1234-1234-1234-123456789abc@example.com:443#Server2
"""
        response = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text,
            headers=auth_headers,
            params={
                "dry_run": True,
                "name_strategy": "fragment",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["parsed_count"] == 2

    @pytest.mark.asyncio
    async def test_sync_text_exceeds_max_lines(self, client: AsyncClient, auth_headers):
        lines = ["vless://12345678-1234-1234-1234-123456789abc@example.com:443#Server" + str(i) for i in range(501)]
        text = "\n".join(lines)
        response = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text,
            headers=auth_headers,
            params={"dry_run": True},
        )
        assert response.status_code == 400
        assert "Too many lines" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_sync_text_replace_mode_creates_new(
        self, client: AsyncClient, auth_headers
    ):
        text = "vless://12345678-1234-1234-1234-123456789abc@example.com:443#NewServer"
        response = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text,
            headers=auth_headers,
            params={
                "dry_run": False,
                "import_group": "replace-test",
                "mode": "replace",
                "deactivate_missing": True,
                "name_strategy": "fragment",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is False
        assert len(data["created"]) == 1
        assert data["created"][0]["name"] == "NewServer"

    @pytest.mark.asyncio
    async def test_sync_text_append_mode_only_adds(
        self, client: AsyncClient, auth_headers
    ):
        text1 = "vless://11111111-1111-1111-1111-111111111111@example.com:443#First"
        response1 = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text1,
            headers=auth_headers,
            params={
                "dry_run": False,
                "import_group": "append-test",
                "mode": "append",
                "name_strategy": "fragment",
            },
        )
        assert response1.status_code == 200
        assert len(response1.json()["created"]) == 1

        text2 = "vless://22222222-2222-2222-2222-222222222222@example.com:443#Second\nvless://11111111-1111-1111-1111-111111111111@example.com:443#First"
        response2 = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text2,
            headers=auth_headers,
            params={
                "dry_run": False,
                "import_group": "append-test",
                "mode": "append",
                "name_strategy": "fragment",
            },
        )
        assert response2.status_code == 200
        data = response2.json()
        assert len(data["created"]) == 1
        assert len(data["updated"]) == 0

    @pytest.mark.asyncio
    async def test_sync_text_tags_assigned(self, client: AsyncClient, auth_headers):
        tag_headers = {
            "Authorization": auth_headers["Authorization"],
        }
        tag_response = await client.post(
            "/api/v1/admin/vpn-source-tags",
            json={"name": "SyncTest", "slug": "sync-test"},
            headers=tag_headers,
        )
        assert tag_response.status_code == 201

        text = "vless://aaaa1111-1111-1111-1111-111111111111@example.com:443#Tagged"
        response = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text,
            headers=auth_headers,
            params={
                "dry_run": False,
                "import_group": "tag-test",
                "tags": "sync-test",
                "mode": "replace",
                "name_strategy": "fragment",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["created"]) == 1
        created_item = data["created"][0]
        assert len(created_item["tags"]) == 1
        assert created_item["tags"][0]["slug"] == "sync-test"

    @pytest.mark.asyncio
    async def test_sync_text_name_strategy_host(
        self, client: AsyncClient, auth_headers
    ):
        text = "vless://12345678-1234-1234-1234-123456789abc@myserver.example.com:443?security=reality"
        response = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text,
            headers=auth_headers,
            params={
                "dry_run": True,
                "name_strategy": "host",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["to_create_count"] == 1

    @pytest.mark.asyncio
    async def test_sync_text_invalid_without_ignore_invalid(
        self, client: AsyncClient, auth_headers
    ):
        text = "invalid-uri\nvless://12345678-1234-1234-1234-123456789abc@example.com:443#Valid"
        response = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text,
            headers=auth_headers,
            params={
                "dry_run": True,
                "ignore_invalid": False,
                "name_strategy": "fragment",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["invalid_count"] == 1
        assert len(data["failed"]) == 1

    @pytest.mark.asyncio
    async def test_sync_text_nonexistent_tag(
        self, client: AsyncClient, auth_headers
    ):
        text = "vless://12345678-1234-1234-1234-123456789abc@example.com:443#Test"
        response = await client.put(
            "/api/v1/admin/vpn-sources/sync-text",
            content=text,
            headers=auth_headers,
            params={
                "dry_run": True,
                "tags": "nonexistent-tag",
                "name_strategy": "fragment",
            },
        )
        assert response.status_code == 400
        assert "nonexistent-tag" in response.json()["detail"]