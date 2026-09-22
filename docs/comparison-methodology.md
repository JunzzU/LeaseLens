# Comparison Methodology

`GET /api/v1/buildings/{id}/comparison` answers: *how does this building's latest evaluation compare with buildings like it?* The rule, the group size and the spread are always returned, so the answer can be checked.

## What is compared

- **Only the 2023+ scoring system.** Each building's latest `V2023` evaluation. Pre-2023 scores are never compared with 2023+ scores (the method change alone moved the median from 74 to 91; see [data-audit.md](data-audit.md), finding 1).
- **Peers must have been evaluated recently.** A peer's latest evaluation must be within **730 days** of the building's own. Size-matched buildings without one are left out and counted as `excludedWithoutRecentEvaluation`, which is the missing-data rate.
- **Permit activity** is the number of attached permits applied for in the **last 5 years**, compared with the peers' median and upper quartile.

## Choosing peers

Rules are tried in order, and the first that finds **at least 15 peers** is used:

| Rule | Location | Units | Storeys |
|---|---|---|---|
| `SAME_WARD_SIMILAR_SIZE` | same ward | ±25% | ±3 |
| `SAME_WARD_BROADER_SIZE` | same ward | ±50% | ±5 |
| `WITHIN_3_KM_BROADER_SIZE` | within 3 km | ±50% | ±5 |

The distance rule needs the building's coordinates; it is skipped when there are none. The planned "adjacent wards" step is replaced by the 3 km radius because ward boundaries aren't loaded yet.

**Property type (private, TCHC, social housing) is not a filter.** Requiring it would drop the first rule's coverage from 63% to 52% of buildings. The peer group's property-type mix is returned instead (`peerPropertyTypes`), so clients can show it.

## What is returned

| Field | Meaning |
|---|---|
| `availability` | `AVAILABLE`, `TOO_FEW_PEERS`, `NO_CURRENT_EVALUATION` or `MISSING_BUILDING_SIZE` |
| `rule` | The rule used, with all its parameters |
| `peerCount` | Peers in the group |
| `peerScores` | Median, quartiles, min and max. Null below 15 peers. |
| `percentOfPeersBelow` / `percentOfPeersEqual` | Share of peers with a lower / identical score. Null below 15 peers. Scores are integers, so ties are common and reported separately. |

Suggested wording (the API returns numbers, never verdicts): *"This result is higher than 70% of 20 comparable buildings (same ward, similar size)."*

## Coverage on the current data

On a random sample of 300 buildings:

| Result | Buildings |
|---|---|
| `AVAILABLE` | 273 (91%) |
| `TOO_FEW_PEERS` | 22 |
| `NO_CURRENT_EVALUATION` | 4 |
| `MISSING_BUILDING_SIZE` | 1 |

The rules used were `SAME_WARD_SIMILAR_SIZE` for 182 buildings, `SAME_WARD_BROADER_SIZE` for 68 and `WITHIN_3_KM_BROADER_SIZE` for 45. Median response time is 25 ms (p95 45 ms).
