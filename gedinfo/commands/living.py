"""`gedinfo living` subcommand implementation."""

from __future__ import annotations

import argparse
from gedinfo import parser as parser_module
from gedinfo import queries
from gedinfo.commands import _output


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    parser = subparsers.add_parser(
        "living",
        help="List individuals with a _LIVING flag.",
        description=(
            "List individuals whose _LIVING field is set to a truthy value "
            "(Y, yes, true — case-insensitive). Use -v/--invert to list "
            "individuals who are not marked as living: those with an "
            "explicit non-living value, an empty value, or no _LIVING "
            "tag at all."
        ),
    )
    parser.add_argument("gedcom_file", help="Path to the GEDCOM file.")
    _output.add_output_options(parser)
    parser.add_argument(
        "-v",
        "--invert",
        action="store_true",
        default=False,
        help=(
            "Invert the match: list individuals who are NOT marked as "
            "living. Includes those with an explicit non-living _LIVING "
            "value (e.g. N, no, false), those with an empty _LIVING value, "
            "and those with no _LIVING tag at all."
        ),
    )
    parser.set_defaults(func=handle)


def handle(args: argparse.Namespace) -> None:
    data = parser_module.parse(args.gedcom_file)
    mode = _output.validate_output_mode(args)
    if getattr(args, "invert", False):
        individuals = queries.get_not_living(data)
    else:
        individuals = queries.get_living(data)
    for individual in individuals:
        print(_output.format_individual(individual, mode))
