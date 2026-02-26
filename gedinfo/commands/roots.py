"""`gedinfo roots` subcommand implementation."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ..parser import parse
from ..queries import get_roots
from ._output import add_output_options, validate_output_mode, format_individual


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser("roots", help="List individuals with no parents")
    add_output_options(sub)
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    mode = validate_output_mode(args)
    roots = get_roots(data)
    for r in roots:
        print(format_individual(r, mode))
