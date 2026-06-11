"""Unit tests for gedinfo.tui pure logic (no textual required)."""

from pathlib import Path

import pytest

from gedinfo.parser import parse
from gedinfo.tui import NavItem, _go_to_root, build_nav_items

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def relatives_data():
    return parse(FIXTURES / "relatives.ged")


def left_items(items: list[NavItem]) -> list[NavItem]:
    return [i for i in items if i.pane == "left"]


def center_items(items: list[NavItem]) -> list[NavItem]:
    return [i for i in items if i.pane == "center"]


def right_items(items: list[NavItem]) -> list[NavItem]:
    return [i for i in items if i.pane == "right"]


def test_parents_in_left_pane(relatives_data):
    # I001 (Bob Smith) has parents I002 (father) and I003 (mother) via F000
    items = build_nav_items(relatives_data, "@I001@")
    left = left_items(items)
    assert len(left) == 2
    labels = {i.label for i in left}
    assert "father:" in labels
    assert "mother:" in labels
    for item in left:
        assert item.individual is not None


def test_self_in_center_pane(relatives_data):
    items = build_nav_items(relatives_data, "@I001@")
    center = center_items(items)
    assert center[0].label == "self:"
    assert center[0].individual is not None
    assert center[0].individual.id == "@I001@"


def test_spouse_in_center_pane(relatives_data):
    # I001 has spouses: I004 (wife, F001), I007 (wife, F002), unknown (F003)
    items = build_nav_items(relatives_data, "@I001@")
    center = center_items(items)
    spouse_labels = {i.label for i in center if i.label != "self:"}
    assert "wife:" in spouse_labels


def test_children_in_right_pane(relatives_data):
    # I001 has children: I005 (son), I006 (daughter) via F001; I008 (child) via F003
    items = build_nav_items(relatives_data, "@I001@")
    right = right_items(items)
    assert len(right) >= 2
    labels = [i.label for i in right]
    assert "son:" in labels
    assert "daughter:" in labels


def test_no_relatives_individual(relatives_data):
    # I005 (Charlie Smith) has no spouse and no children; has parents via F001
    # Test with an individual that has no parents, no spouses, no children
    # Build minimal data: use simple.ged or craft inline
    from gedinfo.models import GedcomData, Individual
    data = GedcomData()
    lone = Individual(id="@I999@", first_name="Lone", last_name="Wolf")
    data.individuals["@I999@"] = lone

    items = build_nav_items(data, "@I999@")
    assert left_items(items) == []
    assert right_items(items) == []
    assert len(center_items(items)) == 1
    assert center_items(items)[0].label == "self:"


def test_date_hint_on_self_both(relatives_data):
    # I002 (John Smith) has birth 1 JAN 1900 and death 1 JAN 1970
    items = build_nav_items(relatives_data, "@I002@")
    self_item = center_items(items)[0]
    assert "1 JAN 1900" in self_item.date_hint
    assert "1 JAN 1970" in self_item.date_hint
    assert " – " in self_item.date_hint


def test_date_hint_on_self_birth_only(relatives_data):
    # I001 (Bob Smith) has birth 3 APR 1930 but no death date
    items = build_nav_items(relatives_data, "@I001@")
    self_item = center_items(items)[0]
    assert "3 APR 1930" in self_item.date_hint
    assert " – " not in self_item.date_hint


def test_date_hint_on_spouse(relatives_data):
    # I001's marriage to I004 (F001) has date 10 OCT 1955
    items = build_nav_items(relatives_data, "@I001@")
    center = center_items(items)
    spouse_items = [i for i in center if i.label == "wife:"]
    # Find the one with a marriage date
    dated = [i for i in spouse_items if i.date_hint.startswith("m. ")]
    assert dated, "Expected at least one spouse item with marriage date hint"
    assert "10 OCT 1955" in dated[0].date_hint


def test_unknown_individual_raises(relatives_data):
    with pytest.raises(ValueError, match="Unknown individual ID"):
        build_nav_items(relatives_data, "@I999@")


def test_idx_assignment(relatives_data):
    items = build_nav_items(relatives_data, "@I001@")
    assert [i.idx for i in items] == list(range(len(items)))


def test_idx_starts_at_zero(relatives_data):
    items = build_nav_items(relatives_data, "@I001@")
    assert items[0].idx == 0


def test_go_to_root_from_child(relatives_data):
    # I001's first parent is I002 (father, no parents) — root should be I002
    root = _go_to_root(relatives_data, "@I001@")
    assert root == "@I002@"


def test_go_to_root_already_at_root(relatives_data):
    # I002 (John Smith) has no parents — root is itself
    root = _go_to_root(relatives_data, "@I002@")
    assert root == "@I002@"


def test_go_to_root_two_generations(relatives_data):
    # I005 (Charlie) → parent I001 (Bob, father) → parent I002 (John, no parents)
    root = _go_to_root(relatives_data, "@I005@")
    assert root == "@I002@"


def test_left_items_before_center_before_right(relatives_data):
    items = build_nav_items(relatives_data, "@I001@")
    panes = [i.pane for i in items]
    # All "left" items come before any "center" item, which come before any "right" item
    last_left = max((j for j, p in enumerate(panes) if p == "left"), default=-1)
    first_center = min((j for j, p in enumerate(panes) if p == "center"), default=len(panes))
    last_center = max((j for j, p in enumerate(panes) if p == "center"), default=-1)
    first_right = min((j for j, p in enumerate(panes) if p == "right"), default=len(panes))
    assert last_left < first_center
    assert last_center < first_right


def test_family_id_on_spouse_items(relatives_data):
    # Spouse items in center pane should carry the marriage family_id; self item should be None
    items = build_nav_items(relatives_data, "@I001@")
    center = center_items(items)
    self_item = center[0]
    assert self_item.family_id is None
    spouse_items = [i for i in center if i.label != "self:"]
    for item in spouse_items:
        assert item.family_id is not None
        assert item.family_id.startswith("@F")


def test_center_cursor_zero_shows_all_children(relatives_data):
    # cursor on self (idx 0) → target_fam is None → all children shown
    items_default = build_nav_items(relatives_data, "@I001@")
    right_default = right_items(items_default)
    labels_default = [i.label for i in right_default]
    # I001 has children via F001 and F003 — should show all
    assert "son:" in labels_default
    assert "daughter:" in labels_default


def test_center_cursor_on_spouse_filters_right_pane(relatives_data):
    # I001's second spouse in F002 has no children; right pane should be empty for that cursor
    # Find which center index corresponds to a spouse with no children (I007 via F002)
    items = build_nav_items(relatives_data, "@I001@")
    center = center_items(items)
    # Find the spouse item whose family_id is @F002@
    f002_idx = next(
        (i for i, item in enumerate(center) if item.family_id == "@F002@"),
        None,
    )
    assert f002_idx is not None, "Expected a spouse item for F002"
    # Rebuild with cursor on that spouse — right pane should be empty (F002 has no children)
    items_filtered = build_nav_items(relatives_data, "@I001@", center_cursor=f002_idx)
    assert right_items(items_filtered) == []


def test_center_cursor_on_f001_spouse_shows_f001_children(relatives_data):
    # I001's spouse in F001 (Alice, I004) has children I005 + I006; cursor on that spouse
    items = build_nav_items(relatives_data, "@I001@")
    center = center_items(items)
    f001_idx = next(
        (i for i, item in enumerate(center) if item.family_id == "@F001@"),
        None,
    )
    assert f001_idx is not None
    items_filtered = build_nav_items(relatives_data, "@I001@", center_cursor=f001_idx)
    right = right_items(items_filtered)
    assert len(right) == 2
    labels = [i.label for i in right]
    assert "son:" in labels
    assert "daughter:" in labels


def test_idx_sequential_after_center_cursor_change(relatives_data):
    # idx values must always be sequential 0..N-1 regardless of center_cursor
    items = build_nav_items(relatives_data, "@I001@", center_cursor=1)
    assert [i.idx for i in items] == list(range(len(items)))
