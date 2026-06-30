"""`gedinfo strip` subcommand implementation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

_STRUCTURAL_TAGS: frozenset[str] = frozenset(
    {
        "INDI",
        "FAM",
        "FAMS",
        "FAMC",
        "HUSB",
        "WIFE",
        "CHIL",
        "NAME",
        "GIVN",
        "SURN",
        "HEAD",
        "TRLR",
    }
)

_STRUCTURAL_WARNINGS: dict[str, str] = {
    "INDI": "removes entire individual records, including everything nested under them",
    "FAM": "removes entire family records, including everything nested under them",
    "FAMS": "breaks the link from an individual to their family-as-spouse record",
    "FAMC": "breaks the link from an individual to their family-as-child record",
    "HUSB": "breaks the husband link within family records",
    "WIFE": "breaks the wife link within family records",
    "CHIL": "breaks child links within family records",
    "NAME": "removes individuals' names, including any GIVN/SURN substructure",
    "GIVN": "removes the given-name component of NAME structures",
    "SURN": "removes the surname component of NAME structures",
    "HEAD": "removes the mandatory GEDCOM header record, producing an invalid file",
    "TRLR": "removes the mandatory GEDCOM trailer record, producing an invalid file",
}


def _detect_line_ending(raw_text_lines: list[str]) -> str:
    for raw in raw_text_lines:
        if raw.endswith("\r\n"):
            return "\r\n"
        if raw.endswith("\r"):
            return "\r"
        if raw.endswith("\n"):
            return "\n"
    return "\n"


def _split_line(line: str) -> Tuple[int, str, str, Optional[str]]:
    parts = line.split(" ", 2)
    try:
        level = int(parts[0])
    except (ValueError, IndexError):
        return -1, "", "", None
    tag = ""
    value = ""
    xref: Optional[str] = None
    if level == 0 and len(parts) >= 3 and parts[1].startswith("@"):
        xref = parts[1]
        rest = parts[2]
        sub = rest.split(" ", 1)
        tag = sub[0]
        value = sub[1] if len(sub) > 1 else ""
    elif len(parts) >= 2:
        tag = parts[1]
        if len(parts) == 3:
            value = parts[2]
    return level, tag, value, xref


def _strip_lines(raw_lines: list[str], strip_set: set[str]) -> list[str]:
    out: list[str] = []
    strip_level: Optional[int] = None
    for line in raw_lines:
        if not line.strip():
            continue
        level, tag, _value, _xref = _split_line(line)
        if strip_level is not None:
            if level > strip_level:
                continue
            strip_level = None
        if tag.upper() in strip_set:
            strip_level = level
            continue
        out.append(line)
    return out


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``strip`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "strip",
        help="Remove GEDCOM lines matching specified tag(s)",
        description=(
            "Remove lines matching one or more specified GEDCOM tags, along with "
            "all lower-ranking (child) lines nested under each removed line."
        ),
    )
    sub.add_argument(
        "-o",
        "--output",
        help="Write output to FILE instead of stdout",
        metavar="FILE",
    )
    sub.add_argument(
        "fields",
        nargs="+",
        metavar="FIELD",
        help="GEDCOM tag(s) to remove (e.g. NOTE OBJE)",
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args) -> None:
    """Handler invoked when ``gedinfo strip`` is run."""
    strip_set = {f.upper() for f in args.fields}

    risky = strip_set & _STRUCTURAL_TAGS
    for tag in sorted(risky):
        print(f"Warning: stripping {tag} {_STRUCTURAL_WARNINGS[tag]}.", file=sys.stderr)

    p = Path(args.gedcom_file)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {args.gedcom_file}")

    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        raw_text_lines = fh.readlines()

    line_ending = _detect_line_ending(raw_text_lines)
    raw_lines = [line.rstrip("\r\n") for line in raw_text_lines]

    lines = _strip_lines(raw_lines, strip_set)
    text = line_ending.join(lines) + line_ending

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8", newline="")
    else:
        print(text, end="")
