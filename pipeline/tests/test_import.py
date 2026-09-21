"""Import behaviour against a real PostgreSQL database (skipped when none is running)."""
import pytest

from leaselens_pipeline.loading.evaluations import load_evaluations
from leaselens_pipeline.loading.registration import load_registration

from .conftest import registration_row, v2023_row

pytestmark = pytest.mark.db

REGISTRATION = [
    registration_row("1001", "181-183  GERRARD ST E "),
    registration_row("1002", "2727 VICTORIA PARK AVE"),
    registration_row("1003", "145 ST GEORGE ST"),
    registration_row("1004", "40 LOWER RIVER ST."),
    registration_row("1005", "289 THE KINGSWAY"),
]
EVALUATIONS = [
    v2023_row("1001", "181-183 GERRARD ST E", "2024-03-08", "78"),
    v2023_row("1001", "181-183 GERRARD ST E", "2026-06-12", "84"),
    v2023_row("1002", "2727 VICTORIA PARK AVE", "2024-09-16", "95"),
    v2023_row("9999", "10 NOT REGISTERED RD", "2025-01-10", "70"),   # evaluated, not registered
]


def counts(conn):
    return {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("buildings", "building_aliases", "evaluations", "building_changes")}


def test_rerunning_an_import_changes_nothing(conn, raw_file):
    reg, ev = raw_file("registration", REGISTRATION), raw_file("evaluations_v2023", EVALUATIONS)
    first = (load_registration(conn, reg), load_evaluations(conn, ev))
    after_first = counts(conn)
    second = (load_registration(conn, reg), load_evaluations(conn, ev))

    assert [r.inserted for r in first] == [5, 4]
    assert [(r.inserted, r.updated, r.unchanged) for r in second] == [(0, 0, 5), (0, 0, 4)]
    assert counts(conn) == after_first
    assert after_first["building_changes"] == 0   # the first load is a baseline, not "news"


def test_building_details_and_location(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    load_evaluations(conn, raw_file("evaluations_v2023", EVALUATIONS))

    row = conn.execute("""SELECT address, normalized_address, rentsafe_registered, ward_name,
                                 ST_Y(geom::geometry), ST_X(geom::geometry)
                          FROM buildings WHERE source_building_id = '1001'""").fetchone()
    assert row == ("181-183 GERRARD ST E", "181|GERRARD|ST|E", True, "Toronto Centre", 43.66, -79.37)
    aliases = {a for (a,) in conn.execute("""SELECT search_text FROM building_aliases a
                                             JOIN buildings b ON b.id = a.building_id
                                             WHERE b.source_building_id = '1001'""")}
    assert aliases == {"181 GERRARD ST E", "183 GERRARD ST E"}
    assert conn.execute("SELECT rentsafe_registered FROM buildings WHERE source_building_id = '9999'"
                        ).fetchone() == (False,)


def test_new_and_revised_evaluations_are_recorded_as_changes(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    load_evaluations(conn, raw_file("evaluations_v2023", EVALUATIONS))

    revised = [dict(r) for r in EVALUATIONS]
    revised[2]["CURRENT BUILDING EVAL SCORE"] = "91"                           # score corrected
    revised.append(v2023_row("1003", "145 ST GEORGE ST", "2026-08-01", "88"))  # new evaluation
    result = load_evaluations(conn, raw_file("evaluations_v2023", revised))

    assert (result.inserted, result.updated, result.unchanged) == (1, 1, 3)
    changes = set(conn.execute("SELECT change_type, change_summary FROM building_changes").fetchall())
    assert changes == {
        ("new_evaluation", "Evaluation recorded on 2026-08-01: score 88 (2023+ scoring)"),
        ("evaluation_changed", "Evaluation of 2024-09-16 revised: score 95 -> 91 (2023+ scoring)"),
    }


def test_failed_import_leaves_existing_data_untouched(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    load_evaluations(conn, raw_file("evaluations_v2023", EVALUATIONS))
    before = counts(conn)

    broken = [{k: v for k, v in r.items() if k != "CURRENT BUILDING EVAL SCORE"} for r in EVALUATIONS]
    result = load_evaluations(conn, raw_file("evaluations_v2023", broken))

    assert result.status == "failed"
    assert "CURRENT BUILDING EVAL SCORE" in result.error
    assert counts(conn) == before
    assert conn.execute("SELECT status, error_summary IS NOT NULL FROM data_imports WHERE id = %s",
                        (result.import_id,)).fetchone() == ("failed", True)


def test_bad_rows_are_rejected_with_a_reason(conn, raw_file):
    rows = REGISTRATION + [
        registration_row("1001", "999 DUPLICATE ST"),
        registration_row("1006", "** CREATED IN ERROR ** 399 THE WEST MALL"),
        registration_row("ABC", "1 BAD RSN AVE"),
        registration_row("1007", "NO NUMBER RD"),
    ]
    result = load_registration(conn, raw_file("registration", rows))

    assert (result.inserted, result.rejected, result.status) == (5, 4, "completed_with_warnings")
    reasons = {r for (r,) in conn.execute("SELECT reason FROM import_rejections")}
    assert reasons == {"duplicate RSN", "address marked CREATED IN ERROR", "invalid RSN: 'ABC'",
                       "no civic number in 'NO NUMBER RD'"}


def test_buildings_leaving_registration_are_deregistered_not_deleted(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    result = load_registration(conn, raw_file("registration", REGISTRATION[:4]))

    assert result.warnings["deregistered_buildings"] == 1
    assert conn.execute("SELECT rentsafe_registered FROM buildings WHERE source_building_id = '1005'"
                        ).fetchone() == (False,)
    assert conn.execute("SELECT change_type FROM building_changes").fetchall() == [("deregistered",)]


def test_truncated_registration_file_is_refused(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    result = load_registration(conn, raw_file("registration", REGISTRATION[:1]))

    assert result.status == "failed"
    assert conn.execute("SELECT count(*) FROM buildings WHERE rentsafe_registered").fetchone() == (5,)


def test_new_source_columns_are_reported(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    with_extra = [dict(r, NEW_CITY_FIELD="x") for r in REGISTRATION]
    result = load_registration(conn, raw_file("registration", with_extra))

    assert result.warnings["columns_added"] == "NEW_CITY_FIELD"
