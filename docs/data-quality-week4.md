# Data Quality Report — Week 4

Generated 2026-09-21 by `leaselens-pipeline report` after a full rebuild (`import all` on an empty schema), followed by a second `import permits` run to confirm the import is idempotent. How permits are matched, and how the accuracy was measured, is in [matching-methodology.md](matching-methodology.md).

## Findings

- **643,556 permit rows are read and 18,925 are stored**, the ones whose address matches a RentSafeTO building. 17,975 of those are attached to exactly one building. 950 are held back because their address belongs to several buildings.
- **2,745 of 3,670 buildings (75%) have at least one attached permit.** Another 121 have only unattachable, shared-address candidates, and 804 have no candidate at all. Sampling suggests those 804 are genuine: no permit was filed under their address.
- **The permit identity rule from the audit holds:** exactly 24 duplicate `(permit number, revision, type)` rows are rejected.
- **Idempotency bug found and fixed.** Some permits publish a fraction-of-a-cent cost (`14783.974`), which the `numeric(14,2)` column rounds. The stored value then never equalled the incoming one, so the row looked updated on every run. Costs are now rounded to cents when parsed.
- **New construction and demolition on rental sites is common enough to label.** 1,095 attached permits are `NEW_CONSTRUCTION` and 112 are `DEMOLITION`. One example is 11 Yorkville Ave, which has left the RentSafeTO registry while a 62-storey tower replaces it.
- **"Rental Renovation Licence"** (Toronto's 2025 renoviction bylaw) now appears as a permit type. It's rare in these files so far, but it's worth highlighting in the UI once the timeline exists.
- **Builder names are not stored.** `BUILDER_NAME` often names a private individual and isn't needed.
- **`EST_CONST_COST` is non-numeric in about 6,400 matched rows** (e.g. "DO NOT UPDATE OR DELETE THIS INFO FIELD"). It's stored as null with a warning.

---

## Latest import per dataset

| Dataset | Import | Status | Source version | Completed | Records | Inserted | Updated | Unchanged | Rejected | Skipped |
|---|---|---|---|---|---|---|---|---|---|---|
| evaluations_pre2023 | 2 | completed_with_warnings | 2026-02-20T17:41:23.374212 | 2026-09-21 23:19 | 11,760 | 11,751 | 0 | 0 | 9 | 0 |
| evaluations_v2023 | 3 | completed_with_warnings | 2026-09-21T09:34:52.393280 | 2026-09-21 23:19 | 6,674 | 6,674 | 0 | 0 | 0 | 0 |
| permits_active | 4 | completed_with_warnings | 2026-09-21T10:25:31.382395 | 2026-09-21 23:19 | 204,605 | 6,671 | 0 | 0 | 9 | 197,925 |
| permits_cleared | 5 | completed_with_warnings | 2026-09-21T11:19:35.797959 | 2026-09-21 23:19 | 438,951 | 12,254 | 0 | 0 | 15 | 426,682 |
| registration | 1 | completed_with_warnings | 2026-07-05T09:00:19.147056 | 2026-09-21 23:19 | 3,611 | 3,611 | 0 | 0 | 0 | 0 |

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

## Permits

| Measure | Count |
|---|---|
| Buildings with at least one attached permit | 2,745 |
| Buildings with no candidate permit at all | 804 |
| Permits attached to exactly one building | 17,975 |
| Permits not attached: address shared by several buildings | 950 |

| Method | Confidence | Site relation | Attached | Matches | Buildings |
|---|---|---|---|---|---|
| ADDRESS | HIGH | BUILDING | 1 | 15,372 | 2,695 |
| ADDRESS | MEDIUM | OTHER_STRUCTURE_ON_SITE | 1 | 1,126 | 46 |
| ADDRESS | MEDIUM | NON_RESIDENTIAL_SPACE | 1 | 1,008 | 278 |
| PERMIT_RANGE | MEDIUM | BUILDING | 1 | 386 | 63 |
| PERMIT_RANGE | MEDIUM | NON_RESIDENTIAL_SPACE | 1 | 58 | 16 |
| PERMIT_RANGE | MEDIUM | OTHER_STRUCTURE_ON_SITE | 1 | 25 | 3 |
| PERMIT_RANGE | LOW | BUILDING | 0 | 1,487 | 224 |
| PERMIT_RANGE | LOW | OTHER_STRUCTURE_ON_SITE | 0 | 658 | 10 |
| ADDRESS | LOW | BUILDING | 0 | 251 | 37 |
| PERMIT_RANGE | LOW | NON_RESIDENTIAL_SPACE | 0 | 157 | 40 |
| ADDRESS | LOW | OTHER_STRUCTURE_ON_SITE | 0 | 6 | 3 |
| ADDRESS | LOW | NON_RESIDENTIAL_SPACE | 0 | 5 | 5 |

| Work category | File | Attached permits |
|---|---|---|
| ALTERATION_OR_REPAIR | ACTIVE | 5,948 |
| ALTERATION_OR_REPAIR | CLEARED | 10,820 |
| DEMOLITION | ACTIVE | 18 |
| DEMOLITION | CLEARED | 94 |
| NEW_CONSTRUCTION | ACTIVE | 417 |
| NEW_CONSTRUCTION | CLEARED | 678 |

## Rejected rows (latest import)

| Dataset | Reason | Rows |
|---|---|---|
| evaluations_pre2023 | address marked CREATED IN ERROR | 7 |
| evaluations_pre2023 | duplicate (RSN, evaluation date) | 2 |
| permits_active | duplicate (permit number, revision, type) | 9 |
| permits_cleared | duplicate (permit number, revision, type) | 15 |

## Warnings (latest import)

| Dataset | Warnings |
|---|---|
| evaluations_pre2023 | buildings_not_in_registration_created: 58, missing_coordinates: 231 |
| evaluations_v2023 | buildings_not_in_registration_created: 1, decimal_score_rounded: 1, missing_coordinates: 226 |
| permits_active | ambiguous_address_not_attached: 288, non_numeric_est_const_cost: 2077, unmatchable_address: 212 |
| permits_cleared | ambiguous_address_not_attached: 662, non_numeric_est_const_cost: 4342, unmatchable_address: 256 |
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

