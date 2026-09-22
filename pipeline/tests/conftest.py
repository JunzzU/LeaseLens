import csv
import hashlib
import os
from pathlib import Path

import psycopg
import pytest

from leaselens_pipeline.db import migration_files
from leaselens_pipeline.download.fetch import SOURCES, RawFile

TEST_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://localhost:5432/leaselens_test")


@pytest.fixture(scope="session")
def test_db_url():
    admin_url = TEST_URL.rsplit("/", 1)[0] + "/postgres"
    name = TEST_URL.rsplit("/", 1)[1]
    try:
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=3) as admin:
            if not admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
                admin.execute(f'CREATE DATABASE "{name}"')
    except psycopg.OperationalError as e:
        pytest.skip(f"PostgreSQL not available: {e}")
    return TEST_URL


@pytest.fixture
def conn(test_db_url):
    """A freshly migrated, empty schema for every test."""
    with psycopg.connect(test_db_url, autocommit=True) as c:
        c.execute("DROP SCHEMA public CASCADE")
        c.execute("CREATE SCHEMA public")
        for _, path in migration_files():   # what Flyway would apply, without needing the JVM
            c.execute(path.read_text())
        yield c


@pytest.fixture
def raw_file(tmp_path):
    """Write rows to a CSV and wrap it as a RawFile for the given source key."""
    counter = iter(range(1_000_000))

    def make(source_key: str, rows: list[dict]) -> RawFile:
        path = tmp_path / f"{source_key}-{next(counter)}.csv"
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return RawFile(SOURCES[source_key], Path(path), digest, "test", "file://" + str(path))

    return make


def registration_row(rsn, address, storeys="10", units="100", **extra):
    return {"_id": rsn, "RSN": rsn, "SITE_ADDRESS": address, "CONFIRMED_STOREYS": storeys,
            "CONFIRMED_UNITS": units, "PROPERTY_TYPE": "PRIVATE", "WARD": "13", "YEAR_BUILT": "1965",
            "YEAR_REGISTERED": "2017", "PCODE": "M5A", **extra}


def v2023_row(rsn, address, date, score, lat="43.66", lon="-79.37"):
    return {"_id": "1", "RSN": rsn, "SITE ADDRESS": address, "EVALUATION COMPLETED ON": date,
            "CURRENT BUILDING EVAL SCORE": score, "PROACTIVE BUILDING SCORE": score,
            "CURRENT REACTIVE SCORE": "0", "NO OF AREAS EVALUATED": "45", "WARD": "13",
            "WARDNAME": "Toronto Centre", "CONFIRMED STOREYS": "10", "CONFIRMED UNITS": "100",
            "YEAR BUILT": "1965", "YEAR REGISTERED": "2017", "PROPERTY TYPE": "PRIVATE",
            "LATITUDE": lat, "LONGITUDE": lon}


def permit_row(num, street_num, street_name, street_type="AVE", direction="", status="Inspection",
               permit_type="Building Additions/Alterations", structure="Apartment Building", **extra):
    return {"_id": "1", "PERMIT_NUM": num, "REVISION_NUM": "0", "PERMIT_TYPE": permit_type,
            "STRUCTURE_TYPE": structure, "WORK": "Balcony/Guard Repairs", "STREET_NUM": street_num,
            "STREET_NAME": street_name, "STREET_TYPE": street_type, "STREET_DIRECTION": direction,
            "POSTAL": "M5A", "GEO_ID": "123", "WARD_GRID": "S1", "APPLICATION_DATE": "2025-01-15",
            "ISSUED_DATE": "2025-03-01", "COMPLETED_DATE": "", "STATUS": status,
            "DESCRIPTION": "Balcony slab repairs", "CURRENT_USE": "Apartment", "PROPOSED_USE": "Apartment",
            "DWELLING_UNITS_CREATED": "", "DWELLING_UNITS_LOST": "", "EST_CONST_COST": "25000",
            "BUILDER_NAME": "JANE PRIVATEPERSON", **extra}
