from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from src.infrastructure.happ.crypto_adapter import HappCryptoAdapter


class TestHappCryptoAdapter:
    @pytest.mark.asyncio
    async def test_encrypt_link_success(self):
        adapter = HappCryptoAdapter(api_url="https://test-api.example.com")

        mock_response = MagicMock()
        mock_response.json.return_value = {"url": "happ://crypt5/encrypted123"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await adapter.encrypt_link("https://subscription.example.com/abc")

            assert result == "happ://crypt5/encrypted123"
            mock_client.post.assert_called_once_with(
                "https://test-api.example.com",
                json={"url": "https://subscription.example.com/abc"},
                timeout=30.0,
            )

    @pytest.mark.asyncio
    async def test_encrypt_link_empty_response_raises(self):
        adapter = HappCryptoAdapter(api_url="https://test-api.example.com")

        mock_response = MagicMock()
        mock_response.json.return_value = {"url": None}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="empty encrypted link"):
                await adapter.encrypt_link("https://subscription.example.com/abc")

    @pytest.mark.asyncio
    async def test_encrypt_link_missing_url_key_raises(self):
        adapter = HappCryptoAdapter(api_url="https://test-api.example.com")

        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="empty encrypted link"):
                await adapter.encrypt_link("https://subscription.example.com/abc")
