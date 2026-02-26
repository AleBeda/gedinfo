"""`gedinfo names` subcommand implementation."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ..parser import parse
from ..queries import display_name, find_by_id


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``names`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "names", help="Batch print names for a file containing individual IDs"
    )
    sub.add_argument("ids_file", help="Path to file with one individual ID per line")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo names`` is run.

    Reads `ids_file`, ignores blank lines and lines starting with `#`, and
    for each ID prints the corresponding display name or `"<id>: (not found)"`.
    """
    try:
        with open(args.ids_file, encoding="utf-8") as fh:
            lines = [ln.rstrip("\n\r") for ln in fh]
    except FileNotFoundError:
        raise FileNotFoundError(f"IDs file not found: {args.ids_file}")

    data = parse(args.gedcom_file)
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        indi = find_by_id(data, s)
        if indi is None:
            print(f"{s}: (not found)")
        else:
            print(display_name(indi))
