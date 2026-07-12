"""Command-line interface entry point for gedinfo.

This module builds an ``argparse``-based command dispatcher and provides
centralised error handling so that subcommands can raise exceptions and
have user-friendly messages printed. Only ``UserError`` (and its
subclasses, e.g. ``GedcomParseError``, ``ConfigError``) and
``FileNotFoundError`` are treated as user errors: they print tersely to
stderr with exit code 1. Any other exception, including a bare
``ValueError`` raised by a genuine programming bug, is left to propagate
as a full traceback so it doesn't masquerade as a polite user error.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .errors import UserError

# import command modules lazily to avoid circular imports

# Order defines help output order (registration order == argparse subcommand
# listing order), not import/filesystem order.
_COMMAND_MODULES = [
    "name",
    "id_",
    "names",
    "lastnames",
    "ancestors",
    "descendants",
    "roots",
    "leaves",
    "stat",
    "disjoint",
    "living",
    "givennames",
    "indi",
    "males",
    "females",
    "nosex",
    "noname",
    "fam",
    "relatives",
    "anonymize",
    "strip",
    "calendar",
    "tags",
    "diff",
    "explore",
    "gen",
    "relationship",
]


class _DescriptionFirstParser(argparse.ArgumentParser):
    """Subparser variant that prints description before the usage line."""

    def format_help(self) -> str:
        formatter = self._get_formatter()
        if self.description:
            formatter.add_text(self.description)
        formatter.add_usage(self.usage, self._actions, self._mutually_exclusive_groups)
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
    subparsers = parser.add_subparsers(
        dest="command", parser_class=_DescriptionFirstParser
    )
    subparsers.required = False

    # register built-in subcommands
    import importlib

    for _mod_name in _COMMAND_MODULES:
        importlib.import_module(f".commands.{_mod_name}", __package__).register(
            subparsers
        )

    args = parser.parse_args()

    if args.version:
        print(f"gedinfo {__version__}")
        sys.exit(0)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        # dispatch to subcommand handler attached by register()
        assert hasattr(args, "func"), "no handler for command"
        args.func(args)
    except (UserError, FileNotFoundError) as e:
        if getattr(args, "debug", False):
            raise
        print(str(e), file=sys.stderr)
        sys.exit(1)
