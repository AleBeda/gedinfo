"""Pure functions operating on ``GedcomData`` instances.

Functions in this module perform lookups and graph traversals without any
side effects.  They are intentionally simple so that unit tests can exercise
them without invoking the CLI or parser.
"""

from __future__ import annotations

from collections import deque
from typing import List, Optional, Set
import re

from .models import Family, GedcomData, Individual

# Regex to parse IDs like @I123@ or I123 -> prefix 'I', number 123
_ID_RE = re.compile(r"^@?([A-Za-z]+)(\d+)@?$")


def id_sort_key(id_str: str):
    """Return a sort key for GEDCOM IDs that sorts numerically by the
    numeric suffix when possible. Examples: I89 < I123.

    Returns a tuple (prefix, number) when the pattern matches, otherwise
    falls back to the raw string for lexicographic ordering.
    """
    m = _ID_RE.match(id_str)
    if m:
        prefix = m.group(1)
        num = int(m.group(2))
        return (prefix, num)
    return (id_str, -1)


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
    """Normalise a name-like string for comparison.

    - Strip leading/trailing whitespace
    - Replace slash delimiters with spaces
    - Collapse internal whitespace and lower-case
    """
    s = s.strip().lower()
    if "/" in s:
        s = s.replace("/", " ")
    return " ".join(s.split())


def find_by_name(data: GedcomData, name: str) -> List[Individual]:
    """Return individuals matching a multi-token name query.

    The query is split into tokens on whitespace and commas. Each token is
    matched case-insensitively as a substring against either ``first_name``
    or ``last_name``. An individual matches only when every token matches at
    least one of those fields. Token order is irrelevant — "John Doe" and
    "Doe John" return identical results. Slash delimiters are accepted and
    ignored.

    Individuals with neither ``first_name`` nor ``last_name`` never match.
    Returns a list of matching ``Individual`` instances sorted by ``id``.
    """
    normalised = name.strip().lower().replace("/", " ").replace(",", " ")
    tokens = normalised.split()
    if not tokens:
        return []
    matches: List[Individual] = []
    for indi in data.individuals.values():
        if not indi.first_name and not indi.last_name:
            continue
        fn = _normalise_name(indi.first_name) if indi.first_name else ""
        ln = _normalise_name(indi.last_name) if indi.last_name else ""
        if all(t in fn or t in ln for t in tokens):
            matches.append(indi)
    return sorted(matches, key=lambda i: id_sort_key(i.id))


def get_ancestor_last_names(
    data: GedcomData,
    indi_id: str,
    max_generations: Optional[int] = None,
    include_unknown: bool = False,
) -> List[str]:
    """Return deduplicated, sorted last names for ancestors of indi_id.

    This helper wraps :func:`get_ancestor_details` and applies an optional
    filter to include nameless (unknown) ancestors. Unknown ancestors do not
    contribute a last-name string; they are only relevant when ``include_unknown``
    is True for callers that want to report presence of unnamed ancestors.
    """
    records = get_ancestor_details(data, indi_id, max_generations=max_generations)
    names = set()
    for rec in records:
        indi = rec["individual"]
        if not include_unknown and not indi.first_name and not indi.last_name:
            continue
        if indi.last_name:
            names.add(indi.last_name)
    return sorted(names)


def get_roots(data: GedcomData, sort_key: str | None = None) -> List[Individual]:
    """Return individuals who have no recorded parents.

    An individual is considered a root if they are not listed as a child in any
    family record. This is more robust than simply checking for the presence of
    a FAMC link on the individual record, since some GEDCOM files may contain
    spurious FAMC references that are not reflected in the corresponding family
    record's CHIL list.
    If sort_key is 'id', sort by numeric ID. If 'name', sort by display name.
    Otherwise (including None), return in GEDCOM file order.
    """
    child_ids: set[str] = set()
    for fam in data.families.values():
        child_ids.update(fam.child_ids)
    roots = [i for i in data.individuals.values() if i.id not in child_ids]
    if sort_key == "id":
        return sorted(roots, key=lambda i: id_sort_key(i.id))
    if sort_key == 'name':
        return sorted(roots, key=lambda i: display_name(i).lower())
    return roots


def get_leaves(data: GedcomData, sort_key: str | None = None) -> List[Individual]:
    """Return individuals who have no recorded children.

    A person is a leaf if they are not listed as a parent in any family, or
    all families they appear in as spouse lack children.

    If sort_key is 'id', sort by numeric ID. If 'name', sort by display name.
    Otherwise (including None), return in GEDCOM file order.
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
    if sort_key == "id":
        return sorted(leaves, key=lambda i: id_sort_key(i.id))
    if sort_key == "name":
        return sorted(leaves, key=lambda i: display_name(i).lower())
    return leaves


def get_all_individuals(data: GedcomData, sort_key: str | None = None) -> List[Individual]:
    """Return all individuals in the GEDCOM data.

    If sort_key is 'id', sort by numeric ID. If 'name', sort by display name.
    Otherwise (including None), return in GEDCOM file order.
    """
    individuals = list(data.individuals.values())
    if sort_key == "id":
        return sorted(individuals, key=lambda i: id_sort_key(i.id))
    if sort_key == "name":
        return sorted(individuals, key=lambda i: display_name(i).lower())
    return individuals


def get_males(data: GedcomData, sort_key: str | None = None) -> List[Individual]:
    """Return all male individuals (sex == 'M').

    If sort_key is 'id', sort by numeric ID. If 'name', sort by display name.
    Otherwise (including None), return in GEDCOM file order.
    """
    result = [i for i in data.individuals.values() if i.sex == "M"]
    if sort_key == "id":
        return sorted(result, key=lambda i: id_sort_key(i.id))
    if sort_key == "name":
        return sorted(result, key=lambda i: display_name(i).lower())
    return result


def get_females(data: GedcomData, sort_key: str | None = None) -> List[Individual]:
    """Return all female individuals (sex == 'F').

    If sort_key is 'id', sort by numeric ID. If 'name', sort by display name.
    Otherwise (including None), return in GEDCOM file order.
    """
    result = [i for i in data.individuals.values() if i.sex == "F"]
    if sort_key == "id":
        return sorted(result, key=lambda i: id_sort_key(i.id))
    if sort_key == "name":
        return sorted(result, key=lambda i: display_name(i).lower())
    return result


def get_nosex(data: GedcomData, sort_key: str | None = None) -> List[Individual]:
    """Return all individuals with unknown/unspecified sex (sex == 'U').

    If sort_key is 'id', sort by numeric ID. If 'name', sort by display name.
    Otherwise (including None), return in GEDCOM file order.
    """
    result = [i for i in data.individuals.values() if i.sex == "U"]
    if sort_key == "id":
        return sorted(result, key=lambda i: id_sort_key(i.id))
    if sort_key == "name":
        return sorted(result, key=lambda i: display_name(i).lower())
    return result


def get_living(data: GedcomData, sort_key: str | None = None) -> List[Individual]:
    """Return individuals whose living-flag field is True.

    Only individuals with living == True are included.

    If sort_key is 'id', sort by numeric ID. If 'name', sort by display name.
    Otherwise (including None), return in GEDCOM file order.
    """
    result = [i for i in data.individuals.values() if i.living is True]
    if sort_key == "id":
        return sorted(result, key=lambda i: id_sort_key(i.id))
    if sort_key == "name":
        return sorted(result, key=lambda i: display_name(i).lower())
    return result


def get_not_living(data: GedcomData, sort_key: str | None = None) -> List[Individual]:
    """Return individuals whose living-flag field is not True.

    Includes individuals with living == False and living == None.

    If sort_key is 'id', sort by numeric ID. If 'name', sort by display name.
    Otherwise (including None), return in GEDCOM file order.
    """
    result = [i for i in data.individuals.values() if i.living is not True]
    if sort_key == "id":
        return sorted(result, key=lambda i: id_sort_key(i.id))
    if sort_key == "name":
        return sorted(result, key=lambda i: display_name(i).lower())
    return result


def family_name_key(family: Family, data: GedcomData) -> str:
    """Return a sort key string for a Family for --sort name.

    Priority: husband display name > wife display name > first child display name
    > stripped family ID. Returns lowercase string for case-insensitive sorting.
    """
    for fid in (family.husband_id, family.wife_id) + family.child_ids:
        ind = data.individuals.get(fid)
        if ind:
            dn = display_name(ind)
            if dn != "(unknown)":
                return dn.lower()
    return family.id.strip("@").lower()


def get_all_families(data: GedcomData, sort_key: str | None = None) -> List[Family]:
    """Return all families in data.

    If sort_key is 'id', sort by numeric ID. If 'name', sort by family name.
    Otherwise (including None), return in GEDCOM file order.
    """
    families = list(data.families.values())
    if sort_key == "id":
        return sorted(families, key=lambda f: id_sort_key(f.id))
    if sort_key == "name":
        return sorted(families, key=lambda f: family_name_key(f, data))
    return families

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
    for root in sorted(comps, key=id_sort_key):
        result.append(sorted(comps[root], key=lambda i: id_sort_key(i.id)))
    return result


def get_ancestor_details(
    data: GedcomData, indi_id: str, max_generations: Optional[int] = None
) -> List[dict]:
    """BFS upward from ``indi_id``, returning details for each ancestor.

    Each returned dict has keys:
      - 'individual': Individual
      - 'generation': int (2 for parents, ...)
      - 'path': str (e.g. 'pp?')

    The subject (generation 1) is NOT included. Raises ``ValueError`` if
    ``indi_id`` is unknown. Traversal is cycle-safe (tracks visited IDs).
    """
    if max_generations is not None and max_generations < 1:
        raise ValueError("max_generations must be >= 1")
    root = find_by_id(data, indi_id)
    if root is None:
        raise ValueError(f"Unknown individual ID: {indi_id}")

    results: List[dict] = []
    visited: Set[str] = set()
    # queue items: (Individual, generation:int, path:str)
    q = deque()
    q.append((root, 1, ""))
    visited.add(root.id)

    while q:
        current, gen, path = q.popleft()
        # do not include subject
        if gen > 1:
            results.append({"individual": current, "generation": gen, "path": path})
        if max_generations is not None and gen >= max_generations:
            continue
        # enqueue parents
        for fam_id in current.family_ids_as_child:
            fam = data.families.get(fam_id)
            if not fam:
                continue
            for parent_id in (fam.husband_id, fam.wife_id):
                if not parent_id:
                    continue
                parent = data.individuals.get(parent_id)
                if not parent:
                    continue
                if parent.id in visited:
                    continue
                # determine path char based on parent's sex
                sex = (parent.sex or "U").upper()
                if sex == "M":
                    ch = "p"
                elif sex == "F":
                    ch = "m"
                else:
                    ch = "?"
                visited.add(parent.id)
                q.append((parent, gen + 1, path + ch))

    return results


def get_descendant_details(
    data: GedcomData, indi_id: str, max_generations: Optional[int] = None
) -> List[dict]:
    """BFS downward from ``indi_id``, returning details for each descendant.

    Each returned dict has keys:
      - 'individual': Individual
      - 'generation': int (2 for children, 3 for grandchildren, ...)
      - 'path': str (e.g. 'sd' — s=son/male, d=daughter/female, ?=unknown sex)

    The subject (generation 1) is NOT included. Raises ``ValueError`` if
    ``indi_id`` is unknown. Traversal is cycle-safe (tracks visited IDs).
    If ``max_generations`` is supplied, traversal stops when the generation
    counter reaches that limit (same semantics as ``get_ancestor_details``).
    """
    if max_generations is not None and max_generations < 1:
        raise ValueError("max_generations must be >= 1")
    root = find_by_id(data, indi_id)
    if root is None:
        raise ValueError(f"Unknown individual ID: {indi_id}")

    results: List[dict] = []
    visited: Set[str] = set()
    q: deque = deque()
    q.append((root, 1, ""))
    visited.add(root.id)

    while q:
        current, gen, path = q.popleft()
        if gen > 1:
            results.append({"individual": current, "generation": gen, "path": path})
        if max_generations is not None and gen >= max_generations:
            continue
        for fam_id in current.family_ids_as_spouse:
            fam = data.families.get(fam_id)
            if not fam:
                continue
            for child_id in fam.child_ids:
                child = data.individuals.get(child_id)
                if not child or child.id in visited:
                    continue
                sex = (child.sex or "U").upper()
                ch = "s" if sex == "M" else ("d" if sex == "F" else "?")
                visited.add(child.id)
                q.append((child, gen + 1, path + ch))

    return results


def find_relationships(
    data: GedcomData, id1: str, id2: str
) -> list[tuple]:
    """Find all common ancestors of two individuals.

    Returns a list of (ancestor, path1, path2) tuples where path1 and path2
    are lists of Individuals starting at the common ancestor and ending at
    the respective individual (inclusive on both ends). Raises ValueError if
    either ID is unknown. Returns an empty list when no common ancestor
    exists. Sorted by total path length ascending (closest first), then by
    ancestor display name for ties.
    """
    def _all_paths_up(start_id: str) -> dict:
        """DFS upward collecting ALL distinct paths to every ancestor.

        Returns {ancestor_id: [[start, ..., ancestor], ...]} — one list per
        distinct path. Per-path cycle detection prevents infinite loops in
        endogamous trees while still finding every valid lineage.
        """
        start = find_by_id(data, start_id)
        if start is None:
            raise ValueError(f"Unknown individual ID: {start_id}")
        # {anc_id: [path_a, path_b, ...]} where each path goes UP from start
        result: dict = {start.id: [[start]]}
        # stack items: (current_individual, ids_in_current_path, current_path)
        stack = [(start, {start.id}, [start])]
        while stack:
            current, path_ids, path = stack.pop()
            for fam_id in current.family_ids_as_child:
                fam = data.families.get(fam_id)
                if not fam:
                    continue
                for parent_id in (fam.husband_id, fam.wife_id):
                    if not parent_id or parent_id in path_ids:
                        continue  # already in this path — skip to avoid cycles
                    parent = data.individuals.get(parent_id)
                    if not parent:
                        continue
                    new_path = path + [parent]
                    result.setdefault(parent.id, []).append(new_path)
                    stack.append((parent, path_ids | {parent_id}, new_path))
        return result

    paths1 = _all_paths_up(id1)
    paths2 = _all_paths_up(id2)

    results = []
    for anc_id in set(paths1) & set(paths2):
        ancestor = data.individuals[anc_id]
        for p1_up in paths1[anc_id]:
            for p2_up in paths2[anc_id]:
                path1 = list(reversed(p1_up))
                path2 = list(reversed(p2_up))
                results.append((ancestor, path1, path2))

    results.sort(key=lambda t: (len(t[1]) + len(t[2]), display_name(t[0])))

    # Drop entries where any individual below the CA appears in both paths —
    # such an individual is itself a closer common ancestor that covers this one.
    results = [
        (anc, p1, p2) for anc, p1, p2 in results
        if not ({x.id for x in p1[1:]} & {x.id for x in p2[1:]})
    ]
    return results


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


def has_parents(data: GedcomData, individual: Individual) -> bool:
    """Return True if the individual has at least one recorded parent.

    An individual has parents if they have at least one FAMC link and at
    least one of the corresponding family records has a non-None husband_id
    or wife_id. FAMC links pointing to family IDs absent from data.families
    are silently ignored.

    When determining whether a family record indicates parentage, we ignore
    parent references that point to the individual themself or to one of the
    individual's spouses. This avoids treating malformed GEDCOM records that
    reference the individual as their own parent (or spousal parent) as
    evidence of parentage.
    """
    # Collect the individual's spouses (by ID) to avoid counting self/spousal
    # references as genuine parents.
    spouse_ids: set[str] = set()
    for fam_id in individual.family_ids_as_spouse:
        fam = data.families.get(fam_id)
        if not fam:
            continue
        if fam.husband_id and fam.husband_id != individual.id:
            spouse_ids.add(fam.husband_id)
        if fam.wife_id and fam.wife_id != individual.id:
            spouse_ids.add(fam.wife_id)

    for fam_id in individual.family_ids_as_child:
        fam = data.families.get(fam_id)
        if not fam:
            continue
        # Ignore parent references that are self or spouse.
        if (
            fam.husband_id
            and fam.husband_id not in spouse_ids
            and fam.husband_id != individual.id
        ):
            return True
        if (
            fam.wife_id
            and fam.wife_id not in spouse_ids
            and fam.wife_id != individual.id
        ):
            return True
    return False


def get_spouse_suppressed(data: GedcomData, roots: list[Individual]) -> set[str]:
    """Return the IDs of roots that are spouse-suppressed.

    A root is spouse-suppressed when it has at least one spouse who has
    parents (via has_parents), AND at least one parent of any such spouse
    has a known name (first_name or last_name is not None).

    Returns a set of individual ID strings. The input list is not mutated.
    """
    suppressed: set[str] = set()
    for root in roots:
        for fam_id in root.family_ids_as_spouse:
            fam = data.families.get(fam_id)
            if not fam:
                continue
            # collect spouse ids (exclude self)
            spouses: list[str] = []
            if fam.husband_id and fam.husband_id != root.id:
                spouses.append(fam.husband_id)
            if fam.wife_id and fam.wife_id != root.id:
                spouses.append(fam.wife_id)
            if not spouses:
                continue
            # for each spouse that has parents, check parents for a known name
            for spouse_id in spouses:
                spouse = data.individuals.get(spouse_id)
                if not spouse:
                    continue
                if not has_parents(data, spouse):
                    continue
                # spouse has parents; inspect all parents of this spouse
                for famc_id in spouse.family_ids_as_child:
                    famc = data.families.get(famc_id)
                    if not famc:
                        continue
                    for parent_id in (famc.husband_id, famc.wife_id):
                        if not parent_id:
                            continue
                        parent = data.individuals.get(parent_id)
                        if not parent:
                            continue
                        if parent.first_name or parent.last_name:
                            suppressed.add(root.id)
                            # found a named parent-in-law — suppression triggered
                            break
                    if root.id in suppressed:
                        break
                if root.id in suppressed:
                    break
            if root.id in suppressed:
                break
        # if no spouses, cannot be spouse-suppressed
    return suppressed


def get_unknown_roots(roots: list[Individual]) -> set[str]:
    """Return the IDs of roots that are nameless.

    A root is nameless if both first_name and last_name are None.
    Returns a set of individual ID strings.
    """
    return {r.id for r in roots if not r.first_name and not r.last_name}


def apply_root_filters(
    data: GedcomData,
    roots: list[Individual],
    include_spouse_suppressed: bool = False,
    include_unknowns: bool = False,
) -> list[Individual]:
    """Apply the standard suppression filters to a list of roots.

    By default (both flags False), removes spouse-suppressed roots and
    nameless roots. Each flag re-enables the corresponding group.

    Returns a new list preserving the order of surviving individuals.
    The input list is not mutated.
    """
    if not roots:
        return []
    spouse_suppressed = get_spouse_suppressed(data, roots)
    unknowns = get_unknown_roots(roots)
    result: list[Individual] = []
    for r in roots:
        if (r.id in spouse_suppressed) and not include_spouse_suppressed:
            continue
        if (r.id in unknowns) and not include_unknowns:
            continue
        result.append(r)
    return result


def count_families_no_children(data: GedcomData) -> int:
    """Count families that have no children recorded."""
    return sum(1 for fam in data.families.values() if not fam.child_ids)


def get_leaf_spouse_suppressed(data: GedcomData, leaves: list[Individual]) -> set[str]:
    """Return IDs of leaves whose spouse has children with another partner.

    A leaf is spouse-suppressed when it is in a childless family with a spouse
    who has children in some other family — indicating they married into the
    documented tree rather than representing an independent line.
    """
    suppressed: set[str] = set()
    for leaf in leaves:
        for fam_id in leaf.family_ids_as_spouse:
            fam = data.families.get(fam_id)
            if not fam:
                continue
            spouse_ids = []
            if fam.husband_id and fam.husband_id != leaf.id:
                spouse_ids.append(fam.husband_id)
            if fam.wife_id and fam.wife_id != leaf.id:
                spouse_ids.append(fam.wife_id)
            for spouse_id in spouse_ids:
                spouse = data.individuals.get(spouse_id)
                if not spouse:
                    continue
                for sfam_id in spouse.family_ids_as_spouse:
                    sfam = data.families.get(sfam_id)
                    if sfam and sfam.child_ids:
                        suppressed.add(leaf.id)
                        break
                if leaf.id in suppressed:
                    break
            if leaf.id in suppressed:
                break
    return suppressed


def apply_leaf_filters(
    data: GedcomData,
    leaves: list[Individual],
    include_spouse_suppressed: bool = False,
    include_unknown: bool = False,
) -> list[Individual]:
    """Apply suppression filters to a list of leaves.

    By default removes spouse-suppressed leaves and nameless leaves.
    Each flag re-enables the corresponding group.
    """
    if not leaves:
        return []
    spouse_suppressed = get_leaf_spouse_suppressed(data, leaves)
    unknowns = {leaf.id for leaf in leaves if not leaf.first_name and not leaf.last_name}
    result: list[Individual] = []
    for leaf in leaves:
        if leaf.id in spouse_suppressed and not include_spouse_suppressed:
            continue
        if leaf.id in unknowns and not include_unknown:
            continue
        result.append(leaf)
    return result


def count_generations(data: GedcomData) -> int:
    """Return the depth of the deepest generation in the family tree.

    Defined as the longest root-to-leaf path measured in generations.
    Roots (individuals with no known parents) are generation 1.
    Returns 0 if there are no individuals.
    """
    if not data.individuals:
        return 0

    child_ids_map: dict[str, list[str]] = {i: [] for i in data.individuals}
    remaining: dict[str, int] = {i: 0 for i in data.individuals}
    max_parent_gen: dict[str, int] = {i: 0 for i in data.individuals}

    for indi_id, indi in data.individuals.items():
        for fam_id in indi.family_ids_as_child:
            fam = data.families.get(fam_id)
            if fam:
                for p_id in [fam.husband_id, fam.wife_id]:
                    if p_id and p_id in data.individuals:
                        child_ids_map[p_id].append(indi_id)
                        remaining[indi_id] += 1

    gen: dict[str, int] = {}
    queue: deque[str] = deque()
    for indi_id in data.individuals:
        if remaining[indi_id] == 0:
            gen[indi_id] = 1
            queue.append(indi_id)

    while queue:
        indi_id = queue.popleft()
        for child_id in child_ids_map[indi_id]:
            if gen[indi_id] > max_parent_gen[child_id]:
                max_parent_gen[child_id] = gen[indi_id]
            remaining[child_id] -= 1
            if remaining[child_id] == 0:
                gen[child_id] = max_parent_gen[child_id] + 1
                queue.append(child_id)

    for indi_id in data.individuals:
        if indi_id not in gen:
            gen[indi_id] = 1

    return max(gen.values())


def get_noname(data: GedcomData, sort_key: str | None = None) -> List[Individual]:
    """Return all individuals with neither first nor last name."""
    result = [i for i in data.individuals.values() if not i.first_name and not i.last_name]
    if sort_key == "id":
        return sorted(result, key=lambda i: id_sort_key(i.id))
    if sort_key == "name":
        return sorted(result, key=lambda i: display_name(i).lower())
    return result
