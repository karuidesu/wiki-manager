from unittest.mock import AsyncMock

import pytest
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from app.core.exceptions.api_exception import ApiException
from app.models.security.auth_user import AuthenticatedUser
from app.security.api_roles import ApiRoles
from app.services.user.user_service import UserService
from app.storage.rds.datastore.interfaces.user import IUser


class MockUserStore(IUser):
    def __init__(self):
        self.get_user_mock = AsyncMock()
        self.get_users_mock = AsyncMock()

    async def get_user(self, user_id: str):
        return await self.get_user_mock(user_id)

    async def get_users(self, page_index: int, max_result: int):
        return await self.get_users_mock(page_index=page_index, max_result=max_result)


@pytest.fixture
def user_store():
    return MockUserStore()


@pytest.fixture
def user_service(user_store):
    return UserService(user_store)


@pytest.mark.asyncio
async def test_get_user_success(user_service, user_store):
    user_store.get_user_mock.return_value = {
        "id": "123",
        "username": "testuser",
        "firstName": "Test",
        "lastName": "User",
        "email": "test@example.com",
    }

    result = await user_service.get_user("123")
    assert result["id"] == "123"
    assert result["username"] == "testuser"
    user_store.get_user_mock.assert_called_once_with("123")


@pytest.mark.asyncio
async def test_get_user_not_found(user_service, user_store):
    user_store.get_user_mock.return_value = None

    with pytest.raises(ApiException) as exc_info:
        await user_service.get_user("999")

    assert exc_info.value.status_code == HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_users_forbidden(user_service):
    auth_user = AuthenticatedUser(
        user_id="user1", roles=[ApiRoles.EMPLOYEE], username="user1"
    )

    with pytest.raises(ApiException) as exc_info:
        await user_service.get_users(page=1, max_results=10, auth_user=auth_user)

    assert exc_info.value.status_code == HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_users_success(user_service, user_store):
    auth_user = AuthenticatedUser(
        user_id="admin1", roles=[ApiRoles.MANAGER], username="admin1"
    )
    user_store.get_users_mock.return_value = [
        {"id": "1", "username": "u1"},
        {"id": "2", "username": "u2"},
    ]

    result = await user_service.get_users(page=2, max_results=20, auth_user=auth_user)

    assert result["page"] == 2
    assert result["max_results"] == 20
    assert len(result["items"]) == 2
    user_store.get_users_mock.assert_called_once_with(page_index=2, max_result=20)
