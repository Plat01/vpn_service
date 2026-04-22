import logging
from abc import ABC, abstractmethod

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class HappCryptoAdapterPort(ABC):
    @abstractmethod
    async def encrypt_link(self, subscription_url: str) -> str:
        pass


class HappCryptoAdapter(HappCryptoAdapterPort):
    def __init__(self, api_url: str | None = None):
        self._api_url = api_url or settings.happ_crypto_api_url

    async def encrypt_link(self, subscription_url: str) -> str:
        payload = {"url": subscription_url}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._api_url,
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()

                data = response.json()
                encrypted_link = data.get("url")

                if not encrypted_link:
                    raise ValueError("HAPP API returned empty encrypted link")

                logger.info(
                    "HAPP encryption successful: api_url=%s, link_length=%d",
                    self._api_url,
                    len(encrypted_link),
                )

                return encrypted_link

        except httpx.HTTPStatusError as e:
            logger.error(
                "HAPP API HTTP error: status=%d, url=%s",
                e.response.status_code,
                self._api_url,
            )
            raise ValueError(
                f"HAPP encryption failed: HTTP {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            logger.error(
                "HAPP API request error: url=%s, error=%s", self._api_url, str(e)
            )
            raise ValueError(f"HAPP encryption failed: request error") from e
