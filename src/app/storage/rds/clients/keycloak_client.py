import logging
from typing import Any, Dict, List

import httpx

from app.configs.environment import EnvKey
from app.core.exceptions.api_exception import ApiException

LOGGER = logging.getLogger(__name__)


class KeycloakClient:
    def __init__(self, env: dict):
        self._env = env
        self._client = httpx.AsyncClient(timeout=5.0)
        self._admin_token = None

    async def _get_admin_token(self) -> str:
        keycloak_url = self._env.get(EnvKey.WIKI_KEYCLOAK_URL, "").rstrip("/")
        token_url = f"{keycloak_url}/protocol/openid-connect/token"

        client_id = self._env.get(EnvKey.WIKI_KEYCLOAK_CLIENT_ID, "")
        client_secret = self._env.get(EnvKey.WIKI_KEYCLOAK_CLIENT_SECRET, "")

        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }

        try:
            response = await self._client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            self._admin_token = token_data.get("access_token")
            return self._admin_token
        except Exception as exc:
            LOGGER.error(f"Failed to authenticate with Keycloak as admin. {exc}")
            raise ApiException(
                status_code=503, message="Identity provider unavailable", error_code=503
            )

    def _get_admin_api_url(self) -> str:
        url = self._env.get(EnvKey.WIKI_KEYCLOAK_URL, "").rstrip("/")
        if "/realms/" in url:
            return url.replace("/realms/", "/admin/realms/")
        return url

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if not self._admin_token:
            await self._get_admin_token()

        admin_url = self._get_admin_api_url()
        full_url = f"{admin_url}{path}"

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._admin_token}"

        try:
            response = await self._client.request(
                method, full_url, headers=headers, **kwargs
            )

            if response.status_code == 401:
                await self._get_admin_token()
                headers["Authorization"] = f"Bearer {self._admin_token}"
                response = await self._client.request(
                    method, full_url, headers=headers, **kwargs
                )

            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            LOGGER.error(
                f"Keycloak HTTP error: {exc.response.status_code} - {exc.response.text}"
            )
            if exc.response.status_code == 404:
                raise ApiException(
                    status_code=404,
                    message="Resource not found in Keycloak",
                    error_code=404,
                )
            raise ApiException(
                status_code=503, message="Identity provider error", error_code=503
            )
        except Exception as exc:
            LOGGER.error(f"Keycloak request failed: {exc}")
            raise ApiException(
                status_code=503, message="Identity provider unavailable", error_code=503
            )

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        response = await self._request("GET", f"/users/{user_id}")
        return response.json()

    async def get_users(
        self, first: int = 0, max_results: int = 20
    ) -> List[Dict[str, Any]]:
        params = {"first": first, "max": max_results}
        response = await self._request("GET", "/users", params=params)
        return response.json()
