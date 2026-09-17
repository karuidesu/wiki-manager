from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.api.dto.wiki.wiki_dto import CreateCategoryDTO, UpdateCategoryDTO
from app.core.exceptions.api_exception import ApiException
from app.models.security.auth_user import AuthenticatedUser
from app.models.wiki.wiki_models import Category
from app.services.category.category_service import CategoryService
from app.storage.rds.datastore.interfaces.category import ICategory


@pytest.fixture
def mock_category_store():
    store = MagicMock(spec=ICategory)
    store.get_category_by_title = AsyncMock(return_value=None)
    return store


@pytest.fixture
def category_service(mock_category_store):
    return CategoryService(category_store=mock_category_store)


@pytest.fixture
def mock_auth_user():
    user = MagicMock(spec=AuthenticatedUser)
    user.user_id = "user-123"
    user.username = "john.doe"
    user.roles = ["wiki_manager"]
    return user


@pytest.mark.asyncio
async def test_create_category_success(
    category_service, mock_category_store, mock_auth_user
):
    dto = CreateCategoryDTO(
        title="Tech",
        description="Technology section",
    )

    expected_category = Category(
        category_id="computed-uuid",
        title=dto.title,
        description=dto.description,
        created_by=mock_auth_user.user_id,
        created_at=None,
        updated_by=None,
        updated_at=None,
        version=1,
    )

    mock_category_store.get_category_by_title = AsyncMock(return_value=None)
    mock_category_store.create_category = AsyncMock(return_value=expected_category)

    result = await category_service.create_category(mock_auth_user, dto)

    assert result["message"] == "Category created successfully."
    assert result["category"].title == "Tech"
    assert result["category"].created_by == mock_auth_user.user_id

    mock_category_store.create_category.assert_called_once()

    called_cat = mock_category_store.create_category.call_args.kwargs["category"]
    assert isinstance(called_cat, Category)
    assert called_cat.title == "Tech"
    assert called_cat.description == "Technology section"
    assert called_cat.created_by == mock_auth_user.user_id
    assert UUID(called_cat.category_id)


@pytest.mark.asyncio
async def test_create_category_duplicate_title_raises_api_exception(
    category_service, mock_category_store, mock_auth_user
):
    dto = CreateCategoryDTO(
        title="Duplicate",
        description="Desc",
    )

    existing_category = Category(
        category_id="some-id",
        title="Duplicate",
        description="Desc",
        created_by="user",
        created_at=None,
        updated_by=None,
        updated_at=None,
        version=1,
    )

    mock_category_store.get_category_by_title = AsyncMock(
        return_value=existing_category
    )

    with pytest.raises(ApiException) as exc_info:
        await category_service.create_category(mock_auth_user, dto)

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_get_category_success(
    category_service, mock_category_store, mock_auth_user
):
    category_id = "uuid-111"

    existing_category = Category(
        category_id=category_id,
        title="HR",
        description="Human Resources",
        created_by="someone",
        created_at=None,
        updated_by=None,
        updated_at=None,
        version=1,
    )

    mock_category_store.get_category = AsyncMock(return_value=existing_category)

    result = await category_service.get_category(
        mock_auth_user,
        category_id,
    )

    assert result.category_id == category_id
    assert result.title == "HR"

    mock_category_store.get_category.assert_called_once_with(category_id=category_id)


@pytest.mark.asyncio
async def test_get_category_not_found(
    category_service, mock_category_store, mock_auth_user
):
    mock_category_store.get_category = AsyncMock(return_value=None)

    with pytest.raises(ApiException) as exc_info:
        await category_service.get_category(
            mock_auth_user,
            "unknown-id",
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_all_categories(
    category_service, mock_category_store, mock_auth_user
):
    mock_categories = [
        Category(
            category_id="1",
            title="A",
            description="D",
            created_by="u",
            created_at=None,
            updated_by=None,
            updated_at=None,
            version=1,
        ),
        Category(
            category_id="2",
            title="B",
            description="D",
            created_by="u",
            created_at=None,
            updated_by=None,
            updated_at=None,
            version=1,
        ),
    ]

    mock_category_store.list_categories = AsyncMock(
        return_value=(mock_categories, len(mock_categories))
    )

    results, total = await category_service.get_all_categories(
        mock_auth_user,
        index_size=1,
        max_result=10,
    )

    assert len(results) == 2
    assert total == 2
    assert results[0].title == "A"

    mock_category_store.list_categories.assert_called_once_with(
        index=1,
        limit=10,
    )


@pytest.mark.asyncio
async def test_update_category_success(
    category_service, mock_category_store, mock_auth_user
):
    category_id = "uuid-999"
    dto = UpdateCategoryDTO(
        title="New Title",
        description="New Desc",
    )

    existing_category = Category(
        category_id=category_id,
        title="Old Title",
        description="Old Desc",
        created_by="other-user",
        created_at=None,
        updated_by=None,
        updated_at=None,
        version=1,
    )

    mock_category_store.get_category = AsyncMock(return_value=existing_category)
    mock_category_store.get_category_by_title = AsyncMock(return_value=None)
    mock_category_store.update_category = AsyncMock(return_value=existing_category)

    result = await category_service.update_category(
        mock_auth_user,
        category_id,
        dto,
    )

    assert result["message"] == "Category updated successfully."
    mock_category_store.update_category.assert_called_once()

    updated_cat = mock_category_store.update_category.call_args.kwargs["category"]
    assert updated_cat.title == "New Title"
    assert updated_cat.description == "New Desc"
    assert updated_cat.updated_by == mock_auth_user.user_id


@pytest.mark.asyncio
async def test_update_category_not_found(
    category_service, mock_category_store, mock_auth_user
):
    dto = UpdateCategoryDTO(
        title="Title",
        description="Desc",
    )

    mock_category_store.get_category = AsyncMock(return_value=None)

    with pytest.raises(ApiException) as exc_info:
        await category_service.update_category(
            mock_auth_user,
            "missing-id",
            dto,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_success(
    category_service, mock_category_store, mock_auth_user
):
    category_id = "uuid-888"

    existing_category = Category(
        category_id=category_id,
        title="To Delete",
        description="Desc",
        created_by="u",
        created_at=None,
        updated_by=None,
        updated_at=None,
        version=1,
    )

    mock_category_store.get_category = AsyncMock(return_value=existing_category)
    mock_category_store.delete_category = AsyncMock()

    result = await category_service.delete_category(
        mock_auth_user,
        category_id,
    )

    assert result["message"] == "Category deleted successfully."
    mock_category_store.delete_category.assert_called_once_with(category_id=category_id)


@pytest.mark.asyncio
async def test_delete_category_not_found(
    category_service, mock_category_store, mock_auth_user
):
    category_id = "missing-id"

    mock_category_store.get_category = AsyncMock(return_value=None)

    with pytest.raises(ApiException) as exc_info:
        await category_service.delete_category(
            mock_auth_user,
            category_id,
        )

    assert exc_info.value.status_code == 404
