"""`gedinfo givennames` subcommand implementation."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from importlib import resources
from pathlib import Path
from typing import Any

from ..parser import parse
from ..queries import get_ancestor_details, get_descendant_details


def _split_field(raw: str) -> list[str]:
    """Split a name field into individual name tokens.

    Separators are whitespace, commas, and forward slashes.
    Dash-connected substrings (no surrounding spaces) are kept together
    as composite names and are not split further.
    Blank or whitespace-only input returns an empty list.
    """
    text = raw.strip()
    if not text:
        return []
    parts = re.split(r"[\s,/]+", text)
    return [p for p in parts if p]


def _load_variants(variants_file: str | Path | None = None) -> dict[str, str]:
    """Return a mapping of name -> canonical_name (all lowercase).

    The canonical name for a group is its first token.
    If variants_file is None, the bundled gedinfo/data/name_variants.txt is used.
    """
    if variants_file is None:
        ref = resources.files("gedinfo.data").joinpath("name_variants.txt")
        text = ref.read_text(encoding="utf-8")
    else:
        text = Path(variants_file).read_text(encoding="utf-8")

    mapping: dict[str, str] = {}
    for line in text.splitlines():
        if "#" in line:
            line = line[:line.index("#")]
        tokens = line.lower().split()
        if not tokens:
            continue
        canonical = tokens[0]
        for token in tokens:
            mapping[token] = canonical
    return mapping


def _collect_names(
    data,
    indi_id: str,
    max_generations: int | None,
    use_second: bool,
    use_hebrew: bool,
    direction: str = "desc",
) -> tuple[Counter, Counter, Counter]:
    """Collect given-name counts for relatives in the chosen direction, split by sex.

    Returns (masculine_counter, feminine_counter, unknown_counter).
    Each counter maps lowercase name -> occurrence count across all relatives.
    A relative contributes each distinct name (from applicable fields) once.
    """
    if direction == "asc":
        records = get_ancestor_details(data, indi_id, max_generations=max_generations)
    else:
        records = get_descendant_details(data, indi_id, max_generations=max_generations)

    masc: Counter = Counter()
    fem: Counter = Counter()
    unkn: Counter = Counter()

    for rec in records:
        indi = rec["individual"]
        names: set[str] = set()

        if indi.first_name:
            for n in _split_field(indi.first_name):
                names.add(n.lower())

        for raw in indi.givn:
            for n in _split_field(raw):
                names.add(n.lower())

        if use_second:
            for raw in indi.nam2:
                for n in _split_field(raw):
                    names.add(n.lower())

        if use_hebrew:
            for raw in indi.namh:
                for n in _split_field(raw):
                    names.add(n.lower())

        target = masc if indi.sex == "M" else (fem if indi.sex == "F" else unkn)
        for n in names:
            target[n] += 1

    return masc, fem, unkn


def _apply_fuzzy(
    counter: Counter,
    variants: dict[str, str],
) -> list[tuple[int, str, dict[str, int]]]:
    """Group counter by variant equivalence; return sorted list.

    Each element: (total_count, representative_name, {variant: count}).
    The representative is the most-frequent variant; first-encountered breaks ties.
    Sorted descending by total, then ascending by representative name.
    """
    grouped: dict[str, dict[str, int]] = {}
    for name, count in counter.items():
        canonical = variants.get(name, name)
        grouped.setdefault(canonical, {})[name] = count

    result = []
    for var_counts in grouped.values():
        total = sum(var_counts.values())
        # max() keeps the first-seen element on ties, matching tree-traversal order
        representative = max(var_counts, key=lambda v: var_counts[v])
        result.append((total, representative, var_counts))

    result.sort(key=lambda x: (-x[0], x[1]))
    return result


def _print_section(
    label: str,
    counter: Counter,
    fuzzy: bool,
    variants: dict[str, str],
    sort_mode: str = "frequency",
) -> None:
    if not counter:
        return
    print(f"{label}:")
    if not fuzzy:
        if sort_mode == "name":
            items = sorted(counter.items(), key=lambda x: x[0])
        else:
            items = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
        for name, count in items:
            print(f"{count}\t{name.capitalize()}")
    else:
        groups = _apply_fuzzy(counter, variants)
        if sort_mode == "name":
            groups.sort(key=lambda x: x[1])
        for total, canonical, var_counts in groups:
            if len(var_counts) == 1:
                print(f"{total}\t{canonical.capitalize()}")
            else:
                detail = ", ".join(
                    f"{v.capitalize()}: {c}"
                    for v, c in sorted(var_counts.items(), key=lambda x: -x[1])
                )
                print(f"{total}\t{canonical.capitalize()}  ({detail})")
    print()


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """Register the ``givennames`` subcommand with the top-level parser."""
    sub = subparsers.add_parser(
        "givennames",
        help="Print given-name frequency for ancestors",
        description="Print given-name frequency for ancestors",
    )
    sub.add_argument(
        "-g", "--generations",
        type=int, default=None,
        help="Limit traversal to N generations (>=1)",
    )
    sub.add_argument(
        "-2", "--second",
        action="store_true", default=False,
        help="Include names from NAM2 (second/additional names)",
    )
    sub.add_argument(
        "-s", "--sort",
        choices=["frequency", "name"],
        default="frequency",
        help="Sort output by 'frequency' (default) or 'name'",
    )
    sub.add_argument(
        "-e", "--hebrew",
        action="store_true", default=False,
        help="Include names from NAMH (Hebrew names)",
    )
    sub.add_argument(
        "-a", "--all_names",
        action="store_true", default=False,
        help="Equivalent to --second --hebrew",
    )
    sub.add_argument(
        "-f", "--fuzzy",
        action="store_true", default=False,
        help="Group name variants together using the bundled variants file",
    )
    sub.add_argument(
        "-d", "--direction",
        choices=["asc", "desc"],
        default="desc",
        help="Traversal direction: 'asc' for ancestors, 'desc' for descendants (default: desc)",
    )
    sub.add_argument("indi_id", help="Individual ID to inspect")
    sub.add_argument("gedcom_file", help="Path to GEDCOM file")
    sub.set_defaults(func=run)


def run(args: Any) -> None:
    """Handler invoked when ``gedinfo givennames`` is run."""
    g = args.generations
    if g is not None and g < 1:
        print("Invalid generations value: must be >= 1", file=sys.stderr)
        sys.exit(1)

    use_second = args.second or args.all_names
    use_hebrew = args.hebrew or args.all_names

    data = parse(args.gedcom_file)

    masc, fem, unkn = _collect_names(data, args.indi_id, g, use_second, use_hebrew, args.direction)

    variants: dict[str, str] = {}
    if args.fuzzy:
        variants = _load_variants()

    _print_section("Masculine names", masc, args.fuzzy, variants, args.sort)
    _print_section("Feminine names", fem, args.fuzzy, variants, args.sort)
    _print_section("Unknown sex", unkn, args.fuzzy, variants, args.sort)
