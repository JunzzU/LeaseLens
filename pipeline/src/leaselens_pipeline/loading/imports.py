"""Bookkeeping shared by every loader: the data_imports row, rejections, staging, aliases.

A loader does all of its writes inside one transaction, so a failed import leaves the
existing data untouched. Only the data_imports row is written outside it, so failures
are recorded too.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import psycopg
from psycopg.types.json import Jsonb

from ..download.fetch import RawFile
from ..normalization.address import Address, expand_keys, key_to_text
from ..validation.rows import Warnings


def payload(row: dict) -> Jsonb:
    """The source row as JSON, minus the portal's _id (regenerated on every portal refresh)."""
    return Jsonb({k: v for k, v in row.items() if k != "_id"})


@dataclass
class ImportResult:
    dataset: str
    import_id: int
    status: str
    record_count: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0
    warnings: dict = field(default_factory=dict)
    error: str | None = None

    def report(self) -> str:
        lines = [
            f"Dataset: {self.dataset} (import #{self.import_id})",
            f"Source records: {self.record_count:,}",
            f"Inserted: {self.inserted:,}",
            f"Updated: {self.updated:,}",
            f"Unchanged: {self.unchanged:,}",
            f"Rejected: {self.rejected:,}",
        ]
        for kind, n in sorted(self.warnings.items()):
            lines.append(f"Warning: {kind}: {n}")
        if self.error:
            lines.append(f"Error: {self.error}")
        lines.append(f"Status: {self.status.replace('_', ' ').capitalize()}")
        return "\n".join(lines)


class ImportRun:
    def __init__(self, conn: psycopg.Connection, raw: RawFile):
        self.conn = conn
        self.raw = raw
        self.dataset = raw.source.key
        self.warnings = Warnings()
        self.schema_drift: dict[str, list[str]] = {}
        self.rejections: list[tuple[int, str, dict]] = []
        (self.id,) = conn.execute(
            """INSERT INTO data_imports (dataset_name, source_url, source_version, raw_path, checksum)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (self.dataset, raw.url, raw.source_version, str(raw.path), raw.sha256),
        ).fetchone()
        prev = conn.execute(
            """SELECT source_columns FROM data_imports
               WHERE dataset_name = %s AND status LIKE 'completed%%' AND id < %s
               ORDER BY id DESC LIMIT 1""",
            (self.dataset, self.id),
        ).fetchone()
        self.is_baseline = prev is None       # first load: no change events, everything is "new"
        self.previous_columns = prev[0] if prev else None

    def record_columns(self, columns: list[str]) -> None:
        self.conn.execute("UPDATE data_imports SET source_columns = %s WHERE id = %s", (columns, self.id))
        if self.previous_columns is not None:
            added = sorted(set(columns) - set(self.previous_columns))
            removed = sorted(set(self.previous_columns) - set(columns))
            if added:
                self.schema_drift["columns_added"] = added
            if removed:
                self.schema_drift["columns_removed"] = removed

    def reject(self, source_row: int, reason: str, row: dict) -> None:
        self.rejections.append((source_row, reason, row))

    def save_rejections(self) -> None:
        with self.conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO import_rejections (import_id, source_row, reason, raw_payload) VALUES (%s, %s, %s, %s)",
                [(self.id, n, reason, Jsonb(row)) for n, reason, row in self.rejections],
            )

    def change(self, building_id: int, entity_type: str, entity_id: int, change_type: str, summary: str) -> None:
        if self.is_baseline:
            return
        self.conn.execute(
            """INSERT INTO building_changes (building_id, entity_type, entity_id, change_type, change_summary, import_id)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (building_id, entity_type, entity_id, change_type, summary, self.id),
        )

    def complete(self, record_count: int, inserted: int, updated: int) -> ImportResult:
        rejected = len(self.rejections)
        unchanged = record_count - rejected - inserted - updated
        warnings = {**self.warnings, **{k: ", ".join(v) for k, v in self.schema_drift.items()}}
        status = "completed_with_warnings" if (warnings or rejected) else "completed"
        self.conn.execute(
            """UPDATE data_imports SET completed_at = now(), status = %s, record_count = %s,
                   inserted_count = %s, updated_count = %s, unchanged_count = %s, rejected_count = %s,
                   warnings = %s
               WHERE id = %s""",
            (status, record_count, inserted, updated, unchanged, rejected, Jsonb(warnings), self.id),
        )
        return ImportResult(self.dataset, self.id, status, record_count, inserted, updated,
                            unchanged, rejected, warnings)

    def fail(self, error: Exception) -> ImportResult:
        msg = f"{type(error).__name__}: {error}"
        self.conn.execute(
            "UPDATE data_imports SET completed_at = now(), status = 'failed', error_summary = %s WHERE id = %s",
            (msg, self.id),
        )
        return ImportResult(self.dataset, self.id, "failed", error=msg)


def copy_rows(conn: psycopg.Connection, table: str, columns: list[str], types: list[str], rows) -> None:
    """Bulk-load rows into a (temporary) table with COPY."""
    with conn.cursor().copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN") as cp:
        cp.set_types(types)
        for row in rows:
            cp.write_row(row)


def upsert_aliases(conn: psycopg.Connection, aliases: list[tuple[str, str, Address]], source: str) -> int:
    """Add every civic-number key for (RSN, raw address, parsed address). Existing aliases are kept."""
    conn.execute("""CREATE TEMP TABLE stage_aliases (rsn text, raw_address text, normalized_address text,
                                                     search_text text) ON COMMIT DROP""")
    rows = {(rsn, raw, key, key_to_text(key)) for rsn, raw, addr in aliases for key in expand_keys(addr)}
    copy_rows(conn, "stage_aliases", ["rsn", "raw_address", "normalized_address", "search_text"],
              ["text"] * 4, sorted(rows))
    cur = conn.execute(
        """INSERT INTO building_aliases (building_id, raw_address, normalized_address, search_text, source)
           SELECT DISTINCT ON (b.id, s.normalized_address) b.id, s.raw_address, s.normalized_address, s.search_text, %s
           FROM stage_aliases s JOIN buildings b ON b.source_building_id = s.rsn
           ORDER BY b.id, s.normalized_address, s.raw_address
           ON CONFLICT (building_id, normalized_address) DO NOTHING""",
        (source,),
    )
    return cur.rowcount
