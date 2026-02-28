"""`gedinfo ancestors` subcommand implementation."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ..parser import parse
from ..queries import get_ancestors, get_ancestor_details


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``ancestors`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "ancestors", help="Print distinct last names of all ancestors"
    )
    sub.add_argument(
        "-g",
        "--generations",
        type=int,
        default=None,
        help="Limit traversal to N generations (>=1)",
    )
    sub.add_argument(
        "-l",
        "--long",
        action="store_true",
        help="Print long ancestor details (path, generation, last name, id)",
    )
    sub.add_argument(
        "-s",
        "--sort",
        choices=["generation", "path", "name", "id"],
        default=None,
        help="Sort order for --long mode",
    )
    sub.add_argument("indi_id", help="Individual ID to inspect")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo ancestors`` is run."""
    g = args.generations
    if g is not None and g < 1:
        print("Invalid generations value: must be >= 1", file=sys.stderr)
        sys.exit(1)
    if getattr(args, "sort", None) and not getattr(args, "long", False):
        print("--sort requires --long", file=sys.stderr)
        sys.exit(1)
    data = parse(args.gedcom_file)
    try:
        if args.long:
            records = get_ancestor_details(data, args.indi_id, max_generations=g)
        else:
            surnames = get_ancestors(data, args.indi_id, max_generations=g)
    except ValueError as exc:
        raise ValueError(str(exc))

    if not args.long:
        for s in surnames:
            print(s)
        return

    # Filter to branch-tip ancestors only
    def is_branch_tip(rec: dict) -> bool:
        indi = rec["individual"]
        gen = rec["generation"]
        # no recorded parent families -> root
        if not indi.family_ids_as_child:
            return True
        for fam_id in indi.family_ids_as_child:
            fam = data.families.get(fam_id)
            if not fam:
                continue
            for parent_id in (fam.husband_id, fam.wife_id):
                if parent_id and parent_id in data.individuals:
                    parent_gen = gen + 1
                    if g is None or parent_gen <= g:
                        return False
        return True

    tips = [r for r in records if is_branch_tip(r)]

    # Sorting
    sort_key = getattr(args, "sort", None)
    if sort_key is None:
        sort_key = "path"

    if sort_key == "generation":
        tips.sort(key=lambda r: (r["generation"], r["path"]))
    elif sort_key == "path":
        tips.sort(key=lambda r: (r["path"], (r["individual"].last_name or "").lower(), r["individual"].id))
    elif sort_key == "name":
        # last_name None sorts last
        tips.sort(key=lambda r: ((r["individual"].last_name or "").lower() if r["individual"].last_name else "~", r["path"], r["individual"].id))
    elif sort_key == "id":
        tips.sort(key=lambda r: r["individual"].id)

    # Format: generation, path, last_name (or (unknown)), id (with @)
    for r in tips:
        indi = r["individual"]
        gen = r["generation"]
        path = r["path"]
        last = indi.last_name or "(unknown)"
        print(f"{gen}\t{path}\t{last}\t{indi.id}")
