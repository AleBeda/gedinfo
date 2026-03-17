"""`gedinfo disjoint` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import get_connected_components, get_roots, filter_spouse_roots
from ..models import GedcomData
from ._output import add_output_options, validate_output_mode, format_individual


def register(subparsers: argparse._SubparsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "disjoint", help="List roots of each disjoint component"
    )
    add_output_options(sub)
    sub.add_argument(
        "-s", "--spouse",
        action="store_true",
        default=False,
        help=(
            "As per the roots command: suppress roots whose spouse "
            "has at least one recorded parent. If this suppression "
            "removes all roots from a connected component, that "
            "component is shown with a single placeholder line "
            '"(roots suppressed)" instead of individual entries.'
        ),
    )
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def render_component(
    data: GedcomData, component: list[Individual], mode: str, apply_spouse_filter: bool
) -> list[str]:
    """Return the output lines for one disjoint component.

    If apply_spouse_filter is True, roots whose spouses have parents are
    suppressed. If suppression removes all roots, returns ['(roots suppressed)'].
    """
    # Find roots in this component
    component_roots = [i for i in component if not i.family_ids_as_child]
    
    if apply_spouse_filter:
        filtered_roots = filter_spouse_roots(data, component_roots)
    else:
        filtered_roots = component_roots

    if filtered_roots:
        return [format_individual(r, mode) for r in filtered_roots]
    else:
        return ["(roots suppressed)"]


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    mode = validate_output_mode(args)

    components = get_connected_components(data)

    first = True
    for comp in components:
        lines = render_component(data, comp, mode, getattr(args, "spouse", False))
        if not lines:
            # Skip empty components
            continue
        if not first:
            # blank line between components
            print()
        first = False
        for line in lines:
            print(line)
