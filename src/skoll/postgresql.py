import os
import typing as t

from json import dumps
from attrs import define
from asyncpg.pool import Pool
from asyncpg.connection import Connection
from contextlib import asynccontextmanager
from asyncpg import Record, create_pool, UniqueViolationError

from .result import Result, is_fail
from .utils import from_json, create_db_cursor
from .exceptions import InternalError, NotFound, Conflict
from .domain import Entity, DB, Repository, Criteria, ListPage


def parse_pg_row(row: t.Any, errors_hints: dict[str, t.Any] | None = None) -> dict[str, t.Any]:
    raw = {}
    if row is None:
        raise NotFound(hints=errors_hints or {})
    if not isinstance(row, Record):
        raise InternalError(debug={"row": row, "message": "Invalid row PG data", "errors_hints": errors_hints})
    for key, value in row.items():
        json_value = from_json(value)
        raw[key] = json_value if isinstance(value, str) and json_value is not None else value
    return raw


class PostgresDB(DB[Connection]):

    dsn: str
    __pool: Pool | None
    __max_pool_size: int
    __min_pool_size: int

    def __init__(self, dsn: str | None = None, max_pool_size: int = 10, min_pool_size: int = 10) -> None:
        dsn = dsn or os.getenv("PG_DB_DSN", "")
        if not dsn:
            raise InternalError(debug={"dsn": dsn, "message": "PG_DB_DSN is not set"})
        self.dsn = dsn
        self.__pool = None
        self.__min_pool_size = min_pool_size
        self.__max_pool_size = max_pool_size

    @t.override
    async def connect(self) -> None:
        if self.__pool is None:
            try:
                self.__pool = await create_pool(
                    dsn=self.dsn, min_size=self.__min_pool_size, max_size=self.__max_pool_size
                )
            except Exception as exc:
                raise InternalError.from_exception(exc)

    @t.override
    async def close(self) -> None:
        if self.__pool is not None:
            await self.__pool.close()
            self.__pool = None

    @t.override
    @asynccontextmanager
    async def session(self):
        if self.__pool is None:
            raise RuntimeError("Database pool is not initialized.")
        async with self.__pool.acquire() as conn:
            yield t.cast(Connection, conn)

    @t.override
    @asynccontextmanager
    async def transaction(self):
        if self.__pool is None:
            raise RuntimeError("Database pool is not initialized.")
        async with self.__pool.acquire() as conn:
            async with conn.transaction():
                yield t.cast(Connection, conn)


@define(kw_only=True, frozen=True, slots=True)
class PostgresRepo[T: Entity](Repository[T]):

    table: str
    conn: Connection
    restore_func: t.Callable[[dict[str, t.Any]], Result[T]]

    @t.override
    async def get(self, criteria: Criteria) -> T | None:
        try:
            qry, params, _, _, _ = criteria.as_sql
            record = await self.conn.fetchrow(qry, *params)
            if not isinstance(record, Record):
                return None
            res = self.restore_func(parse_pg_row(record))
            if is_fail(res):
                raise ValueError("Entity Parsing failed")
            return res.value
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"criteria": criteria.as_sql}) from exc

    @t.override
    async def exist(self, criteria: Criteria) -> bool:
        try:
            qry, params, _, _, _ = criteria.as_sql
            record = await self.conn.fetchrow(qry, *params)
            return record is not None
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"criteria": criteria.as_sql}) from exc

    @t.override
    async def delete(self, criteria: Criteria) -> None:
        try:
            _, _, count_query, count_params, _ = criteria.as_sql
            delete_query = count_query.replace("SELECT COUNT(*)", "DELETE", 1)
            await self.conn.execute(delete_query, *count_params)
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"criteria": criteria.as_sql}) from exc

    @t.override
    async def list(self, criteria: Criteria) -> ListPage[T]:
        try:
            qry, params, count_query, count_params, items_count = criteria.as_sql
            count: int = (
                items_count if items_count else t.cast(int, await self.conn.fetchval(count_query, *count_params))
            )
            rows = await self.conn.fetch(qry, *params)
            items: list[T] = []
            for row in rows:
                if not isinstance(row, Record):
                    raise ValueError("Invalid row type")
                res = self.restore_func(parse_pg_row(row))
                if is_fail(res):
                    raise ValueError("Entity Parsing failed")
                items.append(res.value)
            if len(items) == criteria.limit + 1:
                cursor = create_db_cursor(items[-1].id.value, count, criteria.limit)
                return ListPage(cursor=cursor, items=items[:-1])
            return ListPage(items=items)
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"criteria": criteria.as_sql}) from exc

    @t.override
    async def save(self, state: T) -> None:
        try:
            raw = state.serialize()
            sql_stm, params = self.__prepare_insert(raw) if state.version.value == 0 else self.__prepare_update(raw)
            _ = await self.conn.execute(sql_stm, *params)
        except UniqueViolationError as exc:
            raise Conflict(debug={"raw": state.serialize(), "table": self.table}) from exc
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"raw": state.serialize(), "table": self.table}) from exc

    def __prepare_insert(self, raw: dict[str, t.Any]):
        keys: list[str] = []
        attrs: list[str] = []
        params: list[t.Any] = []

        for idx, kv in enumerate(raw.items()):
            attrs.append(kv[0])
            keys.append(f"${idx + 1}")
            params.append(dumps(kv[1]) if isinstance(kv[1], (dict, list)) else kv[1])
        sql_stm = f"INSERT INTO {self.table}({", ".join(attrs)}) VALUES({", ".join(keys)})"
        return sql_stm, params

    def __prepare_update(self, raw: dict[str, t.Any]):
        params = [raw["id"], raw["version"] - 1]
        changes: list[str] = []
        for idx, kv in enumerate(raw.items()):
            changes.append(f"{kv[0]} = ${idx + 3}")
            params.append(dumps(kv[1]) if isinstance(kv[1], (dict, list)) else kv[1])
        sql_stm = f"UPDATE {self.table} SET {", ".join(changes)} WHERE id = $1 AND version = $2"
        return sql_stm, params


__all__ = ["PostgresDB", "PostgresRepo", "parse_pg_row"]
