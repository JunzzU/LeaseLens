from datetime import date

import pytest

from leaselens_pipeline.validation.rows import FieldError, parse_coords, parse_date, parse_int, parse_rsn, parse_score


def test_parse_int():
    assert parse_int("42") == 42
    assert parse_int("1,200") == 1200
    assert parse_int("12.0") == 12
    assert parse_int(None) is None
    with pytest.raises(FieldError):
        parse_int("0", lo=1)
    with pytest.raises(FieldError):
        parse_int("DO NOT UPDATE OR DELETE THIS INFO FIELD")


def test_parse_score_rounds_decimals_and_says_so():
    assert parse_score("91") == (91, False)
    assert parse_score("81.1") == (81, True)
    assert parse_score("80.5") == (81, True)
    assert parse_score(None) == (None, False)
    with pytest.raises(FieldError):
        parse_score("101")


def test_parse_date():
    assert parse_date("2024-09-16") == date(2024, 9, 16)
    assert parse_date("2024-09-16T00:00:00") == date(2024, 9, 16)
    with pytest.raises(FieldError):
        parse_date("OCT 18, 2021")


def test_parse_coords_rejects_points_outside_toronto():
    assert parse_coords("43.7774", "-79.3233") == (43.7774, -79.3233)
    assert parse_coords(None, "-79.3") == (None, None)
    with pytest.raises(FieldError):
        parse_coords("0", "0")
    with pytest.raises(FieldError):
        parse_coords("-79.3233", "43.7774")   # swapped


def test_parse_rsn():
    assert parse_rsn("4152852") == "4152852"
    with pytest.raises(FieldError):
        parse_rsn("41528 52")
