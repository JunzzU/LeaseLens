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
