"""Database access. Every tenant-scoped transaction sets app.tenant_id so row-level security applies."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class Database:
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10) -> None:
        self.pool = ConnectionPool(dsn, min_size=min_size, max_size=max_size, open=True,
                                   kwargs={"row_factory": dict_row, "autocommit": False})

    def close(self) -> None:
        self.pool.close()

    @contextmanager
    def tenant_tx(self, tenant_id: str) -> Iterator[psycopg.Connection]:
        """Transaction bound to one tenant. Tenant ID must come from a verified principal."""
        if not tenant_id:
            raise ValueError("tenant_id required")
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
                yield conn

    @contextmanager
    def system_tx(self) -> Iterator[psycopg.Connection]:
        """Transaction with no tenant context: only definer lookups and non-tenant tables are visible."""
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute("SELECT set_config('app.tenant_id', '', true)")
                yield conn
