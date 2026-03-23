"""`gedinfo stat` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import (
    count_no_name,
    count_incomplete_name,
    count_families_with_unnamed_parent,
    count_families_no_children,
    get_roots,
    get_leaves,
    get_connected_components,
    apply_root_filters,
)
import sys


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser("stat", help="Show statistics about a GEDCOM file")
    filter_group = sub.add_argument_group("filter options")
    filter_group.add_argument(
        "-s", "--spouse",
        action="store_true",
        default=False,
        help=(
            "Include roots whose spouse has parents with at least one known "
            "name. By default such individuals are suppressed."
        ),
    )
    filter_group.add_argument(
        "-u", "--unknowns",
        action="store_true",
        default=False,
        help=(
            "Include nameless roots (no NAME tag). By default nameless "
            "individuals are suppressed."
        ),
    )
    filter_group.add_argument(
        "-a", "--all",
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
    if getattr(args, "all", False) and (getattr(args, "spouse", False) or getattr(args, "unknowns", False)):
        print("--all cannot be combined with --spouse or --unknowns", file=sys.stderr)
        sys.exit(1)

    data = parse(args.gedcom_file)

    total_individuals = len(data.individuals)
    males = sum(1 for i in data.individuals.values() if i.sex == "M")
    females = sum(1 for i in data.individuals.values() if i.sex == "F")
    unknown = sum(1 for i in data.individuals.values() if i.sex == "U")
    raw_roots = get_roots(data)
    roots_list = apply_root_filters(
        data,
        raw_roots,
        include_spouse_suppressed=(getattr(args, "all", False) or getattr(args, "spouse", False)),
        include_unknowns=(getattr(args, "all", False) or getattr(args, "unknowns", False)),
    )
    roots = len(roots_list)
    leaves = len(get_leaves(data))
    no_name = count_no_name(data)
    incomplete = count_incomplete_name(data)

    total_families = len(data.families)
    unnamed_parents = count_families_with_unnamed_parent(data)
    no_children = count_families_no_children(data)
    disjoint = len(get_connected_components(data))

    # Print report following specification formatting
    print(f"Individuals: {total_individuals}")
    print(f"  Males: {males}")
    print(f"  Females: {females}")
    print(f"  Unknown sex: {unknown}")
    # add optional note when flags change the root count
    note = ""
    if getattr(args, "all", False) or getattr(args, "spouse", False) or getattr(args, "unknowns", False):
        if getattr(args, "all", False):
            note = "  (all)"
        else:
            parts = []
            if getattr(args, "spouse", False):
                parts.append("+spouse")
            if getattr(args, "unknowns", False):
                parts.append("+unknowns")
            note = "  (" + ",".join(parts) + ")"
    print(f"  Roots (no parents): {roots}{note}")
    print(f"  Leaves (no children): {leaves}")
    print(f"  No name: {no_name}")
    print(f"  Incomplete name: {incomplete}")
    print()
    print(f"Families: {total_families}")
    print(f"  Families with unnamed/incomplete parent: {unnamed_parents}")
    print(f"  Families with no children: {no_children}")
    print()
    print(f"Disjoint forests: {disjoint}")
