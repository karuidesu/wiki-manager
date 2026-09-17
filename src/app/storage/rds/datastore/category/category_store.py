import logging
from datetime import timezone
from typing import Any, Optional, Tuple

from app.api.dto.wiki.wiki_dto import CategoryResponseDTO
from app.models.wiki import Category
from app.storage.rds.clients.database_manager import DataBaseManager
from app.storage.rds.commons.sql_query_builder import (
    DeleteQueryBuilder,
    InsertQueryBuilder,
    SelectQueryBuilder,
    UpdateQueryBuilder,
)
from app.storage.rds.datastore.interfaces.category import ICategory

LOGGER = logging.getLogger(__name__)


class CategoryStore(ICategory):
    def __init__(self, database_manager: DataBaseManager):
        self._database_manager = database_manager

    async def create_category(self, category: Category) -> CategoryResponseDTO:
        category_iqb = InsertQueryBuilder(Category)
        category_sql, category_cols = category_iqb.sql_query()

        real_category_cols = list(Category.__table__.columns.keys())
        category_cols = [c for c in category_cols if c in real_category_cols]

        category_row = []

        for c in category_cols:
            value = getattr(category, c)

            if hasattr(value, "tzinfo") and value is not None:
                value = value.replace(tzinfo=None)

            category_row.append(value)

        async with self._database_manager.connection_pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(category_sql, *category_row)

        inserted_category = await self.get_category(category.category_id)

        if inserted_category is None:
            raise RuntimeError("Failed to retrieve inserted category.")

        return inserted_category

    async def get_category(self, category_id: str) -> Optional[CategoryResponseDTO]:
        async with self._database_manager.connection_pool.acquire() as connection:
            async with connection.transaction():
                category_sql, category_params = SelectQueryBuilder(
                    model_cls=Category,
                    where_clauses={"category_id": category_id},
                    limit=1,
                ).sql_query()

                category_row = await connection.fetchrow(
                    category_sql,
                    *category_params,
                )

                if category_row is None:
                    return None

                return self.parse_category_response_kwargs(
                    category_row=dict(category_row)
                )

    async def get_category_by_title(self, title: str) -> Optional[CategoryResponseDTO]:
        async with self._database_manager.connection_pool.acquire() as connection:
            async with connection.transaction():
                category_sql, category_params = SelectQueryBuilder(
                    model_cls=Category,
                    where_clauses={"title": title},
                    limit=1,
                ).sql_query()

                category_row = await connection.fetchrow(
                    category_sql,
                    *category_params,
                )

                if category_row is None:
                    return None

                return self.parse_category_response_kwargs(
                    category_row=dict(category_row)
                )

    async def get_categories_by_ids(
        self, category_ids: list[str]
    ) -> list[CategoryResponseDTO]:
        if not category_ids:
            return []

        async with self._database_manager.connection_pool.acquire() as connection:
            async with connection.transaction():
                sql = """
                    SELECT * FROM categories
                    WHERE category_id = ANY($1)
                """
                rows = await connection.fetch(sql, category_ids)

                return [
                    self.parse_category_response_kwargs(category_row=dict(row))
                    for row in rows
                ]

    async def list_categories(
        self,
        index: int = 0,
        limit: int = 20,
    ) -> Tuple[list[CategoryResponseDTO], int]:

        index = max(0, index - 1)
        limit = max(1, limit)
        offset = index * limit

        async with self._database_manager.connection_pool.acquire() as conn:
            async with conn.transaction():

                count_sql, count_params = SelectQueryBuilder(
                    model_cls=Category,
                    selected_columns=["COUNT(1)::bigint AS total"],
                    allow_expressions=True,
                ).sql_query()

                total = int(await conn.fetchval(count_sql, *count_params) or 0)

                if total == 0:
                    return [], 0

                category_sql, category_params = SelectQueryBuilder(
                    model_cls=Category,
                    order_by="created_at",
                    order_dir="DESC",
                    limit=limit,
                    offset=offset,
                ).sql_query()

                rows = await conn.fetch(category_sql, *category_params)

                return (
                    [
                        self.parse_category_response_kwargs(category_row=dict(row))
                        for row in rows
                    ],
                    total,
                )

    async def update_category(
        self, category: Category, category_id: str
    ) -> CategoryResponseDTO:

        updated_fields = [
            "title",
            "description",
            "updated_by",
            "updated_at",
        ]

        category_sql, upd_cols, where_cols = UpdateQueryBuilder(
            model_cls=Category,
            updated_fields=updated_fields,
            where_fields=["category_id"],
            manage_version=True,
        ).sql_query()

        params = []

        for c in upd_cols:
            value = getattr(category, c)

            if hasattr(value, "tzinfo") and value is not None:
                value = value.replace(tzinfo=None)

            params.append(value)

        for c in where_cols:
            params.append(getattr(category, c))

        async with self._database_manager.connection_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(category_sql, *params)

        updated_category = await self.get_category(category_id)

        if updated_category is None:
            raise RuntimeError("Failed to retrieve updated category.")

        return updated_category

    async def delete_category(self, category_id: str) -> None:
        async with self._database_manager.connection_pool.acquire() as connection:
            async with connection.transaction():

                await connection.execute(
                    """
                    DELETE FROM article_categories
                    WHERE category_id = $1
                    """,
                    category_id,
                )

                delete_sql, delete_params = DeleteQueryBuilder(
                    model_cls=Category,
                    where_clauses={"category_id": category_id},
                ).sql_query()

                await connection.execute(delete_sql, *delete_params)

    @classmethod
    def parse_category_response_kwargs(
        cls,
        *,
        category_row: dict[str, Any],
    ) -> CategoryResponseDTO:

        created_at = category_row.get("created_at")

        if created_at is not None and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        updated_at = category_row.get("updated_at")

        if updated_at is not None and updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        return CategoryResponseDTO(
            category_id=category_row["category_id"],
            title=category_row["title"],
            description=category_row.get("description"),
            created_by=category_row["created_by"],
            # pyrefly: ignore [bad-argument-type]
            created_at=created_at,
            updated_by=category_row.get("updated_by"),
            updated_at=updated_at,
            version=category_row["version"],
        )
