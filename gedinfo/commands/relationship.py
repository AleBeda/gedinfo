"""`gedinfo relationship` subcommand."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import find_relationships, display_name


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "relationship",
        help="Show all relationships between two individuals",
        description=(
            "Find all common ancestors of two individuals and print each "
            "relationship as a two-column block showing the lineage paths."
        ),
    )
    sub.add_argument("first_id", help="First individual ID")
    sub.add_argument("second_id", help="Second individual ID")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def _format_block(ancestor, path1, path2) -> list[str]:
    names1 = [display_name(p) for p in path1]
    names2 = [display_name(p) for p in path2]
    left_w = max(len(n) for n in names1)
    right_w = max(len(n) for n in names2)

    max_gen = max(len(path1), len(path2))
    gen_w = len(str(max_gen))

    lines = []
    for i in range(max_gen):
        gen_str = f"{i + 1:>{gen_w}}"
        left_name = display_name(path1[i]) if i < len(path1) else ""
        right_name = display_name(path2[i]) if i < len(path2) else ""
        lines.append(f"{gen_str}  {left_name:<{left_w}}  {right_name}".rstrip())

    return lines


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    relationships = find_relationships(data, args.first_id, args.second_id)

    first = True
    for ancestor, path1, path2 in relationships:
        if not first:
            print()
        first = False
        for line in _format_block(ancestor, path1, path2):
            print(line)
