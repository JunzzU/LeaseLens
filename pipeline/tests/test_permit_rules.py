"""Classification rules, using wording taken from real permits in the reviewed sample
(testdata/permit-match-review.csv)."""
from decimal import Decimal

import pytest

from leaselens_pipeline.loading.permits import confidence, parse_cost, site_relation, work_category
from leaselens_pipeline.validation.rows import FieldError


@pytest.mark.parametrize("structure, permit_type, expected", [
    ("Apartment Building", "Fire/Security Upgrade", "BUILDING"),
    ("Mixed Use/Res w Non Res", "Partial Permit", "BUILDING"),
    ("", "Plumbing(PS)", "BUILDING"),
    ("Restaurant 30 Seats or Less", "Plumbing(PS)", "NON_RESIDENTIAL_SPACE"),
    ("Medical/Dental Office", "Mechanical(MS)", "NON_RESIDENTIAL_SPACE"),
    ("Parking Garage", "Conditional Permit", "NON_RESIDENTIAL_SPACE"),
    ("Stacked Townhouses", "Plumbing(PS)", "OTHER_STRUCTURE_ON_SITE"),
    ("SFD - Townhouse", "Demolition Folder (DM)", "OTHER_STRUCTURE_ON_SITE"),
    ("Apartment Building", "New Houses", "OTHER_STRUCTURE_ON_SITE"),
])
def test_site_relation(structure, permit_type, expected):
    assert site_relation(structure, permit_type) == expected


@pytest.mark.parametrize("permit_type, work, description, expected", [
    ("New Building", "New Building", "Proposed construction of a 27 storey, 341 unit apartment building", "NEW_CONSTRUCTION"),
    ("Partial Permit", "Partial Permit - Structural Framing", "demolish the existing 10 storey building", "NEW_CONSTRUCTION"),
    ("Mechanical(MS)", "Building Permit Related(MS)",
     "HVAC - Proposal to construct a new 50-storey apartment building", "NEW_CONSTRUCTION"),
    ("Demolition Folder (DM)", "Demolition", "Proposal to demo existing community hall", "DEMOLITION"),
    ("Building Additions/Alterations", "Balcony/Guard Repairs", "Slab reconstruction on all 39 balconies",
     "ALTERATION_OR_REPAIR"),
    ("Plumbing(PS)", "Building Permit Related(PS)",
     "Plumbing - Proposal for interior alterations to all 17 units", "ALTERATION_OR_REPAIR"),
])
def test_work_category(permit_type, work, description, expected):
    assert work_category(permit_type, work, description) == expected


def test_shared_addresses_are_never_accepted():
    assert confidence("ADDRESS", "BUILDING", 1) == ("HIGH", True)
    assert confidence("PERMIT_RANGE", "BUILDING", 1) == ("MEDIUM", True)
    assert confidence("ADDRESS", "NON_RESIDENTIAL_SPACE", 1) == ("MEDIUM", True)
    assert confidence("ADDRESS", "BUILDING", 2) == ("LOW", False)


def test_cost_is_rounded_to_cents_so_reruns_compare_equal():
    assert parse_cost("14783.974") == Decimal("14783.97")
    assert parse_cost("1,200,000") == Decimal("1200000.00")
    assert parse_cost(None) is None
    with pytest.raises(FieldError):
        parse_cost("DO NOT UPDATE OR DELETE THIS INFO FIELD")
