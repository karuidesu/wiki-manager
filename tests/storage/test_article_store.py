from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.wiki.wiki_models import Status
from app.storage.rds.datastore.article.article_store import ArticleStore
from app.storage.rds.dto.search_options import SearchOptionsDTO


@pytest.fixture
def mock_db_manager():
    manager = MagicMock()

    # Setup mock connection and transaction
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    mock_conn.fetch = AsyncMock(return_value=[])

    mock_acquire = MagicMock()
    mock_acquire.__aenter__.return_value = mock_conn
    mock_acquire.__aexit__.return_value = None

    manager.connection_pool.acquire = MagicMock(return_value=mock_acquire)
    return manager, mock_conn


@pytest.fixture
def article_store(mock_db_manager):
    manager, _ = mock_db_manager
    return ArticleStore(manager)


@pytest.mark.asyncio
async def test_search_articles_sql_generation(article_store, mock_db_manager):
    _, mock_conn = mock_db_manager

    options = SearchOptionsDTO(
        page=2,
        max_results=10,
        order_by="created_at",
        direction="DESC",
        state=Status.PUBLISHED,
        tags=["pytest"],
        search="Test title",
        user_id="author-123",
    )

    await article_store.search_articles(options)

    assert mock_conn.fetchval.call_count == 1
    assert mock_conn.fetch.call_count == 1

    # Check count SQL
    count_call_args = mock_conn.fetchval.call_args[0]
    count_sql = count_call_args[0]
    assert "SELECT COUNT(1) FROM articles" in count_sql
    assert "is_deleted = FALSE" in count_sql
    assert "state = $1" in count_sql
    assert "user_id = $2" in count_sql
    assert "title ILIKE $3" in count_sql
    assert "tags::jsonb @> $4::jsonb" in count_sql

    # Count params
    assert count_call_args[1] == "PUBLISHED"
    assert count_call_args[2] == "author-123"
    assert count_call_args[3] == "%Test title%"
    assert count_call_args[4] == '["pytest"]'

    # Check select SQL
    fetch_call_args = mock_conn.fetch.call_args[0]
    select_sql = fetch_call_args[0]
    assert "SELECT * FROM articles WHERE" in select_sql
    assert "ORDER BY created_at DESC" in select_sql
    assert "LIMIT $5 OFFSET $6" in select_sql

    # Select params
    assert fetch_call_args[1] == "PUBLISHED"
    assert fetch_call_args[2] == "author-123"
    assert fetch_call_args[3] == "%Test title%"
    assert fetch_call_args[4] == '["pytest"]'
    assert fetch_call_args[5] == 10  # limit
    assert fetch_call_args[6] == 10  # offset (page=2, max_results=10 -> 10)
