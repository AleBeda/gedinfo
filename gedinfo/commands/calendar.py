"""`gedinfo calendar` subcommand — list birth, death, and marriage anniversaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

_MONTH = {
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
_FULL_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_DATE_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$")


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    m = _DATE_RE.match(s.strip())
    if not m:
        return None
    month = _MONTH.get(m.group(2).upper())
    if month is None:
        return None
    try:
        return date(int(m.group(3)), month, int(m.group(1)))
    except ValueError:
        return None


def _parse_month_name(name: str) -> Optional[int]:
    lower = name.lower().strip()
    if lower in _FULL_MONTHS:
        return _FULL_MONTHS[lower]
    return _MONTH.get(lower[:3].upper())


def _display_name(indi) -> str:
    parts = [p for p in (indi.first_name, indi.last_name) if p]
    return " ".join(parts) if parts else "(unknown)"


@dataclass
class _Event:
    date: date
    kind: str  # "birth", "death", "marriage"
    name: str


def _collect_events(data) -> list[_Event]:
    events: list[_Event] = []
    for indi in data.individuals.values():
        d = _parse_date(indi.birth_date)
        if d:
            events.append(_Event(d, "birth", _display_name(indi)))
        d = _parse_date(indi.death_date)
        if d:
            events.append(_Event(d, "death", _display_name(indi)))
    for fam in data.families.values():
        d = _parse_date(fam.marriage_date)
        if d:
            husb = data.individuals.get(fam.husband_id)
            wife = data.individuals.get(fam.wife_id)
            h_name = _display_name(husb) if husb else "(unknown)"
            w_name = _display_name(wife) if wife else "(unknown)"
            events.append(_Event(d, "marriage", f"{h_name} & {w_name}"))
    return events


def _format_event(event: _Event, date_fmt: str) -> str:
    return f"{event.date.strftime(date_fmt)}\t{event.kind:<8}\t{event.name}"


def register(subparsers) -> None:
    """Register the ``calendar`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "calendar",
        help="List birth, death, and marriage anniversaries from a GEDCOM file",
        description="List birth, death, and marriage anniversaries from a GEDCOM file",
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Write output to FILE instead of stdout",
    )
    sub.add_argument(
        "--today",
        action="store_true",
        help="Show only events matching today's day and month",
    )
    sub.add_argument(
        "--thismonth",
        action="store_true",
        help="Show only events in the current calendar month",
    )
    sub.add_argument(
        "--month",
        metavar="MONTHNAME",
        default=None,
        help="Show only events in the specified month (full name or 3-letter abbreviation, any case)",
    )
    sub.add_argument(
        "--dateformat",
        metavar="PATTERN",
        default="%d %b %Y",
        help='strftime pattern for dates (default: "%%d %%b %%Y")',
    )
    sub.add_argument(
        "--nosep",
        action="store_true",
        help="Do not print blank lines between day-month groups",
    )
    sub.set_defaults(func=run)


def run(args) -> None:
    """Handler invoked when ``gedinfo calendar`` is run."""
    active_filters = sum([args.today, args.thismonth, args.month is not None])
    if active_filters > 1:
        raise ValueError("--today, --thismonth, and --month are mutually exclusive")

    from ..parser import parse

    data = parse(args.gedcom_file)
    events = _collect_events(data)

    today = date.today()
    if args.today:
        events = [
            e for e in events if (e.date.month, e.date.day) == (today.month, today.day)
        ]
    elif args.thismonth:
        events = [e for e in events if e.date.month == today.month]
    elif args.month is not None:
        month_num = _parse_month_name(args.month)
        if month_num is None:
            raise ValueError(f"Unknown month: {args.month!r}")
        events = [e for e in events if e.date.month == month_num]

    events.sort(key=lambda e: (e.date.month, e.date.day, e.date.year))

    lines: list[str] = []
    prev_md: tuple | None = None
    for e in events:
        md = (e.date.month, e.date.day)
        if not args.nosep and prev_md is not None and md != prev_md:
            lines.append("")
        lines.append(_format_event(e, args.dateformat))
        prev_md = md

    text = "\n".join(lines) + ("\n" if lines else "")
    if args.output:
        Path(args.output).write_text(text)
    else:
        print(text, end="")
