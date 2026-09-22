"""Load City of Toronto building permits (active and cleared) and match them to buildings.

Only permits whose address matches a RentSafeTO building alias are stored. Each file is
one import; a permit that moves from the active file to the cleared file keeps its row
(natural key: number, revision, type) and is recorded as a status change.

Matching is by address only, and every candidate is kept in permit_matches with how it
was found. An address that belongs to several buildings is never attached silently.
"""
from __future__ import annotations

import re
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

import psycopg

from ..download.fetch import RawFile
from ..normalization.address import permit_match_keys
from ..validation.rows import FieldError, check_columns, parse_date, parse_int, read_source
from .imports import ImportResult, ImportRun, copy_rows, payload

REQUIRED = {"PERMIT_NUM", "REVISION_NUM", "PERMIT_TYPE", "STRUCTURE_TYPE", "WORK", "STREET_NUM", "STREET_NAME",
            "STREET_TYPE", "STREET_DIRECTION", "POSTAL", "GEO_ID", "APPLICATION_DATE", "ISSUED_DATE",
            "COMPLETED_DATE", "STATUS", "DESCRIPTION", "CURRENT_USE", "PROPOSED_USE",
            "DWELLING_UNITS_CREATED", "DWELLING_UNITS_LOST", "EST_CONST_COST"}
# Contractor names are often private individuals; not needed for the product, so not kept.
PRIVATE_COLUMNS = {"BUILDER_NAME"}
SOURCE_FILE = {"permits_active": "ACTIVE", "permits_cleared": "CLEARED"}

_OTHER_STRUCTURE = re.compile(r"^SFD|TOWNHOUSE|^\d\+? UNIT|LANEWAY|GARDEN SUITE|^DETACHED|SEMI-DETACHED", re.I)
_NON_RESIDENTIAL = re.compile(
    r"OFFICE|RETAIL|RESTAURANT|PARKING|MEDICAL|DENTAL|CHILD CARE|DAYCARE|FITNESS|INDUSTRIAL|NON RESIDENTIAL|"
    r"WAREHOUSE|BANK|PERSONAL SERVICE|SCHOOL|WORSHIP|CHURCH|HOTEL|MOTEL|LABORATORY|GAS STATION|AUTO|CLINIC|"
    r"HOSPITAL|THEATRE|CLUB|STORE|SHOP|SIGN", re.I)
_RESIDENTIAL_BUILDING = re.compile(r"APARTMENT|MULTIPLE UNIT|MIXED USE/RES|HOME FOR THE AGED|ROOMING|RESIDENTIAL", re.I)

_NEW_CONSTRUCTION_WORK = re.compile(r"^NEW BUILDING$|^PARTIAL PERMIT", re.I)
_NEW_CONSTRUCTION_TEXT = re.compile(r"\b(CONSTRUCT|ERECT)\w*\s+(A\s+)?NEW\s+(\d+[- ]STOREY|[\w-]+\s+STOREY)", re.I)
_DEMOLITION = re.compile(r"DEMOLITION", re.I)


def work_category(permit_type: str | None, work: str | None, description: str | None) -> str:
    """NEW_CONSTRUCTION / DEMOLITION on the site, or ALTERATION_OR_REPAIR of what is there."""
    if _DEMOLITION.search(permit_type or "") or _DEMOLITION.search(work or ""):
        return "DEMOLITION"
    if (permit_type or "").upper() == "NEW BUILDING" or _NEW_CONSTRUCTION_WORK.search((work or "").strip()) \
            or _NEW_CONSTRUCTION_TEXT.search(description or ""):
        return "NEW_CONSTRUCTION"
    return "ALTERATION_OR_REPAIR"


PERMIT_COLUMNS = [
    ("row_no", "int4"), ("permit_number", "text"), ("revision_number", "text"), ("permit_type", "text"),
    ("status", "text"), ("structure_type", "text"), ("work", "text"), ("work_category", "text"),
    ("description", "text"),
    ("current_use", "text"), ("proposed_use", "text"), ("application_date", "date"), ("issued_date", "date"),
    ("completed_date", "date"), ("est_const_cost", "numeric"), ("dwelling_units_created", "int4"),
    ("dwelling_units_lost", "int4"), ("street_num", "text"), ("street_name", "text"), ("street_type", "text"),
    ("street_direction", "text"), ("postal_fsa", "text"), ("geo_id", "text"), ("payload", "jsonb"),
]
COL = {name: i for i, (name, _) in enumerate(PERMIT_COLUMNS)}   # position of each column in a staged row
FIELDS = [c for c, _ in PERMIT_COLUMNS if c not in ("row_no", "permit_number", "revision_number", "permit_type",
                                                     "payload")]


def site_relation(structure_type: str | None, permit_type: str | None) -> str:
    """How the permitted work relates to the apartment building at that address."""
    st = structure_type or ""
    if (permit_type or "").upper() == "NEW HOUSES" or _OTHER_STRUCTURE.search(st):
        return "OTHER_STRUCTURE_ON_SITE"
    if _RESIDENTIAL_BUILDING.search(st):
        return "BUILDING"
    if _NON_RESIDENTIAL.search(st):
        return "NON_RESIDENTIAL_SPACE"
    return "BUILDING"   # blank, 'Other', 'Unknown': most permits at these addresses concern the building


def confidence(method: str, relation: str, candidates: int) -> tuple[str, bool]:
    """(match_confidence, accepted). An address shared by several buildings is never accepted."""
    if candidates > 1:
        return "LOW", False
    if method == "ADDRESS" and relation == "BUILDING":
        return "HIGH", True
    return "MEDIUM", True


def parse_cost(value) -> Decimal | None:
    """Dollars, rounded to cents as stored (numeric(14,2)); otherwise reruns would see a change."""
    if value is None:
        return None
    s = str(value).replace(",", "").replace("$", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        raise FieldError(f"not a cost: {value!r}")
    return Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def load_permits(conn: psycopg.Connection, raw: RawFile) -> ImportResult:
    run = ImportRun(conn, raw)
    try:
        with conn.transaction():
            return _load(conn, run, raw, SOURCE_FILE[raw.source.key])
    except Exception as e:  # noqa: BLE001 - every failure is recorded on the import row
        return run.fail(e)


def _clean(value) -> str | None:
    return value if value else None


def _load(conn: psycopg.Connection, run: ImportRun, raw: RawFile, source_file: str) -> ImportResult:
    df = read_source(raw.path)
    run.record_columns(list(df.columns))
    check_columns(df, REQUIRED, run.dataset)

    # Pass 1, every row: natural key, duplicates, address match keys.
    keys, row_key, seen = [], {}, set()
    cols = [df[c].tolist() for c in ("PERMIT_NUM", "REVISION_NUM", "PERMIT_TYPE", "STREET_NUM", "STREET_NAME",
                                     "STREET_TYPE", "STREET_DIRECTION")]
    for n, (num, rev, ptype, snum, name, stype, sdir) in enumerate(zip(*cols), start=1):
        if not num or not ptype:
            run.reject(n, "missing permit number or type", _row(df, n))
            continue
        natural = (num, (rev or "0").zfill(2), ptype)
        if natural in seen:
            run.reject(n, "duplicate (permit number, revision, type)", _row(df, n))
            continue
        seen.add(natural)
        row_key[n] = natural
        found = permit_match_keys(snum, name, stype, sdir)
        if not found:
            run.warnings.add("unmatchable_address")
        keys.extend((n, k, via_range) for k, via_range in found)

    conn.execute("CREATE TEMP TABLE stage_keys (row_no int4, match_key text, via_range bool) ON COMMIT DROP")
    copy_rows(conn, "stage_keys", ["row_no", "match_key", "via_range"], ["int4", "text", "bool"], keys)
    candidates: dict[int, list[tuple[int, str, bool]]] = defaultdict(list)
    for row_no, building_id, target, via_range in conn.execute(
            """SELECT DISTINCT ON (k.row_no, a.building_id) k.row_no, a.building_id, a.search_text, k.via_range
               FROM stage_keys k JOIN building_aliases a ON a.match_key = k.match_key
               ORDER BY k.row_no, a.building_id, k.via_range, a.search_text"""):
        candidates[row_no].append((building_id, target, via_range))

    # Pass 2, candidate rows only: full, typed permit rows.
    permit_rows = []
    for n in sorted(candidates):
        r = _row(df, n)
        number, rev, ptype = row_key[n]
        permit_rows.append((
            n, number, rev, ptype, _clean(r["STATUS"]), _clean(r["STRUCTURE_TYPE"]), _clean(r["WORK"]),
            work_category(ptype, r["WORK"], r["DESCRIPTION"]), _clean(r["DESCRIPTION"]), _clean(r["CURRENT_USE"]), _clean(r["PROPOSED_USE"]),
            _soft(run, parse_date, r["APPLICATION_DATE"], "invalid_application_date"),
            _soft(run, parse_date, r["ISSUED_DATE"], "invalid_issued_date"),
            _soft(run, parse_date, r["COMPLETED_DATE"], "invalid_completed_date"),
            _soft(run, parse_cost, r["EST_CONST_COST"], "non_numeric_est_const_cost"),
            _soft(run, parse_int, r["DWELLING_UNITS_CREATED"], "invalid_dwelling_units"),
            _soft(run, parse_int, r["DWELLING_UNITS_LOST"], "invalid_dwelling_units"),
            _clean(r["STREET_NUM"]), _clean(r["STREET_NAME"]), _clean(r["STREET_TYPE"]),
            _clean(r["STREET_DIRECTION"]), _clean(r["POSTAL"]), _clean(r["GEO_ID"]),
            payload({k: v for k, v in r.items() if k not in PRIVATE_COLUMNS}),
        ))

    conn.execute(f"""CREATE TEMP TABLE stage_permits ({', '.join(f'{c} {t}' for c, t in PERMIT_COLUMNS)})
                     ON COMMIT DROP""")
    copy_rows(conn, "stage_permits", [c for c, _ in PERMIT_COLUMNS], [t for _, t in PERMIT_COLUMNS], permit_rows)

    merged = conn.execute(
        f"""MERGE INTO permits p
            USING stage_permits s
            ON p.permit_number = s.permit_number AND p.revision_number = s.revision_number
               AND p.permit_type = s.permit_type
            WHEN MATCHED AND ({', '.join(f'p.{f}' for f in FIELDS)}, p.source_file, p.raw_payload)
                 IS DISTINCT FROM ({', '.join(f's.{f}' for f in FIELDS)}, %(src)s, s.payload) THEN
                UPDATE SET {', '.join(f'{f} = s.{f}' for f in FIELDS)}, source_file = %(src)s,
                           raw_payload = s.payload, updated_import_id = %(imp)s, updated_at = now()
            WHEN NOT MATCHED THEN
                INSERT (permit_number, revision_number, permit_type, {', '.join(FIELDS)}, source_file,
                        raw_payload, created_import_id, updated_import_id)
                VALUES (s.permit_number, s.revision_number, s.permit_type, {', '.join(f's.{f}' for f in FIELDS)},
                        %(src)s, s.payload, %(imp)s, %(imp)s)
            RETURNING merge_action(), s.row_no, old.status, old.source_file""",
        {"src": source_file, "imp": run.id},
    ).fetchall()
    actions = {row_no: (action, old_status, old_file) for action, row_no, old_status, old_file in merged}

    ids = dict(conn.execute(
        """SELECT s.row_no, p.id FROM stage_permits s JOIN permits p
             ON p.permit_number = s.permit_number AND p.revision_number = s.revision_number
            AND p.permit_type = s.permit_type""").fetchall())
    by_row = {row[0]: row for row in permit_rows}

    matches = []
    for n, cands in candidates.items():
        row = by_row[n]
        relation = site_relation(row[COL["structure_type"]], row[COL["permit_type"]])
        source_address = " ".join(row[COL[c]] for c in ("street_num", "street_name", "street_type",
                                                        "street_direction") if row[COL[c]])
        for building_id, target, via_range in cands:
            method = "PERMIT_RANGE" if via_range else "ADDRESS"
            conf, accepted = confidence(method, relation, len(cands))
            matches.append((ids[n], building_id, method, conf, relation, accepted, source_address, target))
        if len(cands) > 1:
            run.warnings.add("ambiguous_address_not_attached")
    _save_matches(conn, run, matches)

    if not run.is_baseline:
        _record_changes(run, candidates, actions, ids, by_row, source_file)

    (vanished,) = conn.execute(
        """SELECT count(*) FROM permits p WHERE p.source_file = %s
           AND NOT EXISTS (SELECT 1 FROM stage_permits s WHERE s.permit_number = p.permit_number
                           AND s.revision_number = p.revision_number AND s.permit_type = p.permit_type)""",
        (source_file,),
    ).fetchone()
    if vanished:
        # Usually an active permit that has since moved to the cleared file; kept, not deleted.
        run.warnings.add("permits_no_longer_in_this_file", vanished)

    run.save_rejections()
    inserted = sum(1 for a, _, _ in actions.values() if a == "INSERT")
    updated = len(actions) - inserted
    skipped = len(row_key) - len(candidates)
    return run.complete(len(df), inserted, updated, skipped)


def _row(df, n: int) -> dict:
    return {k: (v if v != "" else None) for k, v in df.iloc[n - 1].to_dict().items()}


def _soft(run: ImportRun, parser, value, kind: str):
    try:
        return parser(value)
    except FieldError:
        run.warnings.add(kind)
        return None


def _save_matches(conn: psycopg.Connection, run: ImportRun, matches: list[tuple]) -> None:
    cols = [("permit_id", "int8"), ("building_id", "int8"), ("match_method", "text"), ("match_confidence", "text"),
            ("site_relation", "text"), ("accepted", "bool"), ("source_address", "text"), ("target_address", "text")]
    conn.execute(f"CREATE TEMP TABLE stage_matches ({', '.join(f'{c} {t}' for c, t in cols)}) ON COMMIT DROP")
    copy_rows(conn, "stage_matches", [c for c, _ in cols], [t for _, t in cols], matches)
    names = [c for c, _ in cols]
    conn.execute(
        f"""INSERT INTO permit_matches ({', '.join(names)}, import_id)
            SELECT {', '.join(names)}, %(imp)s FROM stage_matches
            ON CONFLICT (permit_id, building_id) DO UPDATE SET
                {', '.join(f'{c} = excluded.{c}' for c in names[2:])}, import_id = excluded.import_id,
                matched_at = now()
            WHERE ({', '.join(f'permit_matches.{c}' for c in names[2:])})
                  IS DISTINCT FROM ({', '.join(f'excluded.{c}' for c in names[2:])})""",
        {"imp": run.id},
    )
    # A permit's candidate set can shrink if a building alias is corrected; drop stale matches.
    conn.execute("""DELETE FROM permit_matches m
                    WHERE m.permit_id IN (SELECT permit_id FROM stage_matches)
                      AND NOT EXISTS (SELECT 1 FROM stage_matches s
                                      WHERE s.permit_id = m.permit_id AND s.building_id = m.building_id)""")


def _record_changes(run, candidates, actions, ids, by_row, source_file) -> None:
    for n, (action, old_status, old_file) in actions.items():
        cands = candidates[n]
        if len(cands) != 1:
            continue   # not attached to a building, so not news for any building
        building_id = cands[0][0]
        row = by_row[n]
        number, ptype, status = row[COL["permit_number"]], row[COL["permit_type"]], row[COL["status"]]
        if action == "INSERT":
            when = row[COL["application_date"]] or row[COL["issued_date"]]
            what = (row[COL["description"]] or "").strip()
            summary = f"{ptype} permit {number} ({status})" + (f", applied {when}" if when else "")
            if what:
                summary += f": {what[:120]}"
            run.change(building_id, "permit", ids[n], "new_permit", summary)
        elif old_file == "ACTIVE" and source_file == "CLEARED":
            run.change(building_id, "permit", ids[n], "permit_cleared", f"{ptype} permit {number} closed ({status})")
        elif old_status != status:
            run.change(building_id, "permit", ids[n], "permit_status_changed",
                       f"{ptype} permit {number}: {old_status} -> {status}")
