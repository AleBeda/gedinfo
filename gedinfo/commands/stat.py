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
)


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser("stat", help="Show statistics about a GEDCOM file")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    data = parse(args.gedcom_file)

    total_individuals = len(data.individuals)
    males = sum(1 for i in data.individuals.values() if i.sex == "M")
    females = sum(1 for i in data.individuals.values() if i.sex == "F")
    unknown = sum(1 for i in data.individuals.values() if i.sex == "U")
    roots = len(get_roots(data))
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
    print(f"  Roots (no parents): {roots}")
    print(f"  Leaves (no children): {leaves}")
    print(f"  No name: {no_name}")
    print(f"  Incomplete name: {incomplete}")
    print()
    print(f"Families: {total_families}")
    print(f"  Families with unnamed/incomplete parent: {unnamed_parents}")
    print(f"  Families with no children: {no_children}")
    print()
    print(f"Disjoint forests: {disjoint}")
