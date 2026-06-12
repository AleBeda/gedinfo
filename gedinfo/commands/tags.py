"""`gedinfo tags` subcommand implementation."""

from __future__ import annotations

import argparse
import pathlib
from typing import Any

_TAGS_FILE = pathlib.Path(__file__).parent.parent / "data" / "gedcom551_tags.txt"


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "tags",
        help="List all GEDCOM tags found in a file with occurrence counts",
        description="List all GEDCOM tags found in a file with occurrence counts.",
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    standard_tags = frozenset(_TAGS_FILE.read_text(encoding="utf-8").split())

    counts: dict[str, int] = {}
    with open(args.gedcom_file, encoding="utf-8-sig") as f:
        for line in f:
            parts = line.split()
            if not parts or not parts[0].isdigit():
                continue
            if len(parts) >= 2 and parts[1].startswith("@"):
                tag = parts[2] if len(parts) >= 3 else None
            else:
                tag = parts[1] if len(parts) >= 2 else None
            if tag:
                counts[tag] = counts.get(tag, 0) + 1

    if not counts:
        return

    count_width = len(str(max(counts.values())))
    for tag in sorted(counts):
        flag = "" if tag in standard_tags else "not in GEDCOM 5.5.1"
        print(f"{tag}\t{counts[tag]:>{count_width}}\t{flag}")
