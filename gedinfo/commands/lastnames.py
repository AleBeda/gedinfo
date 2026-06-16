"""`gedinfo lastnames` subcommand implementation."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ..parser import parse
from ..queries import get_ancestors, get_ancestor_details, get_descendant_details


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``lastnames`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "lastnames",
        help="Print distinct last names of all ancestors",
        description="Print distinct last names of all ancestors",
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
    sub.add_argument(
        "-u",
        "--unknown",
        action="store_true",
        default=False,
        help=(
            "Include ancestors with no name (no NAME tag in the GEDCOM file). "
            "By default, nameless ancestors are suppressed. "
            "In short mode this flag has no visible effect (nameless ancestors "
            "have no last name to print). In --long mode, nameless ancestors "
            "appear with '(unknown)' in the last-name field."
        ),
    )
    sub.add_argument(
        "-d",
        "--direction",
        choices=["ancestors", "descendants", "up", "down"],
        default="ancestors",
        help=(
            "Traversal direction: 'ancestors'/'up' for ancestors (default), "
            "'descendants'/'down' for descendants"
        ),
    )
    sub.add_argument("indi_id", help="Individual ID to inspect")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo lastnames`` is run."""
    g = args.generations
    if g is not None and g < 1:
        print("Invalid generations value: must be >= 1", file=sys.stderr)
        sys.exit(1)
    if getattr(args, "sort", None) and not getattr(args, "long", False):
        print("--sort requires --long", file=sys.stderr)
        sys.exit(1)

    direction = getattr(args, "direction", "ancestors")
    is_desc = direction in ("descendants", "down")

    data = parse(args.gedcom_file)
    try:
        if getattr(args, "long", False):
            if is_desc:
                records = get_descendant_details(data, args.indi_id, max_generations=g)
            else:
                records = get_ancestor_details(data, args.indi_id, max_generations=g)
        else:
            if is_desc:
                desc_records = get_descendant_details(
                    data, args.indi_id, max_generations=g
                )
                surnames = sorted(
                    {
                        r["individual"].last_name
                        for r in desc_records
                        if r["individual"].last_name
                    }
                )
            else:
                surnames = get_ancestors(data, args.indi_id, max_generations=g)
    except ValueError as exc:
        raise ValueError(str(exc))

    if not getattr(args, "long", False):
        for s in surnames:
            print(s)
        return

    # Filter out nameless records unless --unknown was requested
    include_unknown = getattr(args, "unknown", False)
    if not include_unknown:
        records = [
            r
            for r in records
            if r["individual"].first_name or r["individual"].last_name
        ]

    # Filter to branch-tip records only
    def is_branch_tip_anc(rec: dict) -> bool:
        indi = rec["individual"]
        gen = rec["generation"]
        if not indi.family_ids_as_child:
            return True
        for fam_id in indi.family_ids_as_child:
            fam = data.families.get(fam_id)
            if not fam:
                continue
            for parent_id in (fam.husband_id, fam.wife_id):
                if parent_id and parent_id in data.individuals:
                    if g is None or gen + 1 <= g:
                        return False
        return True

    def is_branch_tip_desc(rec: dict) -> bool:
        indi = rec["individual"]
        gen = rec["generation"]
        for fam_id in indi.family_ids_as_spouse:
            fam = data.families.get(fam_id)
            if not fam:
                continue
            for child_id in fam.child_ids:
                if child_id in data.individuals:
                    if g is None or gen + 1 <= g:
                        return False
        return True

    is_tip = is_branch_tip_desc if is_desc else is_branch_tip_anc
    tips = [r for r in records if is_tip(r)]

    def path_to_sort_key(path: str) -> tuple:
        char_map = {"p": 0, "s": 0, "?": 1, "m": 1, "d": 2}
        return tuple(char_map.get(ch, 3) for ch in path)

    sort_key = getattr(args, "sort", None) or "path"

    if sort_key == "generation":
        tips.sort(key=lambda r: (r["generation"], path_to_sort_key(r["path"])))
    elif sort_key == "path":
        tips.sort(
            key=lambda r: (
                path_to_sort_key(r["path"]),
                (r["individual"].last_name or "").lower(),
                r["individual"].id,
            )
        )
    elif sort_key == "name":
        tips.sort(
            key=lambda r: (
                (r["individual"].last_name or "").lower()
                if r["individual"].last_name
                else "~",
                path_to_sort_key(r["path"]),
                r["individual"].id,
            )
        )
    elif sort_key == "id":
        tips.sort(key=lambda r: r["individual"].id)

    for r in tips:
        indi = r["individual"]
        gen = r["generation"]
        path = r["path"]
        last = indi.last_name or "(unknown)"
        id_str = indi.id.replace("@", "")
        extra_tab = "\t" if len(last) < 8 else ""
        print(f"{gen}\t{path}\t{last}{extra_tab}\t{id_str}")
