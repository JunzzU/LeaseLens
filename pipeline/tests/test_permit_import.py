"""Permit import against a real PostgreSQL database (skipped when none is running)."""
import pytest

from leaselens_pipeline.loading.permits import load_permits
from leaselens_pipeline.loading.registration import load_registration

from .conftest import permit_row, registration_row

pytestmark = pytest.mark.db

REGISTRATION = [
    registration_row("1001", "181-183 GERRARD ST E"),
    registration_row("1002", "339 THE WEST MALL"),
    registration_row("1003", "33 FLAMBOROUGH DR UNIT B"),
    registration_row("1004", "33 FLAMBOROUGH DR UNIT C"),
    registration_row("1005", "2727 VICTORIA PARK AVE"),
]
ACTIVE = [
    permit_row("25 000001 BLD", "183", "GERRARD", "ST", "E"),               # second number of a range
    permit_row("25 000002 BLD", "339", "THE WEST MALL", ""),                # City splits name/type differently
    permit_row("25 000003 BLD", "33", "FLAMBOROUGH", "DR"),                 # address shared by two buildings
    permit_row("25 000004 BLD", "2721-2729", "VICTORIA PARK"),              # permit range covers the building
    permit_row("25 000005 BLD", "2727", "VICTORIA PARK", structure="Retail Store"),
    permit_row("25 000006 BLD", "10", "ELSEWHERE", "RD"),                   # not a RentSafeTO building
    permit_row("25 000001 BLD", "183", "GERRARD", "ST", "E"),               # duplicate key
]


def matches(conn):
    return {r[0]: r[1:] for r in conn.execute(
        """SELECT p.permit_number || '/' || b.source_building_id, m.match_method, m.match_confidence,
                  m.site_relation, m.accepted
           FROM permit_matches m JOIN permits p ON p.id = m.permit_id JOIN buildings b ON b.id = m.building_id""")}


def test_matching_methods_and_confidence(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    result = load_permits(conn, raw_file("permits_active", ACTIVE))

    assert (result.inserted, result.skipped, result.rejected) == (5, 1, 1)
    assert matches(conn) == {
        "25 000001 BLD/1001": ("ADDRESS", "HIGH", "BUILDING", True),
        "25 000002 BLD/1002": ("ADDRESS", "HIGH", "BUILDING", True),
        "25 000003 BLD/1003": ("ADDRESS", "LOW", "BUILDING", False),
        "25 000003 BLD/1004": ("ADDRESS", "LOW", "BUILDING", False),
        "25 000004 BLD/1005": ("PERMIT_RANGE", "MEDIUM", "BUILDING", True),
        "25 000005 BLD/1005": ("ADDRESS", "MEDIUM", "NON_RESIDENTIAL_SPACE", True),
    }


def test_rerun_changes_nothing(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    permits = raw_file("permits_active", ACTIVE)
    load_permits(conn, permits)
    before = matches(conn)
    again = load_permits(conn, permits)

    assert (again.inserted, again.updated, again.unchanged) == (0, 0, 5)
    assert matches(conn) == before


def test_builder_names_are_not_stored(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    load_permits(conn, raw_file("permits_active", ACTIVE))

    assert conn.execute("SELECT count(*) FROM permits WHERE raw_payload ? 'BUILDER_NAME'").fetchone() == (0,)
    assert conn.execute("SELECT count(*) FROM permits WHERE raw_payload::text LIKE '%PRIVATEPERSON%'"
                        ).fetchone() == (0,)


def test_permit_moving_to_cleared_file_is_a_status_change(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    load_permits(conn, raw_file("permits_active", ACTIVE))
    load_permits(conn, raw_file("permits_cleared", [permit_row("99 999999 BLD", "1", "NOWHERE")]))  # baseline

    cleared = [permit_row("25 000001 BLD", "183", "GERRARD", "ST", "E", status="Closed", COMPLETED_DATE="2026-08-01")]
    result = load_permits(conn, raw_file("permits_cleared", cleared))

    assert (result.inserted, result.updated) == (0, 1)
    row = conn.execute("""SELECT source_file, status, completed_date::text FROM permits
                          WHERE permit_number = '25 000001 BLD'""").fetchone()
    assert row == ("CLEARED", "Closed", "2026-08-01")
    assert conn.execute("SELECT change_type, change_summary FROM building_changes").fetchall() == [
        ("permit_cleared", "Building Additions/Alterations permit 25 000001 BLD closed (Closed)")]


def test_new_permits_after_baseline_are_changes_only_when_attached(conn, raw_file):
    load_registration(conn, raw_file("registration", REGISTRATION))
    load_permits(conn, raw_file("permits_active", ACTIVE))
    more = ACTIVE[:-1] + [permit_row("26 000007 PLB", "181", "GERRARD", "ST", "E", permit_type="Plumbing(PS)"),
                          permit_row("26 000008 PLB", "33", "FLAMBOROUGH", "DR", permit_type="Plumbing(PS)")]
    load_permits(conn, raw_file("permits_active", more))

    changes = conn.execute("""SELECT b.source_building_id, c.change_type FROM building_changes c
                              JOIN buildings b ON b.id = c.building_id""").fetchall()
    assert changes == [("1001", "new_permit")]   # the shared-address permit is not news for either building
