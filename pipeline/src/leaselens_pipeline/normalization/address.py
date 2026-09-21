"""Toronto street-address normalization.

Turns the many spellings of one address into a single comparable key:

    "123 Bloor Street West", "123 BLOOR ST W", "123 Bloor St. W."  ->  "123|BLOOR|ST|W"

Key format is ``number|street name|street type|direction``; the number keeps any
letter suffix ("245C"). Ranges ("85-95") are kept as ``number_low``/``number_high``
and expanded into one key per civic number by :func:`expand_keys`.

The cases in testdata/address-normalization-cases.json are the contract for this
module; the Java search code must pass the same file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

STREET_TYPES = {
    "AVENUE": "AVE", "AVE": "AVE", "AV": "AVE",
    "STREET": "ST", "ST": "ST",
    "ROAD": "RD", "RD": "RD",
    "DRIVE": "DR", "DR": "DR",
    "BOULEVARD": "BLVD", "BLVD": "BLVD",
    "COURT": "CRT", "CRT": "CRT", "CT": "CRT",
    "CRESCENT": "CRES", "CRES": "CRES",
    "PLACE": "PL", "PL": "PL",
    "PARKWAY": "PKWY", "PKWY": "PKWY",
    "HEIGHTS": "HTS", "HTS": "HTS",
    "GARDENS": "GDNS", "GDNS": "GDNS",
    "CIRCUIT": "CRCT", "CRCT": "CRCT",
    "CIRCLE": "CRCL", "CRCL": "CRCL",
    "TERRACE": "TER", "TER": "TER",
    "GROVE": "GRV", "GRV": "GRV",
    "GATE": "GT", "GT": "GT",
    "SQUARE": "SQ", "SQ": "SQ",
    "TRAIL": "TRL", "TRL": "TRL",
    "LANE": "LANE", "LN": "LANE",
    "WAY": "WAY", "MALL": "MALL", "WALK": "WALK", "LINE": "LINE",
    "HILL": "HILL", "RIDGE": "RIDGE", "VISTA": "VISTA", "PATH": "PATH",
    "LANEWAY": "LANEWAY", "PROMENADE": "PROMENADE", "ESPLANADE": "ESPLANADE", "QUAY": "QUAY",
}
DIRECTIONS = {"E": "E", "EAST": "E", "W": "W", "WEST": "W", "N": "N", "NORTH": "N", "S": "S", "SOUTH": "S"}

# Annotations the City appends to addresses. Stripped before parsing; recorded as flags.
_NOISE = [
    (re.compile(r"\*\*\s*CREATED IN ERROR\s*\*\*"), "created_in_error"),
    (re.compile(r"<<[^>]*>>"), "annotation"),
    (re.compile(r"-+\s*CLOSED\b"), "closed"),
    (re.compile(r"-\s*WARD\s+\d+\b"), "annotation"),
]
# Building/unit designators that follow the street: "UNIT B", "- BLDG A"
_DESIGNATOR = re.compile(r"(?:-\s*)?\b(?:UNIT|BLDG|BUILDING|SUITE|APT)\s+([A-Z0-9]+)\s*$")
_NUMBER = re.compile(r"^(\d+)\s?([A-Z])?(?:\s*-\s*(\d+)\s?([A-Z])?)?\s+(.+)$")
# Ranges wider than this are expanded to their endpoints only (e.g. a whole block).
MAX_RANGE_SPAN = 40


class AddressParseError(ValueError):
    pass


@dataclass(frozen=True)
class Address:
    number_low: int
    number_high: int
    suffix: str            # letter after the number, "" if none ("245 C HOWLAND AVE" -> "C")
    street_name: str
    street_type: str       # "" when the street has none ("THE KINGSWAY")
    direction: str         # "" | E | W | N | S
    designator: str = ""   # "B" from "UNIT B"; not part of the key
    flags: frozenset[str] = field(default_factory=frozenset)

    @property
    def street(self) -> str:
        return " ".join(p for p in (self.street_name, self.street_type, self.direction) if p)

    @property
    def key(self) -> str:
        """Key of the first civic number, e.g. '85|THORNCLIFFE PARK|DR|'."""
        return make_key(self.number_low, self.suffix, self.street_name, self.street_type, self.direction)

    @property
    def is_range(self) -> bool:
        return self.number_high != self.number_low

    def display(self) -> str:
        num = f"{self.number_low}{self.suffix}"
        if self.is_range:
            num += f"-{self.number_high}"
        return f"{num} {self.street}"


def make_key(number: int, suffix: str, name: str, stype: str, direction: str) -> str:
    return f"{number}{suffix}|{name}|{stype}|{direction}"


def clean(raw: str) -> tuple[str, set[str]]:
    """Upper-case, strip City annotations and punctuation, collapse whitespace."""
    s = str(raw).upper()
    flags: set[str] = set()
    for pattern, flag in _NOISE:
        if pattern.search(s):
            flags.add(flag)
            s = pattern.sub(" ", s)
    s = s.replace(".", " ").replace(",", " ")
    return re.sub(r"\s+", " ", s).strip(), flags


def parse(raw: str) -> Address:
    s, flags = clean(raw)

    designator = ""
    m = _DESIGNATOR.search(s)
    if m:
        designator = m.group(1)
        s = s[: m.start()].strip()

    m = _NUMBER.match(s)
    if not m:
        raise AddressParseError(f"no civic number in {raw!r}")
    low, suffix, high, _high_suffix, rest = m.groups()
    number_low = int(low)
    number_high = int(high) if high else number_low
    if number_high < number_low:
        raise AddressParseError(f"descending range in {raw!r}")

    words = rest.split()
    direction = ""
    if len(words) > 1 and words[-1] in DIRECTIONS:
        direction = DIRECTIONS[words.pop()]
    street_type = ""
    # The type is the last word, and never the only word ("THE KINGSWAY", "ST" in "ST CLAIR").
    if len(words) > 1 and words[-1] in STREET_TYPES:
        street_type = STREET_TYPES[words.pop()]
    if not words:
        raise AddressParseError(f"no street name in {raw!r}")

    return Address(number_low, number_high, suffix or "", " ".join(words), street_type,
                   direction, designator, frozenset(flags))


def expand_keys(addr: Address) -> list[str]:
    """One key per civic number a range covers, stepping by 2 (same side of the street)."""
    if not addr.is_range:
        return [addr.key]
    span = addr.number_high - addr.number_low
    if span > MAX_RANGE_SPAN:
        numbers = [addr.number_low, addr.number_high]
    else:
        step = 2 if span % 2 == 0 else 1
        numbers = list(range(addr.number_low, addr.number_high + 1, step))
    return [make_key(n, addr.suffix if n == addr.number_low else "", addr.street_name,
                     addr.street_type, addr.direction) for n in numbers]


def key_to_text(key: str) -> str:
    """'181|GERRARD|ST|E' -> '181 GERRARD ST E' (the searchable form of a key)."""
    return " ".join(part for part in key.split("|") if part)
