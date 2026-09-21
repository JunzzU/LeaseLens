"""Load RentSafeTO Apartment Building Registration into buildings (+ aliases).

Registration is the authority for a building's address and size. A building that
drops out of the file is marked rentsafe_registered = false, never deleted.
"""
from __future__ import annotations

import re

import psycopg

from ..download.fetch import RawFile
from ..normalization.address import AddressParseError, parse
from ..validation.rows import FieldError, check_columns, parse_int, parse_rsn, read_source, records
from .imports import ImportResult, ImportRun, copy_rows, payload, upsert_aliases

REQUIRED = {"RSN", "SITE_ADDRESS", "CONFIRMED_STOREYS", "CONFIRMED_UNITS", "PROPERTY_TYPE",
            "WARD", "YEAR_BUILT", "YEAR_REGISTERED", "PCODE"}

# Refuse to deregister buildings en masse because of a truncated or broken file.
MIN_SHARE_OF_REGISTERED = 0.8

BUILDING_COLUMNS = [
    ("rsn", "text"), ("address", "text"), ("street_number_low", "int4"), ("street_number_high", "int4"),
    ("street_number_suffix", "text"), ("street_name", "text"), ("street_type", "text"),
    ("street_direction", "text"), ("normalized_address", "text"), ("postal_fsa", "text"), ("ward", "text"),
    ("storeys", "int4"), ("units", "int4"), ("year_built", "int4"), ("year_registered", "int4"),
    ("property_type", "text"), ("payload", "jsonb"),
]


class ImportAborted(Exception):
    pass


def soft_int(run: ImportRun, value, kind: str, lo=None, hi=None):
    try:
        return parse_int(value, lo, hi)
    except FieldError:
        run.warnings.add(kind)
        return None


def ward_code(value) -> str | None:
    return str(value).zfill(2) if value and str(value).isdigit() else None


def load_registration(conn: psycopg.Connection, raw: RawFile) -> ImportResult:
    run = ImportRun(conn, raw)
    try:
        with conn.transaction():
            return _load(conn, run, raw)
    except Exception as e:  # noqa: BLE001 - every failure is recorded on the import row
        return run.fail(e)


def _load(conn: psycopg.Connection, run: ImportRun, raw: RawFile) -> ImportResult:
    df = read_source(raw.path)
    run.record_columns(list(df.columns))
    check_columns(df, REQUIRED, run.dataset)

    rows, aliases, seen = [], [], set()
    for n, r in records(df):
        try:
            rsn = parse_rsn(r["RSN"])
            addr = parse(r["SITE_ADDRESS"])
        except (FieldError, AddressParseError) as e:
            run.reject(n, str(e), r)
            continue
        if "created_in_error" in addr.flags:
            run.reject(n, "address marked CREATED IN ERROR", r)
            continue
        if rsn in seen:
            run.reject(n, "duplicate RSN", r)
            continue
        seen.add(rsn)
        for flag in addr.flags:
            run.warnings.add(f"address_flag_{flag}")

        fsa = r["PCODE"].upper() if r["PCODE"] else None
        if fsa and not re.fullmatch(r"M\d[A-Z]", fsa):
            run.warnings.add("invalid_postal_fsa")
            fsa = None
        rows.append((
            rsn, addr.display(), addr.number_low, addr.number_high, addr.suffix, addr.street_name,
            addr.street_type, addr.direction, addr.key, fsa, ward_code(r["WARD"]),
            soft_int(run, r["CONFIRMED_STOREYS"], "invalid_storeys", 1, 120),
            soft_int(run, r["CONFIRMED_UNITS"], "invalid_units", 1, 5000),
            soft_int(run, r["YEAR_BUILT"], "invalid_year_built", 1800, 2100),
            soft_int(run, r["YEAR_REGISTERED"], "invalid_year_registered", 2017, 2100),
            r["PROPERTY_TYPE"], payload(r),
        ))
        aliases.append((rsn, r["SITE_ADDRESS"], addr))

    (registered_now,) = conn.execute("SELECT count(*) FROM buildings WHERE rentsafe_registered").fetchone()
    if registered_now and len(rows) < MIN_SHARE_OF_REGISTERED * registered_now:
        raise ImportAborted(f"file has {len(rows)} valid buildings but {registered_now} are registered; "
                            "refusing to deregister that many at once")

    conn.execute(f"""CREATE TEMP TABLE stage_buildings ({', '.join(f'{c} {t}' for c, t in BUILDING_COLUMNS)})
                     ON COMMIT DROP""")
    copy_rows(conn, "stage_buildings", [c for c, _ in BUILDING_COLUMNS], [t for _, t in BUILDING_COLUMNS], rows)

    fields = ["address", "street_number_low", "street_number_high", "street_number_suffix", "street_name",
              "street_type", "street_direction", "normalized_address", "postal_fsa", "ward", "storeys",
              "units", "year_built", "year_registered", "property_type"]
    merged = conn.execute(
        f"""MERGE INTO buildings b
            USING stage_buildings s ON b.source_building_id = s.rsn
            WHEN MATCHED AND ({', '.join(f'b.{f}' for f in fields)}, b.registration_payload, b.rentsafe_registered)
                 IS DISTINCT FROM ({', '.join(f's.{f}' for f in fields)}, s.payload, true) THEN
                UPDATE SET {', '.join(f'{f} = s.{f}' for f in fields)}, registration_payload = s.payload,
                           rentsafe_registered = true, updated_import_id = %(imp)s, updated_at = now()
            WHEN NOT MATCHED THEN
                INSERT (source_building_id, {', '.join(fields)}, registration_payload, rentsafe_registered,
                        created_import_id, updated_import_id)
                VALUES (s.rsn, {', '.join(f's.{f}' for f in fields)}, s.payload, true, %(imp)s, %(imp)s)
            RETURNING merge_action(), b.id, b.address, old.rentsafe_registered""",
        {"imp": run.id},
    ).fetchall()

    inserted = updated = 0
    for action, bid, address, was_registered in merged:
        if action == "INSERT":
            inserted += 1
            run.change(bid, "building", bid, "registered", f"{address} added to RentSafeTO registration data")
        else:
            updated += 1
            if not was_registered:
                run.change(bid, "building", bid, "registered", f"{address} now listed in RentSafeTO registration data")

    gone = conn.execute(
        """UPDATE buildings SET rentsafe_registered = false, updated_import_id = %s, updated_at = now()
           WHERE rentsafe_registered AND source_building_id NOT IN (SELECT rsn FROM stage_buildings)
           RETURNING id, address""",
        (run.id,),
    ).fetchall()
    for bid, address in gone:
        run.change(bid, "building", bid, "deregistered", f"{address} no longer listed in RentSafeTO registration data")
    if gone:
        run.warnings.add("deregistered_buildings", len(gone))

    upsert_aliases(conn, aliases, run.dataset)
    run.save_rejections()
    return run.complete(len(df), inserted, updated + len(gone))
