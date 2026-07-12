"""Shared output formatting helpers for `gedinfo` commands.

Provides mutually-exclusive `-i`/`-n` output flags, `--sort` option,
and formatting helpers used by `roots`, `leaves`, `disjoint`, `living`,
`indi`, `males`, `females`, `nosex`, and `fam` commands.
"""

from __future__ import annotations

import argparse
import sys
from typing import Literal

from ..queries import display_name
from ..models import Individual


def strip_id_delimiters(s: str) -> str:
    """Return the ID without surrounding '@' characters.

    Accepts values like '@I123@' or 'I123' and returns 'I123'.
    """
    return s.strip().strip("@").strip()


def add_output_options(parser: argparse.ArgumentParser) -> None:
    """Add mutually exclusive `-i`/`-n` flags to *parser*.

    The flags indicate whether to print IDs only (`-i`) or names only
    (`-n`). If neither is supplied, the default is to print both.
    """
    # we deliberately do not use argparse's mutually-exclusive group here
    # because we want to handle conflicts ourselves and exit with code 1
    # (argparse would otherwise exit with code 2).  The `validate_output_mode`
    # helper checks for both flags and prints an appropriate error message.
    parser.add_argument("-i", "--id", action="store_true", help="Print IDs only")
    parser.add_argument("-n", "--name", action="store_true", help="Print names only")


def validate_output_mode(args: argparse.Namespace) -> Literal["id", "name", "both"]:
    """Return the effective output mode or exit with a usage error.

    Returns one of: `'id'`, `'name'`, `'both'`.
    """
    if getattr(args, "id", False) and getattr(args, "name", False):
        print(
            "Conflicting output flags: -i and -n are mutually exclusive",
            file=sys.stderr,
        )
        sys.exit(1)
    if getattr(args, "id", False):
        return "id"
    if getattr(args, "name", False):
        return "name"
    return "both"


def format_individual(ind: Individual, mode: Literal["id", "name", "both"]) -> str:
    """Format an `Individual` according to *mode*.

    - `'id'`: returns the ID
    - `'name'`: returns the display name
    - `'both'`: returns `<id>  <display_name>` (two spaces)
    """
    if mode == "id":
        return strip_id_delimiters(ind.id)
    if mode == "name":
        return display_name(ind)
    return f"{strip_id_delimiters(ind.id)}\t{display_name(ind)}"


def add_sort_option(parser: argparse.ArgumentParser) -> None:
    """Add `-s/--sort {id,name}` option to *parser*."""
    parser.add_argument(
        "-s",
        "--sort",
        choices=["id", "name"],
        default=None,
        help="Sort output: 'id' for numeric ID order, 'name' for alphabetical by name. Default is GEDCOM file order.",
    )


def get_sort_key(args: argparse.Namespace) -> str | None:
    """Return the --sort value from *args*, or None if not specified."""
    return getattr(args, "sort", None)
