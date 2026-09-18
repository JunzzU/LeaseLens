# LeaseLens Toronto

Look up a Toronto apartment building before you sign a lease: RentSafeTO evaluation history, building permits, and a unified timeline, built from City of Toronto open data with the source and freshness of every record shown.

**Status:** Week 1 — data audit complete. See [`docs/data-audit.md`](docs/data-audit.md).

## Stack
Python ETL · PostgreSQL/PostGIS · Spring Boot API · Next.js frontend

## Run the data audit
```bash
pip install -r pipeline/requirements.txt
python pipeline/src/audit/run_audit.py   # downloads ~220 MB into ./raw (gitignored)
```

## Layout
```
pipeline/   Python ingestion, validation, matching
backend/    Spring Boot REST API
frontend/   Next.js app
database/   migrations
docs/       audit, methodology, limitations
```

## Data licence
Contains information licensed under the Open Government Licence – Toronto. LeaseLens Toronto is an independent project and is not affiliated with or endorsed by the City of Toronto.
