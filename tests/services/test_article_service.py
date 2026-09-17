import inspect
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.dto.wiki.wiki_dto import CreateArticleDTO
from app.core.exceptions.api_exception import ApiException
from app.models.security.auth_user import AuthenticatedUser
from app.models.wiki.wiki_models import Article, Status
from app.services.article.article_service import ArticleService
from app.storage.rds.clients.database_manager import DataBaseManager
from app.storage.rds.datastore.article.article_store import ArticleStore
from app.storage.rds.datastore.interfaces.article import IArticle


@pytest.fixture
def mock_auth_user():
    user = MagicMock(spec=AuthenticatedUser)
    user.user_id = "uuid-user-123"
    user.email = "test@wiki.com"
    return user


@pytest.fixture
def mock_article_store():
    return MagicMock(spec=IArticle)


@pytest.fixture
def mock_category_store():
    store = MagicMock()
    # Ensure category fetching can be awaited in create_article
    store.get_categories_by_ids = AsyncMock(return_value=[])
    return store


@pytest.fixture
def mock_media_store():
    return MagicMock()


@pytest.fixture
def article_service(mock_article_store, mock_category_store, mock_media_store):
    return ArticleService(
        article_store=mock_article_store,
        category_store=mock_category_store,
        media_store=mock_media_store,
    )


def test_article_store_implements_iarticle():
    mock_db_manager = MagicMock(spec=DataBaseManager)

    store_instance = ArticleStore(database_manager=mock_db_manager)
    assert isinstance(store_instance, IArticle)

    for name, method in inspect.getmembers(IArticle, predicate=inspect.isfunction):
        assert hasattr(
            store_instance, name
        ), f"The method {name} is missing on ArticleStore"


@pytest.mark.asyncio
async def test_create_article_success(
    article_service, mock_article_store, mock_category_store, mock_auth_user
):
    dto = CreateArticleDTO(
        title="Introduction to Python",
        content="Python is a versatile programming language.",
        categories=["uuid-cat-123"],
    )

    expected_article = Article(
        article_id="computed-uuid",
        title=dto.title,
        content=dto.content,
        created_by=mock_auth_user.user_id,
        created_at=None,
        updated_by=None,
        updated_at=None,
        version=1,
    )

    mock_category_store.get_categories_by_ids = AsyncMock(
        return_value=[MagicMock(category_id="uuid-cat-123")]
    )
    mock_article_store.create_article = AsyncMock(return_value=expected_article)

    result = await article_service.create_article(dto.model_dump(), mock_auth_user)

    assert result.title == "Introduction to Python"
    mock_article_store.create_article.assert_called_once()


@pytest.mark.asyncio
async def test_get_article_success(article_service, mock_article_store, mock_auth_user):
    article_id = "uuid-111"

    existing_article = Article(
        article_id=article_id,
        title="Advanced Python",
        content="Deep dive into Python.",
        category_id="uuid-cat-123",
        created_by="someone",
        created_at=None,
        updated_by=None,
        updated_at=None,
        version=1,
    )

    mock_article_store.get_article = AsyncMock(return_value=existing_article)

    result = await article_service.get_article(article_id)

    assert result.article_id == article_id
    assert result.title == "Advanced Python"
    mock_article_store.get_article.assert_called_once_with(article_id)


@pytest.mark.asyncio
async def test_get_article_not_found(
    article_service, mock_article_store, mock_auth_user
):
    mock_article_store.get_article = AsyncMock(return_value=None)

    with pytest.raises(ApiException) as exc_info:
        await article_service.get_article("unknown-id")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_article_success(
    article_service, mock_article_store, mock_auth_user
):
    article_id = "uuid-888"

    existing_article = Article(
        article_id=article_id,
        title="To Delete",
        content="Desc",
        category_id="uuid-cat-123",
        user_id=mock_auth_user.user_id,
        created_by=mock_auth_user.user_id,
        created_at=None,
        updated_by=None,
        updated_at=None,
        version=1,
        is_deleted=False,
    )

    # Fixed: match service call get_article instead of load_article
    mock_article_store.get_article = AsyncMock(return_value=existing_article)
    mock_article_store.update_article = AsyncMock(return_value=existing_article)

    await article_service.delete_article(article_id, mock_auth_user)

    mock_article_store.get_article.assert_called_once_with(article_id)
    mock_article_store.update_article.assert_called_once_with(existing_article)
    assert existing_article.is_deleted is True


@pytest.mark.asyncio
async def test_delete_article_not_found(
    article_service, mock_article_store, mock_auth_user
):
    article_id = "missing-id"

    mock_article_store.get_article = AsyncMock(return_value=None)

    with pytest.raises(ApiException) as exc_info:
        await article_service.delete_article(article_id, mock_auth_user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_publish_article_state_change(
    article_service, mock_article_store, mock_auth_user
):
    article_id = "uuid-publish-123"

    existing_article = Article(
        article_id=article_id,
        title="Article à publier",
        content="Contenu de l'article",
        state=Status.SUBMITTED,
        user_id=mock_auth_user.user_id,
        created_by=mock_auth_user.user_id,
        created_at=datetime.now(timezone.utc),
        version=1,
        is_deleted=False,
    )

    async def mock_update(article_to_update):
        return article_to_update

    mock_article_store.get_article = AsyncMock(return_value=existing_article)
    mock_article_store.update_article = AsyncMock(side_effect=mock_update)

    published_article = await article_service.publish(article_id, mock_auth_user)

    assert published_article.state == Status.PUBLISHED
    mock_article_store.update_article.assert_called_once_with(existing_article)

    passed_article = mock_article_store.update_article.call_args[0][0]
    assert passed_article.state == Status.PUBLISHED
