import logging

from app.models.wiki.wiki_models import Media
from app.storage.rds.clients.database_manager import DataBaseManager
from app.storage.rds.commons.sql_query_builder import (
    DeleteQueryBuilder,
    InsertQueryBuilder,
    SelectQueryBuilder,
)
from app.storage.rds.datastore.interfaces.media import IMedia

LOGGER = logging.getLogger(__name__)


class MediaStore(IMedia):
    def __init__(self, database_manager: DataBaseManager):
        self._database_manager = database_manager

    async def add_medias(self, medias: list[Media]) -> list[Media] | None:
        try:
            query_builder = InsertQueryBuilder(model_cls=Media)
            add_media_sql, media_columns = query_builder.sql_query()

            values = [
                [getattr(media, column) for column in media_columns] for media in medias
            ]

            async with self._database_manager.connection_pool.acquire() as connection:
                async with connection.transaction():
                    await connection.executemany(add_media_sql, values)

            return medias

        except Exception as exc:
            LOGGER.error("Error while adding medias: %s", exc)
            return None

    async def load_media(self, media_id: str) -> Media | None:
        try:
            query_builder = SelectQueryBuilder(
                model_cls=Media,
                where_clauses={"media_id": media_id},
            )
            load_media_sql, params = query_builder.sql_query()

            async with self._database_manager.connection_pool.acquire() as connection:
                async with connection.transaction():
                    row = await connection.fetchrow(load_media_sql, *params)

            if row is None:
                return None

            return Media(**dict(row))

        except Exception as exc:
            LOGGER.error("Error while loading media: %s", exc)
            raise

    async def count_medias(self) -> int:
        try:
            sql = f"SELECT COUNT(*) FROM {Media.__tablename__}"

            async with self._database_manager.connection_pool.acquire() as connection:
                async with connection.transaction():
                    return await connection.fetchval(sql)

        except Exception as exc:
            LOGGER.error("Error while counting medias: %s", exc)
            raise

    async def load_medias(
        self,
        page_index: int | None = None,
        max_result: int | None = None,
        direction: str | None = None,
    ) -> list[Media]:
        try:
            offset = None
            if page_index is not None and max_result is not None and page_index > 0:
                offset = (page_index - 1) * max_result

            query_builder = SelectQueryBuilder(
                model_cls=Media,
                limit=max_result,
                offset=offset,
                order_by="created_at",
                order_dir=direction or "DESC",
            )

            load_medias_sql, params = query_builder.sql_query()

            async with self._database_manager.connection_pool.acquire() as connection:
                async with connection.transaction():
                    records = await connection.fetch(load_medias_sql, *params)

            return [Media(**dict(record)) for record in records]

        except Exception as exc:
            LOGGER.error("Error while loading medias: %s", exc)
            raise

    async def delete_media(self, media_id: str) -> None:
        try:
            query = DeleteQueryBuilder(
                Media,
                {"media_id": media_id},
            ).sql_query()

            if query is None:
                return

            delete_media_sql, params = query

            async with self._database_manager.connection_pool.acquire() as connection:
                async with connection.transaction():
                    await connection.execute(delete_media_sql, *params)

        except Exception as exc:
            LOGGER.error("Error while deleting media: %s", exc)
            raise
