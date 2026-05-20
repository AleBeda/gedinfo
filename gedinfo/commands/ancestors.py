"""`gedinfo ancestors` subcommand implementation."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ..parser import parse
from ..queries import get_ancestor_details, find_by_id
from ._output import add_output_options, validate_output_mode, format_individual, strip_id_delimiters


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``ancestors`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "ancestors",
        help="List all ancestors of an individual",
        description="List all ancestors of an individual",
    )
    add_output_options(sub)
    sub.add_argument(
        "-g", "--generations",
        type=int, default=None,
        help="Limit traversal to N generations (>=1)",
    )
    sub.add_argument(
        "-l", "--long",
        action="store_true",
        help="Print long output (generation, path, last name, ID)",
    )
    sub.add_argument(
        "-s", "--sort",
        choices=["generation", "path", "name", "id"], default=None,
        help="Sort order for --long mode",
    )
    sub.add_argument(
        "-u", "--unknown",
        action="store_true", default=False,
        help="Include ancestors with no name in --long mode",
    )
    sub.add_argument("indi_id", help="Individual ID")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def _path_to_sort_key(path: str) -> tuple:
    char_map = {'p': 0, '?': 1, 'm': 2}
    return tuple(char_map.get(ch, 3) for ch in path)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo ancestors`` is run."""
    g = args.generations
    if g is not None and g < 1:
        print("Invalid generations value: must be >= 1", file=sys.stderr)
        sys.exit(1)
    if args.sort and not args.long:
        print("--sort requires --long", file=sys.stderr)
        sys.exit(1)
    if args.long and (args.id or args.name):
        print("--long cannot be combined with --id or --name", file=sys.stderr)
        sys.exit(1)

    data = parse(args.gedcom_file)
    subject = find_by_id(data, args.indi_id)
    if subject is None:
        raise ValueError(f"Unknown individual ID: {args.indi_id}")

    details = get_ancestor_details(data, args.indi_id, max_generations=g)
    records = [{"individual": subject, "generation": 1, "path": ""}] + details

    if not args.long:
        mode = validate_output_mode(args)
        for rec in records:
            print(format_individual(rec["individual"], mode))
        return

    # Long mode
    if not args.unknown:
        records = [
            r for r in records
            if r["generation"] == 1
            or r["individual"].first_name
            or r["individual"].last_name
        ]

    sort_key = args.sort or "generation"
    if sort_key == "generation":
        records.sort(key=lambda r: (r["generation"], _path_to_sort_key(r["path"])))
    elif sort_key == "path":
        records.sort(key=lambda r: (
            _path_to_sort_key(r["path"]),
            (r["individual"].last_name or "").lower(),
            r["individual"].id,
        ))
    elif sort_key == "name":
        records.sort(key=lambda r: (
            (r["individual"].last_name or "").lower() if r["individual"].last_name else "~",
            _path_to_sort_key(r["path"]),
            r["individual"].id,
        ))
    elif sort_key == "id":
        records.sort(key=lambda r: r["individual"].id)

    for r in records:
        indi = r["individual"]
        last = indi.last_name or "(unknown)"
        id_str = strip_id_delimiters(indi.id)
        extra_tab = "\t" if len(last) < 8 else ""
        print(f"{r['generation']}\t{r['path']}\t{last}{extra_tab}\t{id_str}")
