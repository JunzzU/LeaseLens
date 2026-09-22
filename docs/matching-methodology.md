# Matching Methodology

How LeaseLens connects records from different City of Toronto datasets to one building, and how sure it is.

## Buildings

A **building** is a RentSafeTO registration number (RSN). The RSN joins the registration file and both evaluation files directly, so those need no address matching (see [data-audit.md](data-audit.md), finding 2).

Each building has one **alias** per civic number it covers. `85-95 THORNCLIFFE PARK DR` gets aliases for 85, 87, 89, 91, 93 and 95. Ranges wider than 40 numbers get only their endpoints. Aliases come from every address spelling seen in registration and evaluations.

## Address normalization

Implemented twice (Python pipeline, Java API) and held to one contract: [`testdata/address-normalization-cases.json`](../testdata/address-normalization-cases.json).

| Input | Normalized key |
|---|---|
| `123 Bloor Street West`, `123 BLOOR ST W`, `123 Bloor St. W.` | `123\|BLOOR\|ST\|W` |
| `181-183  GERRARD ST E ` | `181\|GERRARD\|ST\|E` and `183\|GERRARD\|ST\|E` |
| `145 ST GEORGE ST` | `145\|ST GEORGE\|ST\|` ("ST" as Saint is kept in the name) |
| `70 WILSON PARK RD--CLOSED` | `70\|WILSON PARK\|RD\|`, flagged `closed` |

### Comparing across datasets: the match key

The City's permit records do not always split a street into name and type the way registration does. Permits say name `THE WEST MALL` with no type; registration's `339 THE WEST MALL` parses as name `THE WEST`, type `MALL`. So cross-dataset matching compares a **match key** with the street as a single string, `339|THE WEST MALL|`. It is computed on `building_aliases.match_key` and by `permit_match_keys()`, and it agrees whichever way a source split the street.

## Permits → buildings

### Candidates

A permit is a **candidate** for a building when one of its match keys equals one of the building's alias keys.

| Method | When |
|---|---|
| `ADDRESS` | The permit's own civic number matches. |
| `PERMIT_RANGE` | The permit's address is a range (`2721-2729`) and one number in it matches. |

Permits with no candidate are not stored: 624,607 of 643,556 rows in the current files. They remain in the raw files.

### Accepting a match

| Situation | Confidence | Attached |
|---|---|---|
| Exactly one candidate building, `ADDRESS`, work on the apartment building | `HIGH` | yes |
| Exactly one candidate, via `PERMIT_RANGE` or on a non-apartment structure (below) | `MEDIUM` | yes |
| More than one candidate building (e.g. 3 RSNs share `1625 KINGSTON RD`) | `LOW` | **no** |

**An address shared by several buildings is never attached to any of them.** The candidates stay in `permit_matches` with `accepted = false`, and the profile carries the `SOME_PERMITS_NOT_ATTACHED` note so the user knows permits may exist that we couldn't attribute.

Every match stores its evidence: the method, confidence, the permit's published address, the alias it matched, and when.

### What the permit is about

Two labels tell the user how a permit relates to the building. A same-address match isn't always work on the apartment building itself.

**`site_relation`** comes from the permit's structure type:

- `BUILDING`: the apartment building.
- `NON_RESIDENTIAL_SPACE`: a shop, office, clinic or garage in or on the building.
- `OTHER_STRUCTURE_ON_SITE`: houses or townhouses on the same property, e.g. the new stacked townhouse blocks at 17 Farmstead Rd.

**`work_category`** comes from the permit type, the work field and a narrow description pattern:

- `NEW_CONSTRUCTION`: a new building on the site, e.g. a 62-storey tower replacing 11 Yorkville Ave.
- `DEMOLITION`
- `ALTERATION_OR_REPAIR`

The API also returns `predatesBuilding` when the application year is before the building's year built. That usually means the permit was for an earlier structure, or for this building's own construction.

## Measured accuracy

**Precision**: a stratified random sample of 50 attached matches, reviewed by reading each permit's description against the building. The sample was 30 `ADDRESS`/`BUILDING`, 8 `PERMIT_RANGE`, 6 `NON_RESIDENTIAL_SPACE` and 6 `OTHER_STRUCTURE_ON_SITE`. The labelled sample is in [`testdata/permit-match-review.csv`](../testdata/permit-match-review.csv).

| Question | Result |
|---|---|
| Is the permit for the same property? | **50 / 50** |
| Are `site_relation` and `work_category` right? | 49 / 50. A restaurant fit-out whose City structure type is "Multiple Unit Building" is labelled `BUILDING`. |

With 0 errors in 50, the 95% lower confidence bound on precision is about 94%, which is above the project's 90% target. This is one reviewer's judgement; user testing in Week 10 is the next check.

**Missed matches**: of 15 randomly sampled buildings with no candidate permit, all 15 had no permit under their address. Nearby numbers on the same street were different buildings: neighbours, the other side of the street, or other buildings in the same complex.

## Known limitations

- **Address only.** A permit filed under a different address of the same property (e.g. a corner building's side-street address) will be missed. The City's `GEO_ID` could link these through the Address Points dataset. That's a planned improvement; `distance_metres` is reserved for it.
- **Structure types are applicant-entered** and sometimes wrong (see the restaurant example above).
- **Cleared permits since 2017 only.** Older cleared permits (2000–2016) are in a separate archive file not yet loaded. A cleared permit's *application* can still be older, e.g. 1990.
- **Permits are not judgements.** A permit can mean maintenance, renovation, new construction or a compliance upgrade. The absence of a permit record does not show the absence of work or problems.
