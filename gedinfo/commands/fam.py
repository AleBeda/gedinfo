"""`gedinfo fam` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any

from ..parser import parse
from ..queries import display_name, get_all_families
from ._output import (
    add_output_options,
    add_sort_option,
    format_individual,
    get_sort_key,
    strip_id_delimiters,
    validate_output_mode,
)


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    sub = subparsers.add_parser(
        "fam",
        help="List all families with their components",
        description=(
            "List all family records showing the family ID, husband, wife, "
            "and children. Missing parents show as '(none)'. Families with "
            "no children show '(none)' in the children column."
        ),
    )
    add_output_options(sub)
    add_sort_option(sub)
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def _format_family_line(family, data, mode):
    """Format one family as a tab-separated line.

    Format: FAM_ID \t father \t mother \t children
    In 'id' mode: IDs without @ delimiters.
    In 'name' mode: display names.
    In 'both' mode: ID\tName for parents, comma-separated names for children.
    """
    fam_id = strip_id_delimiters(family.id)

    if mode == "id":
        husband = (
            strip_id_delimiters(family.husband_id) if family.husband_id else "(none)"
        )
        wife = strip_id_delimiters(family.wife_id) if family.wife_id else "(none)"
        children = (
            ", ".join(strip_id_delimiters(c) for c in family.child_ids)
            if family.child_ids
            else "(none)"
        )
        return f"{fam_id}\t{husband}\t{wife}\t{children}"
    elif mode == "name":
        husband = _name_or_none(family.husband_id, data)
        wife = _name_or_none(family.wife_id, data)
        children = _children_names(family.child_ids, data)
        return f"{fam_id}\t{husband}\t{wife}\t{children}"
    else:
        # 'both': ID\tName for parents, comma-separated names for children
        husband = _both_or_none(family.husband_id, data)
        wife = _both_or_none(family.wife_id, data)
        children = _children_names(family.child_ids, data)
        return f"{fam_id}\t{husband}\t{wife}\t{children}"


def _name_or_none(indi_id, data):
    if indi_id and indi_id in data.individuals:
        return display_name(data.individuals[indi_id])
    return "(none)"


def _both_or_none(indi_id, data):
    if indi_id and indi_id in data.individuals:
        return format_individual(data.individuals[indi_id], "both")
    return "(none)"


def _children_names(child_ids, data):
    if not child_ids:
        return "(none)"
    names = []
    for cid in child_ids:
        if cid in data.individuals:
            names.append(display_name(data.individuals[cid]))
        else:
            names.append(strip_id_delimiters(cid))
    return ", ".join(names)


def run(args: Any) -> None:
    data = parse(args.gedcom_file)
    mode = validate_output_mode(args)
    families = get_all_families(data, get_sort_key(args))
    for fam in families:
        print(_format_family_line(fam, data, mode))
