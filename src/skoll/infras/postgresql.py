import os
import typing as t

from json import dumps
from attrs import define
from skoll.domain import Entity
from skoll.utils import from_json
from skoll.result import Result, is_fail
from contextlib import asynccontextmanager
from asyncpg.pool import Pool, PoolConnectionProxy
from skoll.errors import InternalError, NotFound, Conflict
from asyncpg import Record, create_pool, UniqueViolationError
from skoll.application import DB, Repository, Criteria, ListCriteria, ListPage


__all__ = ["PostgresDB", "PostgresRepo", "parse_pg_row"]


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


class PostgresDB(DB[PoolConnectionProxy]):

    dsn: str
    __pool: Pool | None

    def __init__(self, dsn: str | None = None) -> None:
        dsn = dsn or os.getenv("PG_DB_DSN", "")
        if not dsn:
            raise InternalError(debug={"dsn": dsn, "message": "PG_DB_DSN is not set"})
        self.dsn = dsn
        self.__pool = None

    @t.override
    async def connect(self) -> None:
        if self.__pool is None:
            try:
                self.__pool = await create_pool(dsn=self.dsn, min_size=1, max_size=10)
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
            yield t.cast(PoolConnectionProxy, conn)

    @t.override
    @asynccontextmanager
    async def transaction(self):
        if self.__pool is None:
            raise RuntimeError("Database pool is not initialized.")
        async with self.__pool.acquire() as conn:
            async with conn.transaction():
                yield t.cast(PoolConnectionProxy, conn)


@define(kw_only=True, frozen=True, slots=True)
class PostgresRepo[T: Entity](Repository[T]):

    table: str
    conn: PoolConnectionProxy
    restore_func: t.Callable[[dict[str, t.Any]], Result[T]]

    @t.override
    async def get(self, criteria: Criteria) -> T | None:
        try:
            qry, params = criteria.as_sql
            record = await self.conn.fetchrow(qry, *params)
            if not isinstance(record, Record):
                return None
            res = self.restore_func(parse_pg_row(record))
            if is_fail(res):
                raise ValueError("Entity Parsing failed")
            return res.value
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"criteria": criteria.as_sql})

    @t.override
    async def exist(self, criteria: Criteria) -> bool:
        try:
            qry, params = criteria.as_sql
            record = await self.conn.fetchrow(qry, *params)
            return record is not None
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"criteria": criteria.as_sql})

    @t.override
    async def delete(self, criteria: Criteria) -> None:
        try:
            qry, params = criteria.as_sql
            await self.conn.execute(qry.replace("SELECT *", "DELETE"), *params)
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"criteria": criteria.as_sql})

    @t.override
    async def list(self, criteria: ListCriteria) -> ListPage[T]:
        try:
            qry, params = criteria.as_sql
            rows = await self.conn.fetch(qry, *params)
            items: list[T] = []
            for row in rows:
                if not isinstance(row, Record):
                    raise ValueError("Invalid row type")
                res = self.restore_func(parse_pg_row(row))
                if is_fail(res):
                    raise ValueError("Entity Parsing failed")
                items.append(res.value)
            return ListPage(cursor="NOOP", items=items)  # TODO: Implement cursor
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"criteria": criteria.as_sql})

    @t.override
    async def save(self, state: T) -> None:
        try:
            raw = state.serialize()
            sql_stm, params = self.__prepare_insert(raw) if state.version.value == 0 else self.__prepare_update(raw)
            _ = await self.conn.execute(sql_stm, *params)
        except UniqueViolationError as exc:
            raise Conflict(debug={"raw": state.serialize(), "table": self.table})
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"raw": state.serialize(), "table": self.table})

    def __prepare_insert(self, raw: dict[str, t.Any]):
        params: list[t.Any] = []
        attrs: list[str] = []
        keys: list[str] = []
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
