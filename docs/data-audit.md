# Data Audit — Week 1

Audit date: 2026-09-17. All figures are reproducible with `python pipeline/src/audit/run_audit.py`.

## Sources

| Dataset (Toronto Open Data) | File used | Rows | Portal refreshed |
|---|---|---|---|
| Apartment Building Evaluation | 2023 – current | 6,602 | 2026-09-17 |
| Apartment Building Evaluation | Pre-2023 | 11,760 | frozen (2017-09 → 2023-05) |
| Apartment Building Registration | Registration Data | 3,611 | 2026-07-05 |
| Building Permits – Active | active permits | 205,672 | 2026-09-17 |
| Building Permits – Cleared | cleared since 2017 | 437,412 | 2026-09-17 |

Not yet used: Cleared Permits 2000–2016 (separate file), Neighbourhoods boundaries, Investigation Activity (no machine-readable source; link out only).

## Key findings and decisions

### 1. Two incompatible evaluation scoring systems (blocking issue)

| | Pre-2023 | 2023 – current |
|---|---|---|
| Item scale | 1–5 | 0–3 |
| Items | ~20 | ~50 |
| Median score | 74 | 91 |

3,447 buildings have evaluations in both eras. A naive trend would show most of them "improving" by roughly 17 points just because of the methodology change.

**Decision:** add `scoring_version` (`PRE_2023`, `V2023`) to `evaluations`. Compute deltas, trends, and percentiles only within one version. The UI shows a visible break in the evaluation chart at June 2023. `CURRENT REACTIVE SCORE` is 0 in every row; ignore it for now.

### 2. RSN is a stable building ID across the RentSafeTO datasets

`RSN` joins registration and both evaluation files, so no address matching is needed between them. Details:

- 60 evaluated RSNs are missing from registration (probably deregistered). Keep them with `rentsafe_registered = false`.
- 17 registered RSNs have no evaluations.
- 7 rows contain `** CREATED IN ERROR **` in the address. Reject these and count them in the import report.
- 5 duplicate `(RSN, date)` pairs in pre-2023. Natural key: `(RSN, evaluation_date, scoring_version)`. Keep the first row and log the rest.

**Decision:** `buildings.source_building_id = RSN`. Do not use the portal `_id` as a key.

### 3. Registration quirks

- The duplicate column pairs `NO_OF_STOREYS` and `NO_OF_UNITS` are 100% null. Use `CONFIRMED_STOREYS` and `CONFIRMED_UNITS`.
- Registration has no coordinates. Take lat/lon from evaluation rows; 225 of the 2023+ rows lack them, so geocode those later via permit `GEO_ID` or the address.
- `PROPERTY_TYPE` is PRIVATE 3,039, TCHC 328, SOCIAL HOUSING 241. This should be a comparison-group filter.
- 61 addresses are ranges, such as `85-95 THORNCLIFFE PARK DR`. Expand them into `building_aliases`, stepping by 2 for same-side numbering.
- Addresses contain double spaces and trailing spaces, so always collapse whitespace.

### 4. Permit identity requires PERMIT_TYPE

- `REVISION_NUM` is formatted inconsistently (`0` vs `00`). Normalize with `zfill(2)`.
- `(PERMIT_NUM, REVISION_NUM)` is not unique: 3,945 duplicates. The same number appears as e.g. "New Houses" and "Conditional Permit".
- Including `PERMIT_TYPE` reduces duplicates to 24, which should be logged and rejected.
- With that key, zero permits appear in both active and cleared. A permit moving between datasets is therefore a status transition, detected by key across imports.

**Decision:** permit natural key = `(permit_number, revision_number, permit_type)`, with a unique index on it.

### 5. Permit address data

- `STREET_NUM` is non-numeric in about 18k rows: `359 1/2`, `58 A`, `273-275`, `1593 B-1615 B`. Parse it into `num_low`, `num_high`, `suffix`.
- `GEO_ID` is missing in about 15k rows, so it can't be the only match key.
- `ISSUED_DATE` is missing in about 50k rows (not yet issued, or cancelled). The timeline must use the application date as a fallback and label it.
- `EST_CONST_COST` contains junk text, e.g. "DO NOT UPDATE OR DELETE THIS INFO FIELD". Parse it as numeric or null.

### 6. Registration → permit matching baseline

A simple normalized `number|street name type direction` key already gives:

| Result | Buildings |
|---|---|
| Exact match on first address number | 2,683 (74%) |
| Match only after range expansion | 7 |
| No permit found | 921 (26%) |

Spot checks of the unmatched addresses (e.g. 260 Sherbourne St, 2419 Keele St) found no nearby permit numbers, so most look like genuine "no permits since 2017" cases rather than matching failures. The permit types matched are plausible: Additions/Alterations, Plumbing, Mechanical, Fire/Security Upgrade. However, 348 matched rows are "New Houses," which needs review; filter or flag by `STRUCTURE_TYPE`.

**Next:** build a hand-labelled test set of about 50 buildings to measure precision, not just match rate. This feeds the 90%-correct success metric.

### 7. Comparison groups are too small at the planned granularity

Test: 2023+ scores only, same ward, units ±25%, storeys ±3.

| Peers per building | Value |
|---|---|
| Median | 22 |
| 25th percentile | 9 |
| Share with fewer than 15 peers | 35% |

That's with 25 wards; the 158 neighbourhoods would be far smaller. Evaluations also have no neighbourhood field, so neighbourhood matching needs a PostGIS point-in-polygon join.

**Decision:** start with ward. Widen to adjacent wards, then to units ±50%. Suppress the percentile below 15 peers. Show the rule used on the page. Also consider k-nearest-neighbours by distance as a later alternative.

## Schema changes from this audit

- `evaluations`: add `scoring_version`; unique `(building_id, evaluation_date, scoring_version)`.
- `permits`: add `num_low`, `num_high`, `num_suffix`, `geo_id`, `match_method`, `match_confidence`; unique `(permit_number, revision_number, permit_type)`.
- `buildings`: add `property_type`, `ward`, `year_built`.
