import os
import typing as t

from json import dumps
from attrs import define
from asyncpg.pool import Pool
from asyncpg.connection import Connection
from contextlib import asynccontextmanager
from asyncpg import Record, create_pool, UniqueViolationError

from .utils import from_json
from .result import Result, is_fail
from .domain import Entity, DB, Repository, Criteria
from .exceptions import InternalError, NotFound, Conflict


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
            # The entity now mirrors a row, so a later `save` guards on this version rather than
            # trying to insert it afresh.
            res.value.mark_stored()
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
    async def list(self, criteria: Criteria) -> tuple[list[T], int]:
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
                res.value.mark_stored()
                items.append(res.value)
            return items, count
            # if len(items) == criteria.limit + 1:
            # #     cursor = create_db_cursor(items[-1].get_id().value, count, criteria.limit)
            # #     return ListPage(cursor=cursor, items=items[:-1])
            # return ListPage(items=items)
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"criteria": criteria.as_sql}) from exc

    @t.override
    async def save(self, state: T) -> None:
        """Insert a new entity, or update the row the caller read.

        The entity says which of the two this is and what the guard should be: `stored_version` is
        `None` until a row exists, and afterwards it is the version that row still carries. An
        update is optimistic -- `WHERE id = ? AND version = ?` against that number -- so a row
        someone else has written since is not overwritten. Taking the guard from the entity rather
        than assuming a single step back from its current version is what lets an aggregate be
        evolved as many times as the work needs before it is saved.

        When the guard does not match, Postgres reports zero rows and nothing else: the caller's
        work is gone, `save` returns, and the aggregate is left holding a state that was never
        stored. That is why the row count is read here. Losing a write is a `Conflict`, and a
        caller that can re-read and re-apply should do so; one that cannot at least fails where the
        loss happened rather than somewhere downstream that wonders why the entity never changed.
        """
        raw = state.serialize()
        stored_version = state.stored_version
        try:
            sql_stm, params = (
                self.__prepare_insert(raw) if stored_version is None else self.__prepare_update(raw, stored_version)
            )
            status = await self.conn.execute(sql_stm, *params)
        except UniqueViolationError as exc:
            raise Conflict(debug={"raw": raw, "table": self.table}) from exc
        except Exception as exc:
            raise InternalError.from_exception(exc, extra={"raw": raw, "table": self.table}) from exc

        # Outside the `except`, or the generic handler above would bury it in an InternalError.
        if stored_version is not None and _rows_affected(status) == 0:
            raise Conflict(
                hints={"reason": "That row moved on since it was read, so the write was not applied"},
                debug={
                    "id": raw.get("id"),
                    "table": self.table,
                    "version": raw.get("version"),
                    "stored_version": stored_version,
                },
            )

        # The row and the entity now agree, so a later `save` guards on this version.
        state.mark_stored()

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

    def __prepare_update(self, raw: dict[str, t.Any], stored_version: int):
        params = [raw["id"], stored_version]
        changes: list[str] = []
        for idx, kv in enumerate(raw.items()):
            changes.append(f"{kv[0]} = ${idx + 3}")
            params.append(dumps(kv[1]) if isinstance(kv[1], (dict, list)) else kv[1])
        sql_stm = f"UPDATE {self.table} SET {", ".join(changes)} WHERE id = $1 AND version = $2"
        return sql_stm, params


def _rows_affected(status: t.Any) -> int | None:
    """The row count in an asyncpg command tag -- "UPDATE 1", "DELETE 0", "INSERT 0 1".

    `None` when the tag is not one this understands, which reads as "cannot tell" rather than
    "nothing was written": a caller must not be handed a conflict on the strength of a guess.
    """
    if not isinstance(status, str):
        return None
    tail = status.rsplit(" ", 1)[-1]
    return int(tail) if tail.isdigit() else None


__all__ = ["PostgresDB", "PostgresRepo", "parse_pg_row"]
