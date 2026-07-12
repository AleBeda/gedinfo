"""Shared statistic aggregation used by both the CLI and the TUI.

Keeping the counting logic here (rather than inside a command's ``run``) lets
the ``stat`` command and the TUI statistics screen report the *same* numbers,
which they historically did not.
"""

from __future__ import annotations

from .models import GedcomData
from .queries import (
    apply_root_filters,
    count_families_no_children,
    count_families_with_unnamed_parent,
    count_generations,
    count_incomplete_name,
    count_no_name,
    get_connected_components,
    get_leaves,
    get_living,
    get_roots,
)


def collect_stats(
    data: GedcomData,
    *,
    include_spouse_suppressed: bool = False,
    include_unknowns: bool = False,
) -> dict[str, int]:
    """Compute the summary counts for a GEDCOM dataset.

    These are the canonical numbers for BOTH the CLI ``stat`` command and the
    TUI statistics screen; both must format this dict rather than counting
    independently. ``include_spouse_suppressed`` and ``include_unknowns`` are
    passed straight through to :func:`apply_root_filters`, matching how the
    ``stat`` command wires its ``--spouse``/``--unknown`` (and ``--all``) flags.
    """
    roots_list = apply_root_filters(
        data,
        get_roots(data),
        include_spouse_suppressed=include_spouse_suppressed,
        include_unknowns=include_unknowns,
    )
    return {
        "individuals": len(data.individuals),
        "males": sum(1 for i in data.individuals.values() if i.sex == "M"),
        "females": sum(1 for i in data.individuals.values() if i.sex == "F"),
        "unknown_sex": sum(1 for i in data.individuals.values() if i.sex == "U"),
        "roots": len(roots_list),
        "leaves": len(get_leaves(data)),
        "no_name": count_no_name(data),
        "incomplete_name": count_incomplete_name(data),
        "living": len(get_living(data)),
        "families": len(data.families),
        "unnamed_parent_families": count_families_with_unnamed_parent(data),
        "childless_families": count_families_no_children(data),
        "generations": count_generations(data),
        "disjoint": len(get_connected_components(data)),
    }
