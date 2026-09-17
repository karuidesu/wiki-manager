import json
import logging
from datetime import timezone
from typing import Any, List, Optional

from app.models.wiki.wiki_models import Article, ArticleReaction, Category, Comment
from app.storage.rds.clients.database_manager import DataBaseManager
from app.storage.rds.commons.sql_query_builder import (
    DeleteQueryBuilder,
    InsertQueryBuilder,
    SelectQueryBuilder,
    UpdateQueryBuilder,
)
from app.storage.rds.datastore.interfaces.article import IArticle

LOGGER = logging.getLogger(__name__)


class ArticleStore(IArticle):
    def __init__(self, database_manager: DataBaseManager):
        self._database_manager = database_manager

    async def create_article(self, article: Article) -> Article:
        article_iqb = InsertQueryBuilder(Article)
        article_sql, article_cols = article_iqb.sql_query()

        article_row = []
        for c in article_cols:
            value = getattr(article, c)
            if hasattr(value, "tzinfo") and value is not None:
                value = value.replace(tzinfo=None)

            if isinstance(value, (list, dict)):
                value = json.dumps(value)

            article_row.append(value)

        async with self._database_manager.connection_pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(article_sql, *article_row)

                if getattr(article, "categories", None):
                    for category in article.categories:
                        category_id = (
                            category.category_id
                            if hasattr(category, "category_id")
                            else category
                        )
                        await connection.execute(
                            """
                            INSERT INTO article_categories (article_id, category_id)
                            VALUES ($1, $2) ON CONFLICT DO NOTHING
                            """,
                            article.article_id,
                            category_id,
                        )

                if getattr(article, "article_medias_gallery", None):
                    for media in article.article_medias_gallery:
                        media_id = (
                            media.media_id if hasattr(media, "media_id") else media
                        )
                        await connection.execute(
                            """
                            INSERT INTO article_medias_gallery (article_id, media_id)
                            VALUES ($1, $2) ON CONFLICT DO NOTHING
                            """,
                            article.article_id,
                            media_id,
                        )

        inserted_article = await self.get_article(article.article_id)
        if inserted_article is None:
            raise RuntimeError("Failed to retrieve inserted article.")

        return inserted_article

    async def get_article(
        self, article_id: str, include_deleted: bool = False
    ) -> Optional[Article]:
        where_clauses = {"article_id": article_id}
        if not include_deleted:
            where_clauses["is_deleted"] = False

        async with self._database_manager.connection_pool.acquire() as connection:
            article_sql, article_params = SelectQueryBuilder(
                model_cls=Article,
                where_clauses=where_clauses,
                limit=1,
            ).sql_query()

            article_row = await connection.fetchrow(
                article_sql,
                *article_params,
            )

            if article_row is None:
                return None

            categories_rows = await connection.fetch(
                """
                SELECT c.*
                FROM categories c
                JOIN article_categories ac
                ON c.category_id = ac.category_id
                WHERE ac.article_id = $1
                """,
                article_id,
            )

            categories = [Category(**dict(row)) for row in categories_rows]

            article = self._parse_article_model(article_row=dict(article_row))
            article.categories = categories
            return article

    async def get_article_by_title(self, title: str) -> Optional[Article]:
        async with self._database_manager.connection_pool.acquire() as connection:
            article_sql, article_params = SelectQueryBuilder(
                model_cls=Article,
                where_clauses={"title": title, "is_deleted": False},
                limit=1,
            ).sql_query()

            article_row = await connection.fetchrow(
                article_sql,
                *article_params,
            )

            if article_row is None:
                return None

            return self._parse_article_model(article_row=dict(article_row))

    async def get_all_articles(
        self, page_index: int, max_result: int, direction: str
    ) -> List[Article]:
        page_index = max(0, page_index - 1)
        limit = max(1, max_result)
        offset = page_index * limit
        order_dir = "ASC" if direction.upper() == "ASC" else "DESC"

        async with self._database_manager.connection_pool.acquire() as conn:
            article_sql, article_params = SelectQueryBuilder(
                model_cls=Article,
                where_clauses={"is_deleted": False},
                order_by="created_at",
                order_dir=order_dir,
                limit=limit,
                offset=offset,
            ).sql_query()

            rows = await conn.fetch(article_sql, *article_params)
            articles = []

            for row in rows:
                art = self._parse_article_model(article_row=dict(row))
                cat_rows = await conn.fetch(
                    """
                    SELECT c.*
                    FROM categories c
                    JOIN article_categories ac
                    ON c.category_id = ac.category_id
                    WHERE ac.article_id = $1
                    """,
                    art.article_id,
                )
                art.categories = [Category(**dict(r)) for r in cat_rows]
                articles.append(art)

            return articles

    async def count_articles(self) -> int:
        async with self._database_manager.connection_pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(1) FROM articles WHERE is_deleted = FALSE"
            )
            return int(total or 0)

    async def update_article(self, article: Article) -> Article:
        updated_fields = [
            "title",
            "content",
            "tags",
            "sources",
            "state",
            "likes",
            "dislikes",
            "admin_review",
            "cover_image_id",
            "is_deleted",
            "updated_by",
            "updated_at",
        ]

        article_sql, upd_cols, where_cols = UpdateQueryBuilder(
            model_cls=Article,
            updated_fields=updated_fields,
            where_fields=["article_id"],
            manage_version=True,
        ).sql_query()

        params = []
        for c in upd_cols:
            val = getattr(article, c)
            if hasattr(val, "tzinfo") and val is not None:
                val = val.replace(tzinfo=None)
            elif isinstance(val, (list, dict)):
                val = json.dumps(val)
            params.append(val)

        for c in where_cols:
            val = getattr(article, c)
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            params.append(val)

        async with self._database_manager.connection_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(article_sql, *params)

                if getattr(article, "categories", None) is not None:
                    await conn.execute(
                        "DELETE FROM article_categories WHERE article_id = $1",
                        article.article_id,
                    )
                    for category in article.categories:
                        category_id = (
                            category.category_id
                            if hasattr(category, "category_id")
                            else category
                        )
                        await conn.execute(
                            """
                            INSERT INTO article_categories (article_id, category_id)
                            VALUES ($1, $2) ON CONFLICT DO NOTHING
                            """,
                            article.article_id,
                            category_id,
                        )

                if getattr(article, "article_medias_gallery", None) is not None:
                    await conn.execute(
                        "DELETE FROM article_medias_gallery WHERE article_id = $1",
                        article.article_id,
                    )
                    for media in article.article_medias_gallery:
                        media_id = (
                            media.media_id if hasattr(media, "media_id") else media
                        )
                        await conn.execute(
                            """
                            INSERT INTO article_medias_gallery (article_id, media_id)
                            VALUES ($1, $2) ON CONFLICT DO NOTHING
                            """,
                            article.article_id,
                            media_id,
                        )

        updated_article = await self.get_article(
            article.article_id, include_deleted=True
        )
        if updated_article is None:
            raise RuntimeError("Failed to retrieve updated article.")

        return updated_article

    async def delete_article(self, article_id: str) -> None:
        async with self._database_manager.connection_pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    DELETE FROM article_categories
                    WHERE article_id = $1
                    """,
                    article_id,
                )

                delete_sql, delete_params = DeleteQueryBuilder(
                    model_cls=Article,
                    where_clauses={"article_id": article_id},
                ).sql_query()

                await connection.execute(delete_sql, *delete_params)

    @classmethod
    def _parse_article_model(cls, *, article_row: dict[str, Any]) -> Article:
        """Parse raw DB row into the Article domain model."""
        data = dict(article_row)

        for field in ("tags", "sources"):
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = json.loads(val)
                except Exception:
                    data[field] = []

        created_at = data.get("created_at")
        if created_at is not None and created_at.tzinfo is None:
            data["created_at"] = created_at.replace(tzinfo=timezone.utc)

        updated_at = data.get("updated_at")
        if updated_at is not None and updated_at.tzinfo is None:
            data["updated_at"] = updated_at.replace(tzinfo=timezone.utc)

        return Article(**data)

    async def get_reaction(
        self, article_id: str, user_id: str
    ) -> Optional[ArticleReaction]:
        async with self._database_manager.connection_pool.acquire() as conn:
            sql, params = SelectQueryBuilder(
                model_cls=ArticleReaction,
                where_clauses={"article_id": article_id, "user_id": user_id},
                limit=1,
            ).sql_query()

            row = await conn.fetchrow(sql, *params)
            if not row:
                return None
            return ArticleReaction(**dict(row))

    async def save_reaction(
        self,
        reaction: ArticleReaction,
        like: int = 0,
        dislike: int = 0,
        is_update: bool = False,
    ) -> ArticleReaction:
        async with self._database_manager.connection_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO article_reactions (
                        reaction_id, article_id, user_id, reaction,
                        created_by, created_at, updated_by, updated_at, version
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (article_id, user_id)
                    DO UPDATE SET
                        reaction = EXCLUDED.reaction,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = EXCLUDED.updated_at,
                        version = article_reactions.version + 1
                    """,
                    reaction.reaction_id,
                    reaction.article_id,
                    reaction.user_id,
                    reaction.reaction,
                    reaction.created_by,
                    (
                        reaction.created_at.replace(tzinfo=None)
                        if reaction.created_at
                        else None
                    ),
                    reaction.updated_by,
                    (
                        reaction.updated_at.replace(tzinfo=None)
                        if reaction.updated_at
                        else None
                    ),
                    reaction.version,
                )

                await conn.execute(
                    """
                    UPDATE articles
                    SET likes = likes + $1,
                        dislikes = dislikes + $2
                    WHERE article_id = $3
                    """,
                    like,
                    dislike,
                    reaction.article_id,
                )

        updated_reaction = await self.get_reaction(
            reaction.article_id,
            reaction.user_id,
        )
        if updated_reaction is None:
            raise RuntimeError("Failed to retrieve saved reaction.")

        return updated_reaction

    async def cancel_reaction(
        self, reaction: ArticleReaction, like: int, dislike: int
    ) -> None:
        async with self._database_manager.connection_pool.acquire() as conn:
            async with conn.transaction():
                sql, params = DeleteQueryBuilder(
                    model_cls=ArticleReaction,
                    where_clauses={"reaction_id": reaction.reaction_id},
                ).sql_query()

                await conn.execute(sql, *params)

                await conn.execute(
                    """
                    UPDATE articles
                    SET likes = likes + $1, dislikes = dislikes + $2
                    WHERE article_id = $3
                    """,
                    like,
                    dislike,
                    reaction.article_id,
                )

    async def load_reactions(
        self, article_id: str, page_index: int, max_result: int, direction: str
    ) -> List[ArticleReaction]:
        page_index = max(0, page_index - 1)
        limit = max(1, max_result)
        offset = page_index * limit
        order_dir = "ASC" if direction.upper() == "ASC" else "DESC"

        async with self._database_manager.connection_pool.acquire() as conn:
            sql, params = SelectQueryBuilder(
                model_cls=ArticleReaction,
                where_clauses={"article_id": article_id},
                order_by="created_at",
                order_dir=order_dir,
                limit=limit,
                offset=offset,
            ).sql_query()

            rows = await conn.fetch(sql, *params)
            return [ArticleReaction(**dict(row)) for row in rows]

    async def count_reactions(self, article_id: str) -> int:
        async with self._database_manager.connection_pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(1) FROM article_reactions WHERE article_id = $1",
                article_id,
            )
            return int(total or 0)

    async def add_comment(self, comment: Comment) -> Comment:
        sql, cols = InsertQueryBuilder(Comment).sql_query()
        params = [getattr(comment, c) for c in cols]

        for i, val in enumerate(params):
            if hasattr(val, "tzinfo") and val is not None:
                params[i] = val.replace(tzinfo=None)
            elif isinstance(val, (list, dict)):
                params[i] = json.dumps(val)

        async with self._database_manager.connection_pool.acquire() as conn:
            await conn.execute(sql, *params)

        inserted_comment = await self.get_comment(comment.comment_id)
        if inserted_comment is None:
            raise RuntimeError("Failed to retrieve inserted comment.")

        return inserted_comment

    async def update_comment(self, comment: Comment) -> Comment:
        sql, upd_cols, where_cols = UpdateQueryBuilder(
            model_cls=Comment,
            updated_fields=["is_deleted", "updated_by", "updated_at", "version"],
            where_fields=["comment_id"],
            manage_version=False,
        ).sql_query()

        params = [getattr(comment, c) for c in upd_cols] + [
            getattr(comment, c) for c in where_cols
        ]
        for i, val in enumerate(params):
            if hasattr(val, "tzinfo") and val is not None:
                params[i] = val.replace(tzinfo=None)
            elif isinstance(val, (list, dict)):
                params[i] = json.dumps(val)

        async with self._database_manager.connection_pool.acquire() as conn:
            await conn.execute(sql, *params)

        updated_comment = await self.get_comment(comment.comment_id)
        if updated_comment is None:
            raise RuntimeError("Failed to retrieve updated comment.")

        return updated_comment

    async def get_comment(self, comment_id: str) -> Optional[Comment]:
        async with self._database_manager.connection_pool.acquire() as conn:
            sql, params = SelectQueryBuilder(
                model_cls=Comment,
                where_clauses={"comment_id": comment_id},
                limit=1,
            ).sql_query()

            row = await conn.fetchrow(sql, *params)
            if not row:
                return None
            return Comment(**dict(row))

    async def load_comments(
        self, article_id: str, page_index: int, max_result: int, direction: str
    ) -> List[Comment]:
        page_index = max(0, page_index - 1)
        limit = max(1, max_result)
        offset = page_index * limit
        order_dir = "ASC" if direction.upper() == "ASC" else "DESC"

        async with self._database_manager.connection_pool.acquire() as conn:
            sql, params = SelectQueryBuilder(
                model_cls=Comment,
                where_clauses={"article_id": article_id, "is_deleted": False},
                order_by="created_at",
                order_dir=order_dir,
                limit=limit,
                offset=offset,
            ).sql_query()

            rows = await conn.fetch(sql, *params)
            return [Comment(**dict(row)) for row in rows]

    async def count_comments(self, article_id: str) -> int:
        async with self._database_manager.connection_pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(1) FROM comments "
                "WHERE article_id = $1 AND is_deleted = FALSE",
                article_id,
            )
            return int(total or 0)
