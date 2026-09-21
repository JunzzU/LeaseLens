# Data Quality Report — Week 2

Generated 2026-09-21 by `leaselens-pipeline report` after loading all three RentSafeTO files into a fresh database, then running the import again to confirm it is idempotent. Regenerate at any time with the same command.

## What changed since the Week 1 audit

- **The 2023+ evaluation file grew from 6,602 to 6,674 rows** between Sept 17 and Sept 21. The latest evaluation is dated 2026-09-19, so the file is updated continuously. Change detection depends on this.
- **Addresses shared by more than one building: 64 civic addresses map to 2–4 RSNs.** Examples: the registration range `1625-1641 KINGSTON RD` covers three separately registered buildings; `33 FLAMBOROUGH DR` has Units B, C, D and an unlettered building. Search must show all candidates and let the user choose; it must never pick one.
- **Duplicate evaluations:** the audit's 5 duplicate `(RSN, date)` pairs are now 2. The other 3 were `CREATED IN ERROR` rows, which are rejected first.
- **One 2023+ score is a decimal** (`81.1`, 8 Tree Sparroway, 2023-07-26). It is rounded to 81 with a warning. The original stays in `raw_payload`.
- **The registration file has 16 never-evaluated buildings**, not 17 (the audit counted one `CREATED IN ERROR` RSN).
- **Missing postal FSA: 135** (75 registrations with a blank `PCODE`, 1 invalid (`M53`), and 59 buildings known only from evaluations, which have no postal field). Postal code is not used for matching, so this is cosmetic.

## How the import behaves

| Property | How it's guaranteed | Test |
|---|---|---|
| Rerunning changes nothing | `MERGE` on natural keys (RSN; building + date + scoring version) with `IS DISTINCT FROM`, so unchanged rows are not rewritten | `test_rerunning_an_import_changes_nothing` |
| A failed import leaves data untouched | Each file loads in one transaction; only the `data_imports` row is written outside it, so the failure is still recorded | `test_failed_import_leaves_existing_data_untouched` |
| Schema changes are caught | Required columns missing → import fails; new columns → `columns_added` warning | `test_new_source_columns_are_reported` |
| Every rejected row is explainable | Stored in `import_rejections` with reason and the original row | `test_bad_rows_are_rejected_with_a_reason` |
| Buildings are never deleted | A building missing from registration becomes `rentsafe_registered = false` and a `deregistered` change is logged. The import refuses to proceed if the file would deregister more than 20% of buildings | `test_buildings_leaving_registration_are_deregistered_not_deleted`, `test_truncated_registration_file_is_refused` |
| New and revised evaluations become change events | Written to `building_changes`, except on a dataset's first load (the baseline) | `test_new_and_revised_evaluations_are_recorded_as_changes` |

The portal `_id` column is excluded from comparisons because the portal regenerates it on refresh. Evaluation coordinates are validated against a bounding box around Toronto; a building's location is taken from its most recent evaluation that has coordinates.

---

## Latest import per dataset

| Dataset | Import | Status | Source version | Completed | Records | Inserted | Updated | Unchanged | Rejected |
|---|---|---|---|---|---|---|---|---|---|
| evaluations_pre2023 | 8 | completed_with_warnings | 2026-02-20T17:41:23.374212 | 2026-09-21 15:08 | 11,760 | 0 | 0 | 11,751 | 9 |
| evaluations_v2023 | 9 | completed_with_warnings | 2026-09-21T09:34:52.393280 | 2026-09-21 15:08 | 6,674 | 1 | 0 | 6,673 | 0 |
| registration | 7 | completed_with_warnings | 2026-07-05T09:00:19.147056 | 2026-09-21 15:08 | 3,611 | 0 | 0 | 3,611 | 0 |

## Buildings

| Measure | Count |
|---|---|
| Buildings | 3,670 |
| Registered in RentSafeTO | 3,611 |
| Evaluated but not in registration (kept, rentsafe_registered = false) | 59 |
| With coordinates | 3,548 |
| Missing storeys or units | 6 |
| Missing postal FSA | 135 |
| Address is a range (e.g. 85-95) | 61 |
| Registered but never evaluated | 16 |
| Address aliases (one per civic number) | 3,895 |

| Property type | Buildings |
|---|---|
| PRIVATE | 3,075 |
| TCHC | 340 |
| SOCIAL HOUSING | 252 |
| (missing) | 3 |

## Evaluations

| Scoring version | Evaluations | Buildings | First | Latest | Median score |
|---|---|---|---|---|---|
| PRE_2023 | 11,751 | 3,512 | 2017-09-13 | 2023-02-24 | 74 |
| V2023 | 6,674 | 3,588 | 2023-06-05 | 2026-09-19 | 91 |

Buildings evaluated under both scoring versions: 3,446. Their scores are not comparable across versions, so trends are computed within one version only.

## Rejected rows (latest import)

| Dataset | Reason | Rows |
|---|---|---|
| evaluations_pre2023 | address marked CREATED IN ERROR | 7 |
| evaluations_pre2023 | duplicate (RSN, evaluation date) | 2 |

## Warnings (latest import)

| Dataset | Warnings |
|---|---|
| evaluations_pre2023 | missing_coordinates: 231 |
| evaluations_v2023 | decimal_score_rounded: 1, missing_coordinates: 226 |
| registration | invalid_postal_fsa: 1, invalid_storeys: 6, invalid_units: 6 |

## Addresses shared by more than one building

Search must ask the user to choose between these rather than pick one.

| Address | RSNs |
|---|---|
| 10 KINGSTON RD | 4153671, 4156594 |
| 10 ROANOKE RD | 4154894, 4156233 |
| 101 KENDLETON DR | 4155782, 4156208 |
| 109 GENERATION BLVD | 4152889, 4156416 |
| 111 GENERATION BLVD | 4152889, 4156074 |
| 115 GENERATION BLVD | 4152889, 4156075 |
| 12 KINGSTON RD | 4153671, 4156593 |
| 1539 BATHURST ST | 4154935, 4250612 |
| 1625 KINGSTON RD | 4155804, 4155805, 4155806 |
| 1627 KINGSTON RD | 4155804, 4155805, 4155806 |
| 1629 KINGSTON RD | 4155804, 4155805, 4155806 |
| 1631 KINGSTON RD | 4155804, 4155805, 4155806 |
| 1633 KINGSTON RD | 4155804, 4155805, 4155806 |
| 1635 KINGSTON RD | 4155804, 4155805, 4155806 |
| 1637 KINGSTON RD | 4155804, 4155805, 4155806 |
| 1639 KINGSTON RD | 4155804, 4155805, 4155806 |
| 1641 KINGSTON RD | 4155804, 4155805, 4155806 |
| 170 BERRY RD | 4155281, 4168798 |
| 2085 ISLINGTON AVE | 4155358, 4155918 |
| 2087 ISLINGTON AVE | 4155358, 4155918 |
| 2089 ISLINGTON AVE | 4155358, 4155918 |
| 2091 ISLINGTON AVE | 4155358, 4155918 |
| 2093 ISLINGTON AVE | 4155358, 4155918 |
| 2095 ISLINGTON AVE | 4155358, 4155918 |
| 2097 ISLINGTON AVE | 4155358, 4155918 |
| 2099 ISLINGTON AVE | 4155358, 4155918 |
| 2101 ISLINGTON AVE | 4155358, 4155918 |
| 30 FALSTAFF AVE | 4155625, 4155999 |
| 3015 QUEEN ST E | 4155743, 4317586 |
| 3017 QUEEN ST E | 4155743, 4317590 |
| 3036 BATHURST ST | 4154485, 4155914 |
| 305 PARLIAMENT ST | 4250288, 5815386 |
| 3171 EGLINTON AVE E | 4155943, 4156313 |
| 33 FLAMBOROUGH DR | 4155845, 5299588, 5299592, 5299600 |
| 4 KINGSTON RD | 4153671, 4156597 |
| 40 ALEXANDER ST | 4167698, 4167699, 4167700 |
| 40 FALSTAFF AVE | 4155625, 4155913 |
| 41 BROOKWELL DR | 4154459, 4156504 |
| 42 ALEXANDER ST | 4167698, 4167699, 4167700 |
| 4201 KINGSTON RD | 4152838, 4156242 |
| 44 ALEXANDER ST | 4167698, 4167699, 4167700 |
| 46 ALEXANDER ST | 4167698, 4167699, 4167700 |
| 4752 DUNDAS ST W | 4156289, 4156523 |
| 4754 DUNDAS ST W | 4156225, 4156523 |
| 48 ALEXANDER ST | 4167698, 4167699, 4167700 |
| 50 ALEXANDER ST | 4167698, 4167699, 4167700 |
| 55 BROADWAY AVE | 4286226, 5697761 |
| 6 KINGSTON RD | 4153671, 4264078 |
| 7 ROANOKE RD | 4154895, 4156531 |
| 711 FINCH AVE W | 4154619, 5803406 |
| 740 MIDLAND AVE | 4152689, 4155890 |
| 75 SILVER SPRINGS BLVD | 4156516, 4156521, 4156533 |
| 77 SILVER SPRINGS BLVD | 4156516, 4156521 |
| 79 SILVER SPRINGS BLVD | 4156516, 4156521 |
| 8 KINGSTON RD | 4153671, 4264076 |
| 81 SILVER SPRINGS BLVD | 4156516, 4156521 |
| 83 SILVER SPRINGS BLVD | 4156516, 4156521 |
| 85 SILVER SPRINGS BLVD | 4156516, 4156521 |
| 85 THORNCLIFFE PARK DR | 4154159, 4237447 |
| 87 THORNCLIFFE PARK DR | 4154159, 4237447 |
| 89 THORNCLIFFE PARK DR | 4154159, 4237447 |
| 91 THORNCLIFFE PARK DR | 4154159, 4237447 |
| 93 THORNCLIFFE PARK DR | 4154159, 4237447 |
| 95 THORNCLIFFE PARK DR | 4154159, 4237447 |

