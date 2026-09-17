from typing import Generator, Optional

import pytest
from sqlmodel import Field, SQLModel

from app.storage.rds.commons.sql_query_builder import (
    DeleteQueryBuilder,
    InsertQueryBuilder,
    SelectQueryBuilder,
    UpdateQueryBuilder,
)


class User(SQLModel, table=True):
    # pyrefly: ignore [bad-override]
    __tablename__: str = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    version: int = Field(default=1)


@pytest.fixture
def mock_pool() -> Generator[None, None, None]:
    pool_connected = True
    assert pool_connected is True
    yield
    pool_connected = False
    assert pool_connected is False


def test_select_builder_success(mock_pool: None) -> None:
    builder = SelectQueryBuilder(
        model_cls=User,
        selected_columns=["username", "email"],
        where_clauses={"username": "Alice", "email": "alice@example.com"},
        limit=10,
        offset=5,
        order_by="username",
        order_dir="ASC",
    )
    sql, params = builder.sql_query()

    assert (
        "SELECT username, email FROM users" in sql
        or "SELECT email, username FROM users" in sql
    )
    assert "WHERE" in sql
    assert "username = $1" in sql or "username = $2" in sql
    assert "email = $1" in sql or "email = $2" in sql
    assert "ORDER BY username ASC" in sql
    assert "LIMIT $3" in sql
    assert "OFFSET $4" in sql
    assert "Alice" not in sql
    assert "alice@example.com" not in sql
    assert params == ["Alice", "alice@example.com", 10, 5] or params == [
        "alice@example.com",
        "Alice",
        10,
        5,
    ]


def test_select_builder_unknown_where_column_raises_error() -> None:
    with pytest.raises(ValueError) as exc_info:
        SelectQueryBuilder(model_cls=User, where_clauses={"unknown_col": "value"})

    assert "WHERE column 'unknown_col' does not exist" in str(exc_info.value)


def test_select_builder_unknown_order_by_column_raises_error() -> None:
    with pytest.raises(ValueError) as exc_info:
        SelectQueryBuilder(model_cls=User, order_by="invalid_column")

    assert "Order by column 'invalid_column' does not exist" in str(exc_info.value)


@pytest.mark.parametrize("invalid_dir", ["SEM-ASC", "DROP TABLE users;", "1; SELECT 1"])
def test_select_builder_order_dir_injection_rejected(invalid_dir: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        SelectQueryBuilder(model_cls=User, order_by="username", order_dir=invalid_dir)

    assert "order_dir must be strictly 'ASC' or 'DESC'" in str(exc_info.value)


def test_select_builder_order_dir_normalized() -> None:
    builder = SelectQueryBuilder(
        model_cls=User, order_by="username", order_dir=" asc  "
    )
    sql, _ = builder.sql_query()
    assert "ORDER BY username ASC" in sql


def test_insert_builder_success() -> None:
    builder = InsertQueryBuilder(model_cls=User)
    sql, columns = builder.sql_query()

    assert sql.startswith("INSERT INTO users")
    assert "$1" in sql
    assert "$2" in sql
    assert "id" in columns
    assert "username" in columns
    assert "email" in columns


def test_update_builder_success() -> None:
    builder = UpdateQueryBuilder(
        model_cls=User,
        updated_fields=["username", "email"],
        where_fields=["id"],
        manage_version=True,
    )
    sql, updated, where = builder.sql_query()

    assert "UPDATE users SET" in sql
    assert "username = $1" in sql
    assert "email = $2" in sql
    assert "version = version + 1" in sql
    assert "WHERE id = $3" in sql
    assert updated == ["username", "email"]
    assert where == ["id"]


def test_update_builder_invalid_field_raises_error() -> None:
    with pytest.raises(ValueError):
        UpdateQueryBuilder(
            model_cls=User, updated_fields=["fake_col"], where_fields=["id"]
        )


def test_delete_builder_success() -> None:
    builder = DeleteQueryBuilder(model_cls=User, where_clauses={"id": 1})
    sql, params = builder.sql_query()

    assert sql == "DELETE FROM users WHERE id = $1"
    assert params == [1]


def test_delete_builder_no_where_raises_error() -> None:
    builder = DeleteQueryBuilder(model_cls=User, where_clauses={})
    with pytest.raises(ValueError) as exc_info:
        builder.sql_query()

    assert "DELETE query requires at least one WHERE clause" in str(exc_info.value)
