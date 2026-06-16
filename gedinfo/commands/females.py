"""`gedinfo females` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import get_females
from ._output import (
    add_output_options,
    add_sort_option,
    format_individual,
    validate_output_mode,
    get_sort_key,
)


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "females",
        help="List all female individuals",
        description="List all female individuals",
    )
    add_output_options(sub)
    add_sort_option(sub)
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    mode = validate_output_mode(args)
    for ind in get_females(data, get_sort_key(args)):
        print(format_individual(ind, mode))
