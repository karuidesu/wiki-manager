from typing import Any, Dict, List, Optional

from app.core.exceptions.api_exception import ApiException
from app.storage.rds.clients.keycloak_client import KeycloakClient
from app.storage.rds.datastore.interfaces.user import IUser


class KeycloakDatastore(IUser):
    def __init__(self, keycloak_client: KeycloakClient):
        self._client = keycloak_client

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self._client.get_user(user_id)
        except ApiException as e:
            if e.status_code == 404:
                return None
            raise

    async def get_users(self, page_index: int, max_result: int) -> List[Dict[str, Any]]:
        first = (page_index - 1) * max_result
        return await self._client.get_users(first=first, max_results=max_result)
