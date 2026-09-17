from typing import Any, Literal, Type, cast

from sqlalchemy import Table, inspect
from sqlalchemy.orm import Mapper
from sqlmodel import SQLModel


class SelectQueryBuilder:
    def __init__(
        self,
        model_cls: Type[SQLModel],
        selected_columns: Literal["*"] | list[str] | None = None,
        where_clauses: dict[str, Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
        order_by: str | None = None,
        order_dir: str = "DESC",
        allow_expressions: bool = False,
    ):
        mapper = cast(Mapper, inspect(model_cls))
        table: Table = mapper.local_table

        self._model_cls = model_cls
        self._schema = table.schema
        self._table_name = table.name
        self._fqtn = f"{self._schema + '.' if self._schema else ''}{self._table_name}"

        self._model_columns = {c.name for c in table.columns}
        self._where_clauses = where_clauses or {}
        self._offset = offset
        self._limit = limit
        self._order_by = order_by

        normalized_dir = order_dir.strip().upper()
        if normalized_dir not in ("ASC", "DESC"):
            raise ValueError("order_dir must be strictly 'ASC' or 'DESC'")
        self._order_dir = normalized_dir

        if selected_columns is None:
            self._selected_columns: str | list[str] = list(self._model_columns)
        elif selected_columns == "*":
            self._selected_columns = "*"
        else:
            if not allow_expressions:
                for col in selected_columns:
                    if col not in self._model_columns:
                        raise ValueError(
                            f"Selected column '{col}' does not exist in "
                            f"model {model_cls.__name__}"
                        )
            self._selected_columns = list(selected_columns)

        for col in self._where_clauses.keys():
            if col not in self._model_columns:
                raise ValueError(
                    f"WHERE column '{col}' does not exist in model {model_cls.__name__}"
                )

        if self._order_by and self._order_by not in self._model_columns:
            raise ValueError(
                f"Order by column '{self._order_by}' "
                f"does not exist in model {model_cls.__name__}"
            )

    def sql_query(self) -> tuple[str, list[Any]]:
        if isinstance(self._selected_columns, str):
            cols_clause = self._selected_columns
        else:
            cols_clause = ", ".join(self._selected_columns)

        query = f"SELECT {cols_clause} FROM {self._fqtn}"
        params: list[Any] = []

        if self._where_clauses:
            where_parts = []
            for col, val in self._where_clauses.items():
                if val is None:
                    where_parts.append(f"{col} IS NULL")
                else:
                    params.append(val)
                    where_parts.append(f"{col} = ${len(params)}")
            query += f" WHERE {' AND '.join(where_parts)}"

        if self._order_by:
            query += f" ORDER BY {self._order_by} {self._order_dir}"

        if self._limit is not None:
            params.append(self._limit)
            query += f" LIMIT ${len(params)}"

        if self._offset is not None:
            params.append(self._offset)
            query += f" OFFSET ${len(params)}"

        return query, params


class InsertQueryBuilder:
    def __init__(
        self, model_cls: Type[SQLModel], explicit_columns: list[str] | None = None
    ):
        self._model_cls = model_cls
        table = model_cls.__table__
        self._table_name = table.name

        if explicit_columns:
            self._columns = explicit_columns
        else:
            self._columns = [col.name for col in table.columns]

    def sql_query(self) -> tuple[str, list[str]]:
        sql_columns = ", ".join(self._columns)
        sql_values = ", ".join(f"${i + 1}" for i in range(len(self._columns)))
        return (
            f"INSERT INTO {self._table_name} ({sql_columns}) VALUES ({sql_values})",
            self._columns,
        )


class UpdateQueryBuilder:
    def __init__(
        self,
        model_cls: Type[SQLModel],
        updated_fields: list[str],
        where_fields: list[str],
        manage_version: bool = True,
    ):
        self._model_cls = model_cls
        table = model_cls.__table__
        self._table_name = table.name
        self._updated_fields = updated_fields
        self._where_fields = where_fields
        self._manage_version = manage_version
        self._column_names = {col.name for col in table.columns}

        for f in updated_fields + where_fields:
            if f not in self._column_names:
                raise ValueError(
                    f"Field '{f}' does not exist in model '{model_cls.__name__}'"
                )

    def sql_query(self) -> tuple[str, list[str], list[str]]:
        assignments = [
            f"{field} = ${i + 1}" for i, field in enumerate(self._updated_fields)
        ]

        if self._manage_version and "version" in self._column_names:
            assignments.append("version = version + 1")

        set_clause = ", ".join(assignments)

        base_index = len(self._updated_fields) + 1
        where_parts = [
            f"{field} = ${base_index + i}" for i, field in enumerate(self._where_fields)
        ]
        where_clause = " AND ".join(where_parts)

        sql = f"UPDATE {self._table_name} SET {set_clause} WHERE {where_clause}"
        return sql, self._updated_fields, self._where_fields


class DeleteQueryBuilder:
    def __init__(self, model_cls: Type[SQLModel], where_clauses: dict[str, Any]):
        table = model_cls.__table__
        self._table_name = table.name
        self._column_names = {col.name for col in table.columns}
        self._where_clauses = where_clauses or {}

        for col in self._where_clauses.keys():
            if col not in self._column_names:
                raise ValueError(
                    f"WHERE column '{col}' does not exist in model {model_cls.__name__}"
                )

    def sql_query(self) -> tuple[str, list[Any]]:
        if not self._where_clauses:
            raise ValueError("DELETE query requires at least one WHERE clause")

        conditions = []
        params: list[Any] = []
        for col, val in self._where_clauses.items():
            if val is None:
                conditions.append(f"{col} IS NULL")
            else:
                params.append(val)
                conditions.append(f"{col} = ${len(params)}")

        sql = f"DELETE FROM {self._table_name} WHERE {' AND '.join(conditions)}"
        return sql, params
