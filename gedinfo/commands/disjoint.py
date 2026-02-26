"""`gedinfo disjoint` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import get_connected_components, get_roots
from ._output import add_output_options, validate_output_mode, format_individual


def register(subparsers: argparse._SubparsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "disjoint", help="List roots of each disjoint component"
    )
    add_output_options(sub)
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    mode = validate_output_mode(args)

    components = get_connected_components(data)
    global_root_ids = {i.id for i in get_roots(data)}

    first = True
    for comp in components:
        # find roots in this component
        roots = [i for i in comp if i.id in global_root_ids]
        if not roots:
            # skip empty component root list silently
            continue
        if not first:
            # blank line between components
            print()
        first = False
        for r in roots:
            print(format_individual(r, mode))
