"""`gedinfo id` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import find_by_name


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``id`` subcommand with the top-level parser."""
    sub = subparsers.add_parser("id", help="Look up an individual ID by full name")
    sub.add_argument("name", help="Full name (surname may be wrapped in / /)")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo id`` is run."""
    data = parse(args.gedcom_file)
    matches = find_by_name(data, args.name)
    for indi in matches:
        print(indi.id)
