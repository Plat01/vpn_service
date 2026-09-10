
import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.main import app

load_dotenv()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def admin_credentials():
    password = os.getenv("ADMIN_PASSWORD", "change_me_in_production")
    return {"username": "admin", "password": password}
