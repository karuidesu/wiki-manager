from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions.api_exception import ApiException
from app.models.security.auth_user import AuthenticatedUser
from app.models.wiki.wiki_models import Article, Comment
from app.services.article.article_service import ArticleService
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
def article_service(mock_article_store):
    return ArticleService(
        article_store=mock_article_store,
        category_store=MagicMock(),
        media_store=MagicMock(),
    )


@pytest.fixture
def existing_article():
    return Article(
        article_id="article-uuid-123",
        title="Test Article",
        content="Test content",
        user_id="owner-id",
        created_by="owner-id",
        version=1,
        is_deleted=False,
    )


@pytest.mark.asyncio
async def test_add_comment_success(
    article_service, mock_article_store, mock_auth_user, existing_article
):
    mock_article_store.get_article = AsyncMock(return_value=existing_article)
    payload = {"content": "Great article!"}

    expected_comment = Comment(
        comment_id="comment-123",
        content=payload["content"],
        article_id=existing_article.article_id,
        created_by=mock_auth_user.user_id,
        is_deleted=False,
    )
    mock_article_store.add_comment = AsyncMock(return_value=expected_comment)

    result = await article_service.add_comment(
        existing_article.article_id, payload, mock_auth_user
    )

    assert result.content == "Great article!"
    mock_article_store.add_comment.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_comments_success(
    article_service, mock_article_store, existing_article
):
    mock_article_store.get_article = AsyncMock(return_value=existing_article)
    mock_comments = [
        Comment(
            comment_id="c1",
            content="Insightful read.",
            article_id=existing_article.article_id,
            is_deleted=False,
        )
    ]
    mock_article_store.load_comments = AsyncMock(return_value=mock_comments)
    mock_article_store.count_comments = AsyncMock(return_value=1)

    result = await article_service.load_comments(
        article_id=existing_article.article_id,
        page_size=1,
        max_result=20,
        direction="DESC",
    )

    assert result["total"] == 1
    assert len(result["comments"]) == 1
    mock_article_store.load_comments.assert_called_once_with(
        article_id=existing_article.article_id,
        page_index=1,
        max_result=20,
        direction="DESC",
    )


@pytest.mark.asyncio
async def test_delete_comment_success(
    article_service, mock_article_store, mock_auth_user
):
    comment_id = "comment-123"
    existing_comment = Comment(
        comment_id=comment_id,
        content="Test comment",
        article_id="article-123",
        created_by=mock_auth_user.user_id,
        is_deleted=False,
    )

    mock_article_store.get_comment = AsyncMock(return_value=existing_comment)
    mock_article_store.update_comment = AsyncMock(return_value=existing_comment)

    await article_service.delete_comment(comment_id, mock_auth_user)

    mock_article_store.get_comment.assert_called_once_with(comment_id)
    mock_article_store.update_comment.assert_called_once()


@pytest.mark.asyncio
async def test_delete_comment_not_found(
    article_service, mock_article_store, mock_auth_user
):
    mock_article_store.get_comment = AsyncMock(return_value=None)

    with pytest.raises(ApiException) as exc_info:
        await article_service.delete_comment("unknown-comment-id", mock_auth_user)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_comment_forbidden(
    article_service, mock_article_store, mock_auth_user
):
    comment_id = "comment-123"
    existing_comment = Comment(
        comment_id=comment_id,
        content="Test comment",
        article_id="article-123",
        created_by="other-user-id",
        is_deleted=False,
    )

    mock_article_store.get_comment = AsyncMock(return_value=existing_comment)

    with pytest.raises(ApiException) as exc_info:
        await article_service.delete_comment(comment_id, mock_auth_user)

    assert exc_info.value.status_code == 403
