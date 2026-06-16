"""`gedinfo living` subcommand implementation."""

from __future__ import annotations

import argparse
from gedinfo import parser as parser_module
from gedinfo import queries
from gedinfo.commands import _output
from gedinfo.config import require_tag


def register(subparsers: argparse._SubParsersAction) -> None:    # type: ignore
    parser = subparsers.add_parser(
        "living",
        help="List individuals marked by the configured living-flag tag.",
        description=(
            "List individuals whose configured living-flag tag is set to a "
            "truthy value (Y, yes, true — case-insensitive). Use -v/--invert "
            "to list individuals who are not marked as living: those with an "
            "explicit non-living value, an empty value, or no living-flag "
            "tag at all."
        ),
    )
    parser.add_argument("gedcom_file", help="Path to the GEDCOM file.")
    _output.add_output_options(parser)
    _output.add_sort_option(parser)
    parser.add_argument(
        "-v",
        "--invert",
        action="store_true",
        default=False,
        help=(
            "Invert the match: list individuals who are NOT marked as "
            "living. Includes those with an explicit non-living value "
            "(e.g. N, no, false), those with an empty value, "
            "and those with no living-flag tag at all."
        ),
    )
    parser.set_defaults(func=handle)


def handle(args: argparse.Namespace) -> None:
    data = parser_module.parse(args.gedcom_file)
    require_tag(data.tag_config, "living")
    mode = _output.validate_output_mode(args)
    sort_key = _output.get_sort_key(args)
    if getattr(args, "invert", False):
        individuals = queries.get_not_living(data, sort_key)
    else:
        individuals = queries.get_living(data, sort_key)
    for individual in individuals:
        print(_output.format_individual(individual, mode))
