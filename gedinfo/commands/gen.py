"""`gedinfo gen` subcommand — generation depth relative to an individual."""

from __future__ import annotations

import argparse
from typing import Any

from ..errors import UserError
from ..parser import parse
from ..queries import get_ancestor_details, get_descendant_details, find_by_id


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "gen",
        aliases=["generations"],
        help="Count ancestor and descendant generations for an individual",
        description=(
            "Print the maximum number of ascending and descending generations "
            "relative to the specified individual. The individual themselves "
            "counts as generation 1 in the total."
        ),
    )
    sub.add_argument("indi_id", help="Individual ID")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    if find_by_id(data, args.indi_id) is None:
        raise UserError(f"Unknown individual ID: {args.indi_id}")

    anc = get_ancestor_details(data, args.indi_id)
    desc = get_descendant_details(data, args.indi_id)

    nga = max((r["generation"] for r in anc), default=1) - 1
    ngd = max((r["generation"] for r in desc), default=1) - 1
    ngt = nga + ngd + 1

    print(f"ancestors: {nga}\tdescendants: {ngd}\ttotal: {ngt}")
