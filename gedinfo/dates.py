"""Structured parsing of GEDCOM date values.

GEDCOM dates are a small grammar, not a fixed format: an exact date
(``5 MAY 1950``, ``MAY 1950``, ``1950``), a qualified date (``ABT``, ``EST``,
``CAL``, ``BEF``, ``AFT`` prefixing an exact date), a range (``BET ... AND
...``, ``FROM ... TO ...``, or a bare ``FROM``/``TO``), or an interpreted date
(``INT <date> (<phrase>)``). :func:`parse_gedcom_date` turns any of these into
a :class:`GedcomDate`; it never raises, because real-world GEDCOM files
routinely contain free text ("before the war") in date fields.

Explicitly OUT of scope (fall through to a raw-only, unparsed ``GedcomDate``):
dual years (``1732/33``), calendar escapes (``@#DHEBREW@`` and similar), and
non-English month names. Nobody should half-implement these later without
updating this module and its tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

MONTH_ABBREVIATIONS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

_SINGLE_QUALIFIERS = ("ABT", "EST", "CAL", "BEF", "AFT")

_CORE_RE = re.compile(r"^(?:(\d{1,2})\s+)?(?:([A-Za-z]{3})\s+)?(\d{3,4})$")
_BET_AND_RE = re.compile(r"^BET\s+(.*?)\s+AND\s+(.*)$", re.IGNORECASE)
_FROM_TO_RE = re.compile(r"^FROM\s+(.*?)\s+TO\s+(.*)$", re.IGNORECASE)
_FROM_RE = re.compile(r"^FROM\s+(.*)$", re.IGNORECASE)
_TO_RE = re.compile(r"^TO\s+(.*)$", re.IGNORECASE)
_INT_RE = re.compile(r"^INT\s+(.*?)\s*\(.*\)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class GedcomDate:
    raw: str  # always preserved verbatim
    qualifier: Optional[str] = None  # None|ABT|EST|CAL|BEF|AFT|BET|FROM|TO|INT
    year: Optional[int] = None
    month: Optional[int] = None  # 1-12
    day: Optional[int] = None
    year2: Optional[int] = None  # second endpoint of BET…AND / FROM…TO
    month2: Optional[int] = None
    day2: Optional[int] = None


def _parse_core(text: str) -> Optional[tuple[int, Optional[int], Optional[int]]]:
    """Parse a ``[day] [month] year`` fragment, returning ``(year, month, day)``.

    Returns ``None`` if the fragment does not match the grammar (including a
    day given without a month, and an unrecognised month abbreviation).
    """
    m = _CORE_RE.match(text.strip())
    if not m:
        return None
    day_s, month_s, year_s = m.groups()
    month = None
    if month_s:
        month = MONTH_ABBREVIATIONS.get(month_s.upper())
        if month is None:
            return None
    day = int(day_s) if day_s else None
    if day is not None and month is None:
        return None
    return int(year_s), month, day


def parse_gedcom_date(raw: Optional[str]) -> Optional[GedcomDate]:
    """Parse a raw GEDCOM date string into a :class:`GedcomDate`.

    Returns ``None`` only for ``None`` or blank input. Never raises; text
    that does not match the supported grammar comes back as
    ``GedcomDate(raw=raw)`` with every other field ``None``.
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None

    for kw in _SINGLE_QUALIFIERS:
        if text[: len(kw)].upper() == kw and text[len(kw) : len(kw) + 1].isspace():
            core = _parse_core(text[len(kw) :])
            if core is None:
                return GedcomDate(raw=raw)
            year, month, day = core
            return GedcomDate(raw=raw, qualifier=kw, year=year, month=month, day=day)

    m = _BET_AND_RE.match(text)
    if m:
        c1 = _parse_core(m.group(1))
        c2 = _parse_core(m.group(2))
        if c1 is None or c2 is None:
            return GedcomDate(raw=raw)
        y1, mo1, d1 = c1
        y2, mo2, d2 = c2
        return GedcomDate(
            raw=raw,
            qualifier="BET",
            year=y1,
            month=mo1,
            day=d1,
            year2=y2,
            month2=mo2,
            day2=d2,
        )

    m = _FROM_TO_RE.match(text)
    if m:
        c1 = _parse_core(m.group(1))
        c2 = _parse_core(m.group(2))
        if c1 is None or c2 is None:
            return GedcomDate(raw=raw)
        y1, mo1, d1 = c1
        y2, mo2, d2 = c2
        return GedcomDate(
            raw=raw,
            qualifier="FROM",
            year=y1,
            month=mo1,
            day=d1,
            year2=y2,
            month2=mo2,
            day2=d2,
        )

    m = _FROM_RE.match(text)
    if m:
        core = _parse_core(m.group(1))
        if core is None:
            return GedcomDate(raw=raw)
        year, month, day = core
        return GedcomDate(raw=raw, qualifier="FROM", year=year, month=month, day=day)

    m = _TO_RE.match(text)
    if m:
        core = _parse_core(m.group(1))
        if core is None:
            return GedcomDate(raw=raw)
        year, month, day = core
        return GedcomDate(raw=raw, qualifier="TO", year=year, month=month, day=day)

    m = _INT_RE.match(text)
    if m:
        core = _parse_core(m.group(1))
        if core is None:
            return GedcomDate(raw=raw)
        year, month, day = core
        return GedcomDate(raw=raw, qualifier="INT", year=year, month=month, day=day)

    core = _parse_core(text)
    if core is None:
        return GedcomDate(raw=raw)
    year, month, day = core
    return GedcomDate(raw=raw, year=year, month=month, day=day)


def sort_key(d: GedcomDate) -> tuple:
    """Sort key for a :class:`GedcomDate`; unparseable dates sort last.

    Ranges sort by their first endpoint.
    """
    return (
        d.year if d.year is not None else 10**9,
        d.month or 0,
        d.day or 0,
    )
