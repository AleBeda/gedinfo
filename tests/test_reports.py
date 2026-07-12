"""Unit tests for gedinfo.reports.collect_stats."""

from pathlib import Path

from gedinfo import queries
from gedinfo.parser import parse
from gedinfo.reports import collect_stats

FIXTURES = Path(__file__).parent / "fixtures"


def test_collect_stats_simple():
    # Numbers pinned by tests/test_commands/test_stat.py::test_stat_simple.
    data = parse(FIXTURES / "simple.ged")
    stats = collect_stats(data)
    assert stats == {
        "individuals": 4,
        "males": 2,
        "females": 2,
        "unknown_sex": 0,
        "roots": 2,
        "leaves": 2,
        "no_name": 0,
        "incomplete_name": 0,
        "living": 0,
        "families": 1,
        "unnamed_parent_families": 0,
        "childless_families": 0,
        "generations": 2,
        "disjoint": 1,
    }


def test_collect_stats_refinements_roots_are_filtered():
    # Default flags apply the suppression filters, exactly as `gedinfo stat`
    # with no flags does — derive the expected count the same way test_stat.py
    # does rather than hardcoding it.
    data = parse(FIXTURES / "refinements.ged")
    expected_roots = len(queries.apply_root_filters(data, queries.get_roots(data)))
    stats = collect_stats(data)
    assert stats["individuals"] == len(data.individuals)
    assert stats["roots"] == expected_roots


def test_collect_stats_flags_passthrough():
    # The two keyword flags must reach apply_root_filters unchanged.
    data = parse(FIXTURES / "refinements.ged")
    all_expected = len(
        queries.apply_root_filters(
            data,
            queries.get_roots(data),
            include_spouse_suppressed=True,
            include_unknowns=True,
        )
    )
    stats = collect_stats(data, include_spouse_suppressed=True, include_unknowns=True)
    assert stats["roots"] == all_expected
