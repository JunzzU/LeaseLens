"""Schema checks and field parsers shared by the loaders.

Parsers return None for blank input and raise FieldError for input that is present
but unusable, so each loader decides whether a bad field rejects the row or only
blanks the field with a warning.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date

import pandas as pd

# Loose box around the City of Toronto; anything outside is a bad coordinate.
TORONTO_LAT = (43.55, 43.88)
TORONTO_LON = (-79.65, -79.10)


class SchemaError(Exception):
    """The source file no longer has the columns we rely on. Fails the whole import."""


class FieldError(ValueError):
    pass


def check_columns(df: pd.DataFrame, required: set[str], dataset: str) -> list[str]:
    """Raise if required columns are gone; return columns we have never seen before."""
    missing = required - set(df.columns)
    if missing:
        raise SchemaError(f"{dataset}: source is missing expected columns {sorted(missing)}")
    return sorted(set(df.columns) - required)


def read_source(path) -> pd.DataFrame:
    """Read every column as text; blanks become None. Types are parsed per field."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return df.apply(lambda col: col.str.strip())


def records(df: pd.DataFrame):
    """(1-based row number, row dict) pairs; row numbers match the raw file's data rows."""
    for i, row in enumerate(df.to_dict("records"), start=1):
        yield i, {k: (None if blank(v) or v == "" else v) for k, v in row.items()}


def blank(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def parse_int(value, lo: int | None = None, hi: int | None = None) -> int | None:
    if blank(value):
        return None
    s = str(value).replace(",", "")
    if not re.fullmatch(r"-?\d+(\.0+)?", s):
        raise FieldError(f"not an integer: {value!r}")
    n = int(float(s))
    if (lo is not None and n < lo) or (hi is not None and n > hi):
        raise FieldError(f"out of range [{lo}, {hi}]: {n}")
    return n


def parse_score(value) -> tuple[int | None, bool]:
    """Evaluation score 0-100. A decimal score is rounded; the bool says whether that happened."""
    if blank(value):
        return None, False
    try:
        x = float(str(value))
    except ValueError:
        raise FieldError(f"score is not a number: {value!r}") from None
    if not 0 <= x <= 100:
        raise FieldError(f"score out of range [0, 100]: {value!r}")
    n = int(x + 0.5)   # half-up, independent of Python's banker's rounding
    return n, n != x


def parse_date(value) -> date | None:
    if blank(value):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise FieldError(f"not an ISO date: {value!r}") from None


def parse_coords(lat, lon) -> tuple[float, float] | tuple[None, None]:
    if blank(lat) or blank(lon):
        return None, None
    try:
        la, lo = float(lat), float(lon)
    except ValueError:
        raise FieldError(f"non-numeric coordinates: {lat!r}, {lon!r}") from None
    if not (TORONTO_LAT[0] <= la <= TORONTO_LAT[1] and TORONTO_LON[0] <= lo <= TORONTO_LON[1]):
        raise FieldError(f"coordinates outside Toronto: {la}, {lo}")
    return la, lo


def parse_rsn(value) -> str:
    if blank(value) or not re.fullmatch(r"\d+", str(value)):
        raise FieldError(f"invalid RSN: {value!r}")
    return str(value)


class Warnings(Counter):
    """Counts of non-fatal problems, stored in data_imports.warnings."""

    def add(self, kind: str, n: int = 1) -> None:
        self[kind] += n
