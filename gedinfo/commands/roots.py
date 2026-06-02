"""`gedinfo roots` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import get_roots, apply_root_filters
import sys
from ._output import add_output_options, add_sort_option, validate_output_mode, format_individual, get_sort_key


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "roots",
        help="List individuals with no recorded parents (roots of the family tree).",
        description="List individuals with no recorded parents (roots of the family tree).",
    )
    add_output_options(sub)
    add_sort_option(sub)
    filter_group = sub.add_argument_group("filter options")
    filter_group.add_argument(
        "--spouse",
        action="store_true",
        default=False,
        help=(
            "Include roots whose spouse has parents with at least one known "
            "name. By default, such individuals are suppressed because they "
            "likely married into a documented family rather than representing "
            "an independent lineage."
        ),
    )
    filter_group.add_argument(
        "-u", "--unknown",
        action="store_true",
        default=False,
        help=(
            "Include roots with no name at all (no NAME tag in the GEDCOM "
            "file). By default, nameless individuals are suppressed."
        ),
    )
    filter_group.add_argument(
        "-a", "--all",
        action="store_true",
        default=False,
        help=(
            "Include all roots without any suppression. Equivalent to "
            "combining --spouse and --unknowns, and will also disable any "
            "future suppression categories. Cannot be combined with "
            "--spouse or --unknowns."
        ),
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    # validate mutually exclusive flags
    if getattr(args, "all", False) and (getattr(args, "spouse", False) or getattr(args, "unknown", False)):
        print("--all cannot be combined with --spouse or --unknown", file=sys.stderr)
        sys.exit(1)

    mode = validate_output_mode(args)
    roots = get_roots(data, get_sort_key(args))
    roots = apply_root_filters(
        data,
        roots,
        include_spouse_suppressed=(getattr(args, "all", False) or getattr(args, "spouse", False)),
        include_unknowns=(getattr(args, "all", False) or getattr(args, "unknown", False)),
    )
    for r in roots:
        print(format_individual(r, mode))
