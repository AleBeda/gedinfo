"""`gedinfo stat` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..reports import collect_stats
import sys


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "stat",
        help="Show statistics about a GEDCOM file",
        description="Show statistics about a GEDCOM file",
    )
    filter_group = sub.add_argument_group("filter options")
    filter_group.add_argument(
        "--spouse",
        action="store_true",
        default=False,
        help=(
            "Include roots whose spouse has parents with at least one known "
            "name. By default such individuals are suppressed."
        ),
    )
    filter_group.add_argument(
        "-u",
        "--unknown",
        action="store_true",
        default=False,
        help=(
            "Include nameless roots (no NAME tag). By default nameless "
            "individuals are suppressed."
        ),
    )
    filter_group.add_argument(
        "-a",
        "--all",
        action="store_true",
        default=False,
        help=(
            "Include all roots without suppression. Cannot be combined with "
            "--spouse or --unknowns."
        ),
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    # validate mutually exclusive flags if present
    if getattr(args, "all", False) and (
        getattr(args, "spouse", False) or getattr(args, "unknown", False)
    ):
        print("--all cannot be combined with --spouse or --unknown", file=sys.stderr)
        sys.exit(1)

    data = parse(args.gedcom_file)

    stats = collect_stats(
        data,
        include_spouse_suppressed=(
            getattr(args, "all", False) or getattr(args, "spouse", False)
        ),
        include_unknowns=(
            getattr(args, "all", False) or getattr(args, "unknown", False)
        ),
    )

    # Print report following specification formatting
    print(f"Individuals: {stats['individuals']}")
    print(f"  Males: {stats['males']}")
    print(f"  Females: {stats['females']}")
    print(f"  Unknown sex: {stats['unknown_sex']}")
    # add optional note when flags change the root count
    note = ""
    if (
        getattr(args, "all", False)
        or getattr(args, "spouse", False)
        or getattr(args, "unknown", False)
    ):
        if getattr(args, "all", False):
            note = "  (all)"
        else:
            parts = []
            if getattr(args, "spouse", False):
                parts.append("+spouse")
            if getattr(args, "unknown", False):
                parts.append("+unknown")
            note = "  (" + ",".join(parts) + ")"
    print(f"  Roots (no parents): {stats['roots']}{note}")
    print(f"  Leaves (no children): {stats['leaves']}")
    print(f"  No name: {stats['no_name']}")
    print(f"  Incomplete name: {stats['incomplete_name']}")
    if data.tag_config.living:
        print(f"  Living ({data.tag_config.living} = Y): {stats['living']}")
    else:
        print("  Living: (no living tag configured)")
    print()
    print(f"Families: {stats['families']}")
    print(
        f"  Families with unnamed/incomplete parent: {stats['unnamed_parent_families']}"
    )
    print(f"  Families with no children: {stats['childless_families']}")
    print()
    print(f"Generations: {stats['generations']}")
    print()
    print(f"Disjoint forests: {stats['disjoint']}")
