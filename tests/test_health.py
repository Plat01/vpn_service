import base64

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_check_returns_ok(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "database" in data


class TestAdminEndpoint:
    def test_admin_test_requires_authentication(self, client):
        response = client.get("/api/v1/admin/test")
        assert response.status_code == 401

    def test_admin_test_with_invalid_credentials(self, client):
        credentials = base64.b64encode(b"wrong:credentials").decode("utf-8")
        response = client.get(
            "/api/v1/admin/test", headers={"Authorization": f"Basic {credentials}"}
        )
        assert response.status_code == 401

    def test_admin_test_with_valid_credentials(self, client, admin_credentials):
        credentials = base64.b64encode(
            f"{admin_credentials['username']}:{admin_credentials['password']}".encode()
        ).decode("utf-8")
        response = client.get(
            "/api/v1/admin/test", headers={"Authorization": f"Basic {credentials}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Admin access confirmed"
        assert "timestamp" in data
