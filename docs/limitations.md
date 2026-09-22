# Limitations

What LeaseLens can and can't tell a renter. The website and the app word their coverage notes from this page. Each item names the API field or code that signals it.

## Coverage

- **RentSafeTO covers only purpose-built rental apartment buildings with 3+ storeys and 10+ units.** Condominiums, townhouses, and rentals in houses are not in the data at all.
- **Evaluations concern the building and its common areas, not any particular unit** (`BUILDING_NOT_UNIT`, always present).
- **Some buildings have left the registration file** (`NOT_IN_CURRENT_REGISTRATION`). Often this is because they were redeveloped or deregistered. Their past evaluations are kept.
- **Investigation and enforcement activity is not included.** The City's Investigation Activity application covers only two years and includes investigations where no violation was found. LeaseLens links to it rather than scraping or re-classifying it.

## Evaluations

- **The City changed its scoring method in June 2023** (`SCORING_SYSTEM_CHANGED`, and a `SCORING_SYSTEM_CHANGE` timeline event). Scores before and after are not comparable, so change and comparison use one method only.
- **Evaluations are periodic.** The latest score may be up to 3 years old; its date is always shown.

## Permits

- **Matched by address only.** Permits filed under another address of the same property can be missed ([matching-methodology.md](matching-methodology.md)).
- **Permits at an address shared by several buildings are not shown for any of them** (`SOME_PERMITS_NOT_ATTACHED`).
- **A permit can mean maintenance, renovation, new construction or a safety upgrade.** It is not a judgement of the building. `workCategory` separates new construction and demolition on the site from work on the building.
- **Cleared permits are loaded from 2017 onward.** Older history is incomplete.

## Comparisons

- **Peers are chosen by size and location only**, from the first rule that finds 15 or more. Below 15 peers, no percentile is given (`TOO_FEW_PEERS`) ([comparison-methodology.md](comparison-methodology.md)).

## Freshness

- **"Last imported" is when LeaseLens last loaded the file.** The City's "last modified" stamp (`sourceVersion`) is when the portal file changed. Neither guarantees that every record is current.
- **Registration year is not shown as a history event.** The City's `YEAR_REGISTERED` is often later than a building's first evaluation, so it isn't the year the building joined RentSafeTO.

## Always

**No record found does not mean no issue exists.**
