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
        if getattr(args, "long", False):
            records = get_ancestor_details(data, args.indi_id, max_generations=g)
        else:
            surnames = get_ancestors(data, args.indi_id, max_generations=g)
    except ValueError as exc:
        raise ValueError(str(exc))

    if not getattr(args, "long", False):
        for s in surnames:
            print(s)
        return

    # Filter out nameless ancestors unless --unknown was requested
    include_unknown = getattr(args, "unknown", False)
    if not include_unknown:
        records = [r for r in records if not (not r["individual"].first_name and not r["individual"].last_name)]

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

    # Helper to convert path string to a sortable tuple (paternal-to-maternal order)
    def path_to_sort_key(path: str) -> tuple:
        """Convert path 'ppm...' to tuple where p=0, ?=1, m=2 for proper ordering."""
        char_map = {'p': 0, '?': 1, 'm': 2}
        return tuple(char_map.get(ch, 3) for ch in path)

    # Sorting
    sort_key = getattr(args, "sort", None)
    if sort_key is None:
        sort_key = "path"

    if sort_key == "generation":
        tips.sort(key=lambda r: (r["generation"], path_to_sort_key(r["path"])))
    elif sort_key == "path":
        tips.sort(key=lambda r: (path_to_sort_key(r["path"]), (r["individual"].last_name or "").lower(), r["individual"].id))
    elif sort_key == "name":
        # last_name None sorts last
        tips.sort(key=lambda r: ((r["individual"].last_name or "").lower() if r["individual"].last_name else "~", path_to_sort_key(r["path"]), r["individual"].id))
    elif sort_key == "id":
        tips.sort(key=lambda r: r["individual"].id)

    # Format: generation, path, last_name (or (unknown)), id (without @)
    # Add extra tab if last_name is shorter than 8 chars for ID alignment
    for r in tips:
        indi = r["individual"]
        gen = r["generation"]
        path = r["path"]
        last = indi.last_name or "(unknown)"
        id_str = indi.id.replace("@", "")
        extra_tab = "\t" if len(last) < 8 else ""
        print(f"{gen}\t{path}\t{last}{extra_tab}\t{id_str}")
