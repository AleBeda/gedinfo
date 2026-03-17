"""`gedinfo roots` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import get_roots, filter_spouse_roots
from ._output import add_output_options, validate_output_mode, format_individual


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "roots",
        help=(
            "List individuals with no recorded parents (roots of the family tree). "
            "By default all such individuals are listed. Use -s/--spouse to suppress "
            "roots whose spouse has at least one recorded parent, as these individuals "
            "are typically spouses who married into the tree rather than independent "
            "lineage starting points."
        ),
    )
    add_output_options(sub)
    sub.add_argument(
        "-s", "--spouse",
        action="store_true",
        default=False,
        help=(
            "Suppress roots whose spouse has parents. An individual with no "
            "parents is excluded from the output if at least one of their "
            "spouses has at least one recorded parent in the GEDCOM file."
        ),
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    mode = validate_output_mode(args)
    roots = get_roots(data)
    if getattr(args, "spouse", False):
        roots = filter_spouse_roots(data, roots)
    for r in roots:
        print(format_individual(r, mode))
