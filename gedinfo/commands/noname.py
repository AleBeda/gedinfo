"""`gedinfo noname` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import get_noname
from ._output import (
    add_output_options,
    add_sort_option,
    validate_output_mode,
    format_individual,
    get_sort_key,
)


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "noname",
        help="List individuals with no name recorded",
        description="List individuals with no name recorded",
    )
    add_output_options(sub)
    add_sort_option(sub)
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    mode = validate_output_mode(args)
    individuals = get_noname(data, get_sort_key(args))
    for ind in individuals:
        print(format_individual(ind, mode))
