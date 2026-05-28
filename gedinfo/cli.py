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


class _DescriptionFirstParser(argparse.ArgumentParser):
    """Subparser variant that prints description before the usage line."""

    def format_help(self) -> str:
        formatter = self._get_formatter()
        if self.description:
            formatter.add_text(self.description)
        formatter.add_usage(
            self.usage, self._actions, self._mutually_exclusive_groups
        )
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()
        formatter.add_text(self.epilog)
        return formatter.format_help()


def main() -> None:
    """Entry point invoked by the ``gedinfo`` console script."""
    parser = argparse.ArgumentParser(
        prog="gedinfo",
        epilog="Run 'gedinfo <command> -h' for help on a specific command.",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--debug", action="store_true", help="Show tracebacks on error")
    subparsers = parser.add_subparsers(dest="command", parser_class=_DescriptionFirstParser)
    subparsers.required = False

    # register built-in subcommands
    from .commands import (
        id_ as id_cmd,
        name as name_cmd,
        names as names_cmd,
        lastnames as lastnames_cmd,
        ancestors as ancestors_cmd,
        descendants as descendants_cmd,
        roots as roots_cmd,
        leaves as leaves_cmd,
        stat as stat_cmd,
        disjoint as disjoint_cmd,
        living as living_cmd,
        givennames as givennames_cmd,
        indi as indi_cmd,
        males as males_cmd,
        females as females_cmd,
        nosex as nosex_cmd,
        fam as fam_cmd,
        relatives as relatives_cmd,
        anonymize as anonymize_cmd,
    )

    name_cmd.register(subparsers)
    id_cmd.register(subparsers)
    names_cmd.register(subparsers)
    lastnames_cmd.register(subparsers)
    ancestors_cmd.register(subparsers)
    descendants_cmd.register(subparsers)
    roots_cmd.register(subparsers)
    leaves_cmd.register(subparsers)
    stat_cmd.register(subparsers)
    disjoint_cmd.register(subparsers)
    living_cmd.register(subparsers)
    givennames_cmd.register(subparsers)
    indi_cmd.register(subparsers)
    males_cmd.register(subparsers)
    females_cmd.register(subparsers)
    nosex_cmd.register(subparsers)
    fam_cmd.register(subparsers)
    relatives_cmd.register(subparsers)
    anonymize_cmd.register(subparsers)

    args = parser.parse_args()

    if args.version:
        print("gedinfo 0.12.3")
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
