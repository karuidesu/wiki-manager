from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions.api_exception import ApiException
from app.models.security.auth_user import AuthenticatedUser
from app.models.wiki.wiki_models import Article, Status
from app.security.api_roles import ApiRoles
from app.services.article.article_service import ArticleService
from app.storage.rds.datastore.interfaces.article import IArticle
from app.storage.rds.dto.search_options import SearchOptionsDTO


@pytest.fixture
def mock_auth_user():
    user = MagicMock(spec=AuthenticatedUser)
    user.user_id = "uuid-user-123"
    user.email = "test@wiki.com"
    user.roles = []
    return user


@pytest.fixture
def mock_reviewer_user():
    user = MagicMock(spec=AuthenticatedUser)
    user.user_id = "uuid-reviewer-456"
    user.email = "reviewer@wiki.com"
    user.roles = [ApiRoles.MANAGER]
    return user


@pytest.fixture
def mock_article_store():
    return MagicMock(spec=IArticle)


@pytest.fixture
def mock_category_store():
    return MagicMock()


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


@pytest.mark.asyncio
async def test_get_all_articles_success(article_service, mock_article_store):
    fake_article = Article(
        article_id="art-1",
        title="Public Article",
        content="Content",
        state=Status.PUBLISHED,
        created_by="user-1",
        version=1,
    )
    mock_article_store.search_articles = AsyncMock(return_value=([fake_article], 1))

    result = await article_service.get_all_articles(
        page=1,
        max_results=20,
        order_by="created_at",
        direction="DESC",
        tags=["python"],
        search="Public",
    )

    assert result["total"] == 1
    assert result["page"] == 1
    assert result["max_results"] == 20
    assert result["total_pages"] == 1
    assert len(result["items"]) == 1

    mock_article_store.search_articles.assert_called_once()
    options: SearchOptionsDTO = mock_article_store.search_articles.call_args[0][0]
    assert options.page == 1
    assert options.max_results == 20
    assert options.state == Status.PUBLISHED
    assert options.tags == ["python"]
    assert options.search == "Public"


@pytest.mark.asyncio
async def test_get_all_articles_rejected_order_by(article_service, mock_article_store):
    mock_article_store.search_articles = AsyncMock(
        side_effect=ValueError("Unauthorized sort column: 'password'")
    )

    with pytest.raises(ApiException) as exc_info:
        await article_service.get_all_articles(order_by="password")

    assert exc_info.value.status_code == 400
    msg = exc_info.value.message
    error_text = msg.get("message", "") if isinstance(msg, dict) else str(msg)
    assert "Unauthorized sort column" in error_text


@pytest.mark.asyncio
async def test_get_admin_all_articles_forbidden_non_reviewer(
    article_service, mock_auth_user
):
    mock_auth_user.roles = ["USER"]

    with pytest.raises(ApiException) as exc_info:
        await article_service.get_admin_all_articles(auth_user=mock_auth_user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_admin_all_articles_success_with_filters(
    article_service, mock_article_store, mock_reviewer_user
):
    fake_article = Article(
        article_id="art-2",
        title="Draft Article",
        content="Draft Content",
        state=Status.DRAFT,
        user_id="author-789",
        created_by="author-789",
        version=1,
    )
    mock_article_store.search_articles = AsyncMock(return_value=([fake_article], 1))

    result = await article_service.get_admin_all_articles(
        auth_user=mock_reviewer_user,
        page=2,
        max_results=10,
        order_by="updated_at",
        direction="ASC",
        state=Status.DRAFT,
        author_id="author-789",
        search="Draft",
    )

    assert result["total"] == 1
    assert result["page"] == 2
    assert result["max_results"] == 10
    assert result["total_pages"] == 1
    assert len(result["items"]) == 1

    mock_article_store.search_articles.assert_called_once()
    options: SearchOptionsDTO = mock_article_store.search_articles.call_args[0][0]
    assert options.page == 2
    assert options.max_results == 10
    assert options.order_by == "updated_at"
    assert options.direction == "ASC"
    assert options.state == Status.DRAFT
    assert options.user_id == "author-789"
    assert options.search == "Draft"


@pytest.mark.asyncio
async def test_get_admin_all_articles_rejected_order_by(
    article_service, mock_article_store, mock_reviewer_user
):
    mock_article_store.search_articles = AsyncMock(
        side_effect=ValueError("Unauthorized sort column: 'injected_column'")
    )

    with pytest.raises(ApiException) as exc_info:
        await article_service.get_admin_all_articles(
            auth_user=mock_reviewer_user,
            order_by="injected_column",
        )

    assert exc_info.value.status_code == 400
    msg = exc_info.value.message
    error_text = msg.get("message", "") if isinstance(msg, dict) else str(msg)
    assert "Unauthorized sort column" in error_text
