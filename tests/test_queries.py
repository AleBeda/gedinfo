import pytest
from gedinfo import parser
from gedinfo.queries import (
    normalise_id,
    find_by_id,
    display_name,
    find_by_name,
    get_roots,
    get_leaves,
    get_ancestors,
    get_connected_components,
    count_no_name,
    count_incomplete_name,
    count_families_with_unnamed_parent,
    count_families_no_children,
)

FIX = Path = __import__("pathlib").Path
FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return parser.parse(FIXTURES / name)


def test_find_by_id_found():
    data = load("simple.ged")
    assert find_by_id(data, "@I001@") is not None


def test_find_by_id_not_found():
    data = load("simple.ged")
    assert find_by_id(data, "@I999@") is None


def test_find_by_id_normalises():
    data = load("simple.ged")
    assert find_by_id(data, "I001") is not None


def test_display_name_both():
    ind = parser.parse(FIXTURES / "simple.ged").individuals["@I001@"]
    assert display_name(ind) == "John Smith"


def test_display_name_first_only():
    ind = parser.parse(FIXTURES / "no_names.ged").individuals["@I003@"]
    assert display_name(ind) == "Jane"


def test_display_name_last_only():
    ind = parser.parse(FIXTURES / "no_names.ged").individuals["@I002@"]
    assert display_name(ind) == "Smith"


def test_display_name_neither():
    ind = parser.parse(FIXTURES / "no_names.ged").individuals["@I001@"]
    assert display_name(ind) == "(unknown)"


def test_find_by_name_exact():
    data = load("simple.ged")
    result = find_by_name(data, "John Smith")
    assert len(result) == 1 and result[0].id == "@I001@"


def test_find_by_name_case_insensitive():
    data = load("simple.ged")
    result = find_by_name(data, "john smith")
    assert result and result[0].id == "@I001@"


def test_find_by_name_slash_syntax():
    data = load("simple.ged")
    assert find_by_name(data, "John /Smith/") == find_by_name(data, "John Smith")


def test_find_by_name_no_match():
    data = load("simple.ged")
    assert find_by_name(data, "Nonexistent Person") == []


def test_get_roots():
    data = load("simple.ged")
    ids = [i.id for i in get_roots(data)]
    assert ids == ["@I001@", "@I002@"]


def test_get_leaves():
    data = load("simple.ged")
    ids = [i.id for i in get_leaves(data)]
    assert ids == ["@I003@", "@I004@"]


def test_get_ancestors_unlimited():
    data = load("deep.ged")
    names = get_ancestors(data, "@I004@")
    assert names == ["Elder"]


def test_get_ancestors_limited():
    data = load("deep.ged")
    names = get_ancestors(data, "@I004@", max_generations=2)
    assert names == ["Elder"]


def test_get_ancestors_g1():
    data = load("deep.ged")
    names = get_ancestors(data, "@I004@", max_generations=1)
    assert names == []


def test_get_ancestors_large_g():
    data = load("deep.ged")
    assert get_ancestors(data, "@I004@", max_generations=999) == ["Elder"]


def test_get_ancestors_unknown_id():
    data = load("deep.ged")
    with pytest.raises(ValueError):
        get_ancestors(data, "@I999@")


def test_get_connected_components_single():
    data = load("simple.ged")
    comps = get_connected_components(data)
    assert len(comps) == 1 and comps[0][0].id == "@I001@"


def test_get_connected_components_multi():
    data = load("multi_tree.ged")
    comps = get_connected_components(data)
    assert len(comps) == 2


def test_get_connected_components_empty():
    data = load("empty.ged")
    assert get_connected_components(data) == []


def test_count_no_name():
    data = load("no_names.ged")
    assert count_no_name(data) == 2


def test_count_incomplete_name():
    data = load("no_names.ged")
    assert count_incomplete_name(data) == 2


def test_count_families_unnamed_parent(tmp_path):
    # create temporary ged with one family and unnamed parent
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 NAME /Smith/\n"
        "0 @I2@ INDI\n"
        "1 NAME John /Doe/\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I1@\n"
        "1 WIFE @I2@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "temp.ged"
    f.write_text(content)
    data = parser.parse(f)
    assert count_families_with_unnamed_parent(data) == 1


def test_count_families_no_children():
    data = load("simple.ged")
    assert count_families_no_children(data) == 0
    data2 = load("multi_tree.ged")
    assert count_families_no_children(data2) == 0
