"""`gedinfo relatives` subcommand implementation."""

from __future__ import annotations

import argparse
from typing import Any, Optional

from ..parser import parse
from ..queries import find_by_id, display_name
from ._output import add_output_options, validate_output_mode, strip_id_delimiters


def _parent_label(indi) -> str:
    return {"M": "father:", "F": "mother:"}.get(indi.sex, "parent:")


def _spouse_label(indi) -> str:
    return {"M": "husband:", "F": "wife:"}.get(indi.sex, "spouse:")


def _child_label(indi) -> str:
    return {"M": "son:", "F": "daughter:"}.get(indi.sex, "child:")


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``relatives`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "relatives",
        help="Show immediate family of an individual",
        description="Show immediate family of an individual",
    )
    add_output_options(sub)
    sub.add_argument("-b", "--birth",    action="store_true", help="Print birth date")
    sub.add_argument("-d", "--death",    action="store_true", help="Print death date")
    sub.add_argument("-m", "--marriage", action="store_true", help="Print marriage date")
    sub.add_argument(
        "-l", "--long",
        action="store_true",
        help="Equivalent to -b -d -m",
    )
    sub.add_argument("indi_id",     help="Individual ID")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo relatives`` is run."""
    mode = validate_output_mode(args)
    show_birth    = args.birth    or args.long
    show_death    = args.death    or args.long
    show_marriage = args.marriage or args.long

    data = parse(args.gedcom_file)
    indi = find_by_id(data, args.indi_id)
    if indi is None:
        raise ValueError(f"Unknown individual ID: {args.indi_id}")

    # Each entry: (label, individual_or_none, marriage_date_or_none)
    # None individual with label "(unknown spouse):" is a section header.
    rows: list[tuple[str, Any, Optional[str]]] = []

    # Parents
    for fam_id in indi.family_ids_as_child:
        fam = data.families.get(fam_id)
        if fam is None:
            continue
        for parent_id in [fam.husband_id, fam.wife_id]:
            if not parent_id:
                continue
            parent = data.individuals.get(parent_id)
            if parent is None:
                continue
            rows.append((_parent_label(parent), parent, fam.marriage_date))

    # Self
    rows.append(("self:", indi, None))

    # Spouses and children
    for fam_id in indi.family_ids_as_spouse:
        fam = data.families.get(fam_id)
        if fam is None:
            continue
        other_id = fam.wife_id if fam.husband_id == indi.id else fam.husband_id
        if other_id:
            spouse = data.individuals.get(other_id)
        else:
            spouse = None
        if spouse is not None:
            rows.append((_spouse_label(spouse), spouse, fam.marriage_date))
        elif fam.child_ids:
            rows.append(("(unknown spouse):", None, None))
        # else: no spouse and no children — skip

        for child_id in fam.child_ids:
            child = data.individuals.get(child_id)
            if child is None:
                continue
            rows.append((_child_label(child), child, None))

    # Output
    for label, individual, marriage_date in rows:
        if individual is None:
            print(label)
            continue
        fields: list[str] = []
        if mode in ("id", "both"):
            fields.append(strip_id_delimiters(individual.id))
        if mode in ("name", "both"):
            fields.append(display_name(individual))
        if show_birth:
            fields.append(individual.birth_date or "")
        if show_death:
            fields.append(individual.death_date or "")
        if show_marriage:
            fields.append(marriage_date or "")
        print(label + "\t" + "\t".join(fields))
