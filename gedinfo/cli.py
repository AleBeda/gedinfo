"""Command-line interface entry point for gedinfo.

This module builds an ``argparse``-based command dispatcher and provides
centralised error handling so that subcommands can raise exceptions and
have user-friendly messages printed.
"""

from __future__ import annotations

import argparse
import sys

from .parser import GedcomParseError

# import command modules lazily to avoid circular imports


def main() -> None:
    """Entry point invoked by the ``gedinfo`` console script."""
    parser = argparse.ArgumentParser(prog="gedinfo")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--debug", action="store_true", help="Show tracebacks on error")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = False

    # register built-in subcommands
    from .commands import (
        id_ as id_cmd,
        name as name_cmd,
        names as names_cmd,
        ancestors as ancestors_cmd,
        roots as roots_cmd,
        leaves as leaves_cmd,
        stat as stat_cmd,
        disjoint as disjoint_cmd,
        living as living_cmd,
    )

    name_cmd.register(subparsers)
    id_cmd.register(subparsers)
    names_cmd.register(subparsers)
    ancestors_cmd.register(subparsers)
    roots_cmd.register(subparsers)
    leaves_cmd.register(subparsers)
    stat_cmd.register(subparsers)
    disjoint_cmd.register(subparsers)
    living_cmd.register(subparsers)

    args = parser.parse_args()

    if args.version:
        print("gedinfo 0.4.0")
        sys.exit(0)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        # dispatch to subcommand handler attached by register()
        assert hasattr(args, "func"), "no handler for command"
        args.func(args)
    except (GedcomParseError, FileNotFoundError, ValueError) as e:
        if getattr(args, "debug", False):
            raise
        print(str(e), file=sys.stderr)
        sys.exit(1)
