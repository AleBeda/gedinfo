"""`gedinfo explore` subcommand — interactive family tree browser."""

from __future__ import annotations

import argparse
from typing import Any

from ..errors import UserError


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "explore",
        help="Browse a GEDCOM file interactively in the terminal",
        description=(
            "Launch an interactive terminal browser for a GEDCOM file.\n\n"
            "With no arguments, opens with an empty state (use 'o' to load a file).\n"
            "With one argument, opens the specified GEDCOM file.\n"
            "With two arguments, opens the file starting at the given individual ID."
        ),
    )
    sub.add_argument(
        "positional",
        nargs="*",
        metavar="ARG",
        help="[<indi_id>] <gedcom_file>",
    )
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    positional = args.positional
    if len(positional) > 2:
        raise UserError("explore: too many arguments (expected [INDIID] GEDCOMFILE)")

    file_path = positional[-1] if positional else None
    initial_id = positional[0] if len(positional) == 2 else None

    data = None
    if file_path:
        from gedinfo.parser import parse

        data = parse(file_path)

    from gedinfo.tui import run_tui

    run_tui(data, file_path, initial_id=initial_id)
