"""`gedinfo disjoint` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any
from ..models import Individual

from ..parser import parse
from ..queries import get_connected_components, apply_root_filters
from ..models import GedcomData
import sys
from ._output import add_output_options, validate_output_mode, format_individual


def register(subparsers: argparse._SubparsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "disjoint",
        help="List roots of each disjoint component",
        description="List roots of each disjoint component",
    )
    add_output_options(sub)
    filter_group = sub.add_argument_group("filter options")
    filter_group.add_argument(
        "--spouse",
        action="store_true",
        default=False,
        help=(
            "Include roots whose spouse has parents with at least one known "
            "name. By default such individuals are suppressed."
        ),
    )
    filter_group.add_argument(
        "-u",
        "--unknown",
        action="store_true",
        default=False,
        help=(
            "Include nameless roots (no NAME tag). By default nameless "
            "individuals are suppressed."
        ),
    )
    filter_group.add_argument(
        "-a",
        "--all",
        action="store_true",
        default=False,
        help=(
            "Include all roots without suppression. Cannot be combined with "
            "--spouse or --unknowns."
        ),
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def render_component(
    data: GedcomData,
    component: list[Individual],
    mode: str,
    include_spouse_suppressed: bool,
    include_unknowns: bool,
) -> list[str]:
    """Return the output lines for one disjoint component.

    Applies apply_root_filters to the component's roots. If the result is
    empty:
      - If include_spouse_suppressed is True (i.e. -s or -a was passed) and
        the component had roots before filtering, return ['(roots suppressed)'].
      - Otherwise (default suppression removed everything), return [] to
        indicate the component should be skipped silently.
    """
    component_roots = [i for i in component if not i.family_ids_as_child]
    if not component_roots:
        return []

    final_roots = apply_root_filters(
        data,
        component_roots,
        include_spouse_suppressed=include_spouse_suppressed,
        include_unknowns=include_unknowns,
    )

    if final_roots:
        return [format_individual(r, mode) for r in final_roots]

    # no final roots
    if include_spouse_suppressed:
        # suppression was explicitly requested but still removed everything
        return ["(roots suppressed)"]
    # default suppression removed everything — skip silently
    return []


def run(args: Any) -> None:
    # validate mutually exclusive flags
    if getattr(args, "all", False) and (
        getattr(args, "spouse", False) or getattr(args, "unknown", False)
    ):
        print("--all cannot be combined with --spouse or --unknown", file=sys.stderr)
        sys.exit(1)

    data = parse(args.gedcom_file)
    mode = validate_output_mode(args)

    components = get_connected_components(data)

    first = True
    for comp in components:
        lines = render_component(
            data,
            comp,
            mode,
            include_spouse_suppressed=(
                getattr(args, "all", False) or getattr(args, "spouse", False)
            ),
            include_unknowns=(
                getattr(args, "all", False) or getattr(args, "unknown", False)
            ),
        )
        if not lines:
            # Skip empty components
            continue
        if not first:
            # blank line between components
            print()
        first = False
        for line in lines:
            print(line)
