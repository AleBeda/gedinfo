"""Pure functions operating on ``GedcomData`` instances.

Functions in this module perform lookups and graph traversals without any
side effects.  They are intentionally simple so that unit tests can exercise
them without invoking the CLI or parser.
"""

from __future__ import annotations

from collections import deque
from typing import List, Optional, Set

from .models import GedcomData, Individual


def normalise_id(indi_id: str) -> str:
    """Return the GEDCOM ID wrapped in ``@`` characters.

    The input may or may not already include the delimiters; the returned
    string will always start and end with ``@``.  Leading/trailing whitespace
    is trimmed and the value is returned unchanged if it already contains
    both delimiters.
    """
    s = indi_id.strip()
    if not s.startswith("@"):
        s = "@" + s
    if not s.endswith("@"):
        s = s + "@"
    return s


def find_by_id(data: GedcomData, indi_id: str) -> Optional[Individual]:
    """Look up an individual by ID in ``data``.

    ``indi_id`` may be supplied without surrounding ``@`` characters.
    Returns ``None`` if there is no matching individual.
    """
    key = normalise_id(indi_id)
    return data.individuals.get(key)


def display_name(individual: Individual) -> str:
    """Return a one-line display name for ``individual``.

    If both first and last names are known, they are joined with a space.
    If only one part is known, that part is returned.  If neither part is
    available, ``"(unknown)"`` is returned.
    """
    fn = individual.first_name
    ln = individual.last_name
    if fn and ln:
        return f"{fn} {ln}"
    if fn:
        return fn
    if ln:
        return ln
    return "(unknown)"


def _normalise_name(s: str) -> str:
    s = s.strip().lower()
    if "/" in s:
        s = s.replace("/", " ")
    return " ".join(s.split())


def find_by_name(data: GedcomData, name: str) -> List[Individual]:
    """Return a list of individuals whose full name matches ``name``.

    Matching is case-insensitive and normalises whitespace.  The surname may
    optionally be wrapped in slashes (``/Smith/``) as per GEDCOM conventions.
    """
    target = _normalise_name(name)
    matches: List[Individual] = []
    for indi in data.individuals.values():
        nm = display_name(indi)
        if _normalise_name(nm) == target:
            matches.append(indi)
    return matches


def get_roots(data: GedcomData) -> List[Individual]:
    """Return individuals who have no parents (i.e. appear in no family as a child)."""
    roots = [i for i in data.individuals.values() if not i.family_ids_as_child]
    return sorted(roots, key=lambda i: i.id)


def get_leaves(data: GedcomData) -> List[Individual]:
    """Return individuals who have no recorded children.

    A person is a leaf if they are not listed as a parent in any family, or
    all families they appear in as spouse lack children.
    """
    leaves: List[Individual] = []
    for indi in data.individuals.values():
        has_child = False
        for fam_id in indi.family_ids_as_spouse:
            fam = data.families.get(fam_id)
            if fam and fam.child_ids:
                has_child = True
                break
        if not has_child:
            leaves.append(indi)
    return sorted(leaves, key=lambda i: i.id)


def get_ancestors(
    data: GedcomData, indi_id: str, max_generations: Optional[int] = None
) -> List[str]:
    """Return distinct last names of ancestors of the given individual.

    The list is sorted alphabetically and deduplicated.  Generation counting
    begins at 1 for the individual themself.  If ``max_generations`` is
    specified, traversal stops after that many generations (must be >= 1).

    Raises ``ValueError`` if the supplied ``indi_id`` does not exist.
    """
    if max_generations is not None and max_generations < 1:
        raise ValueError("max_generations must be >= 1")
    indi = find_by_id(data, indi_id)
    if indi is None:
        raise ValueError(f"Unknown individual ID: {indi_id}")

    surnames: Set[str] = set()
    queue = deque([(indi, 1)])
    while queue:
        current, gen = queue.popleft()
        if gen > 1 and current.last_name:
            surnames.add(current.last_name)
        if max_generations is not None and gen >= max_generations:
            continue
        # add parents
        for fam_id in current.family_ids_as_child:
            fam = data.families.get(fam_id)
            if fam:
                for parent_id in (fam.husband_id, fam.wife_id):
                    if parent_id:
                        parent = data.individuals.get(parent_id)
                        if parent:
                            queue.append((parent, gen + 1))
    return sorted(surnames)


def get_connected_components(data: GedcomData) -> List[List[Individual]]:
    """Return a list of connected components of the family graph.

    Each component is a list of ``Individual`` instances.  Components and the
    individuals within them are sorted by ID.
    """
    parent_map: dict[str, str] = {}

    def find(x: str) -> str:
        parent_map.setdefault(x, x)
        if parent_map[x] != x:
            parent_map[x] = find(parent_map[x])
        return parent_map[x]

    def union(a: str, b: str) -> None:
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent_map[rb] = ra

    # initialise
    for indi in data.individuals.values():
        find(indi.id)
    # connect via families
    for fam in data.families.values():
        members: List[str] = []
        if fam.husband_id:
            members.append(fam.husband_id)
        if fam.wife_id:
            members.append(fam.wife_id)
        members.extend(fam.child_ids)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                union(members[i], members[j])
    comps: dict[str, List[Individual]] = {}
    for indi in data.individuals.values():
        root = find(indi.id)
        comps.setdefault(root, []).append(indi)
    result: List[List[Individual]] = []
    for root in sorted(comps):
        result.append(sorted(comps[root], key=lambda i: i.id))
    return result


def count_no_name(data: GedcomData) -> int:
    """Number of individuals with neither first nor last name."""
    return sum(
        1 for i in data.individuals.values() if not i.first_name and not i.last_name
    )


def count_incomplete_name(data: GedcomData) -> int:
    """Number of individuals with exactly one of first or last name."""
    return sum(
        1
        for i in data.individuals.values()
        if (i.first_name and not i.last_name) or (i.last_name and not i.first_name)
    )


def count_families_with_unnamed_parent(data: GedcomData) -> int:
    """Count families where either parent has no name or incomplete name."""

    def unnamed(id_: Optional[str]) -> bool:
        if not id_:
            return False
        indi = data.individuals.get(id_)
        if not indi:
            return False
        return not indi.first_name or not indi.last_name

    return sum(
        1
        for fam in data.families.values()
        if unnamed(fam.husband_id) or unnamed(fam.wife_id)
    )


def count_families_no_children(data: GedcomData) -> int:
    """Count families that have no children recorded."""
    return sum(1 for fam in data.families.values() if not fam.child_ids)
