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
    get_ancestor_details,
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


def test_normalise_id_various():
    # explicit and implicit forms
    assert normalise_id("@I123@") == "@I123@"
    assert normalise_id("I123") == "@I123@"
    assert normalise_id("I123@") == "@I123@"


def test_root_leaf_overlap():
    # in no_names.ged every individual has no parents and no children
    data = load("no_names.ged")
    roots = {i.id for i in get_roots(data)}
    leaves = {i.id for i in get_leaves(data)}
    assert roots == leaves


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


def test_find_by_name_last_name_partial():
    data = parser.parse(FIXTURES / "refinements.ged")
    res = find_by_name(data, "smith")
    ids = [r.id for r in res]
    assert ids == ["@I001@", "@I002@", "@I005@"]


def test_find_by_name_last_name_exact():
    data = parser.parse(FIXTURES / "refinements.ged")
    res = find_by_name(data, "Smith")
    ids = [r.id for r in res]
    assert ids == ["@I001@", "@I002@", "@I005@"]


def test_find_by_name_first_name_partial():
    data = parser.parse(FIXTURES / "refinements.ged")
    res = find_by_name(data, "joh")
    ids = [r.id for r in res]
    # Johann (@I003@) and John (@I001@) match
    assert set(ids) == {"@I001@", "@I003@"}


def test_find_by_name_first_name_only_match():
    data = parser.parse(FIXTURES / "refinements.ged")
    res = find_by_name(data, "ali")
    ids = [r.id for r in res]
    assert ids == ["@I004@"]


def test_find_by_name_no_match():
    data = parser.parse(FIXTURES / "refinements.ged")
    res = find_by_name(data, "xyz")
    assert res == []


def test_find_by_name_nameless_never_matches():
    data = parser.parse(FIXTURES / "refinements.ged")
    res = find_by_name(data, "smith")
    ids = [r.id for r in res]
    assert "@I006@" not in ids


def test_find_by_name_slash_stripped():
    data = parser.parse(FIXTURES / "refinements.ged")
    a = find_by_name(data, "/Smith/")
    b = find_by_name(data, "Smith")
    assert [r.id for r in a] == [r.id for r in b]


def test_find_by_name_case_insensitive():
    data = parser.parse(FIXTURES / "refinements.ged")
    a = find_by_name(data, "SMITH")
    b = find_by_name(data, "smith")
    assert [r.id for r in a] == [r.id for r in b]


def test_find_by_name_whitespace_normalised():
    data = parser.parse(FIXTURES / "refinements.ged")
    a = find_by_name(data, "  smith  ")
    b = find_by_name(data, "smith")
    assert [r.id for r in a] == [r.id for r in b]


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


def test_get_ancestor_details_all():
    data = parser.parse(FIXTURES / "long_ancestors.ged")
    res = get_ancestor_details(data, "@I001@")
    ids = {r["individual"].id for r in res}
    assert ids == {"@I002@", "@I003@", "@I004@", "@I005@", "@I006@", "@I007@", "@I008@", "@I009@"}
    # spot checks
    found = {r["individual"].id: r for r in res}
    assert found["@I004@"]["generation"] == 3
    assert found["@I004@"]["path"] == "pp"
    assert found["@I009@"]["generation"] == 4
    assert found["@I009@"]["path"] == "pp?"


def test_get_ancestor_details_g2():
    data = parser.parse(FIXTURES / "long_ancestors.ged")
    res = get_ancestor_details(data, "@I001@", max_generations=2)
    ids = [r["individual"].id for r in res]
    assert set(ids) == {"@I002@", "@I003@"}


def test_get_ancestor_details_g3():
    data = parser.parse(FIXTURES / "long_ancestors.ged")
    res = get_ancestor_details(data, "@I001@", max_generations=3)
    assert len(res) == 6


def test_get_ancestor_details_cycle(tmp_path):
    content = (
        "0 HEAD\n"
        "0 @I1@ INDI\n"
        "1 FAMC @F1@\n"
        "0 @I2@ INDI\n"
        "1 FAMC @F2@\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I2@\n"
        "1 CHIL @I1@\n"
        "0 @F2@ FAM\n"
        "1 HUSB @I1@\n"
        "1 CHIL @I2@\n"
        "0 TRLR\n"
    )
    f = tmp_path / "cycle.ged"
    f.write_text(content)
    data = parser.parse(f)
    res = get_ancestor_details(data, "@I1@")
    # should terminate and return without infinite loop
    assert isinstance(res, list)


def test_get_ancestor_details_unknown_id():
    data = parser.parse(FIXTURES / "long_ancestors.ged")
    with pytest.raises(ValueError):
        get_ancestor_details(data, "@I999@")


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
