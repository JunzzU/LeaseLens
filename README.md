# LeaseLens Toronto

Look up a Toronto apartment building before you sign a lease: RentSafeTO evaluation history, building permits, and a unified timeline, built from City of Toronto open data with the source and freshness of every record shown.

**Status:** Week 4 — building profiles with permit records. City building permits are matched to RentSafeTO buildings by address, with the evidence and confidence of every match stored. See [`docs/matching-methodology.md`](docs/matching-methodology.md), [`docs/data-quality-week4.md`](docs/data-quality-week4.md) and the Week 1 [`docs/data-audit.md`](docs/data-audit.md).

The website comes first; a mobile app follows. All business logic lives in the API so both clients share it.

## Stack
Python ETL · PostgreSQL/PostGIS · Spring Boot API · Next.js frontend

## Local setup (macOS)

Requires Java 25, Python 3.11+ and **PostgreSQL 18+ with PostGIS** ([Postgres.app](https://postgresapp.com) includes both). PostgreSQL 18 is required because the import uses `MERGE ... RETURNING old.*`.

```bash
createdb leaselens
createdb leaselens_api_test
python3 -m venv pipeline/.venv
pipeline/.venv/bin/pip install -e "pipeline[dev]"
```

## Run it

1. **Start the API.** On startup Flyway applies `database/migrations`; the backend owns the schema.
   ```bash
   cd backend && ./mvnw spring-boot:run
   ```
2. **Load the data** (in another terminal). The pipeline checks the schema is current and refuses to run otherwise.
   ```bash
   pipeline/.venv/bin/leaselens-pipeline import all        # RentSafeTO, then permits (~15 s); safe to rerun
   pipeline/.venv/bin/leaselens-pipeline report            # data-quality summary (Markdown)
   ```
3. **Try it:** http://localhost:8080/swagger-ui.html, or
   ```bash
   curl "http://localhost:8080/api/v1/buildings/search?q=181+gerrard+st+e"
   ```

Raw files are kept untouched under `raw/<dataset>/<date>/` (gitignored; ~230 MB with permits). Configuration is via environment variables: `DATABASE_URL` (pipeline), `LEASELENS_DB_URL` / `LEASELENS_DB_USER` / `LEASELENS_DB_PASSWORD` and `LEASELENS_CORS_ORIGINS` (backend).

## API (v1)

| Endpoint | Returns |
|---|---|
| `GET /api/v1/buildings/search?q=&limit=` | Candidate buildings plus `matchType` (`ADDRESS`, `PREFIX`, `STREET`, `FUZZY`, `NONE`) and `ambiguous`. Never a silent single guess. |
| `GET /api/v1/buildings/{id}` | Profile: details, evaluation summary (change is only computed within one scoring version), permit counts, coverage-note codes, source freshness |
| `GET /api/v1/buildings/{id}/evaluations` | All evaluations, newest first |
| `GET /api/v1/buildings/{id}/permits?status=active\|cleared\|all&limit=&offset=` | Attached permits, newest activity first, each with match evidence, `workCategory` and `predatesBuilding` |
| `GET /v3/api-docs` | OpenAPI 3.1 description, used to generate client types for the website and the app |

Errors are RFC 9457 problem details. `/api/v1` changes are additive only, because installed app versions can't be forced to update.

## Tests

```bash
pipeline/.venv/bin/pytest pipeline     # pipeline: unit + import tests (database leaselens_test)
cd backend && ./mvnw test             # backend: unit + HTTP tests (database leaselens_api_test)
```

Database tests rebuild their schema from the migrations on every run. Address-normalization cases live in [`testdata/address-normalization-cases.json`](testdata/address-normalization-cases.json), and both the Python and the Java normalizer must pass them.

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
database/   SQL migrations (applied by Flyway in the backend)
testdata/   test cases shared between Python and Java
docs/       audit, data quality, methodology, limitations
```

## Data licence
Contains information licensed under the Open Government Licence – Toronto. LeaseLens Toronto is an independent project and is not affiliated with or endorsed by the City of Toronto.
