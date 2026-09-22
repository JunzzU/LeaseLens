import json
from pathlib import Path

import pytest

from leaselens_pipeline.normalization.address import AddressParseError, expand_keys, parse

CASES = json.loads((Path(__file__).parents[2] / "testdata/address-normalization-cases.json").read_text())


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["input"])
def test_shared_cases(case):
    addr = parse(case["input"])
    assert addr.key == case["key"]
    assert expand_keys(addr) == case["keys"]
    assert addr.designator == case.get("designator", "")
    assert addr.flags == frozenset(case.get("flags", []))


@pytest.mark.parametrize("raw", CASES["invalid"])
def test_invalid(raw):
    with pytest.raises(AddressParseError):
        parse(raw)


def test_spellings_converge():
    spellings = ["123 Bloor Street West", "123 BLOOR ST W", "123 Bloor St. W.", "  123  bloor   st  west "]
    assert {parse(s).key for s in spellings} == {"123|BLOOR|ST|W"}


def test_display_is_readable():
    assert parse("181-183  GERRARD ST E ").display() == "181-183 GERRARD ST E"
    assert parse("245 C HOWLAND AVE").display() == "245C HOWLAND AVE"


def test_permit_match_keys():
    from leaselens_pipeline.normalization.address import permit_match_keys
    assert permit_match_keys("181", "GERRARD", "ST", "E") == [("181|GERRARD ST|E", False)]
    assert permit_match_keys("140", "THE ESPLANADE", "", " ") == [("140|THE ESPLANADE|", False)]
    assert permit_match_keys("58 A", "MAIN", "STREET", "") == [("58A|MAIN ST|", False)]
    assert permit_match_keys("273-277", "KING", "ST", "W") == [
        ("273|KING ST|W", True), ("275|KING ST|W", True), ("277|KING ST|W", True)]
    assert permit_match_keys("359 1/2", "QUEEN", "ST", "W") == []
    assert permit_match_keys("", "QUEEN", "ST", "W") == []


def test_permit_and_registration_keys_agree():
    """A building alias and a permit for the same place produce the same match key."""
    from leaselens_pipeline.normalization.address import permit_match_keys
    for raw, fields in [("339 THE WEST MALL", ("339", "THE WEST MALL", "", "")),
                        ("10 QUEENS QUAY W", ("10", "QUEENS QUAY", "", "W")),
                        ("245 C HOWLAND AVE", ("245 C", "HOWLAND", "AVE", ""))]:
        a = parse(raw)
        alias_key = f"{a.number_low}{a.suffix}|{' '.join(p for p in (a.street_name, a.street_type) if p)}|{a.direction}"
        assert permit_match_keys(*fields)[0][0] == alias_key
