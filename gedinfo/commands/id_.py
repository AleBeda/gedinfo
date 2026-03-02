"""`gedinfo id` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import find_by_name, display_name
from ._output import strip_id_delimiters


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``id`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "id",
        help=(
            "Search for individuals by partial name match. The query is matched "
            "case-insensitively as a substring against the first name and last name "
            "independently. Prints one line per match: the ID (without @), a tab, and "
            "the full name."
        ),
    )
    sub.add_argument(
        "name",
        help=(
            "Name fragment to search for. Matched as a case-insensitive substring "
            "against first name and last name independently. Slash delimiters (//) "
            "around surnames are accepted and ignored."
        ),
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo id`` is run."""
    data = parse(args.gedcom_file)
    matches = find_by_name(data, args.name)
    for indi in matches:
        print(f"{strip_id_delimiters(indi.id)}\t{display_name(indi)}")
