"""`gedinfo leaves` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import get_leaves
from ._output import add_output_options, validate_output_mode, format_individual


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser("leaves", help="List individuals with no children")
    add_output_options(sub)
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    mode = validate_output_mode(args)
    leaves = get_leaves(data)
    for r in leaves:
        print(format_individual(r, mode))
