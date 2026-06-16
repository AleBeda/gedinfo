"""`gedinfo names` subcommand implementation."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ..parser import parse
from ..queries import display_name, find_by_id, id_sort_key
from ._output import add_sort_option, get_sort_key, strip_id_delimiters


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``names`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "names",
        help="Batch print names for a file containing individual IDs",
        description="Batch print names for a file containing individual IDs",
    )
    sub.add_argument(
        "ids_file",
        help="Path to file with one individual ID per line, or '-' to read from stdin",
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    add_sort_option(sub)
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo names`` is run.

    Reads `ids_file`, ignores blank lines and lines starting with `#`, and
    for each ID prints the corresponding display name or `"<id>: (not found)"`.
    """
    if args.ids_file == "-":
        lines = [ln.rstrip("\n\r") for ln in sys.stdin]
    else:
        try:
            with open(args.ids_file, encoding="utf-8") as fh:
                lines = [ln.rstrip("\n\r") for ln in fh]
        except FileNotFoundError:
            raise FileNotFoundError(f"IDs file not found: {args.ids_file}")

    data = parse(args.gedcom_file)
    results = []  # list of (Individual or None, output_line_string)
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        indi = find_by_id(data, s)
        if indi is None:
            results.append((None, f"{strip_id_delimiters(s)}: (not found)"))
        else:
            results.append((indi, display_name(indi)))

    # Apply sorting
    sort_key = get_sort_key(args)
    if sort_key == "id":
        results.sort(key=lambda r: id_sort_key(r[0].id) if r[0] else (r[1],))
    elif sort_key == "name":
        results.sort(key=lambda r: display_name(r[0]).lower() if r[0] else r[1].lower())

    for _, line in results:
        print(line)
