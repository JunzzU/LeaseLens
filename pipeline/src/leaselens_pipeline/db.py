"""Database connection and schema migrations.

Migrations are the plain SQL files in database/migrations, applied in version order
and recorded in schema_migrations. The Spring Boot backend is expected to take this
over with Flyway (same file naming) in Week 3.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = REPO_ROOT / "database" / "migrations"
DEFAULT_URL = "postgresql://localhost:5432/leaselens"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_URL)


def connect(url: str | None = None) -> psycopg.Connection:
    """Autocommit connection; callers open explicit transactions with conn.transaction()."""
    return psycopg.connect(url or database_url(), autocommit=True)


def migrate(conn: psycopg.Connection) -> list[str]:
    conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                        version integer PRIMARY KEY,
                        filename text NOT NULL,
                        applied_at timestamptz NOT NULL DEFAULT now())""")
    applied = {v for (v,) in conn.execute("SELECT version FROM schema_migrations")}
    done = []
    for path in sorted(MIGRATIONS.glob("V*__*.sql"), key=lambda p: int(re.match(r"V(\d+)__", p.name)[1])):
        version = int(re.match(r"V(\d+)__", path.name)[1])
        if version in applied:
            continue
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute("INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                         (version, path.name))
        done.append(path.name)
    return done
