# LeaseLens Toronto

Look up a Toronto apartment building before you sign a lease: RentSafeTO evaluation history, building permits, and a unified timeline, built from City of Toronto open data with the source and freshness of every record shown.

**Status:** Week 2 — RentSafeTO registration and evaluations load into PostgreSQL with a repeatable, idempotent import. See [`docs/data-quality-week2.md`](docs/data-quality-week2.md) and the Week 1 [`docs/data-audit.md`](docs/data-audit.md).

The website comes first; a mobile app follows. All business logic lives in the API so both clients share it.

## Stack
Python ETL · PostgreSQL/PostGIS · Spring Boot API · Next.js frontend

## Local setup (macOS)

Requires Python 3.11+ and **PostgreSQL 18+ with PostGIS** ([Postgres.app](https://postgresapp.com) includes both). PostgreSQL 18 is required because the import uses `MERGE ... RETURNING old.*`.

```bash
createdb leaselens
python3 -m venv pipeline/.venv
pipeline/.venv/bin/pip install -e "pipeline[dev]"
```

## Load the data

```bash
pipeline/.venv/bin/leaselens-pipeline import rentsafe   # download + load; safe to rerun
pipeline/.venv/bin/leaselens-pipeline report            # data-quality summary (Markdown)
```

Raw files are kept untouched under `raw/<dataset>/<date>/` (gitignored). The database defaults to `postgresql://localhost:5432/leaselens`; override with `DATABASE_URL`.

## Tests

```bash
pipeline/.venv/bin/pytest pipeline
```

Import tests create and reset a separate `leaselens_test` database (`TEST_DATABASE_URL`), and are skipped if PostgreSQL isn't running. Address-normalization cases live in [`testdata/address-normalization-cases.json`](testdata/address-normalization-cases.json), which the Java backend will also test against.

## Week 1 data audit
```bash
pip install -r pipeline/requirements.txt
python pipeline/src/audit/run_audit.py   # downloads ~220 MB into ./raw (gitignored)
```

## Layout
```
pipeline/   Python ingestion: download, validation, normalization, loading
backend/    Spring Boot REST API
frontend/   Next.js app
database/   SQL migrations (Flyway naming)
testdata/   test cases shared between Python and Java
docs/       audit, data quality, methodology, limitations
```

## Data licence
Contains information licensed under the Open Government Licence – Toronto. LeaseLens Toronto is an independent project and is not affiliated with or endorsed by the City of Toronto.
