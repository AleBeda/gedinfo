import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "gedinfo"] + args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_stat_simple():
    code, out, err = run_cmd(["stat", str(FIXTURES / "simple.ged")])
    assert code == 0
    assert err == ""
    expected = [
        "Individuals: 4",
        "  Males: 2",
        "  Females: 2",
        "  Unknown sex: 0",
        "  Roots (no parents): 2",
        "  Leaves (no children): 2",
        "  No name: 0",
        "  Incomplete name: 0",
        "  Living (_LIVING = Y): 0",
        "",
        "Families: 1",
        "  Families with unnamed/incomplete parent: 0",
        "  Families with no children: 0",
        "",
        "Generations: 2",
        "",
        "Disjoint forests: 1",
    ]
    assert out.strip().splitlines() == expected


def test_stat_empty():
    code, out, err = run_cmd(["stat", str(FIXTURES / "empty.ged")])
    assert code == 0
    assert err == ""
    expected = [
        "Individuals: 0",
        "  Males: 0",
        "  Females: 0",
        "  Unknown sex: 0",
        "  Roots (no parents): 0",
        "  Leaves (no children): 0",
        "  No name: 0",
        "  Incomplete name: 0",
        "  Living (_LIVING = Y): 0",
        "",
        "Families: 0",
        "  Families with unnamed/incomplete parent: 0",
        "  Families with no children: 0",
        "",
        "Generations: 0",
        "",
        "Disjoint forests: 0",
    ]
    assert out.strip().splitlines() == expected


def test_stat_no_names():
    code, out, err = run_cmd(["stat", str(FIXTURES / "no_names.ged")])
    assert code == 0
    assert err == ""
    # two individuals have no name (I001, I004), two have incomplete names (I002, I003)
    from gedinfo import parser, queries

    data = parser.parse(FIXTURES / "no_names.ged")
    roots = queries.get_roots(data)
    expected_roots = len(queries.apply_root_filters(data, roots))
    lines = out.strip().splitlines()
    assert lines[0] == "Individuals: 4"
    assert lines[4].startswith("  Roots (no parents):")
    assert str(expected_roots) in lines[4]
    # remaining high-level assertions
    assert "  No name: 2" in lines
    assert "  Incomplete name: 2" in lines


def test_stat_multi_tree():
    code, out, err = run_cmd(["stat", str(FIXTURES / "multi_tree.ged")])
    assert code == 0
    assert err == ""
    expected = [
        "Individuals: 4",
        "  Males: 3",
        "  Females: 1",
        "  Unknown sex: 0",
        "  Roots (no parents): 2",
        "  Leaves (no children): 2",
        "  No name: 0",
        "  Incomplete name: 0",
        "  Living (_LIVING = Y): 0",
        "",
        "Families: 2",
        "  Families with unnamed/incomplete parent: 0",
        "  Families with no children: 0",
        "",
        "Generations: 2",
        "",
        "Disjoint forests: 2",
    ]
    assert out.strip().splitlines() == expected


def test_stat_roots_default_count():
    code, out, err = run_cmd(["stat", str(FIXTURES / "spouse.ged")])
    assert code == 0
    # compute expected via queries.apply_root_filters default
    from gedinfo import parser, queries

    data = parser.parse(FIXTURES / "spouse.ged")
    roots = queries.get_roots(data)
    expected = len(queries.apply_root_filters(data, roots))
    lines = out.splitlines()
    roots_line = [l for l in lines if l.strip().startswith("Roots (no parents):")][0]
    assert str(expected) in roots_line


def test_stat_roots_with_spouse_flag():
    code, out, err = run_cmd(["stat", "--spouse", str(FIXTURES / "spouse.ged")])
    assert code == 0
    from gedinfo import parser, queries

    data = parser.parse(FIXTURES / "spouse.ged")
    roots = queries.get_roots(data)
    expected = len(
        queries.apply_root_filters(data, roots, include_spouse_suppressed=True)
    )
    roots_line = [
        l for l in out.splitlines() if l.strip().startswith("Roots (no parents):")
    ][0]
    assert str(expected) in roots_line
    assert "+spouse" in roots_line or "(all)" in roots_line


def test_stat_roots_with_unknowns_flag():
    code, out, err = run_cmd(["stat", "-u", str(FIXTURES / "spouse.ged")])
    assert code == 0
    from gedinfo import parser, queries

    data = parser.parse(FIXTURES / "spouse.ged")
    roots = queries.get_roots(data)
    expected = len(queries.apply_root_filters(data, roots, include_unknowns=True))
    roots_line = [
        l for l in out.splitlines() if l.strip().startswith("Roots (no parents):")
    ][0]
    assert str(expected) in roots_line


def test_stat_roots_with_all_flag():
    code, out, err = run_cmd(["stat", "-a", str(FIXTURES / "spouse.ged")])
    assert code == 0
    from gedinfo import parser, queries

    data = parser.parse(FIXTURES / "spouse.ged")
    roots = queries.get_roots(data)
    expected = len(
        queries.apply_root_filters(
            data, roots, include_spouse_suppressed=True, include_unknowns=True
        )
    )
    roots_line = [
        l for l in out.splitlines() if l.strip().startswith("Roots (no parents):")
    ][0]
    assert str(expected) in roots_line


def test_stat_all_with_spouse_error():
    code, out, err = run_cmd(["stat", "-a", "--spouse", str(FIXTURES / "spouse.ged")])
    assert code == 1


def test_stat_other_counts_unaffected_by_flags():
    code1, out1, err1 = run_cmd(["stat", str(FIXTURES / "spouse.ged")])
    code2, out2, err2 = run_cmd(["stat", "-a", str(FIXTURES / "spouse.ged")])

    # compare Individuals, Families, Leaves lines are identical
    def pick(lines, prefix):
        return [l for l in lines if l.startswith(prefix)][0]

    lines1 = out1.splitlines()
    lines2 = out2.splitlines()
    assert pick(lines1, "Individuals:") == pick(lines2, "Individuals:")
    assert pick(lines1, "Families:") == pick(lines2, "Families:")
    assert pick(lines1, "  Leaves (no children):") == pick(
        lines2, "  Leaves (no children):"
    )
