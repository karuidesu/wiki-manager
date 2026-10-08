import logging
from typing import Any, Dict

from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from app.core.exceptions.api_exception import ApiErrorsCode, ApiException
from app.models.security.auth_user import AuthenticatedUser
from app.security.api_roles import ApiRoles
from app.storage.rds.datastore.interfaces.user import IUser

LOGGER = logging.getLogger(__name__)


class UserService:
    def __init__(self, user_store: IUser):
        self._user_store = user_store

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        user = await self._user_store.get_user(user_id)
        if not user:
            raise ApiException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ApiErrorsCode.USER_NOT_FOUND,
                message="User not found",
            )
        return {
            "id": user.get("id"),
            "username": user.get("username"),
            "firstName": user.get("firstName"),
            "lastName": user.get("lastName"),
            "email": user.get("email"),
        }

    async def get_users(
        self, page: int, max_results: int, auth_user: AuthenticatedUser
    ) -> Dict[str, Any]:
        user_roles = getattr(auth_user, "roles", [])
        is_reviewer = any(
            role in user_roles for role in [ApiRoles.MANAGER, ApiRoles.DIRECTOR]
        )
        if not is_reviewer:
            raise ApiException(
                status_code=HTTP_403_FORBIDDEN,
                error_code=ApiErrorsCode.FORBIDDEN,
                message="Access denied. Reviewer role required.",
            )

        users = await self._user_store.get_users(
            page_index=page, max_result=max_results
        )

        items = [
            {
                "id": u.get("id"),
                "username": u.get("username"),
                "firstName": u.get("firstName"),
                "lastName": u.get("lastName"),
                "email": u.get("email"),
            }
            for u in users
        ]

        return {
            "items": items,
            "page": page,
            "max_results": max_results,
        }
