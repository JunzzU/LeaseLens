"""Load RentSafeTO building evaluations (both scoring versions) into evaluations.

Each file maps to one scoring_version; natural key is (building, date, version).
An RSN missing from registration gets a building row with rentsafe_registered = false.
Building coordinates come from here: registration publishes none.
"""
from __future__ import annotations

from dataclasses import dataclass

import psycopg

from ..download.fetch import RawFile
from ..normalization.address import AddressParseError, parse
from ..validation.rows import (FieldError, check_columns, parse_coords, parse_date, parse_int, parse_rsn,
                               parse_score, read_source, records)
from .imports import ImportResult, ImportRun, copy_rows, payload, upsert_aliases
from .registration import soft_int, ward_code


@dataclass(frozen=True)
class Layout:
    """Where each field lives in one version of the evaluation file."""
    version: str
    label: str
    address: str
    date: str
    score: str
    areas: str
    storeys: str
    units: str
    year_built: str
    year_registered: str
    property_type: str
    proactive: str | None = None
    result: str | None = None

    @property
    def required(self) -> set[str]:
        cols = {"RSN", "WARD", "WARDNAME", "LATITUDE", "LONGITUDE", self.address, self.date, self.score,
                self.areas, self.storeys, self.units, self.year_built, self.year_registered, self.property_type}
        return cols | {c for c in (self.proactive, self.result) if c}


LAYOUTS = {
    "evaluations_v2023": Layout(
        "V2023", "2023+ scoring", "SITE ADDRESS", "EVALUATION COMPLETED ON", "CURRENT BUILDING EVAL SCORE",
        "NO OF AREAS EVALUATED", "CONFIRMED STOREYS", "CONFIRMED UNITS", "YEAR BUILT", "YEAR REGISTERED",
        "PROPERTY TYPE", proactive="PROACTIVE BUILDING SCORE"),
    "evaluations_pre2023": Layout(
        "PRE_2023", "pre-2023 scoring", "SITE_ADDRESS", "EVALUATION_COMPLETED_ON", "SCORE",
        "NO_OF_AREAS_EVALUATED", "CONFIRMED_STOREYS", "CONFIRMED_UNITS", "YEAR_BUILT", "YEAR_REGISTERED",
        "PROPERTY_TYPE", result="RESULTS_OF_SCORE"),
}

EVAL_COLUMNS = [
    ("rsn", "text"), ("evaluation_date", "date"), ("evaluation_score", "int4"), ("proactive_score", "int4"),
    ("areas_evaluated", "int4"), ("result_text", "text"), ("latitude", "float8"), ("longitude", "float8"),
    ("ward_name", "text"), ("source_record_id", "text"), ("payload", "jsonb"),
]
BUILDING_COLUMNS = [
    ("rsn", "text"), ("latest_date", "date"), ("address", "text"), ("street_number_low", "int4"),
    ("street_number_high", "int4"), ("street_number_suffix", "text"), ("street_name", "text"),
    ("street_type", "text"), ("street_direction", "text"), ("normalized_address", "text"), ("ward", "text"),
    ("storeys", "int4"), ("units", "int4"), ("year_built", "int4"), ("year_registered", "int4"),
    ("property_type", "text"),
]
# Building fields an evaluation row can supply for buildings that registration doesn't cover.
DESCRIPTIVE = [c for c, _ in BUILDING_COLUMNS if c not in ("rsn", "latest_date")]


def load_evaluations(conn: psycopg.Connection, raw: RawFile) -> ImportResult:
    run = ImportRun(conn, raw)
    try:
        with conn.transaction():
            return _load(conn, run, raw, LAYOUTS[raw.source.key])
    except Exception as e:  # noqa: BLE001 - every failure is recorded on the import row
        return run.fail(e)


def _load(conn: psycopg.Connection, run: ImportRun, raw: RawFile, lay: Layout) -> ImportResult:
    df = read_source(raw.path)
    run.record_columns(list(df.columns))
    check_columns(df, lay.required, run.dataset)

    evals, latest, aliases, seen = [], {}, [], set()
    for n, r in records(df):
        try:
            rsn = parse_rsn(r["RSN"])
            when = parse_date(r[lay.date])
            score, rounded = parse_score(r[lay.score])
            addr = parse(r[lay.address])
        except (FieldError, AddressParseError) as e:
            run.reject(n, str(e), r)
            continue
        if when is None or score is None:
            run.reject(n, "missing evaluation date or score", r)
            continue
        if "created_in_error" in addr.flags:
            run.reject(n, "address marked CREATED IN ERROR", r)
            continue
        if (rsn, when) in seen:
            run.reject(n, "duplicate (RSN, evaluation date)", r)
            continue
        seen.add((rsn, when))
        if rounded:
            run.warnings.add("decimal_score_rounded")   # original kept in raw_payload

        try:
            lat, lon = parse_coords(r["LATITUDE"], r["LONGITUDE"])
        except FieldError:
            run.warnings.add("invalid_coordinates")
            lat = lon = None
        if lat is None:
            run.warnings.add("missing_coordinates")

        evals.append((
            rsn, when, score,
            _proactive(run, r[lay.proactive]) if lay.proactive else None,
            soft_int(run, r[lay.areas], "invalid_areas_evaluated", 0, 100),
            r[lay.result] if lay.result else None,
            lat, lon, r["WARDNAME"], r.get("_id"), payload(r),
        ))
        aliases.append((rsn, r[lay.address], addr))
        if rsn not in latest or when > latest[rsn][1]:
            latest[rsn] = (rsn, when, addr.display(), addr.number_low, addr.number_high, addr.suffix,
                           addr.street_name, addr.street_type, addr.direction, addr.key, ward_code(r["WARD"]),
                           parse_int_or_none(r[lay.storeys], 1, 120), parse_int_or_none(r[lay.units], 1, 5000),
                           parse_int_or_none(r[lay.year_built], 1800, 2100),
                           parse_int_or_none(r[lay.year_registered], 2017, 2100), r[lay.property_type])

    new_buildings = _upsert_unregistered_buildings(conn, run, list(latest.values()))

    conn.execute(f"""CREATE TEMP TABLE stage_evaluations ({', '.join(f'{c} {t}' for c, t in EVAL_COLUMNS)})
                     ON COMMIT DROP""")
    copy_rows(conn, "stage_evaluations", [c for c, _ in EVAL_COLUMNS], [t for _, t in EVAL_COLUMNS], evals)

    fields = ["evaluation_score", "proactive_score", "areas_evaluated", "result_text", "latitude", "longitude",
              "ward_name"]
    merged = conn.execute(
        f"""MERGE INTO evaluations e
            USING (SELECT b.id AS building_id, s.* FROM stage_evaluations s
                   JOIN buildings b ON b.source_building_id = s.rsn) s
            ON e.building_id = s.building_id AND e.evaluation_date = s.evaluation_date
               AND e.scoring_version = %(v)s
            WHEN MATCHED AND ({', '.join(f'e.{f}' for f in fields)}, e.raw_payload)
                 IS DISTINCT FROM ({', '.join(f's.{f}' for f in fields)}, s.payload) THEN
                UPDATE SET {', '.join(f'{f} = s.{f}' for f in fields)}, raw_payload = s.payload,
                           source_record_id = s.source_record_id, updated_import_id = %(imp)s, updated_at = now()
            WHEN NOT MATCHED THEN
                INSERT (building_id, scoring_version, evaluation_date, {', '.join(fields)}, source_record_id,
                        raw_payload, created_import_id, updated_import_id)
                VALUES (s.building_id, %(v)s, s.evaluation_date, {', '.join(f's.{f}' for f in fields)},
                        s.source_record_id, s.payload, %(imp)s, %(imp)s)
            RETURNING merge_action(), e.id, e.building_id, e.evaluation_date, old.evaluation_score,
                      e.evaluation_score""",
        {"v": lay.version, "imp": run.id},
    ).fetchall()

    inserted = updated = 0
    for action, eid, bid, when, old_score, score in merged:
        if action == "INSERT":
            inserted += 1
            run.change(bid, "evaluation", eid, "new_evaluation",
                       f"Evaluation recorded on {when}: score {score} ({lay.label})")
        else:
            updated += 1
            if old_score != score:
                run.change(bid, "evaluation", eid, "evaluation_changed",
                           f"Evaluation of {when} revised: score {old_score} -> {score} ({lay.label})")

    (missing,) = conn.execute(
        """SELECT count(*) FROM evaluations e JOIN buildings b ON b.id = e.building_id
           WHERE e.scoring_version = %s
             AND NOT EXISTS (SELECT 1 FROM stage_evaluations s
                             WHERE s.rsn = b.source_building_id AND s.evaluation_date = e.evaluation_date)""",
        (lay.version,),
    ).fetchone()
    if missing:
        # Kept, not deleted: the City may have withdrawn them, but we don't know why.
        run.warnings.add("evaluations_no_longer_in_source", missing)

    _refresh_locations(conn, run)
    upsert_aliases(conn, aliases, run.dataset)
    if new_buildings:
        run.warnings.add("buildings_not_in_registration_created", new_buildings)
    run.save_rejections()
    return run.complete(len(df), inserted, updated)


def _proactive(run: ImportRun, value) -> int | None:
    try:
        return parse_score(value)[0]
    except FieldError:
        run.warnings.add("invalid_proactive_score")
        return None


def parse_int_or_none(value, lo, hi):
    try:
        return parse_int(value, lo, hi)
    except FieldError:
        return None


def _upsert_unregistered_buildings(conn: psycopg.Connection, run: ImportRun, rows: list[tuple]) -> int:
    """Create buildings for RSNs registration doesn't list; refresh the ones we created that way before.

    Details are only refreshed from this file when its latest evaluation is at least as recent
    as any evaluation already stored, so loading the older file never overwrites newer details.
    """
    conn.execute(f"""CREATE TEMP TABLE stage_eval_buildings ({', '.join(f'{c} {t}' for c, t in BUILDING_COLUMNS)})
                     ON COMMIT DROP""")
    copy_rows(conn, "stage_eval_buildings", [c for c, _ in BUILDING_COLUMNS], [t for _, t in BUILDING_COLUMNS], rows)
    created = conn.execute(
        f"""INSERT INTO buildings (source_building_id, {', '.join(DESCRIPTIVE)}, rentsafe_registered,
                                   created_import_id, updated_import_id)
            SELECT s.rsn, {', '.join(f's.{c}' for c in DESCRIPTIVE)}, false, %(imp)s, %(imp)s
            FROM stage_eval_buildings s
            WHERE NOT EXISTS (SELECT 1 FROM buildings b WHERE b.source_building_id = s.rsn)""",
        {"imp": run.id},
    ).rowcount
    conn.execute(
        f"""UPDATE buildings b SET {', '.join(f'{c} = s.{c}' for c in DESCRIPTIVE)},
                                  updated_import_id = %(imp)s, updated_at = now()
            FROM stage_eval_buildings s
            WHERE b.source_building_id = s.rsn AND b.registration_payload IS NULL
              AND s.latest_date >= coalesce((SELECT max(evaluation_date) FROM evaluations e
                                             WHERE e.building_id = b.id), '-infinity'::date)
              AND ({', '.join(f'b.{c}' for c in DESCRIPTIVE)})
                  IS DISTINCT FROM ({', '.join(f's.{c}' for c in DESCRIPTIVE)})""",
        {"imp": run.id},
    )
    return created


def _refresh_locations(conn: psycopg.Connection, run: ImportRun) -> None:
    """Location = that on the most recent evaluation with coordinates; ward name = the most
    recent one published. Kept separate: many evaluations have a ward but no coordinates."""
    conn.execute(
        """UPDATE buildings b
           SET latitude = l.latitude, longitude = l.longitude,
               geom = ST_SetSRID(ST_MakePoint(l.longitude, l.latitude), 4326)::geography,
               updated_import_id = %s, updated_at = now()
           FROM (SELECT DISTINCT ON (building_id) building_id, latitude, longitude
                 FROM evaluations WHERE latitude IS NOT NULL
                 ORDER BY building_id, evaluation_date DESC, scoring_version DESC) l
           WHERE b.id = l.building_id AND (b.latitude, b.longitude) IS DISTINCT FROM (l.latitude, l.longitude)""",
        (run.id,),
    )
    conn.execute(
        """UPDATE buildings b SET ward_name = w.ward_name, updated_import_id = %s, updated_at = now()
           FROM (SELECT DISTINCT ON (building_id) building_id, ward_name
                 FROM evaluations WHERE ward_name IS NOT NULL
                 ORDER BY building_id, evaluation_date DESC, scoring_version DESC) w
           WHERE b.id = w.building_id AND b.ward_name IS DISTINCT FROM w.ward_name""",
        (run.id,),
    )
