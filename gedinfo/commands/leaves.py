"""`gedinfo leaves` subcommand implementation."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ..parser import parse
from ..queries import get_leaves, apply_leaf_filters
from ._output import (
    add_output_options,
    add_sort_option,
    validate_output_mode,
    format_individual,
    get_sort_key,
)


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "leaves",
        help="List individuals with no children",
        description="List individuals with no children",
    )
    add_output_options(sub)
    add_sort_option(sub)
    filter_group = sub.add_argument_group("filter options")
    filter_group.add_argument(
        "--spouse",
        action="store_true",
        default=False,
        help=(
            "Include leaves whose spouse has children with another partner. "
            "By default, such individuals are suppressed because they likely "
            "married into a documented family rather than representing an "
            "independent line."
        ),
    )
    filter_group.add_argument(
        "-u",
        "--unknown",
        action="store_true",
        default=False,
        help=(
            "Include leaves with no name at all (no NAME tag in the GEDCOM "
            "file). By default, nameless individuals are suppressed."
        ),
    )
    filter_group.add_argument(
        "-a",
        "--all",
        action="store_true",
        default=False,
        help=(
            "Include all leaves without any suppression. Equivalent to "
            "combining --spouse and --unknown. Cannot be combined with "
            "--spouse or --unknown."
        ),
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    if getattr(args, "all", False) and (
        getattr(args, "spouse", False) or getattr(args, "unknown", False)
    ):
        print("--all cannot be combined with --spouse or --unknown", file=sys.stderr)
        sys.exit(1)

    data = parse(args.gedcom_file)
    mode = validate_output_mode(args)
    leaves = get_leaves(data, get_sort_key(args))
    leaves = apply_leaf_filters(
        data,
        leaves,
        include_spouse_suppressed=(
            getattr(args, "all", False) or getattr(args, "spouse", False)
        ),
        include_unknown=(
            getattr(args, "all", False) or getattr(args, "unknown", False)
        ),
    )
    for r in leaves:
        print(format_individual(r, mode))
