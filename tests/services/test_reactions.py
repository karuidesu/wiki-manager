from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions.api_exception import ApiException
from app.models.security.auth_user import AuthenticatedUser
from app.models.wiki.wiki_models import Article, ArticleReaction
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
async def test_like_article_success(
    article_service, mock_article_store, mock_auth_user, existing_article
):
    mock_article_store.get_article = AsyncMock(return_value=existing_article)
    mock_article_store.get_reaction = AsyncMock(return_value=None)

    expected_reaction = ArticleReaction(
        reaction_id="reaction-123",
        article_id=existing_article.article_id,
        user_id=mock_auth_user.user_id,
        reaction="LIKE",
    )
    mock_article_store.save_reaction = AsyncMock(return_value=expected_reaction)

    result = await article_service.like_article(
        existing_article.article_id, mock_auth_user
    )

    assert result.reaction == "LIKE"
    mock_article_store.get_article.assert_called_once_with(existing_article.article_id)
    mock_article_store.save_reaction.assert_called_once()


@pytest.mark.asyncio
async def test_dislike_article_success(
    article_service, mock_article_store, mock_auth_user, existing_article
):
    mock_article_store.get_article = AsyncMock(return_value=existing_article)
    mock_article_store.get_reaction = AsyncMock(return_value=None)

    expected_reaction = ArticleReaction(
        reaction_id="reaction-124",
        article_id=existing_article.article_id,
        user_id=mock_auth_user.user_id,
        reaction="DISLIKE",
    )
    mock_article_store.save_reaction = AsyncMock(return_value=expected_reaction)

    result = await article_service.dislike_article(
        existing_article.article_id, mock_auth_user
    )

    assert result.reaction == "DISLIKE"
    mock_article_store.save_reaction.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_reaction_success(
    article_service, mock_article_store, mock_auth_user, existing_article
):
    existing_reaction = ArticleReaction(
        reaction_id="reaction-123",
        article_id=existing_article.article_id,
        user_id=mock_auth_user.user_id,
        reaction="LIKE",
    )
    mock_article_store.get_article = AsyncMock(return_value=existing_article)
    mock_article_store.get_reaction = AsyncMock(return_value=existing_reaction)
    mock_article_store.cancel_reaction = AsyncMock(return_value=None)

    await article_service.cancel_reaction(existing_article.article_id, mock_auth_user)

    mock_article_store.cancel_reaction.assert_called_once_with(
        reaction=existing_reaction,
        like=-1,
        dislike=0,
    )


@pytest.mark.asyncio
async def test_load_reactions_success(
    article_service, mock_article_store, existing_article
):
    mock_article_store.get_article = AsyncMock(return_value=existing_article)
    mock_reactions = [
        ArticleReaction(
            reaction_id="r1",
            article_id=existing_article.article_id,
            user_id="user1",
            reaction="LIKE",
        )
    ]
    mock_article_store.load_reactions = AsyncMock(return_value=mock_reactions)
    mock_article_store.count_reactions = AsyncMock(return_value=1)

    result = await article_service.load_reactions(
        article_id=existing_article.article_id,
        page_size=1,
        max_result=20,
        direction="DESC",
    )

    assert result["total"] == 1
    mock_article_store.load_reactions.assert_called_once_with(
        article_id=existing_article.article_id,
        page_index=1,
        max_result=20,
        direction="DESC",
    )


@pytest.mark.asyncio
async def test_reaction_article_not_found(
    article_service, mock_article_store, mock_auth_user
):
    mock_article_store.get_article = AsyncMock(return_value=None)

    with pytest.raises(ApiException) as exc_info:
        await article_service.like_article("non-existent-id", mock_auth_user)

    assert exc_info.value.status_code == 404
