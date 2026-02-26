"""`gedinfo ancestors` subcommand implementation."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ..parser import parse
from ..queries import get_ancestors


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``ancestors`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "ancestors", help="Print distinct last names of all ancestors"
    )
    sub.add_argument(
        "-g",
        "--generations",
        type=int,
        default=None,
        help="Limit traversal to N generations (>=1)",
    )
    sub.add_argument("indi_id", help="Individual ID to inspect")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo ancestors`` is run."""
    g = args.generations
    if g is not None and g < 1:
        print("Invalid generations value: must be >= 1", file=sys.stderr)
        sys.exit(1)
    data = parse(args.gedcom_file)
    try:
        surnames = get_ancestors(data, args.indi_id, max_generations=g)
    except ValueError as exc:
        # propagate as CLI-friendly error
        raise ValueError(str(exc))
    for s in surnames:
        print(s)
