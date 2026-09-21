"""Database connection and schema check.

The schema is owned by Flyway in the Spring Boot backend, which applies the files in
database/migrations when it starts. The pipeline never changes the schema; it only
checks that the migrations it was written against have been applied.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = REPO_ROOT / "database" / "migrations"
DEFAULT_URL = "postgresql://localhost:5432/leaselens"


class SchemaNotReady(Exception):
    pass


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_URL)


def connect(url: str | None = None) -> psycopg.Connection:
    """Autocommit connection; callers open explicit transactions with conn.transaction()."""
    return psycopg.connect(url or database_url(), autocommit=True)


def migration_files() -> list[tuple[int, Path]]:
    files = [(int(re.match(r"V(\d+)__", p.name)[1]), p) for p in MIGRATIONS.glob("V*__*.sql")]
    return sorted(files)


def check_schema(conn: psycopg.Connection) -> None:
    expected = migration_files()[-1][0]
    has_history = conn.execute("SELECT to_regclass('flyway_schema_history') IS NOT NULL").fetchone()[0]
    applied = conn.execute(
        "SELECT max(version::int) FROM flyway_schema_history WHERE success AND version IS NOT NULL"
    ).fetchone()[0] if has_history else None
    if applied is None or applied < expected:
        raise SchemaNotReady(
            f"database schema is at version {applied or 'none'}, expected {expected}. "
            "Start the backend once to apply migrations: cd backend && ./mvnw spring-boot:run")
