"""`gedinfo calendar` subcommand — list birth, death, and marriage anniversaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from ..dates import MONTH_ABBREVIATIONS, parse_gedcom_date
from ..errors import UserError
from ..queries import display_name

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


def _parse_full_date(s: Optional[str]) -> Optional[date]:
    """Parse a raw GEDCOM date into a full ``date``, or ``None``.

    Only dates with a year, month, and day all present qualify (an
    anniversary needs a full date); qualifiers (``ABT``, ``BEF``, …) are
    accepted as long as the underlying date is complete.
    """
    gd = parse_gedcom_date(s)
    if gd is None or gd.year is None or gd.month is None or gd.day is None:
        return None
    try:
        return date(gd.year, gd.month, gd.day)
    except ValueError:
        return None


def _parse_month_name(name: str) -> Optional[int]:
    lower = name.lower().strip()
    if lower in _FULL_MONTHS:
        return _FULL_MONTHS[lower]
    return MONTH_ABBREVIATIONS.get(lower[:3].upper())


@dataclass
class _Event:
    date: date
    kind: str  # "birth", "death", "marriage"
    name: str


def _collect_events(data) -> list[_Event]:
    events: list[_Event] = []
    for indi in data.individuals.values():
        d = _parse_full_date(indi.birth_date)
        if d:
            events.append(_Event(d, "birth", display_name(indi)))
        d = _parse_full_date(indi.death_date)
        if d:
            events.append(_Event(d, "death", display_name(indi)))
    for fam in data.families.values():
        d = _parse_full_date(fam.marriage_date)
        if d:
            husb = data.individuals.get(fam.husband_id)
            wife = data.individuals.get(fam.wife_id)
            h_name = display_name(husb) if husb else "(unknown)"
            w_name = display_name(wife) if wife else "(unknown)"
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
        raise UserError("--today, --thismonth, and --month are mutually exclusive")

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
            raise UserError(f"Unknown month: {args.month!r}")
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
