"""`gedinfo name` subcommand implementation."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ..parser import parse, GedcomParseError
from ..queries import display_name, find_by_id


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``name`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "name", help="Print the full name of an individual by ID"
    )
    sub.add_argument("indi_id", help="Individual ID (""@I...@"" optional)")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo name`` is run."""
    data = parse(args.gedcom_file)
    indi = find_by_id(data, args.indi_id)
    if indi is None:
        print(f"ID not found: {args.indi_id}", file=sys.stderr)
        sys.exit(1)
    print(display_name(indi))
