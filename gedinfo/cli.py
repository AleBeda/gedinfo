"""Command-line interface entry point for gedinfo.

This module builds an ``argparse``-based command dispatcher and provides
centralised error handling so that subcommands can raise exceptions and
have user-friendly messages printed.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from .parser import GedcomParseError, parse

# import command modules lazily to avoid circular imports


def main() -> None:
    """Entry point invoked by the ``gedinfo`` console script."""
    parser = argparse.ArgumentParser(prog="gedinfo")
    parser.add_argument(
        "--version", action="store_true", help="Print version and exit"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Show tracebacks on error"
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    # register built-in subcommands
    from .commands import id_ as id_cmd, name as name_cmd, names as names_cmd

    name_cmd.register(subparsers)
    id_cmd.register(subparsers)
    names_cmd.register(subparsers)

    args = parser.parse_args()

    if args.version:
        print("gedinfo 0.1.0")
        sys.exit(0)

    try:
        # dispatch to subcommand handler attached by register()
        assert hasattr(args, "func"), "no handler for command"
        args.func(args)
    except (GedcomParseError, FileNotFoundError, ValueError) as e:
        if getattr(args, "debug", False):
            raise
        print(str(e), file=sys.stderr)
        sys.exit(1)
